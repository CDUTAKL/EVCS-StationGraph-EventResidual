# 新增补强证据映射

## 2026-10-26 代理标签排序敏感性复评

- **CLM-032-LABEL-RANK**：SG-EXP-019/027/032的48份冻结预测与两套标签数据，在相同708,560个Caltech测试键上交叉评价；未训练、未改变预测。总体MAE排名的Spearman为0.993（先平均三种子MAE再排序），逐种子相关均值为0.974；按评价标签定义的非零组分别为0.420与0.000。门控优势平均由2.69%降至1.65%，seed-2024由+1.73%反转为−0.91%。证据限于已查看时期与所检12配置，不能证明实测效度或未见时期泛化。产物：`outputs/analysis/SG-ANA-20261026-proxy-stability/`；正文§3.8.5、表3-16、图3-17、附表A-2。
- **MAT-PROXY-STABILITY-PROVENANCE**：小型集成副本保存50项输入与27项冻结输出的来源哈希；输入大文件未复制进Git。`source-provenance.lock.json`锁定来源字段，`make_manifest.py`将当前查找位置写入单独的`lookup_*`字段，源缺失或哈希错误时失败关闭。外部原包未改写。

## 2026-10-22当前补充入口

- **REPLAY-031/032**：`revision-20261022-evidence/reproducibility-package.json`及`.md`保存源码归档、配置/环境、检查点/预测清单与复算入口；031源清单67项、032为91项，18次运行清单及已有预测指标复算通过。范围为保存预测的算术/统计复算，不是权重前向或从头训练复现；原历史Git身份限制保留。大文件为本地外置归档，尚未发布公共仓库。
- **EPFL-V2-SHAPE**：正文2.1.2；`revision-20261022-evidence/epfl-proxy-audit-v2.json`及报告。无Energy时间键1,878对匹配，1,620条纳入；形态距离中位0.0736。只支持外部表内P字段时间分布与均匀化参照的探索性比较，计量边界未清、分箱口径不同，不支持ACN标签校准、模型性能或运行收益。
- **DATA-TARGETED**：`revision-20261022-evidence/targeted-data-search.md`限定下一轮具体材料门槛。当前候选未找到ACN冻结模型兼容的未查看期段，不推断其他来源不存在。EPFL部分真实容量/控制信息已确认，ACN对齐运行合同仍缺。

下方日期条目保留历史来源状态；正文新数据引用为[84]，原[84]—[92]顺延为[85]—[93]，近邻[76]编号不变。

## 当前证据状态（2026-10-21更新）

本节为当前入口；下方按日期保留的历史失败、预检和待办状态仅代表当时情况。正文表号以当前主稿为准。

### 论文核心结论权限

| 结论层级 | 当前证据 | 正文可作的判断 | 不支持的外推 |
|---|---|---|---|
| 主要模型比较 | Caltech事件时刻协议、JPL重新拟合；整体与分层MAE/RMSE | MRG-GCN在所检协议下有整体MAE优势；该优势没有稳定延伸至非零目标和标签事件组 | 活跃充电预测全面领先、跨数据家族泛化或实测功率预测 |
| 节点门控增量 | Caltech与JPL同参数共享门控对照，各有一个共享门控种子触及60轮上限 | 当前预算及选模规则下，节点级门控的整体MAE较低 | 更长预算下仍占优或跨时期普遍成立 |
| 关系增量 | SG-EXP-031 JPL同参数自环替换：负荷与轮廓关系的整体差异区间为正；行为关系区间跨零 | 负荷与轮廓关系在本架构、协议和预算下有条件性整体增量证据；行为关系仍不确定 | 三类关系均不可替代或对其他站点同样有效 |
| 非零组关系结果 | 031已查看测试期上的事后分层；负荷关系相对自环的非零组差为正，未作多重校正 | 可作探索性组件分层描述 | 完整MRG-GCN胜过TCN；确认性或多重校正后的非零组结论 |
| 目标敏感性 | SG-EXP-032固定原图与测试键，仅更换完成时刻截断代理目标 | 全局MAE排序在该替代目标下保持；非零组仍未优于TCN | 实测功率效度、替代目标重建图后的端到端稳健性 |
| MDP诊断 | L1联合参数敏感度、L2受检学生蒸馏、L3四格误差还原及JPL复核 | 修订关系权重解释、学生替代结论和指标报告重点 | 诊断指导改模已提高预测或运行收益 |
| 应用价值 | 固定代理轨迹、合成LP核验；真实案例状态为`MATERIALS_REQUIRED` | 界定采数、校准、离线评价和影子运行步骤 | 真实越限、安全改善、成本节约或直接调度能力 |

