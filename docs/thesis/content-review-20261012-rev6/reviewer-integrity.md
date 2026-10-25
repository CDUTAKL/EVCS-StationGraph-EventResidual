# Independent thesis-integrity review and scoring proposal

## Scope and version

Reviewed the complete frozen manuscript [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261012-rev6/packet/manuscript-frozen.md) and the evidence artifacts listed in [evidence-manifest.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261012-rev6/evidence-manifest.json), packet `EVCS-THESIS-REV6-20261012`. The manuscript SHA-256 matches the specified value: `21e54e81244e6dc07721dfb1395fe31ba7ba71f7e8d99de805d8ebf61e021350`. Scoring uses `EVCS-THESIS-CONTENT-1.0`: 12 criteria, 90 raw points, 0.5-point steps.

This is one AI perspective, an unofficial simulation—not an institutional score or decision. I did not open the packet’s REV5 scorecard or forensic report, and did not solicit other reports. The comparison below uses only the REV5 vector supplied in the task and evidence in the REV6 packet.

The packet contains the full manuscript text and selected audit summaries, but not the underlying raw records, prediction bundles, or figure files for independent reruns or visual inspection. I reviewed text, tables, captions, the manifest, and listed audit artifacts; I did not independently rerun experiments or validate citations against source publications. WPS pagination and final-layout inspection are outside this review.

## Overall integrity judgment

The research spine is **supported**: the thesis defines a node-level session-derived proxy target, asks whether station-internal statistical relations and node-specific gating help forecast it, distinguishes predictive results from mechanism diagnosis, and limits its conclusions to the protocols actually tested. Chapter 5’s directionality, interval, and decision-interface work is consistently framed as exploratory support rather than another primary prediction claim.

No academic-integrity violation or contradiction in the headline values was identified in the inspected packet. This is not a forensic certification. A new, material reproducibility limitation is disclosed: 60 of 63 checkpoint forward checks passed; the three failures are the archived AdaptiveGraph runs. Their stored predictions reproduce the reported metrics arithmetically, but CPU replay does not reproduce those predictions; backend-dependent top-k ties are only a possible explanation. This limits independent confirmation of the close AdaptiveGraph comparison, not the checked MRG-GCN results.

## Research-spine map

| Link | Assessment and manuscript evidence |
|---|---|
| **Title → problem** | **Supported.** The title and §1.1–1.3 focus on short-term forecasts at charging-node scale, where aggregation obscures node heterogeneity. The text defines the modeled quantity as session-reconstructed proxy energy, not metered power. |
| **Problem → questions** | **Supported.** §1.3–1.4 pose three connected questions: whether relations and node differences improve prediction; what the diagnostic evidence says about model dependence and error composition; and what input and target conditions bound the claims. |
| **Questions → methods** | **Supported.** §1.4–1.6 and Fig. 1-2 map the Caltech work to LRE/MRG-GCN prediction and MDP diagnosis. JPL is explicitly a separate refit for prediction and node-gating comparisons, not an MDP replication. |
| **Methods → results** | **Partly supported, with limitations stated.** Chapter 3 reports separate Caltech retrospective, Caltech event-time, and JPL protocols; it avoids combining their error values. Results support bounded MAE claims, not universal or all-metric superiority. |
| **Results → contributions** | **Partly supported.** The strongest incremental evidence is the equal-parameter node-gating comparison, observed on Caltech’s event-time protocol and the JPL refit. Evidence does not establish independent positive benefit for learned β weights, every relation type, or every architectural component. |
| **Contributions → conclusion** | **Supported.** The conclusion preserves the same two core contributions and the same limits: proxy target, ACN-only overlapping periods, incomplete MDP replication at JPL, and no field validation. Chapter 5 remains exploratory. |

## Chapter progression

