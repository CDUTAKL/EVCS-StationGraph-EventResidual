# 创新性文献调研报告（2026-08-02）

5 个并行检索 agent（中英文各方向，合计 68 轮检索，覆盖 2018-2026 文献池）
验证本研究的四个创新点。检索范围为公开可及文献（arXiv/IEEE/Elsevier/MDPI/
知网/万方摘要级），不含付费全文精读；结论标注"基于公开可检索文献"。

## 一、总体结论

**独创性等级：中高（组合型/集成型创新，非原始创新）**

- 四个创新点的**每个组件**在文献池中均有先例（多关系图、自适应邻接、门控融合、
  残差修正、事件感知、会话重构均为 2023-2026 热门方向）；
- 但**完整组合**（站内桩级多关系门控图 + 事件门控残差 + 四层审计诊断）未见于
  任何检索文献——创新在于"集成方式 + 领域迁移 + 严谨性纪律"；
- 最强差异化空间：**站内 EVSE 级图建模场景**（文献池中 EV 图预测几乎全部是
  站间/区域级，节点=充电站；单站内 10 桩为图节点未见直接对应）。

## 二、逐创新点新颖性判定

| 创新点 | 判定 | 依据 | 表述策略 |
|--------|------|------|---------|
| A. 多关系门控图卷积 | **常见→差异化收敛** | 多图/多关系+门控融合是 2024-2026 热点（贠昕尧 2024 硕士论文、STGR-Net 2026、SPIES 2025、CADGN 2025、AMSTG 2025 等）；自适应邻接构造（Graph WaveNet 2019/电力系统自动化 2023）为直接先例 | 不主打"多关系图卷积"概念；收敛到"站内桩级 + 三类统计关系构造 + 关系级β/节点级G双级门控"的组合 |
| B. 事件门控残差修正 | **少见（最强方法创新点）** | 完整链路（4 分量行为事件分数 + 验证集冻结阈值 + 因果前向窗口扩展 + 门控激活有界残差 MLP + 事件加权损失）无先例；"因果前向窗口扩展"与"4 分量行为事件分数"针对性检索零结果 | 主动对照 PAR-LLM（2026）/lunar masked learning（2025），声明三维差异：行为信号事件分数 / 有界残差 MLP / 冻结+因果前向防泄漏 |
| C. 四层机制诊断协议 | **中高（L2 最高独特）** | 干预范式（Causal Head Gating NeurIPS 2025）在 NLP 成熟、负荷预测 GNN 零先例；"四格连续误差分解 + 加权和≡全局 MAE（≤1e-9）恒等式审计"无任何先例，填补 XAI 综述"仅 23% 验证解释鲁棒性"的空白 | 定位"可复现性评价协议"贡献；不声称发明干预，写"首次系统引入多关系 GNN 负荷预测"；引用 Hydra 效应说明三干预互补设计 |
| D. 会话重构+节点筛选 | **常见（成熟实践）** | PRAIM/EV-Insights/PARC 已有标准流程 | 不作核心创新主张；表述为"遵循并强化既有最佳实践 + 中文池无先例的严谨性披露" |

## 三、必须引用并差异化的风险文献（按优先级）

### 创新点 A 直接重叠（审稿风险最高）
1. 贠昕尧《基于多图融合的电动汽车充电站群负荷时空预测方法研究》（西安理工大学，2024 硕士论文）——多图融合+充电负荷，中文池最强先例。差异化：地理/交通关系 vs 统计相关关系；站群 vs 站内桩间
2. STGR-Net（Applied Energy 2026）——三流图（重力/相关/静态）+ 门控融合，机制最接近。差异化：站间 vs 站内
3. SPIES 2025 多图负荷预测——地理核+Pearson+气象余弦三图+门控融合，结构高度相似（非充电域）
4. CADGN（IEEE TSG 2025）——EV 多图+关键节点动态
5. AMSTG（IJEPES 2025）——静态+自适应双图融合
6. MGAT-MIC-LSTM（RSER 2024）——同 10 节点规模多图融合
7. AST-GCN（中国电机工程学报 2025）/ 张延宇动态自适应图（电力系统自动化 2023）——自适应邻接构造近邻

