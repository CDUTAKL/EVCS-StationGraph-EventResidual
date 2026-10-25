# Readability-focused calibration-pair review

- Protocol: EVCS-THESIS-REVIEW-2.0; rubric: EVCS-THESIS-CONTENT-1.0; reviewer: codex_readability_review_2026-10-19.
- Context: 9932a34c-fb11-4131-8661-4f687ca16252; mode: calibration_pair; historical scores exposed: false.
- Frozen packet: /Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/revision-20261019-nontraining/calibration-review-preparation/reviewer-packet.
- Baseline SHA-256: 62fe9dd1dbc44187f18992394051e2f31a705ef1b25dc06337bade4d6e5c9a66.
- Current SHA-256: 451642e15e0fc51343acabf84e727b5079d8a1f2243c0ab8d8542adeed8b9b42. Both match the packet manifest.
- Local totals (90-point rubric): 74.5/90 → 75.5/90 (+1.0). Scores use 0.5 increments.
- Figures were reviewed by captions only; figure content, layout, and PPI remain unchecked. This is not an official thesis judgment.

## BR-01 — 选题意义与问题定义: 4.5 → 4.5/5
- Components (baseline→current): problem 2/2→2/2; significance 1.5/2→1.5/2; need 1/1→1/1.
- Locator: 摘要；§1.1.1–1.1.3、§1.3–1.4；§2.1.1–2.1.3.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/DATA_AVAIL.md, evidence/QUALITY.md.
- Rationale: 两稿均明确站内代理负荷问题与切分粒度，且动机由稀疏性和数据现象支撑；实际功率和业务效益尚未量测，属于已声明边界，主要限制实践评价而非问题定义。文本无足以改变此项的修订。
- Uncertainty: 数据证据可支持研究动机，但不能外推到真实功率或业务收益；这不是当前任务定义的内在缺陷。

## BR-02 — 研究问题、范围与题目一致性: 4.5 → 4.5/5
- Components (baseline→current): alignment 2/2→2/2; progression 1.5/2→1.5/2; closure 1/1→1/1.
- Locator: 摘要；§1.3–1.6；§3.9；§4.5；§5.5及结论.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/CAL.md, evidence/MAP.md.
- Rationale: 研究问题、代理目标、受控比较和受限结论整体闭合。章节推进包含多个诊断分支，读者需自行整合三层MDP各自回答的问题；新版1.6贡献句更具体但不改变整体进展评分。
- Uncertainty: 三层诊断是否足够紧凑属组织判断；题目与范围并无明显越界。

## BR-03 — 文献综述与缺口定位: 4 → 4.5/5
- Components (baseline→current): coverage 1/1→1/1; sources 1.5/2→2/2; gap 1.5/2→1.5/2.
- Locator: §1.2.2、表1-1及表后段；§1.2.3–1.2.4；§1.3.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/NEAR76.md, evidence/NEAR.md, evidence/NEAR2.md.
- Rationale: 唯一评分变化：表后引文从[12-13,67,70-76]调整为[12-13,67-73,76]，与表1-1实际列出的比较项相符，读者更易核对引用覆盖且减少未列条目的含混。近邻[76]的目标、粒度和验证差异已有说明，但差异维度仍可更紧凑地并列。
- Uncertainty: 近邻原文核读范围受材料包所列可读部分限制；稿件已披露未核实全文细节。

## BR-04 — 理论基础与专业知识: 4.5 → 4.5/5
- Components (baseline→current): concepts 2/2→2/2; formulas 1.5/2→1.5/2; knowledge 1/1→1/1.
- Locator: §2.1–2.5（式2-1、2-2）；§3.2–3.5（式3-1–3-16）；§4.2.5、§4.4；§5.2–5.4.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/MDP.md, evidence/ADAPT.md, evidence/S31.md, evidence/S32.md.
- Rationale: 概念、符号与代理量基本连贯，模型和诊断方法被用于具体问题。公式与代码实现的逐项独立核对不在本次材料范围；文中已说明关键尺度和解释限制，因此保留部分缺口分，两稿无理论说明的实质改变。
- Uncertainty: 未作源码级公式—实现核验；不把已声明建模假设视为理论错误。

## BR-05 — 方法与实验设计: 8 → 8/10
- Components (baseline→current): information_split 2.5/3→2.5/3; comparators 1.5/2→1.5/2; controls 2.5/3→2.5/3; selection_budget 1.5/2→1.5/2.
- Locator: §2.1.1表2-2；§3.6.1–3.6.3表3-1–3-3；§3.7.1–3.7.2表3-9、3-11；§3.8.3表3-14；§4.3.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/S31.md, evidence/S32.md, evidence/CAL.md, evidence/MDP.md, evidence/ADAPTAUDIT.json.
- Rationale: 主要信息权限、时间划分、基线和干预结构清楚；关系替换及门控对照能回答限定问题。对照容量/训练预算并非处处完全匹配，门控预算解释仍保留。当前稿未改变设计，因此分数不变。
- Uncertainty: 审阅材料支持受检期间和固定预算结论，不足以证明未见时期的外部稳健性；稿件将其列为后续验证。

## BR-06 — 可复现性与方法严谨性: 4 → 4/5
- Components (baseline→current): data_split 1/1→1/1; source_config 1/1.5→1/1.5; keys_metrics 1.5/1.5→1.5/1.5; environment_package 0.5/1→0.5/1.
- Locator: §2.1–2.2；§3.6.1、§3.6.4、§3.8.3表3-14；§4.6.1.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/DATA_AVAIL.md, evidence/QUALITY.md, evidence/ADAPTAUDIT.json.
- Rationale: 数据切分、预测键和指标定义可追溯，主要结果有审计/重算支撑；环境封装及部分旧基线源码身份仍不齐。当前修订未补入新的复现工件，故保持原分。
- Uncertainty: 未从材料包独立复跑全部模型；有限复现记录是已证实的覆盖缺口，不推断结果错误。

