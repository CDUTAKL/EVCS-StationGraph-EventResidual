# 图1-2与图2-13风格重绘记录（2026-10-06）

后续状态：本文件记录两图此前的重绘过程。图1-2下部与图2-13评价区随后再次整理，当前选定版本及完整提示词见 `roadmap-evaluation-grid-polish-20261006.md`；历次旧图均保留于各轮archive目录。

用户反馈：图1-2中部布局不美观；图2-13体积过大、文字过多、颜色区分不足。两张图均由内置ImageGen重新绘制，沿用 `flowchart-house-style-polish-20260922.md` 的项目规范及图5-6作为风格锚点。

## 本轮选定方案

- 白底16:9；低饱和蓝灰为常规流程、暖米灰为来源或锁定节点、浅象牙色为辅助步骤；石板蓝细轮廓与虚线分区，深灰正交箭头，宋体风格中文与Times风格拉丁字符。
- 图1-2采用Caltech上部主线和JPL下部独立支线。中部补为预测方法模块，与右侧MDP模块形成两项贡献；模块内部细节与模块间箭头分别解释，不将关系图理解为时间编码的直接输入。两条汇总线各自进入研究结论，不将Caltech诊断串入JPL比较。
- 图2-13改为“数据准备—固定划分—训练与评价”三个横向区域。缩短框内文字，保留输入/目标分离、四段职责、训练段拟合、调参MAE选模、锁定后测试和七日比较。10节点、UTC 15 min、96步/4步、标签成熟及训练预算等细节仍以正文2.1.3节、3.8.2节和图注为准。
- 旧首版保存在 `outputs/figures/archive/2026-10-06-jpl-imagegen-style-redraw/`。图片保留原生PNG，未用脚本修图或包装为SVG。

## 生成和复核

| 图 | 初次重绘 | 复核及选定输出 |
|---|---|---|
| 图1-2 | `exec-b8da1522-3d70-4821-9a9e-a3a8b38612bc.png` | 初次存在错误汇总线；补齐中部模型模块并改正连线后选定 `exec-7deebec7-b343-4c70-836b-0f7993f4b485.png` |
| 图2-13 | `exec-275c2bfb-de2d-4992-b65e-bdc7d7a0a738.png` | 初次数据入口箭头悬空；改为接入“完整窗口留段”框后选定 `exec-eaaf20a1-95e4-48e3-b828-85706ebbc52a.png` |

上述文件位于 `/Users/xushuyuan/.codex/generated_images/01a10a6b-4ba7-7f72-8036-ea5cf8ea9990/`。选定图逐张查看了文字、模块归属和箭头终点。工作区稳定路径为 `outputs/figures/fig1_2_roadmap.png` 与 `outputs/figures/fig2_13_jpl_validation_protocol.png`；尺寸及哈希记录于各图同名source.json。

## 实际提示词

### 图1-2重绘

