# 独立模拟盲审报告：研究闭合、贡献边界与诚信风险

**性质：模拟评阅，仅供研究修改参考，不是学校评分、等级或评审决定。**

## 1. 审阅范围与冻结材料

- 审阅日期：2026-10-15。
- 仅以冻结材料包 `/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/` 为研究证据；未打开旧 scorecard，也未参考历史评分或讨论分数。
- 全文读取 `manuscript-frozen.md`（1,774行，SHA-256：`99c5e22c64aa5d46333b727bd6f313a75f4958f1de4dbbf1133ae476f9643419`）及参考文献。采用 `rubric.json`（`EVCS-THESIS-CONTENT-1.0`，原始满分90、0.5分步长；SHA-256：`244fb698bd39b0e935e45116671c1954659a6720dc33faa42d9a7faf89433548`）。
- 范围沿用指定的既定边界：致谢和“在读期间发表的学术论文与研究成果”占位不作评价；不评价学校版式、WPS分页或全部图形的视觉质量。
- 已逐一阅读 packet 内与本次判断有关的证据映射、实验登记、材料护照、数据可用性、近邻文献原文核查、JPL MDP摘要、SG-EXP-031/032报告及审计材料、AdaptiveGraph CUDA复核材料和图表清单。实验审计 JSON与报告在包内可交叉核对；本次没有从包外取回原始会话、张量、预测、检查点或训练源码，也没有重新训练或重跑审计。

## 2. 总体判断

稿件围绕“会话记录重构的节点代理能量”形成了较完整的研究闭环：任务与三个评估协议有定义，核心预测结果、同参数节点门控比较、JPL关系替换、MDP诊断及应用探索均与结论中的适用边界相连。作者没有把代理能量写成电表功率，没有把JPL写成零样本迁移或未来期确认，也没有把β冻结替换、方向性筛查或合成调度算例提升为因果机制或实际收益证据。这些边界说明是全文的主要优点。

当前最强的经验结论是：所检固定协议和预算下，MRG-GCN在整体MAE上相对若干指定比较模型占优；同参数节点级门控在两套协议的已查看测试期表现出正向MAE差；JPL事后同参数自环替换支持负荷耦合及轮廓相似关系的条件性整体MAE增量。行为共现关系的增量尚不确定。总体成绩受零目标占比影响；活跃非零目标、事件组、不同场站/时期以及实测功率上的普遍优势均未成立。

主要修订工作集中在证据状态同步、近邻文献收束和对有限外部效度的持续约束；未见需要推翻当前代理任务结论的算术矛盾或可证实的学术诚信问题。建议完成这些定向修订后再进行一次内容复核。

## 3. 分项评分（原始分）

### BR-01 选题意义与问题定义 — **4.0/5**

- **正文定位：** 摘要第1段；§1.1.1–1.1.3；§2.1、表2-2；§5.4.1–5.4.5。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[data-availability.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/data-availability.md)、[material-passport.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/material-passport.md)。
- **得分理由：** 节点粒度、稀疏性和会话代理目标交代清楚，背景问题能够落到可建模对象；方法面向节点误差而非仅聚合负荷，数据身份与量纲也有说明。
- **主要缺口：** 实际运维需求没有来自场站用户、容量事件或业务损失的量化证据；“节点级预测更有用”的动机仍是合理性论证，实践效益留待现场验证。

### BR-02 研究问题、范围与题目一致性 — **4.5/5**

- **正文定位：** 摘要；§1.3–1.6；§2.1.1–2.1.3、表2-2；§3.8.2–3.8.4；结论“主要研究结论”及“研究局限与后续工作”。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[claim-evidence-map.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/claim-evidence-map.md)、[experiment-registry.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/experiment-registry.md)。
- **得分理由：** 题目中的站内多关系预测与机制诊断均在正文中有对应方法和结果。三种主协议、完成时刻目标敏感性及JPL关系替换的范围反复分开说明，结论也回到各自可回答的问题。
- **主要缺口：** 章节覆盖面从点预测延伸至方向性统计、共形区间及运行接口，研究主线较宽；尽管第5章已标为探索，终稿仍应维持“预测支持探索”的次级地位，避免让题目或摘要暗示已经形成完整运行机制。

