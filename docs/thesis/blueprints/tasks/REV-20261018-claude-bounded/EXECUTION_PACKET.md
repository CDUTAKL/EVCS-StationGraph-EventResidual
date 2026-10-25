# Claude Code执行任务包

任务编号：REV-20261018-claude-bounded
任务类型：content_revision；对应12流程阶段：8/10/11
目标：按已有证据收束主线与重复表达，准备公平门控预算补验，实查官方新数据入口；不训练、不评分、不更新正式Word。

## 开始前
只依据本任务包的冻结摘录和蓝图列出的材料工作。不要从聊天历史、归档计划或整份实验登记表重建当前状态。正文源稿为`docs/thesis/thesis-manuscript.md`。

## 可写范围
- `docs/thesis/thesis-manuscript.md`
- `docs/thesis/revision-20261018-claude-review/change-report.md`
- `docs/thesis/revision-20261018-claude-review/gate-budget-plan.md`
- `docs/thesis/revision-20261018-claude-review/gate-budget-contract.json`
- `docs/thesis/revision-20261018-claude-review/data-availability-check.md`
- `docs/thesis/revision-20261018-claude-review/consistency-review.md`
- 以上路径是任务约束和事后审计范围，不是操作系统级文件隔离；不要写入未列路径，也不要把Git忽略路径当作可审计输出。

## 锁定主张与口径
- 所有数值、表格、公式、引文、实验结果保持不变。只修改scope.json允许的标题对应正文段落；不改标题。
- 负荷关系相对自环的非零组增量与完整模型非零组未胜TCN同时成立；已查看时期、未实测、预算触顶、蒸馏容量限制保留。
- 不读取历史评分，不评分，不预设涨分；不运行训练/SSH/远端命令；不访问凭据或下载原始会话。

## 执行步骤
1. 读取指定范围与技能，完成简洁、学术化的局部收束，中文英文摘要对应。优先减少重复边界句，不堆字；无需为改而改。
2. 在change-report.md记录逐节前后变化与理由；consistency-review.md记录主张—证据—结论闭合及未完成项，明确JPL独立校准已完成，不重复列旧问题。
3. 按120轮/耐心16、两配置各3种子、从头训练准备gate-budget-plan.md及JSON合同。JSON顶层必须有training_started:false,max_epochs:120,patience:16,seeds:[2024,2025,2026],variants两个配置；写明数据/源码哈希待冻结清单、成对初始化、32,714参数、输入与调参选模一致、全局/非零/事件评价、统计与停止规则、失败保留、回收验收后关机。说明同时改变轮数上限和耐心，是共同预算策略敏感性，不是单独轮数效应。检查现有入口能否直接支持JPL；不能支持则列具体待实现项，不虚构ready_to_run。
4. 通过WebFetch读取https://ev.caltech.edu/dataset及页面明确的站点/下载入口，实查是否能得到晚于既有2021年记录的元数据。仅网页/公开元数据，不登录、不用API令牌、不下载会话、不按结果选时期。若页面无记录计数/日期，明确未知；不得把网页说明当作新数据已可用。记录实际URL、读取范围、失败信息和下一步。
5. 仅运行checks_to_run的唯一命令；禁止自行ls/shasum或其他Bash。检查通过后填写execution-report.json，记录网页与技能、改动与限制，不宣称验收。完成后停止等待操作者/exit。

## 指定Claude Code Skills
- 本任务明确要求调用`research-paper-writing` skill；请通过Claude Code的Skill工具加载并遵循其适用步骤。
- 只加载上面列出的skill；不要调用未列出的skill。
- skill中的相对路径不要按项目根目录解释：先解析skill真实目录（`realpath ~/.claude/skills/<name>`）；skill自身资源在其目录下，kit级脚本/文档在kit根目录下。
- 命名skill不会自动授予Bash；若skill步骤需要运行脚本，蓝图必须把对应命令列入`checks_to_run`，否则只做只读分析并在报告中说明。
- skill的`SKILL.md`和引用资源已在prepare时冻结哈希；若发现资源缺失或被改动，停止并报告，不要创建空占位文件。

## 验收条件
- 范围、数字、公式、表格、引用检查通过
- 正文主线准确且凝练；未改变证据权限
- 预算合同可审查但不宣称已完成训练或获益
- 新数据结论来自实际可见网页或如实记录阻断
- 执行报告完整且无越界改动

## 操作权限
- 训练：False；远程执行：False；联网：True；Git提交/暂存：False。
- 除非明确列入允许范围，不得启动训练、远程作业、联网采集、Git暂存/提交或覆盖正式Word。不得使用绕过权限的启动方式。
- 不得修改`.git/`、`.claude/settings*.json`、凭据文件或交接控制文件；如需修改，停止并报告。
- 只运行蓝图列出的检查：python3 tmp/check_claude_revision_20261018.py。未列检查时不要新增或运行测试。
- Bash网络主机白名单：ev.caltech.edu。空数组表示Bash无网络；WebSearch/WebFetch须单独取得工具权限。

## 冻结的证据摘录

### 直接证据

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "摘  要"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
# 摘  要

场站内充电节点负荷稀疏且异质，全局误差未必反映活跃片段表现。本文以公开会话记录重构的15 min节点代理能量为对象，检验站内关系与节点级门控的预测增量，并分析这些证据如何影响模型选择和误差报告。主要比较采用Caltech事件时刻协议与JPL另一场站重新拟合协议，均假定行为计数在时间片末可见。

本文构建负荷耦合、行为共现和轮廓相似关系图，以多关系门控图卷积网络（MRG-GCN）融合时间表示与节点关系；并用三层机制诊断协议（MDP）分别检验冻结参数敏感度、受检时序学生的替代表现和事件—规则四格误差构成。本文的主要贡献是对站内关系增量及其解释范围进行受控检验，不主张基础图卷积、门控或时序网络组合为算法首创。

Caltech事件时刻协议下，MRG-GCN整体MAE较容量近似TCN低16.1%，但完整AGCRN更低，且MRG-GCN在非零目标和标签事件组均未优于TCN。JPL中MRG-GCN整体MAE较三项预登记基线低2.64%—3.36%，但TCN的RMSE、事件及非零目标误差更低。节点级门控在两场站相对同参数共享门控的整体MAE分别低2.69%和2.71%；共享门控各有一个种子触及60轮上限，结论限于该预算。

JPL关系替换重训支持负荷耦合和轮廓相似关系相对自环的条件性整体MAE增量，行为共现关系仍不确定。负荷关系相对自环的非零组正向差异属于未校正事后分层；完整MRG-GCN非零组仍未胜过TCN。完成时刻截断保持全局排序，但非零组未改善。以上补充分析复用已查看测试期。

MDP将参数敏感度、特定学生的替代表现和误差构成分开解释，修正了关系取舍、替代性判断与分层报告重点。现有结果可支持节点代理负荷模型筛选和后续采数安排；实测功率效度、输入到达时延和运行收益仍需同步量测及现场评价。

关键词：充电节点短期负荷预测；LRE；MRG-GCN；MDP；节点代理负荷

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "Abstract"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
# Abstract

Charging-node proxy energy is sparse and heterogeneous, so aggregate error can conceal performance on active intervals. This thesis studies 15-minute node-level energy reconstructed from public charging sessions. It tests whether within-station relations and node-specific gates add predictive value, and what decisions those comparisons support. Main analyses use Caltech's event-time protocol and a separately refitted JPL site, assuming behavioral counts are available at interval end.

MRG-GCN combines temporal representations with load-coupling, behavioral co-occurrence, and profile-similarity relations. At Caltech, its overall MAE is 0.03890 kWh/15 min, 16.1% below a capacity-near TCN, but full AGCRN performs better and MRG-GCN does not lead on nonzero or event targets. At JPL, its overall MAE is 2.64%–3.36% below three preregistered baselines, while TCN has lower RMSE and lower nonzero- and event-target errors. Node-specific gates reduce overall MAE by 2.69% and 2.71% at Caltech and JPL, respectively; one shared-gate seed per site reaches the 60-epoch limit, so this result is budget-bound.

JPL relation-replacement retraining supports conditional overall-MAE gains over self-loop replacements for load coupling (1.82%) and profile similarity (1.52%); the behavioral relation remains uncertain. A post-hoc nonzero-target difference for load coupling is exploratory and does not imply that the complete model beats TCN on nonzero targets. Completion-time target truncation preserves global ranking but not nonzero-target performance. These supplements reuse inspected test periods.

MDP separates parameter sensitivity, a tested student's replacement performance, and error composition. The distinctions refine relation choice, model replacement claims, and subgroup reporting, but do not show that diagnosis-guided model changes improve prediction. The findings can guide node-proxy-load model screening and data collection; meter validity, reporting delays, and operational benefits require synchronized measurements and field evaluation.

Keywords: short-term charging-node load forecasting; LRE; MRG-GCN; MDP; proxy load

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "1.3 现有研究不足"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 1.3 现有研究不足

现有研究已包括会话重构EV负荷的残差预测[76]、站间关系建模和住宅用户图门控。由此，本文研究缺口进一步限定为：在会话重构的站内节点代理负荷任务中，哪些统计关系相对自环具有可复核的条件增量，以及参数干预、替代学生和误差分层能够支持何种机制判断。围绕这一范围，还需回答三个相互关联的问题。

（1）如何表示并检验站内节点差异。多类统计关系可以刻画负荷同步、行为共现和轮廓相似，但关系图本身不保证带来预测增益；关系融合和节点差异门控的作用需要在明确协议下比较。

（2）如何区分模型的观察信号、功能依赖和性能增量。门控权重可描述参数分配，冻结替换可检验既有配置的敏感度，蒸馏可检验特定学生设置的替代尝试；这些证据回答的问题不同，均不能单独确立因果机制。还需把整体误差拆至事件与稳定窗口，说明改进发生于哪些样本。

（3）如何界定行为信息和可靠性结论。目标侧事件标签、回溯规则和预测时可见行为输入具有不同的信息条件。代理负荷中的零值和稀有高误差窗口也要求分别报告总体误差与事件表现；否则，事后分层或全局均值都可能掩盖模型的适用边界。

上述三项研究问题及其与相关研究方向的对应关系见图1-1。

![研究不足映射](../../outputs/figures/fig1_1_research_gap_map.png)

**图1-1 研究方向与本文关注不足的对应关系**  从时间序列预测、多节点关系建模、行为事件建模和机制解释四个方向，归纳本文所关注的站内节点关系语义、结构贡献边界、双事件口径和诊断证据链问题。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "1.4 研究目标与主要内容"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 1.4 研究目标与主要内容

本文关注站内关系和节点差异门控对代理负荷预测的增量，并以MDP区分参数敏感度、受检模型替代与误差构成。贡献在于提供任务内的受控比较及其证据边界，不主张基础算子或通用诊断工具首创。

（1）数据与协议。审计会话字段和节点标识，重构15 min节点代理能量，明确输入可见时点、标签成熟条件和时间切分；分析稀疏性与节点异质性，为关系构建和分层评价提供依据。

