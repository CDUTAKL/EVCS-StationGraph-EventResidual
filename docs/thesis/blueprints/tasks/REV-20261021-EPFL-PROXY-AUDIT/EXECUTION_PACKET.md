# Claude Code执行任务包

任务编号：REV-20261021-EPFL-PROXY-AUDIT
任务类型：evidence_audit；对应12流程阶段：第8/10/11/12步：实测目标核验、来源链和受限修订
目标：使用已下载并按Git提交与SHA-256冻结的EPFL-DESL Level-3同步实测数据，审计“Arrival至Departure均匀分配会话Energy”与同会话15 min实测功率/能量曲线的差异；生成可复算脚本、逐会话派生表、汇总和来源清单，并同步更新数据兼容性/来源链证据。不得将此外站审计写成ACN冻结检查点验证或应用收益；本轮不改论文主稿，待Codex独立复算后再决定正文措辞。

## 开始前
只依据本任务包的冻结摘录和蓝图列出的材料工作。不要从聊天历史、归档计划或整份实验登记表重建当前状态。正文源稿为`docs/thesis/thesis-manuscript.md`。

## 可写范围
- `scripts/audit_epfl_proxy_shape.py`
- `docs/thesis/revision-20261021-evidence/epfl-proxy-audit/`
- `docs/thesis/revision-20261021-evidence/data-source-compatibility.md`
- `docs/thesis/data-availability.md`
- `docs/thesis/claim-evidence-map.md`
- `docs/thesis/revision-20261021-evidence/source-chain-summary.md`
- 以上路径是任务约束和事后审计范围，不是操作系统级文件隔离；不要写入未列路径，也不要把Git忽略路径当作可审计输出。

## 锁定主张与口径
- 此数据期未进入论文既有ACN训练/验证/测试与既有实验，但本轮已读取数据工作簿结构和少量样例；因此本次分析是探索性外部核验，不得称为盲态、预注册或确认性未查看测试。
- EPFL数据是瑞士Level-3商业站，只包含两个被测CCS端口、1 min功率测量和会话字段；不含ACN十节点映射、相同站内关系图及96×10×7输入张量。不得对论文冻结检查点做直接推理，不得训练。
- 审计只对比会话Arrival–Departure均摊能量与该外站实测功率/能量时间形态；不得将外站结果与论文ACN主目标的MAE直接比较，也不得推断模型精度、真实部署收益或调度收益。
- 先报告数据连接、覆盖率、功率积分/累计能量/会话电量闭合和纳排流程；若核心能量链未通过，不报告形态差异为有效证据。不得根据结果修改预设门槛。
- 原始工作簿位于Git忽略目录data/external/epfl-l3-20261021/，只读且不得移动、重写、提交或复制到生成目录；来源提交、文件SHA和MIT许可须保留。
- 源链训练核验不得补造Git提交。SG-EXP-031/032的事后测试期边界、[76]原文可读范围、ACN范围检查限度均按既有来源摘要保持不变。
- 本轮不得修改thesis-manuscript.md、DOCX、图表、评分、Git状态；如审计有效，先输出待Codex复核的建议措辞，不直接进正文。

## 执行步骤
1. 阅读协议与源README，先检查输入文件存在、SHA-256吻合、工作簿sheet/字段/行数和仓库提交引用；不要联网或尝试重新下载。
2. 编写scripts/audit_epfl_proxy_shape.py，固定列映射、匹配键、时序积分、异常/缺失/重复筛选和预定纳排标准；保留每个排除原因，运行入口使用显式路径参数。
3. 检查Session_data与Measurement_data按CCS+Session连接的唯一性和覆盖；按源字段对P(W)梯形积分，按Energy(Wh)累计读数和会话Energy独立闭合。确认DST/时区限制、采样间隔与相邻记录关系，不把naive本地时刻冒充UTC。
4. 对通过预先固定质量门槛的会话，将会话Energy按Arrival至Departure的15 min片段重叠比例均匀分配；把同窗口测量功率积分成15 min实测电量。分离总量误差与归一化形态误差，并按协议计算TVD及描述统计。
5. 输出去标识逐会话指标CSV、summary.json、源文件/脚本/结果哈希清单和审计报告；报告包含输入覆盖、连接数、排除表、异常解释、单位、时间口径和全部局限。不得仅保留拟合较好的会话。
6. 运行蓝图指定的本地分析命令并检查输出完整性；随后只在授权证据文档中更新EPFL数据兼容性、探索性审计结果、ACN冻结模型不兼容边界及正确的SG-EXP-031表号/CSV路径。更新当前入口，不覆盖日期化历史记录。
7. 保持主稿不变。在审计报告末尾给出“是否具备进入后续正文修改”的有限建议，不作分数判断；填写execution-report.json并标记pending_codex_review。

