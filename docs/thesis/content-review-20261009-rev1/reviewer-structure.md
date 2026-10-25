# Raw content review — structure, expression, and professional application

**Assessment status:** exploratory single-perspective simulation; not an institutional score or decision.  
**Rubric:** `EVCS-THESIS-CONTENT-1.0`; 12 rows, project-fixed 90-point raw scale, 0.5-point increments. This report intentionally gives no aggregate score or grade band.  
**Review date:** 2026-10-09.  
**Manuscript reviewed:** `docs/thesis/thesis-manuscript.md`, SHA-256 `6402f06a4deff473f09d75824bbab08023c34d9246408dca7a31fac71bf22ca0`. Hash matches the assigned frozen version.  
**Coverage:** full Markdown manuscript (all chapters, conclusion, figures/tables and reference list), with emphasis on whole-thesis structure, expression, and professional application. All 12 criteria were assessable; **N/A: none**.

## Evidence packet opened

Review packet ID: `EVCS-THESIS-CONTENT-1.0 / content-review-20261009-rev1`.

- `docs/thesis/AGENTS.md`, `docs/thesis/scoring/README.md`, and `docs/thesis/scoring/rubric.json`.
- `docs/thesis/experiment-reports/SG-EXP-029-node-composition-sensitivity.md` — SHA-256 `c420caf2482d0274e5e93e2b8eb93b0711079e893e01488a6d36a79874052c2c`.
- `docs/thesis/experiment-reports/SG-EXP-027-paired-gate-control-report.md` — SHA-256 `8d219e2b0a76a6adcaf153dc9a6e7f5dd35c98c6fecab57d9f07ea424fcb0511`.
- `docs/thesis/experiment-reports/SG-EXP-028-jpl-independent-site-validation-report.md` — SHA-256 `edf3f29b5fd1675d7f139b15c431280fef8a0f691b9505985f3e4a1cb67ebc06`.
- `docs/thesis/experiment-reports/EXP-024-026-no-training-supplement.md` — SHA-256 `d7eec350e2fbf366b5a21e5e8d44bfd4c9bd23ae8e38236c875c537543cd7f21`.
- `docs/thesis/experiment-reports/EXP-023-independent-calibration.md` — SHA-256 `9dcacb950e49188e11ae6bf0d557e9ef81b5a11dc396789264be4dd18e43ccfe`.
- Application evidence: `outputs/analysis/SG-EXP-021-demand-warning/final/report.md` (SHA-256 `95be0da00c6122107bdfb894766b38e9d03261e6b6b487a2396d56a7b52df91e`); `outputs/analysis/SG-EXP-022-forecast-operation-interface/audit.json` (SHA-256 `bd0f8c823c34512194bf9578ac72708fa2277093a776c5863eb1b7ac3ef81ab7`); and `outputs/analysis/SG-EXP-026-charging-decision/{audit.json,actual_thesis_case_status.json,shadow_plan.json}`.
- Nearest-work source checks: the original CSEE article PDF for Huang et al. [10] (`https://epjournal.csee.org.cn/rc-pub/front/front-article/download/96713687/lowqualitypdf/%E8%AE%A1%E5%8F%8A%E5%A4%9A%E5%85%AC%E5%85%B1%E5%85%85%E7%94%B5%E7%AB%99%E5%B7%AE%E5%BC%82%E5%8C%96%E8%80%A6%E5%90%88%E5%85%B3%E8%81%94%E7%9A%84%E7%94%B5%E5%8A%A8%E6%B1%BD%E8%BD%A6%E5%85%85%E7%94%B5%E8%B4%9F%E8%8D%B7%E6%97%B6-%E7%A9%BA%E7%9F%AD%E6%9C%9F%E9%A2%84%E6%B5%8B.pdf`) and Wiley’s original STGNet article [92] (`https://doi.org/10.1002/ese3.1633`).

**Review limits:** I did not open previous scorecards, earlier reviewer reports, or forensic-review documents. I read SG-EXP-029 itself but did not follow its link into older review folders. The SG-EXP-003 legacy training/prediction artifacts were not available in the evidence opened for this assignment; I therefore treat its 0.01376 result as manuscript-reported and do not claim an independent recalculation. I did not independently re-run the reference-closure parser or audit all 92 cited sources; the coordinator separately reported corrected closure validation. Figure captions and their stated scope were read in the manuscript, but this was not a page-by-page visual audit of every rendered graphic. No manuscript edits were made.

## Independent criterion scores

### BR-01 — 选题意义与问题定义: **4.5 / 5**

