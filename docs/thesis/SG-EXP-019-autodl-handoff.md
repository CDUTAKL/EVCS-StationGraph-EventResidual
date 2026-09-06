# SG-EXP-019 新协议训练适配与AutoDL交付

日期：2026-09-05。执行目标：local_mac仅CPU验证，用户手动租用的cloud_autodl执行正式实验。
当前无RTX4060/A6000可用，因此按用户要求直接准备AutoDL；未租用实例或发起付费训练。

## 实验目标与边界

检验新版事件时刻可见行为输入下，统计多关系结构相对纯时序/容量/自环对照的增量，
以及β、G、精炼、跨层拼接和单关系的作用。不能在实验前假设完整模型一定优于基线。
研究目标降级为事后会话能量代理；零入库延迟是假设，旧测试集非独立确认。
固定配置同预算比较不等于穷尽或等额超参搜索后的最优基线比较。

## 新增模块

| 路径 | 职责 |
|---|---|
| src/evcs_station_graph/eventtime/data.py | 固定SHA256数据加载、语义schema、严格分段与标签成熟检查、原点规则广播 |
| src/evcs_station_graph/eventtime/models.py | 保持原完整MRG计算、7项消融、自环、宽TCN、完整核心AGCRN |
| src/evcs_station_graph/eventtime/runner.py | 同协议训练、tuning选best、严格断点、预测与四格导出 |
| scripts/eventtime_experiment.py | check/smoke/benchmark/phase1/phase2/all/train/evaluate/summary |
| scripts/package_eventtime.py | 白名单打包、便携配置与来源、SHA256 |
| scripts/finalize_eventtime.py | 保存云端退出码、日志索引、结果归档及校验 |
| cloud/eventtime/run_autodl.sh + scripts/parallel_eventtime.py | 用户启动的4卡并行批量执行、异常退出留档、正式任务默认请求关机 |
| cloud/eventtime/README.md | 上传、验证、测速、两批训练、恢复、下载流程 |

完整MRG32714参数，原TCN16996，加宽TCN32674（45通道，差40参数，约0.122%），
完整核心AGCRN199912。AGCRN不是参数匹配对照；容量对照由宽TCN承担。
AGCRN保留节点自适应参数池和图、两层递归、K=2、embedding10、hidden32与多步卷积头。
参考作者公开实现：https://github.com/LeiBAI/AGCRN/tree/master/model 。
以公式独立实现并数值测试，不声称原论文性能复现。

## 运行合同

12配置×3种子=36正式拟合；阶段一15次，阶段二21次。4个独立worker分别绑定物理GPU，
共享完成队列保证某卡空闲后继续领任务；不使用DDP，不在单个任务内复制模型到4卡。
共同优化协议固定lr0.001/batch256/60epoch/patience8/AdamW/标准化L1/原单位tuning MAE；
梯度裁剪5，float32，确定性算法，num_workers0。
训练阶段仅访问train/tuning；训练完成才导出calibration/test。没有旧权重热启动。
checkpoint绑定配置、数据SHA、模型源码SHA、Torch版本与设备；每完整epoch原子保存。
配置和源码更改视作新实验，不允许静默沿用旧checkpoint。

## 本地核查记录

- Python3.12，本地Torch2.13.0 / NumPy2.3.5 / pandas2.2.3；CPU执行，无CUDA可用。
- 新增11项实验测试、既有数据可见性9项测试，共20项通过。
- 全仓库109项测试通过（2026-09-05本轮执行）。
- 原冻结产物和source_hashes全部匹配，未修改原图构建/模型源码或冻结数据。
- 完整MRG与原结构加载同一state_dict后输出逐位一致。
- 12配置均完成有限值前向/反向，所有可训练参数都有梯度。
- 节点自适应卷积与独立显式求和一致；自环对照无跨节点输入路径。
- 连续2epoch与中断1epoch再恢复的TCN参数逐位一致；漂移seed会被拒绝。
- 训练/导出边界、四格误差还原、哈希、独立目录包加载、篡改配置拒绝、故障归档测试通过。
- 本地小样本不是性能结果。用户报告单卡克隆实例在同为sm_89架构的4090上完成正式阶段；归档已回收到本地并完成逐运行复核。
- 远程预检曾确认4×RTX4090D；最终记录为phase2在单卡克隆实例完成36/36，不能把原4卡执行器计划写成实际执行方式。
- 4卡版本包：`outputs/releases/SG-EXP-019/evcs-eventtime-autodl-4gpu-v2.tar.gz`；旧单卡包保留，不再作为当前交付包。
- 最终包在独立临时目录以隔离Python入口完成12配置×2epoch CPU smoke和11项包内测试。
  本地核查记录和smoke产物保存在`outputs/releases/SG-EXP-019/`，不进入正式结果。

## 产物、存储与恢复

上传文件：outputs/releases/SG-EXP-019/evcs-eventtime-autodl-v1.tar.gz及其SHA256。
完整操作规范：cloud/eventtime/README.md。
正式结果：云端results/formal/<model>/seed-<seed>；manifest覆盖指标/预测/权重/配置/日志。
云端archives保存全结果归档、摘要和校验；每次启动单独cloud_logs索引。
归档来源为远端`/root/autodl-tmp/evcs-eventtime-4gpu-v3/archives/launch-phase2-1gpu.tar.gz`，本地回收路径为`outputs/recovered/SG-EXP-019/launch-phase2-1gpu.tar.gz`。远端和本地SHA256均为`fe6f7ebba559cbf275814e245239e548b70ab19248402a0d7129edf02b6ab141`；解压结果已通过36/36逐运行审计，状态提升为`reviewed`。远端摘要仍记为`scheduled_by_wrapper_not_confirmed`，不等同于控制台停机确认；应人工确认实例已停止计费。

## 后续论文核验门槛

1. 已完成36次运行的归档回收、SHA256校验和逐运行工件核验。
2. 全部预测按相同节点/原点/步长完成检查，主模型三种子四格和误差指标已复核。
3. 新协议当前未新增时间块显著性结论；若后续需要比较，仍应依据原点时间做配对日/周统计。
4. 若要超参搜索，预登记各模型相同预算、单独版本，只用tuning，不用校准/测试选择。
5. 新协议结果已可进入独立报告和正文限定段落；不写成跨协议显著改进或普遍获胜结论。