| Chapter | Role and incoming/outgoing link | Evidence anchors | Integrity observation |
|---|---|---|---|
| 1. 绪论 | Defines the need and gap; passes explicit questions and two core contributions to Chapter 2 and the study design. | §§1.1–1.7, especially §§1.3–1.6 (lines 110, 126, 140, 156) | Clear research role. The literature comparison is unusually careful about what source text could be checked, while full source verification is outside this packet review. |
| 2. 充电行为数据与特征分析 | Defines proxy target, protocol inputs, node screening, event labels, and data characteristics for Chapter 3. | §§2.1–2.7 (line 180 onward); Tables 2-1–2-3 | Strong boundary-setting. The 15-node sensitivity set has not been retrained, and inputs’ real reporting delay is unverified; both are disclosed. |
| 3. 多关系图预测 | Formalizes LRE/MRG-GCN, reports results across three distinct protocols, and summarizes component evidence for Chapter 4. | §§3.5–3.9; Tables 3-2, 3-3, 3-9, 3-12 (lines 687, 716, 882, 970) | Main evidence is connected to claims and the chapter explicitly rejects cross-protocol score comparisons. Several controls remain incomplete. |
| 4. MDP与可解释性分析 | Uses Caltech evidence to separate parameter sensitivity, a specified distillation attempt, and four-cell error composition; passes limitations to Chapter 5. | §§4.1–4.6; Tables 4-1, 4-4, 4-5 (lines 1001, 1110, 1137) | Strong scope discipline: none of these analyses is treated as causal identification; JPL is not presented as an MDP replication. |
| 5. 结构与预测支持探索 | Tests directionality, empirical interval coverage, and a prospective application interface; returns limitations rather than new headline prediction claims. | §§5.1–5.5; Tables 5-1, 5-5, 5-6, 5-9 (lines 1252, 1386, 1405, 1510) | The role is consistent with the title and conclusion, but the chapter ranges broadly. Its application value remains a defined interface and synthetic feasibility demonstration, not field validation. |
| Conclusion | Answers the questions, restates contribution evidence, and names the limits and next validations. | Conclusion §§研究工作总结–研究局限与后续工作 (lines 1524–1540) | Tracks the abstract and chapter summaries without converting proxy-forecast evidence into claims about metered power or deployment. |

## Contribution-to-evidence closure

| Contribution or claim | Evidence read | Closure judgment and remaining gap |
|---|---|---|
| **MRG-GCN for station-internal node proxy-load forecasting** | §3.6.2/Table 3-2: event-time MRG-GCN MAE 0.03890, 16.1% below parameter-matched TCN, while full AGCRN is lower. §3.6.3/Table 3-3: JPL refit MAE is below three preregistered comparators, with adjusted seven-day intervals above zero. §3.6.4/Table 3-4: retrospective Caltech comparison. | **Partly supported.** Main MAE evidence is direct and carefully bounded. JPL shows RMSE, event MAE, and nonzero-target MAE favor TCN; it is another ACN station in overlapping years, not a new data family or future period. |
| **Node-specific gate adds value over a shared gate** | §3.7.1/Table 3-9: equal-parameter, paired Caltech experiment reports 2.69% lower overall MAE; §3.6.3/Table 3-3 reports 2.71% at JPL. Both sections disclose budget/early-stop caveats and conditional time-block inference. | **Partly supported, strongest incremental component evidence.** Direction repeats across protocols; effect is specific to tested settings and does not establish broad generalization. Shared-gate runs reaching the training cap limit optimization-equivalence claims. |
| **LRE’s three relations and learned β as distinct sources of gain** | §§3.7.2–3.7.3, §3.8.1/Table 3-12, §4.2.5: single-relation results are close; equal-β retraining does not support independent positive β gain; frozen substitutions test dependence of the joint β–transform configuration. | **Partly supported.** The text appropriately avoids attributing independent value to β or claiming every relation is necessary. The net gain of the full relation design is not isolated from all other model differences. |
| **MDP as a diagnostic framework** | §§4.2–4.4/Tables 4-1, 4-4, 4-5: the text distinguishes frozen parameter sensitivity, a specified TCN distillation attempt, and four-cell error composition; arithmetic reconstruction closes. | **Partly supported.** The protocol organizes useful, auditable diagnostic questions, but it is not causal identification. Distillation does not control student capacity, input, and objective sufficiently to resolve structural substitutability. |
| **Chapter 5 support and application analysis** | §§5.2–5.4/Tables 5-1, 5-5, 5-6, 5-8–5-9: TE candidates do not survive family correction; interval coverage remains poor for events; rolling calibration improves coverage at large width cost; the LP case is synthetic. | **Exploratory only.** Claims are properly limited. No verified field benefit, metered-power validation, or real dispatch result is established. |

## Cross-chapter consistency

- **Target and units:** §§2.1, 3.2, and 5.4 consistently define `kWh/15 min` as session-reconstructed interval energy. The proxy-power conversion in §5.4 is explicitly only a unit conversion, not a metered-power result.
- **Protocol separation:** §§2.1.1–2.1.3 define distinct retrospective Caltech, event-time Caltech, and JPL refit protocols. Chapters 3–5 consistently keep their inputs, prediction keys, and inferential scope separate.
- **Time convention:** Abstract, §§2.1.1 and 3.2, and §5.4 define four target bins starting at release time and spanning one hour. No conflicting horizon convention was found.
- **Events:** The manuscript consistently distinguishes target-side `target_event` from retrospective `rule_trigger`, including their different information timing and denominators. The §4.4/Table 4-5 1.3933% event/rule-nontriggered share matches the abstract’s rounded 1.39%.
- **JPL scope:** Abstract, §§1.4–1.6, 2.1.3, 3.6.3, 3.8.2, and the conclusion consistently describe JPL as a separate station refit within the ACN family and overlapping years—not zero-shot transfer, future-period confirmation, or MDP replication.
- **Communication:** Chapter handoffs and chapter summaries generally reinforce the same boundaries. Some caveats recur often, making the text dense, but the repetition did not create a material scope contradiction in the inspected text.

