# SG-EXP-032 result audit

Audit status: PASS; six complete runs, exact common forecast keys and labels, per-file checksums, finite predictions, and independent metric recalculation verified.

## Test-set summary (mean ± sample SD across three seeds)

| Model | MAE | RMSE | Event MAE | Non-event MAE | Zero MAE | Nonzero MAE |
|---|---:|---:|---:|---:|---:|---:|
| mrg_full | 0.043401±0.000303 | 0.193411±0.000728 | 0.480282±0.004677 | 0.037018±0.000241 | 0.008700±0.001153 | 0.614498±0.013807 |
| tcn_wide | 0.051703±0.000074 | 0.193320±0.000349 | 0.484651±0.000875 | 0.045377±0.000063 | 0.018353±0.000117 | 0.600560±0.001180 |

## Paired primary contrast

Mean TCN−MRG test MAE difference: 0.008302 kWh/15 min; 95% paired 7-day-block bootstrap interval [0.007757, 0.008797], 27/27 blocks positive.

Positive values favor MRG-GCN. The primary comparison uses the same 17,714 forecast origins × 4 target slices × 10 nodes = 708,560 keys under the new target. Event strata use the unchanged original event labels; zero/nonzero strata use the new target.

## Limits

This is post-hoc analysis on an already viewed Caltech period. The alternate target is a session-derived proxy, not measured power. The graph was held fixed to isolate label sensitivity. The 0.0477816 kWh/15 min target-definition difference is not a model-error bound and is not directly comparable to model MAE.

Detailed evidence is in `audit.json`, per-run results in `run-metrics.csv`, and block differences in `paired-seven-day-blocks.csv`.
