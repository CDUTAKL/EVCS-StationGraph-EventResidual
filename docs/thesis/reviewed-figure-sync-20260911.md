# 审定重绘图漏同步修复

## 原因

9月6日会话目录的6幅ImageGen重绘图没有进入正式图片目录；9月9日的图3-1、3-2、3-3风格重绘仍被说明文件标为“未覆盖正式图片”。正文生成器读取正式目录PNG，而不是会话链接。此前仅验证正式文件与旧manifest一致，没有验证其是否是会话审定版本，故漏同步未被发现。

## 选定版本

| 图号 | 审定源版本 |
|---|---|
| 1-2 | roadmap_v2，修正双贡献连接 |
| 2-1 | data_reconstruction，9月6日ImageGen |
| 3-1 | thesis_style_20260909 |
| 3-2 | thesis_style_20260909 |
| 3-3 | thesis_style_20260909 |
| 3-6 | gate_residual_detail_v3，16:9 |
| 3-7 | cross_layer_detail_v5，修正顶面分格及四步输出 |
| 3-8 | train_predict_pipeline，9月6日ImageGen |
| 4-1 | three_layer_framework，9月6日ImageGen |

逐图原路径、替换前后SHA256见同名JSON。原PNG及5幅旧SVG保存在`outputs/figures/archive-before-reviewed-sync-20260911/`，可恢复；没有把PNG伪装成SVG。现为29幅SVG+PNG、14幅PNG，共43幅。正文只改5处图片扩展名，正文内容、实验结果与主线不变。

## 防回退

生成DOCX时对已审定的12幅ImageGen图片校验注册SHA256，不符即停止；`scripts/audit_docx_figure_sync.py`检查实际DOCX图片顺序及每幅哈希是否与正文对应的43幅PNG一致。更新manifest不能替代此项检查。