（2）预测与受控增量。构建LRE三关系图，以MRG-GCN融合时间表示和关系消息。在Caltech事件时刻与JPL重拟合协议中比较节点级和共享门控；在JPL逐一以自环替换关系邻接，在Caltech更换为完成时刻截断目标重训。分别检验模型整体表现、组件增量和目标敏感性，并以非零组和事件组评价约束总体结论。

（3）机制诊断。通过L1冻结β替换及重参数化分析、L2受检时序学生蒸馏和L3事件—规则四格分解，区分联合配置依赖、特定替代尝试与误差来源；在JPL既有检查点上事后复核L1/L3。据此修订关系解释、学生替代结论和分层报告重点；诊断指导改模的收益尚待检验。

（4）可靠性与使用条件。开展方向性候选筛查、独立校准与成熟标签滚动回放，并用固定预测轨迹和合成约束例检查运行接口。结果按代理目标、固定测试期和计量材料边界解释；场站间比较限于ACN同源、时期重叠的重新拟合任务。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "1.7 本章小结"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 1.7 本章小结

本章将研究问题归纳为站内关系预测、组件增量辨识和分层诊断。后续章节依次完成数据与时点定义、受控预测比较、诊断判断及可靠性分析，重点考察总体收益是否延伸至非零目标与事件样本。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "3.8.1 方法组件与目标敏感性证据综合"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
### 3.8.1 方法组件与目标敏感性证据综合

表3-13按对照类型归纳组件证据及其权限。节点门控和两类关系仅在所检协议、预算与基线下获得整体增量证据；负荷关系的非零组差异仍属探索性结果。基础图卷积、TCN和门控算子沿用已有方法。

**表3-13 方法组件与目标敏感性证据、贡献范围**

| 组件 | 直接证据及定位 | 可以支持的判断 | 尚未建立的判断 |
|---|---|---|---|
| LRE三关系图 | 表3-2主要比较、附表A-1单关系及同参数自环；表3-10旧协议关系子集；表3-11 JPL同参数关系自环替换 | 跨节点关系路径在事件时刻协议下有整体MAE价值；JPL同参数重训练支持负荷耦合和轮廓相似关系相对自环替换的条件性整体MAE增量 | 行为关系增量尚不确定；负荷关系非零组结果属未校正事后描述，不等同完整模型胜过TCN；旧协议子集仍受容量差异限制，也未证三类关系普遍必要 |
| 完成时刻截断目标（032） | 表3-15；原Caltech事件时刻目标与替代目标在共同测试键上分别比较 | 两种会话代理目标下，MRG-GCN相对容量近似TCN的全局MAE排序方向一致 | 替代目标零值占94.27%，非零目标组MRG-GCN误差更高；不能据此确认实测功率效度、活跃负荷优势或替代拓扑下的端到端稳健性 |
| 关系级$\beta$ | 表4-2、表4-3冻结替换；3.7.2节等权重训练；4.2.5节重参数化 | 已训练$\beta$与关系变换的联合配置有功能敏感度 | $\beta$独立正增益、权重大小等同关系贡献或关系不可替代 |
| 节点级$G$ | 表3-9 Caltech同参数配对；表3-3 JPL同参数配对 | 当前预算及选模规则下，保留节点差异使整体MAE分别低2.69%和2.71% | 更长预算下差异仍保持、所有样本层面占优或站点普遍优势 |
| 精炼与跨层融合 | 附表A-1删除变体及3.7.2节时间块分析 | 描述所检配置的优化响应；跨层拼接去除的差异区间跨零 | 所有模块分别必需或均有稳定独立增量 |
| 关系随机失活 | 表3-10的$p=0/0.2/0.4$比较 | 所检小网格未见实质收益，主配置关闭 | 对其他数据与失活设置普遍无效 |
| MDP诊断组织 | 第4章参数干预、受检学生与四格还原；表4-6判断变化 | 修正关系解释、替代性判断与误差报告口径 | 新的预测收益、现实因果机制或已验证的运行收益 |

注：组件证据来自不同实验协议，表中不把冻结参数替换、删除后重训练和同参数配对合并解释。基础TCN、图卷积及门控算子采用已有方法；本文新增价值按任务化构造、所检增量及诊断判断分别陈述。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "3.9 本章小结"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 3.9 本章小结

Caltech与JPL结果均显示MRG-GCN在所检配置下具有整体MAE优势，但该优势没有稳定延伸至非零和事件样本；Caltech完整AGCRN的整体MAE更低。受控比较支持节点门控在当前预算下，以及JPL负荷和轮廓关系相对自环替换的条件性整体增量；行为关系仍不确定。完成时刻截断后全局排序保持，非零组仍未改善。回溯结果与参数干预作为补充证据，由第4章解释。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "4.5 MDP诊断结果与适用边界"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 4.5 MDP诊断结果与适用边界

MDP修正了三项判断：L1将$\beta$敏感度解释为$\beta$与关系变换共同决定的联合配置变化；L2将图结构不可替代收窄为当前受检学生未逼近教师；L3要求并列报告困难格单键误差和常态格总误差贡献。表4-6据此列出论文报告与后续研究取舍。

**表4-6 MDP证据引起的研究判断与后续决策**

| 层次 | 原解释 | 诊断结果 | 修订后的研究判断与可支持的决策 |
|---|---|---|---|
| L1 | 较大$\beta$代表关系更重要；冻结替换退化证明其独立增益 | 冻结替换显示联合配置敏感；函数保持重参数化说明$\beta$单独不具可识别的“重要性”；JPL未重训等权配置 | 不按$\beta$删减关系，也不称其独立增益。关系取舍另依据3.7.2节自环替换：负荷与轮廓关系获条件增量证据，行为关系仍不确定；支持后续复核这三种关系，而非按权重排序 |
| L2 | 蒸馏学生未逼近教师，说明图结构不可替代 | 当前TCN学生未弥合差距；参数量、输入路径及损失设置不匹配；JPL未复做L2 | 结论限于所检学生。当前主张不涉及图结构普遍必要性，故无需据此扩大训练矩阵；若要主张不可替代，须先匹配容量、输入、目标和预算 |
| L3 | 全局MAE足以代表各类样本表现 | 四格中稀有事件键单键误差较高，常态未触发格贡献多数总误差 | 主结果并列报告全局与事件/非零分层，后续模型筛选同时检查两类指标；误差份额仅用于确定研究评价重点，不转换为风险或报警阈值 |

这些诊断支持安排关系对照、学生配置核验和分层评价，尚未验证诊断指导改模的收益。β独立增益、图结构普遍必要性和跨预算门控优势仍需各自的受控实验。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "5.1 引言"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 5.1 引言

第4章显示，整体误差改善不等于困难样本表现改善。本章据此检验方向性候选、区间覆盖和运行接口所需证据。方向性分析仅用训练段序列；区间评价分别复用Caltech与JPL冻结预测；固定轨迹和合成线性规划用于说明接口及其条件。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "5.5 本章小结"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 5.5 本章小结

表5-9汇总本章三类分析：方向性候选、区间可靠性和运行接口。

**表5-9 第5章探索结果汇总**

| 问题 | 操作 | 主要观察 | 结论边界 |
|---|---|---|---|
| 统计关系能否呈现方向信息？ | TE候选筛查与PCMCI+条件独立分析 | TE有76/90个未经校正的名义候选，270项Bonferroni后为0；当前环境PCMCI+为22/360个Holm校正滞后单元 | 历史PCMCI+的80个名义单元缺版本和完整p矩阵；方向统计不是物理因果边 |
| 点预测能否给出可靠区间？ | 标准共形、回溯规则路由与oracle对比 | 标签事件覆盖率1.9%→3.9%；oracle为86.1% | 旧规则不具备已验证实时可见性，覆盖未达标；oracle仅为事后参照 |
| 分离模型选择与校准后能否达标？ | 新协议冻结三种子、独立校准段与有限样本秩修正 | 行为分层整体覆盖80.04%，事件5.92%；平均宽度较标准增加43.3% | 测试时期已查看；存在时间依赖与失配，不能报告90%保证或与旧覆盖直接计算收益 |
| 滚动残差更新能否缓解失配？ | 14/28天成熟标签历史回放 | 14天行为分层整体覆盖89.01%，事件26.71%；宽度为冻结分层的4.47倍 | 已查看时期的条件回放，未达90%，不证明分层独有优势 |
| JPL独立校准能否覆盖困难样本？ | 复用冻结三种子预测，按原两条路径校准 | 标准/行为分层整体覆盖90.08%/90.11%，事件46.43%/45.88% | 固定已查看测试期；总体接近目标不等于事件可靠性 |
| 节点预测如何进入运行决策？ | 代理需求回放及合成充电分配线性规划 | 实例末步低估43.1%；合成计划满足1 kWh请求与容量限制 | 真实预测与合成约束来源不同，尚无计量映射或实际调度收益 |

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "研究工作总结"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 研究工作总结

本文围绕站内节点代理负荷，完成关系建模、受控预测比较和MDP诊断。新增证据支持所检JPL设置下负荷耦合与轮廓相似关系相对自环的条件性整体MAE增量，并说明组件价值、完整模型表现和参数敏感度须分别判断。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "主要研究结论"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 主要研究结论

（1）整体误差优势未延伸至困难样本。Caltech事件时刻协议下，MRG-GCN整体MAE为0.03890 kWh/15 min，较容量近似TCN低16.1%，但完整AGCRN更低，且MRG-GCN非零目标与标签事件误差均未优于TCN。JPL重新拟合后，其整体MAE为0.081067 kWh/15 min，较三项预登记对照低2.64%—3.36%，校正时间块区间为正；TCN的RMSE及困难样本误差更低。因此，模型选择应并列考察整体与分层指标。

（2）组件增量具有明确边界。节点级门控相对同参数共享门控在Caltech、JPL的整体MAE分别低2.69%和2.71%；每站一个共享门控种子触及60轮上限，结果限于该训练预算。JPL同参数自环替换显示，负荷耦合和轮廓相似关系的整体MAE增量分别为1.82%和1.52%，Bonferroni校正区间下限均为正；行为共现关系的区间跨零。事后分层中，负荷邻接换为自环后非零组MAE较完整模型高0.004893 kWh/15 min，三种子同向，但该结果未经多重校正。它是组件内差异，不是模型间排名：完整MRG-GCN在Caltech、JPL及完成时刻截断目标下的非零组均未胜过容量近似TCN。

（3）目标敏感性与MDP改变了证据解释。完成时刻截断下MRG-GCN全局MAE低于容量近似TCN（0.043401对0.051703 kWh/15 min），但新目标零值占比为94.27%，MRG-GCN非零组MAE高0.013938 kWh/15 min，优势仍由零目标组驱动；该实验固定关系图并复用已查看测试期。MDP区分联合参数敏感度、受检学生替代表现和误差组成：$\beta$未显示独立增益，当前学生未弥合差距，四格结果要求并列报告稀有困难格误差与常态格总误差。它支持修订研究判断和评价重点，尚未证明诊断指导改模可提升预测。

