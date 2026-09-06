# 论文图表索引与图注口径（41 幅，2026-08-10）

本文件记录主文 41 幅图的文件、图注主题与证据口径；图号和文件名以
[`figure-renumbering-2026-08-10.md`](figure-renumbering-2026-08-10.md) 为唯一依据，
正文中的完整图注以 `thesis-manuscript.md` 为准。

## 使用边界

- 31 幅可复现结果图均保留 SVG 与 1200 DPI PNG，并登记于
  `outputs/figures/manifest.json`。
- 10 幅方法示意图当前为 PNG 构图版；正式送审前须按相同图号完成可编辑 SVG 重绘。
- 事件评价使用 `target_event=1.43%`；四格诊断和共形路由使用
  `rule_trigger=0.43%`，两者不得混用。
- 四格图改为原正式 MRG-GCN StaticGraph 三种子诊断：A 为四格 MAE 均值及离散度，
  B 为样本组成与 `n×MAE` 绝对误差贡献；图4-5、图4-6仍是 seed-2024 描述性补充。
- 知识蒸馏不再单列图，由表 4-3 以 (4\alpha×3) 种子结果承载。
- 11 幅撤出主文的图保留在
  `outputs/figures/archive/2026-08-10-withdrawn-from-main-text/`，不删除、不进入附录。

## 第 1 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图1-1 | `fig1_1_research_gap_map` | 研究方向与本文关注不足的对应关系 | 示意图 PNG |
| 图1-2 | `fig1_2_roadmap` | 总体技术路线；图内嵌“方法贡献—机制诊断贡献”两条主线 | SVG+PNG |

## 第 2 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图2-1 | `fig2_1_data_reconstruction` | 会话记录至节点代理负荷张量的数据重构和划分 | SVG+PNG |
| 图2-2 | `fig2_2_node_coverage` | 候选节点覆盖率、活跃月份与主分析节点 | SVG+PNG |
| 图2-3 | `fig2_3_load_heatmap` | 连续四周节点代理负荷热力图 | SVG+PNG |
| 图2-4 | `fig2_4_autocorrelation` | 代表节点代理负荷自相关 | SVG+PNG |
| 图2-5 | `fig2_5_weekly_curves` | 代表节点典型周负荷曲线 | SVG+PNG |
| 图2-6 | `fig2_6_load_distribution` | 非零节点代理负荷经验分布 | SVG+PNG |
| 图2-7 | `fig2_7_event_score_flow` | 事件分数与冻结规则事件窗口生成 | 示意图 PNG |
| 图2-8 | `fig2_8_event_hourly` | 真实事件时间步的日内分布 | SVG+PNG |
| 图2-9 | `fig2_9_event_component_composition` | 规则事件窗口内四类行为分量构成 | SVG+PNG |
| 图2-10 | `fig2_10_dual_window_definition` | `target_event` 与 `rule_trigger` 的双口径定义 | 示意图 PNG |
| 图2-11 | `fig2_11_feature_correlation` | 输入特征 Spearman 秩相关矩阵 | SVG+PNG |
| 图2-12 | `fig2_12_weekday_hour_heatmap` | 星期—小时节点代理负荷热力图 | SVG+PNG |

## 第 3 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图3-1 | `fig3_1_mrggcn_architecture` | MRG-GCN 整体架构 | 示意图 PNG |
| 图3-2 | `fig3_2_relation_propagation_unit` | 多关系门控传播单元 | 示意图 PNG |
| 图3-3 | `fig3_3_temporal_skip_fusion` | 时间编码与跨层融合预测结构 | 示意图 PNG |
| 图3-4 | `fig3_4_lre_construction` | LRE 三关系构建流程 | 示意图 PNG |
| 图3-5 | `fig3_5_lre_matrices` | 三类固定统计关系矩阵 | SVG+PNG |
| 图3-6 | `fig3_6_train_predict_pipeline` | 训练—预测—评价流程 | 示意图 PNG |
| 图3-7 | `fig3_7_model_mae_comparison` | 12 个模型的全局 MAE 对比 | SVG+PNG |
| 图3-8 | `fig3_8_mae_by_horizon` | 六模型逐预测步长 MAE | SVG+PNG |
| 图3-9 | `fig3_9_bootstrap_difference` | 点级 pooled Bootstrap 误差差异 | SVG+PNG |
| 图3-10 | `fig3_10_mae_by_window` | 全局、事件、稳定与非零负荷窗口 MAE | SVG+PNG |
| 图3-11 | `fig3_11_mae_by_node` | 节点×模型 MAE 热力图 | SVG+PNG |
| 图3-12 | `fig3_12_mechanism_ablation` | 结构消融结果 | SVG+PNG |

## 第 4 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图4-1 | `fig4_1_three_layer_framework` | 三层机制诊断协议 | SVG+PNG |
| 图4-2 | `fig4_2_beta_profile` | StaticGraph 两层关系级 $\beta$ 权重画像（三种子均值±样本标准差） | SVG+PNG |
| 图4-3 | `fig4_3_intervention` | 关系级 $\beta$ 参数干预结果 | SVG+PNG |
| 图4-4 | `fig4_4_four_cell` | 原正式MRG-GCN三种子事件标签×规则触发四格诊断；含MAE离散度与样本占比—绝对误差贡献配对点线图 | SVG+PNG |
| 图4-5 | `fig4_5_residual_distribution` | TCN、StaticGraph 与 MLP 的预测残差分布 | SVG+PNG |
| 图4-6 | `fig4_6_error_vs_event_intensity` | 误差与可见事件分数的关系 | SVG+PNG |

## 第 5 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图5-1 | `fig5_1_te_pcmci_flow` | TE 候选与 PCMCI+ 条件独立核验的圆形关系图 | SVG+PNG |
| 图5-2 | `fig5_2_transfer_entropy` | 传递熵方向性候选结构 | SVG+PNG |
| 图5-3 | `fig5_3_asymmetry` | 双向传递熵与方向不对称性 | SVG+PNG |
| 图5-4 | `fig5_4_te_vs_relations` | TE 与三类统计关系权重的对应 | SVG+PNG |
| 图5-5 | `fig5_5_pcmci_validation_network` | PCMCI+ 条件独立核验网络 | SVG+PNG |
| 图5-6 | `fig5_6_conformal_method` | 冻结规则路由的分层共形方法 | 示意图 PNG |
| 图5-7 | `fig5_7_coverage` | 标准与规则路由共形覆盖率 | SVG+PNG |
| 图5-8 | `fig5_8_quantile_per_node` | 分层残差分位数与事件层区间膨胀 | SVG+PNG |
| 图5-9 | `fig5_9_parameter_intervention` | 分层参数干预敏感度 | SVG+PNG |

## 交付检查

- 完整主文：41 幅，章节计数为 2 / 12 / 12 / 6 / 9。
- 关系图、阈值、特征归一化等训练期统计均不使用测试集。
- 结果图的误差棒、种子数、Bootstrap 或单种子诊断边界，以正文相应完整图注为准。
- Word/PDF 最终导出时，应再次检查示意图 SVG 重绘、图注、交叉引用、灰度可辨性和版心缩放可读性。
