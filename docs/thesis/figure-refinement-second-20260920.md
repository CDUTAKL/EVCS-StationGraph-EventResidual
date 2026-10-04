# 第二轮指定图精修（2026-09-20）

- fig5_5：压缩图例和面板标题，移除底部长注与重复计数；详细口径保留正文图注。
- fig3_10：从既有18份正式metrics重算六模型四步均值与样本标准差；蓝色实线/实心方块突出MRG-GCN，其他模型使用空心标记及不同线型；15–60 min横轴。来源表为outputs/figures/fig3_10_revision_sources.json。
- fig5_6：按用户要求使用内置ImageGen，上下校准/预测流程；两条分位数输出接半宽选择，点预测独立进入最终区间。最后一轮专门修正q_trig连线，未采用前两轮候选。

视觉检查：文字未越界，模块未跨区，数据图坐标与统计口径明确。原生PNG不宣称SVG；未生成Word。

## ImageGen首轮提示词

Redesign the provided Chinese thesis conformal method diagram completely. Scientific academic figure, landscape 16:9, white background, very pale blue-gray flat fills, thin muted slate blue lines, black Chinese Song serif large legible typography and Times math. NO circles everywhere, no bubbles, gradients, shadows, icons, oversized cards, scattered footnotes. Elegant aligned compact rectangular modules, two clearly separated panels with subtle pale blue background and fine boundary, short panel headers 验证期校准 (left 55%) and 测试期预测 (right 45%). Correct scientific topology essential. LEFT: 验证集 → 冻结模型 → 残差 |y−ŷ|. Residual arrow leads to 按冻结规则分层, then splits to two aligned small boxes: 触发样本 → 合并节点 → q_trig; 未触发样本 → 逐节点校准 → q_stable,n. Put a single short α=0.1 near calibration branch labels; these are empirical 90% quantiles, not coverage guarantee. The splitting uses rule_trigger, NOT target_event. RIGHT: 测试输入 splits into two parallel paths: 冻结模型 → 点预测 ŷ ; 可见规则 → 选择半宽 q. Two separate thin orthogonal arrows from calibrated q_trig and q_stable,n in left panel must feed 选择半宽 q in right panel. Rule path selects q based on trigger (1 selects q_trig, 0 selects q_stable,n). CRITICAL ŷ does NOT feed selector; ŷ and chosen q converge only at final 预测区间 [ŷ−q, ŷ+q] at bottom right. All arrows terminate on modules, no line crossings, no dangling elements. Labels just specified, use proper mathematical subscripts instead of printed underscores. Remove target_event footer entirely. No diagram title/number. Ample balanced padding, aligned rows, main text large, concise, restrained engineering thesis style. Preserve method data not original bubble layout.

## 后续定向修订

将左右布局改为上下两条流程，去掉大标题条和多余参数标注；最终删除90%分位数框与其连接，改为纯文字，将q_trig右侧经独立通道连接选择器。q_stable,n保持另一条输入连接，点预测仅进入预测区间。

## fig5_6 从零重绘（李芳凝论文视觉语言参考）

参考文件：`/Users/xushuyuan/Downloads/基于深度学习组合模型的电动汽车换电站负荷预测研究_李芳凝.pdf`。仅参考其中图3-1、图3-3与图4-3的版式语言，不复用其研究内容：浅蓝过程框、淡黄判断菱形、淡粉起止节点、细正交箭头和浅蓝虚线阶段分区。

最终设计：16:9左右双栏。左栏以`rule_trigger=1?`将验证残差分为触发与未触发两路，分别形成`q_trig`与`q_stable,n`并冻结入半宽库；右栏测试输入分别生成点预测与可见规则，规则选择冻结半宽，点预测与半宽仅在最终预测区间汇合。蓝色虚线专门表示半宽库到测试路由的数据依赖，黑色实线表示流程与选择关系。

最终ImageGen提示词要点：白底、浅蓝矩形、淡黄菱形、淡粉圆角节点、无阴影渐变和图标；中文宋体风格、数学变量Times New Roman；不出现`target_event`、`alpha=0.1`或测试覆盖保证；箭头不得交叉或悬空。最终候选为`exec-2e094452-9405-4e93-9d3c-2082b35ac10b.png`，正式文件为`outputs/figures/fig5_6_conformal_method.png`。
