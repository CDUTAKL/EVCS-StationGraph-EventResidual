# 补充实验清单

- **编制日期**：2026-07-30
- **前置条件**：夜跑（SG-EXP-002~006 三种子）结果已确认
- **代码分支**：`feat/multi-relation-gated-gcn`
- **底座模型**：AdaptiveGraph（B3 最优：levels=6, hidden=32, embed=12, fixed_weight=0.5）

---

## 执行顺序

```
Step 0: 确认夜跑结果（SG-EXP-002~006 三种子）
  ↓
Step 1: P0 基线实验（AGCRN / MLP / Graph WaveNet）
  ↓
Step 2: SG-EXP-007a 事件加权损失 λ 筛选
  ↓
Step 3: SG-EXP-007b 强度加权对比
  ↓
Step 4: P1 补充实验（叠加 / Bootstrap / 可视化）
  ↓
Step 5: P2 锦上添花（损失函数 / 节点敏感性 / 训练策略）
```

**Step 0 完成后才能进入 Step 1**——因为需要确认 AdaptiveGraph 三种子基线稳定，后续所有实验都以此为底座。

---

## Step 0：确认夜跑结果

**目标**：确认 SG-EXP-002~006 三种子正式实验全部完成，指标合理。

**检查清单**：

```
□ 服务器 SSH 连接（10.14.92.65）
□ outputs/night_run/<tag>/night_manifest.json 状态
□ SG-EXP-002 TCN 三种子指标（均值±标准差）
□ SG-EXP-003 StaticGraph 三种子指标
□ SG-EXP-004 AdaptiveGraph 三种子指标 ← 这是后续所有实验的底座基线
□ SG-EXP-005 EventResidual 三种子指标（重点关注事件窗口 MAE 均值±标准差）
□ SG-EXP-006 机制消融结果
□ 四格诊断 weighted_reconstructed_mae ≈ global_mae
```

**决策点**：
- 如果 SG-EXP-005 事件窗口改善 >10% 且统计显著 → 事件残差修正可以保留在标题中
- 如果 <5% 或不显著 → 按修订后的大纲，标题使用"事件感知机制"，重心转向 SG-EXP-007

---

## Step 1：P0 基线实验（致命硬伤修补）

> 两个 agent 独立判断：缺少 SOTA 基线是答辩中最可能被一击致命的点。

### 1.1 AGCRN（自适应图对比基线）

**目的**：与本文 AdaptiveGraph 的自适应图模块直接可比。AGCRN 也使用节点嵌入学习自适应邻接矩阵——如果 AGCRN 在你的数据上效果接近，则本文的"自适应图"贡献需要重新定位。

**方法**：
- 使用与 SG-EXP-002~006 **完全相同的**预测键、输入特征、可见性约束
- 节点嵌入维度与本文一致（embedding_dim=12）
- 三种子（2024/2025/2026）+ 早停 patience=8

**关键文件**：
- 新建 `configs/experiments/SG-EXP-008-agcrn-baseline.yaml`
- 参考实现：AGCRN 原始论文（Bai et al., NeurIPS 2020）

**预计耗时**：~2h（实现+训练）

**成功标准**：三种子结果写入对比表（§6.1.3 层次3）

---

### 1.2 3 层 MLP 基线（图结构必要性证明）

**目的**：排除"模型更大所以更好"的替代解释。将所有 10 个节点的 96 步历史拼接成一个向量（10×96×F），过 3 层 MLP 直接输出预测（10×4）。

**方法**：
- 输入：所有节点历史特征展平 [B, 10×96×F]
- 3 层全连接 + ReLU，参数量与 StaticGraph 可比（~25K）
- 三种子 + 早停

**关键文件**：
- 新建 `configs/experiments/SG-EXP-009-mlp-baseline.yaml`
- 可能需要新建轻量 MLP 模型 `src/evcs_station_graph/models/mlp.py` 或直接在脚本中实现

**预计耗时**：~0.5h

**成功标准**：MLP 的 MAE 必须显著高于 StaticGraph——这是证明"图结构必要"的门槛实验。若 MLP 接近甚至优于 GCN，整篇论文的图建模前提就塌了。

---

### 1.3 Graph WaveNet 或 STGCN（时空图 SOTA 参照）

**目的**：至少有一个标准时空图基线，证明本文的多关系门控 GCN 不是"选弱对手"。

**选择建议**：Graph WaveNet 优先——它的自适应邻接矩阵与本文场景更接近（不需要先验物理拓扑）。

**方法**：
- 使用与本文相同的预测键和输入特征
- 图结构使用本文的三类固定关系（取均值作为单图输入）
- 三种子 + 早停

