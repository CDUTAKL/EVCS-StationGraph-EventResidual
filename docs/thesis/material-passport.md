# 2026-10-04新增材料身份记录

该文件只覆盖本轮新增材料，不代替既有完整归档与图表manifest。

| 材料ID | 身份/来源 | 版本及完整性 | 权限 | 使用范围 |
|---|---|---|---|---|
| MAT-024-SUPPORT | 原会话主10节点及SG-DATA-006固定目标；脚本audit_proxy_engineering.py | sources.json与manifest.json；替代重构仅派生 | 原始数据不进入Git；只保留本地证据 | 支持范围/总量，不是实测负荷 |
| DATA-024-CURRENT-PROBE | ACN-Data Static公开历史Caltech会话；预定10个、8个质量通过 | selection.json、各通过文件URL/SHA256，元数据及派生份额manifest | 原文件不保存/再分发；许可需遵守官方条款 | 归一化电流形态，非实测能量、新时期或在线性能 |
| MAT-025-ROLLING | SG-EXP-019 MRG三种子冻结calibration/test及成熟时间张量 | 配置SG-EXP-025-rolling-calibration.json、sources与manifest；独立复核23,310条分位数 | 本地派生证据，无源工件改动 | 已查看历史上的成熟标签回放 |
| DATA-026-SYNTHETIC | 人工设定单车4片影子决策单元算例 | synthetic_parameters.json、shadow_plan.json、sources/manifest；枚举复核 | 完全合成，无真实车辆材料 | 算法可行性，不报告实际经济收益 |
| MAT-024-026-REPORT | EXP-024-026-no-training-supplement.md | 与实验registry/质量报告/指标定义映射 | 研究记录 | 2026-10-04经核验纳入正文2.1.2、5.3.7、5.5.4 |
| MAT-027-GATE | 同5090六次配对门控训练及完整归档 | 原归档SHA256为2afb6019b11808a2eca437f4590c68ba7f58752ad8af5cb5e1f229164c1cbb50；6/6独立PASS | 本地完整归档，权重与逐键预测不进入Git | 新协议节点门值差异，不替换旧成绩或原36次结果 |
| MAT-027-BLOCK | SG-EXP-027-time-block派生统计 | 新冻结配置、sources与manifest；两种聚合及百分位复算一致 | 派生摘要与脚本可复跑，原源文件只读 | 既有测试期条件性区间，不是跨站或未见确认 |

前轮保持论文哈希的说明对应重训前检查点；本轮经用户授权将补充证据写入正文并原位同步唯一DOCX，版本由Git保存，不新增日期后缀Word。原模型主结果和原phase2全部工件未修改。本轮无私人token或原始量测再发布材料。