## 指定Claude Code Skills
- 本任务未指定Claude Code专用skill；如需技能支持，先在报告中说明阻塞，不要假定Codex全局skill已自动安装到Claude Code。

## 验收条件
- 数据文件SHA-256与协议一致；分析脚本可在本地重跑，输出清楚记录工作簿sheet、字段、纳排、时间口径和所有文件哈希。
- 全部输入会话按CCS+Session可复核匹配；功率积分、累计能量和会话Energy闭合统计完整，并明确阈值、失败数量与未匹配数量。
- 均摊目标与实测数据比较只在质量门槛内会话开展；幅值与形状分别量化，结果与结论不超出单站双CCS外部形态审计。
- 明确该数据不兼容现有冻结检查点、非ACN新时期模型验证、非目标kWh校准证据、非真实调度回放。
- 正文与DOCX保持不变；不训练、不访问网络、不改原始数据、不提交Git；输出须待Codex独立复核而非宣称验收通过。
- 修复data-availability.md当前入口中SG-EXP-031表3-11的旧引用（应为表3-10；历史日期段不改），并在CLM-031-RELATION中补充已经存在的逐种子/块级CSV证据目录。

## 操作权限
- 训练：False；远程执行：False；联网：False；Git提交/暂存：False。
- 除非明确列入允许范围，不得启动训练、远程作业、联网采集、Git暂存/提交或覆盖正式Word。不得使用绕过权限的启动方式。
- 不得修改`.git/`、`.claude/settings*.json`、凭据文件或交接控制文件；如需修改，停止并报告。
- 只运行蓝图列出的检查：python3 scripts/audit_epfl_proxy_shape.py --input-dir data/external/epfl-l3-20261021 --output-dir docs/thesis/revision-20261021-evidence/epfl-proxy-audit。未列检查时不要新增或运行测试。
- Bash网络主机白名单：无。空数组表示Bash无网络；WebSearch/WebFetch须单独取得工具权限。

## 冻结的证据摘录

### 证据控制台

#### docs/thesis/revision-20261021-evidence/epfl-proxy-audit-protocol.md — 预先冻结数据来源、连接键、能量闭合、形态指标与结论权限
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

