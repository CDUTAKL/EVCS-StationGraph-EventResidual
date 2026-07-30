# EVCS-StationGraph-EventResidual — Claude 项目记忆

## 项目概要

基于站内充电单元行为交互图的短期负荷预测（15 min 粒度，96→4 步）。
10 个充电节点，三类固定关系（load/event/pattern）+ 自适应第四关系，
事件门控残差修正 + 事件加权损失训练。

### 数据规模

| 指标 | 值 |
|------|-----|
| 时间步总数 | 118,818 |
| 训练预测起点 | 83,103 |
| 验证预测起点 | 17,807 |
| 测试预测起点 | 17,809 |
| 节点数 | 10 |
| 特征数 | 7 |

> 数据规模影响设计决策：10 节点场景下 hidden_dim=32 泛化优于 64；
> 小 batch（256）已充分利用 GPU，增大 batch 无益。

## 环境与兼容性

### 本地

- macOS，Python 3.11+，PyTorch 2.3+
- 虚拟环境：`.venv/`（已 gitignored）
- 首次搭建：`python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`

### 服务器（远程训练）

| 项目 | 详情 |
|------|------|
| IP | `10.14.92.65` |
| SSH | `ssh -i ~/.ssh/claude_code_server root@10.14.92.65` |
| 项目路径 | `/root/EVCS-StationGraph-EventResidual` |
| GPU | 2× RTX A6000（49.1 GB each），CUDA 12.1 |
| Python | **3.8.10**，PyTorch 2.4.1+cu121 |

### Python 3.8 兼容（关键！）

> **服务器 Python 3.8.10，以下写法会导致服务器运行崩溃：**

| 禁止使用 | 替代写法 |
|----------|---------|
| `str.removeprefix("xxx")` | `s[3:] if s.startswith("xxx") else s` |
| `str.removesuffix("xxx")` | `s[:-3] if s.endswith("xxx") else s` |
| `list[int]` / `dict[str, Any]` | `List[int]` / `Dict[str, Any]`（需 `from typing import ...`） |
| `tuple[str, ...]` | `Tuple[str, ...]` |
| `X \| Y` 联合类型 | `Union[X, Y]` |

### 确定性算法

**永远不要开启** `torch.use_deterministic_algorithms(True)`：
- 训练步 12.6ms → 1789.9ms（慢 **142 倍**）
- 即使 `warn_only=True` 下 CuBLAS GEMM 仍非确定性
- 即既慢 142 倍又未达成 bitwise 复现，纯负收益

## 命令

```bash
# 测试
.venv/bin/pytest -q

# 构建节点张量（--max-time-steps 仅限冒烟，正式构建不得设置）
.venv/bin/evcs-sg prepare-data --project configs/project.yaml

# 运行单个实验（SG-EXP-002~005）
.venv/bin/evcs-sg run --project configs/project.yaml \
  --experiment configs/experiments/SG-EXP-XXX.yaml \
  --set experiment.training.epochs=60   # 覆盖配置项（可重复）

# 运行 SG-EXP-005 需指定底座 checkpoint
.venv/bin/evcs-sg run --project configs/project.yaml \
  --experiment configs/experiments/SG-EXP-005-event-residual.yaml \
  --base-checkpoint outputs/experiments/SG-EXP-002/.../seed_2024/checkpoint.pt

# 运行 SG-EXP-006 机制消融套件
.venv/bin/evcs-sg run-mechanism --project configs/project.yaml \
  --suite configs/experiments/SG-EXP-006-mechanism.yaml \
  --base-checkpoint <SG-EXP-002-checkpoint>

# 运行正式流水线（SG-EXP-002→003→004→005→006 全流程）
.venv/bin/evcs-sg run-pipeline --project configs/project.yaml

# 汇总结果
python scripts/summarize_formal_results.py
```

