# 独立技术/方法复评（同量表配对）

- 上下文 ID：blind-tech-20261026-dc6107e0-271b-48f4-afd4-6b7eb494a276
- 评阅日期：2026-10-26
- 量表/协议：EVCS-THESIS-CONTENT-1.0 / EVCS-THESIS-REVIEW-2.0
- 范围：仅限冻结 reviewer-packet 中的评阅说明、量表、锚点、两稿和 evidence 子目录；历史分数未暴露。
- 计分：原始 90 分制，按组件逐项给分并由代码求和；不换算百分制或学校等级。

## 总分

- 旧稿：**72.0/90**
- 当前稿：**73.5/90**
- 配对变化：**+1.5 分**

分项遵循相同锚点；未见修订而评价依据相同的项目维持相同分。新稿新增分析带来的变分分别指向结果证据、统计解释和经验贡献，不把同一事实扩张为普遍验证。

## 12 项配对复评

### BR-01 选题意义与问题定义

- 分数：旧稿 **4/5**；当前稿 **4/5**。
- 组件：旧稿：BR-01-problem 2/2；BR-01-significance 1.5/2；BR-01-need 0.5/1。当前稿：BR-01-problem 2/2；BR-01-significance 1.5/2；BR-01-need 0.5/1。
- 证据位置：baseline.md/current.md §§1.1, 1.3–1.4; Abstract; §§2.1–2.3；evidence/ACN_DECISION.md §§2, 5；evidence/DATA_AVAIL.md §§1–2。
- 理由：节点、15 min粒度、未来四片、站内关系问题和代理目标均具体，研究动机有公开数据、文献和稀疏性/异质性描述支持。尚未量化实际运维需求规模或对照业务基线；电表效度与使用条件仍待同步量测。
- 修订影响：无实质变化。新增排序结果不改变问题定义或实际需求证据。

### BR-02 研究问题、范围与题目一致性

- 分数：旧稿 **4.5/5**；当前稿 **4.5/5**。
- 组件：旧稿：BR-02-alignment 2/2；BR-02-progression 1.5/2；BR-02-closure 1/1。当前稿：BR-02-alignment 2/2；BR-02-progression 1.5/2；BR-02-closure 1/1。
- 证据位置：baseline.md/current.md title, Abstract, §§1.3–1.6, 3.8, 4.5, 5.4, 结论；current.md §3.8.5 and Appendix A-2。
- 理由：题目、问题、方法和结论围绕站内代理节点负荷、关系增量与机制诊断闭合；摘要和结论明确限定代理目标与应用边界。章节5的方向性、区间和运行接口是较宽的补充线，部分削弱主线紧凑度，但各自均有边界说明。
- 修订影响：无评分变化。当前稿新增§3.8.5，并在§1.4、§1.5和结论回收其排序敏感性结论，整体仍与主问题相连。

### BR-03 文献综述与缺口定位

- 分数：旧稿 **3.5/5**；当前稿 **3.5/5**。
- 组件：旧稿：BR-03-coverage 1/1；BR-03-sources 1.5/2；BR-03-gap 1/2。当前稿：BR-03-coverage 1/1；BR-03-sources 1.5/2；BR-03-gap 1/2。
- 证据位置：baseline.md/current.md §§1.2.1–1.2.4, Table 1-1, §1.3；evidence/NEAR.md；evidence/NEAR2.md；evidence/NEAR_20261016.md；evidence/NEAR76.md。
- 理由：覆盖EV站间图、住宅用户图门控、时序预测及事件/解释方法，且按节点粒度、输入和验证范围区别近邻。短板是[76]已是公开EV会话重构代理负荷预测与残差校正的直接近邻，稿件虽引用并收窄泛化主张，仍未正面比较其Boulder重构、持续性锚、直接/残差对照和指标依赖；部分文献证据限于摘要或页面可读片段。该缺口在两稿中相同。
- 修订影响：无变化。[76]缺少直接比较在baseline与current均存在；本次未把已知缺口只归于当前稿。

### BR-04 理论基础与专业知识

