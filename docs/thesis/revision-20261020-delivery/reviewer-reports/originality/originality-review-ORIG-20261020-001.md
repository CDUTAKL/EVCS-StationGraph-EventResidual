# 原创性与科学贡献隔离评阅

评阅上下文：ORIGINALITY-REVIEW-20261020-001

## 范围与方法

按冻结量表 EVCS-THESIS-CONTENT-1.0 对 baseline/current 成对评分；固定12项，满分90，0.5分步长，先按组件评分再求和。本评阅为专业硕士论文内容模拟评审，不预测学校等级。

历史分数暴露：false / not_provided。原因仅为隔离上下文提供的冻结材料包不含历史评分卡或评分历史；未检索相关历史。

资料边界：manifest说明图像内容及整页视觉验收未检查，仅阅读图注和正文引用，不能视为插图通过。本文不报告数值置信区间。

## 成对总分

- baseline：72.0/90（按量表公式换算80.00/100）。
- current：72.5/90（按量表公式换算80.56/100）。

current仅在BR-12提高0.5分，反映局部句式和对象名称更清楚；其余11项不变，因为核心问题、证据、结果和贡献边界基本未变。当前稿没有新增独立确认性研究结果。

## 12项逐项评分

### BR-01 选题意义与问题定义 — baseline 4.5/5.0；current 4.5/5.0

组件分（baseline/current）：BR-01-problem: 2.0/2.0（满分2.0）；BR-01-significance: 1.5/1.5（满分2.0）；BR-01-need: 1.0/1.0（满分1.0）。

稿件定位：
- manuscripts/baseline.md:35-57，§1.1 背景与研究问题
- manuscripts/current.md:35-57，§1.1 背景与研究问题
- manuscripts/baseline.md:110-137，§1.3–1.4 研究缺口与目标
- manuscripts/current.md:110-137，§1.3–1.4 研究缺口与目标

已读证据ID：evidence/PASSPORT.md；evidence/ACN_DECISION.md；evidence/ACN_RANGE.json；evidence/ACN_BOUNDS.json；evidence/DATA_AVAIL.md

评分理由：对象、节点粒度、15 min代理负荷、预测时距和问题具体，公开会话来源及重构边界可查，任务与离线代理设置相符。节点级实际运行价值仍主要由一般性规划和负荷均衡需求支撑，未量化具体运营方的需求。

剩余缺口：应用需求未由运营约束或同步量测量化；这限制实际意义，不推翻所定义的代理预测问题。

### BR-02 研究问题、范围与题目一致性 — baseline 4.5/5.0；current 4.5/5.0

组件分（baseline/current）：BR-02-alignment: 2.0/2.0（满分2.0）；BR-02-progression: 1.5/1.5（满分2.0）；BR-02-closure: 1.0/1.0（满分1.0）。

稿件定位：
- manuscripts/baseline.md:1-27，题名及中英文摘要
- manuscripts/current.md:1-27，题名及中英文摘要
- manuscripts/baseline.md:110-170，§1.3–1.6 问题、技术路线与章节结构
- manuscripts/current.md:110-170，§1.3–1.6 问题、技术路线与章节结构
- manuscripts/baseline.md:1615-1637，结论及使用条件
- manuscripts/current.md:1615-1637，结论及使用条件

已读证据ID：evidence/MAP.md；evidence/MDP.md；evidence/S31.md；evidence/S32.md；evidence/S31AUDIT.json；evidence/S32AUDIT.json

评分理由：题名、摘要、研究问题、章节路线和结论围绕站内节点代理负荷、关系增量及诊断边界展开。JPL明确为同源场站重新拟合；MDP改变关系解释、学生替代判断和报告重点。第5章增添方向候选、区间与决策接口，已限制为探索或条件性分析。

剩余缺口：MDP指导改模收益未验证；应用章节只有接口和合成算例，不能支持运行收益。