（4）可靠性与应用证据仍有限。Caltech 14天成熟标签滚动分层覆盖为89.01%，事件覆盖为26.71%，区间宽度达到冻结方案的4.47倍；JPL标准独立校准整体覆盖为90.08%，事件覆盖仅46.43%。TE候选经270项家族校正后均未保留。固定轨迹和合成线性规划只核验了代理接口与约束求解；缺少计量映射及实际运行资料，尚不能评价现场风险或经济收益。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "研究判断与使用条件"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 研究判断与使用条件

在会话重构的站内节点代理能量任务中，可优先复核负荷耦合和轮廓相似关系，将行为共现关系保留为待确认候选；若关注活跃片段，应按非零组和事件组表现选模，不以整体MAE或$\beta$排序单独决定关系取舍。现有证据可用于安排模型复核与数据采集，不能支持现场设备选型、容量控制或收益估算。

```

#### docs/thesis/thesis-manuscript.md — 唯一允许修订范围与现有表述
定位：`{"kind": "markdown_heading", "value": "研究局限与后续工作"}`；来源SHA-256：`5da3c63f5fb6397b7a7e08403dcd4b28294eb9202e4fd58b96622a55e4105bf4`
```text
## 研究局限与后续工作

后续工作分三步推进：首先以同步电表和输入到达时间戳校准代理目标，并在未见时期或其他数据来源复核；若要检验全流程稳健性，替代目标下还应重建关系图。其次，若要排除门控优化预算的影响，应以一致的更长预算重训共享门控；若要判断图信息能否被时序模型替代，应匹配学生容量、输入和训练预算。最后，结合成熟标签、实时可见信号及设备和车辆约束开展真实站点影子运行，评价事件覆盖、漏报、执行效果与成本。上述补验对应更强主张，不改变本文当前结果的适用范围。

```

#### docs/thesis/revision-20261018-claude-review/scope.json — 修订范围
定位：`{"kind": "whole_file"}`；来源SHA-256：`444107d727ed56c60111e886ac67d1f027b70d260201b2a649a98fdc859a176e`
```text
{
  "allowed_headings": [
    "摘  要",
    "Abstract",
    "1.3 现有研究不足",
    "1.4 研究目标与主要内容",
    "1.7 本章小结",
    "3.8.1 方法组件与目标敏感性证据综合",
    "3.9 本章小结",
    "4.5 MDP诊断结果与适用边界",
    "5.1 引言",
    "5.5 本章小结",
    "研究工作总结",
    "主要研究结论",
    "研究判断与使用条件",
    "研究局限与后续工作"
  ]
}

```

#### docs/thesis/claim-evidence-map.md — 当前主张证据
定位：`{"kind": "whole_file"}`；来源SHA-256：`3a1ae1eea4bd7eccba86c8b49e8a38dcf121810a78a614f40a4f8f72ab9fca42`
```text
# 新增补强证据映射

## 当前证据状态（2026-10-18更新）

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
| NEAR76-LITERATURE | §1.2表1-1、§1.2.3、§1.3 | 出版社原文核验快照：`content-review-20261017-calibration-pair/reviewer-packet/evidence/NEAR76-primary.md` | Liang[76]已报告公开Boulder交易重构EV负荷上的直接/残差预测及指标依赖结果；本文不把一般会话重构代理预测或残差校正作为空白。其单场站内多节点关系、节点门控、关系替换重训与MDP差异用于定位本文问题，不支持跨文误差排名。 |

| 主张 | 正文 | 直接证据 | 权限 |
|---|---|---|---|
| CLM-031-RELATION | §3.7.2、表3-11、表3-13 | SG-EXP-031实验报告；audit.json与逐种子/块级CSV | 两类邻接相对自环替换的条件性整体MAE增量；第三类不确定 |
| CLM-032-TARGET | §2.1.2、§3.8.4、表3-15 | SG-EXP-032目标审计、逐键预测、回收manifest | 固定图、共同键上的替代代理目标敏感性，不是实测效度 |
| CLM-JPL-INTERVAL | §5.3.5 | JPL-calibration-20261015/audit.json、independent-verification.json | 固定已查看测试期的独立校准经验覆盖，事件覆盖不足 |
| CLM-ADAPTIVE-CUDA | §3.6.1、§3.6.4 | AdaptiveGraph-CUDA-20261015独立核验及回收数组 | 匹配CUDA权重→预测复算通过，原生CPUtop-k选边机制；保留训练源码认证限制 |

```

#### docs/thesis/experiment-reports/SG-EXP-031-jpl-relation-controls.md — 关系证据
定位：`{"kind": "whole_file"}`；来源SHA-256：`d93dd099dbc4a55385fa4e3122323ca1c8ee5f4ddc205562ebc4fd69d57519d9`
````text
# SG-EXP-031：JPL同容量关系替换对照

日期2026-10-15。状态：训练完成、归档回收并通过结果审计；可形成限定于本协议和预算的补充结论。该实验使用已查看的JPL固定测试期，属于事后补充验证，不是盲测确认。

## 设计与合同检查

依据 `training-design-20261015.md`，四配置full/load_to_self/event_to_self/pattern_to_self，各2024/2025/2026三个种子。从头训练，同种子非邻接初始参数SHA-256一致，32714个可训练参数，三槽位均保留。只将指定邻接换为自环，不删除参数、不屏蔽梯度。

本地CPU和服务器CUDA各完成12组合同检查：冻结JPL数据哈希和时序成熟度、关系槽位替换、未替换邻接一致、参数数量、初始参数配对、六组关系变换梯度有限且非零、探针后参数未改变。探针只有小批train的前向/反向检查，无优化器更新。首次检查的输出目录创建错误已修复并重跑。

服务器CUDA检查产物已回收至 `outputs/experiments/SG-EXP-031/cuda-contract-check.json`。环境PyTorch2.8.0+cu128、CUDA12.8、NumPy2.3.2、RTX4090 D，与旧JPL软件环境一致。正式上限60轮、耐心8、batch256、AdamW0.001/weight_decay0.0001，完整tuning原单位MAE选模，FP32确定性计算、关闭TF32。

## 源码与入口

实现入口 `scripts/jpl_relation_controls.py`，复用原runner，仅在本CLI进程内通过作用域工厂适配注入邻接替换，退出时恢复。旧runner、模型源码和旧上传包未修改。冻结包67项manifest在最终回收时全部核验，入口和设计哈希写入每次训练合同。

本地冻结包：`outputs/experiments/SG-EXP-031/bundle/`。
传输压缩包SHA-256：`5361c41a147592d0ea6bb14cd2282637f4906015a0dc76f4563d2b0e388b4d8a`，远端一致。
另保存原Git HEAD、已跟踪源码差异和每文件哈希；源码有未提交内容，不将HEAD单独当作完整版本认证。

远端包：`ssh://root@connect.westc.seetacloud.com:24376/root/autodl-tmp/SG-EXP-031`。
日志：`/root/autodl-tmp/SG-EXP-031/train.log`。
正式产物：`/root/autodl-tmp/SG-EXP-031/results/SG-EXP-031/jpl/<variant>/seed-<seed>/`。
启动包装脚本：`scripts/run_jpl_relation_controls.sh`，初始PID3324，仅作为本次进程标识，不作持久身份。

## 可执行命令

在新冻结包根目录运行：

```sh
/root/miniconda3/bin/python scripts/jpl_relation_controls.py check --device cuda --out results/SG-EXP-031
/root/miniconda3/bin/python scripts/jpl_relation_controls.py all --device cuda --out results/SG-EXP-031
```

运行入口另有train/evaluate，train可指定--variant和--seed；已训练目录须加--resume，contract不匹配即拒绝恢复。正式训练开始后不能覆盖check记录。evaluate会先要求全部12次训练完成、合同一致，冻结best/last哈希后统一导出tuning/calibration/test；不存在按先看到test胜负筛配置的路径。

## 结果回收与审核

- 远端汇总状态为`completed_unreviewed`，退出码0，12/12次正式训练结束时间为2026-10-14 19:01:52 UTC。测试预测已导出，checkpoint-lock包含12组best/last哈希。
- 远端归档SHA-256为`4eb436fbf30823d4df9b3e1be9f34652f849bdf7a130ce1c4229d9b2964f8c5f`；本地归档哈希一致，tar可读，内层173项SHA-256全部通过。冻结输入包67项manifest、数据、入口脚本、训练计划、模型/runner源码和原始关系图哈希均与运行合同相符。
- 合同状态PASS；每个配置均为32,714参数。同一种子下四配置的初始非图参数哈希一致。三种子共用15,816个预测原点、632,640个预测键；标签、节点、事件标记、触发标记及时间键逐数组完全一致。全部预测有限，起点和节点编号无重复。
- 从逐键预测独立复算MAE、RMSE、事件/非事件MAE、逐目标片、逐节点误差，均与`metrics.json`匹配；独立四格重构通过1e-9容差。最佳轮次与训练日志中tuning原单位MAE最低轮次一致，12次运行均未达到60轮上限。
- 10,000次配对七日块bootstrap以三个种子逐键绝对误差均值为基础；固定JPL测试期划分为24个洛杉矶本地周块。三项全局MAE比较使用Bonferroni 98.333%同时区间。完整逐次结果、块级结果、源哈希和解释边界见[SG-EXP-031结果审计](../../../outputs/analysis/SG-EXP-031-audit-20261015/README.md)及[审计JSON](../../../outputs/analysis/SG-EXP-031-audit-20261015/audit.json)。

## 主要结果与可写结论

| 自环替换配置 | Full相对替换配置的全局MAE变化 | Bonferroni 98.333%周块区间 | 三种子方向 | 结论 |
|---|---:|---:|---|---|
| `load_to_self` | 低0.001501 kWh/15 min（1.82%） | [0.000048, 0.002689] | 3/3更优 | 支持负荷关系在本JPL协议、架构和预算下的条件增量 |
| `event_to_self` | 低0.000120（0.15%） | [-0.000432, 0.000728] | 2/3更优 | 同时区间跨零；不支持事件关系具有独立正向全局MAE增量 |
| `pattern_to_self` | 低0.001252（1.52%） | [0.000167, 0.002275] | 3/3更优 | 支持模式关系在本JPL协议、架构和预算下的条件增量 |

因此，本实验只支持**负荷关系和模式关系相对自环替代的条件增量**；不能再写“三类关系均有独立增益”或“三类关系均不可替代”。事件组为描述性结果：将事件关系图替换为自环后，事件MAE平均降低0.005142；将模式关系图替换为自环后，事件MAE平均降低0.003677，说明全局MAE改善不等于事件片段改善。JPL测试零目标键占72.75%，与Caltech事件时刻协议的87.25%不同，需分协议报告。

