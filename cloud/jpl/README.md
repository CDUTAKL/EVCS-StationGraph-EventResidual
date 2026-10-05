# SG-EXP-028 JPL AutoDL 包

此包用于 **SG-DATA-007 / SG-EXP-028** 的 JPL 独立场站实验。数据集已冻结，包内没有原始会话 JSONL、API 令牌、账号凭据或论文 DOCX。它不会自动开始正式训练；本地打包也没有运行训练。

## 上传与环境

将 `SG-EXP-028-JPL-AutoDL.tar.gz` 上传到 AutoDL 实例并解压；保持解压目录完整。使用实例自带的 CUDA 版 PyTorch，不要用 pip 覆盖安装 CPU 版 PyTorch。按需安装 `cloud/jpl/requirements.txt` 中其余 Python 依赖。

```bash
tar -xzf SG-EXP-028-JPL-AutoDL.tar.gz
cd evcs-jpl-sg-exp-028
bash cloud/jpl/run_autodl.sh preflight
```

`preflight` 只核对 bundle 哈希、数据 schema、固定节点/特征、成熟标签窗口、训练矩阵和模型参数量；不训练，也不生成测试预测。

## 后续 GPU 烟测与正式运行

GPU 烟测使用训练段和 tuning 段的少量窗口，最多运行两轮，只验证执行链路；不会读 calibration/test 标签或产生测试预测，结果不属于论文证据：

```bash
bash cloud/jpl/run_autodl.sh smoke
```

`formal` 命令会检查这份烟测通过凭据；缺少或与当前包/数据哈希不一致时会拒绝启动。

正式训练必须等用户另行明确授权。授权后，四卡示例为：

```bash
CONFIRM_FORMAL=SG-EXP-028 GPU_IDS=0,1,2,3 AUTO_SHUTDOWN=0 \\
  bash cloud/jpl/run_autodl.sh formal
```

默认不关机。只有确认希望运行结束后请求关机时才将 `AUTO_SHUTDOWN=1`；云平台是否停止计费仍须在控制台核实。脚本按每卡一个进程调度12个冻结任务，任一任务失败即停止队列且不导出测试结果；全部模型/种子检查点完成后，先写入检查点哈希锁，再一次性导出 tuning、calibration 和 test。支持断点续跑时显式附加 `RESUME=1`；不得改变冻结配置或挑选种子。

## 结果解释边界

JPL 是 ACN 数据的另一场站，并非独立数据提供方或全新时间时期。目标仍为由会话总电量均匀分配形成的事后 proxy（kWh/15 min），不是实测功率；输入事件即时可见是假设，实际上报延迟未测。该验证回答同一协议下的跨场站重拟合表现，不支持零样本迁移、真实功率准确性或未来时期泛化。

运行完成后，归档写入 `archives/`，包括结果、训练日志、检查点锁、manifest 和 SHA-256。运行失败时也会尝试归档当前产物；失败情况下脚本不会发出自动关机请求，以保留排障与恢复机会。
