# REV8独立评阅：方法与证据

## 评阅记录

- 量表：EVCS-THESIS-CONTENT-1.0；原始满分90分，单项0.5分步进。
- 稿件：REV8冻结稿，`manuscript-frozen.md`；SHA-256：`f5ba2ddba9157fa18ea91c93214a375c2422916916125ba0f50a9d5ced228f6e`。已对冻结稿实算SHA-256，与证据清单一致。
- 配对基线：REV7，稿件SHA-256 `99c5e22c64aa5d46333b727bd6f313a75f4958f1de4dbbf1133ae476f9643419`；基线评分文件SHA-256 `a9eb3b540f29f5a94efd8ea645a3855caf39efd863379decb3211915e7860165`。两者均与清单一致。
- 范围：双语摘要、五章、结论、表格及图注的内容和证据；版式与图片视觉验收不在本报告判断范围。
- 置信度：中。

## 逐项评分

| 指标 | REV8 | REV7 | 差值 | 变化类型 |
|---|---:|---:|---:|---|
| BR-01 选题意义与问题定义 | 4.5/5 | 4.5/5 | 0 | unchanged |
| BR-02 研究问题、范围与题目一致性 | 5.0/5 | 5.0/5 | 0 | unchanged |
| BR-03 文献综述与缺口定位 | 4.5/5 | 4.5/5 | 0 | unchanged |
| BR-04 理论基础与专业知识 | 4.5/5 | 4.5/5 | 0 | unchanged |
| BR-05 方法与实验设计 | 8.5/10 | 8.5/10 | 0 | unchanged |
| BR-06 可复现性与方法严谨性 | 5.0/5 | 4.5/5 | +0.5 | improvement |
| BR-07 工作量与解决问题能力 | 9.0/10 | 9.0/10 | 0 | unchanged |
| BR-08 结果与证据充分性 | 9.0/10 | 9.0/10 | 0 | unchanged |
| BR-09 统计解释与结论边界 | 9.5/10 | 9.5/10 | 0 | unchanged |
| BR-10 贡献与创新 | 8.0/10 | 8.0/10 | 0 | unchanged |
| BR-11 专业实践价值 | 3.5/5 | 3.5/5 | 0 | unchanged |
| BR-12 结构、表达与学术规范 | 9.5/10 | 9.0/10 | +0.5 | improvement |

### BR-01 — 4.5/5（基线4.5；差值0；unchanged）

- **正文定位：** 摘要；§1.1、§1.3—1.4；§2.1—2.2；§5.4.1—5.4.5。
- **实际阅读证据：** `manuscript-frozen.md`；`data-availability.md`；`material-passport.md`；`claim-evidence-map.md`。
- **理由与缺口：** 研究对象、节点代理能量、时间粒度、节点来源与筛选范围具体；论文亦说明会话总电量均摊不等于连续功率。现有需求陈述仍缺同步电表、现场用户需求和业务效益量化。REV8没有新增现场需求证据，维持REV7判断。

### BR-02 — 5.0/5（基线5.0；差值0；unchanged）

- **正文定位：** 题名、摘要；§1.3—1.6；§2.1.1—2.1.3；§3.6、§3.8.2—3.8.4；结论。
- **实际阅读证据：** `manuscript-frozen.md`；`claim-evidence-map.md`；`experiment-registry.md`。
- **理由与缺口：** 题目、节点代理目标、三套预测协议、方法、结果和结论相互对应。Caltech/JPL均限定为会话派生代理目标，JPL限定为另一ACN场站重拟合而非零样本迁移；SG-EXP-031/032也标为已查看测试期的事后补充。REV8重排和压缩表述，没有改变问题范围或修补新的范围偏移。实测功率和跨域主张仍不成立，但已明确排除。

### BR-03 — 4.5/5（基线4.5；差值0；unchanged）

