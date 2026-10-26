# ACN 代理标签敏感性与排序稳定性分析包

日期：2026-10-26  
范围：Caltech 事件时刻协议，708,560 个测试预测键  
性质：只读已有冻结预测；不训练、不联网、不修改论文、不保存原始会话

## 这个包解决什么问题

论文的两个主要弱点是：

1. **创新增量有限**：MRG-GCN 是已有组件的组合，效果量小，MDP 没有带来预测增益。
2. **实践效度受代理数据限制**：标签是会话总电量均匀分摊，不是实测功率。

这个包不试图掩盖这两点，而是把它们变成可复核的证据：

- **创新**：把“模型排序是否对标签定义敏感”做成一个新的经验/方法问题，并给出可复用的 MDP 协议卡与最小报告清单。
- **实践效度**：量化均匀分摊 vs 完成时刻截断的标签差异，显示三种子平均全局排序基本保持、活跃/事件排序更敏感；明确哪些结论只能等实测功率。

## 核心结果

| 评价口径 | 三种子平均 MAE 排序的 Spearman（先平均 MAE 再排序） | 逐种子 Spearman 均值 | 逐种子范围 |
|---|---:|---:|---:|
| 全局 MAE | **0.993** | 0.974 | 0.972–0.979 |
| 稳定窗口 MAE | **0.993** | 0.974 | 0.965–0.986 |
| 零目标 MAE | **0.951** | 0.907 | 0.874–0.965 |
| 固定均匀非零键 MAE | **0.671** | 0.671 | 0.629–0.727 |
| 标签事件 MAE | **0.559** | 0.324 | 0.007–0.608 |
| 非零目标 MAE（评价标签） | **0.420** | 0.000 | −0.112–0.098 |

注：0.993 是先把每个配置的三种子 MAE 平均、再对 12 个配置排序得到的 Spearman；逐种子相关均值是 0.974，两者不是同一个统计量。非零 0.420 与逐种子均值 0.000 同理。相关值仅描述本已查看 Caltech 测试期；脚本未设通过/不通过阈值，原 0.9/0.6 分类已删除。

其他关键数字：

- 12 个配置“先平均 MAE 再排序”的全局 Spearman 0.993，逐种子相关均值 0.974，Top-1 均为 `agcrn_full`，Top-3 重合 3/3，最大排名变化 1 位；逐种子 0.972/0.972/0.979。
- 固定非零子集：`agcrn_full` 由第 1 降至第 6，`mrg_event` 由第 6 升至第 1。
- MRG-GCN vs 容量近似 TCN 的全局 MAE 差在四种训练/评估组合下均为正：**11.44%–16.06%**；这是所检条件下的描述，2×2 不是四个独立确认实验。
- 节点门控三种子平均：均匀标签 **2.69%** → 截断标签 **1.65%**；但截断标签下 seed-2024 由 **+1.73%** 变为 **−0.91%**，发生反转，不能写“方向不变”。
- 标签差异：测试键零值率 87.25% → 94.27%；49,768 个均匀正键变为零；无零→正迁移；逐键绝对差均值 0.033530，P95 0.266875 kWh/15 min；全网格均值 0.047782（与论文 0.0477816 一致）。
- 非零键标签差异均值 0.262941、P95 0.759664；事件键均值 0.261314、P95 0.844667。与 5.3 节区间宽度的比较只作描述性量级对照：统计集合不同，不能推断逐键覆盖率或实测覆盖；本文未针对同步实测值校准或评价区间。

## Codex 复核修正（已应用）

- **R1 门控**：披露 seed-2024 在截断标签下的反转（+1.73%→−0.91%）；不再写“方向不变/各次一致”。
- **R2 统计量命名与范围**：表头/CSV 使用 `rho_of_seed_mean_mae_ranks`（先平均 MAE 再排序，0.993）与 `mean_of_seed_rhos`（逐种子相关均值，0.974）；非零 0.420 vs 0.000 同理。全局结论限定为 12 配置、两套标签、已查看 Caltech 测试期；删除 0.9/0.6 阈值。
- **R3 区间**：删除“不能覆盖实测功率”的推断；改为“未针对同步实测值校准或评价区间，实测覆盖尚未验证”。
- **R4 贡献**：区分关系组件价值（JPL 自环替换：负荷 1.82%、轮廓 1.52%；负荷关系非零组为未校正探索性证据）与完整模型未胜 TCN；不再写“增量不延伸至非零组”。
- **R5 网站/材料**：GET 页面 200；注册 POST 先 502 后 500（截图）；登录 POST 为“用户名或密码无效”；2026-10-25 API 无认证 401、Basic 认证 500/超时；年度 0 行不作源端零记录证据；公开资料含电流时序。
- **路径/可携带**：四个脚本用 `Path(__file__).resolve().parent` 定位包根，项目根由 `EVCS_PROJECT_ROOT` 或 `config.json` 提供；50 个输入已在包内，`locate_inputs.py` 报 `skip_verified=50, mismatch=0`。
- **交付**：候选图 1200 dpi（11320×4563），去掉 0.9 阈值线，隐藏右面板左轴线；最终仍需按论文版心缩放做视觉验收。

