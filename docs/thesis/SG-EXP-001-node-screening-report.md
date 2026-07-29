# SG-EXP-001 节点覆盖率与跨期可用性筛选报告

## 口径

- 与 EXP-111 共用 `chronological_70_15_15` 时间切分。
- 与既有实验共用 15 min 节点代理负荷，不重新定义负荷。
- 主分析与敏感性节点清单仅依据训练集和验证集冻结。
- 测试集只生成 `test_evaluable` 标记，不参与门槛选择。

## 时间边界

- train: 2018-04-26T10:45:00 至 2020-09-08T02:15:00，83103 个预测起点。
- validation: 2020-09-08T02:30:00 至 2021-03-12T14:00:00，17807 个预测起点。
- test: 2021-03-12T14:15:00 至 2021-09-14T02:15:00，17809 个预测起点。

## 筛选结果

- 全部候选节点：55
- 主分析节点（训练集与验证集冻结）：10
- 主分析节点中测试期可评价：10
- 敏感性节点（训练集与验证集冻结）：15
- 敏感性节点中测试期可评价：14
- 主分析节点：CA-303, CA-304, CA-305, CA-307, CA-311, CA-315, CA-317, CA-321, CA-327, CA-489
- 敏感性节点：CA-212, CA-303, CA-304, CA-305, CA-307, CA-308, CA-309, CA-311, CA-315, CA-317, CA-321, CA-325, CA-327, CA-489, CA-492

## 主分析筛选失败原因

- `validation_access_events`：44 个节点
- `validation_active_month_ratio`：42 个节点
- `train_access_events`：7 个节点
- `train_active_month_ratio`：7 个节点
- `train_monthly_energy_cv`：2 个节点
- `train_nonzero_load_bins`：2 个节点

## 质量门禁

- `raw_and_timeslice_node_counts_match`：通过
- `stationID_and_EVSEID_are_exact_aliases`：通过
- `stationID_to_spaceID_is_one_to_one`：通过
- `complete_cartesian_rows_per_split`：通过
- `split_indices_are_contiguous`：通过
- `split_indices_do_not_overlap`：通过
- `split_time_order_is_chronological`：通过
- `primary_selection_respects_test_boundary`：通过
- `sensitivity_selection_respects_test_boundary`：通过

## 证据边界

该筛选仅证明节点具备进入后续站内图模型实验的最低数据条件，不证明节点标识一定对应独立物理充电桩，也不证明统计关系等同电气拓扑。
