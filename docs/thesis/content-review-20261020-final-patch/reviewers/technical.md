# Technical reviewer report

- **Review context ID:** TECH-REV-20261020-T1-9f6c2b
- **Scope:** Frozen packet only: both manuscripts, reviewer instructions, rubric, anchors, manifest, and registered evidence files under `preparation-run01/reviewer-packet`.
- **Historical scores exposed:** No. The packet manifest says prior scorecards and reviewer reports are excluded; I did not inspect any external report or scorecard.
- **Review limits:** I did not inspect figure pixels or full-page layout. The manifest limits figure review to captions, so all visual content and PPI/page acceptance remain unchecked. I relied on the supplied audit summaries and did not independently rerun training or recover underlying experiment arrays. This is an unofficial content-review estimate, not an expert credential claim or institutional outcome.

## Overall assessment and revision effect

The thesis makes a technically coherent, carefully bounded case for forecasting **session-derived 15-minute node proxy energy**. It generally distinguishes that target from metered power, event-time inputs from retrospectively reconstructed targets, component-level contrasts from model rankings, and diagnostics from causal explanation. The primary Caltech and JPL results, post-hoc relation and target supplements, calibration analyses, and stated limits are broadly consistent with the packet evidence. The strongest unresolved technical constraints are target validity, unverified behavior-report latency, three-seed/fixed-period inference, and limited convergence/independent-confirmation evidence.

The baseline-to-current patch adds no new experiments. It promotes the JPL relation-replacement result into its own table, separates it from historical relation-subset sensitivity, clarifies that the completion-time-truncated target preserves the overall ranking **relative to the capacity-near TCN while nonzero-target MAE remains higher**, identifies the L1 checkpoint as Caltech’s retrospective protocol, and clarifies the distinct calibration paths. Most reported findings already existed in the baseline; scores remain unchanged where the underlying evidence and claim scope did not materially change. I raise BR-02 and BR-12 by 0.5 each for clearer closure and organization.

| Criterion | Baseline | Current | Change |
|---|---:|---:|---:|
| BR-01 | 4.0/5 | 4.0/5 | 0 |
| BR-02 | 4.5/5 | 5.0/5 | +0.5 |
| BR-03 | 4.0/5 | 4.0/5 | 0 |
| BR-04 | 4.5/5 | 4.5/5 | 0 |
| BR-05 | 8.0/10 | 8.0/10 | 0 |
| BR-06 | 4.0/5 | 4.0/5 | 0 |
| BR-07 | 9.5/10 | 9.5/10 | 0 |
| BR-08 | 8.0/10 | 8.0/10 | 0 |
| BR-09 | 8.0/10 | 8.0/10 | 0 |
| BR-10 | 7.5/10 | 7.5/10 | 0 |
| BR-11 | 3.0/5 | 3.0/5 | 0 |
| BR-12 | 8.0/10 | 8.5/10 | +0.5 |
| **Total** | **73.0/90 (81.11/100)** | **74.0/90 (82.22/100)** | **+1.0/90** |

Totals and normalized scores were computed from the 12 criterion scores by code, using the rubric’s 90-point denominator and two decimal places.

## Criterion-level review

### BR-01 — 选题意义与问题定义: 4.0/5 (baseline 4.0)

- **Components:** problem 2/2; significance 1.5/2; need 0.5/1.
- **Basis:** The object, granularity, target and purpose are concrete: a 15-minute, 10-node proxy-energy forecasting problem with a stated one-hour horizon (§1.1.2–1.1.3, §2.1.1, §3.2; lines 43–57, 216–233, 461–477). Motivation cites infrastructure growth and operational decisions, then supports sparsity and heterogeneity with data summaries (§1.1.1, §2.3; lines 35–49, 287–337). However, the operational need for forecasting these selected proxy nodes is not quantified against a measured decision threshold or actual site requirement.
- **Evidence:** `DATA_AVAIL`, `QUALITY`, `S32`, `S32AUDIT`.
- **Recommendation:** Keep the research question proxy-specific. If the introduction retains capacity-planning or dispatch motivations, add a concise statement of which decision could use these outputs and what measured input would be required; do not imply present operational validation.

