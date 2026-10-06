# 图1-2四阶段整图重构（2026-10-06）

用户认为此前图1-2整体不如图2-1、2-7、2-10、3-8，要求重新设计。本轮使用内置ImageGen重新组织整图，随后做局部连线与间距校正。当前正文图件为 `outputs/figures/fig1_2_roadmap.png`。图2-13仍使用 `roadmap-evaluation-grid-polish-20261006.md` 记录的选定版本。

## 对照查看与设计判断

实际查看了四张用户认可的现行图，以及李芳凝论文图3-1、3-3、3-13的PDF渲染区域。参考论文为 `/Users/xushuyuan/Downloads/基于深度学习组合模型的电动汽车换电站负荷预测研究_李芳凝.pdf`，PDF SHA256为 `af597281d085a079bd0265bf33e56a3501d167f337283a8e716a333c2c0dc03e`。

| 对照对象 | 观察到的组织方式 | 本轮采用 |
|---|---|---|
| 图2-1 | 浅虚线阶段带、小模块与分流汇合、来源与结果使用暖色 | 数据和方法按阶段分区；取消三个大型竖列 |
| 图2-7 | 主轴清楚；补充输入从侧面进入对应步骤 | 时序表示与LRE关系在多关系传播处分别接入 |
| 图2-10 | 信息来源分开，交汇和后续用途通过连接关系体现 | 分开两路模型输入及Caltech、JPL两路证据 |
| 图3-8 | 训练和评价有层级；同层格子保持基线和尺寸 | 三层诊断等高并列；阶段标题与操作模块区分 |
| 李芳凝图3-1、3-13 | 按阶段展开，同层分支由共同母线连接，阶段末收束 | 四个横向阶段及三诊断的分叉、汇合总线 |
| 李芳凝图3-3 | 紧凑流程、旁路留出通道、线头落在对象边界 | 数据与证据输出走预留通道，减少重复线段 |

此前图1-2的主要问题是重复套框、过大的模块和字号，以及三个竖列相近的视觉重量。新图减少外框层级，统一同层框高、内边距和正交连线，以四个横向阶段组织阅读顺序。

## 新图结构及语义

1. **Caltech数据基础**：Caltech会话 → 15 min代理重构 → 节点筛选 → 节点数据张量。
2. **贡献一：预测方法**：张量分别进入时间编码和LRE三关系。时间编码从左进入多关系传播，LRE关系从上进入该步骤；再接节点门控融合和MRG-GCN预测。LRE三关系的小组含负荷、行为、轮廓三张并列卡片。图中没有把LRE图串联输入时间编码。
3. **贡献二：MDP诊断**：模型进入参数干预、蒸馏验证和四格溯源三个互补分析分支；三路证据收束到结构分析与预测支持。并列布局不表示模型集成，也不要求L1的计算结果作为L2或L3的输入。
4. **JPL补充验证**：从JPL会话独立开始，经冻结协议、本站构图与训练、点预测与门控对照，进入证据综合与研究结论。Caltech证据单独进入结论，未连入JPL训练。

图中保留两项核心贡献；不把JPL补充实验扩展为零样本迁移、MDP跨站复现、实测功率验证或新增贡献。图注继续采用论文1.5节的原有表述，没有修改正文研究结论。

## 视觉规范

保留16:9白底、宋体风格中文与Times风格拉丁字符。蓝灰为常规操作、暖米灰为来源和模型输出/结论、浅象牙色为LRE局部区域；轮廓和阶段线使用细石板蓝灰，连接线使用细深灰。配色属于本文，未采用参考论文的亮色体系。生成提示词中的色值和坐标是约束，不作为逐像素相等的承诺。

## 选定输出与保存

原生生成目录：`/Users/xushuyuan/.codex/generated_images/01a10a6b-4ba7-7f72-8036-ea5cf8ea9990/`。

- 整体重构首版：`exec-b4c621b7-5e60-4bc3-be1d-6bbb3c19ac5e.png`。
- 最终选定：`exec-c4ed956f-d20d-4e6b-abb8-960d41c5405d.png`。
- 最终版本整理数据张量的单一分叉母线、Caltech标题换行及三诊断卡片的横向间距。
- 替换前的PNG、source.json、manifest、ImageGen登记及正式DOCX保存在 `outputs/figures/archive/2026-10-06-roadmap-four-stage-redesign/`。
- 主代理与独立审阅代理查看了新图的标签、数据流、分支归属及证据汇合；旧版仍保留以便对照。
- 原生PNG直接复制入项目，不用脚本重绘图片或包装为SVG。尺寸和SHA256见同名source.json。

## 实际提示词

### 整图重新设计

输入顺序为：旧图1-2（只参考科学内容）、图2-1、图2-10、图3-8（自有风格参考）、李芳凝图3-13的PDF渲染区域（只参考空间组织）。图2-7另由代理查看，不作为此调用的图像输入。

