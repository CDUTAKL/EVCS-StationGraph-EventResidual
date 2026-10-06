# 图1-2下部与图2-13评价区版式修订（2026-10-06）

后续状态：图2-13继续采用本文件选定的评价网格版本；图1-2已按用户反馈重新设计整图，当前图1-2及提示词见 `roadmap-four-stage-redesign-20261006.md`。本文件保留局部修订过程。

本轮根据用户截图和审美反馈，使用内置 ImageGen 对两张现有原生 PNG 做局部编辑。图号、论文研究结论及两图完整图注不变。当前正文图件是 `outputs/figures/fig1_2_roadmap.png` 与 `outputs/figures/fig2_13_jpl_validation_protocol.png`。

## 具体修订

| 图 | 用户指出的问题 | 选定版修订 |
|---|---|---|
| 图1-2 | 下部大型椭圆与两条右侧长回折线使版面松散 | JPL四步骤沿同一基线横排；结论改为右侧矩形，JPL从左、Caltech从上分别接入；取消底部独立椭圆和绕行线 |
| 图2-13 | 右下评价卡片宽度、中心轴、汇合线不整齐 | 导出、共同键和结论改为三张对齐的宽矩形；整体与分层评价采用双列两行网格，分叉与汇合沿中心轴组织；统一间距与线条 |

保留白底16:9、宋体风格中文、Times风格拉丁字符及论文自有蓝灰、暖米灰、象牙色体系。本轮没有增加图内说明句或浮动注释。再次查看此前从李芳凝论文原图渲染的图3-13和图4-3参考区域，继续采用共同母线、并列卡片和层级分区的组织原则；不采用参考论文的亮色体系。

图2-13提示词对浅蓝灰 `#DCE6EC`、暖米灰 `#E5E0D8`、石板轮廓 `#607585` 作了约束。坐标和色值用于指导生成，未声称生成图在每个像素上精确等宽或精确匹配色值；选定标准为阅读尺度上的对齐、比例与语义一致。

## 学术含义复核

- 图1-2：Caltech预测方法与MDP诊断属于主线，JPL在自己的数据上重新构图和训练。两条路径各自进入证据综合，不把Caltech模型连入JPL流程，也不表示JPL已复现MDP三层诊断。
- 图2-13：训练段接标准化与LRE拟合，调参段接MAE选模，测试段接预测导出；校准段保留且无输出连线。锁定全部检查点后才导出测试预测。
- 整体误差进入七日配对比较；分层误差进入适用边界。两路汇合不表示在每个分层上都做了时间块推断。
- 原图注继续承担每次训练运行仅导出一次测试预测、完整窗口留段及代理目标等协议说明。
- 主代理和独立审阅代理均查看了两张选定原图；未发现需继续修复的标签或连线错误。

## 来源与保存

生成目录：`/Users/xushuyuan/.codex/generated_images/01a10a6b-4ba7-7f72-8036-ea5cf8ea9990/`。

| 图 | 选定原生输出 | 工作区路径 |
|---|---|---|
| 图1-2 | `exec-46331b1a-f54f-4d50-9020-fb95837e8e5b.png` | `outputs/figures/fig1_2_roadmap.png` |
| 图2-13 | `exec-78f1d1a7-44ec-4bc8-aabc-dfae7520e6fe.png` | `outputs/figures/fig2_13_jpl_validation_protocol.png` |

图2-13初次局部修订 `exec-d539598a-ebb8-4f29-887c-141026e44a76.png` 的宽框与双列总宽仍不协调；追加网格约束后选择第二版。原生文件保留，不用脚本重新绘制、重着色、拼接或包装成SVG。

替换前的两张PNG、source.json、manifest、ImageGen登记及正式DOCX保存在 `outputs/figures/archive/2026-10-06-roadmap-evaluation-grid-polish/`。尺寸与SHA256以各图source.json为准；当前Git源状态为 `5dac84e`。

## 实际提示词

### 图1-2下部整理