审计文件另含零目标/非零目标的次要分层，未作为三项预登记全局MAE比较。对“负荷耦合邻接→自环”而言，替换配置绝对误差减完整模型绝对误差的三种子平均差，非零组为0.004893 kWh/15 min、零目标组为0.000230 kWh/15 min；非零组的种子差均为正（0.005892、0.002579、0.006209）。该分解是已查看测试期上的探索性描述，未为该分层计算经多重校正的区间，不应表述为确认性非零组优势。它回答的是完整三关系配置相对同参数自环替代的组件问题；与完整MRG-GCN相对TCN的模型比较不同，后者在JPL非零组MAE仍较低，参见主稿表3-3。

以上区间反映已查看JPL固定测试期的时间块变异；它不估计场站抽样不确定性，也不包含完整的种子抽样不确定性。该结果不证明跨站点普遍性、未来期泛化、真实功率预测或现场运行收益。

## AutoDL状态

本地归档已回收并完成哈希与内容核验。远端summary中的`shutdown_status`仍为`pending_local_recovery`；AutoDL保持在线，**本次没有下达关机命令**，遵循用户“AutoDL是远程服务器，我不会关闭它”的说明。远端guardian状态文件仍为`armed`，但本轮未执行关机；不要据此声称AutoDL已自动关闭。

2026-10-15后续状态：本节上述在线/未关机记录对应031结束时。此后用户授权SG-EXP-032完成训练，结果回收核验后实例已关机；以SG-EXP-032/shutdown-evidence.json为当前控制台证据。

````

#### docs/thesis/experiment-reports/SG-EXP-032-completion-target-sensitivity.md — 目标敏感性
定位：`{"kind": "whole_file"}`；来源SHA-256：`9585428a9501321944ba38efcfacaa3978d8c2514149c6eedfe0a46fd25b0f8a`
```text
# SG-EXP-032：完成时刻截断代理目标敏感性

日期：2026-10-15。状态：6组正式训练完成；远端归档、99项内层校验、逐键独立复算均通过；AutoDL控制台已确认目标实例关机。实验编号SG-EXP-032独立登记。目标是检验模型比较对“接入—断开均摊”代理标签改为“接入—有效充电完成时刻截断均摊”的敏感程度。

## 冻结的目标规则

复用SG-EXP-024已有的`alternative_reconstruction.npz`，并使用其中同一重构函数从原始会话表独立重建。仅当`connectionTime <= doneChargingTime <= disconnectTime`时以完成时刻为分摊终点；完成时刻缺失或不满足区间条件时，退回`disconnectTime`。每个会话的`kWhDelivered`仍守恒。此替代序列是由会话字段重构的代理标签，不是电表功率。

有效完成时刻会话10,399个，缺失420个，无效非空266个。替代重构把28,403.239 kWh移出完成时刻之后的片段。新旧标签总电量均为92,650.016936 kWh，最大节点总量差为4.91e-10 kWh；替代序列与SG-EXP-024原数组逐元素一致。全序列平均绝对标签差0.0477816 kWh/15 min仅描述两种重构定义的差异，不能解释成标签不确定度上限或模型误差基准。

## 训练前审计与固定项

数据源为SG-DATA-006 Caltech事件时刻协议，冻结数据SHA-256为`f663b510c75e203c8150f57c3765645f92b9a941e0745227c6ea078008a0dc8f`；SG-EXP-024替代包SHA-256为`a09c99c00fc1f6728f6bc276817b15f66fc1c8f646e929e2230c8782e6640b6f`。替代数组118,818个时间戳、10个节点及节点顺序均与冻结协议逐项一致。保留全部7通道行为/日历输入、事件与触发标签、图、split边界、起点和样本键；事件标签仍仅用于事后分组评价，不参与筛样、加权、训练、选模或种子选择。

每split的预测原点保持不变：train 83,099、tuning 8,803、calibration 8,805、test 17,714。每个原点按4个目标片、10个节点形成键；test共708,560个`(origin,horizon,node)`预测键。测试零目标比例从原目标的87.25%变为替代目标的94.27%；train/tuning/calibration替代目标零值比例分别85.56%、99.40%、96.89%。因此分层指标必须按协议分别报告，不能把标签零值组成变化当成模型改善。

SG-DATA-006关系图以成熟训练前缀构造。训练前将该图从原训练前缀逐位重建，结果与冻结图相同；本实验固定原图以隔离目标标签变化。该设计检验固定拓扑下的目标敏感性，不检验按替代标签重建拓扑后的端到端流程。新目标成熟前缀仍为83,198片；每个固定split原点窗口均通过替代标签成熟度检查。每节点目标均值和标准差仅在替代目标的该训练前缀重新计算。

比较模型为`mrg_full`与`tcn_wide`，可训练参数量分别32,714与32,674（差0.12%）。各模型使用种子2024/2025/2026，从头训练，AdamW、学习率0.001、weight decay 0.0001、batch 256、最多60轮、patience 8；以完整tuning集原单位MAE选best。精度为FP32确定性计算、TF32关闭。正式训练不缩减数据、轮数、种子或测试键。

## 合同和smoke证据

- 训练入口：`scripts/completion_target_sensitivity.py`；合同数据包：`outputs/experiments/SG-EXP-032/frozen-contract/`。
- CPU合同检查：`check`确认替代目标、固定输入/图/事件标签/起点键和预期参数量。
- 本地CPU smoke：1轮、32个train原点、16个tuning原点；MRG 32,714参数，loss及16×4×10预测均有限；没有导出calibration/test。
- 完整合同审计：`outputs/experiments/SG-EXP-032/frozen-contract/contract_audit.json`；训练入口SHA-256为`6bb968944a4db08cb3458cf0dbdd4b07c192ce5c31cbcdefad44b9cb945ad753`。远端CUDA smoke同样通过：AutoDL RTX4090 D，PyTorch 2.8.0+cu128、NumPy 2.3.2；1轮、32个train原点、16个tuning原点，有限预测且未导出calibration/test。环境快照见`outputs/experiments/SG-EXP-032/remote-preflight.txt`，smoke摘要见`outputs/experiments/SG-EXP-032/remote-cuda-smoke/`。训练完成后追加正式运行、逐键复算、归档SHA和控制面关机证据。
- 正式矩阵：`mrg_full`、`tcn_wide` × 种子2024/2025/2026；远程执行命令为`/root/miniconda3/bin/python scripts/completion_target_sensitivity.py all --device cuda --bundle outputs/experiments/SG-EXP-032/frozen-contract --out /root/autodl-tmp/SG-EXP-032/results/formal`。服务器为用户已启动的AutoDL实例，启动时RTX4090 D空闲、无其他训练进程；远端合同包SHA-256为`d53015b7de8150ad00efaa631449df57360c2987094c102e3f175561dee001df`（91项文件manifest通过）。正式训练日志与完整归档已回收；远端环境、进程和GPU预检见本地归档副本。正式运行均以exit marker 0结束，训练日志含6条完成记录且无Python traceback。

## 结果解释规则

主比较为共同测试键上`tcn_wide`绝对误差减`mrg_full`绝对误差，正值表示MRG-GCN较优。按三个种子逐键误差、固定测试期连续7日块报告配对区间；同时报告全局、零目标、非零目标及冻结事件标签分层MAE。新旧目标下的MAE只能作为各自任务中的模型比较，不得把两种目标的MAE差当作真实功率误差、也不得与0.0477816标签重构差直接排序。

本测试期曾用于既有SG-DATA-006分析，本实验是事后敏感性补充，不是盲测确认。即使模型排序在替代目标下保持，也只说明相对于本次替代代理构造具有一定稳健性，不能证明预测实测功率、现场收益或未来/新场站泛化。


## 正式训练与结果复算

六组训练均按冻结合同完成：`mrg_full`参数32,714，`tcn_wide`参数32,674（相差0.12%），种子均为2024/2025/2026；每组使用全部合同训练数据，最大60轮、patience 8，未缩减轮数或种子。实际最佳轮/停止轮分别为MRG 16/24、12/20、14/22；TCN 6/14、12/20、4/12。六组训练日志累计约2,214.83秒（36.9分钟）。

本地独立审计重新计算了全部预测指标，核对六组逐文件manifest、配置、best checkpoint与调参日志所选轮次、有限预测值，以及校准/测试集预测键、标签、事件标签、触发标志和时间戳。每组具有708,560个`(origin,horizon,node)`测试键，六组共同键完全一致。审计状态为PASS，完整逐键证据见`outputs/analysis/SG-EXP-032-target-audit/`。

| 模型 | 测试MAE（均值±种子SD） | RMSE | 原事件标签组MAE | 非事件组MAE | 新目标零值组MAE | 新目标非零组MAE |
|---|---:|---:|---:|---:|---:|---:|
| MRG-GCN | 0.043401±0.000303 | 0.193411±0.000728 | 0.480282±0.004677 | 0.037018±0.000241 | 0.008700±0.001153 | 0.614498±0.013807 |
| 容量近似TCN | 0.051703±0.000074 | 0.193320±0.000349 | 0.484651±0.000875 | 0.045377±0.000063 | 0.018353±0.000117 | 0.600560±0.001180 |

训练前冻结的主比较为同种子、同一`(origin,horizon,node)`键上的TCN绝对误差减MRG绝对误差，正值支持MRG。三个种子平均差为0.008302 kWh/15 min；固定测试期按连续7日时间块进行10,000次配对bootstrap，95%区间为[0.007757, 0.008797]，27/27个区块差值为正。共同全局MAE差方向一致，但RMSE近乎持平且略偏向TCN（差约0.000091）。

这一总体优势不能被解释为活跃负荷预测普遍更好：替代目标测试键零值比例为94.27%；MRG的零值组和非事件组MAE较低，但非零组MAE比TCN高0.013938 kWh/15 min（MRG 0.614498，TCN 0.600560）。原事件标签组仅有轻微总体差距，且各种子配对差异并不一致。因而本实验支持的结论是：在完成时刻截断代理目标下，MRG相对容量近似TCN的共同键全局MAE优势仍存在；这一优势主要由新目标零值组驱动；按旧事件标签划分的非事件组另呈较低边际MAE，两种边际分层未联合分解，不能据此声称模型改善了非零活跃负荷预测或实际运行价值。

## 回收与AutoDL关机验收

远端结果归档SHA-256为`b6f73aeb350db65f1d25ee59c19bcf8b316270049f46aaeee59ff971947670b3`，本地下载归档SHA逐字一致；归档内99项文件的SHA-256全部通过，随后逐键审计PASS。证据见`outputs/experiments/SG-EXP-032/recovery-verification.json`及`outputs/experiments/SG-EXP-032/recovered/closeout/closeout/`。关机前远端GPU为1 MiB占用、0%利用率且无训练进程，训练PID已消失。AutoDL控制台将目标实例`38a84e9a75-8c21d369`由“运行中”更新为“已关机”；不以SSH断连作为关机证明。控制面记录见`outputs/experiments/SG-EXP-032/shutdown-evidence.json`。

## 结论权限与限制

SG-EXP-032完成了目标敏感性补充，但它属于已查看Caltech固定测试期上的事后实验。它没有解决会话代理目标与电表实测功率之间的效度差距，也没有改变测试集高零值占比这一解释限制。原事件/触发标签冻结为事后分组口径；替代目标的零/非零标签仅用于结果分层。完成时刻截断结果可用于比较同一新代理目标下两种模型，不可把新旧标签上的绝对MAE差解释为模型误差变化，也不可将0.0477816 kWh/15 min标签定义差当作误差上限。训练、选模和审计均未调用目标事件/触发标签。

```

