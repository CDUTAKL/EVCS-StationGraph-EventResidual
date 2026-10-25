# Independent content review — literature and nearest-prior-art perspective

- Rubric: EVCS-THESIS-CONTENT-1.0 (effective 2026-10-09), unofficial simulation.
- Review date: 2026-10-09.
- Frozen manuscript: docs/thesis/thesis-manuscript.md
- SHA-256 verified before review: 6402f06a4deff473f09d75824bbab08023c34d9246408dca7a31fac71bf22ca0
- Scope: full manuscript, the supplied nearest-literature memo, official-source evidence where accessible, and relevant method/experiment evidence. This is one isolated review perspective. No manuscript edits were made. I did not open prior scorecards, earlier reviewer reports, or forensic-review documents.
- N/A: none. The packet permits an independent judgment on all 12 criteria. This raw report does not aggregate scores or assign an overall band.

## Evidence read

I read the complete frozen manuscript and docs/thesis/content-review-20261009/nearest-literature-review.md. For nearest work, I opened the official CSEE journal page and full paper for [Huang et al. [10]](https://epjournal.csee.org.cn/en/article/doi/10.13334/j.0258-8013.pcsee.231589/), the official Wiley full article for [Feng et al. [92]](https://scijournals.onlinelibrary.wiley.com/doi/10.1002/ese3.1633), and official summaries/abstracts for [12](https://opaj.napstic.cn/periodicalArticle/0120240500039734), [13](https://zjdl.cbpt.cnki.net/portal/journal/portal/client/paper/0ac86a2974206d693037fe6da5b72bcd), and [67](https://orbit.dtu.dk/en/publications/causality-aware-multi-graph-convolutional-networks-with-critical-/). For [Xie et al. [70]](https://www.sciencedirect.com/science/article/pii/S1364032124005811), the publisher page was not fully retrievable; I used its official indexed/publisher summary only. I did not infer details absent from those sources.

For method and result checks, I read the EXP-019, EXP-027, and EXP-028 handoff/preregistration and report files under docs/thesis/, including docs/thesis/experiment-reports/EXP-019-eventtime-v1-phase2.md, SG-EXP-027-paired-gate-control-report.md, and SG-EXP-028-jpl-independent-site-validation-report.md. I also opened the available EXP-027 recovered summaries and the EXP-028 analysis report, model summary, paired intervals, checkpoint lock, and test-export state under /Users/xushuyuan/Documents/Codex/2026-10-05/sg-exp-028-jpl/outputs/. I read the EXP-029 node-composition sensitivity report as supporting, explicitly post-hoc evidence. I did not rerun training or independently reproduce the complete experiments.

## Criterion scores

### BR-01 — 选题意义与问题定义

**Score: 4.0 / 5**

**Manuscript locator:** §§1.1.1–1.1.3, lines 39–61; scope statement §1.4, lines 128–141.

**Evidence actually opened:** The manuscript specifies intra-station charger-node forecasting at 15-minute resolution from session records, distinguishes that reconstructed proxy energy from metered power, and motivates sparse/heterogeneous node series and event windows. It cites national public-charger growth and operational needs in lines 41–45, and explicitly says the graph is statistical rather than electrical topology in line 57.

**Rationale:** The object, temporal granularity, data source, prediction target, and central difficulty are concrete. The deliberate proxy-versus-meter boundary is especially clear. The demand is plausible and connected to station operations, rather than being only a generic claim about EV growth.

**Remaining gap:** The cited infrastructure growth is contextual evidence; the manuscript does not quantify an operator’s unmet node-level forecasting need, measured constraint violations, or decision value. The need for finer-grained station forecasts is argued, not established by a field evaluation.

### BR-02 — 研究问题、范围与题目一致性

**Score: 4.5 / 5**

**Manuscript locator:** Title/front matter, line 1; §§1.3–1.7, lines 112–177; chapter summaries and conclusion, especially §§4.5–4.6, 5.6, and lines 1514–1539.

**Evidence actually opened:** The full manuscript links the three questions to multi-relation prediction, bounded mechanism diagnosis, and information/uncertainty limits. Section 1.4 limits the primary claim to Caltech session-derived proxy energy and describes JPL as a preregistered refit within the same ACN data system. The chapter-5 summary and conclusion preserve those boundaries and say the exploratory sections do not add point-prediction claims.

**Rationale:** Title, target, method, validation, and conclusion close around the same narrow task. The manuscript repeatedly distinguishes the older retrospective protocol from the stricter event-time protocol and does not present JPL as zero-shot transfer or real-power validation. Exploratory analysis is labeled as such.

**Remaining gap:** “Mechanism diagnosis” and the thesis’s multi-part scope are broad relative to the narrow causal status of the evidence. The text usually repairs that risk by defining the layers as parameter sensitivity, a bounded student attempt, and error decomposition; the title-level framing still asks the reader to hold several distinct evidence types together.

### BR-03 — 文献综述与缺口定位

**Score: 4.0 / 5**

**Manuscript locator:** §§1.2.1–1.2.4, lines 65–110; Table 1-1, lines 81–90; gap statement §§1.3–1.4, lines 112–141.

**Evidence actually opened:** In addition to the manuscript and nearest-literature-review.md, I read the official full [Huang et al. [10]](https://epjournal.csee.org.cn/en/article/doi/10.13334/j.0258-8013.pcsee.231589/) paper and [STGNet [92]](https://scijournals.onlinelibrary.wiley.com/doi/10.1002/ese3.1633). The former documents adaptive graph modeling and node-adaptive parameters with module ablations for station-level EV charging forecasts. STGNet documents gated fusion of DTW and adaptive graph branches, node-specific GCN parameters, and ablations for residential load. I checked the official abstracts/pages for [12], [13], and [67]; [70] was available only through publisher/indexed summary evidence.

**Rationale:** The review moves beyond model-name listing and compares node granularity, relation source, architecture, validation scope, and information-boundary evidence. Most usefully, it concedes that adaptive graphs, node-specific parameters, and gated fusion are prior art, then places its gap at within-station charger nodes, relation separation, matched node-gate testing, and task-specific diagnostics. It also avoids cross-paper numeric ranking.

**Remaining gap:** The nearest EV studies [12], [13], [67], and especially [70] were not compared from full text; the manuscript appropriately marks this, but it limits the depth of the nearest-prior-art audit. No cited paper was rerun under the same ACN split, inputs, and prediction keys, so the proposed task-specific distinction is reasoned from published descriptions rather than a direct same-task benchmark.

### BR-04 — 理论基础与专业知识

**Score: 4.5 / 5**

**Manuscript locator:** §§2.1–2.6, lines 182–433; §§3.2–3.5, lines 456–643; event and error formulas in §§4.2–4.4; proxy-power discussion in §5.5.3, lines 1452–1461.

**Evidence actually opened:** I read the definitions of session reconstruction, proxy energy, graph statistics, event labels, prediction-time information, MAE/RMSE and interval coverage, as well as the formulas and assumptions used for parameter intervention, distillation, four-cell error reconstruction, transfer entropy, and the synthetic dispatch example. Section 5.5.3 explicitly converts kWh per 15 minutes to interval-average equivalent kW and states it is not metered power.

**Rationale:** Concepts and units are generally well controlled and integrated into the experimental interpretation. The manuscript distinguishes statistical association from physical topology and causal effect; it also separates target-side event labels, retrospective triggers, and genuinely available inputs. The formulas are tied to stated conditions instead of presented as automatic evidence of mechanism.

**Remaining gap:** The analysis remains an applied statistical modeling account rather than a new theoretical result. Several derived quantities rely on reconstructed session energy and fixed window definitions; their physical interpretation is therefore conditional on those data assumptions, which the thesis discloses but cannot validate against synchronized meter measurements.

### BR-05 — 方法与实验设计

**Score: 8.0 / 10**

**Manuscript locator:** §§3.2–3.7, especially §3.6 event-time protocol and §3.7 comparisons; §4.2–4.4; §1.4, lines 130–138.

**Evidence actually opened:** The EXP-019 handoff and phase-2 report document the event-time inputs, split, three-seed protocol, 36-run matrix, fixed selection budget, and parameter-near TCN control. The EXP-027 preregistration/report defines the equal-parameter node-level versus node-shared sigmoid gate refit. The EXP-028 preregistration/report and raw analysis artifacts document the fixed JPL run matrix, test-key protocol, and paired comparisons. These were read alongside the thesis’s caveats about the old final-field/availability protocol.

**Rationale:** The revised central comparisons address important alternatives: the event-time experiment avoids using final-session fields as if they were available, the TCN is approximately capacity matched, and the gate control changes the parameter-sharing choice at equal parameter count. JPL uses a locked, preregistered refit rather than being described as transfer. The thesis also distinguishes refitting, frozen parameter replacement, and retrospective analyses.

**Remaining gap:** The Caltech event-time comparison still lacks a simple behavior-only GRU/MLP or linear baseline and a capacity-matched AGCRN refit under that exact protocol. The TCN comparison is close in capacity but not a full search-budget-matched comparison across all architectures; the JPL budgets are fixed, not tuned independently. JPL is another station in the same ACN family with overlapping years. The old protocol remains informative only with its retrospective information limitation.

### BR-06 — 可复现性与方法严谨性

**Score: 4.5 / 5**

**Manuscript locator:** §§2.1 and 2.1.3; §3.6.1; experiment and artifact references in §§3.6–3.7; EXP-027 and EXP-028 descriptions.

**Evidence actually opened:** I read the protocol manifests/reports and the available EXP-027 recovered summaries. For JPL I opened the analysis report, model summary, paired intervals, checkpoint lock, and test-export state in the EXP-028 bundle. These record the frozen run matrix, settings, prediction comparisons, metrics, and artifact state. The thesis also names the old preprocessing and information-availability weaknesses rather than silently treating protocols as interchangeable.

**Rationale:** The main revised results have unusually specific provenance: model/run identifiers, seeds, input and split rules, budgets, prediction keys, and linked result products are traceable. The checkpoint/test-export lock and paired-interval artifacts provide useful independent audit points for JPL. The report evidence is consistent with the corresponding thesis claims.

**Remaining gap:** I inspected reports and selected raw artifacts, not every prediction row or all source data, and did not independently execute the full pipelines. The older analysis protocol has upstream statistics and final-session-field limitations; these make its numbers less suitable as operational evidence even though the manuscript discloses the issue.

### BR-07 — 工作量与解决问题能力

**Score: 8.0 / 10**

**Manuscript locator:** Whole manuscript; especially data construction §§2.1–2.6, experiments §§3.6–3.8, diagnostics chapter 4, and bounded extensions §§5.2–5.5.

**Evidence actually opened:** The full thesis, EXP-019/027/028 experiment definitions and reports, raw selected EXP-027/JPL audit outputs, and the EXP-029 node-composition sensitivity report. The work includes data-quality reconstruction, distinct retrospective and event-time protocols, matched controls, an independent-site refit, parameter intervention, a constrained distillation attempt, error decomposition, interval analyses, and a synthetic decision-interface demonstration.

**Rationale:** The evidence shows substantial problem-solving beyond fitting one architecture: the author revises information assumptions, separates different kinds of diagnostics, and carries the limits into interpretation. The matched gate design and the locked JPL rerun are particularly relevant independent pieces of work. The score reflects analysis and resolution of methodological problems, not the number of runs, figures, or pages.

**Remaining gap:** Core prediction evidence still comes from two stations in one data family and overlapping periods; MDP layers were not repeated at JPL. Several chapter-5 analyses are exploratory or retrospective and do not create additional external confirmation. There is no field deployment or meter-calibrated study.

### BR-08 — 结果与证据充分性

**Score: 7.5 / 10**

**Manuscript locator:** §§3.6.2–3.8; §4.5–4.6; §5.2–5.6; conclusion, lines 1514–1539.

**Evidence actually opened:** EXP-019 results give Caltech event-time MRG-GCN MAE 0.03890, capacity-near TCN 0.04634, and full AGCRN 0.03743; the thesis says the gain over TCN is concentrated in zero targets. EXP-027 reports the equal-parameter gate difference; EXP-028 reports JPL MRG-GCN MAE 0.081067, TCN 0.083888, AGCRN 0.083268, and shared gate 0.083325, while TCN has lower RMSE, event MAE, and nonzero-target MAE. I read the paired intervals and the manuscript’s four-cell reconstruction and synthetic-example caveats.

**Rationale:** Important claims have direct, protocol-specific evidence, and the thesis reports mixed outcomes instead of collapsing them into a blanket model win. The matched gate comparisons support a narrow incremental claim; JPL provides a second within-family site check. Error and event analyses explain where aggregate differences arise.

**Remaining gap:** The event-time TCN comparison does not establish broad superiority because full AGCRN has lower MAE and TCN wins several JPL metrics. There are missing simple and capacity-matched alternative baselines under the strict protocol, no external data family or future-period test, and no meter-based outcome. The old 0.01376 result is retrospective proxy evidence and should not be combined into a common ranking with the newer protocol.

### BR-09 — 统计解释与结论边界

**Score: 8.5 / 10**

**Manuscript locator:** §§3.6.4–3.7.5; §4.2.5 and §4.3.3; §§4.4.4–4.6; §§5.2, 5.3, and 5.5.5; chapter summaries and conclusion.

**Evidence actually opened:** The thesis reports seed and temporal-block uncertainty, distinguishes locked-period conditional intervals from across-site or across-training uncertainty, flags post-hoc node sensitivity, and labels TE/PCMCI+ tests uncorrected for multiple comparisons. It says conformal event coverage remains inadequate, mature-label rolling results are historical replay, oracle routing is unavailable at prediction time, and JPL does not validate the full MDP. The EXP-028 paired intervals and preregistration/report were also opened.

**Rationale:** Boundaries are unusually explicit and usually matched to the evidence: a frozen-parameter degradation is not treated as independent beta value or causality; a student failure is not generalized to all distillation; four-cell closure is not causal attribution; and interval coverage below target is not marketed as a guarantee. Main claims stay tied to the tested protocols.

**Remaining gap:** The strongest intervals condition on a fixed test history and a small set of training seeds; they do not capture unseen periods/sites or all training variation. Several chapter-5 subgroup and directionality analyses are exploratory, and TE/PCMCI+ has no multiplicity adjustment. These limits are disclosed, but they constrain how far “stability” language can travel.

### BR-10 — 贡献与创新

**Score: 6.5 / 10**

**Manuscript locator:** §§1.2.2–1.2.4, lines 75–110; §§1.3–1.4, lines 112–141; §§3.5.8 and 3.8.1; chapter 4 and conclusion.

**Evidence actually opened:** I compared the thesis’s own framing with full official [Huang et al. [10]](https://epjournal.csee.org.cn/en/article/doi/10.13334/j.0258-8013.pcsee.231589/) and [STGNet [92]](https://scijournals.onlinelibrary.wiley.com/doi/10.1002/ese3.1633/), plus official available evidence for [67] and [70]. Huang et al. already use adaptive EV station graphs, node-adaptive parameters, and component ablations. STGNet already uses gated fusion of graph representations, node-specific GCN parameters, and ablations. The thesis itself acknowledges these precedents and limits MDP to a task-specific diagnostic organization.

**Rationale:** The strongest defensible contribution is narrower than a new graph or gate method: separating three relation statistics at charger-node granularity, testing node-difference gating against a same-parameter shared gate, and organizing task-specific diagnostics with explicit inference boundaries. The gate refit offers evidence for incremental value. The manuscript’s restrained novelty claim is credible as a combination/task contribution.

**Remaining gap:** Generic adaptive graphs, multi-graph fusion, gates, node-conditioned parameters, and module ablation are not new. The relation-subset results do not show a clear independent gain from each relation class, and MDP composes existing diagnostic tools rather than establishing a general new method. No prior-art model was rerun on the same data/split, and independent data-family confirmation is absent.

### BR-11 — 专业实践价值

**Score: 3.0 / 5**

**Manuscript locator:** §§1.1.1 and 1.4; §5.5, especially lines 1450–1495; §5.6 and lines 1509–1512.

**Evidence actually opened:** The thesis gives a fixed-origin proxy-demand example with a 43.1% final-step underprediction and a synthetic four-step LP satisfying specified vehicle-energy and capacity constraints. It explicitly says the synthetic price and operating parameters are artificial and refuses to claim savings. The application-boundary section lists missing synchronized meter mapping, station limits, non-charging load, vehicle requests, and independent shadow operation.

**Rationale:** The work identifies a credible operational interface—node forecasts as an input to capacity review or charging coordination—and shows both an informative failure case and a constrained toy calculation. It is useful as a research prototype for what an operational validation would need to test.

**Remaining gap:** No real station operating constraints, meter calibration, vehicle request stream, tariff evaluation, deployment, or measured decision benefit is available. The thesis appropriately stops short of claiming dispatch or safety value, so practical value remains potential rather than demonstrated.

### BR-12 — 结构、表达与学术规范

**Score: 7.5 / 10**

**Manuscript locator:** Whole manuscript; front-matter/contents lines 1–36; table/figure captions throughout; acknowledgments lines 1540–1542.

**Evidence actually opened:** I read the full markdown, including chapter sequence, tables, figure captions, citations, reference-dependent nearest-work claims, and conclusion. The narrative progresses from task definition and related work through methods, controlled results, mechanism diagnostics, and carefully bounded extensions. Captions often specify the data slice, statistic, and interpretation limit.

**Rationale:** The manuscript is technically dense but generally coherent. Terminology is controlled across proxy energy, event labels, rule triggers, and availability conditions. The literature claims are materially more credible because the text marks abstract-only sources and states when full method details were not checked. Conclusions are consistent with the mixed results and stated scope.

**Remaining gap:** The table of contents retains placeholder entries and acknowledgments remain a placeholder. Some paragraphs and chapter-5 material are dense, and the markdown review did not inspect rendered thesis layout or visually audit the figure assets; those are limits on judging presentation and figure legibility here.