> `--set KEY=VALUE` 覆盖机制：key 为点分路径，如 `experiment.training.epochs=100`。
> 值经 YAML 解析，因此 `true`/`false`/`null`/数字均可正确识别。

### 代码同步到服务器

```bash
# 从本地同步代码到服务器
rsync -avz -e "ssh -i ~/.ssh/claude_code_server" \
  --exclude='.venv' --exclude='.git' --exclude='__pycache__' \
  --exclude='outputs' --exclude='data' \
  /Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/ \
  root@10.14.92.65:/root/EVCS-StationGraph-EventResidual/

# 同步单个文件（如脚本更新）
rsync -avzR -e "ssh -i ~/.ssh/claude_code_server" \
  scripts/night_run.py root@10.14.92.65:/root/EVCS-StationGraph-EventResidual/
```

## 架构

### 模块地图

```
src/evcs_station_graph/
├── config.py          # 配置加载（project.yaml + experiment YAML，deep_merge 合并）
├── cli.py             # CLI 入口 (evcs-sg prepare-data / validate-artifacts)
├── data/
│   ├── tensor.py      # TensorBundle [T,N,F] + 张量构建
│   └── dataset.py     # WindowSpec(history=96, forecast=4) + NodeWindowDataset
├── graphs/
│   └── relations.py   # load/event/pattern 三类固定关系 + RelationSet
├── models/
│   ├── tcn.py         # SG-EXP-002: TCN 时间基线（逐节点独立预测）
│   ├── graph.py       # SG-EXP-003/004: StaticGraph / AdaptiveGraph（±10K params）
│   ├── residual.py    # SG-EXP-005: EventResidual（冻结底座 + 事件门控 + 有界残差 MLP）
│   └── common.py      # ForecastModel 抽象接口 + ForecastOutput([B,H,N])
├── training/
│   ├── engine.py      # train_experiment(流程编排), train_single_seed(五阶段流水线)
│   ├── factory.py     # build_model: 按 config.model 创建模型 + 加载 checkpoint
│   └── losses.py      # WeightedL1Loss(binary/intensity, λ≥0 退化为标准 L1)
├── evaluation/
│   ├── metrics.py     # MAE/RMSE + stratified_metrics(五层) + four_cell_diagnostics
│   └── rules.py       # FrozenEventRule(验证集冻结) + visible_event_scores(4分量)
├── experiments/
│   ├── pipeline.py    # run_formal_pipeline: 编排 SG-EXP-002→003→004→005→006
│   ├── mechanism.py   # 16 变体机制消融（关系子集 + 门控 on/off）
│   └── validation.py  # validate_pipeline_artifacts: 预测键唯一性 + 四格还原
└── reproducibility.py # set_global_seed + environment_snapshot + sha256_file
```

### 配置合并模型

```
project.yaml (基础)  +  experiments/SG-EXP-XXX.yaml (实验差异)
        ↓                       ↓
    deep_merge(base, {"experiment": overrides})   ← 后者覆盖前者
        ↓
    -- CLI overrides: "experiment.training.epochs=100"  (key=value 格式)
        ↓
    validate_common_config()   ← 校验 id/history_steps/forecast_steps/seeds
```

> **新增实验时**：修改实验 YAML 中与 project.yaml 不同的字段即可，相同的字段不需要重复。

### 关系图语义

| 关系类型 | 构建方式 | 含义 |
|---------|---------|------|
| `load` | 训练集负荷向量的 Pearson 相关系数 | 节点间的统计负荷相似性 |
| `event` | 事件标签的 Jaccard 共现系数 | 节点是否倾向于同时发生事件 |
| `pattern` | 日负荷曲线的 DTW 距离取负 | 节点间的时序模式相似性 |
| `adaptive` | 节点嵌入 → 学习邻接矩阵（仅 AdaptiveGraph） | 数据驱动的隐式关系 |

