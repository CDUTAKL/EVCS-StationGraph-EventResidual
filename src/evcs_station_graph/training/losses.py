"""事件感知损失函数。

提供 WeightedL1Loss，支持事件窗口样本的加权训练，解决事件样本仅占 ~0.1%
导致的梯度稀释问题。

两种权重模式：
- binary：基于 rule_trigger 的二值掩码，权重 = 1 + λ·trigger
- intensity：基于 visible_event_scores 的连续强度，权重 = 1 + λ·score_norm

数学直觉（重要性采样视角）：
  全局 MAE ≈ P(stable)·E[|e||stable] + P(event)·E[|e||event]
  标准 L1 对两项的梯度贡献正比于 P(region)，导致事件项被稳定项主导。
  加权后事件样本梯度 ≈ (1+λ) 倍，使两项在总梯度中更均衡。
"""

from __future__ import annotations

import torch
from torch import nn


class WeightedL1Loss(nn.Module):
    """对事件窗口样本施加更高权重的 L1 损失。

    weight = 1.0 + lambda * event_signal
    loss = mean(weight * |pred - target|)

    其中 event_signal 取决于 mode:
    - ``binary``: rule_trigger 的 bool→float 掩码 [B, N]。
      事件窗口内样本权重 = 1+λ，窗口外 = 1.0。
      最简形态，λ=2 时事件样本梯度贡献约翻 3 倍。
    - ``intensity``: visible_event_scores 的连续值 [B, N]。
      高分事件获得更高权重，低分事件接近等权。
      可选 per-batch 归一化到 [0, 1]——注意此口径为 **batch 内相对强度**
      （审查 M-01，2026-08-01：同一事件分数的权重随同 batch 其他样本变化，
      论文需披露 batch-relative，不声称绝对事件强度）。

    Args:
        lambda_: 事件权重系数。λ=0 退化为标准 L1Loss。
        mode: ``"binary"`` | ``"intensity"`` — 权重信号来源。
        normalize_intensity: intensity 模式下是否按 batch 最大值归一化
            （batch 内相对强度，权重随同 batch 样本分布变化——审查 M-01）。

    Note:
        权重仅应用于训练损失的反向传播。验证损失（早停判断）使用
        标准 L1Loss，因为早停应基于模型在原始分布上的泛化能力，
        而非加权分布上的表现。
    """

    def __init__(
        self,
        lambda_: float = 3.0,
        mode: str = "binary",
        normalize_intensity: bool = True,
    ) -> None:
        super().__init__()
        if lambda_ < 0:
            raise ValueError(f"lambda_ 必须非负，实际为 {lambda_}")
        if mode not in ("binary", "intensity"):
            raise ValueError(f"mode 必须为 'binary' 或 'intensity'，实际为 {mode}")
        self.lambda_ = float(lambda_)
        self.mode = mode
        self.normalize_intensity = normalize_intensity

    def forward(
        self,
        prediction: torch.Tensor,
        target: torch.Tensor,
        event_signal: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """计算加权 L1 损失。

        Args:
            prediction: [B, H, N] 预测负荷（已标准化）
            target: [B, H, N] 真实负荷（已标准化）
            event_signal: [B, N] 逐节点事件信号。
                binary 模式：布尔掩码（0/1）
                intensity 模式：连续事件分数（≥0）
                若为 None 或 λ=0，退化为标准 L1Loss。

        Returns:
            scalar 损失值（可用于 backward）
        """
        error = (prediction - target).abs()
        if event_signal is None or self.lambda_ <= 0:
            return error.mean()

        weight = self._compute_weight(event_signal, error)
        return (weight * error).mean()

    def _compute_weight(
        self,
        event_signal: torch.Tensor,
        error: torch.Tensor,
    ) -> torch.Tensor:
        """根据模式计算样本权重 [B, H, N]."""
        signal = event_signal.to(error.dtype)  # [B, N]

        if self.mode == "intensity" and self.normalize_intensity:
            # 按 batch 内最大值归一化，使 λ 的语义稳定
            # 例如 λ=3 意味着"最高强度事件比稳定窗口重 4 倍"
            max_val = signal.max()
            if max_val > 1e-8:
                signal = signal / max_val

        # weight = 1 + λ*signal, shape [B, N] → [B, 1, N] broadcast to [B, H, N]
        weight = 1.0 + self.lambda_ * signal
        return weight[:, None, :].expand_as(error)

    def extra_repr(self) -> str:
        return f"lambda_={self.lambda_}, mode={self.mode}"