```text
Use case: infographic-diagram.
Asset: completely redesigned Figure 1-2 for a Chinese engineering master's thesis.
Input image 1 is the rejected roadmap: preserve its scientific content only, DO NOT preserve its three tall columns or awkward central elbow. Input image 2 is the established thesis style anchor; match its thin blue-gray outlines, Chinese Song/Ming serif typography, Times Latin lettering, small academic flowchart boxes and ample white space.
Render a polished, compact LANDSCAPE 16:9 diagram with white background, flat solid low-saturation fills only. Three visible fill roles: pale blue-gray #DFEAF0 for ordinary steps, warm beige-gray #E9DED4 for core contributions/endpoints, pale ivory #F3EBD8 for supplementary protocol steps. Slate-blue #657E91 thin outlines and stage dashes, charcoal orthogonal arrows. No gradients, shadows, icons, 3D, large background tint, internal overall title, figure number, footer note or caption.
Redesign with TWO major horizontal regions, plus one compact footer:
UPPER region, about two thirds of the useful height, labelled “Caltech主线”. Within it place data preparation at LEFT and the TWO contributions at CENTER and RIGHT. Left preparation is a compact vertical chain with exact labels “Caltech会话” → “代理能量重构” → “LRE三关系”. The middle contribution is a warm rectangle labelled “MRG-GCN预测” aligned with the end of the data chain, receiving a short horizontal arrow from “LRE三关系”. Small label above the middle: “贡献一：预测方法”. The RIGHT contribution is a clean rectangular GROUP MODULE labelled “贡献二：MDP诊断”. It receives a short straight horizontal arrow from the MRG-GCN box into the left border of the group module. Inside this diagnostic group, use THREE equal-size pale-blue cards arranged vertically with aligned spacing: “L1 参数干预”, “L2 蒸馏验证”, “L3 四格溯源”, connected downward. Beneath the three cards inside the group, a small ivory card “结构分析与预测支持”. The group itself is a receiving module, so the incoming horizontal arrow refers to the whole protocol, not only L2 or L3. Central model and diagnostic group must have balanced visual mass, no empty tall middle column, no long zigzag connector to L1. Warm accent distinguishes the two contributions from the data boxes.
LOWER region, a shallow independent dashed stage strip labelled “JPL补充验证”, contains a single left-to-right chain of FOUR compact equal-height boxes: “JPL会话” → “冻结协议” → “重新构图与训练” → “点预测与门控对照”. This strip has its own source; there MUST NOT be an arrow from the Caltech fitted model into JPL.
At bottom outside both regions, one centered compact warm endpoint labelled “证据综合与研究结论”. Exactly two tidy orthogonal arrows feed this endpoint: one from the final Caltech diagnostic group and one from the final JPL comparison box. These connectors use a reserved white gutter and never cross text or another arrow.
Use all stated Chinese labels exactly once. This figure depicts two Caltech contributions and an independently refitted JPL validation, not zero-shot transfer or JPL MDP replication. Short text only, uniform box padding, fine stroke weight, whitespace balanced across central model and diagnostic module. The whole composition should look like a careful academic flowchart, not a presentation infographic.
```

### 图1-2连线与中部模块修订

```text
Use case: infographic-diagram. Refine this newly generated 16:9 thesis roadmap. Retain its white academic canvas, typography, three restrained fill colors, Caltech main region, independent JPL shallow strip and single conclusion endpoint. Make TWO precise corrections:
1. Improve the EMPTY CENTER. Replace the isolated MRG-GCN box and floating label with a compact warm beige-gray GROUP MODULE, similar in height and outline weight to the right MDP module. Group heading exactly “贡献一：预测方法”. Inside it, place three equal blue-gray cards vertically, texts exactly “时间编码” → “节点门控融合” → “MRG-GCN预测”. Connect them downward with short arrows. The input arrow from LRE ends at the LEFT border of this whole prediction group; the output arrow from the RIGHT border goes straight to the LEFT border of the whole MDP group. Whole-group arrows refer to the full protocol, not to a coincident internal row. The middle should now be proportioned and balanced with the diagnostic group, with aligned top/bottom group boundaries and even internal whitespace. Preserve all four cards inside MDP.
2. CORRECT THE BOTTOM WIRES. Remove the incorrect vertical line from MDP into “点预测与门控对照”; remove the incorrect wire from “冻结协议” to conclusion. There are EXACTLY TWO independent contributions to conclusion:
   - Caltech exit: from the RIGHT outer border of the MDP group, run horizontally into an outer gutter at the far right of the drawing, then down OUTSIDE the JPL strip and its boxes, then left into the RIGHT edge of the conclusion box. Reserve enough outer white gutter to make this route clear.
   - JPL exit: from the BOTTOM of the final “点预测与门控对照” box, go down directly into the TOP-RIGHT area of the conclusion box using one short elbow below the JPL strip.
The two exit wires must remain visibly separate until they END ON the conclusion module, and never touch a JPL stage box except the JPL final box's own output. No Caltech-to-JPL link whatsoever. All JPL horizontal arrows are retained. No new wording, no total title, no gradients, shadows, icons or decoration. Use compact group widths and simple aligned orthogonal connectors.
```

### 图2-13精简重绘

