# 并入论文的交接计划（给 Codex）

## 当前状态

- `ACN-PRACTICE-20261025` 仍是 `scope_violation` / `pending_codex_review`。
- 工作树已有未提交改动；项目规则禁止同时开第二个写任务。
- 因此本包**不直接改论文**，只提供可直接并入的正文、表、图、协议卡和任务建议。
- 先让 Codex 收口当前任务；接受后再按下面顺序逐项开新任务。

## Codex 复核修正（R1–R5，入稿前置）

- **R1 门控**：三种子平均 2.69%→1.65%，但截断标签下 seed-2024 由 +1.73% 变为 −0.91%，发生反转；必须披露，不能写“方向不变/各次一致”。
- **R2 范围与统计量**：0.993 是“三种子平均 MAE 排序的 Spearman”（`rho_of_seed_mean_mae_ranks`：先对每种配置的三种子 MAE 取平均，再对 12 个配置排序），不是逐种子相关的平均（`mean_of_seed_rhos`，全局为 0.974）；非零 0.420 vs 逐种子均值 0.000 同理。逐种子为 0.972/0.972/0.979；非零（评价标签）逐种子 −0.112/0.098/0.014；不设 0.9/0.6 通过阈值。0.993 的适用范围仍限于 12 个配置、两套代理标签、已查看 Caltech 测试期。
- **R3 区间**：两套代理标签差异与 5.3 节区间宽度统计集合不同，不能推断实测覆盖；只能写“未针对同步实测值验证”。
- **R4 贡献**：区分关系组件价值（JPL 自环替换：负荷 1.82%、轮廓 1.52%；负荷关系非零组为未校正探索性证据）与完整模型未胜 TCN；不得写“增量不延伸至非零组”。
- **R5 网站/材料**：认证状态与数据更新须绑定日期、站点和请求格式；未认证查询不等于源端零记录；公开资料含电流时序，不能概括为“只有会话起止和总电量”。

## 建议任务顺序

### 任务 1：`REV-20261026-PROXY-STABILITY`

- 类型：`content_revision`；阶段 11。
- 目标：在 3.8.4 之后新增 3.8.5“代理标签的排序敏感性”，加入表 3-16、图 3-17、附表 A-2。
- 可写路径：`docs/thesis/thesis-manuscript.md`。
- 直接证据：
  - `~/acn_proxy_stability_20261026/manuscript_insert.md`
  - `~/acn_proxy_stability_20261026/report.md`
  - `~/acn_proxy_stability_20261026/results.json`
  - `~/acn_proxy_stability_20261026/fig3_17_proxy_rank_stability_candidate.png`
  - `~/acn_proxy_stability_20261026/fig3_17_proxy_rank_stability_candidate.svg`
  - `~/acn_proxy_stability_20261026/table3_16_spearman.csv`
  - `~/acn_proxy_stability_20261026/tableA2_rank_stability.csv`
  - `~/acn_proxy_stability_20261026/table2x2.csv`
  - 既有冻结预测与数据集（只读，不复制原始会话）：
    - `outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz`
    - `outputs/experiments/SG-EXP-032/frozen-contract/dataset.npz`
    - `outputs/recovered/SG-EXP-019/unpacked/results/formal/`
    - `outputs/experiments/SG-EXP-027/recovered/formal/`
- 检查：`git diff --check -- docs/thesis/thesis-manuscript.md`。
- 权限：训练 false；联网 false；Git 提交 false。
- 验收要点：
  - 只改 3.8.5、表 3-16、图 3-17、附表 A-2 及必要的交叉引用。
  - 不改主结果、锁定主张、已有表格数值或结论排序。
  - 明确“固定测试期、代理标签、非实测功率、非未见时期”。
  - 表号/图号连续；若放 5.4.6，需把 5.5 表 5-10 顺延为 5-11（不推荐）。
  - 必须写入 seed-2024 门控反转（+1.73%→−0.91%）；不得写“方向不变”。
  - 表 3-16 的表头必须写“三种子平均 MAE 排序的 Spearman（先平均 MAE 再排序）”；CSV 字段使用 `rho_of_seed_mean_mae_ranks`，另列 `mean_of_seed_rhos`；不得使用 0.9/0.6“稳定/中等/不稳定”阈值。
  - 表 3-16 同时给三种子平均、逐种子范围和逐种子相关均值；注明 0.993 与 0.974、0.420 与 0.000 不是同一个统计量。
  - 图 3-17 的 A 面板标题/图注必须写明“先平均 MAE 再排序”，并注明逐种子相关均值为 0.974。
  - 全局排序结论限定为“12 配置、两套标签、已查看 Caltech 测试期”；不得写“全局 MAE 可用于所有模型筛选”。
  - 不得以两套代理标签差异推断实测覆盖；只能写“未针对同步实测值验证”。

