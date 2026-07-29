# DeepSeek 正式实验执行交接

## 1. 角色边界

DeepSeek 仅作为正式实验执行方，负责环境核验、运行、故障原样记录和初步摘要。
不得修改数据划分、节点清单、模型结构、训练参数、随机种子、候选关系或评价口径。
遇到失败时不得自行删减实验、降低轮数、减少种子或改用测试集调参。

精细分析、论文结论、图表重绘与结果写回由 Codex 在完整产物回传后完成。

## 2. 已冻结的实验链

| 实验 | 内容 | 主要作用 |
|---|---|---|
| SG-EXP-002 | TCN 默认时间模型 | 给出不使用站内图关系的时间基准 |
| SG-EXP-003 | 固定站内交互图模型 | 检验训练集构建的固定关系是否有增益 |
| SG-EXP-004 | 自适应图模型 | 检验数据驱动的站内关系学习能力 |
| SG-EXP-005 | 事件残差修正模型 | 检验事件窗口内有界局部修正的收益与代价 |
| SG-EXP-006 | 消融、五类关系、敏感性、四格诊断 | 解释收益来源、适用边界和稳定性 |

正式实验统一使用随机种子 `2024、2025、2026`，历史窗口 96 步，预测 4 步，
时间分辨率 15 分钟，时间顺序训练/验证/测试划分不变。

## 3. 执行前准备

在 GPU 云实例中进入项目根目录。若尚无环境：

```bash
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e '.[dev]'
```

不得覆盖 `data/processed/SG-DATA-005-primary-tensor.npz`。如文件随项目完整同步，
应直接复用；脚本只会在缺失时按冻结配置重建。

## 4. 唯一正式运行命令

默认运行但不自动关机：

```bash
bash scripts/run_deepseek_formal_experiments.sh
```

确认运行在可安全自动关机的独占云实例后，使用：

```bash
AUTO_SHUTDOWN=1 bash scripts/run_deepseek_formal_experiments.sh
```

不允许手工逐个跳过实验。若进程异常退出，保留
`outputs/executor-runs/<时间标签>/formal_execution.log` 并停止操作。

## 5. DeepSeek 的简要分析格式

执行结束后只报告以下内容，不扩展成论文结论：

1. GPU、PyTorch、CUDA 是否正确识别；
2. 13 项自动化测试是否全部通过；
3. `formal_ready` 与 `validation_passed` 是否均为 `true`；
4. 三随机种子、预测键对齐、四格加权还原是否全部通过；
5. SG-EXP-002～005 在全局、事件窗口、稳定窗口的 MAE 排序；
6. SG-EXP-006 各范围最低 MAE 的变体名称；
7. 是否存在失败实验、缺失文件、NaN、样本量异常或种子标准差异常。

自动生成的初步材料包括：

- `automatic_result_summary.md`
- `automatic_result_summary.json`
- `artifact_validation_report.json`
- `cross_experiment_metrics.csv`
- `mechanism_summary.csv`

自动摘要只用于快速核验，不得据此直接宣称某模型全面最优。

## 6. 必须回传的完整产物

需要将以下两个目录原样回传，不接受只发截图或手工摘录：

1. `outputs/formal/SG-PIPELINE-002-006/<本次时间标签>/`
2. `outputs/executor-runs/<本次时间标签>/`

同时保留各子实验目录中三随机种子的模型、逐键预测、指标、四格结果和运行配置。
Codex 收到后将进一步完成：

- 逐预测键与样本量复核；
- 三种子均值、标准差和成组比较；
- 默认模型、固定图、自适应图与残差修正的公平比较；
- 五类关系、消融与敏感性的机制解释；
- 事件窗口收益与稳定窗口代价的边界分析；
- 论文可用表格、图片与保守结论。
