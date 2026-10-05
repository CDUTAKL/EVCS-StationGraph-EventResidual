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

上述分析产物位于`outputs/analysis/SG-EXP-*`；SG-EXP-027六次原工件位于`outputs/experiments/SG-EXP-027/recovered/`，SG-EXP-028归档及分析表位于本机训练交接工作区。正文映射：CLM-024在2.1.2，CLM-027在3.7.6、4.2.5及表3-10，CLM-025在5.3.7及表5-6，CLM-026在5.5.4、式（5-8）及表5-9，CLM-028在摘要、1.4—1.6、2.1.3、3.8.2、结论与局限。新增表3-12；无新增图号。