#### docs/thesis/experiment-reports/EXP-JPL-calibration-20261015-no-training.md — JPL区间已完成
定位：`{"kind": "whole_file"}`；来源SHA-256：`da74215ccdc23de4aa0901efa6eec09693ca03233be5befb29eae620c702352a`
```text
# JPL既有预测独立校准复核（2026-10-15）

审计ID：AUDIT-JPL-CAL-20261015。复用SG-EXP-028三个既有MRG-GCN运行的calibration/test预测；不训练、不重新选模。因固定测试期已经查看，本报告属于事后可靠性补充。

## 方法与来源

执行前固定alpha=0.1、种子2024/2025/2026及逐节点、行为分层两条路径，沿用Caltech独立校准定义。标准路径逐节点汇聚四个目标片；行为分层触发键跨节点汇聚、未触发键逐节点。校准残差升序第ceil((n+1)*0.9)项为半宽；若秩超过样本数则须报告无穷半宽，本次未发生。区间对称且不截零，事件标签只用于评价；测试不参与半宽或规则选择。

每种子313,120校准键与632,640测试键；三种子真值、节点、原点、目标时刻、事件/规则掩码完全对齐，校准与测试的原点及目标时刻集合互斥。脚本、输入六文件SHA-256、校准样本数/秩及逐种子统计见`outputs/analysis/JPL-calibration-20261015/audit.json`。原训练checkpoint锁和测试导出保持不变。此项评估复用既有导出，未执行检查点前向。

## 结果

| 路径 | 整体覆盖/% | 事件覆盖/% | 非零目标覆盖/% | 平均宽度 | 区间分数 |
|---|---:|---:|---:|---:|---:|
| 标准逐节点 | 90.08±0.13 | 46.43±0.25 | 65.82 | 0.59817 | 1.15254 |
| 行为分层 | 90.11±0.14 | 45.88±0.32 | 66.01 | 0.58608 | 1.13615 |

覆盖为三种子均值±样本标准差；宽度与区间分数单位为kWh/15 min。事件键13,163个，非零目标172,396个；零目标460,244个，两条路径零目标覆盖均超过99%。区间分数=宽度+20×区间外距离，越小越好。

总体覆盖接近90%，但事件与非零目标覆盖明显不足；行为分层没有改善事件覆盖。该结论适用于当前代理目标及已查看的JPL固定测试期，不提供覆盖保证、跨时期效度或业务可接受宽度结论。

## 独立核验

使用完整排序重算顺序统计量，以区间两端比较重算覆盖、分别计算上下端惩罚重算区间分数；与原分区算法及绝对残差公式的最大差2.22e-16，状态PASS。核验记录为`outputs/analysis/JPL-calibration-20261015/independent-verification.json`。输入及预测保持原哈希。正文落点：§5.3.5、§5.5、摘要和结论。

```

#### docs/thesis/revision-20261016-nonexperimental/data-availability-decision.md — 既有数据条件
定位：`{"kind": "whole_file"}`；来源SHA-256：`103d7f4c39dd3d9dcace742ce4ce026486dbffb20fe1d083b6cc2c3c380726f8`
```text
# 未查看数据可得性与适用性判断

核查日期：2026-10-16。目标是判断是否存在可支持论文后续“未查看时期”或目标效度补证的数据；本记录不代表已经获得、处理或验证数据。

## 当前判断

截至本轮，项目材料中没有一份已取得且通过来源、时期、字段和节点映射核验的未查看数据。`docs/thesis/data-availability.md`记录的本地JPL/ACN时间范围止于2021年，2022—2026年本地CSV没有记录；已用于SG-EXP-028及其后续分析的固定测试期不能再称为未查看确认集。

本轮执行环境未发现ACN/Caltech API相关环境变量，因此未开展认证API盘点；未读取或导出钥匙串等凭据。ACN官方页面同时提供按日期筛选并下载JSON的网页界面，以及需要注册令牌的REST API；本轮只核实了接口说明，未实际筛选或导出数据。故当前状态是“存在可尝试的官方入口，但尚未确认可用的新时期数据”，不是“已取得未查看数据”。

## 候选数据与用途边界

| 候选 | 当前可确认的信息 | 可回答的问题 | 主要门槛/不适用范围 | 决定 |
|---|---|---|---|---|
| ACN-Data官方Caltech/JPL网页界面与API | 官方网页界面允许按站点和时间筛选并导出JSON；REST API可查询不含时序的会话元数据、支持过滤和分页，但须注册取得令牌。[官方数据/API说明](https://ev.caltech.edu/dataset) | 若记录确有2021年后且未查看的会话，可先确认时期、会话量、站点和spaceID映射，再判断是否建立独立时间确认集 | 本轮未用网页表单查询或导出，故新时期仍未确认；API令牌未取得。还需核验节点映射、行为字段稳定性和标签成熟性。ACN属于既有数据体系，不构成新数据家族 | **优先做只读元数据盘点**。可先尝试网页界面；若改用API再申请令牌。输出时期覆盖与节点映射摘要，且不得按已查看测试结果挑选有利时期 |
| KIT 2025 EV充电测量数据（Zenodo 17866847） | 数据页称其测量发生于2025-10-28至2025-12-02，包含18组、16辆车、12个品牌；每组对应单一测点。低频文件列出测量电压/电流和计算相功率，页面列示Parquet文件；发布于2026-02-09。[Zenodo记录](https://zenodo.org/records/17866847) | 在许可、会话定义和时间对齐明确后，可检验均匀分摊代理与实际测量功率/能量形态之间的差异，为“代理目标效度”提供独立量测证据 | 不是多节点场站负荷数据，不适合验证MRG-GCN或跨站预测增益；页面Rights/License字段为空，不能仅据“Open”标签推定可任意下载、处理和发表；还需确认低频采样能否可靠积分及会话起止事件定义 | **暂不下载/纳入论文**。先向数据提供方或记录维护者核实许可及科研发表条件；随后做字段和测量语义审查，再决定是否适合目标效度对照 |
| 悉尼路侧充电记录（Zenodo 19866413；较早版本19233669） | 记录说明2025-09至2026-02约27,000次公共路侧会话，数据由三个地方政府提供；最新版记录发布日期为2026-04-30。记录称“地点与使用数据”，文件标记为Restricted，需登录并获授权；许可栏未显示具体条款。[最新版记录](https://zenodo.org/records/19866413) | 若获准访问，可能用于检查不同公共充电场景的会话分布；只有在字段包含可对齐的功率/电量时序后，才可能评估代理目标或预测任务 | 当前无法读取文件和完整字段字典；不能据公开元数据认定具有实测功率、节点级多元时序或本文所需输入；城市路侧场景也不同于封闭场站。访问许可和再分析/发表条件未知 | **暂列受限候选，不视为可用数据**。先申请访问并取得许可，再审查字段、设备映射、时间戳和目标定义；条件通过前不纳入论文或训练 |

## 建议顺序

1. 通过ACN官方API只查元数据，不请求`/ts`时序端点；令牌留在本机环境，不通过聊天传递。检查最晚时间、按月记录数、站点数、spaceID数及与原有节点映射的稳定性。完成后将查询时间、字段、计数和响应哈希记入材料护照，不保存用户身份字段。
2. 并行书面确认Zenodo测量集的许可、再分析和发表要求，以及“session/measurement point”的起止定义。许可未明确前不下载大体量时序文件。
3. 根据结果选择问题：ACN未查看时期可用于固定模型或预登记训练方案的时间外确认，但需要重新评价/训练并严格冻结；KIT实测信号可用于代理目标校准或敏感性核验，但不支持站内图预测增量。两者不能互相替代。

本轮仅完成公开来源审阅和可得性判定；未下载数据、未调用带凭据API、未运行分析或训练。数据源能否补齐论文证据取决于上述门槛，不把“网页可访问”写成“已取得可用数据”。

## 2026-10-16后续候选补查

新增查看悉尼路侧充电数据的Zenodo记录（DOI `10.5281/zenodo.19866413`，版本v2，2026-04-30发布）。记录页报告约27,000次、2025年9月至2026年2月的会话，但将数据文件标为Restricted，且页面未列明确许可；当前只能看到元数据，不能核验字段、实测量和测点映射。该候选补充了“存在后续登记的数据集”这一检索结果，未改变“本地尚无已取得并通过适用性核验的新数据”的结论。可见官方数据页：[Zenodo记录](https://zenodo.org/records/19866413)。

## 2026-10-17复核

复核本地项目后，原始JPL会话文件仍为`data/external/JPL-20261005/sessions.jsonl`，33,638条记录，SHA-256为`68480c71451dfaa0e2ca3a27cefb2fa229c76eac31fc541ccef56af7a9af3af4`；接入时间最晚为2021-09-14，断开时间最晚为2021-09-14。仓库没有新增的2022—2026年原始ACN/JPL会话文件。此结论只针对当前本地材料，不代表官方数据源不存在后续记录。

再次查看[ACN-Data官方页面](https://ev.caltech.edu/dataset)：页面说明网页界面可按站点和日期筛选并导出JSON；REST API要求注册令牌，且明确区分仅会话字段端点与时序端点。本次没有执行日期筛选、导出或认证API查询，故尚不能确认ACN是否存在可用于未查看时期核验的记录。下一步若继续，应先用网页界面只读筛选并记录时间范围、计数和站点映射；如需API令牌，应由用户自行在本机取得，不在聊天中传递。

KIT数据记录当前列出18组、16辆车在2025-10-28至2025-12-02的测量，低频文件含分相电压、电流和计算功率，Parquet低频文件约422.5 MB；但元数据未列明确许可，且每组仅为单一测点，不是与本文相同的多节点场站预测任务。[KIT Zenodo记录](https://zenodo.org/records/17866847) 因而它可能支持经授权后的代理目标形态核验，不能直接验证MRG-GCN跨站性能，也不应在许可核实前下载并纳入论文。

悉尼路侧数据记录描述约27,000次、2025年9月至2026年2月的会话，但文件标为Restricted，记录未显示具体许可或可检查字段字典。[悉尼Zenodo记录](https://zenodo.org/records/19866413) 目前不能据其判断是否包含可用功率时序、节点映射或本文所需预测输入，故仍不属于已取得且可用的新数据。

本次复核没有下载数据、使用凭据或启动训练；新时期评估数据仍未确认。该结果不改变门控预算敏感性补验的适用性：后者复用已查看JPL测试期，只能回答预算替代解释，不承担独立外部验证。

```

