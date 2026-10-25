# 检查点证据包的数据与结果字段

本轮复核三个预测协议、四组实验，仅执行现有权重的测试集前向。该字典供本地交接解析；完整字段顺序以包内冻结张量及源码为准。

## 目录与身份

| 组件 | 数据 | 正式运行范围 | 权重 | 归档预测 | 论文定位 |
|---|---|---|---|---|---|
| `legacy` | SG-DATA-005 | SG-EXP-002/003/004，各3种子 | `model.pt`的`model_state` | `predictions.csv.gz` | 表3-4的TCN、MRG-GCN、AdaptiveGraph三行；不覆盖该表全部模型 |
| `sg019` | SG-DATA-006 | 12模型×3种子 | `best.pt`的`model` | `predictions_test.npz` | 表3-2 |
| `sg027` | SG-DATA-006 | 节点门控/共享门控×3种子 | `best.pt`的`model` | `predictions_test.npz` | 表3-9 |
| `sg028` | SG-DATA-007 | MRG/TCN-wide/完整AGCRN/共享门控×3种子 | `best.pt`的`model` | `predictions_test.npz` | 表3-3 |

种子固定为2024、2025、2026。测试键为`(split, origin_index, horizon, node_id)`，不是将相同目标时刻重复预测合并后的唯一目标数。三个协议的输入权限、原点和节点标识不同，不能混合汇总误差。

## 张量与键

- 旧回溯协议输入包含代理负荷及派生字段；事件时刻协议输入为接入、离站、活跃计数与四个当地日历编码。目标均为事后重构的kWh/15 min代理能量，不是实测功率。
- 测试真值与预测形状均为`[origin, 4, 10]`；`horizon`为1—4，按论文定义对应发布后四个15 min目标片。
- `origins`/`origin_index`是冻结全时间轴的整数索引。NPZ的`target_timestamps_ns`为`[origin, 4]`，UTC纳秒；`origin_cutoff_ns`为片末发布时刻。旧CSV分别保存`forecast_origin`、`target_index`、`target_time`。
- `node_ids`保存输出轴顺序；不得按字符串排序后直接与原数组比较。旧CSV另外保存`node_index`用于恢复原顺序。
- `target_event`是事后评价标签；`rule_trigger`是冻结规则触发。严格协议两者形状为`[origin, 4, 10]`；旧推理返回规则形状`[origin, 10]`，评价时沿目标片轴重复，不以标签替换规则。
- `feature_mean/std`与`target_mean/std`为冻结缩放统计；本轮读取原统计，不在测试集重新估计。旧张量整体的历史上游统计限制仍按正文2.1.1节解释。
- 严格协议张量还保存各段原点和标签成熟时刻；原加载器核对完整窗口留段及目标成熟门禁。

## 复核结果

`legacy.json`、`sg019.json`、`sg027.json`、`sg028.json`保存逐运行记录；`summary.json`汇总并保留失败。关键字段为：

| 字段 | 含义 |
|---|---|
| `status` | 所列检查全部通过才为PASS；未通过不可计入覆盖成功数 |
| `n_test_keys` | 完整测试预测条数：旧712,360；Caltech事件时刻708,560；JPL632,640 |
| `checkpoint_sha256` | 实际读取的现有检查点身份 |
| `archived_prediction_sha256` / `prediction_export_sha256` | 对照的原测试导出身份 |
| `checks` | 键、真值、标签、规则、时间戳、来源与误差容差核验项 |
| `max_prediction_abs_diff` | 当前CPU前向与归档GPU输出的逐键最大绝对差 |
| `mae_abs_diff` | 复算与原报告的全局MAE绝对差 |
| `max_metric_abs_diff` | 六类已核对指标中的最大绝对差，包括逐目标片/节点向量 |
| `recovered_levels` / `original_config_levels` | 旧协议检查点权重形状恢复出的层数与原配置记录，不修改历史配置 |
| `source_authenticity` | 旧源码仅为复算快照，不认证训练时版本 |

判定容差预先设定为预测与指标各5×10⁻⁶；旧CSV真值额外容许1×10⁻⁷的文本序列化差。三个严格组件核验原bundle manifest、运行manifest或JPL测试前检查点锁；旧组件的训练时`git_commit=null`作为缺口保留。

本轮只对MAE表格均值和样本标准差进行打印精度核验；每运行同时复核MAE、RMSE、事件/稳定MAE、逐目标片MAE和逐节点MAE。没有重算全文所有Bootstrap、TE置换或共形区间，也没有从原始会话重新生成数据。