## 文件

| 文件 | 用途 |
|---|---|
| `analyze.py` | 可复现分析脚本；读取冻结预测，输出报告、JSON、图 |
| `make_deliverables.py` | 生成 CSV 表格与合并版候选图 |
| `make_manifest.py` | 生成输入/输出 SHA-256 证据清单 |
| `report.md` | 完整分析报告（推荐先读） |
| `results.json` | 全部数值结果，供论文/复核引用 |
| `validation.md` | 与论文既有表格的数值一致性核对 |
| `manifest.json` | 输入/输出/环境/命令的证据清单 |
| `manuscript_insert.md` | 可直接并入的 3.8.5 正文、表 3-16、图 3-17、附表 A-2 |
| `contribution_reframing.md` | 摘要/绪论/结论的贡献重构文本 |
| `mdp_protocol_card.md` | MDP 三层诊断的可复用协议卡 |
| `minimum_reporting_checklist.md` | 代理负荷预测的最小报告清单 |
| `integration_plan.md` | 给 Codex 的并入顺序、任务建议、验收清单 |
| `defense_qa.md` | 答辩问答准备（创新、代理数据、排序稳定性、MDP、下一步） |
| `table3_16_spearman.csv` | 表 3-16 的机器可读版本；字段为 `rho_of_seed_mean_mae_ranks`、`mean_of_seed_rhos`、`spearman_per_seed_range` |
| `tableA2_rank_stability.csv` | 附表 A-2 的机器可读版本 |
| `table2x2.csv` | 2×2 训练/评估矩阵的机器可读版本 |
| `table_gate_per_seed.csv` | 节点门控逐种子 MAE 与相对改善 |
| `fig3_17_proxy_rank_stability_candidate.png/.svg` | 图 3-17 候选版（A/B 双面板，1200 dpi，右面板左轴线隐藏） |
| `fig_rank_stability_by_metric.png` | 单面板备用图（无 0.9 阈值线） |
| `fig_rank_slope.png` | 12 个配置在两套标签下的排名变化 |
| `fig_ranking_scatter.png` | 全局 MAE 散点（均匀 vs 截断） |
| `fig_gate_label_sensitivity.png` | 节点门控在两种标签下的对照 |
| `fig_label_diff_hist.png` | 测试键标签差异分布 |
| `config.json` | 可配置项目根目录与包内输入布局 |
| `PORTABILITY.md` | 迁移、刷新输入、依赖与边界说明 |
| `locate_inputs.py` | 从项目根目录复制/提取 50 个输入并校验哈希 |
| `inputs/datasets/` | 2 份冻结数据集 |
| `inputs/exp019/` | SG-EXP-019 的 36 份预测副本（派生输出） |
| `inputs/exp027/` | SG-EXP-027 的 6 份预测副本（派生输出） |
| `inputs/exp032/` | SG-EXP-032 的 6 份预测副本（派生输出） |

## 复现

```bash
cd ~/acn_proxy_stability_20261026
PYTHONDONTWRITEBYTECODE=1 python3 analyze.py
```

脚本默认只读包内 `inputs/`：

- `inputs/datasets/uniform.npz`、`alternative.npz`
- `inputs/exp019/`（36 份 SG-EXP-019 预测）
- `inputs/exp027/`（6 份 SG-EXP-027 预测）
- `inputs/exp032/`（6 份 SG-EXP-032 预测）

若包内文件缺失，`analyze.py` 会回退到 `config.json` 的 `project_root`。迁移或刷新见 `PORTABILITY.md`；可用 `python3 locate_inputs.py --force` 重新复制/提取 50 个输入，再运行 `python3 make_manifest.py` 校验哈希。

不写仓库；不训练；不联网；不读取原始会话 CSV。

## 文件哈希（SHA-256）