#### docs/thesis/revision-20261016-nonexperimental/gate-budget-decision-20261017.md — 既有预算决策
定位：`{"kind": "whole_file"}`；来源SHA-256：`5bd04282a3215390f02acd37c7f9816daa689455f21e5bec30402669587dc768`
```text
# 门控预算补验决策

日期：2026-10-17  
对应设计：`docs/thesis/training-design-20261015.md`阶段C。

## 决策

建议开展JPL节点级门控与共享门控的匹配延长预算敏感性补验；本轮只作决策，**没有启动训练**。预算设计为两种配置各3个种子，共6次，从头训练，统一最多120轮、patience 16、同一输入、数据划分、优化器和按调参集选模规则。

## 依据与证据边界

SG-EXP-028中共享门控seed-2024在既定60轮上限处停止，报告记录其已触顶；节点级门控相对共享门控的JPL总体MAE点差为2.71%。当前差异是在60轮/耐心8的共同预算下观察到的。延长预算能直接检验共享门控是否因优化时间不足而受损，因此针对的是一个尚未排除、且可能改变解释的替代因素。

这项补验不依赖新增数据，可先用冻结的JPL事件时刻数据与原划分回答“结论是否对训练预算敏感”。但这些测试期已经查看过；补验即使通过，也只能作为已查看测试期上的预算敏感性分析，不能写成盲测、独立时间外验证或跨场景确认。若共享门控延长预算后缩小差距，应相应收窄“节点门控增量”的结论；若差距保留，也只提高当前协议和预算范围内的稳健性证据。

因此，补验值得做，但应排在候选稿交付审阅之后单独注册、冻结运行合同并按计划留档；不得用本次论文版式验收的完成状态替代训练合同检查，也不得据本轮决策直接启动远端任务。

```

#### src/evcs_station_graph/eventtime/gate_control.py — 共享门控实现
定位：`{"kind": "whole_file"}`；来源SHA-256：`1cf89b3cc00e6cae6ce9ff90916319d390e6af81bed00726d7ff4e6d91cabe95`
```text
"""SG-EXP-027: retain gate capacity, remove node-specific gate values only."""
import torch
from torch import nn


class SharedNodeGate(nn.Module):
    def __init__(self, original):
        super().__init__()
        # Reuse the initialized modules; no additional RNG draws or dummy weights.
        self.W_r = original.W_r
        self.W_gate = original.W_gate
        self.norm = original.norm
        self.dropout = original.dropout
        if original.relation_dropout != 0:
            raise ValueError('Control requires frozen zero relation dropout')

    def forward(self, h, adj, logits):
        beta = logits.softmax(0)
        message = torch.zeros_like(h)
        for r, (a, w) in enumerate(zip(adj, self.W_r)):
            neighbor = torch.einsum('nm,bmd->bnd', a, h)
            message = message + beta[r] * w(neighbor)
        gate = self.W_gate(torch.cat((h, message), -1)).mean(1, keepdim=True).sigmoid()
        updated = gate * message + (1-gate) * h
        return self.norm(h + self.dropout(updated))

```

#### scripts/gate_control_experiment.py — 现有门控入口
定位：`{"kind": "whole_file"}`；来源SHA-256：`b875feca68a8c5fb95f876ac9adf55041631ae956909c311877dd892db2e93e3`
```text
#!/usr/bin/env python3
"""Six paired SG-EXP-027 runs; never invokes the old 36-run suite."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from evcs_station_graph.eventtime.data import DATA_SHA256, FrozenData, sha256
from evcs_station_graph.eventtime.models import build_model, count_parameters
from evcs_station_graph.eventtime.runner import default_config, train, export, write_json

NAMES = ('mrg_full', 'mrg_shared_gate')
SEEDS = (2024, 2025, 2026)


def config(name, seed, stage):
    cfg = default_config(name, seed, smoke=stage == 'smoke')
    cfg['experiment'] = 'SG-EXP-027'
    if stage == 'benchmark':
        cfg.update(mode='BENCHMARK_NOT_SCIENTIFIC_EVIDENCE', max_epochs=2,
                   train_limit=2560, eval_limit=512)
    return cfg


def verify_bundle():
    path = ROOT/'BUNDLE_MANIFEST.json'
    if path.exists():
        for name, digest in json.loads(path.read_text()).items():
            if sha256(ROOT/name) != digest:
                raise ValueError(f'Frozen bundle drift: {name}')
        frozen = json.loads((ROOT/'configs/gate_control.json').read_text())
        expected = [config(n, s, 'formal') for s in SEEDS for n in NAMES]
        if frozen != expected:
            raise ValueError('Frozen gate configuration drift')


def summary(out):
    records = []
    for seed in SEEDS:
        for name in NAMES:
            folder = out/'formal'/name/f'seed-{seed}'
            manifest = json.loads((folder/'manifest.json').read_text())
            for f, digest in manifest.items():
                if sha256(folder/f) != digest:
                    raise ValueError(f'Result hash mismatch: {folder/f}')
            cfg = json.loads((folder/'config_resolved.json').read_text())
            expected = config(name, seed, 'formal')
            metadata = {'dataset_sha256', 'code_sha256', 'contract', 'trainable_parameters'}
            if (set(cfg) != set(expected) | metadata or
                    any(cfg.get(k) != v for k, v in expected.items()) or
                    cfg.get('dataset_sha256') != DATA_SHA256 or
                    cfg.get('trainable_parameters') != 32714):
                raise ValueError(f'Result configuration mismatch: {folder}')
            records.append(dict(model=name, seed=seed,
                                metrics=json.loads((folder/'metrics.json').read_text())))
    write_json(out/'summary.json', dict(experiment='SG-EXP-027', verified_runs=6,
                                      expected_runs=6, records=records))
    print('6/6 verified paired formal runs', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('check', 'smoke', 'benchmark', 'formal', 'summary'))
    p.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    p.add_argument('--out', type=Path, default=ROOT/'results')
    args = p.parse_args()
    verify_bundle()
    if args.stage == 'summary':
        summary(args.out)
        return
    path = ROOT/'data/eventtime/dataset.npz'
    if not path.exists():
        path = ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'
    data = FrozenData(path)
    params = {n: count_parameters(build_model(n, data.arrays['graphs'])) for n in NAMES}
    if len(set(params.values())) != 1:
        raise ValueError('Unequal trainable capacity')
    if args.stage == 'check':
        print(json.dumps(dict(data_sha256=data.digest, parameters=params, formal_runs=6,
                             configuration=[config(n, s, 'formal') for s in SEEDS for n in NAMES]), indent=2))
        return
    seeds = SEEDS if args.stage == 'formal' else (2024,)
    for seed in seeds:
        for name in NAMES:
            cfg = config(name, seed, args.stage)
            folder = args.out/args.stage/name/f'seed-{seed}'
            start = time.monotonic()
            print(f'START {args.stage} {name} seed={seed}', flush=True)
            train(data, cfg, folder, device=args.device)
            export(data, cfg, folder, device=args.device)
            elapsed = time.monotonic()-start
            print(f'COMPLETE {args.stage} {name} seed={seed} seconds={elapsed:.2f}', flush=True)
    if args.stage == 'formal':
        summary(args.out)


if __name__ == '__main__':
    main()

```

#### src/evcs_station_graph/jpl_eventtime/data.py — JPL数据入口
定位：`{"kind": "whole_file"}`；来源SHA-256：`c75fa7cf963b921fa6b102e6a37c947756475d5d42784118361a28098469ddd4`
```text
"""JPL-only frozen tensor loader; deliberately separate from legacy FrozenData."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from torch.utils.data import Dataset

DATA_SHA256 = "1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af"
SCHEMA = "jpl-eventtime-v1-not-legacy-TensorBundle"
FEATURES = (
    "access_count", "departure_count", "active_count", "local_hour_sin",
    "local_hour_cos", "local_weekday_sin", "local_weekday_cos",
)
NODE_IDS = (
    "AG-1F08", "AG-1F10", "AG-1F06", "AG-1F13", "AG-1F02",
    "AG-1F04", "AG-1F01", "AG-1F12", "AG-1F07", "AG-1F03",
)
ORIGIN_COUNTS = {"train": 74168, "tuning": 7826, "calibration": 7828, "test": 15816}
STEP_NS = 15 * 60 * 1_000_000_000
HISTORY = 96
HORIZON = 4


def sha256(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def split_bounds(length: int) -> dict[str, tuple[int, int]]:
    return {
        "train": (0, int(length * 0.70)),
        "tuning": (int(length * 0.70), int(length * 0.775)),
        "calibration": (int(length * 0.775), int(length * 0.85)),
        "test": (int(length * 0.85), length),
    }


class FrozenJPLData:
    """Validate the exact SG-DATA-007 data contract and expose runner-compatible windows."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.digest = sha256(self.path)
        if self.digest != DATA_SHA256:
            raise ValueError("JPL frozen tensor SHA256 mismatch; refusing modified or legacy data")

        with np.load(self.path, allow_pickle=False) as archive:
            self.arrays = {key: archive[key] for key in archive.files}
        a = self.arrays
        required = {
            "timestamps_ns", "node_ids", "feature_names", "features", "targets",
            "label_available_at_ns", "target_event", "rule_trigger", "graphs",
            "rule_thresholds", "feature_mean", "feature_std", "target_mean",
            "target_std", "rule_std", "label_jump_threshold", "train_origins",
            "tuning_origins", "calibration_origins", "test_origins", "schema",
        }
        if set(a) != required:
            raise ValueError(f"JPL tensor key contract mismatch: missing={sorted(required-set(a))}, "
                             f"extra={sorted(set(a)-required)}")
        if str(a["schema"].item()) != SCHEMA:
            raise ValueError("Refusing a non-JPL or legacy tensor schema")

        t = len(a["timestamps_ns"])
        if t != 106096 or a["features"].shape != (t, 10, 7) or a["targets"].shape != (t, 10):
            raise ValueError("JPL tensor dimensions differ from frozen SG-DATA-007")
        if tuple(a["feature_names"].tolist()) != FEATURES or tuple(a["node_ids"].tolist()) != NODE_IDS:
            raise ValueError("Frozen JPL feature order or training-only node order mismatch")
        if a["label_available_at_ns"].shape != (t, 10):
            raise ValueError("JPL label-maturity matrix shape mismatch")
        if a["target_event"].shape != (t, 10) or a["rule_trigger"].shape != (t, 10):
            raise ValueError("JPL event/trigger masks shape mismatch")
        if a["graphs"].shape != (3, 10, 10) or a["rule_thresholds"].shape != (10,):
            raise ValueError("JPL relation graph or rule threshold shape mismatch")
        if a["feature_mean"].shape != (7,) or a["feature_std"].shape != (7,):
            raise ValueError("JPL feature scaler shape mismatch")
        if a["target_mean"].shape != (10,) or a["target_std"].shape != (10,):
            raise ValueError("JPL target scaler shape mismatch")
        if a["rule_std"].shape != (10, 3) or a["label_jump_threshold"].shape != ():
            raise ValueError("JPL rule-statistic shape mismatch")
        if not np.all(np.diff(a["timestamps_ns"]) == STEP_NS):
            raise ValueError("JPL UTC time grid is not a complete 15-minute sequence")

        numeric = ("features", "targets", "graphs", "feature_mean", "feature_std",
                   "target_mean", "target_std", "rule_std")
        if any(not np.isfinite(a[key]).all() for key in numeric):
            raise ValueError("JPL tensor contains nonfinite values")
        if np.any(a["feature_std"] <= 0) or np.any(a["target_std"] <= 0) or np.any(a["rule_std"] <= 0):
            raise ValueError("JPL frozen train-only scale contains a nonpositive value")

        bounds = split_bounds(t)
        train_end = bounds["train"][1]
        train_cutoff = int(a["timestamps_ns"][train_end])
        immature_fit = np.flatnonzero(np.any(a["label_available_at_ns"][:train_end] >= train_cutoff, axis=1))
        fit_end = int(immature_fit[0]) if len(immature_fit) else train_end
        self.fit_prefix_end = fit_end
        for split, (lo, hi) in bounds.items():
            key = f"{split}_origins"
            origins = a[key]
            if origins.ndim != 1 or origins.dtype.kind not in "iu":
                raise ValueError(f"Invalid origin array for {split}")
            if len(origins) != ORIGIN_COUNTS[split] or np.any(np.diff(origins) <= 0):
                raise ValueError(f"Frozen origin count/order mismatch for {split}")
            if np.any(origins - HISTORY + 1 < lo) or np.any(origins + HORIZON >= hi):
                raise ValueError(f"Window crosses a frozen {split} segment boundary")
            cutoff_ns = int(a["timestamps_ns"][hi]) if hi < t else int(a["timestamps_ns"][-1]) + STEP_NS
            for horizon in range(1, HORIZON + 1):
                if np.any(a["label_available_at_ns"][origins + horizon] >= cutoff_ns):
                    raise ValueError(f"Immature proxy labels found in {split}")
            if split == "train" and np.any(origins + HORIZON >= fit_end):
                raise ValueError("Training target extends beyond the mature scaler/graph fit prefix")

        self.x = ((a["features"] - a["feature_mean"]) / a["feature_std"]).astype(np.float32)
        self.y = ((a["targets"] - a["target_mean"]) / a["target_std"]).astype(np.float32)

    def windows(self, split: str, limit: int | None = None) -> "JPLWindows":
        if split not in ORIGIN_COUNTS:
            raise ValueError(f"Unknown split: {split}")
        return JPLWindows(self, split, limit)

    def masks(self, origins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        idx = origins[:, None] + np.arange(1, HORIZON + 1)[None, :]
        target = self.arrays["target_event"][idx]
        trigger = np.repeat(self.arrays["rule_trigger"][origins, None, :], HORIZON, axis=1)
        return target, trigger


class JPLWindows(Dataset):
    def __init__(self, data: FrozenJPLData, split: str, limit: int | None = None):
        self.data = data
        origins = data.arrays[f"{split}_origins"]
        self.origins = origins if limit is None else origins[:limit]

    def __len__(self) -> int:
        return len(self.origins)

    def __getitem__(self, index: int):
        origin = int(self.origins[index])
        return (self.data.x[origin - HISTORY + 1:origin + 1],
                self.data.y[origin + 1:origin + HORIZON + 1], origin)

```