```text
Use case: scientific-educational.
Asset: replace the rejected JPL protocol Figure 2-13 with a concise academic flowchart.
Input image 1 is the rejected long portrait chart: preserve scientific protocol but discard its shape and word-heavy layout. Input image 2 is the established thesis style anchor.
Use WHITE LANDSCAPE 16:9 canvas. Match the anchor's Chinese Song/Ming serif and Times Latin typography, thin slate-blue outlines and dashed stage frames, crisp orthogonal charcoal arrows. Flat pale BLUE-GRAY ordinary boxes, warm BEIGE-GRAY source and locked-checkpoint boxes, pale IVORY proxy-target and reserved-calibration boxes. The three hues must be clearly differentiated, restrained, and printed cleanly. NO gradients, shading, shadows, icons, thick bars, oversized blocks, internal title, figure number, long footnotes or extra labels.
Rebuild as THREE balanced stage panels left to right with equal height and consistent spacing. Panels have only thin dashed borders on white.
LEFT panel header “数据准备”. Small warm source “JPL会话” down to blue box “成熟记录筛选”. Split beneath into TWO compact parallel cards: left blue “行为与日历输入”; right ivory “回顾性代理目标”. The two cards feed a clean merge into the next panel. Do not feed target into input.
MIDDLE panel header “固定划分”. FOUR compact stacked boxes with exactly these texts: “训练 70%”, “调参 7.5%”, “校准 7.5%（保留）”, “测试 15%”. They are four sequential TIME PARTITIONS, not a computational chain; no arrows between the four cells. Below them a short single line “完整窗口留段”. Use blue for training/tuning, ivory for reserved calibration, warm gray for test.
RIGHT panel header “训练与评价”. FOUR vertically spaced compact modules:
1 blue “训练段拟合与训练”, small second line “标准化 · LRE · 四模型×三种子”;
2 blue “调参MAE选模”;
3 warm beige “锁定后一次测试”;
4 pale blue “整体与分层评价”, small second line “七日配对比较”.
Connect these FOUR modules downward by short arrows. Training partition sends a straight orthogonal arrow into module 1; tuning partition sends a separate orthogonal arrow into module 2; test partition sends a separate orthogonal arrow into module 3. Calibration has NO outgoing arrow. Align panel rows to make these arrows short, use white gutters, do not cross arrows or module text.
Only the text specified above may appear. All omitted details (10 nodes, 15 min, 96/4 windows, exact feature channels, target allocation/maturity assumption, models, seeds, epoch budget, test-key count and statistical CI) stay in the external thesis caption, NOT inside this image. Show data responsibilities clearly with substantially less text than the rejected image. Nothing may suggest zero-shot transfer, metered power, completed conformal calibration, physical causality or JPL mechanism diagnosis. Keep box sizes compact and diagram typography readable at a thesis column width.
```

### 图2-13入口连线修订

```text
Use case: infographic-diagram. Make a single connector correction to this concise 16:9 academic JPL protocol chart. Preserve every word, all three panels, all four partition cells, all four right-hand processing modules, typography, dimensions, colors and existing valid arrows. The only defect is the merged arrow from the two left input/target cards: it currently ends in EMPTY SPACE below the partition cells.
Turn the existing short text “完整窗口留段” below the four cells into a compact thin-outline pale blue-gray RECTANGULAR MODULE. Align the center height of this rectangle with the entry arrow. Move/route the merged entry arrow so its arrowhead ENDS EXACTLY ON THE LEFT BORDER of this new rectangle, at its vertical midpoint. It must never float in blank space or point between modules. The label stays exactly “完整窗口留段”, centered with normal padding and the same readable font as the other cards. This small receiving module remains within the middle “固定划分” panel. No outgoing arrow from reserved calibration, no changes to the right responsibilities, no additional words. White 16:9 canvas, flat blue-gray / beige-gray / ivory fills, thin slate outlines and charcoal orthogonal arrows; no gradients/shadows/icons.
```

## 正式稿同步

使用仓库的 `scripts/sync_formal_docx_figure_assets.py` 更新现有正式DOCX的图片媒体与等比高度，保留原正文、样式和公式；候选文件在完整图序与哈希核对通过后替换正式文件。编号仍为46幅（2 / 13 / 16 / 6 / 9），其他图件不改变。核对结果见 `JPL-imagegen-style-redraw-20261006-audit.json`。本轮未进行PDF页面渲染审阅。