```text
6b33a2df82bca560cfa3dd714ecd895c6c9125bed98da1744f253c2f123d0d0c  analyze.py
569cfc1bd1f4a7e1c1b902b3a4fc965d635fe654332cd13a2235d451db866d2c  make_deliverables.py
1ff18850d2fcf1e853a4dc0bee0ecf7066548c3ca653805340b370847bd890de  make_manifest.py
ff8367f1597e1eefbea27ccba39f13291613f8f67ea1e37d6c8280a51eb3e6d3  locate_inputs.py
2769458d87aa7868bff8010fb47e24ca7a483c8cb5458c11062a0f49abe8860c  config.json
5e985f1a5ab6ccfaf214c44e173e812dfccd1b0b23ab53b688f1fe208648e1ad  PORTABILITY.md
166180ab92d093784fe387c6cf6f98f24107a3ae9af30a273f6414a1f4c35a26  report.md
dd198167ef3410332752d0b6661739d329c8519ede448720f649808c5a3c0135  results.json
3d479f012d11d67a11167683ae41a11b2f3a6e3e830ebc95cc4e19a0fd5761d0  manuscript_insert.md
b336a2c2f7bb1fd79c54c2f793192be202a13603209142ae16241349edaa796e  contribution_reframing.md
7ce693fc4139fcb6b68948066b4969c30d41986b5dd34dc202e52da0b5724d76  mdp_protocol_card.md
ff4ec47d8523bb4535f6db3b179a529d8000d8f4e078c923de3cb9591adba13d  minimum_reporting_checklist.md
a72c83f641681b369c618dd5800adf8b32c16ab09819c65d211c990a835fe9e0  integration_plan.md
5ad68289a0a8967d25a36de899dcda26f0b501f644ae5ffd01894d6a54e0b053  validation.md
e830e67802ae1e017c20c4ce87da616ebf80329710f8b9b278fe4d47faca130d  defense_qa.md
489ecc614265d43a3104a669c21bb3fa955bc882068c884edfeb1b1a2d8c8c53  table3_16_spearman.csv
8fca5147be695934ed8efc4408a68ceff0d99203609c2ed4eed0a24076b3ce85  tableA2_rank_stability.csv
ec12536dc3f40ec6ca1a19a43ab76a08a6cae25296b6bcbd00db6c7e10f2e492  table2x2.csv
0158175977de715eebbfcc7c35b0e3c8af262544469218b182bb48180c78fd7d  table_gate_per_seed.csv
5d06c43ee2f91b2c0bd778fcf08ba0f18102c512ce30ac299d13cbe0069b361b  fig_rank_stability_by_metric.png
5cb07aa973047f22a4d3ab002f826e4f84de50fb2639f389521a99fe726c575b  fig_rank_slope.png
a84bd034c07c7cad404f6751ba7a405e86ad259736a5a28e21e3c20a9a5d55e4  fig_ranking_scatter.png
c201351bb24e365d784b259aa85d6572b879cfc39757060390588e9a95a56cde  fig_gate_label_sensitivity.png
e6c3b41aa96450c8820542d9bb5029ff2f57e3a95bb7a3851d9875508e4639a6  fig_label_diff_hist.png
f5ef3d59050f03e01208c06bdc9d2abe6b3857dbf20d4ee790d9e342a40f6ced  fig3_17_proxy_rank_stability_candidate.png
98dbd75f56df6e5e0b67f98f870b6d09d0c1f3c42391015de3ea77825969c848  fig3_17_proxy_rank_stability_candidate.svg
```

`README.md` 与 `manifest.json` 不在此块：`manifest.json` 会在最后重建，并记录 README 的哈希。

## 边界与不主张

- 只覆盖 Caltech 事件时刻协议；JPL 未做同键标签敏感性分析。
- 只比较两种会话分配规则（均匀、完成时刻截断），不是实测功率。
- 测试期已查看；这是固定时期的标签敏感性分析，不是未见时期验证。
- 事件掩码沿用冻结 `target_event`，不随截断目标重建。
- 不改变主结果、锁定主张、已有表格数值或结论排序。
- 不声称代理标签等于实测功率，也不声称现场收益。
- 708,560 个预测键含重叠目标，不作为独立统计样本。
- 不替代训练源码身份核验、检查点加载、GPU 推理复现或 Word/PDF 全页验收；本包只复算已有预测指标。

## 当前工作流状态

`ACN-PRACTICE-20261025` 仍是 `scope_violation` / `pending_codex_review`。本包没有改论文；先让 Codex 收口当前任务，再按 `integration_plan.md` 逐项开新任务。不要在当前脏工作树上直接开第二个写任务。
