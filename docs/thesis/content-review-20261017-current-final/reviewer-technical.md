# Technical Review — Frozen Thesis Packet

**Assessment:** `FORMAL-20261017-CURRENT` / `PACKET-20261017-CURRENT-FINAL`  
**Rubric:** `EVCS-THESIS-CONTENT-1.0` (90 raw points; 0.5-point steps)  
**Reviewed manuscript:** `packet/manuscript.md`, SHA-256 `c9ec6d784adfbccec8feb54c448f2f4b6130d5a9891f7394023621be7696598b`  
**Review date:** 2026-10-17

## Overall assessment

**72.0/90 = 80.00/100.** This falls in the rubric's “内容良好” band. The central technical claims are mostly aligned with the evidence and are unusually careful about proxy labels, post-hoc reuse of fixed test periods, subgroup trade-offs, and the gap between model metrics and operational value. The main deductions reflect incomplete optimization/capacity controls, no genuinely unseen time period or independent data family, limited real-power validation, and a few provenance/physical-output gaps.

No core numerical contradiction or content-integrity blocker was established from the frozen packet. The principal results are supported as *conditional results on the inspected protocols*. They do not establish general cross-site or future-period performance, measured-power accuracy, or operating benefit.

## Criterion scores

### BR-01 — 选题意义与问题定义 (5): **4.0/5**

- **Manuscript locator:** Abstract; §§1.1.1–1.1.3; §§2.1–2.1.3; §5.4.5.
- **Evidence actually inspected:** `MAP.md` current claims table; `DATA-AVAIL-20261017.md` (local data period, missing later-period confirmation, candidate data limits); `PASSPORT.md` (JPL metadata and proxy-data identity); `manuscript.md` (stated ACN session source, target construction, and intended station-level use).
- **Rationale:** The object is specific: 15-minute per-node energy proxies reconstructed from session records, with within-station statistical relations and event/nonzero behavior. The manuscript distinguishes this from metered power and says what downstream questions might eventually use node forecasts.
- **Remaining gap:** The operational need is motivated but not quantified with a real station's capacity, service, or cost measurements. Data are not continuous meter power, and the packet confirms no verified unseen-period data.

### BR-02 — 研究问题、范围与题目一致性 (5): **4.5/5**

- **Manuscript locator:** Title and bilingual abstracts; §§1.4–1.6; §§2.1.1–2.1.3; §§3.6–3.8; §§4.5–4.6; §5.5; Conclusion.
- **Evidence actually inspected:** `MAP.md` (allowed conclusions and prohibited extrapolations); `QUALITY.md` (current protocol/evidence status); `DATA-AVAIL-20261017.md` (no confirmed new period); `S31.md` and `S32.md` (post-hoc status and limits).
- **Rationale:** The title's forecasting and mechanism-diagnosis scope is followed through the objectives, protocol definitions, results, and conclusion. The text repeatedly distinguishes overall model comparison, component increments, exploratory strata, and application exploration; it does not present MDP as a proven model-improvement procedure.
- **Remaining gap:** The title remains broader than the narrow evidence base unless readers carry the session-proxy and fixed-period qualifications with them. “Short-term load” could be mistaken for metered power without the stated proxy definition.

### BR-03 — 文献综述与缺口定位 (5): **4.0/5**

- **Manuscript locator:** §§1.2.1–1.2.4, especially Table 1-1 and its discussion; §§1.3–1.4; references [10], [12], [13], [67], [70]–[73].
- **Evidence actually inspected:** `NEAR.md`, `NEAR-20261016.md`, and `NEAR2.md` (source-level facts, readable source scope, unknowns, and comparison boundaries); `manuscript.md` Table 1-1 and cited-reference entries.
- **Rationale:** The nearest-work comparison names node grain, relation source, model path, and validation scope, and explicitly records what could not be verified. The manuscript correctly avoids claiming general graph convolution, multi-graph fusion, or gating as new and does not rank incompatible papers by reported MAE.
- **Remaining gap:** The review is not a systematic search, and some close-method details rest on abstracts, indexed excerpts, or publisher pages rather than full papers. The gap is therefore credible but not exhaustive; citation records were not independently rechecked against every original publication in this review.

### BR-04 — 理论基础与专业知识 (5): **4.0/5**