**关键文件**：
- 新建 `configs/experiments/SG-EXP-010-graph-wavenet.yaml`
- 可参考 PyTorch Geometric 或自实现

**预计耗时**：~2h（实现+训练）

**成功标准**：三种子结果写入对比表

---

## Step 2：SG-EXP-007a 事件加权损失 λ 筛选

> 代码和配置就绪：`src/evcs_station_graph/training/losses.py`、`configs/experiments/SG-EXP-007a-event-weighted.yaml`、`scripts/sg_exp_007_screen.py`

**目的**：在 AdaptiveGraph 底座上测试二值事件加权损失，筛选最优 λ。

**实验设计**：

| λ | 权重公式 | 事件样本梯度占比（估计） |
|---|---|---|
| 0（对照） | weight = 1.0 | ~1% |
| 2 | weight = 1.0 + 2×trigger | ~6% |
| 3 | weight = 1.0 + 3×trigger | ~9% |
| 5 | weight = 1.0 + 5×trigger | ~13% |

**运行方式**：
```bash
python scripts/sg_exp_007_screen.py
```

或手动逐个运行：
```python
# 修改 config 中的 training.loss.lambda 字段后运行 train_experiment
```

**停止条件**：
- 稳定窗口 MAE 上升 >5%（相对 λ=0 基线）
- 事件窗口 MAE 改善 <5%
- 三种子配对 bootstrap p > 0.05

**预计耗时**：~1.5h GPU（4 个 λ × 3 种子，每种子约 7-8 分钟）

**输出**：`outputs/sg_exp_007/<tag>/experiment_report.json`

**文件**：
- 配置：`configs/experiments/SG-EXP-007a-event-weighted.yaml`
- 脚本：`scripts/sg_exp_007_screen.py`

---

## Step 3：SG-EXP-007b 强度加权对比

> 代码和配置就绪：`configs/experiments/SG-EXP-007b-event-intensity.yaml`

**目的**：使用 Step 2 筛选出的最优 λ，对比二值加权（binary）和强度加权（intensity）的效果。

**实验设计**：

| 模式 | 权重信号 | 归一化 |
|---|---|---|
| binary（007a 最优 λ） | rule_trigger（0/1） | 无需 |
| intensity（相同 λ） | visible_event_scores | per-batch max |

**预计耗时**：~0.5h GPU

**决策点**：
- intensity > binary → 强度加权写入论文作为主要方法
- intensity ≈ binary → 二值加权写入（更简单），强度加权作为讨论
- 两者都不如 λ=0 → 事件加权损失方案不可行，需重新考虑

**文件**：
- 配置：`configs/experiments/SG-EXP-007b-event-intensity.yaml`

---

## Step 4：P1 补充实验

### 4.1 事件修正 + 加权损失叠加

**目的**：验证架构修正（EventResidual）和优化修正（WeightedLoss）是否互补。

**实验设计**：

| 配置 | 底座 | 损失 | 修正器 |
|---|---|---|---|
| A | AdaptiveGraph | 标准 L1 | 无 |
| B | AdaptiveGraph | 加权 L1（007a 最优 λ） | 无 |
| C | AdaptiveGraph | 标准 L1 | EventResidual |
| D | AdaptiveGraph | 加权 L1（007a 最优 λ） | EventResidual |

**预计耗时**：~0.5h GPU（配置 D 需要先训练底座再冻入修正器）

**成功标准**：D > B 且 D > C → 两路径正交互补，论文贡献3更丰满。

---

### 4.2 Bootstrap 统计显著性检验

**目的**：确认事件窗口 MAE 的改善不是随机波动。

**方法**：
- 对三种子的预测文件做配对 bootstrap（10,000 次重采样）
- 报告事件窗口 MAE 改善的 95% CI 和单侧 p 值
- 如果 p > 0.05 → 改善不显著，需要在论文中诚实报告

**预计耗时**：~0.5h（纯分析，不需训练）

**关键文件**：
- 已有 `scripts/summarize_formal_results.py`（可能需要添加 bootstrap 逻辑）

---

### 4.3 自适应图可视化

**目的**：回答评委"自适应图学到了什么"的质问。

**产出**：
- 图 A：自适应邻接矩阵热力图 vs 三类固定关系矩阵（并排 4 列）
- 图 B：固定权重 α = sigmoid(fixed_weight) 随训练 epoch 的变化曲线
- 文字分析：自适应图新增/强化/弱化了哪些节点对？与事件共现关系是否重叠？

**预计耗时**：~1h（纯分析，从已训练模型的 state_dict 中提取嵌入矩阵和 α 值）

