# 文献[72]/[73]补充核查

日期2026-10-15。当前论文保持原书目编号，在§1.2.2新增明确引用及方法比较。以下事实只来自作者/出版机构公开摘要，未获得两文完整可解析论文，不补写未知预算、门控粒度或输入时点。

| 条目 | 来源与可读层级 | 已核实事实 | 仍未知 |
|---|---|---|---|
| [72] Wang等，Applied Soft Computing 146 (2023), 110629 | [出版社文章/摘要](https://www.sciencedirect.com/science/article/pii/S1568494623006476)搜索可读；[作者所属早稻田大学机构库摘要](https://waseda.elsevierpure.com/en/publications/a-short-term-residential-load-forecasting-scheme-based-on-the-mul/)可读 | 住宅节点；Pearson同步图和TE方向信息图；各GCN提取多关系表示，再接LSTM | 原文完整切分、预算、时点权限及参数共享未核实 |
| [73] Zhang等，IEEE TNNLS 36(9) (2025), 17004–17018 | DOI 10.1109/TNNLS.2025.3551778；[作者机构成果记录](https://faculty.cumt.edu.cn/JWH/zh_CN/lwcg/202985/content/158873.htm)；[作者本人在XJTLU的会议摘要](https://www.xjtlu.edu.cn/wp-content/uploads/2025/04/2025-Symposium-Abstract-Brochure.pdf)，题为Spatial-temporal fusion adaptive gated graph convolution networks for short-term residential load forecasting；期刊原始摘要另在[PubMed记录](https://pubmed.ncbi.nlm.nih.gov/40184286/)索引 | 住宅负荷；时空融合图构建、自适应门控融合、门控TCN与多层STFGCN组合 | 全文实验和节点门控细节未核实；不推断与本文同参数控制相同 |

比较用途：[72]限制“多种统计关系+时序图预测”的一般首创，[73]限制“门控图卷积+TCN”的一般首创。本文差异落在单场站会话代理任务、两类邻接/节点门控的受控增量与证据分层，未声称算子创新；不作跨论文性能排序。作者机构成果页的第一作者字段与期刊书目顺序不同，书目沿用期刊摘要/DOI记录的Zhang、Jiao、Yu、Xiong顺序，不用机构网页覆盖作者顺序。