### BR-03 文献综述与缺口定位 — baseline 4.5/5.0；current 4.5/5.0

组件分（baseline/current）：BR-03-coverage: 1.0/1.0（满分1.0）；BR-03-sources: 1.5/1.5（满分2.0）；BR-03-gap: 2.0/2.0（满分2.0）。

稿件定位：
- manuscripts/baseline.md:61-109，§1.2 文献综述
- manuscripts/current.md:61-109，§1.2 文献综述
- manuscripts/baseline.md:77-91，表1-1及表后近邻综合
- manuscripts/current.md:77-91，表1-1及表后近邻综合
- manuscripts/baseline.md:110-125，§1.3 研究缺口
- manuscripts/current.md:110-125，§1.3 研究缺口

已读证据ID：evidence/NEAR.md；evidence/NEAR2.md；evidence/NEAR76.md；evidence/NEAR_20261016.md

评分理由：综述覆盖EV预测、站间图、住宅图门控、事件和解释方法。对最接近的Liang [76]，明确写出公开Boulder会话重构EV代理预测、持续性残差锚点、同特征直接/残差比较和指标依赖结果；本文差异收窄到单场站内节点、关系替换重训和MDP。摘要或索引可读范围的限制有披露。

剩余缺口：未与[76]或其他近邻在同数据、输入权限、节点粒度和预算下对照；近邻差异定位不是统一基准。

### BR-04 理论基础与专业知识 — baseline 4.5/5.0；current 4.5/5.0

组件分（baseline/current）：BR-04-concepts: 2.0/2.0（满分2.0）；BR-04-formulas: 1.5/1.5（满分2.0）；BR-04-knowledge: 1.0/1.0（满分1.0）。

稿件定位：
- manuscripts/baseline.md:216-251，§2.1 预测时点、代理目标和数据协议
- manuscripts/current.md:216-251，§2.1 预测时点、代理目标和数据协议
- manuscripts/baseline.md:470-634，§3.3–3.5 图构建与模型公式
- manuscripts/current.md:470-634，§3.3–3.5 图构建与模型公式
- manuscripts/baseline.md:1053-1189，§4.1–4.3 MDP和蒸馏
- manuscripts/current.md:1053-1189，§4.1–4.3 MDP和蒸馏

已读证据ID：evidence/MDP.md；evidence/S31.md；evidence/S32.md；evidence/S31AUDIT.json；evidence/S32AUDIT.json；evidence/QUALITY.md

评分理由：清楚区分片能量与瞬时功率、统计关系与物理拓扑、权重观察与参数干预；公式与实际用途大体一致，且用于限定具体问题。β与关系变换可重参数化的条件有说明。

剩余缺口：片末行为可见仍是未实测假设；L2学生未匹配容量和输入路径，不能推出普遍可替代性。

### BR-05 方法与实验设计 — baseline 8.0/10.0；current 8.0/10.0

组件分（baseline/current）：BR-05-information_split: 2.5/2.5（满分3.0）；BR-05-comparators: 1.5/1.5（满分2.0）；BR-05-controls: 2.5/2.5（满分3.0）；BR-05-selection_budget: 1.5/1.5（满分2.0）。

稿件定位：
- manuscripts/baseline.md:216-278，§2.1–2.2 协议切分与筛选
- manuscripts/current.md:216-278，§2.1–2.2 协议切分与筛选
- manuscripts/baseline.md:644-734，§3.6 主比较
- manuscripts/current.md:644-734，§3.6 主比较
- manuscripts/baseline.md:864-928，§3.7 门控和关系控制
- manuscripts/current.md:864-928，§3.7 门控和关系控制
- manuscripts/baseline.md:996-1048，§3.8 预算及目标敏感性
- manuscripts/current.md:996-1048，§3.8 预算及目标敏感性

已读证据ID：evidence/S31.md；evidence/S31AUDIT.json；evidence/S32.md；evidence/S32AUDIT.json；evidence/RECOMP.json；evidence/MRECOMP.json；evidence/QUALITY.md