**关键文件**：
- 提取嵌入：`model.adaptive_embedding.weight`
- 提取 α：`model.fixed_weight`（sigmoid 后即为 α）

---

## Step 5：P2 锦上添花

### 5.1 损失函数选择讨论

**目的**：回应"为什么只用 L1？"的质疑。

**内容**（不需要额外实验，纯论述）：
- L1 vs MSE：充电负荷含大量零值和少量尖峰，L1 对异常值更鲁棒
- L1 vs Huber：Huber 在零附近的梯度行为与 L1 相似，但引入了额外超参数 δ
- 分位数损失：可提供预测区间，但 10 节点场景下分位数估计方差大
- 结论：L1 在当前场景下是最合理的默认选择

---

### 5.2 节点数敏感性理论分析

**目的**：回应"只有 10 个节点能推广吗？"的质疑。

**内容**（不需要额外实验，纯论述）：
- 充电站场景的节点数天然有限（通常 5-50 个充电位）
- 关系图构建规则（统计相关、事件共现、时间模式）不依赖节点数量
- top-k 稀疏化的 k 值应随节点数调整（如 k ≈ ⌊N/3⌋）
- 讨论扩展到 50/100 节点的预期行为

---

### 5.3 联合训练 vs 两阶段训练对比

**目的**：验证"先训练底座再冻结训练修正器"是否最优。

**方法**：
- 联合训练：底座和修正器一起训练（warmup 10 epochs 后解冻修正器）
- 与当前两阶段训练对比

**预计耗时**：~1h GPU

**仅在 Step 4.1（叠加实验）显示修正器有显著增益时才值得做**。

---

## 总时间估算

| 步骤 | 内容 | 预计耗时 |
|---|---|---|
| Step 0 | 确认夜跑结果 | 0.5h |
| Step 1 | P0 基线（AGCRN + MLP + Graph WaveNet） | 4.5h |
| Step 2 | SG-EXP-007a λ 筛选 | 1.5h GPU |
| Step 3 | SG-EXP-007b 强度加权 | 0.5h GPU |
| Step 4 | P1 补充（叠加+Bootstrap+可视化） | 2.0h |
| Step 5 | P2 锦上添花（讨论为主+1个可选实验） | 1.5h |
| **合计** | | **~10.5h** |

> 全部实验可在 **1-2 个工作日** 内完成（大部分时间在 GPU 训练，可并行）。

---

## 文件清单

### 已就绪（不需新建）

| 文件 | 作用 |
|---|---|
| `src/evcs_station_graph/training/losses.py` | WeightedL1Loss 实现 |
| `configs/experiments/SG-EXP-007a-event-weighted.yaml` | λ 筛选配置 |
| `configs/experiments/SG-EXP-007b-event-intensity.yaml` | 强度加权配置 |
| `scripts/sg_exp_007_screen.py` | 007 全自动筛选脚本 |

### 需要新建

| 文件 | 对应实验 |
|---|---|
| `configs/experiments/SG-EXP-008-agcrn-baseline.yaml` | P0-1 AGCRN |
| `src/evcs_station_graph/models/mlp.py`（或脚本内实现） | P0-2 MLP |
| `configs/experiments/SG-EXP-009-mlp-baseline.yaml` | P0-2 MLP |
| `configs/experiments/SG-EXP-010-graph-wavenet.yaml` | P0-3 Graph WaveNet |
| `scripts/supplementary_baselines.py` | P0 基线统一运行脚本 |
| `scripts/visualize_adaptive_graph.py` | P1-3 自适应图可视化 |
| `scripts/bootstrap_significance.py` | P1-2 Bootstrap 检验 |

---

## 论文回填对照

| 实验 | 回填位置 | 对应表图 |
|---|---|---|
| P0-1 AGCRN | §6.2 全局比较 | 表 6-2, 图 6-1 |
| P0-2 MLP | §6.3.1 TCN/MLP/图模型比较 | 表 6-2 |
| P0-3 Graph WaveNet | §6.2 全局比较 | 表 6-2, 图 6-1 |
| Step 2 λ 筛选 | §6.5.3 事件加权训练 | 表 6-5, 图 6-9 |
| Step 3 强度加权 | §6.5.3 事件加权训练 | 表 6-5 |
| Step 4.1 叠加 | §6.5.4 两种路径叠加 | 表 6-3 |
| Step 4.2 Bootstrap | §6.1.5 统计方法, §6.5 全节 | 表 6-3(p 值列) |
| Step 4.3 可视化 | §5.3.3 自适应图可解释性, §6.4.2 | 图 5-2, 图 6-4 |
