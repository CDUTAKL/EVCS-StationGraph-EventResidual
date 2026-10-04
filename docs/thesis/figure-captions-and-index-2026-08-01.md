# 论文图表索引与图注口径（43幅图、32张表，2026-10-04同步）

本文件记录主文 43 幅图的文件、图注主题与证据口径；图号和文件名以
[`figure-renumbering-2026-08-10.md`](figure-renumbering-2026-08-10.md) 为唯一依据，
正文中的完整图注以 `thesis-manuscript.md` 为准。

## 使用边界

- 正文选用的43幅图均在 `outputs/figures/manifest.json` 登记；结果图保留相应SVG与PNG，ImageGen示意图以选定PNG为准，不以同名历史SVG替代。图3-6、图3-7为模型细节图。2026-09-07另对16幅优先图进行结构、映射和口径订正，详见 `figure-priority-audit-20260907.md`。
- 当前正文中15幅示意图在ImageGen来源登记中核验；按用户明确要求保留已规范的ImageGen风格，不将其改为矢量重绘，也不把PNG包装成SVG。2026-10-03图2-10与图5-6仅以ImageGen完成局部勘误。
- 事件评价使用 `target_event=1.43%`；四格诊断和共形路由使用
  `rule_trigger=0.43%`，两者不得混用。
- 四格图改为原正式 MRG-GCN StaticGraph 三种子诊断：A 为四格 MAE 均值及离散度，
  B为样本组成，C为逐种子计算后汇总的绝对误差贡献；图4-5、图4-6仍是seed-2024描述性补充。
- 知识蒸馏不再单列图，由表 4-3 以 (4\alpha×3) 种子结果承载。
- 11 幅撤出主文的图保留在
  `outputs/figures/archive/2026-08-10-withdrawn-from-main-text/`，不删除、不进入附录。

## 第 1 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图1-1 | `fig1_1_research_gap_map` | 研究方向与本文关注不足的对应关系 | ImageGen PNG |
| 图1-2 | `fig1_2_roadmap` | 总体技术路线；图内嵌“方法贡献—机制诊断贡献”两条主线 | ImageGen PNG |

## 第 2 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图2-1 | `fig2_1_data_reconstruction` | 会话记录至节点代理负荷张量的数据重构和划分 | ImageGen PNG |
| 图2-2 | `fig2_2_node_coverage` | 候选节点覆盖率、活跃月份与主分析节点 | SVG+PNG |
| 图2-3 | `fig2_3_load_heatmap` | 连续四周节点代理负荷热力图 | SVG+PNG |
| 图2-4 | `fig2_4_autocorrelation` | 代表节点代理负荷自相关 | SVG+PNG |
| 图2-5 | `fig2_5_weekly_curves` | 代表节点典型周负荷曲线 | SVG+PNG |
| 图2-6 | `fig2_6_load_distribution` | 非零节点代理负荷经验分布 | SVG+PNG |
| 图2-7 | `fig2_7_event_score_flow` | 事件分数与冻结规则事件窗口生成 | ImageGen PNG |
| 图2-8 | `fig2_8_event_hourly` | 标签事件时间步的当地日内分布 | SVG+PNG |
| 图2-9 | `fig2_9_event_component_composition` | 规则事件窗口内四类行为分量构成 | SVG+PNG |
| 图2-10 | `fig2_10_dual_window_definition` | `target_event` 与 `rule_trigger` 的双口径定义 | ImageGen PNG |
| 图2-11 | `fig2_11_feature_correlation` | 输入特征 Spearman 秩相关矩阵 | SVG+PNG |
| 图2-12 | `fig2_12_weekday_hour_heatmap` | 星期—小时节点代理负荷热力图 | SVG+PNG |

## 第 3 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图3-1 | `fig3_1_mrggcn_architecture` | MRG-GCN 整体架构 | ImageGen PNG |
| 图3-2 | `fig3_2_relation_propagation_unit` | 多关系门控传播单元 | ImageGen PNG |
| 图3-3 | `fig3_3_temporal_skip_fusion` | 时间编码与跨层融合预测结构 | ImageGen PNG |
| 图3-4 | `fig3_4_lre_construction` | LRE 三关系构建流程 | ImageGen PNG |
| 图3-5 | `fig3_5_lre_matrices` | 三类固定统计关系矩阵 | SVG+PNG |
| 图3-6 | `fig3_6_gate_residual_detail` | 节点门控与残差更新细节 | ImageGen PNG |
| 图3-7 | `fig3_7_cross_layer_detail` | 跨层表示路径及拼接边界 | ImageGen PNG |
| 图3-8 | `fig3_8_train_predict_pipeline` | 训练—预测—评价流程 | ImageGen PNG |
| 图3-9 | `fig3_9_model_mae_comparison` | 12 个模型的全局 MAE 对比 | SVG+PNG |
| 图3-10 | `fig3_10_mae_by_horizon` | 六模型逐预测步长 MAE | SVG+PNG |
| 图3-11 | `fig3_11_bootstrap_difference` | 点级 pooled Bootstrap 误差差异 | SVG+PNG |
| 图3-12 | `fig3_12_mae_by_window` | 全局、事件、稳定与非零负荷窗口 MAE | SVG+PNG |
| 图3-13 | `fig3_13_mae_by_node` | 节点×模型 MAE 热力图 | SVG+PNG |
| 图3-14 | `fig3_14_mechanism_ablation` | 结构消融结果 | SVG+PNG |

