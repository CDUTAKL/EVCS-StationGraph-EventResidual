# 图3-1 原论文风格修订（2026-09-09）

使用内置ImageGen，在当前结构图基础上参考用户论文截图的配色与错位布局。工具未提供版本选择参数，未确认或指定2.5。审阅版另存，不替换正式PNG、不修改DOCX。

## 生成提示词

最终输出：`fig3_1_thesis_style_20260909.png`，原生文件`exec-522b667a-4750-4060-8a4d-cce1339e7b01.png`。补正MLP输入及输出的短连接，未覆盖正式图片。

连接订正提示词：

Make one connector correction to this exact image. Between 第一层关系传播 and 残差MLP精炼 there is a tiny central downward arrow at x554,y612–625. REMOVE that tiny arrow completely, leaving white gap. The existing elbow line from firstlayer output on right runs down at x821 then left at y658 to the right edge of MLP at x703. KEEP this line and put a LEFT-POINTING ARROWHEAD at its endpoint x703,y658 entering MLP. This is the H1 input, no additional input needed. Preserve ALL other lines including MLP→H1ref→secondlayer. Change NOTHING ELSE: no font, no palette, no tensor, no geometry, no added elements.

Add exactly ONE missing downward arrow: from bottom center of the beige 残差MLP精炼 rectangle (around x554,y696) down to top center of H^(1,ref) tensor (around x554,y720). This is a short 24pixel connector. Do not erase or redraw anything else. Keep all current arrows, texts and palette unchanged. Only fill this white gap with a thin black line and down arrowhead.

原始生成提示词：

Use case: scientific-educational, editing a Chinese thesis architecture figure.
Image1 is the PRIMARY visual/layout reference (a screenshot from the user's own thesis). Image2 is current edit target with correct operation semantics but unattractive saturated styling.
Produce ONLY the isolated figure, no page text or caption, on a 3:4 portrait canvas, ideally1800x2400. Match image1's refined subtle blue-gray and warm parchment palette, restrained thin charcoal grid lines, softly colored tensor faces, readable Song/Times typography, polished academic illustration. NO electric blue/red outlines, NO bright orange, NO shiny shading. Three flat shades on3D faces, no drop shadows. Closely restore image1's balanced four-region staggered composition rather than image2's long centered tower.
Four section labels at left: ① 输入与时间编码; ② 两层关系传播; ③ 跨层融合; ④ 预测输出. Quiet lightgray separators.
Section1 (~upper27%): centered 输入X gridded tensor → 因果扩张TCN×6 with stacked feature slabs and d=1,2,4,8,16,32 → H⁽⁰⁾ tensor. Only ONE H0 here, no repeated H0 before layer1.
Section2 (~middle43%): first propagation wide box, three small beige labels entering from left 负荷关系/行为关系/轮廓关系. Internal modules β₁关系融合→G₁节点门控→残差+LayerNorm. This outputs rightward to H⁽¹⁾ tensor on right, like image1. A line from H1 goes DOWN then LEFT into a compact beige 残差MLP精炼 module under first layer. Text in it: H⁽¹,ref⁾=H⁽¹⁾+MLP(H⁽¹⁾). Use this complete abstract residual module to avoid spurious bypass lines. Its downward output connects to H⁽¹,ref⁾ tensor centered, whose bottom connects directly DOWN into top of 第二层关系传播. Second layer same internal modules β₂/G₂, three separate relationship inputs left, output rightward H⁽²⁾ tensor. No secondlayer→originalH1 connection.
Section3 (~next15%): three identical small tensors labelled H⁽⁰⁾ H⁽¹⁾ H⁽²⁾ from left to right, each independent short elbow arrow into a centered pale beige 跨层拼接 box [H⁽⁰⁾∥H⁽¹⁾∥H⁽²⁾]. They repeat state labels only; no long connector from upper region. RefinedH1ref must NOT enter concat.
Section4 bottom15%: compact module 融合映射 with Linear→LayerNorm→GELU→Dropout, then short down arrow to 预测头 Linear, then down arrow to warm pale gold output tensor with exactly FOUR front columns and corresponding four top-face divisions. Label Ŷ ∈ R^(B×4×10). Below column labels t+1,t+2,t+3,t+4. No output O axis. Fine grid, large readable text.
All hidden tensors same grid topology and proportional shape. Prioritize logical connectors and disciplined alignment. Preserve image1's quietly elegant dense tensor feel and evenly balanced whitespace. Omit long explanatory footnotes and any extra modules.