- **正文定位：** §1.2.1—1.2.4；表1-1；§1.3；§3.5.8。
- **实际阅读证据：** `manuscript-frozen.md`；`nearest-work-original.md`；`nearest-work-72-73.md`。
- **理由与缺口：** 综述按站间/站群与单站内节点区分对象，并把贡献收窄至任务化关系定义、节点门控对照及诊断证据。REV8在正文增加[72]、[73]的明确先例和引用，改善了一般多图/门控结构的边界说明；但相关全文实验协议未能从冻结材料核实，[12]、[70]等也仅能查到摘要或索引内容，不能据此完成所有最近工作间的细粒度原文比较。新增引用带来实质文字补全，但尚不足以消除这一证据缺口或改变半分档位。

### BR-04 — 4.5/5（基线4.5；差值0；unchanged）

- **正文定位：** §2.1.1—2.1.3、§2.2；§3.2—3.5；§4.2—4.4；§5.2—5.3。
- **实际阅读证据：** `manuscript-frozen.md`；`data-quality-report.md`；`metric-diagnostics.md`；`sg032-report.md`。
- **理由与缺口：** 能量单位、预测片时点、关系图统计解释、参数干预和蒸馏边界写得较准确；区分了代理能量与功率、统计关联与物理拓扑、冻结β替换与重训练效应。主要尚缺片末事件实际到达时延、代理标签与连续实测功率效度，以及替代目标下重建拓扑的端到端敏感性。REV8未增加这些验证。

### BR-05 — 8.5/10（基线8.5；差值0；unchanged）

- **正文定位：** §2.1.1—2.2；§3.2—3.8，尤其表3-2、3-3、3-9、3-11、3-14、3-15；§4.2—4.3。
- **实际阅读证据：** `manuscript-frozen.md`；`experiment-registry.md`；`sg031-report.md`与`sg031-audit.json`；`sg032-report.md`与`sg032-audit.json`；`adaptivegraph-report.md`；`jpl-calibration-report.md`。
- **理由与缺口：** 主要对照给出输入权限、节点、预测键、参数数、训练上限、早停和选模准则。JPL SG-EXP-031固定参数数、同种子非图初始化并逐个将关系图替为自环；SG-EXP-032固定事件时刻输入、原图、切分和键，仅换标签重训。两者把“条件增量”和“目标敏感性”分开回答，设计有力。缺口仍包括事件时刻协议缺行为GRU及容量匹配AGCRN、共享门控运行触及训练上限、蒸馏学生未容量匹配、SG-031/032均复用已查看测试期、节点筛选敏感性仅审计覆盖而未重训。参数量亦不替代推理成本测量。REV8相较REV7没有新增受控训练设计足以再加分；JPL校准是既有预测的后验评价，不当作新的模型对照。

### BR-06 — 5.0/5（基线4.5；差值+0.5；improvement）

- **正文定位：** §2.1.1—2.2；§3.6.1、§3.6.4、§3.8.3；表3-14；§5.3.3—5.3.5。
- **实际阅读证据：** `sg031-report.md`与`sg031-audit.json`；`sg032-report.md`与`sg032-audit.json`；`adaptivegraph-report.md`与`adaptivegraph-verification.json`；`jpl-calibration-report.md`、`jpl-calibration-audit.json`与`jpl-calibration-verification.json`；`experiment-registry.md`；`data-quality-report.md`；`source-audit.json`。
- **理由与缺口：** 冻结REV8正文已同步AdaptiveGraph三检查点在匹配CUDA环境通过、top-k并列可解释本轮CPU差异、历史macOS偏差仍未解决等状态；基线指出的“正文未同步”问题已修复。SG-031与032审计分别报告工件哈希、共同键/标签掩码、参数和训练合同、逐键指标复算通过；JPL区间审计对校准秩、两端区间和覆盖复算通过，最大差约`2.22e-16`。预测键、切分、输入和选模口径可追溯。保留的限制是AdaptiveGraph原训练`git_commit`缺失，历史macOS数值偏差未完全解释；这些限制在正文和证据中均可见，因此未将其写作完整从头复现。
- **配对依据：** 新增的匹配环境检查点证据与其正文同步，补上REV7基线所记的一项可复核性缺口；不是因审阅口径变严而上调。