- **Manuscript locator:** §§2.1.1–2.1.3, Eqs. (2-1)–(2-2); §§3.2–3.5, Eqs. (3-3)–(3-16); §§4.2.5 and 4.4; §§5.2–5.4, Eqs. (5-1)–(5-7).
- **Evidence actually inspected:** `S31.md` and `S32.md` (target, graph-replacement, and unit/contrast definitions); `MDP.md` (L1/L2/L3 scope); `CAL.md` (finite-sample calibration calculation and limits); `NZ.json` and `DECISION.json` (zero/nonzero decomposition and synthetic-only decision status).
- **Rationale:** The units distinguish 15-minute energy from power; the forecast-origin/target timing is consistent across chapters; graph construction and message/gate equations are interpretable; the manuscript correctly separates parameter sensitivity from retraining effects and separates event labels from real-time event detection. The completion-time reconstruction is treated as another proxy, not truth.
- **Remaining gap:** The forecasting head is unconstrained in the written model, while nonnegative energy is the physical target; the manuscript does not report the frequency or impact of negative predictions or a nonnegative-output treatment. Uniform energy spreading also creates a substantial within-session timing approximation, and behavior-count arrival latency remains assumed rather than measured.

### BR-05 — 方法与实验设计 (10): **7.5/10**

- **Manuscript locator:** §§2.1.1–2.1.3; §§3.2–3.8, especially Tables 3-2, 3-3, 3-9, 3-11, 3-14, and 3-15; §4.3.
- **Evidence actually inspected:** `S31.md` and selected design/results fields in `S31AUDIT.json` (four same-parameter adjacency conditions, matching seeds/keys, paired block design); `S32.md` and `S32AUDIT.json` (fixed target sensitivity, six runs, common keys, contrasts); `MAP.md`; relevant portions of `RECOMP.json` and `MRECOMP.json`.
- **Rationale:** The event-time and JPL protocols use explicit input assumptions, held-out tuning/calibration segments, common prediction keys, three seeds, and matched-capacity TCN comparisons. The JPL relation experiment retains parameter slots and changes only a selected adjacency to self-loop; the node-gate control matches parameter count. Results report nonzero/event trade-offs rather than only the favorable aggregate metric.
- **Remaining gap:** One shared-gate seed in each protocol reaches the 60-epoch cap, leaving the gate increment conditional on that budget. AGCRN is not capacity-matched in the principal behavior-input comparisons; a behavior-only GRU baseline is absent. The two sites share ACN lineage and overlapping years. The added 031/032 and several subgroup analyses reuse already viewed test periods, so they are not independent confirmation.

### BR-06 — 可复现性与方法严谨性 (5): **4.0/5**

- **Manuscript locator:** §§2.1–2.2; §§3.6.1, 3.6.3–3.6.4, 3.7.1–3.7.2, 3.8.3–3.8.4; §§4.6 and 5.3.3–5.3.5.
- **Evidence actually inspected:** `packet-manifest.json`; `S31.md` and selected `S31AUDIT.json` contract/alignment/metric fields; `S32.md` and selected `S32AUDIT.json` manifest/key/metric fields; `ADAPT.md` and `ADAPTAUDIT.json`; relevant summary/check fields in `RECOMP.json` and `MRECOMP.json`; `PASSPORT.md`; `QUALITY.md`.
- **Rationale:** The packet hashes the manuscript and evidence files. The 031/032 audit records describe frozen inputs, source manifests, exact key/label/mask alignment, finite predictions, independent metric recalculation, and the limits of replay versus retraining. The JPL calibration arithmetic is independently checked; AdaptiveGraph's CUDA replay explains the backend-specific top-k tie behavior while preserving the missing original training Git identity.
- **Remaining gap:** `MRECOMP.json` records `manuscripts.after` as `f5ba2dd...`, while the frozen packet and current manuscript hash are `c9ec6d...`. The recomputed values inspected match the manuscript's key 031/032 results, but that record does not itself certify this exact frozen text version. Original AdaptiveGraph training-source identity is missing, and full raw data/checkpoints are not part of the portable packet.

### BR-07 — 工作量与解决问题能力 (10): **8.5/10**

- **Manuscript locator:** §§2.1–2.7; §§3.3–3.8; §§4.1–4.6; §§5.2–5.4; Appendix A.
- **Evidence actually inspected:** `S31.md`, `S32.md`, `MDP.md`, `ADAPT.md`, `CAL.md`, `MAP.md`, `QUALITY.md`, `PASSPORT.md`, `NZ.json`, and `DECISION.json` (data reconstruction, controlled model runs, audits, replay, calibration, and synthetic decision interface).
- **Rationale:** The work goes beyond fitting a predictor: it audits session identity and energy conservation, defines separate protocols, builds controlled gate and adjacency studies, diagnoses proxy-target sensitivity, reproduces prediction metrics, checks calibration failure, and terminates an unsuccessful residual-correction path without converting it into a contribution. The record shows substantial independent debugging and evidence reconciliation.
- **Remaining gap:** Considerable work is concentrated on one session-proxy task family and fixed historical periods. No real meter validation, deployed shadow run, or independently acquired future period tests the proposed application.

