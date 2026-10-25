# Claude Code执行任务包

任务编号：REV-20261022-EVIDENCE-PACKAGE-EPFL
任务类型：evidence_audit；对应12流程阶段：12-step workflow: evidence consolidation, provenance, external data check, manuscript handoff
目标：Create a minimal reproducible evidence package for SG-EXP-031/032 and complete a bounded exploratory EPFL measured-power shape audit with a link key independent of session Energy. Save code, protocol, machine-readable summaries, checksums, and exact replay commands; update the current evidence console and data availability decisions without promoting unsupported model or application claims.

## 开始前
只依据本任务包的冻结摘录和蓝图列出的材料工作。不要从聊天历史、归档计划或整份实验登记表重建当前状态。正文源稿为`docs/thesis/thesis-manuscript.md`。

## 可写范围
- `scripts/replay_sgexp031_032_evidence.py`
- `scripts/audit_epfl_proxy_shape_v2.py`
- `docs/thesis/revision-20261022-evidence/reproducibility-package.md`
- `docs/thesis/revision-20261022-evidence/reproducibility-package.json`
- `docs/thesis/revision-20261022-evidence/epfl-proxy-audit-v2-protocol.md`
- `docs/thesis/revision-20261022-evidence/epfl-proxy-audit-v2.json`
- `docs/thesis/revision-20261022-evidence/targeted-data-search.md`
- `docs/thesis/data-availability.md`
- `docs/thesis/claim-evidence-map.md`
- `docs/thesis/revision-20261021-evidence/data-source-compatibility.md`
- 以上路径是任务约束和事后审计范围，不是操作系统级文件隔离；不要写入未列路径，也不要把Git忽略路径当作可审计输出。

## 锁定主张与口径
- Do not describe SG-EXP-031 or SG-EXP-032 as untouched confirmation; both use already viewed fixed test periods.
- SG-EXP-031 source identity is its frozen bundle hashes plus recorded Git baseline; the entrypoint was untracked and the working-tree patch was empty. SG-EXP-032 has no verified historical Git commit. Do not invent stronger Git provenance.
- The 031/032 source and result archives already contain actual code, configs, environments, checkpoints, predictions and file manifests. Build a lightweight index and replay command; do not duplicate large archives, raw sessions, predictions or weights into Git.
- The replay entry verifies archived source/result contents and independently recomputes metrics from saved predictions. It must explicitly say it does not perform checkpoint forward inference or retraining.
- Preserve the V1 EPFL protocol as historical. V2 is exploratory because the key repair and energy mismatch were examined after V1 stopped.
- Join EPFL sessions and measurements only by (CCS, Arrival, Departure); do not use Energy in the key. Require one-to-one links and complete one-minute coverage for each included session, and report all exclusions before summarizing shape.
- Separate amplitude/energy closure from temporal shape. Record P-integral/session-Energy and cumulative-Energy-delta/session-Energy diagnostics. Because the source does not resolve P meter boundary or timestamp semantics, a normalized shape comparison may be reported only as exploratory; never call it calibration, ACN target error, model validation, or operational benefit.
- Use per-session 15-minute bins on the workbook's naive wall-clock timestamps, integrate P in W by trapezoids, distribute session Energy uniformly by overlap over Arrival-to-Departure, normalize both vectors, and report total-variation distance with equal-session median, IQR and mean. Do not label timestamps UTC or confirmed DST.
- EPFL README reports a 172.5 kW station limit, at most two concurrent EVs, a sharing rule, and P/Pset/Preq fields. Correct any statement that no real operating constraint information exists; state that aligned node/time inputs and a complete causal replay contract are missing.
- Existing bounded data checks found no ACN/API period outside the recorded 2021 bounds; KIT and EPFL support only measured-shape exploration, Scotland has no verified sampled power series, and Sydney remains unverified. Do not continue broad dataset search or claim a compatible unseen ACN period.

## 执行步骤
1. Inspect the existing archive and run manifests without changing historical runs. Create a lightweight reproducibility package index with exact paths, sizes, SHA-256 values, internal manifest coverage, source/config/environment/checkpoint/prediction inventory, privacy/access notes, known Git identity limits, and one command that verifies archives and reruns the existing independent SG-EXP-031/032 saved-prediction metric audits into a new output directory. The command must refuse to overwrite non-empty output and must not train or run model forward inference.
2. Create an append-only exploratory V2 protocol before calculating EPFL shape metrics. State the no-Energy join key, exact inclusion/exclusion checks, 15-minute binning/integration rules, amplitude diagnostics, normalized total-variation shape metric, summary statistics, and interpretation limits. Preserve the frozen V1 protocol unchanged.
3. Implement a concise deterministic script that reads the two local ignored EPFL workbooks, validates file hashes and sheet/field structure, joins on (CCS, Arrival, Departure), checks one-to-one mapping and measurement coverage, computes energy-closure diagnostics separately, then computes normalized shape only for sessions meeting the frozen V2 checks. Save only aggregate machine-readable output and exclusion counts; never save raw session rows or new row-level tables.
4. Run the two requested replay/audit entrypoints listed in checks_to_run. If a declared prerequisite fails, stop shape computation, retain the diagnostic, and record the exact blocker rather than relaxing the protocol.
5. Write a bounded data-search note using the existing ACN boundary probe and the current official-source checks for EPFL, KIT, ChargePlace Scotland and Sydney. State that no directly compatible unseen ACN checkpoint period was found and stop general search.
6. Update only the active sections of data-availability.md, data-source-compatibility.md and claim-evidence-map.md: link to the new evidence, correct the claim about real capacity/control material, preserve all historical text and V1 outcome, and do not edit thesis-manuscript.md or DOCX in this evidence phase.
7. Return execution-report.json with exact changed files, commands and checks, report model, archive/workbook hashes, shape-audit status, and unresolved semantic limits. Keep task pending Codex review.

## 指定Claude Code Skills
- 本任务未指定Claude Code专用skill；如需技能支持，先在报告中说明阻塞，不要假定Codex全局skill已自动安装到Claude Code。

## 验收条件
- The reproducibility package points to the existing actual SG-EXP-031/032 source and result archives, verifies archive and internal run-manifest hashes, inventories environment/config/checkpoint/prediction artifacts, and provides one non-destructive saved-prediction audit command.
- The replay command completes from the current local archive state and reports per-experiment audit status and exact hashes. It clearly distinguishes metric recomputation from checkpoint forward replay and training reconstruction.
- EPFL V2 performs no-Energy one-to-one joining, checks full per-session sampling/coverage and energy diagnostics, and reports normalized profile-shape statistics only if all predeclared shape eligibility conditions pass.
- EPFL script output contains aggregate values and exclusion counts only, not raw records; source workbooks remain local and ignored.
- All shape results are marked exploratory; amplitude closure, source-defined P/Energy ambiguity, naive timestamp semantics, and lack of ACN node compatibility remain explicit.
- Targeted data search has a fixed stopping conclusion and does not claim a genuinely compatible unseen model test period exists.
- The current evidence console corrects the overbroad absence-of-constraints wording while preserving the distinction between partial EPFL operating context and a valid causal dispatch replay.
- Only explicitly allowed paths change; no manuscript, DOCX, figures, training outputs, raw workbooks, or historical V1 protocol changes. No training, network requests, Git mutations, or tests occur.

