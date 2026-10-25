# 科研图片质量审计（2026-09-06）

本报告是生成资产层面的风险筛查，不替代论文版心缩放后的人工目视审阅。

## 汇总

- PNG：46；SVG：30；唯一文件基名：46。
- 重点风险信号：缺少矢量版、PNG无1200 DPI、SVG含控制字符、字体过小、PNG尺寸异常。

## 逐图筛查

| 图文件基名 | PNG | SVG | 分辨率/DPI | SVG文字/字号信号 | 初步处理建议 |
|---|---|---|---|---|---|
| `fig1_1_research_gap_map` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig1_2_roadmap` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig2_10_dual_window_definition` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig2_11_feature_correlation` | 7665×6439 @ 1200 dpi | 文本71；字号7.6–8.8 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig2_12_weekday_hour_heatmap` | 9253×4459 @ 1200 dpi | 文本43；字号7.5–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig2_13_jpl_validation_protocol` | 6709×3772 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig2_1_data_reconstruction` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig2_2_node_coverage` | 6714×5212 @ 1200 dpi | 文本44；字号6.8–8.2 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig2_3_load_heatmap` | 9016×4219 @ 1200 dpi | 文本24；字号7–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig2_4_autocorrelation` | 8179×3859 @ 1200 dpi | 文本21；字号7.5–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig2_5_weekly_curves` | 8239×3878 @ 1200 dpi | 文本21；字号8–10 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig2_6_load_distribution` | 7699×4099 @ 1200 dpi | 文本15；字号5.6–9 | SVG字号<6 | 进入人工目视复核/重绘队列 |
| `fig2_7_event_score_flow` | 6709×3772 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig2_8_event_hourly` | 8299×4219 @ 1200 dpi | 文本21；字号8–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig2_9_event_component_composition` | 6727×3643 @ 1200 dpi | 文本32；字号6.2–7.8 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_10_jpl_stratified_mae` | 6709×4121 @ 1200 dpi | 文本35；字号7–8.5 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_11_model_mae_comparison` | 6727×4999 @ 1200 dpi | 文本43；字号6.3–7.6 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_12_mae_by_horizon` | 9000×4920 @ 1200 dpi | 文本17；字号8–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_13_bootstrap_difference` | 6847×5778 @ 1200 dpi | 文本37；字号7.4–9.5 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_14_mae_by_window` | 6727×3799 @ 1200 dpi | 文本17；字号5.6–8.8 | SVG字号<6 | 进入人工目视复核/重绘队列 |
| `fig3_15_mae_by_node` | 6709×4419 @ 1200 dpi | 文本85；字号7.2–8 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_16_mechanism_ablation` | 6727×3799 @ 1200 dpi | 文本22；字号6.8–8.8 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_1_mrggcn_architecture` | 6709×8945 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig3_2_relation_propagation_unit` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig3_3_temporal_skip_fusion` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig3_4_lre_construction` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig3_5_lre_matrices` | 8546×2814 @ 1200 dpi | 文本72；字号8.2–10 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig3_6_gate_residual_detail` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig3_7_cross_layer_detail` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig3_8_train_predict_pipeline` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig3_9_jpl_mae_primary` | 6709×3161 @ 1200 dpi | 文本25；字号7–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig4_1_three_layer_framework` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig4_2_beta_profile` | 6709×3360 @ 1200 dpi | 文本18；字号7–8.5 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig4_3_intervention` | 6709×4109 @ 1200 dpi | 文本23；字号8–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig4_4_four_cell` | 6713×2887 @ 1200 dpi | 文本54；字号6.6–8.8 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig4_5_residual_distribution` | 10459×4459 @ 1200 dpi | 文本38；字号8–9 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig4_6_error_vs_event_intensity` | 9000×4380 @ 1200 dpi | 文本35；字号7.5–10 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig5_1_te_pcmci_flow` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig5_2_transfer_entropy` | 6720×4164 @ 1200 dpi | 文本32；字号4.9–9 | SVG字号<6 | 进入人工目视复核/重绘队列 |
| `fig5_3_asymmetry` | 6709×6865 @ 1200 dpi | 文本37；字号6–7.4 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig5_4_te_vs_relations` | 6727×3919 @ 1200 dpi | 文本37；字号7.4–8 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig5_5_pcmci_validation_network` | 9000×5520 @ 1200 dpi | 文本48；字号8–10 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig5_6_conformal_method` | 6709×3776 @ 1200 dpi | — | 缺SVG | 优先补矢量版并统一PNG导出 |
| `fig5_7_coverage` | 6709×7441 @ 1200 dpi | 文本47；字号7.5–12 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
| `fig5_8_quantile_per_node` | 6730×5058 @ 1200 dpi | 文本47；字号5.6–8.6 | SVG字号<6 | 进入人工目视复核/重绘队列 |
| `fig5_9_parameter_intervention` | 6737×7448 @ 1200 dpi | 文本126；字号6.5–8.6 | 无 | 通过资产层筛查；仍需版心缩放目视复核 |