## 第 4 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图4-1 | `fig4_1_three_layer_framework` | 三层机制诊断协议 | ImageGen PNG |
| 图4-2 | `fig4_2_beta_profile` | StaticGraph 两层关系级 $\beta$ 权重画像（三种子均值±样本标准差） | SVG+PNG |
| 图4-3 | `fig4_3_intervention` | 关系级 $\beta$ 参数干预结果 | SVG+PNG |
| 图4-4 | `fig4_4_four_cell` | 原正式MRG-GCN三种子四格诊断；A误差热图、B样本占比、C误差贡献 | SVG+PNG |
| 图4-5 | `fig4_5_residual_distribution` | TCN、StaticGraph 与 MLP 的预测残差分布 | SVG+PNG |
| 图4-6 | `fig4_6_error_vs_event_intensity` | 误差与回溯事件分数的关系 | SVG+PNG |

## 第 5 章

| 图号 | 文件基名 | 图注主题 | 状态 |
|---|---|---|---|
| 图5-1 | `fig5_1_te_pcmci_flow` | TE 候选与 PCMCI+ 条件独立核验的圆形关系图 | ImageGen PNG |
| 图5-2 | `fig5_2_transfer_entropy` | 传递熵方向性候选结构 | SVG+PNG |
| 图5-3 | `fig5_3_asymmetry` | 双向传递熵与方向不对称性 | SVG+PNG |
| 图5-4 | `fig5_4_te_vs_relations` | TE 与三类统计关系权重的对应 | SVG+PNG |
| 图5-5 | `fig5_5_pcmci_validation_network` | PCMCI+ 条件独立核验网络 | SVG+PNG |
| 图5-6 | `fig5_6_conformal_method` | 冻结规则路由的分层共形方法 | ImageGen PNG |
| 图5-7 | `fig5_7_coverage` | 标准与规则路由共形覆盖率 | SVG+PNG |
| 图5-8 | `fig5_8_quantile_per_node` | 分层残差分位数与事件层区间膨胀 | SVG+PNG |
| 图5-9 | `fig5_9_parameter_intervention` | 分层参数干预敏感度 | SVG+PNG |

## 交付检查

- 完整主文：43 幅，章节计数为 2 / 12 / 14 / 6 / 9。
- 图构建和训练期z-score统计不使用测试集；旧占用率分母与目标跳变阈值的全时期拟合例外已在2.1和2.4披露，不能笼统声称所有预处理都仅用训练期。
- 结果图的误差棒、种子数、Bootstrap 或单种子诊断边界，以正文相应完整图注为准。
- Word/PDF同步核对选定PNG、图注、交叉引用、灰度可辨性及版心缩放；ImageGen图不进行矢量替换。

## 正文表格索引（2026-10-04）

本轮补齐协议、配置、时间块统计的正式表号，并将跨两节的消融表拆为独立表。只改编号与引用，不改原实验结果。

| 表号 | 内容 |
|---|---|
| 表2-1 | 原始数据形态与审计结果 |
| 表2-2 | 两套数据协议的回答范围 |
| 表2-3 | 节点筛选门槛及主分析条件下的未通过数量 |
| 表2-4 | 主分析节点代理负荷统计 |
| 表2-5 | 代表性节点日、周滞后自相关系数 |
| 表2-6 | 逐节点冻结规则事件统计 |
| 表2-7 | 输入特征的全量描述性统计 |
| 表3-1 | 原主实验冻结配置 |
| 表3-2 | 全局预测指标对比 |
| 表3-3 | 原主实验时间块误差差复核 |
| 表3-4 | 分层MAE对比 |
| 表3-5 | MRG-GCN逐步长与逐节点MAE |
| 表3-6 | 模型规模与正式训练耗时 |
| 表3-7 | 组合配置下的结构消融结果 |
| 表3-8 | 关系子集与超参数敏感性 |
| 表3-9 | 事件时刻输入协议下的正式结果与内部消融 |
| 表3-10 | 新协议下同参数量节点门控配对结果 |
| 表3-11 | 方法设计组件与证据对照 |
| 表4-1 | MDP三层机制画像 |
| 表4-2 | 两层关系级$\boldsymbol\beta$门控权重 |
| 表4-3 | GCN→TCN知识蒸馏结果 |
| 表4-4 | 原正式MRG-GCN三种子四格误差溯源 |
| 表5-1 | TE候选与LRE统计关系的覆盖情况 |
| 表5-2 | 不同共形口径的经验覆盖率 |
| 表5-3 | 规则路由分层共形的节点级区间宽度 |
| 表5-4 | 冻结区间的覆盖失效诊断 |
| 表5-5 | 新协议独立校准的覆盖与区间质量 |
| 表5-6 | 新协议成熟标签滚动校准回放结果 |
| 表5-7 | 分层参数干预敏感度 |
| 表5-8 | 固定发布时刻下的节点集合四步预测示例 |
| 表5-9 | 合成四片充电分配的影子计划 |
| 表5-10 | 第5章探索结果汇总 |

新增表5-5来源为SG-EXP-023，不替换表5-2至5-4旧协议结果；图5-6至5-8仍表现旧回溯口径。新协议测试标签事件为10,204/708,560，与旧图的1.43%及712,360键分别解释，不把新行为规则比例回写旧图。

表3-10来源为SG-EXP-027六次已核验运行及时间块分析；表5-6复用SG-EXP-019预测作成熟标签回放；表5-9来自SG-EXP-026合成约束算例。正文新增式（5-8）为充电分配目标，独立编号公式合计27个。43幅选定图的文件与图号未变，不将新表中的数值回写原图。
