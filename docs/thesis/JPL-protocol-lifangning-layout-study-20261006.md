# 图2-13：李芳凝论文配图学习与JPL协议重绘（2026-10-06）

后续状态：用户要求规范中文、精简早停区域及重新配色，本轮版本已被同日的精简版本替代；当前图2-13及完整提示词见 `flowchart-annotation-cleanup-20261006.md`。本文件保留原图学习和迭代过程供追溯。

本轮依据用户反馈重新组织图2-13，使用内置ImageGen。参考论文用于学习图形的空间组织；配色沿用用户设计的论文专属体系。

## 实际查看的原始配图

参考文件：`/Users/xushuyuan/Downloads/基于深度学习组合模型的电动汽车换电站负荷预测研究_李芳凝.pdf`。

| 原图 | PDF页序号 | 论文页码 | 学习内容 |
|---|---:|---:|---|
| 图3-1：ICEEMDAN分解流程 | 46 | 38 | 横带分阶段；多个分支沿同一基线展开、沿共同母线汇合；回路置于外侧通道 |
| 图3-3：ALA优化过程 | 53 | 45 | 紧凑迭代回路；判断菱形及是/否分支；并列子区域的严格对齐 |
| 图4-3：BiTCN模型 | 75 | 67 | 主结构与内部结构的嵌套；成对模块统一尺寸、间距和层级 |

已用PDF渲染逐张查看完整页及图形区域，而非只依据此前的文字风格说明。临时参考图为 `/private/tmp/lifangning-fig3-1-layout.png`、`lifangning-fig3-3-layout.png` 和 `lifangning-fig4-3-layout.png`。参考图直接从PDF区域渲染，不作为本文正文图件。

## 从原图提炼的组织原则

1. **复杂度来自流程关系。** 将并行配置、训练迭代和不同评价路径展开，避免依靠增加解释句使图显得复杂。
2. **主线与阶段相互对应。** 数据契约置于上层横带，拟合选模和测试比较置于下层；职责连线沿留出的通道进入对应模块。
3. **并行模块使用共同基线。** 四模型等高并列，共用输入分叉和输出汇合；整体误差与分层误差构成成对评价路径。
4. **嵌套体现不同层级。** 外层虚线框标明阶段，内部小框表示操作；标准化与LRE图属于训练段拟合的内部对象，模型配置另形成三种子比较组。
5. **形状服务于含义。** 常规操作用矩形，训练终止用菱形，来源和结论用圆角框；反馈路径置于训练区域底部。
6. **短标签与正文分工。** 图内保留操作和职责，节点数量、成熟定义、窗口长度、预算和统计区间由正文与图注承载。

## 用户专属配色与解释边界

生成提示词锁定低饱和蓝灰流程框、暖米灰来源/检查点/结论、浅象牙色目标/校准/判断节点、石板蓝轮廓及深灰正交箭头。没有采用参考论文的粉色、亮黄色与绿色体系。16:9白底、宋体风格中文及Times风格拉丁字符继续沿用项目要求。

数据筛选只依据训练边界前成熟记录；训练数据仅进入标准化和LRE拟合，调参数据仅用于MAE选模，校准段没有输出连线。四个模型卡片表示比较配置，不声称硬件并行执行或共享学习权重；训练终止判断作用于各运行，所有运行完成并锁定检查点后才统一导出测试预测。整体误差进入七日配对比较；分层误差用于界定适用范围，不把时间块推断扩展到所有分层。

## 选定资产与迭代记录

- 最终工作区路径：`outputs/figures/fig2_13_jpl_validation_protocol.png`。
- ImageGen选定原生输出：`/Users/xushuyuan/.codex/generated_images/01a10a6b-4ba7-7f72-8036-ea5cf8ea9990/exec-efd06fef-ab27-4c16-b3cf-ef7339c139b8.png`。
- 旧版存入：`outputs/figures/archive/2026-10-06-jpl-protocol-reference-redraw/`。
- 未采用的迭代保留于ImageGen原生输出目录：`exec-58744c93-00ff-424e-b916-99b40af77508.png`、`exec-c8123835-33a9-4fe4-864e-bfaf70f44a5c.png`、`exec-e7ef9d08-f9c2-4cfc-a594-d990444b9d11.png`。这些版本分别存在职责连线或模型汇合线问题，未作为最终图件登记。
- 选定图逐张复核了标签、四段比例、模型分叉/汇合、训练反馈、检查点锁定和评价路径。尺寸、哈希和参考PDF指纹见同名source.json。

## 实际提示词

### 整体重绘