SG-EXP-031/032及JPL后续诊断均使用已查看的固定测试期，属于事后补充证据；不作为独立时期确认。全文据此区分总体模型比较、组件内增量、探索性分层与未验证的现场主张。

EPFL Level-3数据兼容性筛选（2026-10-21）只记录筛选失败和V1停止：严格`CCS + Session`连接为CCS1 1,129/1,129、CCS2 0/749，未进入形态比较；事后复合键1,878/1,878唯一匹配仅作映射诊断，含Energy，不是独立能量闭合。该筛选不新增模型、目标效度或应用主张，不改变上表结论层级；详见`revision-20261021-evidence/data-source-compatibility.md`。

- AdaptiveGraph：SG-EXP-004三个冻结检查点在匹配PyTorch 2.4.1/CUDA 12.1环境逐键通过；原生CPU存在top-k并列选边差异，固定CUDA邻接后CPU通过。原训练Git标识缺失、历史Mac环境偏差仍保留。报告：`experiment-reports/EXP-AdaptiveGraph-CUDA-20261015-no-training.md`及`outputs/analysis/AdaptiveGraph-CUDA-20261015/independent-verification.json`。
- SG-EXP-031：四配置×三种子同参数关系自环替换重训，支持负荷耦合和轮廓相似关系在当前JPL设置下的条件性整体MAE增量，行为共现关系区间跨零。审计中的次要分层显示，负荷关系相对自环的非零组种子平均差为0.004893 kWh/15 min，三个种子方向均为正；这是已查看测试期上的事后描述，未作该分层的多重校正，不等同完整模型胜过TCN（JPL非零组仍是TCN较低）。正文§3.7.2、表3-10；输入/容量/预算见表3-14。报告：`experiment-reports/SG-EXP-031-jpl-relation-controls.md`，数值见`outputs/analysis/SG-EXP-031-audit-20261015/audit.json`及`content-review-20261016-paired-reaudit/load-nonzero-crosscheck.json`。
- SG-EXP-032：完成时刻截断代理目标下全局MAE排序保持；新目标零值94.27%，非零组MRG-GCN较差。正文§3.8.4、表3-15；两种分层是边际评价，未作联合贡献分解。两项新训练均为已查看固定测试期上的补充。
- JPL可靠性：AUDIT-JPL-CAL-20261015复用313,120校准键与632,640测试键，标准/行为分层整体覆盖90.08%/90.11%，事件46.43%/45.88%，独立核验PASS。正文§5.3.5；报告`experiment-reports/EXP-JPL-calibration-20261015-no-training.md`。JPL尚缺L2与同硬件时延。
- AutoDL当前关闭状态以SG-EXP-032的控制台关机证据为准。SG-EXP-031结束时在线为历史事实，不作为当前实例状态；材料已回收并核验。

### ACN接口边界核验（2026-10-19）

| 站点 | 会话数 | 最早`connectionTime`（UTC） | 最晚`connectionTime`（UTC） | 下界外/上界外严格`where`计数 |
|---|---:|---|---|---:|
| Caltech | 31,424 | 2018-04-25 11:08:04 | 2021-09-14 01:52:37 | 0/0 |
| JPL | 33,638 | 2018-09-05 11:04:13 | 2021-09-14 05:43:39 | 0/0 |
| Office 1 | 1,683 | 2019-03-25 16:24:42 | 2021-09-13 21:21:51 | 0/0 |

6次严格`where`查询均返回HTTP 200且区间外计数为0，未发现2021年9月之后的接入时间记录；原脚本`earliest`/`latest`标签相对返回时间戳颠倒，已在`range_probe_reviewed.json`按时间顺序订正并留痕。该核验只认证`connectionTime`边界，不认证节点/字段完整性、标签成熟性或Office 1的既有分析使用史，不是完整新数据快照，也不证明其他数据源不可得；未下载会话时序。详见`revision-20261019-nontraining/data-decision.md`。


范围：登记2026-10-04—2026-10-05新增证据及正文落点。各项证据按来源、口径和独立数值复核；旧主实验和36次原结果保持。该映射不是全文证据认证。