## 操作权限
- 训练：False；远程执行：False；联网：False；Git提交/暂存：False。
- 除非明确列入允许范围，不得启动训练、远程作业、联网采集、Git暂存/提交或覆盖正式Word。不得使用绕过权限的启动方式。
- 不得修改`.git/`、`.claude/settings*.json`、凭据文件或交接控制文件；如需修改，停止并报告。
- 只运行蓝图列出的检查：python3 scripts/replay_sgexp031_032_evidence.py --out docs/thesis/revision-20261022-evidence/reproducibility-package.json, python3 scripts/audit_epfl_proxy_shape_v2.py --session data/external/epfl-l3-20261021/Session_data.xlsx --measurements data/external/epfl-l3-20261021/Measurement_data.xlsx --out docs/thesis/revision-20261022-evidence/epfl-proxy-audit-v2.json。未列检查时不要新增或运行测试。
- Bash网络主机白名单：无。空数组表示Bash无网络；WebSearch/WebFetch须单独取得工具权限。

## 冻结的证据摘录

### 证据控制台

#### docs/thesis/claim-evidence-map.md — Preserve current claim hierarchy and limits; update only the current EPFL/source-chain entries.
定位：`{"kind": "markdown_heading", "value": "论文核心结论权限"}`；来源SHA-256：`f635b256baa8fd81269973abc72e5e592f4d25a4b96d38e3cf4b295151c6f85e`
```text
### 论文核心结论权限

| 结论层级 | 当前证据 | 正文可作的判断 | 不支持的外推 |
|---|---|---|---|
| 主要模型比较 | Caltech事件时刻协议、JPL重新拟合；整体与分层MAE/RMSE | MRG-GCN在所检协议下有整体MAE优势；该优势没有稳定延伸至非零目标和标签事件组 | 活跃充电预测全面领先、跨数据家族泛化或实测功率预测 |
| 节点门控增量 | Caltech与JPL同参数共享门控对照，各有一个共享门控种子触及60轮上限 | 当前预算及选模规则下，节点级门控的整体MAE较低 | 更长预算下仍占优或跨时期普遍成立 |
| 关系增量 | SG-EXP-031 JPL同参数自环替换：负荷与轮廓关系的整体差异区间为正；行为关系区间跨零 | 负荷与轮廓关系在本架构、协议和预算下有条件性整体增量证据；行为关系仍不确定 | 三类关系均不可替代或对其他站点同样有效 |
| 非零组关系结果 | 031已查看测试期上的事后分层；负荷关系相对自环的非零组差为正，未作多重校正 | 可作探索性组件分层描述 | 完整MRG-GCN胜过TCN；确认性或多重校正后的非零组结论 |
| 目标敏感性 | SG-EXP-032固定原图与测试键，仅更换完成时刻截断代理目标 | 全局MAE排序在该替代目标下保持；非零组仍未优于TCN | 实测功率效度、替代目标重建图后的端到端稳健性 |
| MDP诊断 | L1联合参数敏感度、L2受检学生蒸馏、L3四格误差还原及JPL复核 | 修订关系权重解释、学生替代结论和指标报告重点 | 诊断指导改模已提高预测或运行收益 |
| 应用价值 | 固定代理轨迹、合成LP核验；真实案例状态为`MATERIALS_REQUIRED` | 界定采数、校准、离线评价和影子运行步骤 | 真实越限、安全改善、成本节约或直接调度能力 |

SG-EXP-031/032及JPL后续诊断均使用已查看的固定测试期，属于事后补充证据；不作为独立时期确认。全文据此区分总体模型比较、组件内增量、探索性分层与未验证的现场主张。

EPFL Level-3数据兼容性筛选（2026-10-21）只记录筛选失败和V1停止：严格`CCS + Session`连接为CCS1 1,129/1,129、CCS2 0/749，未进入形态比较；事后复合键1,878/1,878唯一匹配仅作映射诊断，含Energy，不是独立能量闭合。该筛选不新增模型、目标效度或应用主张，不改变上表结论层级；详见`revision-20261021-evidence/data-source-compatibility.md`。

- AdaptiveGraph：SG-EXP-004三个冻结检查点在匹配PyTorch 2.4.1/CUDA 12.1环境逐键通过；原生CPU存在top-k并列选边差异，固定CUDA邻接后CPU通过。原训练Git标识缺失、历史Mac环境偏差仍保留。报告：`experiment-reports/EXP-AdaptiveGraph-CUDA-20261015-no-training.md`及`outputs/analysis/AdaptiveGraph-CUDA-20261015/independent-verification.json`。
- SG-EXP-031：四配置×三种子同参数关系自环替换重训，支持负荷耦合和轮廓相似关系在当前JPL设置下的条件性整体MAE增量，行为共现关系区间跨零。审计中的次要分层显示，负荷关系相对自环的非零组种子平均差为0.004893 kWh/15 min，三个种子方向均为正；这是已查看测试期上的事后描述，未作该分层的多重校正，不等同完整模型胜过TCN（JPL非零组仍是TCN较低）。正文§3.7.2、表3-10；输入/容量/预算见表3-14。报告：`experiment-reports/SG-EXP-031-jpl-relation-controls.md`，数值见`outputs/analysis/SG-EXP-031-audit-20261015/audit.json`及`content-review-20261016-paired-reaudit/load-nonzero-crosscheck.json`。
- SG-EXP-032：完成时刻截断代理目标下全局MAE排序保持；新目标零值94.27%，非零组MRG-GCN较差。正文§3.8.4、表3-15；两种分层是边际评价，未作联合贡献分解。两项新训练均为已查看固定测试期上的补充。
- JPL可靠性：AUDIT-JPL-CAL-20261015复用313,120校准键与632,640测试键，标准/行为分层整体覆盖90.08%/90.11%，事件46.43%/45.88%，独立核验PASS。正文§5.3.5；报告`experiment-reports/EXP-JPL-calibration-20261015-no-training.md`。JPL尚缺L2与同硬件时延。
- AutoDL当前关闭状态以SG-EXP-032的控制台关机证据为准。SG-EXP-031结束时在线为历史事实，不作为当前实例状态；材料已回收并核验。

```