### BR-03 文献综述与缺口定位 — **3.5/5**

- **正文定位：** §1.2.1–1.2.4，特别是§1.2.2表1-1及其后近邻比较；§1.3；参考文献[10]–[13]、[67]、[70]–[73]。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[nearest-work-source-audit.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/nearest-work-source-audit.md)、[rubric.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/rubric.json)。
- **得分理由：** 对EV直接近邻[12]、[13]、[67]、[70]记录了可读原文层级、节点粒度及未知字段；对住宅负荷STGNet[71]指出多图门控和节点特定参数化已有先例；稿件据此主动缩小首创主张，并避免跨论文数值排名，缺口边界基本可辩护。
- **主要缺口：** 综述总体仍偏方法罗列，少有按节点粒度、预测信息权限、评价设计和可检验增量做系统综合。参考文献[72]、[73]在正文未见对应引文，且尤其[73]题名涉及空间—时间融合的自适应门控图卷积；应核查其与本文定位的关系，补上有来源依据的比较，或按规范删除未引用条目。当前源审计覆盖若干代表性近邻，不等于所有相关研究均已穷尽。

### BR-04 理论基础与专业知识 — **4.5/5**

- **正文定位：** §2.1式（2-1）、§2.4式（2-2）；§3.2–3.5式（3-1）–（3-13）；§4.2.5；§5.2式（5-1）–（5-2）、§5.3及§5.4式（5-4）–（5-7）。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[data-availability.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/data-availability.md)、[sgexp032-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-report.md)。
- **得分理由：** 代理能量与功率区分、预测发布时刻、目标片起点、图关系语义及β/G参数层级定义较严谨。重参数化解释说明了为何冻结β替换只能表示联合配置敏感度；功率换算不被包装为实测量。
- **主要缺口：** 研究对标签物理效度仍主要依赖会话字段重构和有限历史电流形态核查；输入行为计数的到达时刻也没有数据证据。理论表述可以成立，但目前适用对象是代理序列，不能作更强的物理解释。

### BR-05 方法与实验设计 — **7.5/10**

- **正文定位：** §2.1.1–2.1.3；表3-1–3-3、表3-9、表3-11、表3-14–3-15；§4.2–4.6；§5.3.6–5.3.7。
- **已读证据路径：** [sgexp031-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-report.md)、[sgexp031-audit-readme.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-audit-readme.md)、[sgexp031-audit.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-audit.json)、[sgexp032-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-report.md)、[sgexp032-audit.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-audit.json)、[experiment-registry.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/experiment-registry.md)。
- **得分理由：** 训练、调参、校准与测试边界有区分；同参数门控和关系替换控制比单纯删模块更有解释力。SG-EXP-031/032均有共同预测键、预算和复算记录，且正文区分预登记比较与事后补充。
- **主要缺口：** 031与032复用已查看测试期，不能当独立确认；JPL与Caltech仍是同一ACN数据家族且年份重叠。Caltech事件时刻协议缺行为GRU和容量匹配AGCRN；JPL共享门控有种子触及训练上限，训练充分度并未完全对齐。现有区间重采样主要描述固定时期的时间块变异，不是站点或完整训练随机性的抽样推断。

### BR-06 可复现性与方法严谨性 — **4.0/5**

- **正文定位：** §2.1–2.2；§3.6.1、§3.6.3、§3.8.3；表3-14；§4.6.1；§5.3.6–5.3.7。
- **已读证据路径：** [material-passport.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/material-passport.md)、[data-availability.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/data-availability.md)、[sgexp031-audit-readme.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-audit-readme.md)、[sgexp031-audit.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-audit.json)、[sgexp032-audit-readme.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-audit-readme.md)、[sgexp032-audit.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-audit.json)、[sgexp032-recovery.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-recovery.json)、[sgexp032-shutdown.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-shutdown.json)、[adaptivegraph-cuda-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/adaptivegraph-cuda-report.md)、[adaptivegraph-cuda-verification.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/adaptivegraph-cuda-verification.json)。
- **得分理由：** 031记录远端/本地归档一致、173项内层校验、四配置×三种子、每配置32,714参数、共同键及指标独立复算；032记录六次运行、99项校验、708,560共同键和指标复算PASS。数据来源哈希、训练合同和限制均有留档。
- **主要缺口：** 冻结包提供审计摘要而非原始会话、预测和检查点，本次不能独立重跑；部分早期训练记录的源码身份/`git_commit`缺口由材料护照承认。另有一项实质性记录同步问题：AdaptiveGraph于2026-10-15的CUDA复核已显示三个种子在匹配CUDA以及“CPU固定CUDA邻接”下均逐键通过，原生CPU不通过且与top-k边界并列换边相符；但正文§3.6.4仍只记CPU未通过、称未完成跨后端复现，实验登记也保留10月13日“CUDA待确认”。这段CPU失败并非错误陈述，但当前证据状态未写全。建议将CUDA通过、CPU失败及训练源码未认证三者并列说明，并同步登记表。