> 三类固定关系均做 top-k 稀疏化 + 对称归一化。门控融合值可直接解释：
> gate_i 接近 1 → 该关系对节点 i 贡献大；接近 0 → 该关系对节点 i 不重要。

### 事件系统

**事件分数 = 4 分量 per-node std 归一化后求和**：

| 分量 | 含义 | 来源特征 |
|------|------|---------|
| access | 新接入充电会话数 | `access_count` |
| departure | 离站会话数 | `departure_count` |
| active_delta | 活跃会话数突变 | `active_count` 的一阶差分 |
| load_delta | 负荷突变 | `load_jump_flag` |

- 阈值：验证集非零事件分数的 `trigger_quantile=0.95` 分位点
- 窗口扩展：触发点向后 `window_extension=2` 个时间片（因果前向，无未来信息泄漏）
- 相邻/重叠窗口自动合并
- 测试集**仅执行**已冻结规则，不参与阈值或参数确定

### 四格诊断（核心评价约束）

```
           rule_trigger=True   rule_trigger=False
target_event=True    格1              格2
target_event=False   格3              格4
```

**硬性约束**：Σ(格X_MAE × 格X_样本量) / 总样本量 ≡ 全局 MAE，容差 ≤ 1e-9。
若不能还原，则事件收益分析无意义——这是论文级证据的底线。

## 实验约定

- **命名**：SG-EXP-XXX，配置在 `configs/experiments/`。新增实验后更新 [实验登记表](docs/thesis/experiment-registry.md)
- **三随机种子**：2024 / 2025 / 2026
- **底座模型**：B3 最优参 — levels=6, hidden=32, embed=12, fixed_weight=0.5
- **早停**：patience=8，始终基于标准 L1Loss（不基于加权损失）
- **formal vs smoke**：`outputs/smoke/` 仅供实现验证；正式结果必须 3 种子 + `formal_ready=true`
- **新结论**：只来自 SG-EXP-* 实验，不继承旧论文 EXP-108/111/112 结论
- **向后兼容**：新增字段（如 `training.loss`）若缺失 → 走标准路径

### 模型依赖链

```
SG-EXP-002 (TCN) ──→ SG-EXP-005 (EventResidual)  ← 必须同种子 checkpoint 已存在
SG-EXP-003 (StaticGraph) ──→ SG-EXP-004 (AdaptiveGraph)
                           ──→ SG-EXP-006 (消融)
SG-EXP-004 (AdaptiveGraph) ──→ SG-EXP-007 (加权损失)
```

> SG-EXP-005 加载 SG-EXP-002 同种子 checkpoint 作为冻结默认路径。
> 运行 005 前确保 002 的三种子 checkpoint 均已训练完毕。

### 阶段 B 关键发现（底座参数的来源依据）

| 发现 | 数据支撑 | 设计决策 |
|------|---------|---------|
| levels=6 是硬下限 | 感受野 127 步 > 96 步历史窗口 | levels≥6 不可降低 |
| hidden=32 优于 64 | val_mae: 32→0.05958 vs 64→0.05982 | 10 节点不需大隐层 |
| 图结构带来 3.74× 提升 | StaticGraph vs TCN: 0.05958→0.01592 | 图建模是核心贡献 |
| top_k=3 优于 5/7 | 更密集的图增加噪声 | 关系稀疏化有益 |
| ReduceLROnPlateau 无显著收益 | B5 对照实验 | 不启用学习率调度 |

### 正式实验前检查

运行正式实验前必须确认：
- 环境快照完整（git_commit + resolved_config + data_manifest_sha256）
- 输出目录含实验编号和运行时间
- 预测键唯一且跨方法一致
- 四格加权可还原全局 MAE（容差 ≤1e-9）

## 关键约束

