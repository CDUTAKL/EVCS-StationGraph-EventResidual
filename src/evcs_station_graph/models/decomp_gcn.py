"""SG-EXP-011：多分辨率分解 + 关系路由图卷积预测模型。

核心思想：将充电负荷时序信号分解为趋势（日平均）、周期（峰谷形态）和
瞬变（事件驱动）三个分量，每个分量通过最相关的关系图独立进行消息传递，
最后经可学习门控跨分量融合。

架构：
  X [B,T,N,F]
    ├─→ 趋势分支（大核平均池化，~3h 窗口）
    │     → 共享 TCN 编码 → load 关系图 GCN → H_trend
    ├─→ 周期分支（残差平滑，~1h 窗口）
    │     → 共享 TCN 编码 → pattern 关系图 GCN → H_season
    └─→ 瞬变分支（趋势+周期残差）
          → 共享 TCN 编码 → event 关系图 GCN → H_transient

  跨分量融合：γ = softmax([γ_t, γ_s, γ_r])，H = Σ γ_i * H_i
  预测头：Linear(D, H) → [B, H, N]

与 StaticGraph (SG-EXP-003) 的关键差异：
- StaticGraph: 混合信号 → 三类关系一字排开 → 门控选择
- DecompGCN:   分解信号 → 每个分量走专用关系通道 → 跨分量融合

路由消融 (SG-EXP-012) 通过 ``routing`` 参数控制：
  - "one_to_one": trend→load, season→pattern, transient→event（默认）
  - "full": 每个分量使用全部三类关系（类似 StaticGraph 但分分量）
  - "swapped": trend→pattern, season→event, transient→load（验证路由是否重要）
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from evcs_station_graph.models.common import ForecastModel, ForecastOutput
from evcs_station_graph.models.tcn import TemporalConvNet


# ========== 时序分解模块 ==========

class _SeriesDecomp(nn.Module):
    """两阶段移动平均时序分解。

    阶段 1：大核平均池化提取趋势分量（~3h = 12 步 × 15min）
    阶段 2：对残差做小核平滑提取周期分量（~1h = 4 步 × 15min）
    最终残差为瞬变分量。

    分解在 [B, N, F, T] 形状上进行，沿时间维（dim=-1）池化。
    """

    def __init__(self, trend_kernel: int = 12, season_kernel: int = 4) -> None:
        super().__init__()
        self.trend_kernel = trend_kernel
        self.season_kernel = season_kernel
        # 使用独立的 AvgPool1d（每次 forward 时根据输入长度动态 padding），
        # 因为偶数核大小在固定 padding=kernel//2 时会产生比输入多 1 的输出
        # （公式：output = input + 2*pad - kernel + 1，偶核时 = input + 1）
        self.trend_pool = nn.AvgPool1d(trend_kernel, stride=1, padding=0)
        self.season_pool = nn.AvgPool1d(season_kernel, stride=1, padding=0)

    def _smooth(self, x: torch.Tensor, pool: nn.AvgPool1d, kernel: int) -> torch.Tensor:
        """对 x 做保持长度的移动平均平滑。

        策略：两侧 replicate-pad 后池化，再裁剪回原长度。
        复制边界值填充保持序列两端自然，不引入零值伪影。
        """
        pad_left = kernel // 2
        pad_right = kernel - 1 - pad_left  # 保证总填充 = kernel-1，输出长度 = 输入长度
        x_padded = F.pad(x, (pad_left, pad_right), mode="replicate")
        smoothed = pool(x_padded)  # 输出长度 = 输入长度（因为填充了 kernel-1）
        return smoothed

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """分解输入序列。

        参数
        ----
        x: [B*N, F, T] — 所有节点展平的时间序列

        返回
        ----
        (trend, season, transient)，每个形状 [B*N, F, T]
        """
        trend = self._smooth(x, self.trend_pool, self.trend_kernel)
        residual_1 = x - trend
        season = self._smooth(residual_1, self.season_pool, self.season_kernel)
        transient = residual_1 - season
        return trend, season, transient


# ========== 单关系图卷积层（每分量专用） ==========

class _SingleRelationGCN(nn.Module):
    """单关系消息传递 + 残差连接 + LayerNorm。

    与 ``MultiRelationGatedGCN`` 不同，这里只处理一种关系，无需门控融合。
    设计为最简消息传递：邻居聚合 → 线性变换 → 残差 + 归一化。
    """

    def __init__(self, hidden_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.W = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, H: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """单关系图卷积前向。

        参数
        ----
        H: [B, N, D] 节点特征
        adj: [N, N] 归一化邻接矩阵

        返回
        ----
        [B, N, D] 聚合后的节点特征
        """
        # 邻居聚合：A @ H → [B, N, D]
        M = torch.einsum("nm,bmd->bnd", adj, H)
        # 变换 + 残差 + 归一化
        H_out = self.norm(H + self.dropout(self.W(M)))
        return H_out


# ========== 多分辨率分解图卷积预测模型 ==========

class DecompGCNForecast(ForecastModel):
    """多分辨率分解 + 关系路由 GCN 预测模型。

    构造签名：
      (input_dim, horizon, num_nodes, adjacencies, *,
       hidden_dim=32, levels=6, dropout=0.1,
       routing="one_to_one", trend_kernel=12, season_kernel=4)

    参数
    ----
    input_dim:
        输入特征维度 F。
    horizon:
        预测步数 H。
    num_nodes:
        节点数 N。
    adjacencies:
        邻接矩阵列表 [load_adj, event_adj, pattern_adj]，顺序固定。
        索引 0=load, 1=event, 2=pattern。
    hidden_dim:
        隐藏维度 D，默认 32（10 节点最优）。
    levels:
        TCN 层数，默认 6（感受野 127 ≥ 96 步历史窗口）。
    dropout:
        随机失活概率。
    routing:
        分量-关系路由策略：
        - "one_to_one": trend→load, season→pattern, transient→event
        - "full": 每个分量使用全部三类关系（含门控融合）
        - "swapped": trend→pattern, season→event, transient→load
    trend_kernel:
        趋势提取的池化核大小，默认 12（~3h at 15min 粒度）。
    season_kernel:
        周期提取的池化核大小，默认 4（~1h at 15min 粒度）。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        adjacencies: list[torch.Tensor],
        *,
        hidden_dim: int = 32,
        levels: int = 6,
        dropout: float = 0.1,
        routing: str = "one_to_one",
        trend_kernel: int = 12,
        season_kernel: int = 4,
    ) -> None:
        super().__init__()
        if num_nodes <= 0:
            raise ValueError("num_nodes 必须为正整数")
        if input_dim <= 0:
            raise ValueError("input_dim 必须为正整数")
        if horizon <= 0:
            raise ValueError("horizon 必须为正整数")
        if hidden_dim <= 0:
            raise ValueError("hidden_dim 必须为正整数")
        if levels <= 0:
            raise ValueError("levels 必须为正整数")
        if routing not in ("one_to_one", "full", "swapped"):
            raise ValueError(f"不支持的路由策略：{routing}，可选 one_to_one/full/swapped")
        if len(adjacencies) != 3:
            raise ValueError(
                f"DecompGCN 需要恰好 3 类关系 [load, event, pattern]，"
                f"实际收到 {len(adjacencies)} 类"
            )

        self.num_nodes = num_nodes
        self.hidden_dim = hidden_dim
        self.latent_dim = hidden_dim
        self.horizon = horizon
        self.routing = routing

        # 注册三类固定邻接矩阵为 buffer（索引 0=load, 1=event, 2=pattern）
        for idx, adj in enumerate(adjacencies):
            self.register_buffer(
                f"adj_{idx}", torch.as_tensor(adj, dtype=torch.float32),
            )

        # 时序分解器
        self.decomp = _SeriesDecomp(
            trend_kernel=trend_kernel, season_kernel=season_kernel,
        )

        # 共享 TCN 时间编码器（levels=6 保证 RF≥96）
        self.tcn = TemporalConvNet(
            input_dim, horizon,
            hidden_dim=hidden_dim, levels=levels, dropout=dropout,
        )
        del self.tcn.head  # 使用独立预测头，移除 TCN 自带 head

        # 分量专用 GCN（三个分量各一个）
        self.gcn_trend = _SingleRelationGCN(hidden_dim, dropout)
        self.gcn_season = _SingleRelationGCN(hidden_dim, dropout)
        self.gcn_transient = _SingleRelationGCN(hidden_dim, dropout)

        # 全连接路由模式下的额外交互：每个分量使用三类关系的门控融合
        if routing == "full":
            # 每个分量有独立的 3-relation 门控权重
            self.gamma_trend = nn.Parameter(torch.zeros(3))    # trend 的三关系权重
            self.gamma_season = nn.Parameter(torch.zeros(3))   # season 的三关系权重
            self.gamma_transient = nn.Parameter(torch.zeros(3))  # transient 的三关系权重

        # 跨分量融合权重（可学习，三标量经 softmax 归一化）
        self.component_gamma = nn.Parameter(torch.zeros(3))

        # 预测头
        self.head = nn.Linear(hidden_dim, horizon)

    def _get_routing_indices(self) -> list[list[int]]:
        """根据路由策略返回每个分量对应的关系索引列表。

        one_to_one: 每个分量只走一个关系
        full: 每个分量走全部三个关系
        swapped: 交叉路由（用于消融验证）
        """
        if self.routing == "one_to_one":
            # trend→load(0), season→pattern(2), transient→event(1)
            return [[0], [2], [1]]
        elif self.routing == "swapped":
            # trend→pattern(2), season→event(1), transient→load(0)
            return [[2], [1], [0]]
        else:  # full
            # 每个分量使用全部三类关系
            return [[0, 1, 2], [0, 1, 2], [0, 1, 2]]

    def _gcn_aggregate(
        self,
        H: torch.Tensor,
        gcn: _SingleRelationGCN,
        adj_indices: list[int],
        component_gamma: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """对单个分量执行关系路由的消息传递。

        参数
        ----
        H: [B, N, D] 分量隐表示
        gcn: 该分量专用的 GCN 层（full 模式下不使用）
        adj_indices: 该分量应使用的关系索引列表
        component_gamma: full 模式下的分量内关系门控权重，其它模式为 None

        返回
        ----
        [B, N, D] 聚合后的分量表示
        """
        if len(adj_indices) == 1:
            # 单关系路由：直接用该分量的 GCN + 指定关系
            adj = getattr(self, f"adj_{adj_indices[0]}")
            return gcn(H, adj)
        else:
            # 全连接路由：用多个关系分别聚合后门控融合
            beta = torch.softmax(component_gamma, dim=0)  # [R]
            M = torch.zeros_like(H)
            for i, adj_idx in enumerate(adj_indices):
                adj = getattr(self, f"adj_{adj_idx}")
                # 每个关系用独立 GCN 聚合，再按 beta 加权
                branch_out = gcn(H, adj)
                M = M + beta[i] * branch_out
            return M

    def _encode_component(
        self,
        x_comp: torch.Tensor,
        batch: int,
        nodes: int,
    ) -> torch.Tensor:
        """对单个分量执行 TCN 编码，返回 [B, N, D] 隐表示。

        参数
        ----
        x_comp: [B*N, F, T] 分量序列
        batch: batch 大小 B
        nodes: 节点数 N

        返回
        ----
        [B, N, D] 编码后的节点隐表示
        """
        encoded = self.tcn.network(x_comp)[..., -1]  # [B*N, D]
        return encoded.reshape(batch, nodes, self.hidden_dim)  # [B, N, D]

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """将 [B, T, N, F] 编码为 [B, N, D] 融合隐表示。

        流程：分解 → 各分量 TCN 编码 → 关系路由 GCN → 跨分量门控融合
        """
        if x.ndim != 4:
            raise ValueError("DecompGCN 输入必须为 [B, T, N, F]")
        batch, time_steps, nodes, features = x.shape

        # [B, T, N, F] → [B, N, F, T] → [B*N, F, T]
        x_flat = x.permute(0, 2, 3, 1).reshape(batch * nodes, features, time_steps)

        # 阶段 1：时序分解
        trend_raw, season_raw, transient_raw = self.decomp(x_flat)
        # 各分量形状均为 [B*N, F, T]

        # 阶段 2：各分量 TCN 编码
        H_trend = self._encode_component(trend_raw, batch, nodes)       # [B, N, D]
        H_season = self._encode_component(season_raw, batch, nodes)     # [B, N, D]
        H_transient = self._encode_component(transient_raw, batch, nodes)  # [B, N, D]

        # 阶段 3：关系路由 GCN 聚合
        routing_idx = self._get_routing_indices()

        if self.routing == "full":
            # 全连接模式：每个分量内部门控融合三类关系
            H_trend = self._gcn_aggregate(
                H_trend, self.gcn_trend, routing_idx[0], self.gamma_trend,
            )
            H_season = self._gcn_aggregate(
                H_season, self.gcn_season, routing_idx[1], self.gamma_season,
            )
            H_transient = self._gcn_aggregate(
                H_transient, self.gcn_transient, routing_idx[2], self.gamma_transient,
            )
        else:
            # one_to_one / swapped：每个分量走指定关系
            H_trend = self._gcn_aggregate(H_trend, self.gcn_trend, routing_idx[0])
            H_season = self._gcn_aggregate(H_season, self.gcn_season, routing_idx[1])
            H_transient = self._gcn_aggregate(H_transient, self.gcn_transient, routing_idx[2])

        # 阶段 4：跨分量门控融合
        gamma = torch.softmax(self.component_gamma, dim=0)  # [3]
        H_fused = (
            gamma[0] * H_trend
            + gamma[1] * H_season
            + gamma[2] * H_transient
        )  # [B, N, D]

        return H_fused

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        """由 [B, N, D] 融合隐表示生成 [B, H, N] 预测。"""
        prediction = self.head(latent)  # [B, N, H]
        return prediction.permute(0, 2, 1).contiguous()  # [B, H, N]

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        """统一前向接口。"""
        prediction = self.forecast_from_latent(self.encode(x))
        # 返回 load 关系图作为代表性邻接矩阵（供可视化）
        return ForecastOutput(
            prediction=prediction,
            adjacency=getattr(self, "adj_0"),
            relation_weights_gcn1=torch.softmax(self.component_gamma.detach(), dim=0),
        )