#### docs/thesis/claim-evidence-map.md — 核对论文当前核心主张、代理负荷边界和SG-EXP-031证据定位
定位：`{"kind": "line_range", "start": 18, "end": 24}`；来源SHA-256：`66fa63bd7891614733a103d9baa448797f2a991f3d3f6084fdb4b019a7414403`
```text

SG-EXP-031/032及JPL后续诊断均使用已查看的固定测试期，属于事后补充证据；不作为独立时期确认。全文据此区分总体模型比较、组件内增量、探索性分层与未验证的现场主张。

- AdaptiveGraph：SG-EXP-004三个冻结检查点在匹配PyTorch 2.4.1/CUDA 12.1环境逐键通过；原生CPU存在top-k并列选边差异，固定CUDA邻接后CPU通过。原训练Git标识缺失、历史Mac环境偏差仍保留。报告：`experiment-reports/EXP-AdaptiveGraph-CUDA-20261015-no-training.md`及`outputs/analysis/AdaptiveGraph-CUDA-20261015/independent-verification.json`。
- SG-EXP-031：四配置×三种子同参数关系自环替换重训，支持负荷耦合和轮廓相似关系在当前JPL设置下的条件性整体MAE增量，行为共现关系区间跨零。审计中的次要分层显示，负荷关系相对自环的非零组种子平均差为0.004893 kWh/15 min，三个种子方向均为正；这是已查看测试期上的事后描述，未作该分层的多重校正，不等同完整模型胜过TCN（JPL非零组仍是TCN较低）。正文§3.7.2、表3-10；输入/容量/预算见表3-14。报告：`experiment-reports/SG-EXP-031-jpl-relation-controls.md`，数值见`outputs/analysis/SG-EXP-031-audit-20261015/audit.json`及`content-review-20261016-paired-reaudit/load-nonzero-crosscheck.json`。
- SG-EXP-032：完成时刻截断代理目标下全局MAE排序保持；新目标零值94.27%，非零组MRG-GCN较差。正文§3.8.4、表3-15；两种分层是边际评价，未作联合贡献分解。两项新训练均为已查看固定测试期上的补充。
- JPL可靠性：AUDIT-JPL-CAL-20261015复用313,120校准键与632,640测试键，标准/行为分层整体覆盖90.08%/90.11%，事件46.43%/45.88%，独立核验PASS。正文§5.3.5；报告`experiment-reports/EXP-JPL-calibration-20261015-no-training.md`。JPL尚缺L2与同硬件时延。
```

#### docs/thesis/data-availability.md — 当前ACN已查看范围及候选新数据的已核实兼容性
定位：`{"kind": "line_range", "start": 1, "end": 22}`；来源SHA-256：`71a5f14b466d54f02cfa91814c6bc1272e873716af57578a9edd8f4814e35c10`
```text
# 数据可用性

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
- 以上候选均不改变现有冻结推理结论：没有可核验的同步站级电表功率、物理EVSE映射、真实站容量/馈线限额、车辆截止时间与需求、电价序列及同时间基线负荷；`SG-EXP-026`继续标记为合成案例，不升级为应用验证。ACN边界结论仅限已查REST API的`connectionTime`和6个HTTP 200区间外计数为0，不扩展到其他数据源不可得。

## 历史证据状态（截至2026-10-16统一修订）
```