```text
Use case: scientific-educational.
Asset: complete redraw of a Chinese master's-thesis JPL validation protocol, Figure 2-13, refined academic flowchart, 16:9.
REFERENCE ROLES: Image 1 is the user's previous JPL diagram: retain its scientific contract and USER-OWNED palette ONLY, do not reuse its boring three equal tall columns. Images 2–4 are actual cropped figures 3-1, 3-3 and 4-3 from Li Fangning's thesis: learn their aligned parallel small boxes, nested dashed stage partitions, compact iteration loop, shape semantics and orthogonal routing ONLY. DO NOT copy their research content, colored pink/yellow/green palette, names, formulas or figure captions.
VISUAL STYLE: pure white 16:9 canvas; flat pale blue-gray #DFEAF0 process cards, warm beige-gray #E9DED4 source/locked-checkpoint/output cards, pale ivory #F3EBD8 target/reserved-calibration/decision nodes. Slate-blue #657E91 thin outlines and stage dashes; dark charcoal fine orthogonal arrows. Chinese Song/Ming serif typography, Times Latin model names. Consistent compact card heights, padding, font size, baseline grids. No gradients, shadows, glow, icons, thick arrows, internal total title, figure number, footnote or commercial infographic effects.
NEW STRUCTURE: TWO horizontal tiers, moderately complex but clean and densely aligned. A shallow top full-width data-contract tier; a lower wide training panel (about 62% width) and lower evaluation panel (about 34%) separated by a white routing gutter. Stage headings small and tucked at the upper-left of each dashed frame.
TOP TIER heading “数据契约”. Left-to-right flow: warm small “JPL会话” → blue “成熟记录筛选” → fork into two equal stacked mini-cards “行为与日历输入” (blue) and “回顾性代理目标” (ivory) → merge into blue “完整窗口留段” → compact FOUR-CELL chronological strip. The four cells are labelled EXACTLY “训练 70%”, “调参 7.5%”, “校准 7.5%（保留）”, “测试 15%”. The strip is chronological partitioning, NO computation arrows between its cells. Explicit connectors below the strip: training to the training fitting step, tuning to the MAE checkpoint-selection step, test to the one-time export step; calibration has NO outgoing arrow. Reserve routing gutters for these responsibilities.
LOWER LEFT heading “拟合与选模”. This is a structured training loop:
- Entry module “训练段拟合”, with two small equal inset cells “标准化” and “LRE图”.
- Feed a neat nested group headed “三种子比较”. It contains FOUR equal model cards in one horizontal row, EXACT labels “MRG-GCN”, “TCN”, “完整AGCRN”, “共享门控”. Branching and merging are symmetrical; the cards represent configurations, not necessarily concurrent hardware execution.
- Merge into “固定预算训练” → “调参MAE选模” → an ivory DIAMOND “停止训练？”. Arrange these on a compact common row or aligned U-shaped loop like reference 3-3, with clear space for the feedback line.
- A short label by the diamond reads “早停 / 轮次上限”. Its “否” branch loops back ONLY to “固定预算训练”, NEVER to refitting preprocessing or reinitializing models. Its “是” branch proceeds to warm “锁定全部检查点”.
- The tuning partition enters ONLY the “调参MAE选模” step. Locked checkpoints then enter the lower-right export module.
LOWER RIGHT heading “测试与比较”.
- Warm card “每run一次测试导出” receives BOTH the locked checkpoints from left and the test partition from above.
- Down to small blue “共同预测键”.
- Split into TWO equal aligned vertical mini-lanes: “整体误差” → “七日配对比较”; and “分层误差” → “适用边界”.
- Merge both lanes into a compact warm rounded endpoint “验证结论”.
This evaluation topology must NOT suggest that bootstrap inference was carried out on every stratum: the seven-day pairing belongs ONLY to the overall-error lane.
ALL arrowheads must touch the correct module borders; no dangling lines, no crossings over text, no ambiguous line intersections, no spaghetti. Draw control loop in a reserved inner gutter and data-role arrows in outer gutters. Uniform grid and short labels are more important than large empty areas. Keep all labels specified above verbatim. Omit exact node counts, tensors, epoch/patience numbers, result values and long caveats; these belong in the external caption.
Scientific constraints: another-site RE-FITTING, behavioral inputs distinct from retrospective energy target; train-only preprocessing and graph fitting, tuning-only MAE selection; ALL checkpoints locked before per-run single test export; reserved calibration unused in this experiment. No zero-shot transfer, measured power, completed conformal evaluation, causal inference or JPL MDP replication. Only prescribed words and connection labels may appear.
```

### 调参线及反馈标注修订