### 任务 2：`REV-20261026-CONTRIBUTION-REFRAME`

- 类型：`content_revision`；阶段 11。
- 目标：把摘要、1.3/1.4、3.8.1 引导段、4.5、结论的贡献叙事从“提出 MRG-GCN”改为“三类可复核证据”。
- 可写路径：`docs/thesis/thesis-manuscript.md`。
- 直接证据：`~/acn_proxy_stability_20261026/contribution_reframing.md`。
- 检查：`git diff --check -- docs/thesis/thesis-manuscript.md`。
- 权限：训练 false；联网 false；Git 提交 false。
- 验收要点：不新增数字、实验、引用或主张；只改贡献表述；保留“不主张算法首创”的边界。

### 任务 3：`REV-20261026-MDP-PROTOCOL`

- 类型：`content_revision`；阶段 11。
- 目标：把 4.5 的三层诊断整理为可复用协议卡，并在 3.8 或附录加入最小报告清单。
- 可写路径：`docs/thesis/thesis-manuscript.md`。
- 直接证据：
  - `~/acn_proxy_stability_20261026/mdp_protocol_card.md`
  - `~/acn_proxy_stability_20261026/minimum_reporting_checklist.md`
- 检查：`git diff --check -- docs/thesis/thesis-manuscript.md`。
- 权限：训练 false；联网 false；Git 提交 false。
- 验收要点：不新增实验或数字；协议卡只组织已有操作；清单是报告规范，不是新评分表。

### 任务 4（可选）：`REV-20261026-INTERVAL-BOUNDARY`

- 类型：`content_revision`；阶段 11。
- 目标：在 5.4.5 补一句边界声明：“本文未针对同步实测值校准或评价区间；现有覆盖结果仅针对所定义的代理标签。”
- 可写路径：`docs/thesis/thesis-manuscript.md`。
- 直接证据：`~/acn_proxy_stability_20261026/manuscript_insert.md` 的“可选的 5.4.5 边界声明”与 `report.md` 的对应小节。
- 检查：`git diff --check -- docs/thesis/thesis-manuscript.md`。
- 权限：训练 false；联网 false；Git 提交 false。
- 验收要点：只使用已有表述；不新增图表；不得写“区间不能覆盖实测值”或“实测覆盖失败”；如要做覆盖评价，须以同键逐键区间实际重算，并明确仍是代理对代理的敏感性评价。

## 证据登记建议

- 把 `report.md`、`results.json`、`fig3_17_proxy_rank_stability_candidate.png/svg`、四张 CSV 表（含 `table_gate_per_seed.csv`）复制到 `outputs/analysis/SG-EXP-033-proxy-label-stability/`（或现有分析目录），生成 `manifest.json`，记录：
  - 输入预测/数据集路径与 SHA-256；
  - 脚本 `analyze.py` 的 SHA-256；
  - 输出文件的 SHA-256；
  - 运行日期、Python/NumPy/Matplotlib 版本；
  - 明确“只读现有预测，不训练、不联网、不保存原始会话”。
- 原始会话、检查点、凭据不进入 Git；预测文件是派生输出，可按项目既有规则登记。
- 当前包已把 50 个输入复制到 `inputs/`（48 份预测 + 2 份数据集），是可复算的本地包；迁移到其他机器时按 `config.json` / `PORTABILITY.md` 设置根目录并校验哈希。
- **路径配置验证**：四个入口（`analyze.py`、`make_deliverables.py`、`make_manifest.py`、`locate_inputs.py`）应以 `Path(__file__).resolve().parent` 定位包；`EVCS_PROJECT_ROOT` 或 `config.json` 的 `project_root` 必须真正生效。验证方式：把包复制到临时目录，或在项目根目录之外运行 `analyze.py`，确认读取包内 `inputs/` 且不硬编码家目录。
- **locate_inputs.py 的 skip 语义**：跳过已有文件时必须对照 `manifest.json` 的既有哈希；`skip=50` 只表示文件存在，不能单独表述为“完整性检查通过”。刷新时应保留原清单并逐项比对。
- 图 3-17 的候选文件是英文标签、PNG **1200 dpi** + SVG；已去掉无依据的 0.9 阈值线，右面板去掉纵轴标题、用排名前缀标注。图 A 标题/图注须写明“先平均 MAE 再排序”。若论文统一用中文，请按论文图样式重绘，图注可直接用 `manuscript_insert.md` 的版本。