#### docs/thesis/data-availability.md — Update the active data-availability decision and correct the overbroad application-material statement.
定位：`{"kind": "markdown_heading", "value": "当前证据状态（2026-10-21未查看数据兼容性更新）"}`；来源SHA-256：`41d4172093b43b9c4843dcd0b246cbf6a34b1531e14f24e3ef74ab733729f468`
```text
## 当前证据状态（2026-10-21未查看数据兼容性更新）

本节为当前入口；下方按日期保留的历史失败、预检和待办状态仅代表当时情况。正文表号以当前主稿为准。

### ACN接口边界核验（2026-10-19）

- ACN三站点会话元数据接口的`connectionTime`边界已独立核验（2026-10-19）：Caltech 31,424条，最早/最晚为2018-04-25 11:08:04 / 2021-09-14 01:52:37 UTC；JPL 33,638条，2018-09-05 11:04:13 / 2021-09-14 05:43:39 UTC；Office 1 1,683条，2019-03-25 16:24:42 / 2021-09-13 21:21:51 UTC。对每站分别执行严格低于下界和严格高于上界的`where`查询，6次均返回HTTP 200且匹配数为0，未发现2021年9月之后的接入时间记录。原脚本`earliest`/`latest`标签相对返回时间戳颠倒，已在`range_probe_reviewed.json`按时间顺序订正并留痕。
- 该核验只确认`connectionTime`极值，不构成完整新数据快照，也不证明其他数据源不可得；尚未核查各站点的节点标识、字段完整性、标签兼容性和既有分析使用史，未下载会话时序。Office 1仍为候选站点，1,683条会话不构成其可运行性、跨站性能或零样本迁移证据。普通元数据端点返回的payload曾在内存中处理，但未保存或展示用户记录；凭据未保存。
- 本轮证据文件：`revision-20261019-nontraining/evidence/acn/range_probe_reviewed.json`（SHA-256 `84ec68aaf9c9d8b35acb928821a289464a5f66fbb4f946cdb754044b59055ae6`）、`bounds_verification.json`（`430bb7fffbbf62dd5ef92f4099a6ff455dda3362de195d273d36df02fa260b05`）、`provenance.json`（`6089bdc07aee0ba0967606567bb4866f30f2517775791e912f967ad307bae431`）。来源、6个`where`计数和标签订正详见`revision-20261019-nontraining/data-decision.md`。

### 未查看数据候选兼容性（2026-10-21）

论文已查看期：当前主稿的ACN训练、验证与测试均结束于2021-09-14；Caltech测试段为2021-03-12至2021-09-14，JPL测试期同样属于ACN历史段。以下“未查看”只表示该时期未进入现有实验，不表示存在可直接冻结推理的新时期。

- KIT低频单车充电测量（DOI `10.5281/zenodo.17866847`）：数据期为2025-10-28至2025-12-02，KIT校园测量点，18组测量、16辆车、12个品牌；KITopen记录列明CC BY 4.0，Zenodo API列出`cc-by-4.0`。可核实字段包括`charging_uuid`、时间戳、三相实测电压/电流、由电压电流计算的三相有功功率、SoC和设定电流；元数据表含日期、品牌/车型及可用时的电池容量。无ACN式接入、充电完成、断开时间和总交付电量标签。每组为单一测量点，不含ACN的10个EVSE节点ID、相同节点顺序、站内关系图或可重建的同口径输入张量；数据期与论文测试期不重叠。当前判定：只可作有限的实测曲线形态审计，不是ACN节点兼容的未查看模型测试期，不兼容既有冻结检查点，不验证论文目标标签、预测性能、计量校准或运行收益。曲线形态审计状态为`COMPUTED`，尚待Codex最终复核；本轮不将其摘要数值（包括时间覆盖率）写入正文。
- ChargePlace Scotland会话数据（DOI `10.15129/1f431af7-5caa-4840-a9ab-c1f3b521e033`）：2022-10-01至2024-03-31，苏格兰公共ChargePlace Scotland网络。记录页说明含会话开始、充电点ID、会话时长、消耗电量、地方行政区、邮编、充电速度和支付金额，不含按时间采样的实测功率曲线。与ACN站点/节点ID不同，记录介绍未提供与论文10个节点的交叉表、三类站内关系图或相同张量；会话耗能可重新构造成另一代理目标，但不是本文完成时刻/断开规则数据。当前判定：日期上属于论文未查看时期，但字段和节点语义不支持现有冻结检查点直接推理；若要验证须另行定义站点/节点、关系图、标签和训练流程。本轮未下载数据文件、未训练。
- 悉尼路侧充电候选：2025-09至2026-02，独立公共网络。当前页面显示受限访问；字段字典、功率时序和数据许可尚未取得。无法核验站点节点、标签及与论文历史使用的关系。当前判定：可得性与兼容性均未知，不能计为可用未查看期段；受限访问只表示当前不可读，不能据此断言数据不存在。
- EPFL-DESL Level-3会话与逐分钟测量数据（来源仓库提交`680bc3bb751f86a47db32a5641f09dcfa079caae`，MIT License；原始工作簿仅保存在Git忽略的`data/external/epfl-l3-20261021/`）：记录采集期为2022-04-12至2023-07-04，站点仅CCS1、CCS2两个被测直流快充端口。本地结构抽查得到1,878条会话行、1,878个测量组。冻结V1按`CCS + Session`严格连接时，CCS1为1,129/1,129、CCS2为0/749，故V1在形态比较前停止；不报告15 min代理与实测功率的形态差异、代理标签校准、ACN模型评价或目标效度结论。事后复合键（CCS、Arrival、Departure、会话Energy）虽唯一匹配1,878/1,878，但属探索性映射诊断，且Energy是键的一部分，不构成独立能量闭合，也未用于产生形态结果。工作簿时间戳为无时区值；文件级序列分别出现2022-10-30 02:59→02:00（−59 min）和2023-03-26 01:59→03:00（+61 min）的跳变，逐会话轨迹均为一分钟规则且无会话跨越跳变；这只记为文件时间限制，不断言UTC或把跳变解释为已确认时区。该数据没有ACN固定十节点映射、站内关系图或96×10×7输入契约，不能作为冻结检查点的兼容未查看期段，也不支持新的模型或应用主张。四个文件SHA-256及完整筛选口径见`revision-20261021-evidence/data-source-compatibility.md`和`epfl-proxy-audit-protocol.md`。
- 以上候选（含EPFL两端口实测功率筛选）均不改变现有冻结推理结论：没有与ACN十节点映射同步的站级电表功率、物理EVSE映射、真实站容量/馈线限额、车辆截止时间与需求、电价序列及同时间基线负荷；`SG-EXP-026`继续标记为合成案例，不升级为应用验证。ACN边界结论仅限已查REST API的`connectionTime`和6个HTTP 200区间外计数为0，不扩展到其他数据源不可得。

```

