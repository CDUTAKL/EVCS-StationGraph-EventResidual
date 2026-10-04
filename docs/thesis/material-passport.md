# 2026-10-04新增材料身份记录

该文件只覆盖本轮新增材料，不代替既有完整归档与图表manifest。

| 材料ID | 身份/来源 | 版本及完整性 | 权限 | 使用范围 |
|---|---|---|---|---|
| MAT-024-SUPPORT | 原会话主10节点及SG-DATA-006固定目标；脚本audit_proxy_engineering.py | sources.json与manifest.json；替代重构仅派生 | 原始数据不进入Git；只保留本地证据 | 支持范围/总量，不是实测负荷 |
| DATA-024-CURRENT-PROBE | ACN-Data Static公开历史Caltech会话；预定10个、8个质量通过 | selection.json、各通过文件URL/SHA256，元数据及派生份额manifest | 原文件不保存/再分发；许可需遵守官方条款 | 归一化电流形态，非实测能量、新时期或在线性能 |
| MAT-025-ROLLING | SG-EXP-019 MRG三种子冻结calibration/test及成熟时间张量 | 配置SG-EXP-025-rolling-calibration.json、sources与manifest；独立复核23,310条分位数 | 本地派生证据，无源工件改动 | 已查看历史上的成熟标签回放 |
| DATA-026-SYNTHETIC | 人工设定单车4片影子决策单元算例 | synthetic_parameters.json、shadow_plan.json、sources/manifest；枚举复核 | 完全合成，无真实车辆材料 | 算法可行性，不报告实际经济收益 |
| MAT-024-026-REPORT | EXP-024-026-no-training-supplement.md | 与实验registry/质量报告/指标定义映射 | 研究记录 | 正文纳入前待审核 |

真实论文与唯一DOCX此次均保持原哈希，未新增日期后缀Word。原模型主结果和原phase2全部工件未修改。本轮无私人token、远端账户或原始量测再发布材料。
