# Word/WPS 最终交付快照验收

日期：2026-10-20（Asia/Shanghai）  
复核者：Codex  
状态：**当前交付快照的版面验收通过；真实签署和未知行政字段仍待责任人处理。**

## 冻结对象

- 正式 DOCX：`outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx`
- DOCX SHA-256：`54749d10bc365dd60862cb9fef030baec9a07530f5a791e47f6a224e84502f9b`
- WPS 原始导出 PDF：`docs/thesis/revision-20261019-nontraining/formal-thesis-final-wps-20261019.pdf`
- 图像流恢复后的 PDF：`outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.pdf`
- 最终 PDF SHA-256：`06784964b1f3db68049d10d7f931d3f17d12d4f9c2ec9ce649f9507ffb09b9b1`
- 正文 Markdown SHA-256：`451642e15e0fc51343acabf84e727b5079d8a1f2243c0ab8d8542adeed8b9b42`

DOCX 与此前接受的候选稿按字节一致。最终 PDF 保留 WPS 的页面布局，并以 DOCX 中匹配的 46 张原图替换 WPS 导出的低分辨率图像流；共 104 页，页面布局未变。原始导出 PDF SHA-256 为 `ebcf2abe5148d1e21d51e26125fc19f4c9c577b3401c03856b96804aead48a55`，恢复报告为 `formal-thesis-final-wps-20261019-hires-restoration.json`。

## 交付核验

| 项目 | 结论 | 证据 |
|---|---|---|
| 页数与纸张 | 通过：104 页，A4 | `pdfinfo` |
| 目录页码 | 通过：目录在 PDF 第 7–10 页；116 项全部与正文首次出现页匹配，0 项不一致 | `toc-page-verification-hires-reexport-20261020.json` |
| 空白页 | 通过：自动检查无空白页候选；第 3 页为原创性声明、第 4 页为版权授权，均为模板内容页 | `visual-qa-final-20261019-hires/visual-qa.json` |
| 全页视觉 | 通过：第 1–104 页逐页覆盖，26 张四页接触表全部查看；未见明显裁切、版心溢出、拉伸、图文重叠或压缩模糊 | `visual-qa-final-20261019-hires/manual-review.json`、`visual-qa.json` |
| 图像分辨率 | 通过：46 张图的有效分辨率最低 1201.0 PPI、最高 1872.0 PPI，达到至少 1200 DPI 的要求 | `formal-thesis-final-wps-20261019-hires-restoration.json`、`verify-hires-final.json` |
| PDF 字体 | 通过：PDF 使用的 9 种字体均嵌入 | `pdffonts` 输出 |
| 正式文本 | 通过：内封面学号经 PDF 文本提取核对为 `2024050524` | PDF 第 2 页文本提取；作者已确认 |

## 封面、声明与签署

学号按作者确认填写为 `2024050524`。分类号、UDC、密级、送审/答辩/授位日期、答辩委员会主席等字段按作者指示暂留空，不以推断内容补填。原创性声明及版权授权页中的作者、导师签名和日期留出位置，由责任人线下真实签署；本次未代签或生成仿真签名。

## 字体警告

WPS 打开源 DOCX 时仍可能提示本机缺少模板字体。最终 PDF 中实际使用的 9 种字体均嵌入，PDF 可独立显示。本次未以近似字体替换模板字体，以免改变学校格式或分页。若后续需要在该设备编辑 DOCX，应在学校认可的字体环境安装/启用指定字体，并复核排版。

## 验收边界

本验收仅对应上述 DOCX、正文稿和 PDF 哈希。后续如修订正文语言、封面、目录、图件、字体或分页，必须重新生成 PDF、更新目录核验，并对新 PDF 重新完成全页视觉验收。作者/导师签署和未知行政字段仍待责任人；这不影响当前快照的版面检查结论。