### BR-02 — 研究问题、范围与题目一致性: 5.0/5 (baseline 4.5)

- **Components:** alignment 2/2; progression 2/2; closure 1/1 (baseline closure 0.5/1).
- **Basis:** Title, questions, methods, results and conclusions follow the same within-station node-forecasting and mechanism-diagnosis scope (§1.3–1.6, Chapters 2–5, conclusion; lines 110–169, 174–1625). The current abstract and §3.8.4 now say precisely that the alternative target preserves MRG-GCN’s overall-MAE ranking relative to the capacity-near TCN while its nonzero-target MAE remains higher (abstract line 11; §3.8.4, lines 1036–1056). The baseline phrase “global ranking preserved, nonzero group not improved” was less explicit about the comparison target; the current wording closes that ambiguity.
- **Evidence:** `S32`, `S32AUDIT`, `MRECOMP`.
- **Recommendation:** Retain the explicit comparator and subgroup direction in the abstract, chapter summary and conclusion. Keep the stated limits that the graph is fixed and the test period had already been inspected.

### BR-03 — 文献综述与缺口定位: 4.0/5 (baseline 4.0)

- **Components:** coverage 1/1; sources 1.5/2; gap 1.5/2.
- **Basis:** The review covers EV station/cluster graph forecasting, residential graph-gating precedents, event work, and proxy-load/residual forecasting (§1.2.1–1.2.4, Table 1-1; lines 61–108). The nearest-work discussion separates node granularity, target, inputs and validation, and avoids cross-paper MAE ranking. Source strength varies: some comparisons rest on abstracts, publisher-indexed fragments or partial text, but these limits are disclosed in Table 1-1 and the packet’s source audits. The gap is appropriately narrow, though it would benefit from a more systematic side-by-side contrast with [76], the closest proxy-EV forecasting precedent.
- **Evidence:** `NEAR`, `NEAR2`, `NEAR76`, `NEAR_20261016`.
- **Recommendation:** Preserve the source-visibility qualifications. Expand the [76] comparison by one compact row or paragraph covering target construction, forecast horizon, inputs, baseline/validation and the exact missing within-station component contrast. The current manuscript does acknowledge [76] and does not claim general proxy forecasting as novel.

### BR-04 — 理论基础与专业知识: 4.5/5 (baseline 4.5)

- **Components:** concepts 2/2; formulas 1.5/2; knowledge 1/1.
- **Basis:** The manuscript is consistent about kWh per 15-minute bin versus power, statistical rather than physical graph edges, shared relation-level β versus node-specific gates, and the non-causal status of MDP (§2.1–2.1.3, §3.3–3.5, §4.1–4.2; lines 178–258, 478–649, 1064–1126). Core formulas are dimensionally and conceptually plausible. Small remaining gaps include the estimator/embedding details behind the TE conditional-information formula and the fact that its lag-selection and block-shift procedure remains exploratory; the manuscript appropriately reports the full test family and correction outcome (§5.2.2–5.2.5; lines 1334–1397).
- **Evidence:** `QUALITY`, `MAP`, `S31`, `S31AUDIT`, `S32`, `RECOMP`.
- **Recommendation:** Add a short operational definition of the TE estimator’s conditioning/history and bin-boundary treatment if reproducibility requires it. Retain the explicit statements that the graph encodes statistical association and that β is not independently identifiable from relation-transform scales.

### BR-05 — 方法与实验设计: 8.0/10 (baseline 8.0)