评分理由：完整窗口留段、共同预测键、训练期建图和选模规则可查；含容量近似TCN、较大AGCRN及同参数共享门控。节点门控、关系自环替换和目标敏感性各有对应控制。合同、种子和轮次有记录。

剩余缺口：关系替换和替代目标在已查看时期后补做；共享门控有种子触及预算上限；AGCRN未容量匹配，近邻未统一重跑。

### BR-06 可复现性与方法严谨性 — baseline 4.0/5.0；current 4.0/5.0

组件分（baseline/current）：BR-06-data_split: 1.0/1.0（满分1.0）；BR-06-source_config: 1.0/1.0（满分1.5）；BR-06-keys_metrics: 1.5/1.5（满分1.5）；BR-06-environment_package: 0.5/0.5（满分1.0）。

稿件定位：
- manuscripts/baseline.md:644-675，§3.6.1 预测键和指标
- manuscripts/current.md:644-675，§3.6.1 预测键和指标
- manuscripts/baseline.md:735-790，§3.6.4 复算和来源限制
- manuscripts/current.md:735-790，§3.6.4 复算和来源限制
- manuscripts/baseline.md:1260-1305，§4.6 JPL冻结结果复核
- manuscripts/current.md:1260-1305，§4.6 JPL冻结结果复核

已读证据ID：evidence/PASSPORT.md；evidence/QUALITY.md；evidence/MAP.md；evidence/ADAPT.md；evidence/ADAPTAUDIT.json；evidence/RECOMP.json；evidence/MRECOMP.json；evidence/S31AUDIT.json；evidence/S32AUDIT.json

评分理由：数据切分、预测键、指标、哈希和独立数值核对较完整；031/032合同与输出审计可追踪。复算范围及环境限制有披露。

剩余缺口：部分复算为冻结检查点前向或归档数组复算，非从原始输入起的第三方重训；旧AdaptiveGraph训练Git身份缺失，未形成外部一键重训包。

### BR-07 工作量与解决问题能力 — baseline 8.5/10.0；current 8.5/10.0

组件分（baseline/current）：BR-07-technical_work: 3.5/3.5（满分4.0）；BR-07-problem_solving: 3.0/3.0（满分4.0）；BR-07-integration: 2.0/2.0（满分2.0）。

稿件定位：
- manuscripts/baseline.md:178-430，第2章数据处理与特征分析
- manuscripts/current.md:178-430，第2章数据处理与特征分析
- manuscripts/baseline.md:431-1048，第3章方法、实验和敏感性
- manuscripts/current.md:431-1048，第3章方法、实验和敏感性
- manuscripts/baseline.md:1053-1305，第4章MDP及JPL复核
- manuscripts/current.md:1053-1305，第4章MDP及JPL复核

已读证据ID：evidence/MAP.md；evidence/QUALITY.md；evidence/PASSPORT.md；evidence/S31.md；evidence/S31AUDIT.json；evidence/S32.md；evidence/S32AUDIT.json；evidence/MDP.md；evidence/RECOMP.json；evidence/MRECOMP.json

评分理由：完成会话数据处理、节点筛选、多个模型/协议、配对门控、关系替换、目标敏感性、MDP、区间回放和接口核验，形成完整研究链。识别零目标驱动、β与结构增量差异、复算后端差异等体现问题解决能力。

剩余缺口：多项补充仍复用固定测试期；部分探索主要用于限制主张而非形成独立科学发现。未因缺现场或新数据在本项重复扣分。

### BR-08 结果与证据充分性 — baseline 8.0/10.0；current 8.0/10.0

组件分（baseline/current）：BR-08-claim_support: 3.5/3.5（满分4.0）；BR-08-alternatives: 2.5/2.5（满分3.0）；BR-08-robustness_scope: 2.0/2.0（满分3.0）。