| 主张ID | 主张 | 数据/实验 | 产物 | 状态与限制 |
|---|---|---|---|---|
| CLM-024-SUPPORT | 原均摊能量可延续到充电完成后；完成支持重构保持总量 | 原31,424会话、SG-DATA-00610节点；SG-EXP-024 | proxy-engineering/summary.json、session_support_audit.csv | 核验通过的重构敏感性；不是实测或模型MAE偏差 |
| CLM-024-CURRENT | 8个预定匹配会话的实测电流归一化形态不同于等片分摊 | DATA-024-CURRENT-PROBE；SG-EXP-024 | matched-current-probe/selection.json、sample_metadata.json、normalized_bin_shapes.csv | 便利样本、2质量失败；功率/电压缺失，不能推断实测kWh误差 |
| CLM-025-ROLL | 成熟标签回放下滚动校准缓解全体覆盖失配，事件仍明显不足 | SG-DATA-006，SG-EXP-019冻结预测；SG-EXP-025 | rolling-calibration/summary.csv、daily_quantiles.csv、独立verification | 14/28天固定、历史探索；不是保证或未见确认 |
| CLM-026-DECISION | 服务与容量约束的影子LP可执行合成可行性核验 | DATA-026-SYNTHETIC；SG-EXP-026 | charging-decision/shadow_plan.json、audit.json | 算法单元核验；真实案例MATERIALS_REQUIRED，无实际收益 |
| CLM-024-CURRENT-REPLAY-20261025 | 预定的8条ACN-Caltech历史会话中，归一化实测电流份额与均匀分摊代理份额存在会话内形态差异 | DATA-024-CURRENT-PROBE；ACN-CURRENT-SHAPE-REPLAY-20261025 | `docs/thesis/revision-20261025-practice/acn-current-shape-protocol.md`、`acn-current-shape-replay.json`、图5-9源清单；程序`scripts/figures/fig5_9_acn_current_shape.py` | 8/10条便利样本通过既有质量门禁；无电压/功率且处于训练年代，不比较模型预测，不推断实测能量误差或运行价值。完整模型比较仍基于代理目标，见表5-8 |
| CLM-027-GATE | 同参数节点级门控相对节点共享门控具有本测试期MAE增量 | SG-DATA-006；SG-EXP-027 | recovered六次来源、SG-EXP-027-time-block/summary.json与independent-verification.json | 三种子、七日及一日块方向一致；同上限与选模，实际轮次不同，不是旧协议消融或跨期保证 |
| CLM-028-JPL | JPL固定协议测试期内MRG-GCN整体MAE低于预登记的三项基线；节点级门控对照方向与Caltech一致 | SG-DATA-007-JPL；SG-EXP-028 | `experiment-reports/SG-EXP-028-jpl-independent-site-validation-report.md`及回收归档、预测键复核、配对区间CSV；`experiment-reports/EXP-JPL-calibration-20261015-no-training.md`及独立核验 | 12次正式运行；24个七日块、三组校正区间均高于零。TCN的RMSE、事件MAE、非零目标MAE较低。JPL独立校准已完成：总体覆盖约90.1%，事件覆盖约46%；同硬件时延仍未完成。同属ACN家族、年份重叠、目标为会话代理，不代表跨家族、未来时期或零样本迁移 |
| CLM-029-GATE-COMPOSITION | 两个既有测试期的节点级门控整体MAE点估计不由任一单节点单独决定 | SG-DATA-006/007；SG-EXP-027/028原始预测键；SG-EXP-029 | `experiment-reports/SG-EXP-029-node-composition-sensitivity.md`、逐键审计脚本、留一CSV/JSON | 两站各10次留一点估计均为正；事后同测试期分析，无留一区间/多重校正，不是独立验证，不证明每节点获益 |

上述分析产物位于`outputs/analysis/SG-EXP-*`；SG-EXP-027六次原工件位于`outputs/experiments/SG-EXP-027/recovered/`，SG-EXP-028归档及分析表位于本机训练交接工作区。正文映射：CLM-024在2.1.2，CLM-027在3.7.1、4.2.5及表3-9，CLM-029在3.7.1与结论，CLM-025在5.3.4及表5-3，CLM-026在5.4.4、式（5-7）及表5-8，CLM-028在摘要、1.4—1.6、2.1.3、3.6.3、3.8.2、结论与局限。方法组件证据对照见表3-13；本轮重排不新增图号。

## 2026-10-12 检查点复算的增补映射