### 创新点 B 直接重叠
8. PAR-LLM（IEEE Access 2026）——"锚定基线+风险时段检测+选择性残差修正"骨架重合，最强竞争者。差异化：LLM 调整器 vs 有界 MLP；波动阈值 vs 行为事件分数；无冻结规则声明 vs 严格冻结
9. Lunar holiday event-aware masked learning（2025）——掩码激活修正分支先例。差异化：日历事件（预知）vs 行为信号（需检测）
10. ETFN（2026）——事件门控融合先例（特征权重，非残差路径）
11. 高洪超等《考虑事件数据的产消者负荷预测方法》（电力系统自动化 2023）——"事件数据"概念中文出处
12. ERKG（arXiv 2025）——事件加权损失先例
13. 专利 CN116702978B——充电突发事件特征修正先例

### 创新点 C 直接重叠
14. Causal Head Gating（NeurIPS 2025）——L1 干预范式源头
15. Guastavino et al.（2021/2023）——2×2 事件列联表价值加权分解先例（气象域）
16. Arabzadeh & Frank（MLKE 2025）——XAI 能量综述（"仅 23% 验证解释"数据背书）
17. EGCNH（2026）——分层解释框架最接近对标（观测式 vs 干预式）
18. Diebold-Mariano 检验及其 STLF 应用——L3 领域标准，需对照说明选择理由
19. Hydra 效应/门控模块性（Kerce 2026）——干预设计方法论警示
20. Jain & Wallace 2019 "Attention is not Explanation"——差异化论证起点

### 领域成熟度背书（可用于相关工作章）
- 2025-2026 两篇 SLR（Energies / J. Energy Storage）确认 STGNN 是充电预测主流范式、无站内桩级先例
- NIPS 2024 校准冻结阈值论文——"验证集冻结阈值"严谨性设计背书
- ETH Zurich 闭式解（TRC 2025）——"多车同时接入→负荷突变"因果链数学支撑

## 四、创新表述改写建议（论文写作依据）

1. **绪论创新点三条收敛表述**（替代当前表述）：
   - ① 站内桩级多关系门控图模型：以单站内充电桩为图节点，三类充电语义统计关系 + 自适应关系的双级门控融合（明确与站间图工作对位）
   - ② 事件门控残差修正机制：行为信号 4 分量事件分数 + 验证集冻结阈值 + 因果前向窗口的严格无泄漏设计（对照 PAR-LLM 三差异）
   - ③ 四层机制诊断协议：门控干预 + 四格恒等式审计（≤1e-9 还原）+ Bootstrap + 分层敏感度的可复现性评价体系
2. **相关工作章**：按上述 20 篇清单逐篇对位，每篇一句话差异化
3. **不得出现的表述**："首创多关系图卷积"（会被打脸）；"首创事件门控"（有骨架先例）；"首创会话重构"（成熟实践）
4. **可主张的表述**："首次将干预式机制诊断范式系统引入多关系 GNN 负荷预测"；"因果前向事件窗口扩展在充电负荷预测中未见先例"；"四格恒等式审计纪律未见先例"

## 五、检索元信息

- 5 个 agent × 13-15 轮检索，合计 68 轮，零结果检索 6 次（均集中在创新点 B 的事件窗口机制与 C 的四格诊断——零结果本身即新颖性证据）
- 文献粒度：标题/摘要/方法级（未精读全文）；正式撰写论文时建议对 20 篇核心文献下载全文逐条核对
- 局限性：中文学位论文全文不可公开获取（知网/万方授权库），检索基于公开索引；可能遗漏未上网的学位论文

## 六、文献来源链接（按检索方向分组，去重后保留）

> 各 agent 的完整来源 URL。同一文献在多个方向命中时保留在首次出现的分组。

### 6.1 中文文献池方向（agent ①）