### BR-07 — 9.0/10（基线9.0；差值0；unchanged）

- **正文定位：** §2.1—2.6；§3.3—3.8；§4.2—4.6；§5.2—5.4。
- **实际阅读证据：** `manuscript-frozen.md`；`experiment-registry.md`；`sg031-report.md`；`sg032-report.md`；`adaptivegraph-report.md`；`jpl-calibration-report.md`。
- **理由与缺口：** 工作包含会话重构、三套评估协议、多项模型比较、组件重训练、蒸馏/机制诊断、区间回放及应用接口约束，表现出有难度的独立问题处理。按量表不以运行或文件数本身计分。实测、其他数据家族和新时期验证未覆盖；新增后验可靠性结果补充分析范围，但没有改变工程效度边界或足以改变高档位置。

### BR-08 — 9.0/10（基线9.0；差值0；unchanged）

- **正文定位：** §3.6—3.8，特别是表3-2、3-3、3-11、3-15；§4.2—4.4；§5.3.3—5.3.7；结论。
- **实际阅读证据：** `manuscript-frozen.md`；`sg031-report.md`及`sg031-audit.json`；`sg032-report.md`及`sg032-audit.json`；`caltech-main-strata.json`；`jpl-calibration-report.md`及其审计/验证JSON；`metric-diagnostics.md`；`claim-evidence-map.md`。
- **理由与缺口：** 核心表格有直接预测、配对关系替换、零/非零/事件分层、目标敏感性和逐键复核支持；正文没有把全局MAE优势扩展成全面领先。JPL区间结果新增一条经过独立复算的校准证据，但只重用先前固定测试期预测，不能当成独立确认；SG-031/032也使用已查看测试期。事件及非零目标表现、实际功率效度和未见场站/时期验证仍限制核心外推。新增可靠性证据加强第5章，但没有把主要预测结论提升到新的确认等级，故维持配对分数。

### BR-09 — 9.5/10（基线9.5；差值0；unchanged）

- **正文定位：** §2.1.1—2.1.2；§3.6—3.8；§4.2—4.4；§5.2—5.3；§5.4.3—5.4.5；结论。
- **实际阅读证据：** `manuscript-frozen.md`；`metric-diagnostics.md`；`jpl-calibration-report.md`及`jpl-calibration-verification.json`；`sg031-audit.json`；`sg032-audit.json`。
- **理由与缺口：** 稿件区分三种子离散度、固定期时间块Bootstrap、事后分层与独立校准含义；说明时间窗口重叠及种子并非独立站点样本；记录负结果、区间跨零、非零组反向结果和覆盖失败。TE家族校正、JPL关系比较的Bonferroni区间、共形秩、测试失配与局限均有明确解释。剩余缺口是没有新场站/时期抽样不确定性或未查看确认测试；有限样本时间块区间不解决外部效度。新JPL区间仍为已查看时期后验评价，故改善边界披露但不改变统计结论的证据等级。

### BR-10 — 8.0/10（基线8.0；差值0；unchanged）

- **正文定位：** §1.2—1.4；§3.5.8；表3-13；§3.8.1；§4.5—4.6；结论。
- **实际阅读证据：** `manuscript-frozen.md`；`nearest-work-original.md`；`nearest-work-72-73.md`；`sg031-report.md`与`sg031-audit.json`；`claim-evidence-map.md`。
- **理由与缺口：** 贡献定位为站内代理任务的关系构造、同参数节点门控/关系替换证据与诊断组织，不声称通用图算子首创。SG-031支持两类关系相对自环替代的有限条件增量，第三类区间跨零；节点门控比较亦具直接增量证据。[72]/[73]的新增引用更完整地承认多图和门控时空方法先例，但其全文协议未核实。贡献仍是受限增量，尚无未见时期/不同数据家族/实测功率验证，也未证明诊断能指导改模获益，因此维持REV7分数。

### BR-11 — 3.5/5（基线3.5；差值0；unchanged）

