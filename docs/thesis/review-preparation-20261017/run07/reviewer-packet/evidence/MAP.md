# 新增补强证据映射

## 当前证据状态（2026-10-16统一修订）

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

- AdaptiveGraph：SG-EXP-004三个冻结检查点在匹配PyTorch 2.4.1/CUDA 12.1环境逐键通过；原生CPU存在top-k并列选边差异，固定CUDA邻接后CPU通过。原训练Git标识缺失、历史Mac环境偏差仍保留。报告：`experiment-reports/EXP-AdaptiveGraph-CUDA-20261015-no-training.md`及`outputs/analysis/AdaptiveGraph-CUDA-20261015/independent-verification.json`。
- SG-EXP-031：四配置×三种子同参数关系自环替换重训，支持负荷耦合和轮廓相似关系在当前JPL设置下的条件性整体MAE增量，行为共现关系区间跨零。审计中的次要分层显示，负荷关系相对自环的非零组种子平均差为0.004893 kWh/15 min，三个种子方向均为正；这是已查看测试期上的事后描述，未作该分层的多重校正，不等同完整模型胜过TCN（JPL非零组仍是TCN较低）。正文§3.7.2、表3-11；输入/容量/预算见表3-14。报告：`experiment-reports/SG-EXP-031-jpl-relation-controls.md`，数值见`outputs/analysis/SG-EXP-031-audit-20261015/audit.json`及`content-review-20261016-paired-reaudit/load-nonzero-crosscheck.json`。
- SG-EXP-032：完成时刻截断代理目标下全局MAE排序保持；新目标零值94.27%，非零组MRG-GCN较差。正文§3.8.4、表3-15；两种分层是边际评价，未作联合贡献分解。两项新训练均为已查看固定测试期上的补充。
- JPL可靠性：AUDIT-JPL-CAL-20261015复用313,120校准键与632,640测试键，标准/行为分层整体覆盖90.08%/90.11%，事件46.43%/45.88%，独立核验PASS。正文§5.3.5；报告`experiment-reports/EXP-JPL-calibration-20261015-no-training.md`。JPL尚缺L2与同硬件时延。
- AutoDL当前关闭状态以SG-EXP-032的控制台关机证据为准。SG-EXP-031结束时在线为历史事实，不作为当前实例状态；材料已回收并核验。


范围：登记2026-10-04—2026-10-05新增证据及正文落点。各项证据按来源、口径和独立数值复核；旧主实验和36次原结果保持。该映射不是全文证据认证。

| 主张ID | 主张 | 数据/实验 | 产物 | 状态与限制 |
|---|---|---|---|---|
| CLM-024-SUPPORT | 原均摊能量可延续到充电完成后；完成支持重构保持总量 | 原31,424会话、SG-DATA-00610节点；SG-EXP-024 | proxy-engineering/summary.json、session_support_audit.csv | 核验通过的重构敏感性；不是实测或模型MAE偏差 |
| CLM-024-CURRENT | 8个预定匹配会话的实测电流归一化形态不同于等片分摊 | DATA-024-CURRENT-PROBE；SG-EXP-024 | matched-current-probe/selection.json、sample_metadata.json、normalized_bin_shapes.csv | 便利样本、2质量失败；功率/电压缺失，不能推断实测kWh误差 |
| CLM-025-ROLL | 成熟标签回放下滚动校准缓解全体覆盖失配，事件仍明显不足 | SG-DATA-006，SG-EXP-019冻结预测；SG-EXP-025 | rolling-calibration/summary.csv、daily_quantiles.csv、独立verification | 14/28天固定、历史探索；不是保证或未见确认 |
| CLM-026-DECISION | 服务与容量约束的影子LP可执行合成可行性核验 | DATA-026-SYNTHETIC；SG-EXP-026 | charging-decision/shadow_plan.json、audit.json | 算法单元核验；真实案例MATERIALS_REQUIRED，无实际收益 |
| CLM-027-GATE | 同参数节点级门控相对节点共享门控具有本测试期MAE增量 | SG-DATA-006；SG-EXP-027 | recovered六次来源、SG-EXP-027-time-block/summary.json与independent-verification.json | 三种子、七日及一日块方向一致；同上限与选模，实际轮次不同，不是旧协议消融或跨期保证 |
| CLM-028-JPL | JPL固定协议测试期内MRG-GCN整体MAE低于预登记的三项基线；节点级门控对照方向与Caltech一致 | SG-DATA-007-JPL；SG-EXP-028 | `experiment-reports/SG-EXP-028-jpl-independent-site-validation-report.md`及回收归档、预测键复核、配对区间CSV | 12次正式运行；24个七日块、三组校正区间均高于零。TCN的RMSE、事件MAE、非零目标MAE较低；同属ACN家族、年份重叠、目标为会话代理，JPL区间/时延未完成，不代表跨家族、未来时期或零样本迁移 |
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

| 主张 | 正文 | 直接证据 | 权限 |
|---|---|---|---|
| CLM-031-RELATION | §3.7.2、表3-11、表3-13 | SG-EXP-031实验报告；audit.json与逐种子/块级CSV | 两类邻接相对自环替换的条件性整体MAE增量；第三类不确定 |
| CLM-032-TARGET | §2.1.2、§3.8.4、表3-15 | SG-EXP-032目标审计、逐键预测、回收manifest | 固定图、共同键上的替代代理目标敏感性，不是实测效度 |
| CLM-JPL-INTERVAL | §5.3.5 | JPL-calibration-20261015/audit.json、independent-verification.json | 固定已查看测试期的独立校准经验覆盖，事件覆盖不足 |
| CLM-ADAPTIVE-CUDA | §3.6.1、§3.6.4 | AdaptiveGraph-CUDA-20261015独立核验及回收数组 | 匹配CUDA权重→预测复算通过，原生CPUtop-k选边机制；保留训练源码认证限制 |