```text
Use case: scientific-educational. Precise final correction of this redesigned JPL protocol diagram.
PRESERVE the 16:9 canvas, upper data-contract band, lower-left nested model/training panel, lower-right test/evaluation panel, every existing card, all four model names, grid alignment, compactness, stage labels, all valid data arrows and two error-analysis lanes. This layout is now good.
FIX TWO CONNECTORS ONLY:
1. The “调参 7.5%” partition must supply ONLY “调参MAE选模”, not training fitting, checkpoint lock, test or an empty gutter. Redraw its wire: from the bottom of the tuning cell go down into the WHITE ROUTING GUTTER between the two lower panels, then turn LEFT through a clear horizontal corridor JUST ABOVE the bottom training/selection/decision row, then down into the TOP BORDER of “调参MAE选模”. Its arrowhead must touch that box. Stop this wire at selection; do not continue down to the locked-checkpoint handoff. Keep training→训练段拟合 and test→每run一次测试导出 exactly as separate inputs.
2. The “否” label is currently misplaced near the four-model merge into budget training. Delete that misplaced “否”. The actual NO branch must start at the BOTTOM PORT of the “停止训练？” diamond, run down into the inner bottom white gutter, go LEFT and up into the BOTTOM BORDER of “固定预算训练”; put “否” clearly beside this feedback branch near the diamond, with no text overlap. The “是” branch remains a short RIGHT arrow from diamond to “锁定全部检查点”. The feedback returns only to budget training. Move the small phrase “早停 / 轮次上限” from the wire corridor INTO the diamond as a small second line below “停止训练？” so it cannot overlap the feedback line.
COLOR LOCK: preserve the USER'S own restrained academic palette, NOT the reference thesis palette. Regular cards solid blue-gray #DFEAF0, source/lock/conclusion solid warm BEIGE-GRAY #E9DED4 (no pink), reserved calibration/target/decision solid pale ivory #F3EBD8 (no lemon yellow). Thin outlines and dashes slate-blue #657E91, charcoal arrows. Pure white background. Remove any soft gradients, textured fills or shadow effects. Keep readable Song/Ming Chinese and Times Latin, no invented labels, no other topology changes, no internal total title or caption.
All wire ends land on module borders; all routes are isolated in whitespace and do not cross text or other wires.
```

### 数据通道分离

```text
Use case: precise-object-edit. Correct ONLY three thin black data wires in this 1672×942 academic flowchart. Preserve ALL boxes, ALL text, ALL fills, fonts, dimensions, placement, the correct bottom “否” feedback loop, and the two evaluation lanes exactly. Do not redraw the modules. The training and tuning wires must be completely independent.
Use these pixel coordinates as guidance for the current image:
A) TRAINING wire: from the bottom of the “训练70%” cell near (1143,220), go down to y=298, left to x=533, then down with arrowhead into the TOP of “训练段拟合” near (533,367). This wire has NO junctions and NO branches. DELETE the extra T-junction at (1056,298) and the wire descending from it to the MAE selection box.
B) TUNING wire: from the bottom of “调参7.5%” near (1269,220), go down to y=308, left to x=1114 in the WHITE GUTTER, down to y=714, left to x=525, then down with arrowhead into the TOP border of “调参MAE选模” near (525,756). This must be the ONLY downward tuning-data arrow entering MAE selection. It never joins the training-input wire and ends at the MAE box, not at checkpoint export.
C) MODEL-MERGE wire: the four model cards merge near y=672; their common output goes down at x=498 to y=713, left to x=180, then down ONLY into the TOP of “固定预算训练”. DELETE the spurious branch near x=459 descending from this model-merge wire into “调参MAE选模”. The MAE box still receives the VALID horizontal arrow from the RIGHT edge of “固定预算训练”.
After correction, “调参MAE选模” has exactly TWO incoming arrows: a horizontal trained-model arrow from budget training and one tuning-data arrow from above. “训练段拟合” has exactly one training-data arrow. No other data/control wire may join these three paths. Preserve the test-data arrow, lock→export handoff, MAE→diamond→lock path, and diamond NO→budget-training feedback. Do not add text or change colors.
```

### 模型汇合线修订

```text
Precise diagram wire repair. Preserve this entire image unchanged EXCEPT the U-shaped wire above the bottom two training boxes.
The existing U-shaped wire incorrectly links the TOP of “固定预算训练” to the TOP of “调参MAE选模”. Delete its right descending leg into “调参MAE选模”. That U is not a valid connection.
Instead, connect the COMMON OUTPUT BUS under the four model cards (horizontal line at y≈672, from x≈206 to805) into the TOP of “固定预算训练” (x≈180,y≈756). One wire: start at the midpoint of that model output bus, x≈498,y≈672; go DOWN to y≈713; go LEFT to x≈180; go DOWN with arrowhead ending on the TOP border of “固定预算训练”. Do not branch this wire.
Leave the OTHER long tuning wire completely untouched: it comes from “调参7.5%” via the white right gutter and enters the MAE box from above near x≈511. Leave the valid horizontal arrow from “固定预算训练” into “调参MAE选模” untouched.
Final local invariant: model-output bus has one exit, into budget training only. MAE has exactly two inputs, trained-model arrow from LEFT and tuning-data arrow from ABOVE. All cards, labels, colors, good wires, NO feedback loop, evaluation and entire layout stay unchanged.
```

## 正式论文同步

用仓库现有媒体同步脚本更新正式DOCX的选定PNG及等比高度，保留正文、样式和原生公式。图序仍为46幅，图1-2不改动。媒体顺序、文件哈希和XML内容核对记录见 `JPL-protocol-lifangning-layout-study-20261006-audit.json`。本轮未进行PDF页面渲染审阅。