#### docs/thesis/revision-20261021-evidence/data-source-compatibility.md — Keep V1 history intact and append the bounded V2 outcome and data-source search.
定位：`{"kind": "markdown_heading", "value": "EPFL Level-3数据兼容性筛选（2026-10-21）"}`；来源SHA-256：`1e665a2dfec1657f085998f8b08a13822a25816a23b5d1610a8282f9673935bf`
```text
## EPFL Level-3数据兼容性筛选（2026-10-21）

来源身份：Git提交`680bc3bb751f86a47db32a5641f09dcfa079caae`，MIT License。原始工作簿只保存在Git忽略的`data/external/epfl-l3-20261021/`，不进入仓库，也不复制原始数据或逐会话行。来源仓库：[EPFL-DESL Level-3-EV-charging-dataset](https://github.com/DESL-EPFL/Level-3-EV-charging-dataset)。

| 文件 | SHA-256 |
|---|---|
| `Session_data.xlsx` | `b886943bf86520f24f5a53870886c4c43709d265cbebdd65e1345321e22cc192` |
| `Measurement_data.xlsx` | `a0a489e2897ec79235ed914376ab7751ab21c68418543234a60042eaee73a89c` |
| `README.md` | `28daaa5b0d65872d09f95d9a0dd1e4490f6b79bfa2ea780f56b51e8a012c93be` |
| `LICENSE` | `4654a82938a437cf4ef3efbb9ed7cb7a7b95f8250db1e1444d22c6e22e9a9d8f` |

筛选结果（V1在连接阶段停止）：

- 记录采集期为2022-04-12至2023-07-04；站点仅CCS1、CCS2两个被测直流快充端口；工作簿结构抽查为1,878条会话行、1,878个测量组。
- 冻结V1按`CCS + Session`严格连接：CCS1为1,129/1,129，CCS2为0/749。CCS2在该键下无匹配，V1在形态比较前停止；因此不报告15 min代理与实测功率的形态差异、代理标签校准、ACN模型评价、目标效度、部署或调度收益。
- 事后复合键（CCS、Arrival、Departure、会话Energy）唯一匹配1,878/1,878；这是探索性映射诊断，只说明该键可对齐，Energy是键的一部分，不能当作独立能量闭合，也未用于产生任何形态结果。
- 工作簿时间戳为无时区值：文件级序列分别出现2022-10-30 02:59→02:00（−59 min）和2023-03-26 01:59→03:00（+61 min）的跳变；每个会话轨迹均为一分钟规则，且没有会话跨越这两处跳变。该项只记为文件时间限制，不断言UTC，也不把跳变解释为已确认时区（如DST）。
- 兼容性判定：只有两个被测CCS端口，缺少ACN固定十节点映射、三类站内关系图及96×10×7输入契约，不能作为冻结ACN检查点的兼容未查看期段，也不支持新的模型或应用主张。完整协议与结论门槛见`epfl-proxy-audit-protocol.md`。

```

### 直接证据

#### docs/thesis/revision-20261021-evidence/epfl-proxy-audit-protocol.md — Preserve the frozen V1 stop decision and explain why V2 must be labeled exploratory.
定位：`{"kind": "whole_file"}`；来源SHA-256：`745f3849444d9ed949e5a7253ef51b29f623b53103f9713eb74dd034309520d7`
```text
# EPFL 实测功率—会话代理目标外部审计协议

## 目的与证据等级

本审计只检验一件事：按“会话接入至离站期间均匀分配会话电量”构造的15 min代理负荷，能否保留另一实测场景中充电功率的时间形态。它不测试论文模型，不使用ACN十节点模型输入，也不评价调度收益。

数据来自EPFL-DESL瑞士Level-3站点，仅含CCS1、CCS2两个直流快充端口。仓库记录的数据采集期为2022-04-12至2023-07-04，原始工作簿在本地作一次结构抽查后才进入本审计；因此数据期未进入既有论文实验，但本审计是探索性外部验证，不称为盲态或预注册确认性验证。README/License来自Git提交`680bc3bb751f86a47db32a5641f09dcfa079caae`。本地原始工作簿只保存在Git忽略的`data/external/epfl-l3-20261021/`目录，不进入仓库提交。

## 冻结来源

| 文件 | SHA-256 | 来源 |
|---|---|---|
| `Session_data.xlsx` | `b886943bf86520f24f5a53870886c4c43709d265cbebdd65e1345321e22cc192` | [EPFL-DESL GitHub仓库](https://github.com/DESL-EPFL/Level-3-EV-charging-dataset) |
| `Measurement_data.xlsx` | `a0a489e2897ec79235ed914376ab7751ab21c68418543234a60042eaee73a89c` | 同上 |
| `README.md` | `28daaa5b0d65872d09f95d9a0dd1e4490f6b79bfa2ea780f56b51e8a012c93be` | 同上 |
| `LICENSE` | `4654a82938a437cf4ef3efbb9ed7cb7a7b95f8250db1e1444d22c6e22e9a9d8f` | 同上，MIT License |

## 核验顺序

1. 记录工作簿sheet、字段、行数、空值、时间范围、重复键及`CCS + Session`连接唯一性。不得把文件行数直接当成有效会话数。
2. 按`CCS + Session`连接会话表与逐分钟测量表。报告成功匹配、未匹配、重复、边界覆盖不足和被排除会话数及原因。
3. 以测量字段`P (W)`在相邻分钟时间戳之间作梯形积分，并按15 min本地时间片切分；同时用测量表累计`Energy (Wh)`的首末差和会话表`Energy (Wh)`作能量闭合检查。记录时区未由源字段明确的限制，不自行假定UTC。
4. 仅对时间戳单调、功率和能量有限、会话窗口测量覆盖充分且总能量为正的会话开展形态比较。覆盖门槛及完整排除清单须在计算前固定并写入脚本；不因结果大小改变门槛。
5. 将会话表`Energy (Wh)`按`Arrival`至`Departure`的分钟重叠比例均匀分到对应15 min片，得到本文代理目标的外部实现。与同一会话的实测15 min能量向量并列比较，并将幅值偏差与形状偏差分开：分别报告会话总能量的相对差；对各自归一化到单位总量的片级分布计算总变差距离`0.5 × Σ|p_measured - p_uniform|`。汇总中位数、四分位距、均值及有效样本数；如给区间，须按会话重采样并标注其仅描述本数据样本的不确定性。
6. 检查总体汇总是否被少数长会话/高能量会话主导；可同时给会话等权摘要与电量加权摘要，但不得用后者替代等权结果。所有单位、片边界、时间口径和分母写清楚。

## 结论权限

- 只有当功率积分、累计电量和会话标签的闭合情况足以支持比较时，才报告形态差异；不通过则记录失败和原因，不选择性删改阈值。
- 即使发现明显形态差异，也只能说明该外部站点、该类会话和当前重构规则下，均摊代理与实测功率的时间分布存在差别。不能量化为ACN主任务的“目标不确定度”，不能与论文MAE直接比较，不能推断模型预测质量或运行收益。
- 若数据缺少论文十节点ID、三关系图、行为七通道张量及兼容的目标定义，则冻结检查点不能对该数据作直接前向推理；本任务不得做此类推理或训练。
- 站点只有两个被测CCS端口，不能作为多节点、ACN Level-2、站级非充电基线或真实调度数据的替代证据。
- 只有Codex独立复核脚本、来源哈希、筛选流和计算输出后，才创建后续受限正文修订任务。当前协议本身不授权改写摘要或模型结果。

```