```text
Use case: scientific-educational, Chinese thesis technical roadmap.
Primary request: COMPLETELY REDESIGN the existing Figure 1-2. The current picture is rejected because it is oversized, boxed into three tall columns, heavily nested and visually crude. This must be a new composition, not a local repair.

INPUT ROLES:
Image 1 is the REJECTED roadmap: scientific content reference only; discard its entire geometry, three tall columns, giant typography, repeated group borders and old conclusion arrangement.
Images 2–4 are the USER-APPROVED Figure2-1, Figure2-10 and Figure3-8: these establish the exact house visual language of fine outline process cards, Song/Ming serif Chinese, restrained warm source/end nodes, blue-gray steps, ivory limited accents, airy but compact stage division and clear orthogonal wiring. Match their modest text scale, thin dark slate outlines, short arrowheads and consistent internal padding.
Image 5 is Li Fangning thesis Figure3-13: learn ONLY stage-by-stage organization, aligned branching buses, small parallel peer modules and clear merge hierarchy. Never copy its colors, graph content, titles or algorithm terms.

CANVAS AND STYLE:
Pure white LANDSCAPE 16:9, clean high-resolution print-oriented academic diagram. Pale blue-gray #DCE6EC steps, warm beige-gray #E5E0D8 source/output, pale ivory #F0EADB subtle graph/secondary accents. Fine slate #607585 outlines, softer blue-gray thin dashed stage borders, near-black fine arrows and text. Chinese Song/Ming serif with Times Latin. All procedural cards approximately the SAME HEIGHT, same padding and modest readable font. Stage headings are quiet serif labels, smaller than the current rejected giant headings. No gradient, shadow, icon, 3D, thick banner, colored group background, total title, figure number or footnote.

NEW COMPOSITION — FOUR HORIZONTAL STAGES, with rhythmic vertical spacing, NOT three tall columns:
Use about 4% outer margins, only ONE thin dashed border per stage on WHITE. For the first three stages use a small left heading gutter (about 13% width), with the operation region beginning around 20% width. Stage headings may gracefully wrap into two short lines in that gutter. Leave ample white space above cards for branch/merge lines; no routing line ever crosses a heading.

STAGE 1, upper shallow band (roughly y4–19%):
Heading “Caltech数据基础”.
One compact left-to-right row of FOUR equal-height nodes:
“Caltech会话” (warm rounded source) → “15 min代理重构” (blue) → “节点筛选” (blue) → “节点数据张量” (blue).
Balance widths to words, equal arrow gaps, exact row alignment. This is the Caltech source only.

STAGE 2, method band (roughly y22–44%):
Heading “贡献一：预测方法”.
Draw a genuine two-input model structure rather than a false graph→time-encoding chain.
The main row, all four equal-height rectangular cards around y35%, reads:
“时间编码” → “多关系传播” → “节点门控融合” → “MRG-GCN预测”.
Above “多关系传播” draw ONE compact LRE inset group headed “LRE三关系”, containing THREE equal small peer cells side-by-side: “负荷关系” | “行为关系” | “轮廓关系”. No arrows between these three cells. Their collective group output drops by ONE short vertical arrow into the TOP of “多关系传播”.
“节点数据张量” from stage1 supplies TWO independent representation routes by one tidy branching bus in the white inter-stage gutter: a short orthogonal route to the TOP of “时间编码”, and another route to the TOP of the LRE group. It does NOT send a direct arrow to the gate or model output. The time-encoding card supplies multi-relation propagation from LEFT; LRE supplies from ABOVE. Separate clean port positions with no ambiguous crossings.
The MRG-GCN prediction card may be subtly warm to mark the core method. No extra outer box around the four model steps. Moderate hierarchy comes from the small LRE inset and two-input junction, not from nested giant frames.

STAGE 3, diagnostic band (roughly y47–71%):
Heading “贡献二：MDP诊断”.
The prediction output from “MRG-GCN预测” supplies the DIAGNOSTIC PROTOCOL as a whole. Route from model bottom to ONE symmetrical split bus above THREE equal peer cards, aligned in a single horizontal row:
“L1 参数干预” | “L2 蒸馏验证” | “L3 四格溯源”.
These represent complementary diagnostic analyses, not an ensemble and not a computational chain L1→L2→L3. All three receive independent downward arrows from the bus.
All three cards output down to ONE tidy merge bus. From that merge lead a short orthogonal arrow into a BLUE compact card “结构分析与预测支持”, placed at the LOWER RIGHT of this diagnostic stage, approximately below the model-output region. Do not wrap the three cards in another outer frame. This final Caltech stage output is deliberately located over the ultimate evidence-synthesis endpoint below, allowing a short straight output route.

STAGE 4, lower supplementary band (roughly y76–94%):
A shallow dashed stage frame occupies LEFT approximately 73% of canvas width; heading “JPL补充验证” tucked upper-left at the same quiet size as other headings.
A compact row of FOUR equal-height nodes with evenly spaced horizontal arrows:
“JPL会话” (warm rounded source) → “冻结协议” (blue) → “本站构图与训练” (blue) → “点预测与门控对照” (blue).
The two long labels may wrap into TWO balanced lines; keep the same font size as other nodes, never shrink them. JPL has its own source; NO Caltech node supplies any JPL operation.
At lower RIGHT, OUTSIDE the JPL dashed frame, one compact warm source/end-style softly rounded endpoint, exactly “证据综合与研究结论”, centered at approximately x85%, y86%, with generous but economical padding. Avoid giant capsule or detached bottom footer. This card receives EXACTLY TWO short clear inputs: JPL final output enters its LEFT border horizontally; “结构分析与预测支持” from stage3 enters its TOP border vertically. Reserve the narrow right synthesis corridor for the vertical Caltech connection. This wire must remain outside the JPL stage and never touch a JPL node or chain. Use balanced endpoint size, no lonely massive rectangle.

QUALITY AND SCIENTIFIC INVARIANTS:
The entire diagram should look like the approved four figures: small neatly typeset modules, clean stage boundaries, restrained geometry, airy routing corridors, a clear main pathway and parallel diagnostic detail. Every arrowhead touches a proper border; no line floats in space, crosses a label or accidentally joins an unrelated wire. All prescribed text appears exactly once; only repeated generic words inside full labels are allowed. No decorative slogans or long cautions. LRE statistical graphs are constructed from Caltech training statistics; graph input feeds propagation, not temporal encoding. JPL is independently refitted under its frozen protocol, not zero-shot model transfer, not MDP replication. Do not invent performance numbers, causal conclusions, deployment outcomes or additional contributions. Keep the USER'S own palette, not Li Fangning's brighter palette.
```