## BR-07 — 工作量与解决问题能力: 9 → 9/10
- Components (baseline→current): technical_work 4/4→4/4; problem_solving 3.5/4→3.5/4; integration 1.5/2→1.5/2.
- Locator: §2–5，重点§3.7–3.8、§4.2–4.6、§5.2–5.4.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/S31.md, evidence/S32.md, evidence/MDP.md, evidence/MAP.md.
- Rationale: 研究包含数据审计、建图、训练比较、多层诊断和误差解释，体现实质问题处理；各分析链已整合，但章节材料量大、综合主线仍需读者自行提炼。文字修订没有改变已完成工作。
- Uncertainty: 该项以论文中可见工作量和分析链判断，不据未开展的外站/现场试验重复扣分。

## BR-08 — 结果与证据充分性: 8 → 8/10
- Components (baseline→current): claim_support 3.5/4→3.5/4; alternatives 2.5/3→2.5/3; robustness_scope 2/3→2/3.
- Locator: §3.6.2–3.6.5；§3.7.1–3.7.5表3-9–3-15；§4.4–4.6表4-5、4-8；§5.3.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/S31.md, evidence/S32.md, evidence/CAL.md, evidence/ADAPTAUDIT.json.
- Rationale: 核心关系增量和负结果均有对应对照，主张已限于整体MAE等指定协议。独立外部时期、非零/事件子组表现和组件替代仍有限；稿件本次没有新增结果，分数不变。
- Uncertainty: 测试期复用和子组的探索性限制已披露；它们限制外推强度，不构成主结果失效的证据。

## BR-09 — 统计解释与结论边界: 8.5 → 8.5/10
- Components (baseline→current): uncertainty 3.5/4→3.5/4; multiplicity 1.5/2→1.5/2; interpretation 3.5/4→3.5/4.
- Locator: §3.6.1–3.6.4；§3.7.1–3.7.2；§3.8.4；§4.2.5、§4.4；§5.3.3–5.3.7及结论.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/S31.md, evidence/S32.md, evidence/CAL.md, evidence/MDP.md.
- Rationale: 稿件区分受检模型、方向性结果、未校正事后分层与重复查看时期，并保留不确定和负结果。多重分析仍属探索性，统计确认范围有限；本轮修改未改变统计处理。
- Uncertainty: 没有将已披露的三种子/已查看时期自动转作扣分；更广泛数据上的重复性仍待检验。

## BR-10 — 贡献与创新: 8 → 8/10
- Components (baseline→current): prior_difference 2.5/3→2.5/3; contribution 3/3→3/3; demonstration 2.5/4→2.5/4.
- Locator: §1.2.2表1-1；§1.2.3、§1.3–1.4；§3.8.1表3-13；§4.5表4-6；结论.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/NEAR76.md, evidence/NEAR2.md, evidence/S31.md, evidence/S32.md, evidence/MDP.md.
- Rationale: 相对近邻的差异和受控经验/诊断贡献已经说明。当前稿将两项贡献具体重述于1.6，增强可读性，但没有改变已有差异证据或新增价值验证，故贡献清晰度已满、总分不变。
- Uncertainty: 不要求新算子；受控增量与诊断判断可作为贡献，但诊断指导改模的预测收益未被证明。

## BR-11 — 专业实践价值: 3.5 → 3.5/5
- Components (baseline→current): use_case 1/1→1/1; real_inputs 1/1.5→1/1.5; value_evaluation 0.5/1.5→0.5/1.5; usable_outputs 1/1→1/1.
- Locator: §1.1.1；§5.4.1–5.4.5表5-7、5-8；结论.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/DATA_AVAIL.md, evidence/ACN_BOUNDS.json, evidence/ACN_DECISION.md, evidence/CAL.md.
- Rationale: 用途被表述为节点代理需求输入/后续采数安排，且给出接口和条件；实测功率映射、现场收益和运行约束评价尚未完成。该部分属于公开说明的后续工作；当前修订加强了验证次序，但未增加实践价值证据。
- Uncertainty: ACN边界材料未找到更晚记录，不足以证明存在兼容新数据；Office 1节点/字段/使用史待核查，不把未证实可能性算作缺陷。

## BR-12 — 结构、表达与学术规范: 8 → 8.5/10
- Components (baseline→current): structure 2.5/3→2.5/3; writing 2/3→2.5/3; scholarly_content 2.5/3→2.5/3; terminology 1/1→1/1.
- Locator: 摘要；§1.5–1.6；§3.5.4、§3.8.3；§5.4.1；局限与后续工作；表1-1及图表注释.
- Evidence read: manuscripts/baseline.md, manuscripts/current.md, evidence/NEAR76.md, evidence/NEAR.md, evidence/NEAR2.md.
- Rationale: 唯一写作分变化：摘要增加Caltech绝对MAE及JPL关系替换的精确相对差值；§5.4.1删除较泛的应用断言并明确以目标片左端τ和步长h索引；局限段落优先安排代理量测与ACN核查。以上改善读者定位数据、接口与下一步的能力。篇幅与重复仍高，故仅加0.5。
- Uncertainty: 材料包只检查图表标题/说明文字，未检视图像内容、版面和PPI；不据此判为通过或扣分。
