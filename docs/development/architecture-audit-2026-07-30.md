# 图架构审核报告（阶段 B 前验收）

- **审核日期**：2026-07-30
- **审核方式**：本地 CPU、合成小张量（[scripts/audit_architecture_cpu.py](../../scripts/audit_architecture_cpu.py)），**不加载真实数据工件、不读取测试集、不进行训练**
- **代码状态**：分支 `feat/multi-relation-gated-gcn`，提交 `deeb053`（含 `967e9ab`）
- **审核输入尺寸**：与正式实验配置一致 —— N=10 节点、F=7 特征、T=96 历史步、H=4 预测步、D=32 隐维、levels=3

## 审核中发现的缺陷与修复记录

| # | 缺陷 | 严重性 | 修复 | 回归测试 |
|---|------|--------|------|----------|
| 1 | `relation_dropout` 仅写入配置、未进入模型计算，0.0/0.2/0.4 敏感性实验会得到相同模型 | 实验无效 | GCN β 融合与残差邻居聚合两处实现训练期关系屏蔽，factory 全链路传递 | 5 条（967e9ab） |
| 2 | `smoothing` 残留于 4 个配置与 engine 传参，但关系构建已不再使用 | 参数误解 | 全量删除（配置/传参/函数签名/conftest） | 31/31 通过 |
| 3 | 自适应图 `fill_diagonal_`/`scatter_` in-place 操作：backward 崩溃 + 嵌入梯度流截断 | 训练崩溃/自适应图失效 | `masked_fill` + 非 in-place `scatter` | `test_adaptive_graph_backward_reaches_embeddings` |
| 4 | `GroupNorm(1,C)` 跨 (C×T) 归一化：TCN 实测感受野 96 步（理论 15），中间时间步混入未来统计量 | 因果性/文档失真 | 逐时间步 LayerNorm | `test_tcn_receptive_field_matches_theory`、`test_tcn_strictly_causal_per_timestep` |
| 5 | 图模型 `tcn.head` 死参数（132 个）：无梯度、虚增可训练参数统计 | 清洁度 | 构造后删除 | `test_graph_model_has_no_dead_tcn_head` |

## 1. 各模型真实张量维度流（实测）

输入 `x: [2, 96, 10, 7]`（B=2 审核批次）。

**TCN（SG-EXP-002）**

```
x[2,96,10,7] → permute+reshape [20,7,96] → 3×因果卷积块 → 取末步 [20,32]
→ reshape h[2,10,32] → head → [2,10,4] → permute → 预测 [2,4,10]
```

**StaticGraphForecast（SG-EXP-003）**——TCN → GCN1 → 图特征MLP精炼 → GCN2 → 跨层融合 → 预测头

```
h0 = tcn.encode(x)                [2,10,32]
h1 = gcn1(h0; Â_load,Â_event,Â_pattern, β₁)   [2,10,32]   （3 类关系，3×[10,10]）
h1' = h1 + graph_mlp_refine(h1)   [2,10,32]
h2 = gcn2(h1'; 同上, β₂)          [2,10,32]   （独立 β₂、W_r）
fused = skip_fusion([h0‖h1‖h2])   [2,10,96] → [2,10,32] → LayerNorm+GELU
预测 = head(fused)                [2,10,4] → [2,4,10]
```

**AdaptiveGraphForecast（SG-EXP-004）**：同上，消息传递关系数 3→**4**（追加自适应邻接 `A_adp[10,10]`，top-k 排除自身后加自环）；`α = sigmoid(fixed_weight) ≈ 0.574`（初始 fixed_weight=0.3）。

**EventResidualCorrection（SG-EXP-005，三种基模型逐模块实测一致）**

```
base_latent = base.encode(x)      [2,10,32]     （冻结，no_grad）
base_pred = base.forecast(latent) [2,4,10]
M = mean_r(Â_r · base_latent)     [2,10,32]     （关系 dropout 作用点）
E = x[:, -1, :, 事件特征]         [2,10,4]      （access/departure/active/jump_flag）
correction_input = [H‖M-H‖E]      [2,10,68]
residual = bound·tanh(MLP(...))   [2,4,10]
最终 = base_pred + gate ⊙ residual [2,4,10]
```

## 2. 参数量（实测，正式配置）

