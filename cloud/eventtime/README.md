# SG-EXP-019 可直接上传实验包

本包针对低配Mac准备、AutoDL四卡并行执行。未启动云实例或产生训练费用。
本地验证只证明代码可运行，**不代表正式实验完成、性能达标或论文可得85分**。

## 1. 上传与环境

将整个 `evcs-eventtime-autodl-v1.tar.gz` 上传到你有权限使用的AutoDL实例数据盘，
建议在 `/root/autodl-tmp` 下解压。解压到一个新目录，不覆盖已有结果。

```bash
tar -xzf evcs-eventtime-autodl-v1.tar.gz
cd evcs-eventtime
${PYTHON_BIN:-/root/miniconda3/bin/python} --version
${PYTHON_BIN:-/root/miniconda3/bin/python} -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
${PYTHON_BIN:-/root/miniconda3/bin/python} -m pip install -r cloud/eventtime/requirements.txt
${PYTHON_BIN:-/root/miniconda3/bin/python} scripts/eventtime_experiment.py check
${PYTHON_BIN:-/root/miniconda3/bin/python} -m pytest tests/test_eventtime_experiment.py
```

使用 Python 3.11/3.12、带CUDA的PyTorch 2.3及以上环境；Mac测试环境在交付验证记录中。
不要把本地 `.venv` 上传，不要在云端装Mac版Torch。本包不自动安装或替换Torch。
若CUDA检查为False，先处理镜像环境，不要直接开正式任务。
所有正式运行在同一镜像/同一GPU型号上进行；环境变更会阻止旧断点续训。
数据约3MB压缩文件，解压加载后内存需求更大；实际GPU显存和耗时以测速为准。
预留结果盘空间，尤其每次云端启动结束都会另外归档一次已有results。

## 2. 先验证、测速，不要直接开36次

```bash
bash cloud/eventtime/run_autodl.sh smoke
bash cloud/eventtime/run_autodl.sh benchmark --model mrg_full
bash cloud/eventtime/run_autodl.sh benchmark --model agcrn_full
```

smoke遍历12配置，每配置16训练原点、8评价原点、2轮，输出明确标记为非科学证据。
benchmark使用实际batch=256、2560训练原点/512调参原点、2轮；**不是完整训练**。
根据第2轮时间分别估计各模型每轮耗时，另考虑完整调参集和导出时间。
smoke/benchmark也会按4卡并行启动，每个子进程通过`CUDA_VISIBLE_DEVICES`绑定到一张物理卡；
一个GPU槽位只同时运行一个任务。
不要用Mac耗时估计CUDA费用；本包没有编造云端耗时、显存或预算。
check/smoke/benchmark默认不自动关机，执行完请手动停机，或显式设置 `AUTO_SHUTDOWN=1`。
相同输出不能覆盖；重复验证用 `--resume`。裸Python入口允许新的 `--out` 目录，但需自行归档和停机；云封装仅管理默认results目录。

## 3. 正式运行（两批36次）

| 批次 | 配置 | 种子 |
|---|---|---|
| phase1 | 完整MRG、TCN、参数量匹配加宽TCN、自环MRG、完整核心AGCRN | 2024/2025/2026，各3次，共15次 |
| phase2 | 等β、固定G=0.5、无精炼、无跨层拼接、仅负荷/仅行为/仅轮廓 | 各3次，共21次 |

在 `tmux` 等持久会话内启动；断开SSH不应杀掉任务。当前4卡实例必须使用并行封装，
不要再调用旧的`eventtime_experiment.py phase1/phase2/all`顺序入口。

```bash
bash cloud/eventtime/run_autodl.sh phase1
# 第二批需确认实例已重新开机、环境一致
bash cloud/eventtime/run_autodl.sh phase2
```

**这两个正式命令默认在结束或报错后保存、归档并请求关机。** 不在共享主机运行。
如需连续跑两批，使用 `bash cloud/eventtime/run_autodl.sh all`。
默认GPU绑定为`0,1,2,3`；仅当AutoDL的GPU编号确实不同才设置，例如：
`GPU_IDS=0,1,2,3 bash cloud/eventtime/run_autodl.sh phase1`。
调度器采用共享完成队列：某张卡完成一个配置后，该卡立即领取下一个配置，不等待其他卡。
只有明确需要保持实例运行时使用 `AUTO_SHUTDOWN=0`。
不要只运行裸Python正式命令后忘记关机；裸入口本身不负责停止计费。
断点恢复示例：`bash cloud/eventtime/run_autodl.sh phase1 --resume`。
恢复时每个任务独立检查自己的`last.pt`；已有断点的任务续跑，尚未启动的任务正常首次启动。
恢复按完整epoch进行，最多重跑被中断的一个epoch；代码、数据、配置、Torch或设备变更会拒绝恢复。
若出错发生在第一个完整epoch保存之前，该目录没有可恢复断点：将该失败run目录重命名保存，再重新运行，不删除故障证据。
没有自动缩小batch、跳过失败模型或切CPU的暗中降级。
若OOM，先停正式计划，统一修订所有配置的batch和协议版本、重新测速，再开始新一轮，不能混用预算。