#### docs/thesis/revision-20261021-evidence/data-source-compatibility.md — 站点、字段、标签、节点映射和现有应用材料缺口
定位：`{"kind": "whole_file"}`；来源SHA-256：`22a06bad96db6f25fac785201d49c84d6a55372e0eb2315fd87c24eec9fa413a`
```text
# 未查看数据期段与应用材料兼容性核查

核查日期：2026-10-21。当前主稿的ACN训练、验证与测试均结束于2021-09-14；Caltech测试段为2021-03-12至2021-09-14，JPL测试期同样属于ACN历史段。下列“未查看”表示该数据时期未进入本论文现有实验；数据目录页/记录页在本次核查中已访问。

## 数据源筛选

| 候选 | 日期/站点 | 可核实字段与标签 | 节点映射/既有查看范围 | 当前判定 |
|---|---|---|---|---|
| ACN-Data Caltech、JPL、Office 1元数据API | 2026-10-19检查三站；接入时间最晚分别为2021-09-14、2021-09-14、2021-09-13 | 通过6次HTTP 200严格边界外查询，区间外计数均为0条。该轮只审计`connectionTime`边界，没有保存完整会话快照，也未核完整字段、标签成熟性与全部节点映射 | Caltech/JPL模型用10个冻结节点；Office 1官方站点为8个EVSE，且其历史使用史未核 | 对已查接口没有晚于论文时期的ACN记录；Office 1不是新时期，也不满足现成10节点映射。不能据此断言其他来源不可得 |
| KIT低频单车充电测量，DOI `10.5281/zenodo.17866847` | 2025-10-28至2025-12-02；KIT校园测量点；18组测量、16辆车、12个品牌 | `charging_uuid`、时间戳、三相实测电压/电流、由电压电流计算的三相有功功率、SoC、设定电流。元数据表含日期、品牌/车型及可用时的电池容量；无ACN式接入、充电完成、断开时间和总交付电量标签 | 每组为单一测量点，不含ACN的10个EVSE节点ID、相同节点顺序、站内关系图或可重建的同口径输入张量；数据期与论文测试期不重叠 | 可作有限的实测曲线形态审计；不兼容既有冻结检查点，不是新时期模型验证、代理标签校准或现场运行证据 |
| ChargePlace Scotland会话数据，DOI `10.15129/1f431af7-5caa-4840-a9ab-c1f3b521e033` | 2022-10-01至2024-03-31；苏格兰公共ChargePlace Scotland网络 | 官方说明含会话开始、充电点ID、会话时长、消耗电量、地方行政区、邮编、充电速度和支付金额；不包含按时间采样的实测功率曲线 | 与ACN站点/节点ID不同；记录介绍未提供与论文10节点的交叉表、三类站内关系图或相同张量；会话耗能可重新构造成另一代理目标，但不是本文的完成时刻/断开规则数据 | 日期上属于论文未查看时期，但字段和节点语义不支持现有冻结检查点直接推理。若要验证须另行定义站点/节点、关系图、标签和训练流程；目前未下载数据文件或训练 |
| 悉尼路侧充电候选 | 2025-09至2026-02；独立公共网络 | 当前页面显示受限访问；字段字典、功率时序和数据许可尚未取得 | 无法核站点节点、标签和论文历史使用关系 | 可得性与兼容性均未知，不能计为可用未查看期段 |

## KIT低频测量曲线形态审计

原始来源记录：Zenodo API元数据`kit-lf/zenodo_record.json`，SHA-256 `4f1f63ab1ba03beddeabe4573fca718dd4dc364baf9df7bacca6e8a5fc2b9ae7`；KITopen记录列明CC BY 4.0，Zenodo API亦列出`cc-by-4.0`。LF Parquet文件为422,470,722字节，发布校验MD5 `0327dae2664c79ecde0bd07166bf6b1d`。本轮通过DuckDB远程列裁剪读取所需字段，没有下载422 MB的完整功率文件；仅保存1,476字节的充电元数据Parquet（MD5 `530c62c0cfe9e8ca47905c333c7ba62f`，SHA-256 `6eb38551df9d4cd3f1ea4e46a5d0f871bda84f5e992d63b68d0508bdd2415e5b`）。

审计口径：按`charging_uuid`对三相有功功率求和；功率由源数据记录的三相实测电压、电流计算。以总有功功率首次和最后一次超过100 W的样本界定观测活跃窗；相邻样本间以梯形积分，超过每组中位采样间隔5倍的时间段排除。将有效电能分配到相对活跃窗起点的15 min片，并与“保持同一观测总电能、按活跃窗时长均匀分配”的参照比较。形状差异用总变差距离表示：逐片电能绝对差之和除以总电能的两倍。

结果见`kit-lf/summary.json`和18组逐组清单`kit-lf/session_profile_audit.csv`；计算脚本为`../../../scripts/audit_kit_measured_lf_profile.py`。本次只作实测曲线形态审计；比较窗是仪器记录到的首末活跃样本，不是车辆接入至断开区间，因此不能把结果等同于ACN目标重构误差，也不能推导模型MAE或负荷预测收益。该审计汇总状态为`COMPUTED`，因本轮精确纳秒重算受Zenodo HTTP 429限流影响，时间覆盖率及形态统计尚未完成最终复核，不作为论文定量证据。

## 应用证据门槛

当前没有可核验的同步站级电表功率、物理EVSE映射、真实站容量/馈线限额、车辆截止时间与需求、电价序列及同时间基线负荷。KIT数据只有受控单车测量，ChargePlace Scotland虽有网络会话能量但无已核实的分时功率；二者都不能支持真实约束离线调度收益估计。`SG-EXP-026`继续标记为合成案例，不升级为应用验证。

## 可复核来源

- KIT数据：[Zenodo数据集](https://zenodo.org/records/17866847)，[KITopen记录与字段说明](https://publikationen.bibliothek.kit.edu/1000190660)。
- ChargePlace Scotland数据：[University of Strathclyde数据记录](https://pureportal.strath.ac.uk/en/datasets/scottish-public-electric-vehicle-charging-chargeplace-scotland-oc/)。
- ACN字段及接口：[ACN-Data官方文档](https://ev.caltech.edu/dataset.html)。

```