```text
Use case: precise-object-edit, scientific academic diagram.
Edit target: the supplied thesis Figure 1-2 roadmap. Refine only its LOWER JPL strip, final evidence-synthesis block and associated two output wires. Preserve the entire UPPER Caltech main line, all its text and internal connections, MRG-GCN and MDP modules. Keep a crisp white 16:9 landscape canvas.

PROBLEM: the present wide rounded conclusion sitting alone below the JPL strip, with two long right-angle wires entering its right edge, looks bottom-heavy and awkward. Remove that detached oval and BOTH old conclusion wires.

REBUILD LOWER REGION on a precise baseline:
- A shallow dashed JPL stage occupies the lower LEFT approximately 82% of page width; small stage heading exactly “JPL补充验证”, normal Chinese serif, not giant display typography.
- Within it, four compact rectangular cards in a single aligned row, same height and vertical centers, with balanced widths to fit text: “JPL会话” → “冻结协议” → “重新构图与训练” → “点预测与门控对照”. Use equal inter-card arrow gaps and regular internal padding. Make this row and its frame generous but compact. Keep every label exactly once, no other wording.
- To the RIGHT of this JPL stage, OUTSIDE the dashed JPL frame in a reserved white synthesis column, place ONE warm beige-gray ordinary RECTANGULAR outcome card, same height as the JPL cards, aligned on the SAME horizontal centerline. Its label exactly “证据综合与研究结论”, gracefully wrapped over two centered lines “证据综合” / “与研究结论”. No capsule, no extra frame or heading. Left-to-right chain now ends on this card by a short horizontal arrow from the RIGHT border of “点预测与门控对照” to the LEFT border of the conclusion. This arrow crosses only the right dashed JPL stage boundary, never any other node.
- The SECOND independent input is from the BOTTOM BORDER of the upper MDP group as a whole, NOT from L1/L2/L3 individually: leave the diagnostic group at its bottom near the right side, go down a short distance into the WHITE gap between stages, move right to the synthesis-column center, then descend vertically into the TOP BORDER of the warm conclusion card. Reserve the rightmost synthesis column exclusively for this wire. It must NOT enter or touch the JPL stage, its title, any JPL box or arrow.
- Exactly TWO inputs terminate on the final card: JPL from left, Caltech from above. No junction linking the Caltech wire to the JPL chain. Eliminate all long bottom rails and all duplicate final arrows. Make bottom white margin about the same as top margin. The refined composition should feel balanced and editorial, with a compact open lower region.

STYLE: retain existing thin slate-blue outlines, Chinese Song/Ming serif and Times Latin; white canvas, low-saturation blue-gray routine cards, warm neutral beige-gray final card, pale ivory accents. Flat fills, no gradients, shadows, rounded stage borders, icons or decoration. A carefully typeset research-paper flowchart with fine lines and readable text. Preserve all scientific labels and upper layout exactly. This is independently refitted JPL validation, with no Caltech-to-JPL model transfer and no JPL MDP replication.
```

### 图2-13评价区初次重排

```text
Use case: precise-object-edit, scientific academic diagram.
Edit target: the supplied full Figure 2-13 JPL validation protocol.
Change ONLY the lower-right “测试与比较” panel: internal card sizes, alignment, spacing, branching/merging wires and the final conclusion shape. Keep the entire top “数据契约” band and entire lower-left “拟合与选模” panel UNCHANGED, including all wording, four split percentages, standardization/LRE fitting, four model cards, three training/selection/locking cards and all their valid wires. Keep exact white 16:9 landscape.

The lower-right evaluation panel needs a precisely aligned symmetric grid instead of uneven card widths, an off-center vertical spine and cramped connectors. Preserve the panel heading “测试与比较” and its thin dashed rectangular frame. Recompose inside it:
1. Center a warm beige-gray rectangular “测试预测导出” card horizontally in this panel. It receives the EXISTING test partition data at TOP and locked-checkpoint handoff at LEFT. Retain those correct scientific inputs; adjust only the last local turns to reach the respective border midpoints.
2. Below it, center a blue-gray rectangular “共同预测键” card of EXACTLY THE SAME WIDTH AND HEIGHT. Connect by one short vertical arrow along the shared centerline.
3. Below that, split into TWO narrow equal-width lanes. Four cards, all exactly same width and height, on a strict 2×2 grid:
   left top “整体误差”; right top “分层误差”;
   left bottom “七日配对比较”; right bottom “适用边界”.
   Corresponding columns are centered on their own vertical axes, the two rows share baselines, with equal gaps. Each card has ample even text padding and normal readable font. Size the cards to the longest label, not the other way around.
   A centered short stem from “共同预测键” reaches ONE horizontal branching bus, symmetric left/right; two equal-length arrows drop to the two top cards. Each top card connects vertically to its OWN lower card by a short identical arrow.
4. From the bottom centers of both lower cards, equal-length vertical lines descend to ONE clean symmetric horizontal merge bus. A short central downward arrow then enters the TOP CENTER of “验证结论”, a warm beige-gray ordinary RECTANGLE. This final card has exactly the same width and height as “共同预测键” and “测试预测导出”, sharing their centerline. Remove the old rounded capsule completely.
5. The three full-width cards have identical left/right alignment; the 2×2 grid spans the SAME total width. All five vertical gaps are evenly considered, no crowded merge immediately beside a box, no stray line, no off-center T-junction. The panel should use its available height with generous inner margin and an orderly rhythmic hierarchy. All arrowheads touch borders precisely. Thin dark slate orthogonal arrows, identical line weight. No crossings, duplicate stems, unconnected endpoints or wires across labels.

Palette remains the USER'S own scholarly blue-gray / warm gray / ivory, never new bright hues: routine pale blue-gray #DCE6EC, export and conclusion neutral warm beige-gray #E5E0D8, thin slate #607585, frame dashes #97A7B3, dark charcoal serif text and arrows. Flat solid fills, no gradient, shadow, glow, icons, illustration, additional title or footer.
Only the seven prescribed evaluation labels appear, each once. Scientific topology MUST remain overall error → seven-day paired comparison; stratified error → scope boundary; both feed validation conclusion. This does not apply seven-day inferential comparison to every stratum. All other image regions and scientific content unchanged.
```