- 分数：旧稿 **4.5/5**；当前稿 **4.5/5**。
- 组件：旧稿：BR-04-concepts 2/2；BR-04-formulas 1.5/2；BR-04-knowledge 1/1。当前稿：BR-04-concepts 2/2；BR-04-formulas 1.5/2；BR-04-knowledge 1/1。
- 证据位置：baseline.md/current.md §§2.1–2.5, 3.2–3.5, 4.2–4.4, 5.2–5.4；evidence/S32.md 冻结的目标规则；evidence/EPFL22.md 解释边界。
- 理由：代理能量的单位与实测功率区别、发布时间/目标片起点、图关系语义、消息传播和门控计算均有公式或文字定义；方法知识用于解释具体节点预测问题，且把β、规则和事件分层限制为非因果判断。少量实现级重构细则主要留在证据材料，正文对核心替代目标条件可再形式化，因此公式/假设组件扣0.5；这不是把已声明的代理假设当作理论错误。
- 修订影响：无实质变化。新增Spearman分析不改变理论定义或建模假设。

### BR-05 方法与实验设计

- 分数：旧稿 **8/10**；当前稿 **8/10**。
- 组件：旧稿：BR-05-information_split 2.5/3；BR-05-comparators 1.5/2；BR-05-controls 2.5/3；BR-05-selection_budget 1.5/2。当前稿：BR-05-information_split 2.5/3；BR-05-comparators 1.5/2；BR-05-controls 2.5/3；BR-05-selection_budget 1.5/2。
- 证据位置：baseline.md/current.md §§2.1.1–2.1.3, 3.6–3.8.4, Table 3-14；evidence/S31.md §§1–5；evidence/S32.md 训练前审计 and 结果解释规则；evidence/PROVENANCE_GUARD.md。
- 理由：行为输入、分段留窗、标签成熟、共同预测键、近似容量TCN、同参数门控和自环替换提供了多个适配问题的控制；训练种子、选模规则、轮次和预算被列明。限制包括完整AGCRN远大于MRG-GCN、共享门控在两个协议各有种子触顶、旧回溯预处理有全时期统计、多个补充分析复用已查看测试期。不同对照被分开解释，故未按同一问题重复扣分。
- 修订影响：无评分变化。新增标签排序分析只重评既有预测/标签，没有改变样本、输入、训练或测试协议；它加强敏感性描述，但不构成新的设计控制。

### BR-06 可复现性与方法严谨性

- 分数：旧稿 **4/5**；当前稿 **4/5**。
- 组件：旧稿：BR-06-data_split 1/1；BR-06-source_config 1/1.5；BR-06-keys_metrics 1.5/1.5；BR-06-environment_package 0.5/1。当前稿：BR-06-data_split 1/1；BR-06-source_config 1/1.5；BR-06-keys_metrics 1.5/1.5；BR-06-environment_package 0.5/1。
- 证据位置：baseline.md/current.md §§2.1–2.2, 3.6.1, 3.8.3, 4.6.1；evidence/REPLAY22.md §§1–3；evidence/ADAPT.md §§1–4；evidence/RECOMP.json；evidence/MRECOMP.json；evidence/S31AUDIT.json；evidence/S32AUDIT.json。
- 理由：数据时间段、节点、切分、预测键、配置和主要指标有对应记录；多个审计报告说明保存预测的独立算术复核通过，AdaptiveGraph匹配CUDA前向逐键复核通过。扣分来自031入口未纳入Git、032缺可核实历史提交号、早期训练Git身份/硬件信息缺失、结果归档为较大本地sidecar；这些限制意味着材料齐备性尚不等于便携的第三方从头训练复现。
- 修订影响：无实质变化。新结果附有PROXY_RESULTS/PROXY_TABLE和复算摘要，但归档/外部脚本不在冻结评阅包中，本评阅未独立重跑计算。

### BR-07 工作量与解决问题能力