| 模型 | 总参数量 | 可训练 | 说明 |
|------|---------:|-------:|------|
| TCN（002） | 7,492 | 7,492 | network 7,360 + head 132 |
| StaticGraph（003） | 23,210 | 23,210 | tcn 7,360 + gcn1 5,216 + gcn2 5,216 + refine 2,112 + skip 3,104+64 + head 132 + β 3+3 |
| AdaptiveGraph（004） | 25,501 | 25,501 | 上同（gcn 各 6,240，4 关系）+ 嵌入 240 + fixed_weight 1 |
| EventResidual（base=temporal） | 9,832 | **2,340** | base 冻结（7,492），仅 corrector 可训练 |
| EventResidual（base=static_graph） | 25,550 | **2,340** | 同上 |
| EventResidual（base=adaptive_graph） | 27,841 | **2,340** | 同上 |

## 3. TCN 实际感受野（梯度法实测）

| levels | 理论 RF | 实测 RF | 界外梯度严格为零 | 结论 |
|--------|--------:|--------:|:---:|:---|
| 3 | 15 | **15** | ✓ | 匹配（修复后） |
| 5 | 63 | **63** | ✓ | 匹配 |
| 6 | 127 | 96（=窗口全长） | ✓ | 匹配（RF 超过 96 步窗口） |

修复前实测为 96（GroupNorm 时间耦合），与文档公式矛盾；逐时间步 LayerNorm 修复后理论与实测一致。当前正式配置 levels=3 的 TCN 看到的历史长度为 **15 步 = 3.75 小时**——若阶段 B 希望覆盖完整 96 步窗口，levels=6 是候选（这正是预筛选的搜索维度之一）。

## 4. 三种残差模型的基础模型加载测试

| base_model_type | 检查点参数逐位一致 | base 全部冻结 | corrector 可训练 | 门全关输出 = 独立 base |
|---|:---:|:---:|:---:|:---:|
| temporal | ✓ | ✓ | ✓ | ✓（max diff = 0） |
| static_graph | ✓ | ✓ | ✓ | ✓（max diff = 3.0e-7） |
| adaptive_graph | ✓ | ✓ | ✓ | ✓（max diff = 2.4e-7） |

1e-7 量级差异为 einsum 多线程归约顺序的浮点现象（验收口径 rtol=1e-5）；`checkpoint → factory → load(strict=True) → 冻结 → 门控` 全链路三种基模型均通过。

## 5. 小样本前向 / 反向 / 梯度 / NaN 检查

六种模型（TCN、Static、Adaptive、EventResidual×3）全部：

- 前向输出有限（无 NaN/Inf）✓
- L1 损失有限、backward 无异常 ✓
- **全部可训练参数梯度存在且有限** ✓
- 关键可解释参数 `relation_weights_gcn1/gcn2`、`fixed_weight` 梯度**非零**（可学习关系权重真实参与训练）✓
- EventResidual 冻结 base 参数 `requires_grad=False`、无梯度 ✓

## 6. relation_dropout 行为验证

| 检查项 | 结果 |
|---|---|
| 训练模式 16 次前向不同输出种数 | 15 种（随机性生效） |
| eval 模式两次前向 | 逐位一致（推理确定） |
| 掩码保留率（p=0.2，2000 次采样） | [0.859, 0.863, 0.872] ≈ 期望 0.867 |
| 2000 次采样中最少保留关系数 | 1（"至少保留一类"保护恒成立） |

掩码保留率期望公式为 `(1-p) + p/R`（零同步实现：独立 Bernoulli 叠加无条件强制保留一位），p=0.2、R=3 时为 0.8667，实测吻合。

## 7. 自动化测试与提交

- **31/31 全部通过**（连续三次运行无抖动）
- 提交序列（`feat/multi-relation-gated-gcn`，未合并 main）：
  - `967e9ab` relation_dropout 真实生效 + smoothing 清理（27/27）
  - `deeb053` 审核发现的三处缺陷修复 + 审核脚本（31/31）
- 此前已验证项（0c74b79 等）：两跳传播、自适应 top-k 排除自身、单关系/全关系配置子集、事件特征名查找、graph_mlp_refine 非 TCN、事件窗口因果性

## 结论

第八节验收 10 项全部完成。架构当前状态可进入阶段 B 超参数预筛选（待您批准后再同步服务器执行）。

**阶段 B 前请注意**：TCN levels=3 的实测感受野仅 3.75 小时，不足 24 小时窗口；levels∈{5, 6} 应纳入预筛选搜索范围（与原计划一致）。