### BR-07 工作量与解决问题能力 — **9.0/10**

- **正文定位：** 全文第2–5章；表3-2–3-15、表4-1–4-8、表5-1–5-9及结论。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[experiment-registry.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/experiment-registry.md)、[claim-evidence-map.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/claim-evidence-map.md)。
- **得分理由：** 数据重构、模型对照、多协议、两地重拟合、同参数门控、关系自环重训、诊断、区间回放及合成决策接口构成持续且技术要求较高的工作；负结果和无效探索没有被隐去，且结果边界有较多独立审计材料支持。
- **主要缺口：** 工作广度较大但多个侧线仍属探索，已有单一研究家族与固定时期的数据边界限制其独立解决实际运营问题的证据强度。

### BR-08 结果与证据充分性 — **8.0/10**

- **正文定位：** 表3-2–3-3、表3-9、表3-11、表3-15；表4-5、表4-8；表5-2、表5-5–5-6；结论（1）–（5）。
- **已读证据路径：** [sgexp031-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-report.md)、[sgexp031-audit.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-audit.json)、[sgexp032-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-report.md)、[sgexp032-audit.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-audit.json)、[jpl-mdp-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/jpl-mdp-report.md)、[adaptivegraph-cuda-verification.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/adaptivegraph-cuda-verification.json)。
- **得分理由：** 主要新实验数值与包内独立审计一致。031的三项差值、同时区间和事件分层方向正确；032的MAE、零值比例、非零组反向结果与配对区间相符；JPL MDP报告支持正文L1/L3范围。结论承认RMSE/事件/非零层并非全面占优。
- **主要缺口：** 核心新补充实验均是对已查看时期的复用分析。事件窗口稀少，外部站点仍同源；数据包没有实测电表标签。AdaptiveGraph复现状态需同步，现有自适应图近似排名的可复核描述因此不够完整。

### BR-09 统计解释与结论边界 — **8.5/10**

- **正文定位：** §2.1.1–2.1.3；§3.6.2–3.8；§4.2.5、§4.3.3、§4.4、§4.6；§5.2.3–5.2.6、§5.3.2–5.3.7；结论。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[sgexp031-audit-readme.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-audit-readme.md)、[sgexp032-audit-readme.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp032-audit-readme.md)、[data-availability.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/data-availability.md)。
- **得分理由：** 全文多次分清固定期时间块不确定性、种子离散度、场站抽样和未来期验证；事后分析、标签组成、区间覆盖失配、方向性候选多重比较、事件路由错位及代理能量限制均有明确解释。结论没有把零目标全局MAE差推广为活跃负荷改进。
- **主要缺口：** 三种子样本不足以稳定估计训练不确定性；七日重采样只刻画一个固定时期的时间变化。统计叙述已披露这些限制，但证据仍不足以给出可迁移的误差或覆盖保证。

### BR-10 贡献与创新 — **6.5/10**

- **正文定位：** §1.2.2–1.2.4、§1.3–1.4；表3-13；§4.1、§4.5–4.6；结论“研究工作总结”。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[nearest-work-source-audit.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/nearest-work-source-audit.md)、[sgexp031-audit-readme.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/sgexp031-audit-readme.md)、[jpl-mdp-report.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/jpl-mdp-report.md)。
- **得分理由：** 贡献边界经过明显收束，不声称多图、门控或节点参数化的一般形式首创。节点门控有同参数重训证据；JPL关系图相对自环的结果只支持两类关系在限定协议内的条件性增量；MDP更多体现诊断流程的任务化组织与解释约束，作为工程/专业硕士增量具有可信度。
- **主要缺口：** MDP未表现为新的可识别机制理论或能提升预测性能的已验证方法；关系增量证据只有一个事后JPL固定测试期，且事件共现图未获确认。贡献是有限、组合式和条件性的，尚不能支撑广义算法创新。