- 分数：旧稿 **9/10**；当前稿 **9/10**。
- 组件：旧稿：BR-07-technical_work 3.5/4；BR-07-problem_solving 3.5/4；BR-07-integration 2/2。当前稿：BR-07-technical_work 3.5/4；BR-07-problem_solving 3.5/4；BR-07-integration 2/2。
- 证据位置：baseline.md/current.md Chapters 2–5 and conclusion；evidence/QUALITY.md；evidence/ADAPT.md；evidence/S31.md；evidence/S32.md；evidence/MDP.md；evidence/CAL.md；evidence/EPFL22.md。
- 理由：完成了数据协议与质量门禁、三关系构造和模型实现、两场站训练、配对对照、时间块分析、冻结参数干预、蒸馏、四格误差还原、区间校准、方向性筛查和运行接口算例，并能根据反例收窄主张。少量探索章节与核心贡献的关联较间接，且不能把审计数量直接等同于独立科学证据；仍体现有难度的工程研究和问题处理。未因缺外部新数据或现场部署扣分。
- 修订影响：新增排序敏感性和应用边界汇总提升了整合度，但主要复用已有预测与测量材料，整体工作量增幅不足以改变此项分数。

### BR-08 结果与证据充分性

- 分数：旧稿 **8/10**；当前稿 **8.5/10**。
- 组件：旧稿：BR-08-claim_support 3.5/4；BR-08-alternatives 2.5/3；BR-08-robustness_scope 2/3。当前稿：BR-08-claim_support 3.5/4；BR-08-alternatives 2.5/3；BR-08-robustness_scope 2.5/3。
- 证据位置：baseline.md/current.md §§3.6–3.8.4, 4.4, 5.3；current.md §3.8.5, Table 3-16, Fig. 3-17, Appendix A-2；evidence/PROXY_REPORT.md §§2–7；evidence/PROXY_RESULTS.json；evidence/PROXY_TABLE.csv；evidence/S31AUDIT.json；evidence/S32AUDIT.json。
- 理由：核心MAE和组件差异有直接共同键证据，主要替代解释通过基线、同参数门控和关系自环重训部分覆盖；代理目标、独立确认时段和量测效度仍是明确缺口。current新增同一预测在两种标签下的12配置全局与分层排序，补强了模型选择对代理标签定义的敏感性证据，但这是已查看测试键上的事后评价，不是独立确认。
- 修订影响：+0.5：current新增排名相关与子集敏感结果（全局ρ=0.993，评价标签非零ρ=0.420）及完整配置排名，直接补充“代理标签定义是否改变模型选择”这一证据问题；范围限定避免把此增量误作实测稳健性。

### BR-09 统计解释与结论边界

- 分数：旧稿 **8/10**；当前稿 **8.5/10**。
- 组件：旧稿：BR-09-uncertainty 3/4；BR-09-multiplicity 1.5/2；BR-09-interpretation 3.5/4。当前稿：BR-09-uncertainty 3.5/4；BR-09-multiplicity 1.5/2；BR-09-interpretation 3.5/4。
- 证据位置：baseline.md/current.md §§3.6–3.8.4, 4.4, 4.6, 5.3, conclusion；current.md §3.8.5, Table 3-16 and figure note；evidence/PROXY_REPORT.md §§3–4, 9–10；evidence/PROXY_TABLE.csv；evidence/S31AUDIT.json interpretation_limits。
- 理由：种子标准差、配对时间块区间、多重校正和固定测试期边界均有说明，负结果也纳入结论。仍只有三个训练种子，很多区间条件于固定测试期，补充探索复用测试期且预测键重叠。current明确区分“先平均种子MAE再排名”的ρ与逐种子ρ，并说明范围不是置信区间、无阈值且测试期已查看；该清晰区分是统计解释上的具体增量，不把相关当作总体推断。
- 修订影响：+0.5：新增稿分别报告聚合排名相关和逐种子相关的定义/数值，并把逐种子极差明确称为范围而非区间；仍未为相关估计不确定性，故只加半分。

### BR-10 贡献与创新

- 分数：旧稿 **7.5/10**；当前稿 **8/10**。
- 组件：旧稿：BR-10-prior_difference 2.5/3；BR-10-contribution 2.5/3；BR-10-demonstration 2.5/4。当前稿：BR-10-prior_difference 2.5/3；BR-10-contribution 2.5/3；BR-10-demonstration 3/4。
- 证据位置：baseline.md/current.md §§1.2.2–1.4, 3.8.1, 4.5, conclusion；current.md §3.8.5, §3.9, Appendix A-2；evidence/NEAR76.md §§2–3；evidence/PROXY_REPORT.md §§3–8。
- 理由：贡献被收束为单场站代理负荷任务中的关系/门控受控证据及MDP对研究判断的修正，而不是图卷积/门控算法首创；该增量可信且任务具体。当前仍是同一数据体系和单一已查看时间段，无法证成广泛新能力。current新增排序敏感知识，使“总体MAE排序保持但活跃片段排序敏感”成为可检验的经验发现，扩展了评估贡献。
- 修订影响：+0.5：A-2与§3.8.5为不同标签下的总体/非零/事件排序提供直接数据，使标签敏感性成为明确的经验增量；贡献性质仍属限定的评价知识，不是新算法或泛化能力。

