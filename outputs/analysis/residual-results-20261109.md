# 残差化实验结果汇总（2026-11-09）

| 组 | n | 均值 | SD |
|---|---:|---:|---:|
| ablation_extra/beta0_bce0 | 5 | 0.036643 | 0.000158 |
| ablation_extra/lin_lam2 | 5 | 0.036683 | 0.000221 |
| res_baselines/agcrn_matched | 2 | 0.017262 | 0.000321 |
| res_baselines/tcn_wide | 3 | 0.030709 | 0.000289 |
| residual_lin | 5 | 0.016777 | 0.000528 |
| residual_lin48 | 3 | 0.015705 | 0.000136 |
| residual_main | 5 | 0.027242 | 0.001889 |

## 逐种子

| 组 | 种子 | 全局MAE | 非零层 |
|---|---|---:|---:|
| ablation_extra/beta0_bce0 | seed-2024 | 0.036403 | 0.266329 |
| ablation_extra/beta0_bce0 | seed-2025 | 0.036710 | 0.266756 |
| ablation_extra/beta0_bce0 | seed-2026 | 0.036603 | 0.267189 |
| ablation_extra/beta0_bce0 | seed-2027 | 0.036830 | 0.268419 |
| ablation_extra/beta0_bce0 | seed-2028 | 0.036671 | 0.267701 |
| ablation_extra/lin_lam2 | seed-2024 | 0.036323 | 0.265904 |
| ablation_extra/lin_lam2 | seed-2025 | 0.036911 | 0.26826 |
| ablation_extra/lin_lam2 | seed-2026 | 0.036669 | 0.26684 |
| ablation_extra/lin_lam2 | seed-2027 | 0.036798 | 0.267633 |
| ablation_extra/lin_lam2 | seed-2028 | 0.036716 | 0.267131 |
| res_baselines/agcrn_matched | seed-2024 | 0.017489 | 0.079777 |
| res_baselines/agcrn_matched | seed-2026 | 0.017035 | 0.079749 |
| res_baselines/tcn_wide | seed-2024 | 0.030583 | 0.134588 |
| res_baselines/tcn_wide | seed-2025 | 0.030505 | 0.13401 |
| res_baselines/tcn_wide | seed-2026 | 0.031039 | 0.136613 |
| residual_lin | seed-2024 | 0.017308 | 0.08606 |
| residual_lin | seed-2025 | 0.016553 | 0.090712 |
| residual_lin | seed-2026 | 0.016185 | 0.08655 |
| residual_lin | seed-2027 | 0.017363 | 0.093173 |
| residual_lin | seed-2028 | 0.016477 | 0.090882 |
| residual_lin48 | seed-2024 | 0.015583 | 0.084204 |
| residual_lin48 | seed-2025 | 0.015851 | 0.085025 |
| residual_lin48 | seed-2026 | 0.015679 | 0.085586 |
| residual_main | seed-2024 | 0.025043 | 0.107612 |
| residual_main | seed-2025 | 0.028240 | 0.119675 |
| residual_main | seed-2026 | 0.028721 | 0.121439 |
| residual_main | seed-2027 | 0.028867 | 0.127744 |
| residual_main | seed-2028 | 0.025341 | 0.107052 |