- **Manuscript locator:** Abstract; §§1.1.1–1.1.3; §§2.1.1–2.1.3; §§5.5.1–5.5.2.
- **Evidence opened:** Manuscript; `SG-EXP-029` for the station-level scope caveat; `EXP-024-026-no-training-supplement.md` for the session-support and limited-current-shape checks; SG-EXP-028 report for the independent JPL data task.
- **Rationale:** The problem is concrete: forecast 15-minute, node-level proxy energy from discrete charging-session data, where aggregation hides node differences and online meter power is unavailable. The task boundaries are unusually explicit, and the motivation links node-level forecasts to capacity checks and charging coordination without equating the proxy to measured power.
- **Remaining gap:** Need is motivated from general station operations rather than quantified with an operator-defined decision threshold, field workflow, or measured operational consequence. The topic’s practical significance remains plausible, not field-demonstrated.

### BR-02 — 研究问题、范围与题目一致性: **4.5 / 5**

- **Manuscript locator:** Title; Abstract; §§1.3–1.6; §§3.8.2–3.9; Conclusion, “研究工作总结” and “主要研究结论”.
- **Evidence opened:** Full manuscript; SG-EXP-027 and SG-EXP-028 reports; SG-EXP-029 report.
- **Rationale:** The title’s node-level short-term prediction and mechanism-diagnosis claims map to the stated questions, MRG-GCN/MDP methods, and reported results. The three protocols are kept distinct, and the JPL experiment is correctly scoped as refitting at another ACN site rather than zero-shot transfer or future-period validation. Chapter 5 is labeled as exploratory support rather than a third core contribution.
- **Remaining gap:** The title emphasizes “mechanism diagnosis,” while the most useful evidence establishes sensitivity to a learned joint parameter configuration, a bounded distillation attempt, and descriptive error composition—not a physical mechanism. The manuscript explains this boundary, but the title may still invite a stronger causal reading.

### BR-03 — 文献综述与缺口定位: **4.5 / 5**

- **Manuscript locator:** §§1.2.1–1.2.4, especially Table 1-1 and the synthesis in §1.2.4.
- **Evidence opened:** Manuscript and original-source checks for [10] and [92]. The CSEE paper [10] confirms public charging stations as graph nodes, adaptive spatiotemporal graph construction, node-adaptive parameters, GRU, and module comparisons; the original STGNet article [92] confirms residential-unit forecasting, adaptive and temporal-similarity neighbors, gated fusion, node-specific graph convolution, and BiGRU. Links are listed in the evidence-packet section.
- **Rationale:** The review moves beyond listing model names by comparing node granularity, relation source, architecture, validation scope, and the limits of cross-paper numerical comparison. It explicitly acknowledges that adaptive graphs, gating, and node-specific parameters pre-exist, then narrows the gap to within-station charging-node proxy forecasting and a task-specific diagnostic sequence.
- **Remaining gap:** The nearest-work comparison is selective, and at least some entries (including [67]) are explicitly based on abstract-level evidence rather than full-method verification. The gap is credible and carefully bounded, but it is not an exhaustive original-source synthesis of every close EV-charging and load-forecasting study.

### BR-04 — 理论基础与专业知识: **4.5 / 5**

- **Manuscript locator:** §§2.1–2.6 (Eqs. 2-1–2-2); §§3.2–3.5 (Eqs. 3-1–3-15); §§4.2–4.4; §§5.2–5.5 (Eqs. 5-1–5-8).
- **Evidence opened:** Manuscript; `EXP-024-026-no-training-supplement.md` for proxy-energy conservation, endpoint support, and the limited current-shape probe; `EXP-023-independent-calibration.md` for calibration and interval-scoring definitions; the SG-EXP-028 report for JPL target/input separation.
- **Rationale:** The manuscript consistently distinguishes interval energy from instantaneous or metered power, describes units and the uniform-allocation assumption, and carries the limitation through equations, metrics, figures, and application formulas. Model equations, normalization, graph construction, and the roles of relation and node gates are generally well integrated with the experiment design. It also separates observation, fixed-parameter intervention, retraining comparison, and descriptive error decomposition.
- **Remaining gap:** Some technical claims remain conditional on implementation records not independently inspected here, especially the legacy result chain. The directionality section uses exploratory TE/PCMCI+ thresholds without multiplicity correction; the text appropriately narrows interpretation, but the evidence is not enough to promote those candidates to a physical or causal account.

### BR-05 — 方法与实验设计: **7.5 / 10**