#### docs/thesis/revision-20261021-evidence/source-chain-summary.md — Use exact SG-EXP-031/032 source identity, artifact hashes, and Git provenance limits.
定位：`{"kind": "markdown_heading", "value": "训练来源链"}`；来源SHA-256：`f48432f62195b8b2b9505aa0c84ceec2fc819c486b4beefec53ac10cd170d26a`
```text
## 训练来源链

机器可读逐文件索引：[`training-source-chain.json`](training-source-chain.json)，SHA-256：`6f410fd7ee51d2e62f7e74f54af0e903a51edf803a778c50ef0d2685a83cb0dc`。本轮对冻结包、训练入口、每次运行的文件清单、最佳/末轮检查点及校准/测试预测重新计算哈希；两组均通过。

| 实验 | 数据/配置与源码身份 | 冻结包及训练结果 | 本轮重核 |
|---|---|---|---|
| SG-EXP-031 | JPL数据SHA `1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af`；入口`jpl_relation_controls.py` SHA `ac5f7a998ad198af30f07971f929b7abc43300e7aecb9e65e645d633920b9cba`；训练计划SHA `435be23f6a9ed824a24e872617fc75e78972b720da84d7603c438fa47a64c499`；训练代码包SHA `d40d609177089702c0799f106dbce19ce07e906f28410554506d74e1c39d0018` | 输入包67项；结果归档SHA `4eb436fbf30823d4df9b3e1be9f34652f849bdf7a130ce1c4229d9b2964f8c5f`；12次运行、每次632,640个测试键；逐键审计状态`POST_HOC_DIAGNOSTIC` | 输入清单67/67；恢复结果中12份运行清单、156个文件逐项通过；入口脚本与冻结包SHA一致 |
| SG-EXP-032 | 替代目标数据SHA `5802a65e2f7f0e045d54df3359eb52e9de73c5c6f4af06c67ada7db22747293f`；固定配置`config_frozen.json` SHA `a757218639584e723543e1d0dc412d12a1d57cd03ce8d9d61302aff012545b27`；入口`completion_target_sensitivity.py` SHA `6bb968944a4db08cb3458cf0dbdd4b07c192ce5c31cbcdefad44b9cb945ad753` | 训练包SHA `d53015b7de8150ad00efaa631449df57360c2987094c102e3f175561dee001df`；结果归档SHA `b6f73aeb350db65f1d25ee59c19bcf8b316270049f46aaeee59ff971947670b3`；6次运行、每次708,560个共同测试键；逐键审计`PASS` | 训练包91项文件清单逐项通过；6份运行清单、75个文件逐项通过；入口脚本与冻结包SHA一致 |

### Git身份边界

- SG-EXP-031冻结包记录的Git基线为`fce67da891d95ae5021942e3e34fb088c1a9fc2a`；包内`working-tree.patch`为0字节。训练入口当时没有被Git跟踪，但其完整内容在冻结包中按SHA-256识别，并与本地入口逐字节哈希相同。因此，Git提交只能标识基线，实际训练源码身份由冻结包逐文件清单补足；不能声称训练代码完全由该提交本身封存。
- SG-EXP-032冻结包未包含Git提交标识。入口脚本、配置、依赖源码、数据张量及每次运行文件均有冻结包/运行清单哈希；当前文件与包内入口一致。其源码可按文件哈希识别，但无法从现有材料追溯至确定的Git提交。
- 两项结果都使用已经查看的固定测试期，是事后补充证据；来源链完整不改变这一统计边界。

```

#### docs/thesis/experiment-reports/SG-EXP-031-jpl-relation-controls.md — Canonical SG-EXP-031 training contract, artifacts, results, and interpretation limits.
定位：`{"kind": "line_range", "start": 1, "end": 63}`；来源SHA-256：`d93dd099dbc4a55385fa4e3122323ca1c8ee5f4ddc205562ebc4fd69d57519d9`
````text
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

审计文件另含零目标/非零目标的次要分层，未作为三项预登记全局MAE比较。对“负荷耦合邻接→自环”而言，替换配置绝对误差减完整模型绝对误差的三种子平均差，非零组为0.004893 kWh/15 min、零目标组为0.000230 kWh/15 min；非零组的种子差均为正（0.005892、0.002579、0.006209）。该分解是已查看测试期上的探索性描述，未为该分层计算经多重校正的区间，不应表述为确认性非零组优势。它回答的是完整三关系配置相对同参数自环替代的组件问题；与完整MRG-GCN相对TCN的模型比较不同，后者在JPL非零组MAE仍较低，参见主稿表3-3。

以上区间反映已查看JPL固定测试期的时间块变异；它不估计场站抽样不确定性，也不包含完整的种子抽样不确定性。该结果不证明跨站点普遍性、未来期泛化、真实功率预测或现场运行收益。

## AutoDL状态

本地归档已回收并完成哈希与内容核验。远端summary中的`shutdown_status`仍为`pending_local_recovery`；AutoDL保持在线，**本次没有下达关机命令**，遵循用户“AutoDL是远程服务器，我不会关闭它”的说明。远端guardian状态文件仍为`armed`，但本轮未执行关机；不要据此声称AutoDL已自动关闭。

2026-10-15后续状态：本节上述在线/未关机记录对应031结束时。此后用户授权SG-EXP-032完成训练，结果回收核验后实例已关机；以SG-EXP-032/shutdown-evidence.json为当前控制台证据。
````

