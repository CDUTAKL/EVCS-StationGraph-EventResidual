# 流程图悬浮注释清理与JPL协议精简（2026-10-06）

后续状态：本文件记录的四张旁注清理图继续使用；图2-13右下评价区随后进一步对齐，当前图2-13与图1-2及提示词见 `roadmap-evaluation-grid-polish-20261006.md`。本文件保留协议精简及图注修订记录。

工具：内置ImageGen。按用户要求修改图2-1、图2-7、图2-10、图3-8、图2-13。涉及旧版均保存在 `outputs/figures/archive/2026-10-06-flowchart-caption-cleanup/`。

## 注释与图注的分工

| 图号 | 图片修订 | 图注处理 |
|---|---|---|
| 图2-1 | 移除右侧“非在线电表功率”和测试统计量旁注及引线 | 保留代理能量定义，并明确训练/验证职责和旧上游全时期统计例外 |
| 图2-7 | 移除右下孤立的“测试集不参与阈值计算”框 | 原图注已明确训练期标准差、验证期95%阈值及测试不参与阈值估计 |
| 图2-10 | 移除右侧孤立的“target_event仅作事后评价”虚线框 | 原图注保留标签评价、规则路由及旧协议边界 |
| 图3-8 | 移除测试前向右侧两条注释及短引线 | 补充标准化和LRE由训练集拟合；原“窗口不跨切分边界”不适用于旧协议，改为指向2.1.1节已披露的实际窗口限制 |
| 图2-13 | 改为“测试预测导出”，去除早停菱形及回路，统一三个底部步骤尺寸与水平连接；重新配色并整理职责连线 | 明确每次训练运行仅一次测试导出，早停与预算见3.8.2节；时间块推断仅接整体MAE |

上述四张旧图的流程主体保持不变；图片中删除的边界说明由图注承载，不增加无锚点的装饰文字。

## 图2-13进一步学习与简化

另查看李芳凝论文图3-13（PDF第66页，论文第58页），学习其同层模块严格对齐、单一母线分叉/汇合和分阶段处理的组织方式。结合此前已查看的图3-1、3-3、4-3，本轮保留数据契约、四模型比较及两条评价路径，将迭代控制细节留给正文。参考论文路径和PDF指纹记录于source.json。

配色继续属于本文：普通步骤用浅蓝灰 `#DCE6EC`，来源、主模型、锁定与结论用中性暖米灰 `#E5E0D8`，代理目标及保留校准用浅象牙 `#F0EADB`；轮廓使用石板蓝灰 `#607585`，阶段虚线使用较淡的 `#97A7B3`。这些值为生成指令，不将生成图每个像素声称为精确色值。保持白底16:9、宋体风格中文与Times风格拉丁符号。

本轮选定ImageGen原生文件（目录：`/Users/xushuyuan/.codex/generated_images/01a10a6b-4ba7-7f72-8036-ea5cf8ea9990/`）：

- 图2-1：`exec-1521e20f-288d-48e5-97ad-19a0de982791.png`
- 图2-7：`exec-643bba0f-9f6d-42f1-88a4-2abc29c49440.png`
- 图2-10：`exec-f6f734c3-31a3-4e6c-a04e-da17de1a0685.png`
- 图3-8：`exec-89a12cab-1741-4826-ba7e-cf49dc41dbe1.png`
- 图2-13：`exec-a0f7dd7c-868e-49f6-86d0-ea6d06a87a9d.png`；初次简化结果 `exec-d4be74ad-889f-4ba7-b898-e899dd1dcfe6.png` 存在职责连线错误，修订后才选定。

## 实际提示词

### fig2_1_data_reconstruction

```text
Precise image edit, academic flowchart. Remove ONLY the free-standing right-side text “非在线电表功率” in the upper stage. Also remove the right-side annotation “测试集不参与统计量计算” and its short leader attached to the test-set box, because the precise scope is supplied in the external caption. Restore pure white in those annotation areas. Preserve ALL process boxes, exact remaining Chinese/Latin text and numbers (31,424;118,818×10×7;83,103;17,807;17,809), their positions and size, stage headings, dashed borders, valid arrows, fonts, palette and the white 16:9 canvas. Do not add labels, notes, icons, new connectors or reorganize the diagram. The two removed statements will be in the external manuscript caption. Nothing else changes.
```

