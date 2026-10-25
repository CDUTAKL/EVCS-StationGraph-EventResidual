# EPFL Level-3 代理形态核验报告（V2，探索性）

## 范围与证据级别
仅核查EPFL-DESL Level-3公开数据能否为论文节点负荷代理提供有限的外部形态参照。V1以`CCS + Session`严格连接，CCS2为0/749，核验停止；V2改用`CCS + Arrival + Departure`建立时间边界连接，连接键不含能量字段。本报告为探索性证据，不涉及检查点推理、再训练、模型评分或ACN目标规则校准。

## 数据源与哈希
- `data/external/epfl-l3-20261021/Session_data.xlsx`：204,514 B，SHA-256 `b886943bf86520f24f5a53870886c4c43709d265cbebdd65e1345321e22cc192`。
- `data/external/epfl-l3-20261021/Measurement_data.xlsx`：23,558,382 B，SHA-256 `a0a489e2897ec79235ed914376ab7751ab21c68418543234a60042eaee73a89c`。
- 协议：`docs/thesis/revision-20261022-evidence/epfl-proxy-audit-v2-protocol.md`，SHA-256 `7295655ddb23d8602a40ddf277a94e09087f75009b57e46ca8143d9e4fe76075`；V1协议保留于`revision-20261021-evidence/epfl-proxy-audit-protocol.md`。

结构：会话表`Session_data` 1,878行；测量表`CCS1`、`CCS2`各646,680行，合计1,293,360行。会话列含Session、CCS、Arrival、Departure、Energy；测量列含Timestamp、CCS、Session、Power、Energy。

## 步骤
1. 解析1,878条会话与1,878个测量组，按CCS、Arrival、Departure一对一连接；不把Session作为跨表键。
2. 匹配后按持续时长≥15 min筛选，剔除258条，保留1,620条。
3. 测量按连续60 s间隔核验；以Arrival为锚分为15 min片，相邻功率样本作梯形积分。均匀参照按各片覆盖时长分配会话电量，最后一片允许不足15 min。
4. 按V2协议计算每会话总变差距离，以及P积分、累计能量差相对会话电量的比值。

## 结果
连接：1,878对一一匹配；CCS1 1,129、CCS2 749；没有Session标识、未参与会话分组的测量表行1,231,544。剔除258条后eligible 1,620（CCS1 973、CCS2 647）。

形态（总变差距离，等会话）：n=1,620，中位数0.0736，Q1 0.0308，Q3 0.1276，IQR 0.0968，均值0.0887；CCS1中位数0.0741（Q1 0.0316，Q3 0.1283），CCS2中位数0.0720（Q1 0.0301，Q3 0.1261）。

能量闭合：P积分/会话电量中位数1.1492（Q1 1.1373，Q3 1.1627）；累计电量差/会话电量中位数0.9943（Q1 0.9851，Q3 0.9998）；n=1,620。

## 解释边界
- 探索性结果，不构成校准、ACN目标误差、模型验证或运行收益。
- 分箱以会话Arrival锚定、按片段覆盖时长分配电量；论文Eq2-1为固定时钟等片份额，口径不同，不得称为逐片实测校准。
- P列为表内功率字段轨迹，不上升为充电枪口计量；P计量边界与时间戳语义未明，时间戳按朴素墙钟处理，未确认UTC或夏令时。
- 仅两个CCS端口，无ACN十节点映射、站内关系图或96×10×7输入契约；不能外推至论文站点。
- 1,620会话的形态距离是分布差异度量，不是误差率，也不与模型MAE比较。
## 复算入口与覆盖

```bash
python3 scripts/audit_epfl_proxy_shape_v2.py --session data/external/epfl-l3-20261021/Session_data.xlsx --measurements data/external/epfl-l3-20261021/Measurement_data.xlsx --out epfl-audit.json
```

脚本核验两张测量表、固定字段、无Energy连接、时间戳原顺序严格递增且唯一、连续一分钟覆盖、完整首末边界、有限非负功率及正能量。1,878对均通过连接，258条仅因时长不足15 min排除；其余门禁本次未排除会话。没有Session标识的行不属于本次会话轨迹核验范围，不能当作完整场站连续负荷。

本轮第一次草稿只读CCS1，已在入稿前纠正，最终输出包含CCS1和CCS2；未变更冻结V2纳排或V1历史记录。所有统计均来自最终双表重跑。README称64,277条测量；本地两表含Session标识且可分组的行共61,816条，两种计数并非同一定义，本报告不将其混用。原工作簿SHA-256保持不变。