#### docs/thesis/experiment-reports/SG-EXP-032-completion-target-sensitivity.md — Canonical SG-EXP-032 training contract, artifacts, results, and interpretation limits.
定位：`{"kind": "line_range", "start": 1, "end": 57}`；来源SHA-256：`9585428a9501321944ba38efcfacaa3978d8c2514149c6eedfe0a46fd25b0f8a`
```text
# SG-EXP-032：完成时刻截断代理目标敏感性

日期：2026-10-15。状态：6组正式训练完成；远端归档、99项内层校验、逐键独立复算均通过；AutoDL控制台已确认目标实例关机。实验编号SG-EXP-032独立登记。目标是检验模型比较对“接入—断开均摊”代理标签改为“接入—有效充电完成时刻截断均摊”的敏感程度。

## 冻结的目标规则

复用SG-EXP-024已有的`alternative_reconstruction.npz`，并使用其中同一重构函数从原始会话表独立重建。仅当`connectionTime <= doneChargingTime <= disconnectTime`时以完成时刻为分摊终点；完成时刻缺失或不满足区间条件时，退回`disconnectTime`。每个会话的`kWhDelivered`仍守恒。此替代序列是由会话字段重构的代理标签，不是电表功率。

有效完成时刻会话10,399个，缺失420个，无效非空266个。替代重构把28,403.239 kWh移出完成时刻之后的片段。新旧标签总电量均为92,650.016936 kWh，最大节点总量差为4.91e-10 kWh；替代序列与SG-EXP-024原数组逐元素一致。全序列平均绝对标签差0.0477816 kWh/15 min仅描述两种重构定义的差异，不能解释成标签不确定度上限或模型误差基准。

## 训练前审计与固定项

数据源为SG-DATA-006 Caltech事件时刻协议，冻结数据SHA-256为`f663b510c75e203c8150f57c3765645f92b9a941e0745227c6ea078008a0dc8f`；SG-EXP-024替代包SHA-256为`a09c99c00fc1f6728f6bc276817b15f66fc1c8f646e929e2230c8782e6640b6f`。替代数组118,818个时间戳、10个节点及节点顺序均与冻结协议逐项一致。保留全部7通道行为/日历输入、事件与触发标签、图、split边界、起点和样本键；事件标签仍仅用于事后分组评价，不参与筛样、加权、训练、选模或种子选择。

每split的预测原点保持不变：train 83,099、tuning 8,803、calibration 8,805、test 17,714。每个原点按4个目标片、10个节点形成键；test共708,560个`(origin,horizon,node)`预测键。测试零目标比例从原目标的87.25%变为替代目标的94.27%；train/tuning/calibration替代目标零值比例分别85.56%、99.40%、96.89%。因此分层指标必须按协议分别报告，不能把标签零值组成变化当成模型改善。

SG-DATA-006关系图以成熟训练前缀构造。训练前将该图从原训练前缀逐位重建，结果与冻结图相同；本实验固定原图以隔离目标标签变化。该设计检验固定拓扑下的目标敏感性，不检验按替代标签重建拓扑后的端到端流程。新目标成熟前缀仍为83,198片；每个固定split原点窗口均通过替代标签成熟度检查。每节点目标均值和标准差仅在替代目标的该训练前缀重新计算。

比较模型为`mrg_full`与`tcn_wide`，可训练参数量分别32,714与32,674（差0.12%）。各模型使用种子2024/2025/2026，从头训练，AdamW、学习率0.001、weight decay 0.0001、batch 256、最多60轮、patience 8；以完整tuning集原单位MAE选best。精度为FP32确定性计算、TF32关闭。正式训练不缩减数据、轮数、种子或测试键。

## 合同和smoke证据

- 训练入口：`scripts/completion_target_sensitivity.py`；合同数据包：`outputs/experiments/SG-EXP-032/frozen-contract/`。
- CPU合同检查：`check`确认替代目标、固定输入/图/事件标签/起点键和预期参数量。
- 本地CPU smoke：1轮、32个train原点、16个tuning原点；MRG 32,714参数，loss及16×4×10预测均有限；没有导出calibration/test。
- 完整合同审计：`outputs/experiments/SG-EXP-032/frozen-contract/contract_audit.json`；训练入口SHA-256为`6bb968944a4db08cb3458cf0dbdd4b07c192ce5c31cbcdefad44b9cb945ad753`。远端CUDA smoke同样通过：AutoDL RTX4090 D，PyTorch 2.8.0+cu128、NumPy 2.3.2；1轮、32个train原点、16个tuning原点，有限预测且未导出calibration/test。环境快照见`outputs/experiments/SG-EXP-032/remote-preflight.txt`，smoke摘要见`outputs/experiments/SG-EXP-032/remote-cuda-smoke/`。训练完成后追加正式运行、逐键复算、归档SHA和控制面关机证据。
- 正式矩阵：`mrg_full`、`tcn_wide` × 种子2024/2025/2026；远程执行命令为`/root/miniconda3/bin/python scripts/completion_target_sensitivity.py all --device cuda --bundle outputs/experiments/SG-EXP-032/frozen-contract --out /root/autodl-tmp/SG-EXP-032/results/formal`。服务器为用户已启动的AutoDL实例，启动时RTX4090 D空闲、无其他训练进程；远端合同包SHA-256为`d53015b7de8150ad00efaa631449df57360c2987094c102e3f175561dee001df`（91项文件manifest通过）。正式训练日志与完整归档已回收；远端环境、进程和GPU预检见本地归档副本。正式运行均以exit marker 0结束，训练日志含6条完成记录且无Python traceback。

## 结果解释规则

主比较为共同测试键上`tcn_wide`绝对误差减`mrg_full`绝对误差，正值表示MRG-GCN较优。按三个种子逐键误差、固定测试期连续7日块报告配对区间；同时报告全局、零目标、非零目标及冻结事件标签分层MAE。新旧目标下的MAE只能作为各自任务中的模型比较，不得把两种目标的MAE差当作真实功率误差、也不得与0.0477816标签重构差直接排序。

本测试期曾用于既有SG-DATA-006分析，本实验是事后敏感性补充，不是盲测确认。即使模型排序在替代目标下保持，也只说明相对于本次替代代理构造具有一定稳健性，不能证明预测实测功率、现场收益或未来/新场站泛化。


## 正式训练与结果复算

六组训练均按冻结合同完成：`mrg_full`参数32,714，`tcn_wide`参数32,674（相差0.12%），种子均为2024/2025/2026；每组使用全部合同训练数据，最大60轮、patience 8，未缩减轮数或种子。实际最佳轮/停止轮分别为MRG 16/24、12/20、14/22；TCN 6/14、12/20、4/12。六组训练日志累计约2,214.83秒（36.9分钟）。

本地独立审计重新计算了全部预测指标，核对六组逐文件manifest、配置、best checkpoint与调参日志所选轮次、有限预测值，以及校准/测试集预测键、标签、事件标签、触发标志和时间戳。每组具有708,560个`(origin,horizon,node)`测试键，六组共同键完全一致。审计状态为PASS，完整逐键证据见`outputs/analysis/SG-EXP-032-target-audit/`。

| 模型 | 测试MAE（均值±种子SD） | RMSE | 原事件标签组MAE | 非事件组MAE | 新目标零值组MAE | 新目标非零组MAE |
|---|---:|---:|---:|---:|---:|---:|
| MRG-GCN | 0.043401±0.000303 | 0.193411±0.000728 | 0.480282±0.004677 | 0.037018±0.000241 | 0.008700±0.001153 | 0.614498±0.013807 |
| 容量近似TCN | 0.051703±0.000074 | 0.193320±0.000349 | 0.484651±0.000875 | 0.045377±0.000063 | 0.018353±0.000117 | 0.600560±0.001180 |

训练前冻结的主比较为同种子、同一`(origin,horizon,node)`键上的TCN绝对误差减MRG绝对误差，正值支持MRG。三个种子平均差为0.008302 kWh/15 min；固定测试期按连续7日时间块进行10,000次配对bootstrap，95%区间为[0.007757, 0.008797]，27/27个区块差值为正。共同全局MAE差方向一致，但RMSE近乎持平且略偏向TCN（差约0.000091）。

这一总体优势不能被解释为活跃负荷预测普遍更好：替代目标测试键零值比例为94.27%；MRG的零值组和非事件组MAE较低，但非零组MAE比TCN高0.013938 kWh/15 min（MRG 0.614498，TCN 0.600560）。原事件标签组仅有轻微总体差距，且各种子配对差异并不一致。因而本实验支持的结论是：在完成时刻截断代理目标下，MRG相对容量近似TCN的共同键全局MAE优势仍存在；这一优势主要由新目标零值组驱动；按旧事件标签划分的非事件组另呈较低边际MAE，两种边际分层未联合分解，不能据此声称模型改善了非零活跃负荷预测或实际运行价值。

## 回收与AutoDL关机验收

远端结果归档SHA-256为`b6f73aeb350db65f1d25ee59c19bcf8b316270049f46aaeee59ff971947670b3`，本地下载归档SHA逐字一致；归档内99项文件的SHA-256全部通过，随后逐键审计PASS。证据见`outputs/experiments/SG-EXP-032/recovery-verification.json`及`outputs/experiments/SG-EXP-032/recovered/closeout/closeout/`。关机前远端GPU为1 MiB占用、0%利用率且无训练进程，训练PID已消失。AutoDL控制台将目标实例`38a84e9a75-8c21d369`由“运行中”更新为“已关机”；不以SSH断连作为关机证明。控制面记录见`outputs/experiments/SG-EXP-032/shutdown-evidence.json`。

## 结论权限与限制

SG-EXP-032完成了目标敏感性补充，但它属于已查看Caltech固定测试期上的事后实验。它没有解决会话代理目标与电表实测功率之间的效度差距，也没有改变测试集高零值占比这一解释限制。原事件/触发标签冻结为事后分组口径；替代目标的零/非零标签仅用于结果分层。完成时刻截断结果可用于比较同一新代理目标下两种模型，不可把新旧标签上的绝对MAE差解释为模型误差变化，也不可将0.0477816 kWh/15 min标签定义差当作误差上限。训练、选模和审计均未调用目标事件/触发标签。
```