- **正文定位：** §2.1.2—2.1.3；§5.4.1—5.4.5；表5-7、5-8；结论。
- **实际阅读证据：** `manuscript-frozen.md`；`data-availability.md`；`material-passport.md`；`claim-evidence-map.md`。
- **理由与缺口：** 运行接口、代理功率换算、容量余量公式及影子决策过程写得具体，并将10节点范围、提示性质和人工复核要求限制清楚；合成LP可行性不被说成实际收益。没有同步实测、全站负荷/设备容量、车辆请求、电价、影子运行或成本对照，故专业应用价值仍为接口潜力而非验证效果。REV8未增加现场证据。

### BR-12 — 9.5/10（基线9.0；差值+0.5；improvement）

- **正文定位：** 双语摘要；§1.2.2；§1.4—1.6；§3.6—3.8；§5.3；附录A；结论。
- **实际阅读证据：** `manuscript-frozen.md`；REV7冻结稿；`source-audit.json`；`rubric.json`与`score-rules.md`。
- **理由与缺口：** 与REV7逐稿对照，REV8将主预测协议和历史回溯结果重新编排，按“主预测—回溯—组件—证据综合”组织第3章；新增JPL独立区间评价和成熟标签滚动评价并纳入第5章；补入附录A的事件时刻完整组件结果；摘要压缩并更集中呈现限制；修复表3-13删除变体/时间块分析的交叉指向。冻结`source-audit.json`报告引用92条、未引用0条、未定义引用0条、缺失图注目标0条，且确认交叉引用修复。以上改变提升了结构和证据导航。
- **配对依据与剩余缺口：** 具体文本/结构更新且来源闭合支持+0.5，而非仅因写法偏好加分。仍有多处重复提醒“已查看测试期”和代理边界，章节密度较高；本轮只审了冻结稿文字与图注，没有检验图片视觉呈现或学校版式，故不评满分。

## 汇总、配对差值与阻断项

- REV7基线：79.5/90 = 88.33/100。
- REV8本评：80.5/90 = 89.44/100（按总分/90×100，最终四舍五入两位）。
- 配对差值：+1.0/90 = +1.11个百分制点。变化来自BR-06可追溯复算状态与正文同步改善（+0.5），以及BR-12章节重组、引用交叉闭合和增补结果编排（+0.5）。其他项没有因单纯换序或写法压缩而改变分数。
- **阻断项：无。** 证据足以逐项判断，无需N/A或暂停总分。以下是已确认的限制，不构成本轮计分阻断：SG-EXP-031/032为已查看测试期后验补充；同属ACN且时期重叠；代理目标非连续实测功率；事件时刻输入延迟未核实；AdaptiveGraph原训练Git身份缺失且历史Mac偏差未解；行为GRU、容量匹配AGCRN、外部新时期/新数据家族、真实运行收益等仍缺。

## 本轮实际读取的冻结材料

除`README.md`和`evidence-manifest.json`外，本报告直接阅读了以下packet文件；未以文件名代替证据核验：

- 稿件和配对基线：`manuscript-frozen.md`、`prior-manuscript-rev7.md`、`prior-scorecard-rev7.json`。
- 量表：`rubric.json`、`score-rules.md`。
- 方法、实验及审计：`experiment-registry.md`、`sg031-report.md`、`sg031-audit.json`、`sg032-report.md`、`sg032-audit.json`、`adaptivegraph-report.md`、`adaptivegraph-verification.json`、`jpl-calibration-report.md`、`jpl-calibration-audit.json`、`jpl-calibration-verification.json`、`caltech-main-strata.json`。
- 数据、主张和复现范围：`claim-evidence-map.md`、`data-availability.md`、`material-passport.md`、`metric-diagnostics.md`、`data-quality-report.md`、`source-audit.json`。
- 近邻比较：`nearest-work-original.md`、`nearest-work-72-73.md`。

评分适用于上述冻结稿和材料包，不是学校官方等级或实际盲审预测。图像视觉、Word/WPS目录分页和交付版式另审。