### BR-11 专业实践价值 — **3.0/5**

- **正文定位：** §5.4.1–5.4.5、表5-7–5-8；§5.5表5-9；结论“工程含义与适用范围”。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[claim-evidence-map.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/claim-evidence-map.md)、[data-availability.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/data-availability.md)。
- **得分理由：** 预测到运行核查的接口、拒绝无材料的真实计划、失败时标记预测不可用及人工复核路径均有清楚说明；合成LP枚举核验支持约束实现的可行性。
- **主要缺口：** 合成计划不是现场运行证据；真实案例缺同步电表、全站其他负荷、容量限额、车辆约束和实际电价，论文没有验证降低成本、安全风险或调度收益。实践价值目前是合理的候选方向。

### BR-12 结构、表达与学术规范 — **7.5/10**

- **正文定位：** 全文；重点§1.2表1-1、§2.1.1、§3.8、§4.5–4.6、§5.5及参考文献。
- **已读证据路径：** [manuscript-frozen.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/manuscript-frozen.md)、[figure-manifest.json](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/figure-manifest.json)、[nearest-work-source-audit.md](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/thesis/content-review-20261015-rev7/packet/nearest-work-source-audit.md)。
- **得分理由：** 章节推进有层次，单位、张量和指标口径反复交代，表格注释主动区分描述性与主要终点；语句整体可读。图表清单显示46项且无缺失文件，但仅核对清单，未做视觉审读。
- **主要缺口：** 对代理目标、事后分析和应用边界的重复说明较多，全文显得冗长；参考文献[72]、[73]目前未见正文引用；AdaptiveGraph的新CUDA复核尚未同步进正文和登记材料。此评分不含学校格式、WPS分页和完整图像视觉检查。

## 4. 分数与建议

**原始总分：70.5/90。** 仅按12项原始分直接相加，不归一化、不映射学校官方等级，也不提供官方结论预测。

**阻断问题：未发现针对当前“代理能量离线预测与诊断”研究范围的核心证据链崩溃、结果数值相互冲突或可证实诚信问题。** 实测功率效度、现场上报延迟和运行收益仍未验证；正文已把它们列作限制和后续工作，不应在摘要、结论或答辩中把现有结果扩展成实测功率预测或上线收益。

**建议：完成定向修改后再评阅，不据本分数作学校等级或答辩决定。** 优先事项：

1. 在§3.6.4/§3.8.3及实验登记中同步AdaptiveGraph复核状态：CUDA检查点复算3/3通过；原生CPU复算因top-k并列邻接不同而失败；使用CUDA选出的邻接后CPU也通过。仍需保留原训练`git_commit`缺失的限制，不把推理重放写成从头训练复现。
2. 处理文献[72]、[73]的未引用问题，并说明[73]等住宅负荷门控图近邻对贡献边界的影响；若与本文差异有限，进一步把新颖性定位于任务化构造和限定条件下的实验证据。
3. 在摘要和结论维持“整体MAE增量、零值构成、代理目标、固定测试期”四项并列说明；不要将事件共现关系、β独立增益、事件活跃负荷收益或实际调度价值写成已获证实。

## 5. 置信度与限制

- **置信度：中高。** 对研究问题、范围闭合、报告数值之间的文本/审计一致性判断较有把握；对原始训练、数据源以及端到端重现的判断有限，因为本包未附原始张量、逐键预测、检查点和源码快照。
- 本次实验核验是对冻结包中的实验报告、审计JSON、哈希、键/指标摘要和结论边界作逐项交叉检查；不代表我已独立重跑SG-EXP-031/032训练或重新执行全部审计脚本。
- 近邻文献判断沿用包内 `nearest-work-source-audit.md` 所记原文可读范围；未在本轮包外重新获取文献。
- `figure-manifest.json`列出46项且缺失项为0，但图像视觉质量未审阅；学校模板/版式、WPS目录分页与终端成果占位按指定范围排除。