| 原证据/正文 | 新复核材料 | 本轮结论与边界 |
|---|---|---|
| SG-EXP-019，表3-2 | `reproducibility-20261012/sg019.json` | 36/36现有检查点完整test前向通过；只在原事件时刻协议内解释 |
| CLM-027-GATE，表3-9 | `reproducibility-20261012/sg027.json` | 6/6通过；没有增加训练预算或新的确认时期 |
| CLM-028-JPL，表3-3 | `reproducibility-20261012/sg028.json` | 12/12锁定检查点通过；原整体MAE结论及指标边界沿用 |
| SG-EXP-002/003/004，表3-4三行 | `reproducibility-20261012/legacy.json` | TCN/MRG六次通过，AdaptiveGraph三次CPU前向未通过；原预测到指标全部算术一致，训练时源码仍未认证 |
| 上述21行MAE均值/样本标准差 | `paper-mae-archived-audit.json`、`paper-mae-forward-audit.json` | 原预测指标21/21行与论文一致；前向指标20/21行通过，不替换旧AdaptiveGraph原GPU数字 |

本轮总入口状态为FAIL（60/63前向通过），完整失败记录保留。可携带包及权限见`data-availability.md`和`reproducibility-20261012/README.md`。

## 2026-10-14 JPL L1/L3无训练复核

| 主张ID | 来源与定位 | 已支持范围 | 未支持范围 |
|---|---|---|---|
| CLM-AUD-JPL-L1-20261014 | SG-EXP-028三个冻结MRG；audit_jpl_mdp_20261014.py；§4.6.1–4.6.2、表4-7 | 七种替换三个种子均提高整体MAE；函数保持重参数化重现预测；联合配置敏感度 | β独立收益、三关系条件边际、所有分层均退化；事后分析未作确认性统计 |
| CLM-AUD-JPL-L3-20261014 | 同组原正式预测与冻结掩码；§4.6.3、表4-8 | 四格计数与加权MAE闭合；稀有格高单键误差、常态格多数累计误差 | 同时刻事件检测性能、因果归因、实际运行风险或收益 |
| CLM-AUD-BUDGET-20261014 | revision-20261014-evidence/input-capacity-budget.json；表3-13 | 12组主要配置、36运行的输入/容量/最佳与停止轮次可追溯 | 相同预算代表相同充分收敛、参数量代表推理效率 |

MDP判断变化汇总于表4-6，组件范围汇总于表3-13。新工件和独立核验见revision-20261014-evidence/README.md；L2尚未跨站。该历史映射截至2026-10-14；AdaptiveGraph后续CUDA核验见本文件当前入口。

## 本轮新增主张与工件

| 文献定位 | 正文位置 | 直接证据 | 支持范围与边界 |
|---|---|---|---|
| NEAR76-LITERATURE | §1.2表1-1、§1.2.3、§1.3 | 事实摘录：`content-review-20261019-paired/sources/NEAR76-factual-extract.md`；该摘录依据2026-10-17留存的出版社原文核验记录整理，明确其可读范围限于研究定位、方法框架、实验与结论相关部分，本轮未重新取得出版社全文（页面返回429）。 | Liang[76]已报告公开Boulder交易重构EV负荷上的直接/残差预测及指标依赖结果；本文不把一般会话重构代理预测或残差校正作为空白。其单场站内多节点关系、节点门控、关系替换重训与MDP差异用于定位本文问题，不支持跨文误差排名。 |

| 主张 | 正文 | 直接证据 | 权限 |
|---|---|---|---|
| CLM-031-RELATION | §3.7.2、表3-10、表3-13 | `experiment-reports/SG-EXP-031-jpl-relation-controls.md`；`outputs/analysis/SG-EXP-031-audit-20261015/audit.json`、`run-metrics.csv`、`paired-time-blocks.csv`（该目录为本机Git忽略输出）；配对非零复核`content-review-20261016-paired-reaudit/load-nonzero-crosscheck.json`。报告和配对复核文件当前在工作区未跟踪；已建立最小复算索引和入口（见2026-10-22当前入口）；完整复算仍须携带本地源/结果归档及冻结数据，不依赖Git文本单独完成。 | 两类邻接相对自环替换的条件性整体MAE增量；第三类不确定 |
| CLM-032-TARGET | §2.1.2、§3.8.4、表3-15 | SG-EXP-032目标审计、逐键预测、回收manifest | 固定图、共同键上的替代代理目标敏感性，不是实测效度 |
| CLM-JPL-INTERVAL | §5.3.5 | JPL-calibration-20261015/audit.json、independent-verification.json | 固定已查看测试期的独立校准经验覆盖，事件覆盖不足 |
| CLM-ADAPTIVE-CUDA | §3.6.1、§3.6.4 | AdaptiveGraph-CUDA-20261015独立核验及回收数组 | 匹配CUDA权重→预测复算通过，原生CPUtop-k选边机制；保留训练源码认证限制 |
