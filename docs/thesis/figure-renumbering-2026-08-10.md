# 论文主文配图最终编号映射（41 幅，2026-08-10）

本文件是主文图号、文件名、正文引用与 DOCX 插图的唯一编号基准。主文按章节连续编号；撤出主文的 11 幅图保存在 `outputs/figures/archive/2026-08-10-withdrawn-from-main-text/`，仅作后续追溯，不删除也不进入附录。

## 第1章（2 幅）

| 图号 | 文件基名 | 内容 |
|---|---|---|
| 图1-1 | `fig1_1_research_gap_map` | 研究方向与本文关注不足的对应关系 |
| 图1-2 | `fig1_2_roadmap` | 本文总体技术路线与双贡献主线 |

## 第2章（12 幅）

| 图号 | 文件基名 | 内容 |
|---|---|---|
| 图2-1 | `fig2_1_data_reconstruction` | 数据重构与数据划分流程 |
| 图2-2 | `fig2_2_node_coverage` | 候选节点覆盖率与筛选结果 |
| 图2-3 | `fig2_3_load_heatmap` | 连续四周节点负荷热力图 |
| 图2-4 | `fig2_4_autocorrelation` | 代表性节点代理负荷自相关函数 |
| 图2-5 | `fig2_5_weekly_curves` | 代表性节点典型周负荷曲线 |
| 图2-6 | `fig2_6_load_distribution` | 非零节点代理负荷经验分布 |
| 图2-7 | `fig2_7_event_score_flow` | 事件分数与冻结规则事件窗口生成流程 |
| 图2-8 | `fig2_8_event_hourly` | 真实事件时间步日内分布 |
| 图2-9 | `fig2_9_event_component_composition` | 冻结规则事件窗口分量构成 |
| 图2-10 | `fig2_10_dual_window_definition` | 标签事件与冻结规则触发的双口径对比 |
| 图2-11 | `fig2_11_feature_correlation` | 输入特征 Spearman 秩相关矩阵 |
| 图2-12 | `fig2_12_weekday_hour_heatmap` | 星期—小时代理负荷热力图 |

## 第3章（12 幅）

| 图号 | 文件基名 | 内容 |
|---|---|---|
| 图3-1 | `fig3_1_mrggcn_architecture` | MRG-GCN 整体架构 |
| 图3-2 | `fig3_2_relation_propagation_unit` | 多关系门控传播单元 |
| 图3-3 | `fig3_3_temporal_skip_fusion` | 时间编码与跨层融合预测结构 |
| 图3-4 | `fig3_4_lre_construction` | LRE 三关系构建流程 |
| 图3-5 | `fig3_5_lre_matrices` | LRE 三类站内关系矩阵 |
| 图3-6 | `fig3_6_train_predict_pipeline` | 训练—预测—评价流程 |
| 图3-7 | `fig3_7_model_mae_comparison` | 不同模型全局 MAE |
| 图3-8 | `fig3_8_mae_by_horizon` | 不同模型逐步长 MAE |
| 图3-9 | `fig3_9_bootstrap_difference` | 点级 Bootstrap 误差差 |
| 图3-10 | `fig3_10_mae_by_window` | 不同评价窗口 MAE |
| 图3-11 | `fig3_11_mae_by_node` | 不同模型逐节点 MAE |
| 图3-12 | `fig3_12_mechanism_ablation` | 结构消融结果 |

## 第4章（6 幅）

| 图号 | 文件基名 | 内容 |
|---|---|---|
| 图4-1 | `fig4_1_three_layer_framework` | 三层机制诊断协议 |
| 图4-2 | `fig4_2_beta_profile` | 两层关系级 β 门控权重画像 |
| 图4-3 | `fig4_3_intervention` | 关系级门控参数干预结果 |
| 图4-4 | `fig4_4_four_cell` | 事件标签与规则触发的四格诊断（含误差贡献） |
| 图4-5 | `fig4_5_residual_distribution` | 不同模型预测残差分布 |
| 图4-6 | `fig4_6_error_vs_event_intensity` | 误差与可见事件分数的关系 |

## 第5章（9 幅）

| 图号 | 文件基名 | 内容 |
|---|---|---|
| 图5-1 | `fig5_1_te_pcmci_flow` | TE→PCMCI+条件滞后依赖结构发现流程 |
| 图5-2 | `fig5_2_transfer_entropy` | 传递熵方向性候选结构 |
| 图5-3 | `fig5_3_asymmetry` | 双向传递熵与方向不对称性 |
| 图5-4 | `fig5_4_te_vs_relations` | TE 与统计关系权重的对应 |
| 图5-5 | `fig5_5_pcmci_validation_network` | PCMCI+条件独立核验结果 |
| 图5-6 | `fig5_6_conformal_method` | 冻结规则路由的分层共形方法 |
| 图5-7 | `fig5_7_coverage` | 共形覆盖率比较 |
| 图5-8 | `fig5_8_quantile_per_node` | 分层残差分位数与区间膨胀 |
| 图5-9 | `fig5_9_parameter_intervention` | 分层参数干预敏感度 |

## 数量与状态

- 第1章 2 幅、第2章 12 幅、第3章 12 幅、第4章 6 幅、第5章 9 幅，主文共 **41 幅**。
- 31 幅结果图及 2 幅新第4章结果图具有 SVG + 1200 DPI PNG 及可追溯脚本；其余方法示意图当前保留 PNG 构图预览，正式提交前仍需确定性 SVG 重绘。
- 图4-3知识蒸馏结果由表4-3承载；图4-4 的 B 面板以配对点线对照样本占比与按 `count×MAE` 计算的绝对误差贡献。
