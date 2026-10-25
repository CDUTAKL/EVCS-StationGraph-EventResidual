# 论文评分项目规则

数值量表固定为`EVCS-THESIS-CONTENT-1.0`：12项、原始满分90、每项0.5分步长；显示分为原始总分÷90×100。执行协议为`EVCS-THESIS-REVIEW-2.0`。本地数值口径优先于全局skill中“12项满分100”的遗留说明。

## 主评与系统维护角色

读取`scoring/README.md`、`scoring/protocol-v2.md`、`scoring/criterion-anchors-v2.json`、`scoring/history.json`和`scoring/publication-status.json`。历史记录原样保留，当前发布资格以状态文件为准。

正式评分复用本地硕士盲审、完整性检查和最终证据核验技能。使用schema_version=2及配对校准/配对修订模板，发布前执行`python3 scripts/audit_thesis_content_score.py 评分.json --publish`。基础记录`valid`不等于发布资格。

正式评分组包前先运行`python3 scripts/prepare_thesis_review.py --project . --config docs/thesis/scoring/review-preparation.json --out docs/thesis/review-preparation-日期/run序号 --cache-dir .cache/thesis-review --run-checks --freeze`。检查来源阅读声明绑定的证据SHA、登记范围和影响索引；任何阻断或未登记材料都必须先处理。缓存仅复用相同输入闭包的确定性计算，不替代三视角完整阅读、法证裁定、`--publish`验证或Word/WPS全页视觉验收。新证据必须登记到配置，不能因为旧包完整而自动视为已覆盖。

已有旧稿与记录时，不能把全部指标重设baseline。评价依据未变，论文修订效应为0。新发现若旧稿也存在，须同时重评旧稿，分别报告校准效应和修订效应；下调须指出具体错误、证据失效或支撑变化，不能仅称“更严格”。

问题用稳定ID、主要归属及独立跨项理由。未核实担忧不能直接扣分。不因缺实测/新数据/新算子/部署而在理论、工作量等指标重复计价；按论文实际主张及专业硕士标准评价。修订严重度按核实问题形成，不由数字分段自动产生。

## 隔离评阅者角色

若任务指定为独立/隔离评阅者，只读任务给定的冻结材料白名单、`rubric.json`、`criterion-anchors-v2.json`和`reviewer-instructions-v2.md`。不要打开含历史分数的评分README、history、publication-status、原评分表或既往评阅。主评负责读取这些治理材料；隔离评阅者不执行上述主评的历史读取步骤。

明确记录上下文ID和历史分数是否暴露。每位评阅者使用相同12项权重及相同一对稿件，保存原始报告和机器可读分项；总分由程序相加。不得声称AI视角是现实专家，或把评阅分数范围当统计置信区间。

## 通用边界

每项有正文位置、实际读过的证据和理由；材料不足记N/A并暂缓总分。封面、签名、用户暂缓的致谢/成果页、Word分页、图像有效PPI与全页视觉验收另列交付门槛；图表内容和单位错误仍属内容。校验程序只能检查记录、算术和配对约束，不能代替科学核验。
