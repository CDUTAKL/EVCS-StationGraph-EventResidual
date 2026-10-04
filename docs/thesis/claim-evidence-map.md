# 新增补强证据映射

范围：登记2026-10-04新增证据及正文落点。以下补充已按来源、口径和独立数值复核纳入正文，旧主实验和36次原结果保持；该映射不是全文证据认证。

| 主张ID | 主张 | 数据/实验 | 产物 | 状态与限制 |
|---|---|---|---|---|
| CLM-024-SUPPORT | 原均摊能量可延续到充电完成后；完成支持重构保持总量 | 原31,424会话、SG-DATA-00610节点；SG-EXP-024 | proxy-engineering/summary.json、session_support_audit.csv | 核验通过的重构敏感性；不是实测或模型MAE偏差 |
| CLM-024-CURRENT | 8个预定匹配会话的实测电流归一化形态不同于等片分摊 | DATA-024-CURRENT-PROBE；SG-EXP-024 | matched-current-probe/selection.json、sample_metadata.json、normalized_bin_shapes.csv | 便利样本、2质量失败；功率/电压缺失，不能推断实测kWh误差 |
| CLM-025-ROLL | 成熟标签回放下滚动校准缓解全体覆盖失配，事件仍明显不足 | SG-DATA-006，SG-EXP-019冻结预测；SG-EXP-025 | rolling-calibration/summary.csv、daily_quantiles.csv、独立verification | 14/28天固定、历史探索；不是保证或未见确认 |
| CLM-026-DECISION | 服务与容量约束的影子LP可执行合成可行性核验 | DATA-026-SYNTHETIC；SG-EXP-026 | charging-decision/shadow_plan.json、audit.json | 算法单元核验；真实案例MATERIALS_REQUIRED，无实际收益 |
| CLM-027-GATE | 同参数节点级门控相对节点共享门控具有本测试期MAE增量 | SG-DATA-006；SG-EXP-027 | recovered六次来源、SG-EXP-027-time-block/summary.json与independent-verification.json | 三种子、七日及一日块方向一致；同上限与选模，实际轮次不同，不是旧协议消融或跨期保证 |

上述分析产物位于`outputs/analysis/SG-EXP-*`，六次门控原工件位于`outputs/experiments/SG-EXP-027/recovered/`。正文映射：CLM-024在2.1.2，CLM-027在3.7.6、4.2.5及表3-10，CLM-025在5.3.7及表5-6，CLM-026在5.5.4、式（5-8）及表5-9；摘要和结论同步。无新增图号。