稿件定位：
- manuscripts/baseline.md:677-734，§3.6 Caltech/JPL结果
- manuscripts/current.md:677-734，§3.6 Caltech/JPL结果
- manuscripts/baseline.md:885-928，§3.7.2 关系替换及分层
- manuscripts/current.md:885-928，§3.7.2 关系替换及分层
- manuscripts/baseline.md:1027-1048，§3.8.4 目标敏感性
- manuscripts/current.md:1027-1048，§3.8.4 目标敏感性
- manuscripts/baseline.md:1190-1257，§4.4–4.5 四格和MDP判断
- manuscripts/current.md:1190-1257，§4.4–4.5 四格和MDP判断

已读证据ID：evidence/MAP.md；evidence/QUALITY.md；evidence/S31.md；evidence/S31AUDIT.json；evidence/S32.md；evidence/S32AUDIT.json；evidence/RECOMP.json；evidence/MRECOMP.json；evidence/NZ.json；evidence/MDP.md

评分理由：主结果、分层结果、同参数门控和关系替换与共同键及独立复算相符。替代目标下全局排序保持，但零目标占94.27%，非零组仍较差。容量、预算、事件/规则错位和代理目标被作为替代解释。

剩余缺口：负荷关系非零组相对自环差异是已查看期的未校正事后组件分层，不能说完整MRG-GCN胜过TCN；未有实测功率、未查看时期或跨数据家族验证。

### BR-09 统计解释与结论边界 — baseline 8.0/10.0；current 8.0/10.0

组件分（baseline/current）：BR-09-uncertainty: 3.0/3.0（满分4.0）；BR-09-multiplicity: 1.5/1.5（满分2.0）；BR-09-interpretation: 3.5/3.5（满分4.0）。

稿件定位：
- manuscripts/baseline.md:644-734，§3.6 种子、分层和时间块
- manuscripts/current.md:644-734，§3.6 种子、分层和时间块
- manuscripts/baseline.md:885-928，§3.7.2 多重和事后分析
- manuscripts/current.md:885-928，§3.7.2 多重和事后分析
- manuscripts/baseline.md:1338-1389，§5.2 方向候选边界
- manuscripts/current.md:1338-1389，§5.2 方向候选边界
- manuscripts/baseline.md:1615-1637，结论限制
- manuscripts/current.md:1615-1637，结论限制

已读证据ID：evidence/S31.md；evidence/S31AUDIT.json；evidence/S32.md；evidence/S32AUDIT.json；evidence/NZ.json；evidence/MDP.md；evidence/CAL.md；evidence/RECOMP.json；evidence/MRECOMP.json；evidence/ACN_DECISION.md

评分理由：将种子波动、时间块变异和固定期限制分开解释；JPL关系全局比较校正，其它事后分层标明探索；不将键数冒充独立事件。正确区分零值驱动、关系增量、β联合敏感度和阴性结果。

剩余缺口：仅三个训练种子，时间块只描述固定时期；部分亚组未经多重校正，无新时间/站点确认。

### BR-10 贡献与创新 — baseline 7.5/10.0；current 7.5/10.0

组件分（baseline/current）：BR-10-prior_difference: 2.0/2.0（满分3.0）；BR-10-contribution: 2.5/2.5（满分3.0）；BR-10-demonstration: 3.0/3.0（满分4.0）。

稿件定位：
- manuscripts/baseline.md:77-109，表1-1及§1.2近邻比较
- manuscripts/current.md:77-109，表1-1及§1.2近邻比较
- manuscripts/baseline.md:110-137，§1.3–1.4缺口和贡献
- manuscripts/current.md:110-137，§1.3–1.4缺口和贡献
- manuscripts/baseline.md:860-928，§3.7组件增量
- manuscripts/current.md:860-928，§3.7组件增量
- manuscripts/baseline.md:967-1048，§3.8证据综合
- manuscripts/current.md:967-1048，§3.8证据综合
- manuscripts/baseline.md:1053-1257，第4章MDP及研究决策
- manuscripts/current.md:1053-1257，第4章MDP及研究决策
- manuscripts/baseline.md:1621-1637，结论
- manuscripts/current.md:1621-1637，结论