| 文献 | 链接 |
|------|------|
| 贠昕尧：基于多图融合的电动汽车充电站群负荷时空预测方法研究（西安理工大学 2024 硕士） | https://s.wanfangdata.com.cn/paper?q=%E4%BD%9C%E8%80%85%3A%22%E8%B4%A0%E6%98%95%E5%B0%A7%22 |
| 同上（期刊版） | https://ir.xaut.edu.cn/xaut/SearchResult/Details/114331?doc=3 |
| 王进世：基于图注意力网络的电动汽车充电站负荷预测方法研究（西北师范大学 2025 硕士） | https://d.wanfangdata.com.cn/thesis/Ch1UaGVzaXNOZXdTb2xyOVMyMDI2MDUxMjA3Mjk0NxIJRDA0MTk5NTc3GghyYml6bm11Ng%3D%3D |
| 奚圣宽：基于深度学习的电动汽车充电桩负荷预测方法研究（华北电力大学 2023 硕士） | https://s.wanfangdata.com.cn/paper?q=%E4%BD%9C%E8%80%85%3A%22%E5%A5%9A%E5%9C%A3%E5%AE%BD%22 |
| 黄南天等：计及多公共充电站差异化耦合关联的电动汽车充电负荷时-空短期预测（中国电机工程学报 2025） | https://d.wanfangdata.com.cn/periodical/zgdjgcxb202504017 |
| 张延宇等：基于动态自适应图神经网络的电动汽车充电负荷预测（电力系统自动化 2023） | http://www.aeps-info.com/aeps/article/html/20230611001 |
| 高洪超等：考虑事件数据的产消者负荷预测方法及极端误差抑制策略（电力系统自动化 2023） | http://aeps-info.com/aeps/article/html/20220829001 |
| 温子健等：基于时间特征分类与误差修正的电动汽车充电负荷预测（浙江电力 2026） | http://zjdl.chinajournal.net.cn/WKE3/WebPublication/paperDigest.aspx?paperID=d268d424-8aa3-4aa9-96e0-e46cb3c693e6 |
| 孟衡等：MSTGCN+Transformer 多节点负荷预测（电网技术 2024） | 检索关键词：电网技术 2024 多尺度时空图卷积 Transformer |
| 毛俊晨等：动态混合图注意力网络（浙江电力 2026） | 检索关键词：浙江电力 动态混合图注意力 负荷预测 |
| 武继训：基于图数据库与改进图卷积网络的电动汽车可调度容量时空分布预测（合肥工业大学 2024 硕士） | 检索关键词：合肥工业大学 图卷积 可调度容量 2024 |
| 巫朝越：考虑特殊事件影响的单体用户短期负荷预测组合模型（东南大学 2024 硕士） | 检索关键词：东南大学 特殊事件 负荷预测 2024 |
| 基于可解释动态图注意力网络的短期电力负荷预测（计算机应用 2025） | http://dianda.cqvip.com/Qikan/Article/Detail?id=7201442426 |
| 基于时空图注意力网络的超短期区域负荷预测（电力系统自动化 2024） | https://opaj.napstic.cn/periodicalArticle/0120240700512417 |

### 6.2 英文 EV+GNN 方向（agent ②）

| 文献 | 链接 |
|------|------|
| MGAT-MIC-LSTM: Charging station cluster load prediction（RSER 2024） | https://www.sciencedirect.com/science/article/abs/pii/S1364032124005811 |
| CADGN: Causality-Aware Multi-Graph Convolutional Networks（IEEE TSG 2025） | https://xplorestaging.ieee.org/document/11007094 |
| AMSTG: Adaptive multivariate spatiotemporal graph fusion（IJEPES 2025） | https://www.sciencedirect.com/science/article/pii/S0142061525009354?via%3Dihub |
| ASTGRN: Adaptive spatio-temporal graph recurrent network（Applied Energy 2025） | https://www.sciencedirect.com/science/article/abs/pii/S0306261925000509 |
| DAS-GCN: Probabilistic Dual-Adaptive STGCN（Energy 2024） | https://www.sciencedirect.com/science/article/abs/pii/S0045790624009017?via%3Dihub |
| HyperCast: Multi-View Multi-Timescale Hypergraph（IEEE TSG 2025） | https://ar5iv.labs.arxiv.org/html/2511.22072 |
| ID-GCN: Integrated Dynamic Graph Convolutional Network（IEEE 2025） | https://xplorestaging.ieee.org/document/11022230/references#references |
| MSTEM: Multiscale Spatio-Temporal Enhanced STLF of EV Charging Stations（arXiv 2024） | https://ar5iv.labs.arxiv.org/html/2405.19053 |
| STFAG-GCN: Spatial-Temporal Fusion Adaptive Gated GCN（IEEE TNNLS 2025） | https://ieeexplore.ieee.org/abstract/document/10949659 |
| STGR-Net: GAT and GRU with trip distribution estimation（Applied Energy 2026） | https://ideas.repec.org/a/eee/appene/v406y2026ics0306261925019920.html |
| SPIES 2025 多图负荷预测（会议论文集） | http://www.icspies.org/SPIES%202025/SPIES%202025%20Proceedings.pdf |
| HSTF-GL: Hierarchical spatio-temporal fusion graph LSTM（Energy & AI 2026） | https://www.sciencedirect.com/science/article/abs/pii/S2213138826002468?via%3Dihub |
| PAR-LLM: Peak-Aware Residual LLM Over Anchor（IEEE Access 2026） | https://ieeexplore.ieee.org/abstract/document/11471298/figures#figures |
| PARC: Periodicity-Aware Residual Correction（World EV Journal 2026） | https://www.mdpi.com/2032-6653/17/7/336 |
| PGTNet/UCF 自适应事件门控残差连接（2024 thesis） | http://eprints.cs.univie.ac.at/8133/1/CAISE2024%20PGTNet%20A%20Process%20Graph%20Transformer%20Network%20for%20Remaining%20Time%20Prediction%20of%20Business%20Process%20Instances.pdf |
| GS-Fuse: Granger-Supervised Gated Fusion for Event-Driven Financial Forecasting（KDD 2026） | https://ar5iv.labs.arxiv.org/html/2605.28520 |
| SciML for Resilient EV-Grid Planning Under Extreme Events（arXiv 2026） | https://arxiv.org/html/2602.01261v1 |
| PRAIM: Unified Variational Imputation Framework for EV Charging Data（arXiv 2026） | https://ar5iv.labs.arxiv.org/html/2601.13476 |
| EV-Insights: open source framework for EV charging data processing（Energy Informatics 2025） | https://link-hkg.springer.com/article/10.1186/s42162-025-00615-4 |
| ML-Based EV Charging Demand Forecasting: SLR（Energies 2025） | https://dtic.dimensions.ai/details/publication/pub.1192771395 |
| EV Charging Forecasting SLR（J. Energy Storage 2026） | https://www.sciencedirect.com/science/article/abs/pii/S2352152X26031099 |
| EV-GNN（TU Delft 开源） | https://github.com/distributionnetworksTUDelft/EV-GNN |
| 多充电桩 IGRU（IEEE 2023） | https://ieeexplore.ieee.org/document/10364945/references#references |

