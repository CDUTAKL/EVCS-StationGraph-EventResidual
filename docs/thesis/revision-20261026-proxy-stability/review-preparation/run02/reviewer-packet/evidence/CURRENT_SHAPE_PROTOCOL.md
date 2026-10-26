# ACN同站电流形态复算协议

状态：`FROZEN_FOR_REPRODUCTION_AFTER_PRIOR_EXPLORATORY_RESULT`。冻结日期：2026-10-25。此协议固定已完成探索性分析的复算口径和图表生成，不是结果揭晓前的预注册，也不升级原分析的证据等级。

## 研究问题

在预定的Caltech节点会话样本中，按ACN实测电流时间序列得到的15 min归一化片份额，与会话总电量均匀分配形成的等片代理份额相差多少？结果只解释单会话内的形态差异。

## 冻结材料与完整性

输入为既有`DATA-024-CURRENT-PROBE`派生材料：

| 文件 | SHA-256 |
|---|---|
| `normalized_bin_shapes.csv` | `f3b71ed0e70a203815d824c273667d8d57ce940697311f73700f5401c8048de5` |
| `sample_metadata.json` | `1e69a6d4d92db35afcbab74e6cd0a716cf4074cc1641acfbd6de4c163cf58206` |
| `selection.json` | `2f551a78140fb95dad97dc2af0f43be450feec7215b1658babc1d5ea372989e3` |
| `sources.json` | `9afa3c585e2ff9c434ae3779b4f2776200b32b265d58f927819962e86d79513a` |
| `summary.json` | `c858b32619fe26ebe3e120a8cbdaed3944d50ec6bd25ccfffbf08ef67cba8991` |

原始会话记录和时序压缩文件均不进入Git；既有本地样本元数据保留源URL及单文件哈希。新生成的图、协议和复算记录不保留会话ID。

## 样本和变量

- 选择规则沿用原冻结清单：每个论文固定Caltech节点取2018年5月首条按时间排序的正电量会话，共10条；保持原纳入结果，不重新抽样。8条已有有效电流形态，2条按原可得性/质量门禁未进入形态统计。
- 实测量为`Charging Current (A)`；按已登记脚本作分段积分并归一化到各会话总电流积分，得到每片`normalized_current_fraction`。
- 对照量为各会话目标片等份，`uniform_proxy_fraction=1/B`，其中B为该会话覆盖的片数。
- 逐会话总变差距离：`TV = 0.5 × Σ_b |current_fraction_b − uniform_fraction_b|`。
- 峰值片比：`max(current_fraction_b) / (1/B)`。

## 质量门禁与统计

沿用已保存分析的规则：时间严格递增、电流非负且有限、首末覆盖偏差不超过60 s、最大采样间隔不超过60 s、电流积分为正。不得因图形或统计结果放宽门禁、增加或替换会话。报告八个单会话点、范围与中位数；不做总体显著性检验或置信区间，不将会话作为随机抽样总体。

## 复算、图表和禁止解释

原始会话行和分片电流数据留在Git之外。首次复算已对五个冻结派生源文件逐项核验SHA-256、十条选定样本和八条有效样本，并将无会话标识的逐节点TV距离、峰值片比及输入哈希写入`acn-current-shape-replay.json`。图5-9通过`python3 scripts/figures/fig5_9_acn_current_shape.py`从该去标识冻结汇总生成SVG/PDF/1200 dpi PNG；脚本校验样本数、非代表性标记、实测量边界、逐节点值和汇总统计。该入口复现图件，不重新读取原始会话或重新估计统计量。

该分析不使用任何模型预测，不验证`kWh/15 min`实测误差、不估计功率/电量偏差、不评价跨时期或新节点表现，也不测算运行收益。缺电压和功率意味着不能把电流积分称为实测能量。模型结果仍按第3章冻结测试协议的代理标签解释。
