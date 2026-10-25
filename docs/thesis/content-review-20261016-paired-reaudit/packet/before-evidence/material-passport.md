# 2026-10-04新增材料身份记录

该文件只覆盖本轮新增材料，不代替既有完整归档与图表manifest。

| 材料ID | 身份/来源 | 版本及完整性 | 权限 | 使用范围 |
|---|---|---|---|---|
| DATA-JPL-METADATA-20261005 | 官方JPL普通会话API全量必要元数据，337页33,638会话 | acquisition逐页响应哈希；本地快照SHA256 68480c71451dfaa0e2ca3a27cefb2fa229c76eac31fc541ccef56af7a9af3af4；52设备/52车位映射 | 本地教育研究；未存用户字段或令牌；原始记录不进Git，再分发未确认 | 外部场站代理任务来源，不认证实测功率/采集在线率 |
| SG-DATA-007-JPL | 10训练期筛选车位，事件时间输入、事后代理目标 | dataset SHA256 1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af；1,060,960行节点时间格独立核验；完整manifest和身份/节点筛选记录 | 张量只本地研究及后续授权云端处理，不进Git | 另一场站重新训练的固定数据资产，非真正新时期/零样本迁移 |
| MAT-JPL-PREREG-20261005 | SG-EXP-028冻结协议与比较设计 | 配置、方案及代码/来源摘要见JPL-validation-freeze-20261005.json；4模型×3种子共12次 | 可复核研究设计，不含个人数据 | 预登记材料；性能证据见MAT-JPL-RESULT-20261005及正式实验报告 |
| MAT-JPL-RESULT-20261005 | SG-EXP-028十二次正式训练、测试预测和派生统计 | 12/12运行通过；归档SHA256 `50e7beb581c7cd4e3099fa0661d5a1cf3c1f79935516739eae693ba0234d4966`；数据张量SHA256与SG-DATA-007一致；逐键复核见实验报告 | 仅本地研究；原始会话、检查点和逐键预测不进入公开附件 | JPL固定协议点预测比较与条件时间块差异；不是实测功率、零样本迁移或未来时期证据 |
| DATA-JPL-FEASIBILITY-20261004 | ACN-Data-Static JPL固定156条探查 + 官方API元数据跨期抽样113条及1个时序页 | 静态commit abb7cf15cc7108913e965d4375cc7270d532b65f；API报33,638条，抽样50个stationID与静态52候选中50个字符串匹配；`api_authenticated_crosswalk_probe.json`含逐页响应哈希，manifest记录脚本/摘要SHA256；无原始API记录 | 仅本地研究核查；教育研究条款；再分发待明确；令牌未保存 | 外部站点候选；非全量节点盘点，时序页0/25有电流，不是实测kW、正式跨站或新时期性能验证 |
| MAT-024-SUPPORT | 原会话主10节点及SG-DATA-006固定目标；脚本audit_proxy_engineering.py | sources.json与manifest.json；替代重构仅派生 | 原始数据不进入Git；只保留本地证据 | 支持范围/总量，不是实测负荷 |
| DATA-024-CURRENT-PROBE | ACN-Data Static公开历史Caltech会话；预定10个、8个质量通过 | selection.json、各通过文件URL/SHA256，元数据及派生份额manifest | 原文件不保存/再分发；许可需遵守官方条款 | 归一化电流形态，非实测能量、新时期或在线性能 |
| MAT-025-ROLLING | SG-EXP-019 MRG三种子冻结calibration/test及成熟时间张量 | 配置SG-EXP-025-rolling-calibration.json、sources与manifest；独立复核23,310条分位数 | 本地派生证据，无源工件改动 | 已查看历史上的成熟标签回放 |
| DATA-026-SYNTHETIC | 人工设定单车4片影子决策单元算例 | synthetic_parameters.json、shadow_plan.json、sources/manifest；枚举复核 | 完全合成，无真实车辆材料 | 算法可行性，不报告实际经济收益 |
| MAT-024-026-REPORT | EXP-024-026-no-training-supplement.md | 与实验registry/质量报告/指标定义映射 | 研究记录 | 2026-10-04经核验纳入正文2.1.2、5.3.7、5.5.4 |
| MAT-027-GATE | 同5090六次配对门控训练及完整归档 | 原归档SHA256为2afb6019b11808a2eca437f4590c68ba7f58752ad8af5cb5e1f229164c1cbb50；6/6独立PASS | 本地完整归档，权重与逐键预测不进入Git | 新协议节点门值差异，不替换旧成绩或原36次结果 |
| MAT-027-BLOCK | SG-EXP-027-time-block派生统计 | 新冻结配置、sources与manifest；两种聚合及百分位复算一致 | 派生摘要与脚本可复跑，原源文件只读 | 既有测试期条件性区间，不是跨站或未见确认 |

前轮保持论文哈希的说明对应重训前检查点；本轮经用户授权将补充证据写入正文并原位同步唯一DOCX，版本由Git保存，不新增日期后缀Word。原模型主结果和原phase2全部工件未修改。本轮无私人token或原始量测再发布材料。

## 2026-10-12 新增复算与交接材料

| 材料ID | 来源/完整性 | 核验结论 | 权限与范围 |
|---|---|---|---|
| MAT-CHECKPOINT-REPLAY-20261012 | 三个协议、四组实验原权重/配置/冻结张量；1,022文件MANIFEST SHA256 `1e881063a63addbf6a627d14fabe2c372d507a1fe6465f8ae8aaa5c0a37c9f62` | 60/63 test前向通过；63/63原预测指标复算通过；21行论文MAE均值/样本SD一致 | 本地授权研究；不公开权重、预测或张量；不等同训练复现 |
| MAT-ADAPTIVE-REPLAY-GAP-20261012 | 旧SG-EXP-004三种子及`adaptive-topk-diagnostic.json` | CPU前向失败如实保留；top-k并列值是候选解释，未作CUDA确认 | 不修改原结果；不能计为前向通过；训练时源码认证仍缺 |

交接索引为`reproducibility-20261012/README.md`；原预测、模型与历史评分文件保持原证据身份，未用当前PCMCI结果填补历史完整p矩阵。

| 交付材料 | 身份 | 已核验范围 | 待办范围 |
|---|---|---|---|
| MAT-THESIS-DOCX-20261012 | 正式论文稳定文件；SHA256 `489ebf1b68a47f0184b4c1ec34c1ac99a79cdc685de490a1d59af55dcc60df79`；源MD SHA256 `21e54e81244e6dc07721dfb1395fe31ba7ba71f7e8d99de805d8ebf61e021350` | 本轮文字同步、27公式序号、46图片字节顺序通过 | 本轮目录刷新及WPS分页视觉验收未执行；不声明完整格式验收通过 |