### 6.3 多关系/异构图方向（agent ③）

| 文献 | 链接 |
|------|------|
| RLF-MGNN: Residential load forecasting using multiple correlation-temporal GNN（Applied Soft Computing 2023） | https://waseda.elsevierpure.com/en/publications/a-short-term-residential-load-forecasting-scheme-based-on-the-mul/ |
| ENRLF: Multiple correlation-temporal graph neural networks（EAAI 2025） | https://www.sciencedirect.com/science/article/abs/pii/S0952197625019359?via%3Dihub |
| Heterogeneous STGCN for EV charging demand（Transp. Res. Part C 2023） | https://www.sciencedirect.com/science/article/abs/pii/S0968090X23001948 |
| DTA-MHFN: Dynamic topology-aware multimodal hypergraph fusion（Scientific Reports 2026） | https://www.nature.com/articles/s41598-026-59612-6 |
| ST-DAD: Demand-based anomaly detection in EV charging（J. Energy Storage 2026） | https://www.sciencedirect.com/science/article/abs/pii/S2352152X2602459X |
| Multi-GCGRU: Multi-Graph Convolutional Network for Stock Movement（arXiv 2020） | https://ar5iv.labs.arxiv.org/html/2005.04955 |
| DynEC: Dynamic evolutionary clustering multi-view GNN（Frontiers in AI 2026） | 检索关键词：DynEC dynamic evolutionary clustering multi-view graph load profiling |
| EVformer: Spatio-Temporal Decoupled Transformer for Citywide EV（WEVJ 2026） | https://dtic.dimensions.ai/details/publication/pub.1197882738 |
| STGCN-Attention（MDPI Electronics 2025） | https://www.mdpi.com/2079-9292/14/20/4010 |
| Physical virtual multi-graph convolutional coordinated prediction（Frontiers in Energy Research 2024） | https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2024.1409647/full |

### 6.4 事件感知/事件门控方向（agent ④）