- **Components:** information/split 2.5/3; comparators 1.5/2; controls 2.5/3; selection/budget 1.5/2.
- **Basis:** The three protocols distinguish retrospective inputs, event-time behavior inputs, target maturity, complete-window splits and their valid claim scope (§2.1.1–2.1.3, Tables 2-2 and 3-1; lines 216–258, 652–684). Capacity-near TCNs, full AGCRN, matched-parameter shared gates, self-loop relation replacement and multiple diagnostic controls provide meaningful contrasts (§3.6–3.8; lines 650–1056). The relation replacement retains all branches and parameters and controls non-graph initialization; the current patch presents it clearly as a post-hoc supplement (Table 3-10, §3.7.2; lines 895–937). Training and model selection are described in detail, but three seeds, inspected test periods, a shared-gate run reaching the cap, and incomplete sensitivity grids limit the strength of optimization and confirmation claims.
- **Evidence:** `PASSPORT`, `QUALITY`, `S31`, `S31AUDIT`, `S32`, `S32AUDIT`, `MAP`.
- **Recommendation:** Keep the revised separation between SG-EXP-031 and the older relation-subset sweep. In future confirmatory work, choose the shared-gate budget in advance and extend it symmetrically; rebuild the graph under the alternate target if claiming end-to-end target robustness.

### BR-06 — 可复现性与方法严谨性: 4.0/5 (baseline 4.0)

- **Components:** data/split 1/1; source/config 1/1.5; keys/metrics 1.5/1.5; environment/package 0.5/1.
- **Basis:** Data sources, node sets, splits, prediction keys, training setup and key artifacts are traceable. Independent arithmetic and key checks are reported for SG-EXP-031/032 and JPL calibration; AdaptiveGraph’s frozen checkpoints reproduce under the matched CUDA environment, while the native CPU top-k tie behavior is explained (§2, §3.6.1, §3.6.4, §3.8.3; lines 178–430, 652–684, 745–800, 1005–1035). Limits remain: old training Git identity is missing, several legacy runs were only forward-replayed, and manuscript readers cannot independently obtain restricted/raw source material from this packet.
- **Evidence:** `PASSPORT`, `QUALITY`, `ADAPT`, `ADAPTAUDIT`, `RECOMP`, `MRECOMP`, `S31AUDIT`, `S32AUDIT`.
- **Recommendation:** Where permissible, publish or archive immutable source/configuration snapshots and exact software lock files for the primary runs, with non-sensitive feature-generation instructions. Preserve the clear distinction between checkpoint replay and from-scratch reproduction.

### BR-07 — 工作量与解决问题能力: 9.5/10 (baseline 9.5)

- **Components:** technical work 4/4; problem-solving 3.5/4; integration 2/2.
- **Basis:** The work spans session reconstruction and quality gates, three protocols, model comparisons, matched controls, relation replacement retraining, target sensitivity, MDP diagnostics, conformal reliability and a decision-interface example (§2–5; lines 174–1625). It documents substantive problem discovery and correction, including proxy support-range and current-shape checks, environment-specific reproduction issues, and explicit termination of event-residual exploration. Not all sensitivity questions have been run, but they are named as future work rather than represented as completed.
- **Evidence:** `ACN_DECISION`, `ACN_RANGE`, `ACN_BOUNDS`, `ADAPT`, `ADAPTAUDIT`, `QUALITY`, `S31`, `S32`, `MDP`.
- **Recommendation:** Retain the distinction between completed diagnostics and future validation. No additional work is required to establish that substantial research and problem-solving effort was completed.

### BR-08 — 结果与证据充分性: 8.0/10 (baseline 8.0)