### 直接证据

#### docs/thesis/revision-20261021-evidence/source-chain-summary.md — 近邻[12][13][67][70][76]证据来源与训练源码链的既有核查结论
定位：`{"kind": "whole_file"}`；来源SHA-256：`26358e4b586e1bd98c027ebc362b5e39cd15ed80ec93de28f80e75d924d593ef`
```text
# 2026-10-21 来源链与近邻证据复核

## 近邻比较

主稿表1-1已正面对比参考文献[12]、[13]、[67]、[70]和[76]等近邻，按研究对象、节点/关系构造、模型路径、验证范围和限制说明差异；特别指出[76]已研究会话交易重构的EV负荷预测与残差校正，本文不把一般代理负荷预测或残差修正说成研究空白。表后将本文贡献限定为单场站节点关系的受控增量证据与MDP诊断，不作跨论文数值排名。

本轮未重新取得[76]出版社全文（出版社页面返回429）。应以`content-review-20261019-paired/sources/NEAR76-factual-extract.md`作为当前正文事实的溯源入口；该摘录记载其依据2026-10-17留存的出版社原文核验，明确了原文可读范围。不得引用旧评阅包`content-review-20261017-calibration-pair/reviewer-packet/evidence/NEAR76-primary.md`中的“当前稿没有正面比较[76]”作为当前判断，该句反映的是早期稿件状态。

对[12]、[13]、[67]、[70]的原文比较见`content-review-20261015-rev7/packet/nearest-work-source-audit.md`；[71]—[73]及近邻定位结论见`revision-20261016-nonexperimental/nearest-work-source-audit.md`。现稿不需重写近邻章节，需更新证据映射以指向与现稿一致的来源记录。

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

## 论文交叉引用复核

当前正文SG-EXP-031结果位于§3.7.2表3-10；表3-11是旧Caltech关系子集与超参数敏感性结果。已将`claim-evidence-map.md`、`experiment-registry.md`和`material-passport.md`当前入口中的SG-EXP-031表号修正为表3-10；旧历史记录仍按其当时稿件保留，未全局替换。

## 决策范围

本轮只补证据来源、哈希、数据可用性与正文主张边界。训练、检查点、原始ACN会话、逐键预测及完整外部测量文件不进入论文Git；公开文件仅记录可复算的程序、派生汇总、许可信息、数据源与SHA-256。

```

#### docs/thesis/revision-20261021-evidence/training-source-chain.json — SG-EXP-031/032冻结源码、配置、数据与输出哈希的机器记录
定位：`{"kind": "line_range", "start": 1, "end": 25}`；来源SHA-256：`6f410fd7ee51d2e62f7e74f54af0e903a51edf803a778c50ef0d2685a83cb0dc`
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
```

#### docs/thesis/experiment-reports/SG-EXP-032-completion-target-sensitivity.md — 论文代理目标的已知定义、完成时刻敏感性结果及边界
定位：`{"kind": "whole_file"}`；来源SHA-256：`9585428a9501321944ba38efcfacaa3978d8c2514149c6eedfe0a46fd25b0f8a`
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

#### docs/thesis/revision-20261021-evidence/epfl-proxy-audit-protocol.md — 冻结本次外部实测功率审计流程和解释权限
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

## 完成报告
在`docs/thesis/blueprints/tasks/REV-20261021-EPFL-PROXY-AUDIT/execution-report.json`填写Claude Code工作报告。changed_paths使用项目根目录相对路径，仅列实际工作区改动，不必列报告自身；列出证据来源、检查、未解决事项，以及所有数字或主张变化。报告只供Codex复检，不代表验收。
在`model`字段填写当前Claude Code会话实际报告的模型标识；`user_reported_model`只是操作者标签。若provider返回`unrecognized_model`，把原始模型名和诊断写入`unresolved`，不要猜测或自动替换模型。
如证据不足、需要扩大修改范围或发生未授权操作，停止继续并在报告中说明。
