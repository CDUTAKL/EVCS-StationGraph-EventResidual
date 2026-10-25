# 新增补强证据映射

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

上述分析产物位于`outputs/analysis/SG-EXP-*`；SG-EXP-027六次原工件位于`outputs/experiments/SG-EXP-027/recovered/`，SG-EXP-028归档及分析表位于本机训练交接工作区。正文映射：CLM-024在2.1.2，CLM-027在3.7.1、4.2.5及表3-9，CLM-029在3.7.1与结论，CLM-025在5.3.7及表5-6，CLM-026在5.5.4、式（5-8）及表5-9，CLM-028在摘要、1.4—1.6、2.1.3、3.6.3、3.8.2、结论与局限。方法组件证据对照见表3-12；本轮重排不新增图号。

## 2026-10-12 检查点复算的增补映射

| 原证据/正文 | 新复核材料 | 本轮结论与边界 |
|---|---|---|
| SG-EXP-019，表3-2 | `reproducibility-20261012/sg019.json` | 36/36现有检查点完整test前向通过；只在原事件时刻协议内解释 |
| CLM-027-GATE，表3-9 | `reproducibility-20261012/sg027.json` | 6/6通过；没有增加训练预算或新的确认时期 |
| CLM-028-JPL，表3-3 | `reproducibility-20261012/sg028.json` | 12/12锁定检查点通过；原整体MAE结论及指标边界沿用 |
| SG-EXP-002/003/004，表3-4三行 | `reproducibility-20261012/legacy.json` | TCN/MRG六次通过，AdaptiveGraph三次CPU前向未通过；原预测到指标全部算术一致，训练时源码仍未认证 |
| 上述21行MAE均值/样本标准差 | `paper-mae-archived-audit.json`、`paper-mae-forward-audit.json` | 原预测指标21/21行与论文一致；前向指标20/21行通过，不替换旧AdaptiveGraph原GPU数字 |

本轮总入口状态为FAIL（60/63前向通过），完整失败记录保留。可携带包及权限见`data-availability.md`和`reproducibility-20261012/README.md`。