#### docs/thesis/revision-20261021-evidence/data-source-compatibility.md — Use existing bounded candidate checks; do not repeat general web searches or claim a compatible unseen period exists.
定位：`{"kind": "markdown_heading", "value": "数据源筛选"}`；来源SHA-256：`1e665a2dfec1657f085998f8b08a13822a25816a23b5d1610a8282f9673935bf`
```text
## 数据源筛选

| 候选 | 日期/站点 | 可核实字段与标签 | 节点映射/既有查看范围 | 当前判定 |
|---|---|---|---|---|
| ACN-Data Caltech、JPL、Office 1元数据API | 2026-10-19检查三站；接入时间最晚分别为2021-09-14、2021-09-14、2021-09-13 | 通过6次HTTP 200严格边界外查询，区间外计数均为0条。该轮只审计`connectionTime`边界，没有保存完整会话快照，也未核完整字段、标签成熟性与全部节点映射 | Caltech/JPL模型用10个冻结节点；Office 1官方站点为8个EVSE，且其历史使用史未核 | 对已查接口没有晚于论文时期的ACN记录；Office 1不是新时期，也不满足现成10节点映射。不能据此断言其他来源不可得 |
| KIT低频单车充电测量，DOI `10.5281/zenodo.17866847` | 2025-10-28至2025-12-02；KIT校园测量点；18组测量、16辆车、12个品牌 | `charging_uuid`、时间戳、三相实测电压/电流、由电压电流计算的三相有功功率、SoC、设定电流。元数据表含日期、品牌/车型及可用时的电池容量；无ACN式接入、充电完成、断开时间和总交付电量标签 | 每组为单一测量点，不含ACN的10个EVSE节点ID、相同节点顺序、站内关系图或可重建的同口径输入张量；数据期与论文测试期不重叠 | 可作有限的实测曲线形态审计；不兼容既有冻结检查点，不是新时期模型验证、代理标签校准或现场运行证据 |
| ChargePlace Scotland会话数据，DOI `10.15129/1f431af7-5caa-4840-a9ab-c1f3b521e033` | 2022-10-01至2024-03-31；苏格兰公共ChargePlace Scotland网络 | 官方说明含会话开始、充电点ID、会话时长、消耗电量、地方行政区、邮编、充电速度和支付金额；不包含按时间采样的实测功率曲线 | 与ACN站点/节点ID不同；记录介绍未提供与论文10节点的交叉表、三类站内关系图或相同张量；会话耗能可重新构造成另一代理目标，但不是本文的完成时刻/断开规则数据 | 日期上属于论文未查看时期，但字段和节点语义不支持现有冻结检查点直接推理。若要验证须另行定义站点/节点、关系图、标签和训练流程；目前未下载数据文件或训练 |
| 悉尼路侧充电候选 | 2025-09至2026-02；独立公共网络 | 当前页面显示受限访问；字段字典、功率时序和数据许可尚未取得 | 无法核站点节点、标签和论文历史使用关系 | 可得性与兼容性均未知，不能计为可用未查看期段 |
| EPFL-DESL Level-3充电数据（本地筛选，未入仓） | 2022-04-12至2023-07-04；瑞士Level-3站点；仅CCS1、CCS2两个被测直流快充端口 | 工作簿结构抽查：1,878条会话行、1,878个测量组。冻结V1严格`CCS + Session`连接为CCS1 1,129/1,129、CCS2 0/749；未进入形态比较 | 无ACN固定十节点映射、站内三类关系图或96×10×7输入契约；只有两个被测端口 | V1停止，未产生形态差异、代理标签校准、ACN模型评价或目标效度结果；不是冻结检查点可用的兼容未查看期段 |

```

#### data/external/epfl-l3-20261021/README.md — Source-defined EPFL station, power, energy, sampling, and control-field semantics.
定位：`{"kind": "whole_file"}`；来源SHA-256：`28daaa5b0d65872d09f95d9a0dd1e4490f6b79bfa2ea780f56b51e8a012c93be`
```text
# Level 3 electric vehicle charging dataset
## Description of the commercial EV charging station used to collect the dataset

The dataset has been collected on a level 3 electric vehicle (EV) charging station located in southwestern Switzerland. The data has been measured from April 12th 2022 to July 4th 2023.

The charging station includes 6 charging plugs: 2xCCS, 1xCHAdeMO, 1xType 2 socket, 1xType 2plug, and 1xTesla DC. Only measurements from the CCS plugs are included in the dataset as the utilization of other charging options were significantly lower. The maximum power of the charging station is 172.5 kW and two EVs can be supplied at the same time.

In case of two simultaneous charging sessions, the power capacity is equally divided however, in case one EV draws less power than the allocated one by the charging station, the otherwise unused capacity is allocated to the other EV.

The data is retrieved by a custom-made data acquisition software developed by the EPFL-DESL. The data include measurement and session data. The measurement dataset consist of 64277 measurements with a 1-minute resolution. The session dataset consists of 1878 EV charging sessions contained in the measurement data. The description of the two dataset is reported here below.

## Measurement dataset
A measurement data point includes the following values:
| Identifier | Description |
| --- | --- |
| _Data and time_ | |
| _CCS_ | Plug ID (CCS1 or CCS2) |
| _Session_ | ID number given for the session |
| _P_ | AC charging power of the charging station [W] |
| _Pset_ | Power setpoint set by the charging station [W] |
| _Preq_ | Power requested by the EV [W] |
| _TotalCapacity_ | Total energy capacity of the EV’s battery |
| _RemainingCapacity_ | Remaining energy in the EV’s battery |
| _BulkCapacity_ | Usable energy capacity of the EV’s battery |
| _Energy_ | Cumulative energy charged of the charging session [Wh] |
| _SOC_ | State-of-charge of the EV’s battery [%] |
| _Ctrl_t_ | Boolean identifying whether Pset < Preq at the time interval (0=False, 1=True) |
| _Ctrl_s_ | Boolean identifying whether Pset < Preq anytime during the charging session (0=False, 1=True) |

Quantities are recorded with a sampling time of one minute.

## Session data
Each charging session includes the following values:
| Identifier | Description |
| --- | --- |
| _Session_ | ID number attributed to the charging session |
| _CCS_ | Plug ID (CCS1 or CCS2) |
| _Arrival_ | EV arrival time |
| _Departure_ | EV departure time |
| _Stay_ | EV stay duration [min] |
| _Energy_ | Charged energy [Wh] |
| _Pmax_ | Maximum AC charging power of the session [W] |
| _Preq_max_ | Maximum AC charging power of the session [W] |
| _Controlled session_ | Boolean identifying whether Pset < Preq anytime during the charging session (0=False, 1=True) |
| _TotalCapacity_ | Total energy capacity of the EV’s battery [a-dimensional] |
| _BulkCapacity_ | Usable energy capacity of the EV’s battery [a-dimensional] |
| _SOC arrival_ | State-of-charge of the EV’s battery at arrival [%] |
| _SOC departure_ | State-of-charge of the EV’s battery at departure [%] |
| _Energy capacity_ | Approximated capacity of the EV’s battery [Wh] |

```