## Integrity and blocker findings

**No critical academic-integrity blocker observed** for the core research spine. The packet supports the declared manuscript version and gives an auditable account of what was checked and what failed. I found no contradiction between the abstract, results tables, and conclusion for the main reported MAE values or event proportions.

**Localized reproducibility blocker / major limitation:** `checkpoint-replay-report.md` reports 60/63 forward checks passed; the three failures are archived AdaptiveGraph seeds. `paper-mae-archived-audit.json` reports 21/21 archived MAE mean/SD rows match. `paper-mae-forward-audit.json` reports 20/21 rows match; AdaptiveGraph does not. The report says the original training-time git commit is absent and the top-k tie explanation is plausible but unconfirmed. Therefore, the close MRG-GCN–AdaptiveGraph ranking is not independently confirmed by this CPU replay. This is not evidence that the original GPU predictions were fabricated or arithmetically inconsistent; the manuscript discloses the limitation. If that precise ranking is important, verify in the original CUDA environment or keep the claim explicitly secondary and non-significant.

**Other scope limits, not integrity violations:** Historical PCMCI+ lacks a complete p-value matrix and software version; no new training was performed; no field meter or reporting-delay validation is available; the included data and audits do not allow independent raw-data reruns. These limits are acknowledged in the manuscript and packet.

## Twelve-criterion scoring proposal

Scores follow the fixed rubric and are judgments in 0.5 increments. “Evidence read” denotes content reviewed in the frozen manuscript or listed audit files; it does not imply that I reran the experiment.

| Criterion | Score | Exact manuscript locator | Evidence read | Rationale and remaining gap |
|---|---:|---|---|---|
| BR-01 选题意义与问题定义 | **4.5/5** | Abstract, lines 3–14; §§1.1–1.3 (lines 35, 110) | Node-level heterogeneity, proxy-target definition, and three explicit research gaps/questions. | Specific, coherent problem tied to finer-grained station operation. Remaining gap: demand and operational value are not quantified with field evidence. |
| BR-02 研究问题、范围与题目一致性 | **5/5** | §1.4–1.6 (lines 126, 140, 156); conclusion (lines 1524–1540) | Two core contributions, JPL’s limited validation role, and Chapter 5’s exploratory role are restated consistently. | Strong alignment from title through methods and conclusion. Remaining gap: Chapter 5 is broader than the core prediction/diagnosis spine, but is explicitly subordinate. |
| BR-03 文献综述与缺口定位 | **4.5/5** | §§1.2.1–1.2.4 (lines 63–109), especially Table 1-1 (line 79) | Method-family synthesis; direct nearest-work comparisons; disclosed source-read limits for specific papers; gap narrowed to single-station nodes, proxy energy, and tested gate increment. | The review informs the research questions and avoids unsupported novelty claims. Remaining gap: source publications were not independently rechecked from this packet. |
| BR-04 理论基础与专业知识 | **4.5/5** | §2.1/equation (2-1), §2.1.1, §3.2, §§3.5.3–3.5.10, §5.4.1 | Target construction and units; input/horizon convention; distinction between β relation weights and node gate; proxy-energy to interval-average conversion. | Concepts, assumptions, and units are generally integrated and carefully bounded. Remaining gap: actual signal availability and physical power mapping are unverified. |
| BR-05 方法与实验设计 | **8/10** | §§3.6.1–3.6.3 (lines 644, 681, 716); §3.7.1/Table 3-9 (line 882) | Three distinct evaluation protocols, a preregistered JPL comparison with common prediction keys and adjusted block intervals, and equal-parameter gate comparisons. | Design is strong for the stated MAE questions. Remaining gaps: Caltech event-time AGCRN is not capacity-matched, no behavior-GRU control is reported, and shared-gate runs hit the training cap. |
| BR-06 可复现性与方法严谨性 | **4/5** | §3.6.1 and §3.6.3; packet `checkpoint-replay-report.md`, `paper-mae-archived-audit.json`, `paper-mae-forward-audit.json` | Prediction-to-metric audit reports 63/63 pass; checkpoint forward audit reports 60/63 pass; new-protocol MRG runs pass; packet records manifest and replay boundary. | Main new-protocol results are traceable and replayed within stated scope. Remaining gap: three AdaptiveGraph CPU forward failures, missing original training commit, no retraining, and no raw bundle in this review packet. |
| BR-07 工作量与解决问题能力 | **9/10** | §§2.1–2.2, 3.6–3.7, 4.2–4.4, 5.2–5.4 | Data reconstruction and screening; multi-protocol prediction; paired gate experiments; diagnostics; interval failure analysis; synthetic decision case. | Sustained and technically demanding master’s-level work with careful negative-result handling. Remaining gap: several explorations remain descriptive; no field evaluation. |
| BR-08 结果与证据充分性 | **8.5/10** | §§3.6.2–3.6.5; Tables 3-2–3-4, 3-6, 3-9; §4.4/Table 4-5 | Main MAE and gate claims have direct same-protocol comparisons; JPL comparison has adjusted time-block intervals; four-cell arithmetic reconstruction is stated. | Evidence supports bounded primary claims. Remaining gaps: mixed metric results; unresolved near-tie AdaptiveGraph replay; several component effects and external conditions remain untested. |
| BR-09 统计解释与结论边界 | **9.5/10** | §§2.1.1, 3.8.2, 4.2.5, 4.3.3, 5.3.6–5.3.7; conclusion | Clear separation of seeds, prediction keys, and time blocks; disclosure of post hoc analyses, shift, poor event coverage, and external-validity limits. | Exceptionally careful claim boundaries. Remaining gap: no unseen-period/data-family confirmation; event intervals remain far below target coverage. |
| BR-10 贡献与创新 | **7.5/10** | §§1.2.4, 1.4, 3.7.1, 3.8.1/Table 3-12, §4.5 | Literature comparison narrows novelty; same-parameter gate increment is tested; MDP findings are framed as a diagnostic organization, not a causal mechanism. | Credible incremental contribution, especially node-specific gating. Remaining gaps: core operators are established; learned β’s independent gain and broad novelty are not demonstrated. |
| BR-11 专业实践价值 | **3.5/5** | §§5.4.1–5.4.5; Tables 5-7 and 5-8 | Forecast-to-interface definitions, one historical proxy trajectory, and a synthetic constrained LP feasibility case. | Practical pathway is plausible and responsibly scoped. Remaining gap: no metered-power calibration, complete station load/capacity inputs, real vehicle constraints, or measured operational benefit. |
| BR-12 结构、表达与学术规范 | **9.5/10** | §§1.6, 2.7, 3.8–3.9, 4.5–4.6, 5.5, conclusion | Chapter roles, summaries, cross-references, terminology, units, and limitations checked against each other; packet local-repair audit reports equation order and targeted reference-range checks pass. | Coherent, traceable, and unusually explicit about scope. Remaining gap: repeated caveats make the prose dense; figures were not visually inspected, and layout review is separate. |