- **Components:** claim support 3.5/4; alternatives 2.5/3; robustness/scope 2/3.
- **Basis:** Primary results have direct, consistent support: Caltech event-time, JPL refit, matched gate comparisons, and the direction of relation and target sensitivity results agree with their registered audit summaries (Tables 3-2, 3-3, 3-9, 3-10, 3-15; lines 685–744, 874–937, 1036–1057). RECOMP and MRECOMP independently recalculate core arithmetic; S31/S32 audit records report exact keys and manifests. Alternatives are addressed through useful baselines and controls. Robustness is limited to another ACN site with overlapping years and a new proxy target on the already inspected Caltech period; no metered-power or untouched-period evidence is available. The patch improves presentation but does not add evidence, so the score is unchanged.
- **Evidence:** `RECOMP`, `MRECOMP`, `S31AUDIT`, `S32AUDIT`, `CAL`, `ADAPTAUDIT`.
- **Recommendation:** Keep Table 3-10 explicitly labeled as post-hoc and conditional. Do not turn the two positive relationship contrasts into universal or field-level conclusions; preserve the nonzero/label-event trade-off in the headline summaries.

### BR-09 — 统计解释与结论边界: 8.0/10 (baseline 8.0)

- **Components:** uncertainty 3/4; multiplicity 1.5/2; interpretation 3.5/4.
- **Basis:** The thesis separates seed variation, time-block resampling, repeated prediction keys, post-hoc strata and site-level uncertainty. It reports seed counts, block definitions, correction for three SG-EXP-031 primary relation contrasts, and limits for the fixed test period (§3.6.3, §3.7.1–3.7.2, §4.6, §5.3; lines 708–744, 874–937, 1267–1315, 1402–1535). Multiplicity is handled for selected contrast families, while some exploratory subgroup findings and repeated diagnostic questions are explicitly uncorrected. Three training seeds and one temporal test period cannot quantify the full training/site population uncertainty.
- **Evidence:** `S31`, `S31AUDIT`, `S32`, `S32AUDIT`, `CAL`, `RECOMP`, `MRECOMP`.
- **Recommendation:** Continue labeling post-hoc and subgroup intervals as descriptive. For future confirmation, predefine a small primary contrast family and use a new temporal test period; treat seed spread and fixed-period block intervals as different sources of variation.

### BR-10 — 贡献与创新: 7.5/10 (baseline 7.5)

- **Components:** prior difference 2/3; contribution 2.5/3; demonstration 3/4.
- **Basis:** The manuscript avoids claims of algorithmic novelty and limits the contribution to a controlled within-station proxy task, conditional relation/gate evidence, and a diagnostic protocol that changes interpretation and reporting decisions (§1.2.2, §1.3–1.4, §3.8.1, §4.5; lines 71–92, 110–137, 980–997, 1253–1266). The near-work audit identifies graph gating, relation fusion and EV proxy prediction precedents. The novel value is a credible empirical/diagnostic combination, but the diagnostic protocol has not been shown to improve predictions and key supplements reuse inspected test periods.
- **Evidence:** `NEAR`, `NEAR2`, `NEAR76`, `NEAR_20261016`, `S31AUDIT`, `S32AUDIT`, `MDP`.
- **Recommendation:** State the contribution as task-specific empirical evidence and revised research judgments. Keep “diagnosis-guided changes have not been shown to improve prediction” adjacent to the contribution summary.

### BR-11 — 专业实践价值: 3.0/5 (baseline 3.0)

- **Components:** use case 1/1; real inputs 1/1.5; value evaluation 0.5/1.5; usable outputs 0.5/1.
- **Basis:** The use case and required operating conditions are clear (§5.4.1–5.4.5; lines 1537–1610). Inputs come from real ACN sessions, but labels are reconstructed proxies and behavior arrival latency is unverified; there is no synchronized meter validation. The model is evaluated statistically and one fixed proxy trajectory is reported, while the dispatch LP is explicitly synthetic. These support a screening/data-collection interface, not a demonstrated operational benefit.
- **Evidence:** `PASSPORT`, `DATA_AVAIL`, `ACN_DECISION`, `S32`, `S32AUDIT`.
- **Recommendation:** Keep the “interface/next data collection” claim. Any stronger practice claim should await synchronized metering, input-arrival timestamps, site constraints and an operationally measured comparison.

### BR-12 — 结构、表达与学术规范: 8.5/10 (baseline 8.0)