### fig2_7_event_score_flow

```text
Precise image edit. Remove ONLY the isolated bottom-right rectangle containing “测试集不参与阈值计算”, including its outline and fill. Restore white canvas in that area. Preserve ALL other flowchart geometry, text, fonts, numbers, component boxes, thresholds, arrows and stage borders exactly. In particular retain the training-statistics arrow into normalization, validation→95% quantile threshold, trigger decision, and future-only two-step extension. Retain 16:9, existing low-saturation blue-gray/beige/ivory palette. Do not add any floating text or connector. The removed statement remains in the external caption.
```

### fig2_10_dual_window_definition

```text
Precise image edit. Remove ONLY the isolated right-lower dashed note box “target_event仅作事后评价”, including its text, fill and dashed border. Fill its old region with pure white. Preserve ALL other diagram modules and text, two source branches, variable labels target_event and rule_trigger, four-cell matrix 11/10/01/00, proportions 1.43%/0.43%, total712,360, arrows into diagnostics, and the dashed rule_trigger→回溯规则路由 connector exactly. Preserve 16:9 proportions, font, style and palette. Add no new note or label. The removed qualification is carried in the external caption.
```

### fig3_8_train_predict_pipeline

```text
Precise image edit. Remove ONLY the two small dashed annotation boxes at right of “测试集前向”: “窗口不跨切分边界” and “测试集不参与统计量计算”, together with their short dashed leaders. Restore pure white background in those areas. Preserve ALL process modules, numeric table, training stages, early-stopping decision, original loop, frozen checkpoint→test-forward arrow, six-cell evaluation panel, exact remaining text, fonts, palette, stage borders and 16:9 canvas. Do not add any replacement note, invented statement, new arrow or layout change. Detailed preprocessing scope and the legacy protocol's actual window-boundary exceptions will be stated accurately in the external caption.
```

### 图2-13精简与重新配色

```text
Use case: scientific-educational.
Refine and simplify this Chinese thesis JPL protocol diagram. Image 1 is the current diagram; image 2 is Li Fangning thesis Figure3-13 and image3 Figure3-1, which are references ONLY for aligned branch/merge geometry and stage hierarchy, never for their words, data, models or colors.
KEEP a white 16:9 canvas with the useful upper data-contract band and lower training/evaluation regions. But simplify the lower-left control chain, REMOVE the large early-stopping diamond, feedback loop, “是”, “否” and stopping annotations completely. Detailed early stopping belongs in the external caption.
NEW POLISHED PALETTE, in the user's own blue-gray / warm-gray / ivory family: ordinary process fills solid #DCE6EC, primary MRG-GCN and source/lock/endpoint fills solid neutral warm-gray #E5E0D8 (NO pink/red tint), target/calibration fills solid light ivory #F0EADB. Outlines slate blue-gray #607585; dashed region outlines softer #97A7B3; charcoal arrows and near-black text. Flat fills, NO gradients/shadows. White background. Chinese Song/Ming serif and Times Latin, consistent font sizes and compact padding. Colors should be calm and balanced, edges NOT bright cyan or golden yellow.
Preserve UPPER band heading “数据契约” and its short exact modules:
“JPL会话” → “成熟记录筛选” → two parallel stacked cards “行为与日历输入” and “回顾性代理目标” → merge into “完整窗口留段” → four-cell time strip “训练 70%” | “调参 7.5%” | “校准 7.5%（保留）” | “测试 15%”. Chronological cells have no computational arrows between them.
LOWER LEFT heading “拟合与选模”:
Top compact blue “训练段拟合” group contains two equal inset cells “标准化” and “LRE图”.
Below it a symmetrical four-card branch in a nested group labelled “三种子比较”: “MRG-GCN”, “TCN”, “完整AGCRN”, “共享门控”. All four model cards same dimensions, exactly aligned. MRG-GCN warm gray, three controls blue-gray. Merge outputs on one horizontal bus with EXACTLY ONE downward exit.
Below the model group, one CLEAN HORIZONTAL ROW of THREE equal compact rectangular modules, all at the same vertical center:
“固定预算训练” → “调参MAE选模” → “锁定全部检查点”.
The sole model-bus exit enters the TOP BORDER of “固定预算训练”. Do not connect model-bus directly to selection or lock.
Remove the old diamond/control-loop area and use the freed space for even margins; no giant empty block or long trailing loop.
LOWER RIGHT heading “测试与比较”:
Top warm-gray card EXACTLY “测试预测导出” (replace the unprofessional mixed-language wording; DO NOT use run or 每run anywhere).
Down to small “共同预测键”, then two equal aligned mini-lanes:
“整体误差” → “七日配对比较”
“分层误差” → “适用边界”.
Both merge cleanly into rounded warm-gray “验证结论”.
DATA RESPONSIBILITY WIRES: training cell enters only “训练段拟合”; tuning cell enters only TOP of “调参MAE选模” through a RESERVED WHITE GUTTER; test cell enters only TOP of “测试预测导出”. Calibration has no outgoing arrow. Warm locked-checkpoint module enters LEFT BORDER of test export by one short orthogonal route. All three responsibilities remain separate and touch correct module borders. No intersections with model-bus or text.
IMPORTANT: model configurations are compared independently, not ensembled. Checkpoints selected by tuning MAE are all locked before each run exports testing once; external caption states this once-only rule and training budget. No completed calibration, actual-metered power, causal inference or MDP replication.
All stated labels appear exactly once; no notes outside modules, no extra legends, caption, total title or long sentences. Uniform grid, restrained spacing and tidy branch/merge lines like the layout references; this is a careful thesis figure, not a colorful infographic.
```