#### scripts/jpl_relation_controls.py — JPL对照适配参考
定位：`{"kind": "whole_file"}`；来源SHA-256：`ac5f7a998ad198af30f07971f929b7abc43300e7aecb9e65e645d633920b9cba`
```text
#!/usr/bin/env python3
"""SG-EXP-031: equal-capacity JPL relation replacements; isolated runner adapter."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import torch
from evcs_station_graph.eventtime import runner
from evcs_station_graph.eventtime.models import build_model as original_factory, count_parameters
from evcs_station_graph.jpl_eventtime.data import FrozenJPLData, sha256

EXPERIMENT = 'SG-EXP-031'
VARIANTS = ('full', 'load_to_self', 'event_to_self', 'pattern_to_self')
SEEDS = (2024, 2025, 2026)
DEFAULT_DATA = ROOT / 'data/jpl/dataset.npz'

def factory(name, graphs):
    if name not in VARIANTS:
        raise ValueError(f'Unknown relation control: {name}')
    modified = np.array(graphs, copy=True)
    if name != 'full':
        slot = VARIANTS.index(name) - 1
        modified[slot] = np.eye(10, dtype=modified.dtype)
    return original_factory('mrg_full', modified)

@contextmanager
def isolated_factory():
    # Dependency injection is scoped to this dedicated CLI process. The old
    # runner and frozen bundles are not edited; restore on every exit path.
    previous = runner.build_model
    runner.build_model = factory
    try:
        yield
    finally:
        runner.build_model = previous

def verify_bundle():
    path = ROOT / 'BUNDLE_MANIFEST.json'
    if path.exists():
        for rel, digest in json.loads(path.read_text()).items():
            candidate = (ROOT / rel).resolve()
            if not candidate.is_relative_to(ROOT.resolve()) or not candidate.is_file() or sha256(candidate) != digest:
                raise ValueError(f'Input bundle mismatch: {rel}')

def parameter_digest(model):
    h = hashlib.sha256()
    for name, param in model.named_parameters():
        h.update(name.encode())
        h.update(param.detach().cpu().numpy().tobytes())
    return h.hexdigest()

def config(name, seed, data):
    cfg = runner.default_config(name, seed)
    cfg.update(experiment=EXPERIMENT, protocol='SG-DATA-007-jpl-eventtime-v1',
               relation_control=name, entrypoint_sha256=sha256(Path(__file__)),
               original_graph_sha256=hashlib.sha256(data.arrays['graphs'].tobytes()).hexdigest(),
               plan_sha256=sha256(ROOT / 'metadata/training-design-20261015.md'))
    runner.setup(seed, 'cpu')
    model = factory(name, data.arrays['graphs'])
    cfg['initial_parameters_sha256'] = parameter_digest(model)
    cfg['used_graph_sha256'] = hashlib.sha256(np.stack([a.numpy() for a in model._get_adjacencies()]).tobytes()).hexdigest()
    return cfg

def check(data, device, out):
    if (out / 'jpl').exists():
        raise ValueError('Cannot replace contract check after training starts')
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for seed in SEEDS:
        initial = None
        for name in VARIANTS:
            cfg = config(name, seed, data)
            runner.setup(seed, device)
            model = factory(name, data.arrays['graphs']).to(device)
            digest = parameter_digest(model)
            if initial is None:
                initial = digest
            assert digest == initial == cfg['initial_parameters_sha256']
            assert count_parameters(model) == 32714
            assert model._num_relations == 3
            for index, graph in enumerate(model._get_adjacencies()):
                expected = np.eye(10) if name != 'full' and index == VARIANTS.index(name)-1 else data.arrays['graphs'][index]
                assert np.array_equal(graph.detach().cpu().numpy(), expected)
            x, y, _ = next(iter(runner.loader(data, 'train', dict(cfg, train_limit=4, batch_size=4), epoch=0)))
            loss = torch.nn.functional.l1_loss(model(x.to(device)).prediction, y.to(device))
            loss.backward()  # Contract probe only: no optimizer or parameter update.
            for layer in (model.gcn1, model.gcn2):
                assert len(layer.W_r) == 3
                for transform in layer.W_r:
                    grad = transform.weight.grad
                    assert grad is not None and torch.isfinite(grad).all() and torch.count_nonzero(grad) > 0
            assert parameter_digest(model) == digest
            records.append(dict(variant=name, seed=seed, parameters=32714, initial_sha256=digest,
                                branch_gradients_pass=True, parameters_unchanged=True, config=cfg))
    report = dict(status='PASS', experiment=EXPERIMENT, training_started=False,
                  dataset_sha256=data.digest, device=device, environment=runner.environment(device),
                  split_origins={s:len(data.arrays[s+'_origins']) for s in ('train','tuning','calibration','test')},
                  runs=records)
    runner.write_json(out / 'contract-check.json', report)
    print(json.dumps(dict(status='PASS', configurations=len(records), training_started=False)), flush=True)

def locked_runs(data, root, device):
    locks = []
    for seed in SEEDS:
        for name in VARIANTS:
            cfg = config(name, seed, data)
            folder = root / 'jpl' / name / f'seed-{seed}'
            ckpt = torch.load(folder / 'last.pt', map_location='cpu', weights_only=True)
            best = torch.load(folder / 'best.pt', map_location='cpu', weights_only=True)
            expected = runner.contract(data, cfg, device)
            if not ckpt['complete'] or ckpt['contract'] != expected or best['contract'] != expected:
                raise ValueError(f'Incomplete or changed training contract: {folder}')
            locks.append(dict(variant=name, seed=seed, best_sha256=sha256(folder/'best.pt'),
                              last_sha256=sha256(folder/'last.pt'), best_epoch=best['epoch']))
    return locks

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'train', 'evaluate', 'all'))
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--out', type=Path, default=ROOT/'results/SG-EXP-031')
    parser.add_argument('--device', choices=('cpu','cuda'), default='cuda')
    parser.add_argument('--variant', choices=VARIANTS, default='full')
    parser.add_argument('--seed', type=int, choices=SEEDS, default=2024)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command != 'check' and args.device != 'cuda':
        raise ValueError('Formal runs require CUDA')
    verify_bundle()
    data = FrozenJPLData(args.data)
    with isolated_factory():
        if args.command == 'check':
            check(data, args.device, args.out)
            return
        gate = json.loads((args.out/'contract-check.json').read_text())
        if gate['status'] != 'PASS' or gate['dataset_sha256'] != data.digest or gate['device'] != 'cuda':
            raise ValueError('Missing CUDA contract check')
        if gate['environment'] != runner.environment(args.device):
            raise ValueError('Environment changed after contract check')
        frozen = { (r['variant'],r['seed']):r['config'] for r in gate['runs'] }
        for seed in SEEDS:
            for name in VARIANTS:
                if config(name,seed,data) != frozen[(name,seed)]:
                    raise ValueError('Design/config changed after contract check')
        if args.command in ('train','all'):
            jobs = [(seed,name) for seed in SEEDS for name in VARIANTS] if args.command == 'all' else [(args.seed,args.variant)]
            for seed,name in jobs:
                runner.train(data,config(name,seed,data),args.out/'jpl'/name/f'seed-{seed}',args.device,resume=args.resume)
        if args.command in ('evaluate','all'):
            locks = locked_runs(data,args.out,args.device)
            lock_path = args.out/'checkpoint-lock.json'
            if lock_path.exists() and json.loads(lock_path.read_text()) != locks:
                raise ValueError('Frozen checkpoint lock changed')
            runner.write_json(lock_path,locks)
            for seed in SEEDS:
                for name in VARIANTS:
                    runner.export(data,config(name,seed,data),args.out/'jpl'/name/f'seed-{seed}',args.device)
            runner.write_json(args.out/'suite-status.json',dict(status='COMPLETED_UNREVIEWED',runs=12,experiment=EXPERIMENT))

if __name__ == '__main__':
    main()

```

