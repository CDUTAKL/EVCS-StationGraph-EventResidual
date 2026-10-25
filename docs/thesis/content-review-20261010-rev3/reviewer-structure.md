# REV3盲评：EVCS-THESIS-CONTENT-1.0

**总分：72 / 90（80.00 / 100，内容良好）**

**主线判断：** 全文围绕“会话记录重构的节点代理负荷”推进：界定数据和预测协议，提出 MRG-GCN，比较三套协议结果，再用 MDP 区分配置敏感度、受检蒸馏和误差构成，最后讨论区间可靠性与运行接口。JPL 是同属 ACN 数据体系、时期重叠的另一场站重新拟合，不是零样本迁移或未来时期验证。摘要、正文和结论总体守住了这些边界。

**主要剩余问题：** 架构对照仍不齐全；独立验证限于同一数据体系和固定历史时期；区间与运行应用尚未达到可部署证据。全文对协议边界的说明细致，但第3、5章若干段落重复。图3-16图件本身不在评审包中，以下核查限于正文引用、表3-11和图注。未读取项目目录材料、历史分数或其他评阅，也未做新的外部原文核查。

| 项目 | 得分 | 正文位置、评审包证据与理由 | 主要剩余缺口 |
|---|---:|---|---|
| **BR-01 选题意义与问题定义** | **4.5 / 5** | [1.1、1.3节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:37)及摘要把问题限定为稀疏、异质的站内节点代理负荷，并明确会话能量代理不等于电表功率。用公共充电规模和站内预测需求支撑研究动机。 | 需求主要是定性论述；没有量化节点预测误差会造成何种实际运行代价或决策改进。 |
| **BR-02 研究问题、范围与题目一致性** | **4.5 / 5** | [1.4—1.6节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:130)逐项连接研究问题、两项核心贡献、JPL验证及后续探索；[结论](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:1518)再次限定 JPL 不承担 MDP 跨站复现。题目、节点级预测对象与主要方法一致。 | 第5章扩展到方向性结构、共形区间和运行决策，内容跨度较大；虽标为探索，仍略显偏离题目的预测主线。 |
| **BR-03 文献综述与缺口定位** | **4.0 / 5** | [1.2节及表1-1](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:63)按时序预测、多节点图、事件建模和解释诊断梳理工作，并限定比较边界。包内 *nearest-work-source-audit.md* 标明[12]仅核实到摘要、[13]到官方索引片段、[67]查到接受稿全文、[70]依据摘要及索引片段；正文没有把不可读部分补写成事实，也没有跨论文数值排名。 | 最近工作虽有针对性，但几篇直接近邻并非都能核对完整原文；由此支撑的创新差异主要是研究粒度和诊断组合，独立新增能力的论证仍有限。 |
| **BR-04 理论基础与专业知识** | **4.5 / 5** | [第2章重构与事件定义](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:182)、[第3章LRE与MRG-GCN公式](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:483)及[第5章方向与功率换算](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:1163)交代单位、关系含义、目标时点和假设。绝对相关、不等于物理拓扑，门控权重不等于因果贡献，代理能量换算也不等于实测功率，均有明确说明。 | 部分方向性和共形分析依赖单场站历史序列；形式化定义清楚，但不能消除其统计假设和外部适用性限制。 |
| **BR-05 方法与实验设计** | **8.0 / 10** | [2.1.1节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:221)区分三套协议；[3.6.2—3.7.1节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:681)含容量近似匹配TCN、组件结果及同参数门控对照；[JPL报告](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/experiment-reports/SG-EXP-028-jpl-independent-site-validation-report.md)记载预登记主终点、共同预测键及时间块校正。 | 严格行为输入协议缺少同协议GRU及容量匹配AGCRN；论文已披露而未用旧协议结果填补。较宽松节点集合只做过筛选覆盖检查，没有模型重训练。 |
| **BR-06 可复现性与方法严谨性** | **4.0 / 5** | 第2章给出数据映射、切分和目标重构；[SG-EXP-027报告](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/experiment-reports/SG-EXP-027-paired-gate-control-report.md)和[SG-EXP-028报告](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/experiment-reports/SG-EXP-028-jpl-independent-site-validation-report.md)记载哈希、逐键核验、运行数和审计范围。正文也披露旧协议全时期上游统计及窗口边界问题。 | 评审包提供报告、汇总数据和审计摘要，没有完整训练代码、数据及逐次运行产物以供本次独立复算。复现判断依据为包内来源报告，非本次重跑。 |
| **BR-07 工作量与解决问题能力** | **8.0 / 10** | 五章覆盖数据重构、事件定义、图建模、多组基线与消融、冻结参数干预、蒸馏、四格误差分析、JPL重拟合及可靠性和决策接口探索。报告分别记载SG-EXP-019的36次运行、SG-EXP-027的6次配对运行与SG-EXP-028的12次正式运行。 | 大部分结论仍来自有限节点和固定时期；若干第5章结果属探索或历史回放，不能与外部确认验证等量看待。 |
| **BR-08 结果与证据充分性** | **8.0 / 10** | [表3-2、3-3及3.7.1节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:689)报告Caltech事件时刻协议和JPL的整体、分层及节点门控比较；JPL三项校正七日时间块区间均高于零。旧回溯协议也报告事件、稳定、非零窗口和逐步长表现。 | JPL中TCN的RMSE、事件MAE和非零目标MAE更低；旧回溯协议相对AdaptiveGraph的误差差小。JPL与Caltech同属ACN且时期重叠，不能验证不同数据家族或未来时期。 |
| **BR-09 统计解释与结论边界** | **8.5 / 10** | [4.2—4.4节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:1005)区分权重观察、冻结参数干预、蒸馏和误差构成；[5.3.6—5.3.7节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:1328)报告独立校准及成熟标签回放仍未达目标覆盖。结论正确保留滚动行为分层89.01%整体覆盖、26.71%事件覆盖及4.47倍宽度代价。 | TE检验未作多重比较校正；覆盖和时间块结果仍受固定历史时期及相关预测键限制。作者对此已明确降格为探索性证据。 |
| **BR-10 贡献与创新** | **7.5 / 10** | [1.4节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:130)把核心贡献限定为站内多关系预测方法与MDP；[3.5.8、4.2.5节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:610)承认图卷积、门控等组件已有先例，并用同参数门控对照支持一个较窄的节点差异增量。 | 贡献更像任务内组合与诊断组织；β独立增益、各关系的独立正增量及多个结构组件的必要性均未获支持。 |
| **BR-11 专业实践价值** | **3.0 / 5** | [5.5节](/private/tmp/evcs-content-review-20261010-rev3-packet/docs/thesis/thesis-manuscript.md:1417)把预测输入映射到余量核查及合成线性规划；SG-EXP-022记录时间映射审计，SG-EXP-026状态文件标明因代理量到电表映射未经验证，真实算例不可执行。正文没有声称已产生收益。 | 没有同步计量、现场约束或业务成本验证；固定例子显示事件起点前45分钟的低估，合成决策也不证明实际收益。 |
| **BR-12 结构、表达与学术规范** | **7.5 / 10** | 全文按“界定任务—预测证据—机制诊断—适用条件”推进，术语首次展开较完整。图3-12实际SVG横轴是 `[0,15)`、`[15,30)`、`[30,45)`、`[45,60)` min；与第2、3章发布时刻定义一致，表3-7数字也逐步对应。正文先引表3-11结构消融，再引图3-16；图注明确其0.01390内部基线不同于表3-4正式模型结果，引用关系正确。 | 章节边界、局限说明及摘要/小结有一定重复，部分图注较长。图3-16图件文件不在包内，本次只核对了正文引用、表3-11和图注，未检查图中标注本身。 |

**图表专项核查：** 图3-12与表3-7均把目标片区间定义为相对预测发布时刻的起点0、15、30、45分钟，覆盖发布后的连续1小时；h1起点与发布时刻相同，边界口径在正文中已有解释，图表标注相符。图3-16的交叉引用指向表3-11；图注提到表3-4是为说明两套基线不同，未发现误引。第5章压缩后的局限仍保留代理目标、事件路由错位、覆盖未达90%、滚动区间宽度代价、TE未校正、JPL未复现MDP及缺现场验证等关键信息。

**核查范围：** 只读取指定评审包内的规则、rubric、冻结稿全文、实验/分析报告、相关CSV与JSON、近邻文献原文访问层级报告，以及图3-12 SVG。未读取包内旧评阅目录，未访问项目目录，未运行训练、改动稿件或要求新实验。