- **数据性质**：充电会话重构的节点代理负荷，非在线电表实测功率
- **图含义**：边表示站内统计交互，非配电网物理拓扑
- **节点标识**：`stationID == EVSEID` 在当前数据中完全一致，不可重复计作不同层级；规范字段为 `spaceID`
- **WindowSpec**：滑动窗口构建不能使用未来信息（严格按 split_origins 索引）
- **事件阈值**：在验证集上冻结，测试集不可参与阈值确定
- **旧论文项目**：`references/upstream-project.md` 中记录，只读引用

### 历史缺陷与修复记录

| 编号 | 问题 | 修复 |
|------|------|------|
| ISSUE-001 | 事件阈值全为零（归一化错误） | rules.py 重写：仅在验证集非零分数上拟合分位数 |
| ISSUE-001b | 事件窗口过于稀疏 | 方案 C：因果前向扩展（触发点仅向未来延伸） |
| ISSUE-001c | 对称扩展存在未来信息泄漏 | `apply_frozen_event_rule` 改为因果前向 |
| ISSUE-003 | 特征极端稀疏（大量零值） | `stratified_metrics` 新增 `nonzero_load` 子集指标 |
| ISSUE-004 | TCN 感受野文档错误 | 实际 RF=127 步（levels=6），非旧文档的 7 步 |
| 架构审核 #1 | `relation_dropout` 仅写配置未进计算 | GCN β 融合与残差邻居聚合实现训练期关系屏蔽 |
| 架构审核 #3 | 自适应图 in-place 操作 | `masked_fill` 替代 `fill_diagonal_`/`scatter_` |
| 架构审核 #4 | GroupNorm 跨时间维 | 逐时间步 LayerNorm |

> 以上修复均有对应回归测试。修改相关模块前，确保理解 ISSUE 编号对应的修复逻辑，避免倒退。

### 外部 AI 执行纪律

若 DeepSeek 或其他 AI 被用于执行正式实验：

| 允许 | 禁止 |
|------|------|
| 环境核验、运行、故障原样记录 | 修改数据划分、节点清单、模型结构 |
| 简要摘要（见 DeepSeek-formal-execution-handoff.md §5） | 修改训练参数、随机种子、候选关系、评价口径 |
| 遇到失败时原样保留日志 | 自行删减实验、降低轮数、减少种子、测试集调参 |

> 精细分析、论文结论、图表重绘与结果写回由 Codex（Claude）在完整产物回传后完成。

## 代码修改协议

> **每次修改 `src/` 下的 Python 代码后，必须按以下流程执行质量检查。
> 这是硬性约定，不是可选项。**

### 基础编码规范（写代码时遵守）

遵循 [代码样式与修改协议](docs/development/code-style-and-change-protocol.md) 的全部约定，核心要点：

- **全部函数**（含私有）写中文文档字符串，说明输入、输出和边界条件
- 张量维度变换（permute/reshape/einsum）**必须**加行内注释解释变换前后语义
- 数值常量（阈值/容差/魔法数字）**必须**注释取值理由
- 长函数（>80行）用 `# ========== 阶段 N：描述 ==========` 分段
- 函数保持单一职责；遇异常**直接抛出**，不静默补齐或跳过
- 新实验必须通过统一入口，禁止在临时脚本中复制切分/指标/事件定义

### 第一阶段：自动简化（每次修改后）

修改完任意 Python 文件后，启动 **code-simplifier** agent 对变更文件做简化：
- 消除冗余变量和中间赋值
- 统一命名风格（与 [代码样式协议](docs/development/code-style-and-change-protocol.md) 一致）
- 合并可合并的条件分支
- **保留所有功能不变**

```
Agent: code-simplifier
输入: 刚修改的文件列表（git diff --name-only 获取）
```

### 第二阶段：静默失败检查（功能块完成后）

完成一个逻辑功能块后，启动 **silent-failure-hunter** agent：
- 检查 try-except 是否吞掉了异常（`except: pass`）— 违反规范第 4.9 条
- 检查 fallback 路径是否静默返回 None/默认值
- 检查 per-batch 归一化、checkpoint 加载等关键路径的错误处理
- 检查所有 `if` 分支是否都有返回值（无隐式 None）