#### src/evcs_station_graph/eventtime/runner.py — 训练与选模规则
定位：`{"kind": "whole_file"}`；来源SHA-256：`cc4692209a5eb4fc0e662fe71150685c99e3a5f38a35fc2dc94f3307122025a7`
```text
"""Auditable train/selection/export loop for SG-EXP-019, never legacy engine."""
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import time

import numpy as np
import torch
from torch.utils.data import DataLoader

from .data import sha256
from .models import build_model, count_parameters


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    os.replace(tmp, path)


def default_config(model, seed, smoke=False):
    return dict(protocol='SG-DATA-006-eventtime-v1', experiment='SG-EXP-019', model=model,
                seed=seed, max_epochs=2 if smoke else 60, patience=8,
                batch_size=4 if smoke else 256, lr=.001, weight_decay=.0001,
                loss='standardized_L1', selection='tuning_original_unit_MAE',
                mode='SMOKE_NOT_SCIENTIFIC_EVIDENCE' if smoke else 'formal',
                train_limit=16 if smoke else None, eval_limit=8 if smoke else None,
                num_workers=0, threads=2, precision='float32', deterministic=True,
                gradient_clip=5.)


def code_digest():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root/'eventtime').glob('*.py')) + [root/'models'/f for f in ('graph.py','tcn.py','common.py')]
    return hashlib.sha256(''.join(p.name+sha256(p) for p in paths).encode()).hexdigest()


def setup(seed, device, threads=2):
    if device not in ('cpu', 'cuda'):
        raise ValueError('Use cpu for local smoke or cuda for formal runs')
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested but unavailable; no silent CPU fallback')
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def contract(data, cfg, device):
    obj = dict(config=cfg, dataset_sha256=data.digest, code_sha256=code_digest(),
               torch=str(torch.__version__), device=device,
               gpu=torch.cuda.get_device_name(0) if device == 'cuda' else platform.machine())
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def atomic_checkpoint(path, value):
    tmp = Path(str(path)+'.tmp')
    torch.save(value, tmp)
    os.replace(tmp, path)


def loader(data, split, cfg, epoch=None):
    limit = cfg['train_limit'] if split == 'train' else cfg['eval_limit']
    generator = torch.Generator().manual_seed(cfg['seed'] + (epoch or 0))
    return DataLoader(data.windows(split, limit), batch_size=cfg['batch_size'],
                      shuffle=epoch is not None, generator=generator, num_workers=0)


@torch.no_grad()
def predict(model, data, split, cfg, device):
    model.eval()
    predictions, origins = [], []
    for x, _, k in loader(data, split, cfg):
        predictions.append(model(x.to(device)).prediction.cpu().numpy().astype('float64'))
        origins.append(k.numpy())
    origins = np.concatenate(origins)
    pred = np.concatenate(predictions) * data.arrays['target_std'] + data.arrays['target_mean']
    actual = data.arrays['targets'][origins[:, None] + np.arange(1, 5)]
    if not np.isfinite(pred).all():
        raise FloatingPointError('Nonfinite prediction')
    return actual, pred, origins


def metric_report(y, pred, target, trigger):
    error = np.abs(y.astype('float64') - pred.astype('float64'))
    total = float(error.sum())
    cells = {}
    for t, r in ((True, True), (True, False), (False, True), (False, False)):
        mask = (target == t) & (trigger == r)
        n = int(mask.sum())
        s = float(error[mask].sum())
        cells[f'target_{int(t)}_trigger_{int(r)}'] = dict(n=n, mae=s/n if n else None,
              sum_absolute_error=s, error_contribution=s/total if total else 0.)
    mae = float(error.mean())
    reconstructed = sum(c['sum_absolute_error'] for c in cells.values()) / error.size
    gap = abs(mae-reconstructed)
    if gap > 1e-9:
        raise AssertionError('Four-cell reconstruction failed')
    return dict(n=int(error.size), mae=mae, rmse=float(np.sqrt(np.mean((y-pred)**2))),
                event_mae=float(error[target].mean()) if target.any() else None,
                stable_mae=float(error[~target].mean()) if (~target).any() else None,
                by_horizon_mae=error.mean(axis=(0,2)).tolist(),
                by_node_mae=error.mean(axis=(0,1)).tolist(), four_cells=cells,
                four_cell_reconstruction_error=gap)


def environment(device):
    return dict(python=platform.python_version(), platform=platform.platform(),
                torch=str(torch.__version__), numpy=np.__version__, cuda=torch.version.cuda,
                device=device, gpu=torch.cuda.get_device_name(0) if device=='cuda' else None)


def train(data, cfg, out, device='cuda', resume=False, stop_after=None):
    """Only train and tuning are touched. Interruption limit is not a scientific budget."""
    out = Path(out)
    setup(cfg['seed'], device, cfg['threads'])
    fingerprint = contract(data, cfg, device)
    model = build_model(cfg['model'], data.arrays['graphs']).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['lr'], weight_decay=cfg['weight_decay'])
    start, history, best, stale = 0, [], float('inf'), 0
    if out.exists() and any(out.iterdir()) and not resume:
        raise FileExistsError(f'Refusing overwrite: {out}; use --resume')
    out.mkdir(parents=True, exist_ok=True)
    if resume:
        ckpt = torch.load(out/'last.pt', map_location='cpu', weights_only=True)
        if ckpt.get('contract') != fingerprint:
            raise ValueError('Checkpoint contract mismatch: code/data/config/device/environment changed')
        model.load_state_dict(ckpt['model'], strict=True)
        optimizer.load_state_dict(ckpt['optimizer'])
        start, history, best, stale = ckpt['epoch'], ckpt['history'], ckpt['best'], ckpt['stale']
        torch.set_rng_state(ckpt['rng'])
        if device == 'cuda':
            torch.cuda.set_rng_state_all(ckpt['cuda_rng'])
        if ckpt['complete']:
            return ckpt
    write_json(out/'config_resolved.json', dict(cfg, dataset_sha256=data.digest,
        code_sha256=code_digest(), contract=fingerprint, trainable_parameters=count_parameters(model)))
    write_json(out/'environment.json', environment(device))
    if not (out/'environment.txt').exists():
        with (out/'environment.txt').open('w') as f:
            import sys
            subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=f, stderr=subprocess.STDOUT, check=True)
    for epoch in range(start, cfg['max_epochs']):
        tic = time.monotonic()
        model.train()
        loss_sum, count = 0., 0
        for x, y, _ in loader(data, 'train', cfg, epoch=epoch):
            optimizer.zero_grad(set_to_none=True)
            prediction = model(x.to(device)).prediction
            loss = torch.nn.functional.l1_loss(prediction, y.to(device))
            if not torch.isfinite(loss):
                raise FloatingPointError('Nonfinite training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg['gradient_clip'], error_if_nonfinite=True)
            optimizer.step()
            loss_sum += float(loss.detach()) * y.numel()
            count += y.numel()
        y, pred, _ = predict(model, data, 'tuning', cfg, device)
        score = float(np.abs(y-pred).mean())
        improved = score < best
        if improved:
            best, stale = score, 0
        else:
            stale += 1
        row = dict(epoch=epoch+1, train_standardized_mae=loss_sum/count,
                   tuning_mae=score, seconds=time.monotonic()-tic)
        history.append(row)
        print(json.dumps(dict(model=cfg['model'], seed=cfg['seed'], **row)), flush=True)
        ckpt = dict(contract=fingerprint, model=model.state_dict(), optimizer=optimizer.state_dict(),
                    epoch=epoch+1, best=best, stale=stale, history=history,
                    rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if device=='cuda' else [],
                    complete=stale >= cfg['patience'] or epoch+1 >= cfg['max_epochs'])
        # Best is saved first; if last-save is interrupted the deterministic epoch
        # is repeated. Neither calibration nor test participates in this decision.
        if improved:
            atomic_checkpoint(out/'best.pt', dict(contract=fingerprint, model=model.state_dict(), epoch=epoch+1, tuning_mae=score))
        atomic_checkpoint(out/'last.pt', ckpt)
        write_json(out/'train_log.json', history)
        if ckpt['complete'] or (stop_after is not None and epoch+1 >= stop_after):
            break
    return ckpt


def export(data, cfg, out, device='cuda'):
    out = Path(out)
    setup(cfg['seed'], device, cfg['threads'])
    expected = contract(data, cfg, device)
    last = torch.load(out/'last.pt', map_location='cpu', weights_only=True)
    best = torch.load(out/'best.pt', map_location='cpu', weights_only=True)
    if last.get('contract') != expected or best.get('contract') != expected or not last['complete']:
        raise ValueError('Incomplete training or checkpoint contract mismatch')
    model = build_model(cfg['model'], data.arrays['graphs']).to(device)
    model.load_state_dict(best['model'], strict=True)
    reports = {}
    for split in ('tuning', 'calibration', 'test'):
        y, pred, origins = predict(model, data, split, cfg, device)
        target, trigger = data.masks(origins)
        reports[split] = metric_report(y, pred, target, trigger)
        target_indices = origins[:, None] + np.arange(1, 5)
        np.savez_compressed(out/f'predictions_{split}.npz', y_true=y, y_pred=pred,
             origins=origins, node_ids=data.arrays['node_ids'], target_event=target,
             rule_trigger=trigger, target_timestamps_ns=data.arrays['timestamps_ns'][target_indices],
             origin_cutoff_ns=data.arrays['timestamps_ns'][origins]+900_000_000_000)
    write_json(out/'metrics.json', dict(mode=cfg['mode'], unit='retrospective proxy kWh/15min',
                                      selected_epoch=best['epoch'], splits=reports))
    if hasattr(model, 'relation_weights_gcn1'):
        write_json(out/'beta.json', {f'layer_{i}': getattr(model, f'relation_weights_gcn{i}').softmax(0).detach().cpu().tolist() for i in (1,2)})
    (out/'exit_code.txt').write_text('0\n')
    write_json(out/'run_summary.json', dict(status='complete', mode=cfg['mode'],
        artifact_path=str(out.resolve()), contract=expected, best_epoch=best['epoch']))
    write_json(out/'manifest.json', {p.name: sha256(p) for p in sorted(out.iterdir())
                                   if p.is_file() and p.name != 'manifest.json' and not p.name.endswith('.tmp')})
    return reports

```

## 完成报告
在`docs/thesis/blueprints/tasks/REV-20261018-claude-bounded/execution-report.json`填写Claude Code工作报告。changed_paths使用项目根目录相对路径，仅列实际工作区改动，不必列报告自身；列出证据来源、检查、未解决事项，以及所有数字或主张变化。报告只供Codex复检，不代表验收。
在`model`字段填写当前Claude Code会话实际报告的模型标识；`user_reported_model`只是操作者标签。若provider返回`unrecognized_model`，把原始模型名和诊断写入`unresolved`，不要猜测或自动替换模型。
如证据不足、需要扩大修改范围或发生未授权操作，停止继续并在报告中说明。