### BR-08 — 结果与证据充分性 (10): **8.0/10**

- **Manuscript locator:** §§3.6.2–3.8.4 (Tables 3-2, 3-3, 3-9, 3-11, 3-15); §§4.2–4.6 (Tables 4-2–4-8); §§5.3–5.4.
- **Evidence actually inspected:** Relevant metric and hash/alignment summaries in `RECOMP.json` and `MRECOMP.json`; `S31.md` and selected `S31AUDIT.json` comparison fields; `S32.md` and selected `S32AUDIT.json` model/stratum fields; `MDP.md`; `CAL.md`; `ADAPT.md` and `ADAPTAUDIT.json`.
- **Rationale:** The main global-MAE results, paired controls, target sensitivity, and key subgroup conclusions are supported by same-key audits and recalculation records. The central caveat is supported, not hidden: overall gains are largely zero-target-driven, the nonzero/event groups do not show broad dominance, behavior-relation evidence remains uncertain, and the relation gains are defined against self-loop replacements. JPL adds a re-fit at another site, and block intervals are not presented as site-sampling uncertainty.
- **Remaining gap:** There is no untouched time-period confirmation or different data family, and both sites use session-derived targets. Several 031/032 and subgroup findings are post-hoc. Evidence does not yet establish measured power validity, event protection, or practical effect beyond these protocols.

### BR-09 — 统计解释与结论边界 (10): **8.5/10**

- **Manuscript locator:** §§2.1.1–2.1.3; §§3.6–3.8; §§4.1–4.6; §§5.2–5.3; Conclusion.
- **Evidence actually inspected:** `S31.md` and selected `S31AUDIT.json` block/multiplicity fields; `S32.md` and `S32AUDIT.json` paired/block fields; `CAL.md`; `MAP.md`; `QUALITY.md`; `DATA-AVAIL-20261017.md`.
- **Rationale:** The text distinguishes seed SD from time-block uncertainty, uses Bonferroni-adjusted intervals for the three registered 031 global comparisons, labels the 032 and secondary strata post-hoc, reports mixed outcomes and negative findings, and keeps event labels from becoming claims of real-time detection. Calibration coverage shortfalls and widening intervals are plainly reported.
- **Remaining gap:** Three seeds and a small number of blocks cannot characterize full training or site-sampling uncertainty. Exploratory subgroup intervals are not multiplicity-adjusted, and the fixed test periods have been inspected. Coverage results are empirical for those periods, not distribution-free guarantees under their temporal dependence or shift.

### BR-10 — 贡献与创新 (10): **7.0/10**

- **Manuscript locator:** Table 1-1 and §§1.2.2–1.4; §§3.7–3.8; §§4.1 and 4.5; Conclusion.
- **Evidence actually inspected:** `NEAR.md`, `NEAR-20261016.md`, `NEAR2.md` (prior method families and comparison limits); `S31.md`/`S31AUDIT.json` (conditional relation increments); `MDP.md` and `MAP.md` (diagnostic scope and unsupported claims).
- **Rationale:** Contribution is framed as a task-specific combination of relation operationalization, controlled node-gate comparison, same-parameter adjacency replacement, and a diagnostic protocol that separates distinct evidence types. The literature comparison prevents broad claims of algorithmic novelty, and the JPL controls provide direct evidence for two conditional relation increments.
- **Remaining gap:** The advance is incremental and bounded to one proxy task architecture. The diagnostic protocol changes interpretation and reporting, but has not been shown to guide a modification that improves predictions. No new general-purpose method or cross-family capability is established.

### BR-11 — 专业实践价值 (5): **3.0/5**