## 当前不能做的事

| 事项 | 原因 | 处理 |
|---|---|---|
| Caltech 事件时刻关系自环替换（9 次训练） | 需要 GPU/训练预算；当前无新 blueprint；AutoDL 已关闭 | 列为后续任务，不在本轮硬做 |
| 容量匹配 AGCRN / 行为 GRU | 需要新训练；会改变模型比较范围 | 先由 Codex 评估预算与证据价值 |
| proxy-aware 共形区间 | 需要新实验与消融 | 作为后续方法扩展，不并入本轮 |
| 2021 后新时期数据 | 2026-10-25 查询中 ACN 认证接口故障；本地快照与年度下载显示止于 2021-09-14；静态镜像仅 2018–2020 | 在论文中保留数据边界，不等待；未认证查询不等于源端零记录 |
| Word/PDF 最终验收 | CDUT 模板 asset 缺失；无 pwsh/Word；LibreOffice 不等同 Word 定稿 | 不声称视觉验收通过；需恢复模板或换 Windows/Word 环境 |
| token 清理 | 用户明确排除 | 不做 |

## 关键口径

- 新增 3.8.5 是**标签敏感性分析**，不是实测功率验证，也不是未见时期验证。
- 它只使用已有冻结预测；不新增训练、不新增模型、不新增原始数据。
- 它支持“在 12 配置、两套标签、已查看 Caltech 测试期内，三种子平均 MAE 排序的 Spearman（`rho_of_seed_mean_mae_ranks`）0.993、逐种子相关均值 0.974，全局排序基本保持；非零/事件更敏感”的判断；不支持“代理等于实测”“所有模型筛选稳健”或“现场收益”。
- 种子层面相关低于三种子平均 MAE 排序相关（全局逐种子 0.972/0.972/0.979，逐种子均值 0.974；非零逐种子 −0.112/0.098/0.014，逐种子均值 0.000），不能笼统称“排序稳健”，也不能把 0.993 与 0.974 混称。
- 若审稿人问“为什么非零结论和之前不同”，回答：非零子集的定义（评价标签 vs 固定均匀键）不同；本文现在并列报告两种定义，不把单一非零数字当稳健结论。关系组件价值与完整模型未胜 TCN 仍分开陈述。

## 最小验收清单

- [ ] 3.8.5 的文字与 `manuscript_insert.md` 数字一致。
- [ ] 表 3-16 的 6 行同时给出“三种子平均 MAE 排序的 Spearman（先平均 MAE 再排序）”、逐种子范围、逐种子相关均值；CSV 字段为 `rho_of_seed_mean_mae_ranks` 与 `mean_of_seed_rhos`；未使用 0.9/0.6 阈值。
- [ ] 图 3-17 的数值与表 3-16 一致；A 面板标题/图注写明“先平均 MAE 再排序”；PNG 为 1200 dpi，无 0.9 阈值线。
- [ ] 附表 A-2 的 12 行排名与 `results.json` 一致。
- [ ] 明确固定测试期、代理标签、非实测功率、非未见时期。
- [ ] 披露 seed-2024 门控反转（+1.73%→−0.91%）。
- [ ] 不把全局排序结论写成“所有模型筛选稳健”；注明 0.993 与 0.974、0.420 与 0.000 不是同一个统计量。
- [ ] 不以两套代理标签差异推断实测覆盖；写“未针对同步实测值验证”。
- [ ] 关系组件价值与完整模型未胜 TCN 分开陈述。
- [ ] `analyze.py` 等入口以 `Path(__file__).resolve().parent` 定位包；`EVCS_PROJECT_ROOT`/`config.json` 生效；在非家目录路径运行通过。
- [ ] `locate_inputs.py` 输出 `skip_verified`（不是 `skip`）；`skip=50` 不作为完整性通过证据，跳过前已对照 manifest 哈希。
- [ ] 未改主结果、锁定主张、已有表格数值或结论排序。
- [ ] `git diff --check` 通过。
- [ ] 证据 manifest 记录输入/输出/脚本 SHA-256。