**Total: 78/90 raw = 86.67/100 normalized.** Simulated band: **内容良好** under the local rubric. This is not a CDUT A/B/C/D conversion or a prediction of the actual review outcome. Because the evidence check is partial with respect to raw reruns and visual figures, confidence is **medium for coherence and scope, medium-low for computational reproducibility beyond the listed audits**.

## Recommendation versus supplied REV5 vector

**I recommend one change: lower BR-06 from 4.5 to 4.0; keep the other eleven scores unchanged.**

| Criterion | REV5 vector | Proposal | Evidence-based reason |
|---|---:|---:|---|
| BR-06 可复现性与方法严谨性 | 4.5 | **4.0** | The REV6 packet adds the 2026-10-12 checkpoint replay audit: 60/63 forward checks pass, while all 63 archived prediction-to-metric checks pass. The three misses are the close-comparison AdaptiveGraph runs, and the original training commit is absent. This is a specific reproducibility gap, not evidence of arithmetic tampering. |

This changes the raw total from 78.5/90 to **78/90**, or 87.22 to **86.67/100**. I cannot attribute the original BR-06 rationale because the prior report was not inspected. Treat this as an independent score recalibration against the new replay evidence, not a measured change in thesis quality.

## Prioritized revisions

- **Blocker:** None observed for the thesis’s stated research spine or bounded primary claims.
- **Major, localized:** If the close AdaptiveGraph ranking is retained as a key comparison, replay its checkpoints in the original CUDA environment and record the actual top-k selections. If that evidence remains unavailable, preserve the manuscript’s current caveat and do not promote the small ranking margin to a robust superiority claim.
- **Major, future validation:** Metered-power alignment, reporting-delay validation, an unseen period or non-ACN data family, and field-operation evaluation remain required for deployment or broader generalization claims. The manuscript correctly presents them as future work.
- **Minor:** Consider consolidating repeated scope disclaimers where doing so would improve readability without weakening the distinction among proxy targets, protocols, and post hoc event labels.