关机使用AutoDL官方给出的 `/usr/bin/shutdown`，不包含账号API、密码或购买操作。
**请求关机不等于确认停机**，务必到AutoDL控制台确认；失败时手动关机。
官方说明：https://api.autodl.com/docs/save_money/

## 4. 已冻结的比较口径

- 输入 `[B,96,10,7]`：接入、离站、活跃计数及当地时/星期sin/cos；不含事后负荷历史。
- 目标 `[B,4,10]`：事后等时间格会话能量代理（kWh/15min），不是真实电表功率。
- 事件时刻严格早于预测截止时刻；零入库延迟只是假设，不是实测部署保证。
- 原点 train83099 / tuning8803 / calibration8805 / test17714。
- 96步输入和4步目标都在各自分段内，标签成熟检查通过；训练期scaler和图已经固定。
- 节点固定旧10节点研究对象；旧测试集曾被查看，新实验仅为回顾性核验，非独立确认。
- 同一AdamW、lr=0.001、weight_decay=0.0001、batch256、最多60轮、patience8、标准化L1、梯度裁剪5。
- 只以tuning的原单位MAE选best；calibration不早停/调参；test不选择模型、超参或种子。
- 这是**同数据/同预算的固定配置比较**，不是等额超参搜索后的最优基线比较。
  尚未执行额外超参搜索；如要扩展，须先预登记各模型相同搜索预算，只使用tuning，另建版本。
- 完整MRG严格保持原六层TCN+两层门控传播+残差精炼+原始H0/H1/H2拼接的计算。
- 固定G=0.5保持原外层残差；无精炼使用H1直接进入第二层；无skip只将H2经D→D投影再进入原预测头。
- 单关系只保留对应一张冻结图及消息分支；自环保留三分支架构，把三图都换成I；等β冻结两层logits为0。
- TCN宽度仅按参数量匹配，绝不根据测试误差选宽度；`check`显示实际宽度及各配置参数数。
- AGCRN保留DAGG、NAPL、两层图递归单元、Chebyshev阶数2、embedding10、hidden32、多步卷积头。
  未沿用旧简化AGCRN。重写参考作者公式，新增单元数值测试；任务输入/输出、初始化和优化器适配当前协议，
  不声称复现原论文交通数据成绩。参考：https://github.com/LeiBAI/AGCRN/tree/master/model
- 所有模型float32且启用确定性算法；不默认AMP或torch.compile，避免不同实现悄然影响口径。

## 5. 结果下载与后续核验

```bash
${PYTHON_BIN:-/root/miniconda3/bin/python} scripts/eventtime_experiment.py summary
```

输出位于 `results/formal/<model>/seed-<seed>/`：

- `config_resolved.json`、环境版本、训练日志；
- `best.pt`、含优化器/RNG/早停状态的 `last.pt`；
- tuning/calibration/test三个 `predictions_*.npz`：原单位真值/预测、原点、目标时间、节点、双事件掩码；
- `metrics.json`：全局、事件/稳定、节点、步长、四格MAE/样本量/绝对误差贡献；四格还原误差≤1e-9；
- β权重（适用模型）、完成摘要、`manifest.json`哈希。

主模型三种子的四格诊断会分别保留，不能只挑单个种子。
rule_trigger取预测原点可见规则并沿4步广播；target_event取各目标时刻标签，两者不可混用。
时间块统计可基于导出的原点/时间/逐项误差后续进行配对日/周块bootstrap；**本包未声称已完成显著性检验**。
测试原点相互重叠，不能将所有节点×步长当作独立样本做普通t检验。
云端 `results/cloud_logs/launch-*/` 保存退出码、日志和归档摘要；`archives/` 保存压缩结果和SHA256。
整个归档及同名 `.summary.json`、`.sha256` 都要下载到Mac；下载后校验，再考虑释放实例。
不要只下载截图或指标均值，也不要把smoke/benchmark结果写入论文。
阶段结束后需额外做公平性审阅、三种子比较和时间块统计；本包不自动修改论文/图表。

## 6. 可携带性和敏感信息

`BUNDLE_MANIFEST.json`列出代码、数据、配置、测试文件哈希。
`PROVENANCE.json`记录冻结数据来源版本，不包含原始记录或Mac绝对数据路径。
压缩包无原始会话CSV、旧模型权重、Word、论文图、.git、.venv、账号密码。
包含的聚合张量仍属于研究数据，上传前应确保你有相应云端处理权限。
包内 `configs/suite.json` 是生成时的可读冻结配置快照；真实运行入口同时核对该快照，修改配置需新版本。
