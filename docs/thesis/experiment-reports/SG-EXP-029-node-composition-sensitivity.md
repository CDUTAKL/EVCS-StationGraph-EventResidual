# SG-EXP-029：节点门控增量的节点构成敏感性复核

## 分析性质

本分析复用SG-EXP-027（Caltech事件时刻协议）及SG-EXP-028（JPL重拟合协议）已有测试预测键，不训练模型、不新增测试时期或场站。分析问题是：总体节点门控MAE增量是否完全由某一个被评价节点驱动？该分析在已有总体结果和测试集已查看后制定，属于事后描述性敏感性复核，不是预登记确认性检验。

## 材料与复核范围

| 材料 | 位置/标识 | 核验范围 |
|---|---|---|
| Caltech冻结张量 | `outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz`；SHA-256 `f663b510c75e203c8150f57c3765645f92b9a941e0745227c6ea078008a0dc8f` | 测试原点、节点顺序、真值、事件标签、规则掩码及目标时间 |
| SG-EXP-027逐键预测 | `outputs/experiments/SG-EXP-027/recovered/formal/{mrg_full,mrg_shared_gate}/seed-{2024,2025,2026}/predictions_test.npz` | 6份逐运行manifest完整校验；每份708,560键 |
| JPL冻结张量 | `outputs/visibility/SG-DATA-007-jpl-eventtime-v1/dataset.npz`；SHA-256 `1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af` | 测试原点、节点顺序、真值、事件标签、规则掩码及目标时间 |
| SG-EXP-028逐键预测 | 本机交接归档解包目录下4配置×3种子正式运行 | 12份逐运行manifest校验；每份632,640键；外层归档SHA-256 `50e7beb581c7cd4e3099fa0661d5a1cf3c1f79935516739eae693ba0234d4966` |

所有模型和种子的测试原点、节点顺序、真值、事件/规则掩码及时间键均与对应冻结张量一致，预测值有限。模型间预测键完全相同。SG-EXP-027另由既有审计完整检查tuning、calibration、test分区、运行配置、检查点、训练曲线及指标；SG-EXP-028本项只复核测试预测键与运行manifest，不替代完整训练合同审计。

## 分析定义

先在每个预测键上计算绝对误差，再对同一模型的三个固定训练种子逐键取平均。整体MAE按保留节点、原点和4个预测步的全部键计算。每次剔除一个节点后，用其余节点上的共同预测键重算两种门控的整体MAE。相对降幅定义为：

`100 × (MAE_shared_gate − MAE_node_gate) / MAE_shared_gate`。

逐键预测与程序均留存在报告所列位置；完整JSON/CSV结果见`content-review-20261009/gate-node-composition-audit-final/`。

## 结果

| 协议 | 全节点节点级门控降幅 | 逐节点剔除的降幅范围 | 留一方向 |
|---|---:|---:|---|
| SG-EXP-027 Caltech事件时刻协议（10节点） | 2.6853% | 2.2545%～2.8884% | 10/10为正 |
| SG-EXP-028 JPL重拟合协议（10节点） | 2.7104% | 2.1266%～3.2018% | 10/10为正 |

按节点的完整MAE、共享门控MAE和留一降幅见`gate-node-composition-audit/leave_one_node_out.csv`。该结果支持的表述是：在这两个既有测试集上，观察到的总体点估计不因删除任一单节点而反向。它不说明各节点都分别改善，也不证明新时期或新场站泛化。

## 统计边界与论文使用

- 留一百分比为点估计；本补充未为20个留一子集另行计算区间或校正多重比较。
- 所有逐键均来自已经参与既有报告的固定历史测试期，节点间预测键相关；节点剔除不是新增独立抽样。
- 本分析不替代SG-EXP-027七日块区间，也不改变SG-EXP-028预登记的三项整体MAE比较及其Bonferroni区间。
- 两个协议的绝对MAE不合并比较；结论限于各自协议内部的节点组成敏感性。
- 结果写入正文3.7.1及结论，仅补充“未见单节点支配总体点估计”的限定表述；不使用“普遍稳健”“独立验证”或“显著”描述留一结果。

## 复算

```bash
PYTHONPATH=src .venv/bin/python scripts/audit_gate_node_composition.py \
  --jpl-root /Users/xushuyuan/Documents/Codex/2026-10-05/sg-exp-028-jpl/outputs/recovered/SG-EXP-028/extracted \
  --out docs/thesis/content-review-20261009/gate-node-composition-audit-final
```

程序验证预测文件和数据哈希，执行键对齐门禁，独立复算整体、分层、逐步和逐节点指标及四格加权还原，再生成留一结果。脚本SHA-256：`64e74da074069f3c4b362aa3363390559ea79111701370ee9ca08b560d00716f`。原始模型训练产物未修改。
