# 三幅图修订与检查记录（2026-09-20）

本轮由用户指定修订fig5_5、fig4_6，并明确指定ImageGen重绘fig3_7。结果图采用项目Python/Matplotlib，模型图保留原生PNG，不称其为矢量图。

| 图 | 设计与数据 | 检查 |
|---|---|---|
| fig5_5 | A方向矩阵；B各节点入/出边；C90个有向对的交集分解。数据源outputs/analysis/pcmci/pcmci_summary.json | 44/32/6互斥组与8个均未达阈值对；10个自回归对排除；节点顺序一致 |
| fig4_6 | A各分箱MAE；B样本占比与绝对误差贡献的配对点图。沿用SG-EXP-004 seed-2024逐键预测、冻结规则与原有分箱 | 712360个预测键；n×MAE贡献归一化；对数轴明确；不虚构误差棒 |
| fig3_7 | 16:9双层布局；蓝灰张量；大字号与正交路径 | 对照src/evcs_station_graph/models/graph.py；H1ref不拼接，H0/H1/H2拼接，预测头Linear；输出四步 |

生成脚本：scripts/figures/refine_requested_20260920.py。逐图来源哈希与实际绘图数值：outputs/figures/revision_20260920_sources.json。输出沿用outputs/figures内原文件名；结果图为可编辑文本SVG及1200 DPI PNG。原fig3_7存于outputs/figures/archive/2026-09-20-requested-revision/。

可读性复核：原尺寸检查坐标、图例、数值标签无裁切；矩阵使用形状与颜色双编码；新增面板有独立信息；数据图图注同步正文。DOCX本轮未重新生成。

## ImageGen最终提示词

Edit this thesis model schematic into a beautifully precise academic neural architecture figure, landscape 16:9, high resolution. White background, muted blue-gray outlines (#61788F), pale blue tensor faces, very pale warm beige only for residual MLP. Black Chinese Song-style serif text, clean Times math, LARGE readable text, no neon blue or red, no gradients, no shadows, no decorations, no title or caption. Preserve exact computational topology from reference. Two clearly aligned horizontal tiers: upper tier H⁽⁰⁾ tensor → 第一层传播 → H⁽¹⁾ tensor → residual MLP refinement (Linear → GELU → Dropout → Linear, bypass from INPUT of this MLP to a circled plus after last Linear) → H⁽¹,ref⁾ tensor → 第二层传播 → H⁽²⁾ tensor. All four hidden-state tensors must have identical shape and consistent isometric grids, each B×N×32, TCN already removed time dimension. Top and front grid lines meet exactly, no arbitrary extra grid on one tensor. Lower tier: three separate noncrossing orthogonal arrows ONLY from original H⁽⁰⁾, original H⁽¹⁾, H⁽²⁾ into a compact 三层拼接 module with colored feature slices labelled H⁽⁰⁾ | H⁽¹⁾ | H⁽²⁾ and B×N×96. H⁽¹,ref⁾ NEVER enters concatenation. Then arrow to 跨层融合: Linear → LayerNorm → GELU → Dropout, with B×N×32 underneath. Then arrow 预测头 Linear → output tensor Ŷ, B×4×10. Output has EXACTLY four columns labeled t+1, t+2, t+3, t+4, vertical axis 节点 N=10 (schematic grid allowed), batch dimension implicit. Hat over Y complete and never cropped. Use elegant compact group boundaries, generous text padding, 5% safe margins, accurate arrow endpoints and no crossing. Improve composition compared to reference by limiting residual MLP width, aligning upper blocks and enlarging lower operator text. Scientifically exact, sophisticated restrained paper figure.
