# 图1-2与JPL验证协议流程图的ImageGen记录

本文件记录首版生成过程。用户反馈后，两图于同日按16:9项目规范重新绘制，当前选定版本见 `JPL-imagegen-style-redraw-20261006.md`；本文件所述首版及来源已存入 `outputs/figures/archive/2026-10-06-jpl-imagegen-style-redraw/`。

日期：2026-10-06。生成时仓库HEAD：`5dac84e`。工具：内置ImageGen。

## 图1-2 总体技术路线

更新Caltech预测方法、MDP诊断与JPL补充验证三条路径。JPL使用本站数据重新构图和训练，不表示Caltech模型直接迁移；MDP诊断证据来自Caltech。

- 工作区输出：`outputs/figures/fig1_2_roadmap.png`
- 原生生成输出：`/Users/xushuyuan/.codex/generated_images/01a10a6b-4ba7-7f72-8036-ea5cf8ea9990/exec-46de60cb-fea8-47c5-9e0c-eda15494e8f5.png`
- 编辑参考：此前的`fig1_2_roadmap.png`，已保存至`outputs/figures/archive/2026-10-06-jpl-imagegen-update/`。

### 实际生成提示词

```text
Use case: infographic-diagram. Asset: replacement for figure 1-2 in a Chinese master's thesis.
Edit the supplied image as the style reference and prior technical roadmap. Produce a NEW carefully arranged version that incorporates the newly completed JPL supplementary refit validation. Keep the restrained white background, muted blue-gray rectangles, warm pale gray/gold accents, thin blue-gray panel borders, black Chinese serif-style text and clean orthogonal arrows. Replace the old crowded topology with a clear three-column landscape layout, about 3:2 aspect, high resolution, generous white margins. Flat solid fills only.
The three vertical columns should have these exact headers:
left: "Caltech主线：预测方法"
middle: "Caltech主线：MDP诊断"
right: "JPL补充验证"
Left column in order: "Caltech ACN会话" → "15 min节点代理能量" → "LRE三关系构建" → "MRG-GCN预测".
Middle column in order: "L1 参数干预" → "L2 蒸馏验证" → "L3 四格溯源" → "结构分析与预测支持". Connect the left final MRG-GCN box horizontally to middle L1, meaning the Caltech fitted model enters Caltech diagnosis.
Right column in order, with independent JPL source at top: "JPL ACN会话" → "冻结协议与节点筛选" → "重新构图与训练" → "点预测与同参数门控对照". This is a separate refit validation on another ACN site; no arrow from the fitted Caltech model into JPL, no MDP steps in the JPL column. Use a lighter warm-gray background for this supplementary column so the two central contributions remain visually primary.
All three columns feed an aligned common bottom strip "证据综合与适用边界", then a small final box "研究结论".
Use each specified Chinese label verbatim, legible and spelled correctly. Do not add any extra labels, modules, result numbers, figure number, title, caption, icons, network decorations, charts, gradients, shadows, glow or 3D. The drawing is a research technical roadmap, not a physical electrical topology. Use ample spacing so the cross-column MRG→L1 connector does not overlap text or any other arrow.
```

## 图2-13 JPL固定协议重新拟合验证流程

新生成流程图，区分事件时刻行为输入与回顾性代理目标，标明四段时间划分、训练段拟合、调参选模、检查点锁定及一次测试导出。校准段保留，不代表本轮已经完成JPL共形区间评价。

- 工作区输出：`outputs/figures/fig2_13_jpl_validation_protocol.png`
- 原生生成输出：`/Users/xushuyuan/.codex/generated_images/01a10a6b-4ba7-7f72-8036-ea5cf8ea9990/exec-f87afb93-1640-4e8c-9693-9cde2d7f8a62.png`
- 数据协议：`configs/data/SG-DATA-007-jpl-eventtime-v1.json`
- 训练配置：`configs/experiments/SG-EXP-028-jpl-independent-site.json`
- 冻结记录：`docs/thesis/JPL-validation-freeze-20261005.json`
- 实验报告：`docs/thesis/experiment-reports/SG-EXP-028-jpl-independent-site-validation-report.md`