### 图2-13职责连线修订

```text
Precise edit of two thin responsibility wires only. Preserve this simplified diagram's boxes, every label, palette, model branching/merging, left-to-right bottom chain and evaluation lanes EXACTLY. Do not alter cards or add words.
In the current approximately 1672×941 image:
1. Training cell “训练70%” at x≈1139,y≈221 has one valid wire: down to y≈299, left to x≈533, then arrow down into TOP of “训练段拟合” at y≈370. REMOVE its spurious branch at x≈935,y≈299 descending straight to the “锁定全部检查点” box. Training data never directly enters checkpoint lock. After deletion the training wire is unbranched.
2. Tuning cell “调参7.5%” at x≈1267,y≈221 currently ends as a loose horizontal stub around (1143,311). Replace that dangling stub with a SINGLE correct wire: from tuning bottom down to y≈311, left to x≈1084 in the white gutter between the lower panels, down to y≈748, left to x≈545, then down with arrowhead touching TOP BORDER of “调参MAE选模” near (545,781). The tuning route stays BELOW the training horizontal wire and does not join it; its lower horizontal segment stops at x≈545 so it does not intersect the four-model output route at x≈528.
Do not change the valid training-fit input, model-output→budget-training route, budget-training→MAE-selection horizontal arrow, MAE→lock horizontal arrow, lock→test-export arrow, or test-partition→export arrow.
Final invariant: “调参MAE选模” receives exactly two inputs (trained configuration from LEFT, tuning data from ABOVE); “锁定全部检查点” receives only the horizontal arrow from MAE selection; no dangling lines remain. All other pixels should remain visually unchanged.
```

## 审阅与正式稿同步

逐张查看选定PNG，核对删除区域、主流程标签和数值保留、职责连线与JPL简化链条。图2-13不再出现“run”字样或早停回路；模型汇合只进入预算训练，调参数据只进入MAE选模，锁定后与测试数据共同进入预测导出，校准段无输出连线。

主文及正式DOCX同步更新图注与五张图片，图号仍为46幅（2 / 13 / 16 / 6 / 9）。图片尺寸、哈希和来源登记于source.json及manifest；图序和原生公式核对见 `flowchart-annotation-cleanup-20261006-audit.json`。本轮不声称完成PDF页面渲染审阅。