已读证据ID：evidence/NEAR.md；evidence/NEAR2.md；evidence/NEAR76.md；evidence/NEAR_20261016.md；evidence/S31.md；evidence/S31AUDIT.json；evidence/S32.md；evidence/S32AUDIT.json；evidence/MDP.md；evidence/MAP.md；evidence/MRECOMP.json；evidence/NZ.json

评分理由：准确承认图卷积、门控和时序组合非首创；不把一般代理EV预测或残差方法列为空白。实际增量是单站内节点代理任务的受控经验结果：JPL负荷与轮廓关系相对自环有条件整体MAE证据，行为关系不确定；两个ACN站点的节点门控有预算内整体差异。MDP改变研究判断：不按β大小删关系，当前学生不能证明普遍不可替代，要求并列报告困难格和常态格总误差。

剩余缺口：新增价值外部范围窄，主补充结果复用已查看期；未证明诊断指导改模能增益，未做跨数据家族或真实功率确认。

### BR-11 专业实践价值 — baseline 3.5/5.0；current 3.5/5.0

组件分（baseline/current）：BR-11-use_case: 1.0/1.0（满分1.0）；BR-11-real_inputs: 1.0/1.0（满分1.5）；BR-11-value_evaluation: 1.0/1.0（满分1.5）；BR-11-usable_outputs: 0.5/0.5（满分1.0）。

稿件定位：
- manuscripts/baseline.md:178-251，§2.1 数据和任务边界
- manuscripts/current.md:178-251，§2.1 数据和任务边界
- manuscripts/baseline.md:1526-1600，§5.4 决策接口与合成优化
- manuscripts/current.md:1526-1600，§5.4 决策接口与合成优化
- manuscripts/baseline.md:1631-1637，结论使用条件
- manuscripts/current.md:1631-1637，结论使用条件

已读证据ID：evidence/DATA_AVAIL.md；evidence/ACN_DECISION.md；evidence/ACN_RANGE.json；evidence/ACN_BOUNDS.json；evidence/PASSPORT.md；evidence/MAP.md；evidence/S31.md；evidence/S32.md；evidence/CAL.md

评分理由：提出节点代理负荷筛选、采数安排和影子核查用途，给出预测接口、固定代理轨迹和合成约束求解。真实会话数据有实践对应。

剩余缺口：无同步电表、输入到达时间、现实车辆约束或业务基线；合成计划只证明求解可行，不证明成本、安全或服务收益。新时期候选适用性仍未确认。

### BR-12 结构、表达与学术规范 — baseline 6.5/10.0；current 7.0/10.0

组件分（baseline/current）：BR-12-structure: 2.5/2.5（满分3.0）；BR-12-writing: 1.5/2.0（满分3.0）；BR-12-scholarly_content: 2.0/2.0（满分3.0）；BR-12-terminology: 0.5/0.5（满分1.0）。

稿件定位：
- manuscripts/baseline.md:1-173，题名、摘要、目录及第1章
- manuscripts/current.md:1-173，题名、摘要、目录及第1章
- manuscripts/baseline.md:431-1049，第3章结构和结果
- manuscripts/current.md:431-1049，第3章结构和结果
- manuscripts/baseline.md:1053-1305，第4章诊断
- manuscripts/current.md:1053-1305，第4章诊断
- manuscripts/baseline.md:1615-1762，结论、文献及附录
- manuscripts/current.md:1615-1762，结论、文献及附录

已读证据ID：evidence/MAP.md；evidence/QUALITY.md；evidence/PASSPORT.md；evidence/manifest.json；evidence/rubric.json