#### data/external/epfl-l3-20261021/LICENSE — Confirm the local source license before documenting reuse.
定位：`{"kind": "whole_file"}`；来源SHA-256：`4654a82938a437cf4ef3efbb9ed7cb7a7b95f8250db1e1444d22c6e22e9a9d8f`
```text
MIT License

Copyright (c) 2025 Distributed Electrical Systems Laboratory (DESL), École Polytechnique Fédérale De Lausanne (EPFL)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

#### docs/thesis/revision-20261021-evidence/training-source-chain.json — Existing machine-readable SG-EXP-031/032 source, archive, and manifest chain.
定位：`{"kind": "line_range", "start": 1, "end": 80}`；来源SHA-256：`6f410fd7ee51d2e62f7e74f54af0e903a51edf803a778c50ef0d2685a83cb0dc`
```text
{
  "audit_id": "TRAINING-SOURCE-CHAIN-20261021",
  "generated_utc": "2026-10-21T01:56:23+00:00",
  "audit_script": {
    "path": "scripts/audit_training_source_chain.py",
    "sha256": "d45410f467d4ba56c4f3433ee9a3da4cb28fdf8b54d00983e7272910e020e134"
  },
  "status": "PASS",
  "experiments": {
    "SG-EXP-031": {
      "source_commit_recorded": "fce67da891d95ae5021942e3e34fb088c1a9fc2a",
      "working_tree_patch_bytes": 0,
      "entrypoint": {
        "path": "scripts/jpl_relation_controls.py",
        "sha256": "ac5f7a998ad198af30f07971f929b7abc43300e7aecb9e65e645d633920b9cba",
        "matches_frozen_bundle": true,
        "git_tracked": false
      },
      "training_code_sha256": "d40d609177089702c0799f106dbce19ce07e906f28410554506d74e1c39d0018",
      "training_plan_sha256": "435be23f6a9ed824a24e872617fc75e78972b720da84d7603c438fa47a64c499",
      "data_sha256": "1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af",
      "original_graph_sha256": "1ad00239c64de72cfcd685609fadd9a2de87e7715807b9b3afcd29be6da6e98b",
      "result_archive": {
        "path": "outputs/experiments/SG-EXP-031/SG-EXP-031-results.tar.gz",
        "sha256": "4eb436fbf30823d4df9b3e1be9f34652f849bdf7a130ce1c4229d9b2964f8c5f"
      },
      "bundle_archive": {
        "path": "outputs/experiments/SG-EXP-031/SG-EXP-031-bundle.tar.gz",
        "sha256": "5361c41a147592d0ea6bb14cd2282637f4906015a0dc76f4563d2b0e388b4d8a"
      },
      "bundle_manifest": {
        "manifest_path": "outputs/experiments/SG-EXP-031/bundle/BUNDLE_MANIFEST.json",
        "manifest_sha256": "3ba32eee77da8bea6895804f5c4f1bf4924d3ff394b4aabce84c394fc482ee8b",
        "entries": 67,
        "entries_verified": 67,
        "status": "PASS",
        "mismatches": []
      },
      "result_audit": {
        "path": "outputs/analysis/SG-EXP-031-audit-20261015/audit.json",
        "sha256": "8f98f6cbc9ec71e8433fb47985b3569a92aae01a92e46be5ff53fe55c7042475",
        "status": "POST_HOC_DIAGNOSTIC",
        "source_checksum_entries_verified": 173,
        "test_keys_per_run": 632640,
        "run_count": 12
      },
      "checkpoint_and_prediction_manifests": {
        "runs": 12,
        "files_verified": 156,
        "files_expected": 156,
        "status": "PASS",
        "mismatches": [],
        "run_manifests": [
          {
            "manifest_path": "outputs/experiments/SG-EXP-031/recovered/results/SG-EXP-031/jpl/event_to_self/seed-2024/manifest.json",
            "manifest_sha256": "e27f15cf9cab6912ec18f9f5111d6549cdd92a408b0a700e1ac59b5e682e1407",
            "run_summary_path": "outputs/experiments/SG-EXP-031/recovered/results/SG-EXP-031/jpl/event_to_self/seed-2024/run_summary.json",
            "status": "complete",
            "model": null,
            "seed": null,
            "best_epoch": 23,
            "file_count": 13,
            "files": [
              {
                "path": "best.pt",
                "expected_sha256": "ba8c13f36daa5ee60786e891a3b4b743b4388064b075280af93115a52ae9ced4",
                "actual_sha256": "ba8c13f36daa5ee60786e891a3b4b743b4388064b075280af93115a52ae9ced4",
                "passed": true
              },
              {
                "path": "beta.json",
                "expected_sha256": "e51371c2b7f0d34e27e3c6884122e0d5a0bf1b2177d6ee024c5a6a05e22f3ea5",
                "actual_sha256": "e51371c2b7f0d34e27e3c6884122e0d5a0bf1b2177d6ee024c5a6a05e22f3ea5",
                "passed": true
              },
              {
                "path": "config_resolved.json",
                "expected_sha256": "936016c4013400c1c267b1882c13985bd2389323daff60c3c562396a5f83dd31",
                "actual_sha256": "936016c4013400c1c267b1882c13985bd2389323daff60c3c562396a5f83dd31",
                "passed": true
```

## 完成报告
在`docs/thesis/blueprints/tasks/REV-20261022-EVIDENCE-PACKAGE-EPFL/execution-report.json`填写Claude Code工作报告。changed_paths使用项目根目录相对路径，仅列实际工作区改动，不必列报告自身；列出证据来源、检查、未解决事项，以及所有数字或主张变化。报告只供Codex复检，不代表验收。
在`model`字段填写当前Claude Code会话实际报告的模型标识；`user_reported_model`只是操作者标签。若provider返回`unrecognized_model`，把原始模型名和诊断写入`unresolved`，不要猜测或自动替换模型。
如证据不足、需要扩大修改范围或发生未授权操作，停止继续并在报告中说明。