### BR-11 专业实践价值

- 分数：旧稿 **3/5**；当前稿 **3/5**。
- 组件：旧稿：BR-11-use_case 1/1；BR-11-real_inputs 1/1.5；BR-11-value_evaluation 0.5/1.5；BR-11-usable_outputs 0.5/1。当前稿：BR-11-use_case 1/1；BR-11-real_inputs 1/1.5；BR-11-value_evaluation 0.5/1.5；BR-11-usable_outputs 0.5/1。
- 证据位置：baseline.md/current.md §§1.1, 2.1.2, 5.4.1–5.4.5 and conclusion；evidence/CURRENT_SHAPE_PROTOCOL.md §§1–4；evidence/FIG59.png；evidence/EPFL22.md §§3–5；evidence/DATASEARCH22.md 定向核查与停止条件。
- 理由：容量/均衡、告警和调度接口条件明确，实际会话记录及8条历史归一化电流形态提供有限真实输入参照，合成LP验证约束可行性。仍无同步ACN电表功率/能量、请求到达时刻及实际业务收益；电流样本无电压/功率、训练年代且仅便利抽样。实践结论合理限于模型筛选与采数安排。
- 修订影响：无分数变化。current将真实证据缺口、字段可见性未知和测量回放先于影子调度的步骤写得更清楚，但同站实测样本和评价结果在baseline §2.1.2已存在，未增加现场价值验证。

### BR-12 结构、表达与学术规范

- 分数：旧稿 **8/10**；当前稿 **8/10**。
- 组件：旧稿：BR-12-structure 2.5/3；BR-12-writing 2/3；BR-12-scholarly_content 2.5/3；BR-12-terminology 1/1。当前稿：BR-12-structure 2.5/3；BR-12-writing 2/3；BR-12-scholarly_content 2.5/3；BR-12-terminology 1/1。
- 证据位置：baseline.md/current.md full text; contents, figures, tables, references and appendix；evidence/LANGUAGE_REVIEW.md §§2–3；evidence/LANGUAGE_AUDIT.json checks；evidence/FIG317.png and FIG59.png (only images visually inspected)。
- 理由：五章结构、表格、公式、章节导航和术语定义较完整；语言修订记录核对数字、引用序列、公式及图表链接。篇幅长，限制条件和若干判断在摘要、章节小结、综合表与结论重复，表达可进一步压缩；仅有少数图像在本次隔离评阅中可视核对，故不能据此认定所有图件均已正确。
- 修订影响：无评分变化。current新增表/图和交叉引用整体嵌入结构，差异输出未见明显引用错位；稿件整体重复和长度未显著改善.

## 评阅边界与未检查内容

历史评分、scorecard 和其他评阅意见未读取，历史分数未暴露。本报告不据历史分数校准分项。

未检查项目其余文件、README、publication-status、正式 DOCX/PDF、论文链接到 reviewer-packet 外的图像、原始会话时序、权重/检查点、完整训练日志、包外源码及外部数据。仅视觉查看 evidence/FIG317.png 与 evidence/FIG59.png；其余论文图像未逐幅检查。未逐运行或逐键核对 evidence JSON/CSV 的所有原始数组，也未自行重训或从头重跑预测；复现性判断以包内审计摘要、哈希记录和复算说明为限。近邻文献只按 evidence 中记录的可读范围评价。

两稿逐段差异来自冻结包中的 baseline.md 与 current.md。当前稿主要新增代理标签定义下的12配置排序敏感性、门控方向变化说明，以及应用证据边界/验证条件补充；这些变化没有构成未查看时间期、实测功率或现场收益验证。
