# 2026-10-26 定稿与交付核验

## 文稿与证据包

- 正文源文件：`docs/thesis/thesis-manuscript.md`；内容分数使用的冻结 SHA-256 见同目录评分记录。
- 分析包：`outputs/analysis/SG-ANA-20261026-proxy-stability/`。`make_manifest.py --check`通过；50项输入按SHA-256和字节数核对，27项分析输出与冻结清单一致。原始输入不包含在仓库副本中。
- 来源保护：`source-provenance.lock.json`固定原始`source_path/source_archive/source_member`；迁移查找位置单列为`lookup_*`。普通重建在来源字段漂移、缺失或哈希不符时拒绝写入；显式修复要求冻结manifest哈希及全部输入清单一致。设计和边界见`provenance-regeneration-guard.md`。

## Word/PDF

- 校正版Word：`candidate-final-20261026-v5.docx`，SHA-256 `cf5783e81af5153d0ffb946f49a26f7168f6d3c7eee4da2935a25ca7e7c58327`。
- WPS导出PDF：111页，A4；目录页码核验117/117匹配，报告为`toc-verification-20261026-v5-1200ppi.json`。
- 最终图像PDF：`candidate-final-20261026-v5-1200ppi.pdf`，SHA-256 `b6d495fd6e3854ac5bd26b3540c584ca8e0d2fe9ffd6a134da5dda9af31a1bf8`。48幅嵌入图的有效分辨率为1201–1872 PPI，报告为`figure-resolution-20261026-v5.json`。
- PDF字体检查：9种字体均已嵌入。该项验证PDF可携带字体，不等同于WPS源文档的缺失字体提示已消失；本轮未能独立确认该提示状态，故仍列为待确认项。

## 全页视觉核验

上一版`v3-1200ppi.pdf`的111页记录中，97页与此前人工核对版本逐像素一致，13页经过人工复核，另有第8页按模板要求作为摘要与目录间的空白起始页。新PDF与v3逐页以120 DPI渲染比较后，只有第103页因结论措辞调整而变化；该页已人工检查，文字、行距、页边界及分页正常。其余110页与已验收版像素一致，因此继承既有逐页检查结果。差异记录见`visual-qa-20261026-v5-page-diff.json`。

## 交付边界

本次未改动或合并未知日期、分类号、密级及答辩信息；这些字段仍按作者指示留空。原创性声明和授权页仍需作者、导师线下签署。Word与高分辨率PDF在本机保留，未纳入Git：分别约112 MB和195 MB；仓库记录保存正文源文件、图件源文件、分析代码及轻量复核证据。