- **Components:** structure 2.5/3 (baseline 2/3); writing 2.5/3; scholarly content 2.5/3; terminology 1/1.
- **Basis:** The current patch makes §3.7.2 easier to follow by separating the JPL controlled replacement table (Table 3-10) from historical relation-subset/sensitivity results (Table 3-11), and fixes the cross-reference in §3.6.3. The abstract and summary use a clearer model comparator for the completion-time result. This merits a 0.5 structural increase over the baseline. Across the thesis, the chapter path is coherent and terms are generally well defined; some repetition and dense tables remain. Citations are scoped by what was actually readable, and figures are discussed only from captions because image/page review was outside scope.
- **Evidence:** `LANGUAGE_REVIEW`, `LANGUAGE_AUDIT`, `MAP`, manifest figure scope.
- **Recommendation:** Preserve the table renumbering and cross-references; before final presentation, check every figure/table visually against these captions and inspect the rendered page layout. I did not perform those checks.

## Unresolved concerns and claim boundaries

1. **Proxy validity (evidenced limitation):** The primary label evenly allocates session energy across connection-to-disconnection intervals. The packet reports 28,403.239 kWh, or 30.66% of selected-node energy, allocated into complete intervals after valid recorded charging-completion times; the eight usable current traces are a convenience probe without voltage/power conversion. This is a material limit on claims about actual load shape and power. (§2.1.2; `S32`, `MRECOMP`, `PASSPORT`.)
2. **Input visibility (unverified concern):** Behavioral counts are assumed available at interval end; the archived data lack receipt timestamps, so latency and loss are not verified. The primary event-time task is cleaner in field choice but is not proof of deployable real-time availability. (§2.1.1, §2.1.3; `DATA_AVAIL`, `PASSPORT`.)
3. **External confirmation:** JPL is a separately refitted second site but comes from the same ACN system and overlapping years; it is not a future-period, different-data-family or zero-shot test. SG-EXP-031, SG-EXP-032, JPL calibration and JPL MDP reuse inspected test periods. (§2.1.3, §3.8.2–3.8.4, §4.6, §5.3.5; `S31AUDIT`, `S32AUDIT`, `CAL`, `MDP`.)
4. **Uncertainty and optimization:** Three seeds do not estimate the population of training outcomes well; time-block intervals condition on fixed test periods. One shared-gate seed per site reaches the 60-epoch cap; SG-EXP-031’s runs stopping before the cap do not themselves prove full convergence. (§3.6.3, §3.7.1–3.7.2, §3.8.3; `S31`, `S31AUDIT`, `PASSPORT`.)
5. **Incomplete sensitivity:** The 15-node candidate set, input length and rule threshold/extension grids are not fully rerun; the thesis says this rather than claiming robustness. (§2.2, §3.7.2; `S31`, `QUALITY`.)
6. **Reproduction and visual checks:** Missing old training Git identity and historical environment differences remain; the AdaptiveGraph CUDA checkpoint replay resolves the reported matched-environment forward discrepancy but is not a from-scratch reproduction. Figure pixels and page layout were not inspected. (§3.6.1, §3.6.4; `ADAPT`, `ADAPTAUDIT`, manifest.)

## Evidence reviewed

The packet’s registered report/evidence set was reviewed: `ACN_DECISION`, `ACN_RANGE`, `ACN_BOUNDS`, `ADAPT`, `ADAPTAUDIT`, `CAL`, `DATA_AVAIL`, `LANGUAGE_REVIEW`, `LANGUAGE_AUDIT`, `MAP`, `MDP`, `MRECOMP`, `NEAR`, `NEAR2`, `NEAR76`, `NEAR_20261016`, `NZ`, `PASSPORT`, `QUALITY`, `RECOMP`, `S31`, `S31AUDIT`, `S32`, and `S32AUDIT`. `NZ` is identified as exploratory review-time decomposition, not a manuscript result, and was not used to increase scores.