### 连线、间距与标题换行校正

输入为上述整体重构首版。

```text
Use case: precise-object-edit. Refine this NEW four-stage 1672×941 Chinese thesis roadmap. Keep the FOUR horizontal stage composition, all exact labels, all colors, serif typography, model row, JPL independent source chain, final endpoint and every correct scientific relation. Make ONLY THREE targeted layout refinements:

1. In the top-left stage heading, use graceful TWO-LINE wrapping exactly “Caltech” on the first line and “数据基础” on the second line. The present “Caltech数据” / “基础” wrap is awkward. Same current heading font size and left alignment; do not add a title.

2. Simplify ONLY the two data-output wires from “节点数据张量”. Delete the present pair of almost-parallel horizontal wires near y200 and220. Replace with ONE clean unbranched common segment:
   start at tensor BOTTOM CENTER around (1344,144), descend to y216, run LEFT to x534. From this shared horizontal line, exactly TWO independent downward branches:
   A at x534 straight down with arrowhead on TOP CENTER of “时间编码” around(534,392);
   B at x819 straight down with arrowhead on TOP CENTER of the “LRE三关系” small inset frame around(819,243).
   This is a deliberate T-junction at (819,216), not crossing lines. Parent tensor supplies both representations. Do not route through stage headings, do not add direct gate input or output input. Keep LRE inset→multi-relation propagation and the entire horizontal four-step model chain unchanged.

3. Redistribute ONLY the three MDP peer cards and their branch/merge buses across the available operation region. The present L1 starts too far right. Put all THREE cards at the SAME existing vertical bounds y568..634, with SAME width320 and height66, at:
   “L1 参数干预”: x424..744 (center584);
   “L2 蒸馏验证”: x818..1138 (center978);
   “L3 四格溯源”: x1210..1530 (center1370).
   Identical card fill, outline, font, padding; balanced equal gaps about74. This makes the first diagnosis align with the left edge of “时间编码” and the last diagnosis align with the model output region.
   Redraw the upper split bus y535 spanning centers584..1370; receive the valid existing prediction output from “MRG-GCN预测” via one short orthogonal attachment at its right end. Exactly three equal vertical arrows enter the top centers of the diagnosis cards.
   Redraw the lower merge bus y661 spanning centers584..1370; three equal vertical outputs reach it. Its ONLY output goes down into the TOP of the EXISTING “结构分析与预测支持” card near x1115,y690. Keep that support card in its present position and keep its valid output to final conclusion unchanged.
   MDP cards are parallel evidence analyses, never linked card-to-card. No new modules or labels, no duplicated old frames or residual wires.

Maintain flat pale blue-gray steps, neutral warm beige sources/output, ivory LRE inset, fine slate outlines and short dark arrowheads, white16:9. No gradients, shadows, bright color, icons or decoration. Everything outside these three changes remains exactly as in this redesigned image.
```

## 正式稿同步与核对

用仓库已有 `scripts/sync_formal_docx_figure_assets.py` 更新现有正式DOCX的图片媒体及等比高度，保留正文、图注、样式和原生公式。主文仍为46幅图，第1—5章数量为2、13、16、6、9幅。核对记录见 `roadmap-four-stage-redesign-20261006-audit.json`。本轮没有做DOCX转PDF后的页面渲染审阅。