```
Agent: silent-failure-hunter
输入: 当前功能块涉及的所有文件
```

### 第三阶段：完整审查（提交前）

执行 `/commit` 之前，对**所有未提交的变更**做完整审查：

1. 先对所有新代码启动 **code-reviewer** agent，对照 [代码样式协议](docs/development/code-style-and-change-protocol.md) 检查代码规范 + 逻辑缺陷
2. 如有新增 try-except/fallback 逻辑，再跑一次 **silent-failure-hunter**
3. 对照 [提交前检查清单](docs/development/code-style-and-change-protocol.md#9-提交前检查清单) 逐项确认
4. 修复发现的问题，然后 `/commit`

### 判断标准

| 变更规模 | 执行内容 |
|----------|---------|
| 单文件小改（<20行） | 仅 code-simplifier |
| 单文件大改（≥20行）或新增文件 | code-simplifier + silent-failure-hunter |
| 多文件修改 | code-simplifier + silent-failure-hunter + code-reviewer |
| 提交前 | 上述全流程通过后方可 `/commit` |

### 特别敏感区域

以下文件涉及训练/实验核心逻辑，**任何修改都必须全流程审查**：

- `src/evcs_station_graph/training/engine.py` — 训练循环、早停、损失分发
- `src/evcs_station_graph/training/losses.py` — 自定义损失函数
- `src/evcs_station_graph/models/graph.py` — 门控多关系 GCN
- `src/evcs_station_graph/evaluation/rules.py` — 事件窗口规则 + 四格诊断
- `src/evcs_station_graph/data/dataset.py` — WindowSpec 滑动窗口

## Git 约定

### 分支命名

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat/` | 新增功能、模型、实验 | `feat/multi-relation-gated-gcn` |
| `fix/` | 修复缺陷，不改变研究口径 | `fix/python38-compat` |
| `docs/` | 文档、登记表、大纲 | `docs/experiment-checklist` |
| `experiment/` | 需改动配置或代码的正式实验 | `experiment/SG-EXP-007` |

> 当前分支：`feat/multi-relation-gated-gcn`，主分支：`main`

### 提交信息格式

```
type: 简短中文说明
```

常用 type：`feat` / `fix` / `docs` / `test` / `exp` / `chore`

一次提交一个可解释目的，不混入无关修改。

### 提交前最低检查

```bash
.venv/bin/python -m compileall -q src scripts tests  # 语法检查
.venv/bin/pytest -q                                    # 31 个测试必须全过
git status --short                                      # 确认无数据/权重/敏感文件
git diff --check                                        # 无空白冲突
```

## 图表绘制

### 结果数据图

**使用 scipilot-figure-skill**（路径：`~/.codex/skills/scipilot-figure-skill/`）：
- 职责：数据剖析 → 推荐图型 → 拦截经典错误 → 绘制 → 视觉自检闭环
- 适用图型：MAE/RMSE 对比柱状图、训练曲线、Bootstrap 置信区间、热力图、四格诊断、时序对比
- 脚本：`profile_data.py` / `setup_style.py` / `export_figure.py` / `check_figure.py` / `visual_qa.py`
- **DPI 要求：1200**（论文投稿级，不可降低）
- 色盲安全配色 + 冗余编码 + 灰度预览 + AI 读图复核

### 结果分析（数字 → 论文表述）

**使用 research-results-analysis**（路径：`research-workflow-kit/skills/research-results-analysis/`）：
- 职责：实验工件 → 可信摘要 → 保守论文结论
- 核心原则：不编造结果、标注缺失基线、报告不确定性、区分主结果/消融/鲁棒性/误差分析
- 关键文件：`autoresearch-results.tsv`、`benchmark-report-schema.md`

### 模型架构图

不在 Claude 职责范围内，不绘制。

## 工作流

### Scripts 地图

| 脚本 | 阶段 | 用途 | 执行位置 |
|------|------|------|---------|
| `audit_station_graph_inputs.py` | 数据审计 | 审核会话 CSV 中的节点标识 | 本地 |
| `audit_architecture_cpu.py` | 架构审计 | 合成数据验证图架构计算行为 | 本地 |
| `screen_station_nodes.py` | 数据筛选 | 筛选站内节点清单 | 本地 |
| `phase_b_screen.py` | 超参筛选 | B1-B4 四阶段序贯筛选（单种子） | 本地/服务器 |
| `phase_b5_scheduler.py` | 超参筛选 | ReduceLROnPlateau 对照实验 | 本地/服务器 |
| `night_run.py` | 正式实验 | B6 三底座对照 → SG-EXP-002~006 全流程 | **服务器** |
| `run_formal_experiments.sh` | 正式实验 | 同上（shell 包装版） | **服务器** |
| `run_deepseek_formal_experiments.sh` | 正式实验 | DeepSeek 兼容入口（支持 AUTO_SHUTDOWN） | **服务器** |
| `summarize_formal_results.py` | 汇总 | 读取产物，输出跨实验对比 | 本地 |
| `sg_exp_007_screen.py` | 加权损失 | λ∈{0,2,3,5} 筛选 → intensity 对比 | 本地/服务器 |

> **执行顺序**：数据审计 → 架构审计 → 节点筛选 → 超参筛选(B) → 正式实验 → 汇总
> `phase_b_screen.py` 必须在 `night_run.py` 之前运行——B 阶段最优参数是正式实验的底座。

### 每个实验的输出工件

```
outputs/<实验ID>/<run_tag>/
├── manifest.json          # 实验元信息（result_authority, 种子, 时间戳）
├── resolved_config.yaml   # 解析后的完整配置（可追溯）
├── seed_<N>/
│   ├── checkpoint.pt      # 模型权重
│   ├── predictions.csv    # 预测长表 [split, origin_index, horizon, node_id, pred, truth]
│   ├── metrics_summary.json  # 分层 MAE/RMSE（global/event_window/stable_window/node/horizon）
│   └── diagnostics.json   # 四格诊断 + bootstrap 结果
└── environment.json       # environment_snapshot() 输出
```

### 预测文件主键

```text
split + origin_index + horizon + node_id  ← 四元组保证唯一
```

跨方法比较前必须验证：行数一致、键集合一致、顺序无关指纹一致。

### 夜跑
```bash
# SSH 到服务器
ssh -i ~/.ssh/claude_code_server root@10.14.92.65
# 在服务器上
cd /root/EVCS-StationGraph-EventResidual
python scripts/night_run.py
```

### SSH 进程管理
```bash
# 终止卡死的夜跑进程
ssh -i ~/.ssh/claude_code_server root@10.14.92.65 'kill -9 <PID>'
# 查看是否还在运行
ssh -i ~/.ssh/claude_code_server root@10.14.92.65 'ps aux | grep night_run | grep -v grep'
```

### 实验执行顺序
```
Step 0: 确认夜跑结果 → Step 1: P0 基线 → Step 2: SG-EXP-007a λ 筛选
→ Step 3: SG-EXP-007b 强度加权 → Step 4: P1 补充 → Step 5: P2 锦上添花
```

### 测试覆盖地图

| 测试文件 | 覆盖范围 | 数据 |
|---------|---------|------|
| `test_data_and_keys.py` | WindowSpec 滑动窗口、预测键唯一性、TensorBundle 序列化 | synthetic_bundle |
| `test_models.py` | TCN/StaticGraph/AdaptiveGraph/EventResidual 前向形状 + 梯度流 | synthetic_bundle |
| `test_relations_and_evaluation.py` | 关系构建、归一化邻接矩阵、事件规则拟合、四格诊断还原 | synthetic_bundle |
| `test_experiment_orchestration.py` | 机制变体生成、配置校验 | smoke_config |
| `test_training_smoke.py` | 端到端训练循环、早停、checkpoint 加载、工件验证 | smoke_config |

> 全部使用合成数据（`synthetic_bundle` fixture），不依赖真实数据。31 个测试。
> 冒烟测试使用 `max_samples_per_split=8` 限制样本量（≈30 秒跑完）。

## 文档索引

### 论文与研究设计
- [研究简报](docs/thesis/thesis-brief.md) ← 问题定义、假设、预期贡献（为什么做这个研究）
- [实验架构](docs/thesis/experiment-architecture.md) ← 数据/模型/训练/评价四层架构
- [实验登记表](docs/thesis/experiment-registry.md) ← 新增实验后必须更新
- [范围与硬门槛](docs/thesis/project-scope-control.md) ← 允许/禁止的研究表述（答辩防身）
- [数据可用性](docs/thesis/data-availability.md) ← 原始数据审计结论
- [风险登记表](docs/thesis/risk-register.md) ← 7 项风险及当前控制措施
- [执行路线](docs/thesis/execution-roadmap.md) ← 四阶段路线图（数据→基线→残差→论文）
- [大纲 v1](docs/thesis/new-route-thesis-outline-v1-2026-07-30.md) ← 论文大纲（28 篇调研修订版）
- [SG-EXP-001 节点筛选报告](docs/thesis/SG-EXP-001-node-screening-report.md)
- [ADR-001 独立项目与命名空间](docs/thesis/decisions/ADR-001-project-separation.md) ← 与旧论文项目的边界

### 开发与实验
- [阶段 A/B 全盘总结](docs/development/phase-a-b-summary-2026-07-30.md) ← B3 底座参数的完整数据来源
- [架构审核报告](docs/development/architecture-audit-2026-07-30.md) ← 4 项架构缺陷修复记录
- [SG-EXP-002~006 运行手册](docs/experiments/SG-EXP-002-to-006-runbook.md) ← 实验对应关系、数据准备、单项/正式运行
- [实现与验证记录](docs/experiments/implementation-validation-report.md)
- [DeepSeek 正式实验交接](docs/experiments/DeepSeek-formal-execution-handoff.md) ← 外部 AI 执行边界与回传格式
- [补充实验清单](docs/development/supplementary-experiments-2026-07-30.md) ← P0/P1/P2 完整步骤
- [DeepSeek 审计报告](DeepSeek.md) ← ISSUE-001~004 修复详情、事件窗口统计数据

### 规范与协作
- [代码样式与修改协议](docs/development/code-style-and-change-protocol.md)
- [Git 版本管理工作流](docs/development/git-workflow.md)
- [GPT 沟通桥](docs/development/gpt-bridge.md) ← Claude ↔ GPT 异步对话（28 篇论文调研 + 4 个讨论问题）

### 外部 Skills（路径引用，非项目文件）

| Skill | 路径 | 用途 |
|-------|------|------|
| scipilot-figure-skill | `~/.codex/skills/scipilot-figure-skill/` | 结果数据图（MAE 对比/训练曲线/Bootstrap/热力图/四格诊断/时序），**1200 DPI** |
| research-results-analysis | `research-workflow-kit/skills/research-results-analysis/` | 实验结果 → 保守论文结论 |
| research-code-quality | `research-workflow-kit/skills/research-code-quality/` | 实验合同：config+seed+split+metric+output+registry+smoke |
| research-data-availability | `research-workflow-kit/skills/research-data-availability/` | DATA-* 编号 + material-passport 材料护照 |
| research-paper-writing | `research-workflow-kit/skills/research-paper-writing/` | 论文撰写（术语台账 + Nature 风格检查 + 段落模板） |
| cdut-thesis-format | `~/.claude/skills/cdut-thesis-format/` | 论文 .docx 格式检查/修复（26 类检查） |