- **Manuscript locator:** §§2.1.1–2.2; §§3.6.1–3.7.5; §4.2–4.4; §5.3.2–5.3.7.
- **Evidence opened:** SG-EXP-027 paired-control report; SG-EXP-028 JPL report; SG-EXP-029 node-composition report; EXP-023 independent-calibration report.
- **Rationale:** The JPL refit has a clear fixed protocol, independent node selection, complete window separation, shared prediction keys, matched-size TCN and shared-gate controls, three seeds, checkpoint selection, and a pre-specified primary MAE endpoint with corrected time-block intervals. The Caltech event-time paired gate experiment changes the node dimension of the gate while holding parameter count, initialization, optimizer, data, and selection rules fixed. The MDP separates distinct questions instead of treating parameter images as causal explanations.
- **Remaining gap:** The legacy Caltech main protocol uses final session fields and has disclosed preprocessing and window-boundary limitations. The event-time Caltech comparison still omits some fair behavior-input controls (for example, GRU/MLP and a size-matched AGCRN), while broader sensitivity settings remain unrun. JPL is one overlapping-period site in the same ACN data family, not an external-domain or future-time design.

### BR-06 — 可复现性与方法严谨性: **4.0 / 5**

- **Manuscript locator:** §§2.1.1–2.2; §§3.2, 3.5.7, 3.6.1, 3.6.3; §§3.7.1, 3.7.5; §§4.4.2–4.4.3.
- **Evidence opened:** SG-EXP-027 and SG-EXP-028 reports, including hashes/manifest checks and key-alignment scopes; SG-EXP-029 report; `outputs/analysis/SG-EXP-022-forecast-operation-interface/audit.json`; `outputs/analysis/SG-EXP-026-charging-decision/audit.json` and case-status JSON.
- **Rationale:** For the new paired-control and JPL evidence, data hashes, run counts, seeds, split/window contracts, prediction keys, training configuration, and independent metric checks are documented in inspected reports. The manuscript gives enough task and model detail to understand the analysis and separates seed variability from temporal-block variability.
- **Remaining gap:** The current opened packet does not include the raw SG-EXP-003 prediction/manifests needed to independently reproduce the legacy headline result; the report relies on experiment IDs and manuscript summaries for that central historical chain. Reproduction of the full legacy pipeline therefore remains less directly auditable than the paired gate and JPL results.

### BR-07 — 工作量与解决问题能力: **8.5 / 10**

- **Manuscript locator:** §§2.1–2.6; §§3.3–3.7; §§4.2–4.4; §§5.2–5.5; Conclusion.
- **Evidence opened:** SG-EXP-027 and SG-EXP-028 reports; SG-EXP-029 report; EXP-023 and EXP-024–026 reports; SG-EXP-021 warning analysis, SG-EXP-022 fixed-origin audit, and SG-EXP-026 synthetic decision evidence.
- **Rationale:** Submitted work shows substantial technical problem solving across session reconstruction, node selection, multiple model/protocol comparisons, controlled node-gate ablation, parameter sensitivity, distillation, error decomposition, calibration, and a decision-interface prototype. The work distinguishes completed experiments from negative, inconclusive, and uncompleted items rather than treating every exploration as a contribution.
- **Remaining gap:** The strongest problem-solving evidence is still offline and proxy-based. No synchronized meter evaluation, real operational constraints, unseen-period confirmation, or executed field workflow demonstrates the final professional application.

### BR-08 — 结果与证据充分性: **8.0 / 10**

- **Manuscript locator:** §§3.6.2–3.8; §§4.2.4–4.4; §§5.3.3–5.3.7; §§5.5.3–5.5.5.
- **Evidence opened:** SG-EXP-027 and SG-EXP-028 reports; SG-EXP-029 report; EXP-023 independent-calibration report; SG-EXP-021 demand-warning report; SG-EXP-022 fixed-origin audit; SG-EXP-026 synthetic-only audit and real-case status.
- **Rationale:** The main new point-prediction result has common-key and independently checked support; JPL provides three corrected comparisons for its declared overall-MAE endpoint. The equal-parameter node-gate effect is reproduced in two separate protocols and the SG-EXP-029 leave-one-node audit shows the historical point estimate does not reverse after removing any single evaluated node. Results also report important non-wins: TCN’s better JPL RMSE/event/nonzero errors, weak event-window coverage, and the fixed example’s missed proxy demand rise.
- **Remaining gap:** These are not independent site-family or future-period confirmations. Several Caltech headline/MDP values come from the legacy artifact chain not independently opened in this review. Event and nonzero outcomes remain weak or adverse in places, and the synthetic decision result does not validate real operating value.

### BR-09 — 统计解释与结论边界: **8.5 / 10**