### 实际生成提示词

```text
Use case: scientific-educational. Asset: Chinese master's thesis JPL validation protocol flow diagram.
Generate one brand-new high-resolution academic flow diagram on pure white, flat pale blue-gray boxes, restrained warm pale gray/gold annotations, thin blue-gray borders and black Chinese serif-style typography. Match the visual language of the existing thesis: minimal, spacious, no pictograms, no gradients/shadows/glow/3D, no internal title, figure number or caption. Use a portrait-like or near-square layout approximately 4:5 that fits the staged protocol; do not force 16:9.
Draw exactly this staged topology, with clearly separated input and target lanes:
1. Top box "JPL ACN会话".
2. Box below "训练期成熟记录筛选10节点" with a short small line "稳定spaceID映射 · UTC 15 min栅格".
3. Split into TWO parallel boxes at the same height. Left blue-gray box text "行为与日历输入" and smaller lines "接入 / 离站 / 活跃 + 当地日历" and "X：96 × 10 × 7". A small gray note beneath left: "事件即时上报假设". Right warm pale-gray box text "回顾性代理目标", smaller lines "会话总电量按接入至断开区间均匀分摊" and "Y：4 × 10"; note immediately below right "标签成熟：断开与非空完成时间的较晚者". No arrow from retrospective target into behavior input.
4. Both lanes converge to a box labeled "按时间切分与完整窗口留段". Inside, four horizontally ordered small cells: "训练 70%" | "调参 7.5%" | "校准 7.5%" | "测试 15%". A short annotation "96步历史与4步目标不跨分段". The calibration segment is reserved and does not feed checkpoint selection; do not draw it as fitted/used for this round.
5. Box "仅训练段拟合标准化与LRE图".
6. Box "4种模型 × 3种子固定预算训练" with small line "MRG-GCN / TCN / 完整AGCRN / 共享门控" and small line "最多60轮 · patience 8". Below it a separate box "调参MAE选择最佳检查点".
7. Box "全部检查点锁定后，每个run一次测试导出".
8. Final box "整体与分层误差 · 七日配对时间块比较", smaller line "632,640预测键 · 24个七日块".
All main stages are connected in downward order by simple clean orthogonal arrows; keep the input and target split evident. Small bottom note "另一ACN站点的固定协议重新拟合验证". This schematic must not imply zero-shot transfer, actual metered power, completed JPL conformal evaluation, physical causality, or JPL MDP replication. Do not include performance values or quantitative result plots. Render all specified labels accurately and with enough room, avoid extraneous repeated wording.
```

## 人工审阅与同步

两张原生PNG已逐张查看，核对文字、箭头方向、场站关系及验证边界。保留原始生成图，不包装为SVG；文件尺寸和SHA-256见各图同名source.json。原图、旧manifest及旧ImageGen登记文件保存在上述归档目录。

图1-2仍用于1.5节。图2-13置于2.6节，2.1.3节前向引用该图；不改动既有图2-1至2-12的编号。此前已提交的图3-15、3-16补入3.8.2节，主文因此共46幅图（2 / 13 / 16 / 6 / 9）。

正式DOCX沿用仓库的学校模板生成器，图序与选定PNG逐一核对；核对记录见 `JPL-imagegen-diagrams-20261006-audit.json`。本轮未进行PDF页面渲染审阅。

本机已有公式依赖分别位于内置Node包目录和临时temml目录。实际使用的生成命令（在仓库根目录运行）：

```sh
THESIS_MATH_NODE_PATH='/Users/xushuyuan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules:/private/tmp/codex-thesis-temml-runtime/node_modules' .venv/bin/python scripts/generate_thesis_main_docx.py
```

临时依赖目录可能在系统清理后消失；该路径记录本轮实际环境，依赖不作为项目资产提交。
