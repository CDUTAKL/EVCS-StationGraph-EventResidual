# 2026-10-20 论文交付与盲审证据核验

## 交付快照

本报告核验的是语言修订候选稿，不将尚未完成 Codex 复核的内容标作最终送审定稿。

| 文件 | SHA-256 | 状态 |
|---|---|---|
| 正文稿 `docs/thesis/thesis-manuscript.md` | `17d17c73bc066d22e4da67f0ed5d7ef5fa4069ca197944082373b45c909a0045` | Claude 修订稿；执行报告未完成，待 Codex 复核 |
| Word 候选稿 `thesis-candidate.docx` | `634498a75a0cc76e318c240a7474415bd63be222798ee976b7034d83df95af66` | 结构审计通过 |
| WPS 原始导出 `wps-final/thesis-candidate.pdf` | `465e9097dae29f710e8bdf70e79ad5f7b6013e44f78d3d14bb15d084fbf3d8b0` | WPS 导出，104页 |
| 图像恢复后的候选 PDF `wps-final/thesis-final-wps-1200ppi.pdf` | `8bb0d54877618d264db9197a07e429fae6919406bd21fd6dfc8f8ac12c611764` | 版面与 WPS 导出一致；全页验收通过 |

## Word/PDF 核验

- **页数与纸张：**104页，A4。
- **目录：**目录位于PDF第7–10页；116项均与正文首次出现页匹配，0项不一致。目录在WPS中刷新并保存进DOCX。
- **空白页：**自动筛查无空白页候选；第3、4页是原创性声明与版权授权页。
- **全页视觉：**第1–104页全部覆盖。26张四页接触表逐页查看；最终PDF与用于目视的前一导出版本在104页的120 DPI页面像素哈希上逐页完全一致。未见明显裁切、拉伸、重叠或压缩模糊。PDF第69、79、104页另作放大检查。
- **图像：**46幅图与DOCX中的原始PNG逐一匹配；图像恢复后最低有效分辨率1201.0 DPI、最高1872.0 DPI。
- **公式与DOCX结构：**27个带编号公式均为原生公式且顺序正确；DOCX压缩包完整，结构审计通过。
- **字体：**PDF使用的9种字体全部嵌入。WPS编辑器仍显示“缺失字体”状态提示，具体缺失字体名称未能从界面读取；该提示未导致本次PDF出现可见缺字，但在当前Mac继续编辑DOCX时仍需留意字体替代。
- **封面与签署：**内封面学号已核对为2024050524。分类号、UDC、密级、日期、答辩主席等未提供字段按作者指示留空；原创性声明与授权页的签名和日期留待线下真实填写。

机器审计记录：
- `docx-candidate-audit.json`
- `wps-final/figure-resolution-final.json`
- `wps-final/toc-verification-final.json`
- `wps-final/visual-qa-final/visual-qa.json`
- `wps-final/visual-qa-final/manual-review.json`

## 盲审与评分记录

现有正式同量表配对评分为 **76.5/90 = 85.00/100**（非学校官方成绩），配对基线为75.5/90；主评仅在BR-09、BR-12各加0.5分。评分记录、三份独立视角报告及算术审计均能读取，`scorecard-audit.json` 状态为valid。

该正式分数绑定的正文SHA-256是 `3d883156d9264c9f94c3f7150d7a7647773e1c546d4689b1b283a8eb0b0ed9f3`，不是本报告所列 `17d17c...`。因此85.00分只适用于旧冻结稿；当前Claude修订稿尚未完成独立复核，不能沿用该分，也不据语言修改预先加分。Claude任务编号为 `REV-20261020-LANGUAGE-005`，仪表盘显示本机PID仍存在，但状态遥测已过期，执行报告尚未填写；任务未回收、未验收。

## 结论

当前DOCX/PDF候选快照的版式、目录、页码和图像分辨率核验通过。它可以作为**候选交付快照**供复核；最终送审文件和对新正文的评分，须待Claude交接报告与Codex内容复核完成后冻结。任何后续正文、目录、图件或格式改动都要更新哈希，并重新导出和验收对应PDF。


## 2026-10-20 语言恢复后的版本更新

LANGUAGE-005已中断并保留回收异常记录；LANGUAGE-006完成无工具Claude建议、Codex复检和干净回收。当前正文SHA-256为`7ddffbb0657af8c26d222408b8466aaacb3510e95a2eec782e7eeb46a2d74bc1`，新Word候选与详细核对见`language-recovery/delivery-followup.md`。本报告前述104页PDF及页码/图像验收只对应原文件，不覆盖新稿。旧结构审计所列source哈希不足以单独证明全文同步；新候选已增加文字与表格逐项核对。