- **Manuscript locator:** §§5.3.3–5.3.7; §§5.4.1–5.4.5, especially Tables 5-7 and 5-8; Conclusion “研究判断与使用条件”.
- **Evidence actually inspected:** `CAL.md` (JPL empirical coverage); `DECISION.json` (synthetic-only status, no observed savings); `NZ.json` (no comparison with TCN in its exploratory decomposition); `DATA-AVAIL-20261017.md` (no confirmed unseen or meter-validating dataset); `MAP.md` (real case remains materials-required); `DOCX-DELIVERY-20261017.md` only for delivery separation.
- **Rationale:** The manuscript defines a plausible screening/measurement/影子运行 interface and gives a reproducible synthetic feasibility example. It states that actual constraints, metering, warning quality, and cost are unverified and does not claim savings or safety.
- **Remaining gap:** No real meter mapping, operating constraints, service outcomes, alarm costs, or field/online latency measurements support deployment value. JPL event coverage remains below 50%; Caltech rolling event coverage remains 26.71%, so the current intervals do not support event protection.

### BR-12 — 结构、表达与学术规范 (10): **8.5/10**

- **Manuscript locator:** Entire `manuscript.md` (1763 lines), particularly §§1.2/Table 1-1, §§2.1–2.7, Tables 3-1–3-15, §§4.1–4.6, §§5.2–5.5, Conclusion, and Appendix A.
- **Evidence actually inspected:** Complete manuscript text and captions; `NEAR.md`, `NEAR-20261016.md`, and `NEAR2.md` for citation scope; `MAP.md` for claim mapping; `DOCX-DELIVERY-20261017.md` for the separate delivery audit record; `packet-manifest.json` for frozen scope.
- **Rationale:** Chapter progression is coherent, terminology and timing are unusually explicit, and tables/captions generally state units, denominators, grouping, and uncertainty type. Limitations are carried into the abstract and conclusion. The technical narrative avoids turning an exploratory or post-hoc result into a broader claim.
- **Remaining gap:** The narrative repeats limitations and evidence boundaries in several chapter summaries and conclusions. This review scored the Markdown content and captions; I did not independently render or inspect the embedded figure files, so their visual readability and plotted values are not certified here. The source packet also has a small text-to-recomputation-manifest fingerprint mismatch noted under BR-06.

## Major findings and blockers

1. **No content-integrity blocker identified.** The packet's core result claims agree with the selected independent metric summaries and experiment audits inspected. The main scientific claims remain conditional and are bounded in the text.
2. **External validity is the main research limitation.** JPL is another independently refit site, but it is in the same ACN data family and overlaps the Caltech period. The later 031/032 studies and JPL diagnostics reuse inspected test periods; none is a future-time confirmation.
3. **The target is a reconstructed session-energy proxy.** The manuscript quantifies energy conservation and probes completion-time truncation and a small current-shape sample, but it has no synchronized kWh meter validation. Uniform allocation can distort within-session timing; actual input arrival latency is also unknown.
4. **The strongest effects are not universal across strata.** MRG-GCN's aggregate advantage is driven principally by zero-target keys. The nonzero and event groups often favor TCN or fail to show a consistent difference. The conditional load/pattern relation results concern self-loop replacement within this architecture and budget.
5. **Version-binding gap:** `MRECOMP.json`'s `manuscripts.after` hash (`f5ba2dd...`) differs from the frozen Markdown hash (`c9ec6d...`). Its inspected 031/032 recomputations match the reported values, but the file should not be represented as binding its recomputation to this exact frozen manuscript without resolving or explaining the version difference.

**Content blockers:** None established from this review. The missing meter/future-period evidence limits claim strength but is candidly disclosed and does not invalidate the narrower proxy-task conclusions.

## Content score versus format/release acceptance

The **72.0/90 content score does not certify school-format or release readiness**. The packet's `DOCX-DELIVERY-20261017.md` describes a separate candidate DOCX (SHA-256 `94d91f9e...`) and WPS proof PDF (105 pages; SHA-256 `83131d07...`). That record reports a page-thumbnail review and manual spot checks, while also recording automated warnings, 40/46 PDF raster figures at about 600 PPI, and incomplete cover/signature/personal-information fields plus acknowledgments/publications pages still pending. The candidate DOCX is explicitly distinct from the current Markdown source and is not represented here as a fully cleared submission file. I read this delivery record but did not independently open or render the DOCX/PDF.

## Confidence and review scope

**Confidence: moderate-high for the manuscript's stated scope and displayed core arithmetic; moderate for overall content quality.** The full frozen Markdown manuscript was read. I inspected the packet manifest and rubric, the project scoring rubric/README, the indexed evidence files, experiment notes, and relevant audit/recomputation fields. I did not inspect original training code, raw session datasets, every stored prediction row, or embedded figure images, and did not open the linked historical scorecards or prior reviewer reports. The exact scope of evidence inspection is listed per criterion above.