评分理由：结构推进清楚，注释和术语说明细致。current统一了摘要/结论的对象名称，并改写部分长句、展开WAPE中文名，故写作项加0.5。两稿仍重复说明范围，表格和证据细节密集。图像本体和版面未检查，不能记为通过。

剩余缺口：仍需压缩重复说明、统一代理能量/代理负荷语义并核查长段落；图像实际内容、清晰度和版面未视觉验收。致谢/成果占位是交付门槛，不计内容分。

## 原创性与实际新增知识的综合判断

最接近工作是Liang [76] 的Boulder公开会话重构EV负荷验证。其贡献已包含EV代理负荷预测和预测时点受限的直接/残差预测对照；本文没有把这两项写成研究空白。本文可辩护的差异在于单场站内部充电节点、15 min节点代理负荷、站内多关系及节点门控的任务内增量。EV站间图与住宅用户门控也说明图卷积、多关系和门控组合不是一般算法首创。两类工作数据、节点、输入权限及验证方案不同，本文没有做跨文数值排名。

实际新增知识是条件性而非普遍结论：JPL所检架构、数据、预算和固定时期内，负荷耦合及轮廓相似关系相对自环替换有整体MAE增量证据，行为共现关系仍不确定；节点差异门控在两个ACN场站的现行预算下有整体差异。目标敏感性结果保持全局排序，但替代目标测试键中94.27%为零目标，MRG-GCN非零组仍较容量近似TCN差。关系替换非零组正差仅为已查看期上的未校正事后组件分层，不能改写成完整模型胜过TCN；完整模型在JPL非零组仍落后于TCN，Caltech和完成时刻截断比较也没有非零组优势。

MDP诊断确实改变研究决策：不按β大小排序或删关系，关系取舍改依据邻接替换重训；当前只把负荷和轮廓列为优先复核、行为关系保留待确认。L2未被提升为普遍图不可替代结论，若要判断替代性须匹配学生容量、输入、目标和预算。L3促成同时报告稀有困难格误差和常态格累计误差。诊断因此改变解释、后续比较计划和报告重点，但尚未证明诊断引导的模型修改能提升精度或运行收益。

替代解释及证据限制：总体MAE优势部分由大量零目标键驱动；ACN两站同属一数据体系且时期重叠，不是跨家族或未来验证；行为可见性依赖片末假设，接收时延未核验；关系图是统计联系，不是物理或因果拓扑；补充分析复用已查看时期；三个训练种子和时间块不能代表场站抽样或完整训练随机性；节点范围、拓扑与替代标签的全流程重建未验证。真实同步功率、现场成本和实际运行约束评价缺失。

这些限制压低外推和实践价值，不把新增贡献归零。量表允许受控经验发现、工程判断和诊断方法成为贡献；未因缺新算子、全指标领先或现场部署而额外扣分。

## 已读材料与复核边界

两份稿件已通读并逐段比较；评分基于冻结稿、rubric、anchors及packet内全部证据文件。

Packet fingerprint：df6c1680331963797b6e15a60484f13ff85384a71676443169c2f25e92295724

已读证据文件：evidence/ACN_BOUNDS.json、evidence/ACN_DECISION.md、evidence/ACN_RANGE.json、evidence/ADAPT.md、evidence/ADAPTAUDIT.json、evidence/CAL.md、evidence/DATA_AVAIL.md、evidence/MAP.md、evidence/MDP.md、evidence/MRECOMP.json、evidence/NEAR.md、evidence/NEAR2.md、evidence/NEAR76.md、evidence/NEAR_20261016.md、evidence/NZ.json、evidence/PASSPORT.md、evidence/QUALITY.md、evidence/RECOMP.json、evidence/S31.md、evidence/S31AUDIT.json、evidence/S32.md、evidence/S32AUDIT.json

manifest表明图像本体、有效PPI和整页视觉验收未核验，未将其记录为通过。致谢及成果占位属于交付门槛，不计入内容分。