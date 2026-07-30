# EVCS-StationGraph-EventResidual — Claude 项目记忆

## 项目概要

基于站内充电单元行为交互图的短期负荷预测（15 min 粒度，96→4 步）。
10 个充电节点，三类固定关系（load/event/pattern）+ 自适应第四关系，
事件门控残差修正 + 事件加权损失训练。

## 命令

```bash
# 测试
.venv/bin/pytest -q

# 构建节点张量
.venv/bin/evcs-sg prepare-data --project configs/project.yaml

# 运行完整正式实验
scripts/run_formal_experiments.sh

# 汇总结果
python scripts/summarize_formal_results.py
```

## 架构

```
src/evcs_station_graph/
├── config.py          # 配置加载（project.yaml + experiment YAML）
├── cli.py             # CLI 入口 (evcs-sg)
├── data/
│   ├── tensor.py      # TensorBundle + 张量构建
│   └── dataset.py     # WindowSpec + Dataset
├── graphs/
│   └── relations.py   # 三类固定关系构建
├── models/
│   ├── tcn.py         # SG-EXP-002: TCN 时间基线
│   ├── graph.py       # SG-EXP-003/004: StaticGraph / AdaptiveGraph
│   ├── residual.py    # SG-EXP-005: EventResidual 修正器
│   └── common.py      # ForecastModel 抽象 + ForecastOutput
├── training/
│   ├── engine.py      # train_experiment, train_single_seed
│   ├── factory.py     # build_model
│   └── losses.py      # WeightedL1Loss (SG-EXP-007)
├── evaluation/
│   ├── metrics.py     # MAE/RMSE + 分层
│   └── rules.py       # 事件窗口规则 + 四格诊断
├── experiments/
│   ├── pipeline.py    # 实验流水线
│   ├── mechanism.py   # 消融实验
│   └── validation.py  # 工件验证
└── reproducibility.py # 随机种子控制
```

## 实验约定

- **命名**：SG-EXP-XXX，配置在 `configs/experiments/`
- **三随机种子**：2024 / 2025 / 2026
- **底座模型**：B3 最优参 — levels=6, hidden=32, embed=12, fixed_weight=0.5
- **早停**：patience=8，始终基于标准 L1Loss（不基于加权损失）
- **formal vs smoke**：`outputs/smoke/` 仅供实现验证；正式结果必须 3 种子 + `formal_ready=true`
- **新结论**：只来自 SG-EXP-* 实验，不继承旧论文 EXP-108/111/112 结论
- **向后兼容**：新增字段（如 `training.loss`）若缺失 → 走标准路径

## 关键约束

- **数据性质**：充电会话重构的节点代理负荷，非在线电表实测功率
- **图含义**：边表示站内统计交互，非配电网物理拓扑
- **节点标识**：`stationID == EVSEID` 在当前数据中完全一致，不可重复计作不同层级；规范字段为 `spaceID`
- **WindowSpec**：滑动窗口构建不能使用未来信息（严格按 split_origins 索引）
- **事件阈值**：在验证集上冻结，测试集不可参与阈值确定
- **旧论文项目**：`references/upstream-project.md` 中记录，只读引用

## 工作流

### 夜跑
```bash
# SSH 到服务器
ssh -i ~/.ssh/claude_code_server root@10.14.92.65
# 在服务器上
cd /root/EVCS-StationGraph-EventResidual
python scripts/night_run.py
```

### 实验执行顺序
```
Step 0: 确认夜跑结果 → Step 1: P0 基线 → Step 2: SG-EXP-007a λ 筛选
→ Step 3: SG-EXP-007b 强度加权 → Step 4: P1 补充 → Step 5: P2 锦上添花
```

## 文档索引

- [研究简报](docs/thesis/thesis-brief.md)
- [实验架构](docs/thesis/experiment-architecture.md)
- [实验登记表](docs/thesis/experiment-registry.md)
- [大纲 v1](docs/thesis/new-route-thesis-outline-v1-2026-07-30.md)
- [补充实验清单](docs/development/supplementary-experiments-2026-07-30.md)
- [GPT 沟通桥](docs/development/gpt-bridge.md)
- [代码样式协议](docs/development/code-style-and-change-protocol.md)
- [Git 工作流](docs/development/git-workflow.md)