### 图2-13网格比例校正

```text
Use case: precise-object-edit. Precise grid correction of ONLY the lower-right “测试与比较” panel in this 1672×940 thesis diagram. Preserve ALL other regions, text, colors, model connections, train/tuning data wires and locked-checkpoint logic unchanged. Do not redesign the whole figure.

The previous edit still has unequal left/right evaluation cards and three long cards narrower than the 2-column grid. Fix geometry with this explicit coordinate guide (small subpixel deviations acceptable):
- Dashed panel remains x1112..1648, y320..910.
- Set evaluation center axis x1380, inner left/right edges x1156 and x1604.
- THREE main cards ALL have exactly width448 and height64:
  “测试预测导出” bounds (1156,415)..(1604,479).
  “共同预测键” bounds (1156,513)..(1604,577).
  “验证结论” bounds (1156,829)..(1604,893).
  All ordinary rectangular shapes, not rounded. Same font size, padding, centered Chinese serif.
- FOUR branch cards ALL have exactly width212 and height64:
  “整体误差” (1156,623)..(1368,687);
  “分层误差” (1392,623)..(1604,687);
  “七日配对比较” (1156,723)..(1368,787);
  “适用边界” (1392,723)..(1604,787).
  They have equal widths, same heights, aligned rows, column centers x1262 and x1498. The total two-column span aligns exactly with the three main-card left/right edges. Keep labels exactly and do not split words.
- Internal arrows: export bottom center(1380,479) → common top center(1380,513). Common bottom center(1380,577) descends to horizontal split bus at y600 from x1262 to1498, equal vertical arrows drop from the bus ends into the two top branch cards y623. Branches each have vertical short arrow from y687 to723 at their column center. Both bottom cards drop at x1262 and1498 from y787 to symmetric merge bus y807. A central arrow from (1380,807) ends on top center of conclusion (1380,829).
- TEST input: keep test-cell origin at(1562,220). Its existing wire can go down to y299, left to x1380, then down with arrowhead exactly on export TOP CENTER(1380,415). This route cannot join training or tuning wires.
- LOCKED-CHECKPOINT input: existing bottom-left lock output ends in the left-side reserved gutter. Retain this source and existing route until x1128; go UP along x1128 to y447, then RIGHT with arrowhead ending on export LEFT BORDER(1156,447). No other input to export.
- Keep small “测试与比较” heading in its current position. A consistent dark slate fine stroke, no crossings, no stray old box outlines or old wires.

Warm neutral #E5E0D8 export/conclusion, blue-gray #DCE6EC common-key and four analysis cards, thin #607585 borders. White background, unchanged restrained academic style. Everything outside these geometric changes stays unchanged. The resulting diagram should show a precise shared baseline grid and clear symmetric parallel branches, not approximate uneven rectangles.
```

## 正式论文同步

使用仓库现有 `scripts/sync_formal_docx_figure_assets.py` 同步正式DOCX的选定PNG与等比尺寸。正文、图注及原生公式保留。主文仍为46幅图，第1—5章分别为2、13、16、6、9幅。媒体顺序、图件哈希、正文与公式保留情况记录在 `roadmap-evaluation-grid-polish-20261006-audit.json`。本轮未进行DOCX转PDF后的页面渲染审阅。