- **Manuscript locator:** §§2.1.1–2.1.3; §§3.6.1–3.8.2; §§4.2.5, 4.3.3, 4.4.4, 4.6; §§5.2.2–5.2.6, 5.3.2–5.3.7, 5.4.3, 5.5.5; Conclusion.
- **Evidence opened:** SG-EXP-027, SG-EXP-028, and SG-EXP-029 reports; EXP-023 independent-calibration report; SG-EXP-021 warning analysis and SG-EXP-022 audit.
- **Rationale:** The text repeatedly distinguishes training-seed spread, fixed-test time-block intervals, and any claim about independent sites; it labels post-hoc analyses, avoids calling the JPL result zero-shot transfer, and discloses the proxy target, test-period reuse, limited seed count, incomplete event coverage, and non-significant exploratory scope. It does not convert β interventions into an independent β gain or call the MDP decomposition causal.
- **Remaining gap:** TE/PCMCI+ findings are based on nominal uncorrected tests; some block analyses are post-hoc conditional summaries, and conformal coverage remains well below 90% (especially for events) even after rolling calibration. These are disclosed, but they limit the strength of any positive reliability or generalization inference.

### BR-10 — 贡献与创新: **7.5 / 10**

- **Manuscript locator:** §§1.2.2–1.4; §§3.5.8–3.5.10, 3.7.1, 3.8.1; §§4.1–4.6; Conclusion.
- **Evidence opened:** Manuscript; official original articles for [10] and [92]; SG-EXP-027 and SG-EXP-028 paired-gate/JPL reports; SG-EXP-029 report.
- **Rationale:** The contribution is credibly framed as a specific combination and evaluation in the within-station charging-node proxy task, not as invention of graph convolution, gated fusion, adaptive graphs, or node-specific parameters. The same-parameter gate comparison and second-site refit provide direct evidence for a narrower node-differentiation increment; the MDP is presented as a task-specific diagnostic organization with explicit limits.
- **Remaining gap:** Method components have close precedents, and MDP mainly combines established intervention, distillation, and error-decomposition tools. The evidence establishes incremental task-specific value, not a broadly new mechanism or a validated new forecasting capability beyond this setting.

### BR-11 — 专业实践价值: **3.5 / 5**

- **Manuscript locator:** §§1.1.1, 1.4; §§5.5.1–5.5.5; Table 5-9; Conclusion, “工程含义与适用范围”.
- **Evidence opened:** SG-EXP-021 demand-warning report; SG-EXP-022 forecast-interface audit and case CSV; SG-EXP-026 audit, actual-case status, and shadow-plan JSON; EXP-024–026 supplement; SG-EXP-029 for station/site limits.
- **Rationale:** Professional relevance is concrete: the thesis maps predicted interval energy to proxy-equivalent average power, defines a safe human-review interface, handles missing/stale input, and provides a constrained shadow-plan LP. The fixed-origin example and warning results expose how a proxy-demand rise can be missed; the synthetic LP checks one request under explicit service and capacity limits.
- **Remaining gap:** There is no synchronized meter mapping, complete station load, equipment rating, real vehicle request/price input, or field evaluation. The actual thesis case is `MATERIALS_REQUIRED`; the LP audit is explicitly synthetic-only, with no dispatch, savings, or control claim. Practical value is therefore plausible but not validated for use.

### BR-12 — 结构、表达与学术规范: **8.0 / 10**

- **Manuscript locator:** Full manuscript; particularly chapter transitions §§1.3–1.7, 2.7, 3.8–3.9, 4.5–4.6, 5.6 and the Conclusion; Tables 1-1, 2-2, 3-12, 4-1, and 5-10.
- **Evidence opened:** Full manuscript, including figure/table captions and the complete reference list; the nearest-work source checks for [10] and [92]. The coordinator separately reported that corrected parser validation found all 92 references cited, no undefined/unused entries, and sequential numbering; I did not re-run that parser.
- **Rationale:** The sequence from task definition through data, prediction, diagnostic evidence, reliability, and application boundary is easy to follow. Tables compare methods and protocol scope rather than only reporting numbers. Terminology, units, table notes, and caveats are generally consistent; technical claims are usually separated from measured or proxy evidence. The tone is restrained, and the manuscript reports negative or partial outcomes.
- **Remaining gap:** Scope caveats recur across the abstract, protocol descriptions, chapter summaries, and conclusion; some repetition could be shortened without losing safeguards. Several exploratory sections are dense, with many nested qualifiers and cross-references, which slows reading. The supplied Markdown contains explicit handoff placeholders for the generated contents page, acknowledgements, and author-results section; these are not scored as institutional layout, but they need completion or removal before treating the manuscript package as finished.

## N/A and aggregation note

No criterion was marked N/A. No total, normalized percentage, simulated band, or defense recommendation is supplied because this is the requested raw, unaggregated perspective report; the absence of an aggregate is not a withheld assessment due to missing criteria.
