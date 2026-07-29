# SG-EXP-002～006 实验运行手册

## 1. 实验对应关系

| 实验 | 模型或诊断 | 核心问题 |
|---|---|---|
| SG-EXP-002 | TCN 默认时间模型 | 不使用跨节点关系时能达到怎样的稳定基线 |
| SG-EXP-003 | 固定站内交互图模型 | 训练期固定的统计关系是否提供增益 |
| SG-EXP-004 | 自适应图模型 | 可学习节点关系是否比固定图更适合当前数据 |
| SG-EXP-005 | 事件残差修正模型 | 只在事件窗口局部修正是否改善关键突变场景 |
| SG-EXP-006 | 消融、敏感性和四格诊断 | 收益来自哪里，结论对参数是否稳定 |

## 2. 数据准备

正式节点张量：

```bash
.venv/bin/evcs-sg prepare-data \
  --project configs/project.yaml \
  --output data/processed/SG-DATA-005-primary-tensor.npz \
  --metadata data/manifests/SG-DATA-005-primary-tensor.json
```

张量包含 15 分钟节点代理负荷、预测时点可见行为特征、时间特征、事件标签、
时间顺序切分和训练期标准化参数。预测样本由 96 个历史时间片输入，预测未来
4 个时间片。

## 3. 自动化测试

```bash
.venv/bin/pytest -q
.venv/bin/python -m compileall -q src tests
```

测试覆盖时间片重构、预测键唯一性、模型输出维度、统计关系、四格还原、
检查点种子匹配和编排配置覆盖。

## 4. 单项实验

```bash
.venv/bin/evcs-sg run \
  --project configs/project.yaml \
  --experiment configs/experiments/SG-EXP-002-temporal-baseline.yaml
```

SG-EXP-003 和 SG-EXP-004 只需替换实验配置。SG-EXP-005 必须通过
`--base-checkpoint` 指向 SG-EXP-002 的运行根目录，程序会按随机种子加载检查点。

## 5. 正式一键运行

```bash
scripts/run_formal_experiments.sh
```

若由 DeepSeek 在 GPU 云实例中作为执行方运行，使用带环境、日志、摘要和校验和
留档的入口：

```bash
bash scripts/run_deepseek_formal_experiments.sh
```

仅在确认云实例允许安全自动关机时显式设置：

```bash
AUTO_SHUTDOWN=1 bash scripts/run_deepseek_formal_experiments.sh
```

完整执行边界与回传清单见
`docs/experiments/DeepSeek-formal-execution-handoff.md`。

该入口依次运行 SG-EXP-002～006。每项基础模型使用三个随机种子；SG-EXP-006
运行固定的 16 个机制变体。运行结束后检查：

```text
outputs/formal/SG-PIPELINE-002-006/<时间戳>/artifact_validation_report.json
```

只有 `passed=true` 且 `formal_ready=true` 的流水线可进入论文证据审核。

## 6. 输出工件

每个实验目录至少包含：

- 合并后的实际配置；
- 运行清单和结果权威级别；
- 每个种子的最佳检查点；
- 逐预测键长表；
- 全局、事件、稳定窗口和四格指标；
- 跨种子均值与标准差；
- 四格加权还原检查。

流水线根目录额外包含跨实验指标表和工件一致性报告。

## 7. 结果解释边界

固定图或自适应图未优于 TCN 时，应如实写为“当前节点覆盖与样本条件下未观察到
稳定增益”。事件残差修正只允许解释为事件窗口的条件性局部收益，不得由局部结果
外推为全局最优。统计图边不解释为物理电气连接。
