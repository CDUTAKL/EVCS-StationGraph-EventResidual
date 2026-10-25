# SG-EXP-031：JPL同容量关系替换对照

日期2026-10-15。状态：训练完成、归档回收并通过结果审计；可形成限定于本协议和预算的补充结论。该实验使用已查看的JPL固定测试期，属于事后补充验证，不是盲测确认。

## 设计与合同检查

依据 `training-design-20261015.md`，四配置full/load_to_self/event_to_self/pattern_to_self，各2024/2025/2026三个种子。从头训练，同种子非邻接初始参数SHA-256一致，32714个可训练参数，三槽位均保留。只将指定邻接换为自环，不删除参数、不屏蔽梯度。

本地CPU和服务器CUDA各完成12组合同检查：冻结JPL数据哈希和时序成熟度、关系槽位替换、未替换邻接一致、参数数量、初始参数配对、六组关系变换梯度有限且非零、探针后参数未改变。探针只有小批train的前向/反向检查，无优化器更新。首次检查的输出目录创建错误已修复并重跑。

服务器CUDA检查产物已回收至 `outputs/experiments/SG-EXP-031/cuda-contract-check.json`。环境PyTorch2.8.0+cu128、CUDA12.8、NumPy2.3.2、RTX4090 D，与旧JPL软件环境一致。正式上限60轮、耐心8、batch256、AdamW0.001/weight_decay0.0001，完整tuning原单位MAE选模，FP32确定性计算、关闭TF32。

## 源码与入口

实现入口 `scripts/jpl_relation_controls.py`，复用原runner，仅在本CLI进程内通过作用域工厂适配注入邻接替换，退出时恢复。旧runner、模型源码和旧上传包未修改。冻结包67项manifest在最终回收时全部核验，入口和设计哈希写入每次训练合同。

本地冻结包：`outputs/experiments/SG-EXP-031/bundle/`。
传输压缩包SHA-256：`5361c41a147592d0ea6bb14cd2282637f4906015a0dc76f4563d2b0e388b4d8a`，远端一致。
另保存原Git HEAD、已跟踪源码差异和每文件哈希；源码有未提交内容，不将HEAD单独当作完整版本认证。

远端包：`ssh://root@connect.westc.seetacloud.com:24376/root/autodl-tmp/SG-EXP-031`。
日志：`/root/autodl-tmp/SG-EXP-031/train.log`。
正式产物：`/root/autodl-tmp/SG-EXP-031/results/SG-EXP-031/jpl/<variant>/seed-<seed>/`。
启动包装脚本：`scripts/run_jpl_relation_controls.sh`，初始PID3324，仅作为本次进程标识，不作持久身份。

## 可执行命令

在新冻结包根目录运行：

```sh
/root/miniconda3/bin/python scripts/jpl_relation_controls.py check --device cuda --out results/SG-EXP-031
/root/miniconda3/bin/python scripts/jpl_relation_controls.py all --device cuda --out results/SG-EXP-031
```

运行入口另有train/evaluate，train可指定--variant和--seed；已训练目录须加--resume，contract不匹配即拒绝恢复。正式训练开始后不能覆盖check记录。evaluate会先要求全部12次训练完成、合同一致，冻结best/last哈希后统一导出tuning/calibration/test；不存在按先看到test胜负筛配置的路径。

## 结果回收与审核

- 远端汇总状态为`completed_unreviewed`，退出码0，12/12次正式训练结束时间为2026-10-14 19:01:52 UTC。测试预测已导出，checkpoint-lock包含12组best/last哈希。
- 远端归档SHA-256为`4eb436fbf30823d4df9b3e1be9f34652f849bdf7a130ce1c4229d9b2964f8c5f`；本地归档哈希一致，tar可读，内层173项SHA-256全部通过。冻结输入包67项manifest、数据、入口脚本、训练计划、模型/runner源码和原始关系图哈希均与运行合同相符。
- 合同状态PASS；每个配置均为32,714参数。同一种子下四配置的初始非图参数哈希一致。三种子共用15,816个预测原点、632,640个预测键；标签、节点、事件标记、触发标记及时间键逐数组完全一致。全部预测有限，起点和节点编号无重复。
- 从逐键预测独立复算MAE、RMSE、事件/非事件MAE、逐目标片、逐节点误差，均与`metrics.json`匹配；独立四格重构通过1e-9容差。最佳轮次与训练日志中tuning原单位MAE最低轮次一致，12次运行均未达到60轮上限。
- 10,000次配对七日块bootstrap以三个种子逐键绝对误差均值为基础；固定JPL测试期划分为24个洛杉矶本地周块。三项全局MAE比较使用Bonferroni 98.333%同时区间。完整逐次结果、块级结果、源哈希和解释边界见[SG-EXP-031结果审计](../../../outputs/analysis/SG-EXP-031-audit-20261015/README.md)及[审计JSON](../../../outputs/analysis/SG-EXP-031-audit-20261015/audit.json)。

## 主要结果与可写结论

| 自环替换配置 | Full相对替换配置的全局MAE变化 | Bonferroni 98.333%周块区间 | 三种子方向 | 结论 |
|---|---:|---:|---|---|
| `load_to_self` | 低0.001501 kWh/15 min（1.82%） | [0.000048, 0.002689] | 3/3更优 | 支持负荷关系在本JPL协议、架构和预算下的条件增量 |
| `event_to_self` | 低0.000120（0.15%） | [-0.000432, 0.000728] | 2/3更优 | 同时区间跨零；不支持事件关系具有独立正向全局MAE增量 |
| `pattern_to_self` | 低0.001252（1.52%） | [0.000167, 0.002275] | 3/3更优 | 支持模式关系在本JPL协议、架构和预算下的条件增量 |

因此，本实验只支持**负荷关系和模式关系相对自环替代的条件增量**；不能再写“三类关系均有独立增益”或“三类关系均不可替代”。事件组为描述性结果：将事件关系图替换为自环后，事件MAE平均降低0.005142；将模式关系图替换为自环后，事件MAE平均降低0.003677，说明全局MAE改善不等于事件片段改善。JPL测试零目标键占72.75%，与Caltech事件时刻协议的87.25%不同，需分协议报告。

以上区间反映已查看JPL固定测试期的时间块变异；它不估计场站抽样不确定性，也不包含完整的种子抽样不确定性。该结果不证明跨站点普遍性、未来期泛化、真实功率预测或现场运行收益。

## AutoDL状态

本地归档已回收并完成哈希与内容核验。远端summary中的`shutdown_status`仍为`pending_local_recovery`；AutoDL保持在线，**本次没有下达关机命令**，遵循用户“AutoDL是远程服务器，我不会关闭它”的说明。远端guardian状态文件仍为`armed`，但本轮未执行关机；不要据此声称AutoDL已自动关闭。

2026-10-15后续状态：本节上述在线/未关机记录对应031结束时。此后用户授权SG-EXP-032完成训练，结果回收核验后实例已关机；以SG-EXP-032/shutdown-evidence.json为当前控制台证据。