| 文献 | 链接 |
|------|------|
| PAR-LLM（同 6.2，最强竞争者） | https://ieeexplore.ieee.org/abstract/document/11471298 |
| Lunar holiday event-aware masked learning（2025） | https://dtic.dimensions.ai/details/publication/pub.1199798318 |
| ETFN: Event-aware Temporal Fusion Network 空调负荷（Discover Computing 2026） | https://link.springer.com/article/10.1007/s10791-026-10058-4 |
| ERKG: Event Response for Residential Load Forecasting（arXiv 2025） | https://ar5iv.labs.arxiv.org/html/2501.02781 |
| 专利 CN116702978B：考虑突发事件特征的充电负荷预测 | https://patentguru.com |
| NIPS 2024 校准冻结阈值论文（严谨性背书） | https://papers.nips.cc/paper_files/paper/2024/file/e9721921b799b6ea98d37f9e77f1a7fe-Paper-Conference.pdf |
| Hy-RAG-Forecast: LLM+RAG 事件感知负荷预测（NTU） | https://dr.ntu.edu.sg/entities/publication/b0eaa6e2-4603-47a8-ad79-15b96c13a191 |
| LLM-Driven Multi-Source Event Perception（IEEE 2026） | https://ieeexplore.ieee.org/document/11508993 |
| STIDGCN: Incident-Aware Dynamic Graph Convolution（ESWA 2025） | https://www.sciencedirect.com/science/article/abs/pii/S0957417425043040 |
| DE-GAM: 事故后高速公路速度预测（TRC 2026） | https://www.sciencedirect.com/science/article/abs/pii/S0968090X2600272X |
| Event-CausNet（arXiv 2025） | https://ar5iv.labs.arxiv.org/html/2511.12769 |
| ZINN: Zero-Inflated Neural Network（MDPI Energies 2026） | https://www.mdpi.com/1996-1073/19/9/2068 |
| Anomaly-Aware Q-Learning Framework（MDPI Electronics 2025） | https://www.mdpi.com/2079-9292/15/11/2494 |
| Gated Res2Net（arXiv 2020） | http://arxiv.org/abs/2009.11705 |
| LSTM-XGBoost residual learning（MDPI 2025） | https://www.mdpi.com/2673-4591/144/1/4 |
| Climate-informed AI early warning（Springer 2026） | https://link.springer.com/article/10.1186/s40807-025-00216-5 |
| Self-supervised EV charging event prediction（J. Energy Storage 2023） | https://www.sciencedirect.com/science/article/abs/pii/S2352152X23015864 |
| Federated early prediction EV charging demand（arXiv 2026） | https://ar5iv.labs.arxiv.org/html/2605.04993 |

### 6.5 可解释性/机制诊断方向（agent ⑤）

| 文献 | 链接 |
|------|------|
| Causal Head Gating: Interpreting Roles of Attention Heads（NeurIPS 2025） | https://proceedings.neurips.cc/paper_files/paper/2025/hash/a7f530e11fa19e9551b7a51dbd0f336f-Abstract-Conference.html |
| GNN for Electricity Load Forecasting（arXiv 2025） | https://ar5iv.labs.arxiv.org/html/2507.03690 |
| Four-Dimensional Analysis of XAI in Energy Forecasting（MLKE 2025） | https://www.mdpi.com/2504-4990/7/4/153 |
| Linking STLF and XAI: A review（Applied Energy 2026） | https://www.sciencedirect.com/science/article/pii/S0306261926003107 |
| From XAI to Knowledge Extraction（MLKE 2026） | https://www.semanticscholar.org/paper/From-Explainable-AI-to-Knowledge-Extraction-for-A-Iumanova-Matrenin/8205c2aedac066149bec27a6c7312573b5dc99b4 |
| Bad and good errors: value-weighted skill scores（Guastavino, arXiv 2021） | https://ar5iv.labs.arxiv.org/html/2103.02881 |
| Mini-batch sensitivity in deep residual networks for STLF（Scientific Reports 2026） | https://link.springer.com/article/10.1038/s41598-026-45002-5 |
| Learning-based probabilistic load forecasting（EPSR 2026） | https://www.sciencedirect.com/science/article/abs/pii/S0378779626011296 |
| Probabilistic forecasting with bootstrapped ANN（JETAI 2021） | https://eprints.lancs.ac.uk/id/eprint/139299/ |
| Traffexplainer（IEEE 2023-2024） | https://ieeexplore.ieee.org/document/11418310 |
| muxGNN: Multiplex Graph Neural Networks（IEEE TPAMI 2023） | https://dl.acm.org/doi/abs/10.1109/TPAMI.2023.3263079 |
| SHAP-guided physics-informed load forecasting（arXiv 2026） | https://ar5iv.labs.arxiv.org/html/2604.23500 |
| Interpretable STLF via multi-scale temporal decomposition（EPSR 2024） | https://www.sciencedirect.com/science/article/abs/pii/S0378779624006679 |
| EGCNH 极端自旋备用估计（Elsevier 2026） | https://www.sciencedirect.com/science/article/abs/pii/S2352467726001864 |
| KAN-Mamba: Interpretable Parallel Hybrid（IEEE 2026） | https://ieeexplore.ieee.org/document/11582119 |
| 可解释因果 GNN 用于配电需求预测（Energy and AI 2024） | 检索关键词：interpretable causal GNN distribution household electricity demand 2024 |
