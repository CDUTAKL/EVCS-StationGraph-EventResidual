# EVCS StationGraph EventResidual

独立研究项目：基于站内充电单元行为交互图开展时空负荷预测，并在验证集冻结的事件窗口内实施有界残差修正。

## 研究主线

1. 将充电会话按站内单元和 15 min 时间片重构为节点代理负荷。
2. 以时间模型形成稳定的默认预测。
3. 在同一站点内构建充电单元之间的统计交互图，提取跨节点信息。
4. 由验证集确定并冻结事件阈值、候选关系和分流规则。
5. 仅在事件窗口内对默认预测施加有界残差修正。
6. 分别评价全局、事件窗口、稳定窗口、节点和预测步长表现。

## 证据边界

- 当前数据是充电会话记录重构的**节点代理负荷**，不是在线电表实测功率。
- 图边表示站内充电单元之间的统计交互，不表示配电网物理拓扑。
- `stationID` 与 `EVSEID` 在当前归档中完全一致，不得重复计作不同节点层级。
- 新结论必须来自 `SG-EXP-*` 实验，不直接继承旧论文的 EXP-108/111/112 结论。

## 快速入口

- [研究简报](docs/thesis/thesis-brief.md)
- [范围与硬门槛](docs/thesis/project-scope-control.md)
- [实验架构](docs/thesis/experiment-architecture.md)
- [实验登记表](docs/thesis/experiment-registry.md)
- [数据可用性](docs/thesis/data-availability.md)
- [风险登记表](docs/thesis/risk-register.md)
- [SG-EXP-002～006 运行手册](docs/experiments/SG-EXP-002-to-006-runbook.md)
- [实现与验证记录](docs/experiments/implementation-validation-report.md)
- [代码样式与修改协议](docs/development/code-style-and-change-protocol.md)
- [Git 版本管理工作流](docs/development/git-workflow.md)

## 已实现模块

- 15 分钟节点代理负荷张量、滑动窗口样本和统一预测键；
- TCN 默认时间模型；
- 固定站内统计交互图模型；
- 自适应图模型；
- 验证集冻结事件门控下的有界残差修正模型；
- 五类候选关系、消融、敏感性和四格互斥诊断；
- 统一训练、检查点、三随机种子、评价、汇总与工件审计。

## 常用命令

```bash
# 自动化测试
.venv/bin/pytest -q

# 构建正式节点张量
.venv/bin/evcs-sg prepare-data --project configs/project.yaml

# 运行完整正式实验
scripts/run_formal_experiments.sh
```

`outputs/smoke/` 下的输出仅用于实现验证。只有完整数据、三随机种子且最终
`artifact_validation_report.json` 中 `formal_ready=true` 的结果，才可进入论文证据审核。

旧论文项目只作为只读证据源，路径记录在 [上游项目说明](references/upstream-project.md)。
