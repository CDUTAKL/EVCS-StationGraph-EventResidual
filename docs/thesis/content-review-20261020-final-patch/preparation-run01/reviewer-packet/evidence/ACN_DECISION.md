# ACN接口范围核验的数据决策（2026-10-19）

任务：REV-20261019-NONTRAIN-CLOSEOUT（NT-01）。本文件登记本轮对ACN官方会话元数据端点的只读边界核验及其可支持的文本结论。核验不涉及训练、模型推断、会话时序下载或凭据查询。

## 1. 核验对象与时间

- 范围探测时间：2026-10-19T06:02:57.685593+00:00。
- 区间外计数时间：2026-10-19T06:06:36.557679+00:00。
- 端点：ACN官方普通会话元数据接口，不含时序。
- 查询方式：对三站点分别按`connectionTime`升序与降序各取一次边界值；再对每站执行严格低于候选下界、严格高于候选上界的`where`计数。共6个`where`查询。
- 数据保存：原始响应未保存；仅保留查询元数据、响应SHA-256和匹配计数。普通端点返回的payload曾在内存中处理，但未保存或展示用户记录；凭据未保存。

## 2. 三站点数量与UTC连接时间极值

| 站点 | `site_id` | 会话数 | 最早`connectionTime`（UTC） | 最晚`connectionTime`（UTC） | 下界外计数 | 上界外计数 |
|---|---|---:|---|---|---:|---:|
| Caltech | `caltech` | 31,424 | 2018-04-25 11:08:04 | 2021-09-14 01:52:37 | 0 | 0 |
| JPL | `jpl` | 33,638 | 2018-09-05 11:04:13 | 2021-09-14 05:43:39 | 0 | 0 |
| Office 1 | `office001` | 1,683 | 2019-03-25 16:24:42 | 2021-09-13 21:21:51 | 0 | 0 |

6个严格`where`查询均返回HTTP 200，且每个站点的下界外与上界外计数均为0。因此，上述候选极值在`connectionTime`维度上成立，未发现2021年9月之后的接入时间记录。

逐项`where`与响应：

| 站点 | `where` | 匹配数 | HTTP | 响应SHA-256 |
|---|---|---:|---:|---|
| Caltech | `connectionTime<"Wed, 25 Apr 2018 11:08:04 GMT"` | 0 | 200 | `0392e8121a25fd016265a7fb3ac5e43dff69adde6e5ddff845f95e25a194297c` |
| Caltech | `connectionTime>"Tue, 14 Sep 2021 01:52:37 GMT"` | 0 | 200 | `0392e8121a25fd016265a7fb3ac5e43dff69adde6e5ddff845f95e25a194297c` |
| JPL | `connectionTime<"Wed, 05 Sep 2018 11:04:13 GMT"` | 0 | 200 | `de48d802736d205567d72c949dfcb8a638bb53736ef75d6dd531f9e75b31eea1` |
| JPL | `connectionTime>"Tue, 14 Sep 2021 05:43:39 GMT"` | 0 | 200 | `de48d802736d205567d72c949dfcb8a638bb53736ef75d6dd531f9e75b31eea1` |
| Office 1 | `connectionTime<"Mon, 25 Mar 2019 16:24:42 GMT"` | 0 | 200 | `6ca77754695e88f7657e6eb2f1f508cd7ab7641ed08cb20172e89d469f1898bc` |
| Office 1 | `connectionTime>"Mon, 13 Sep 2021 21:21:51 GMT"` | 0 | 200 | `6ca77754695e88f7657e6eb2f1f508cd7ab7641ed08cb20172e89d469f1898bc` |

边界值响应的SHA-256（升序/降序）：

- Caltech：`8d9d1ddbbb9f1fa2938040cc90f302db71695daa5afef834769e7d3c64b49695` / `6310f67f53bfc5456d239f84612a699a979f54a509381d6bd9a14c49b22dd3d6`。
- JPL：`af325900ab6bb76615ef3a9b9ce0f2410cf8cb12ab699ee2aacabb87fc833797` / `6e165a5adc997ec167b880b020a26ab6b7b3e862a4152d529eb5c9e3f536f99b`。
- Office 1：`81f94880622cca3db2631dc86bcdbf39fe775649ee6ffd0e143d7015afeecda0` / `f1a1e1476d34166997dfc334e252f835c2434479b199535b77b1bd977d201f94`。

## 3. 来源文件与哈希

| 文件 | SHA-256 | 说明 |
|---|---|---|
| `range_probe.json` | `25a3aacea4662049fac8dfac0a934916610e393395fb5cb08434c04a55f0eb43` | 原范围探测输出，保留；原脚本标签相对返回时间戳颠倒 |
| `range_probe_reviewed.json` | `84ec68aaf9c9d8b35acb928821a289464a5f66fbb4f946cdb754044b59055ae6` | 按返回时间顺序订正极值；含`interpretation`与`verification_limit` |
| `bounds_verification.json` | `430bb7fffbbf62dd5ef92f4099a6ff455dda3362de195d273d36df02fa260b05` | 6个`where`计数、HTTP状态与响应哈希 |
| `provenance.json` | `6089bdc07aee0ba0967606567bb4866f30f2517775791e912f967ad307bae431` | 复制来源、审计范围与保存边界 |

上述文件位于`docs/thesis/revision-20261019-nontraining/evidence/acn/`；原始来源路径与复制哈希见`provenance.json`。

## 4. 原脚本标签订正

原`range_probe.json`的最早/最晚标签与返回时间戳的实际先后相反。`range_probe_reviewed.json`未覆盖原文件，而是按两个返回的`connectionTime`边界值重新计算chronological min/max，并在`interpretation`中记录：

> Chronological min/max computed from the two returned connectionTime boundary values; original script labels were inverted relative to the returned timestamps.

原文件及其哈希保留，便于复核。正文和证据控制台只采用订正后的极值。

## 5. 可支持与不可支持的结论

可支持：

- 三站点在核验时点的`connectionTime`最早/最晚值；
- 对每站候选下界和上界各执行一次严格`where`查询，6次均返回0条，因此该端点返回的会话中未发现晚于2021年9月的接入时间；
- Caltech计数31,424与既有主归档会话数一致；JPL计数33,638与既有JPL元数据计数一致。

不可支持：

- 完整新数据快照、未查看时期或独立时间确认集。核验只返回边界值和计数，未保存或下载会话时序。
- 各站点的节点标识、字段完整性、标签成熟性，以及其与既有10节点定义和预测输入的兼容性。
- Office 1的既有分析使用史或可运行性。1,683条会话不是跨站性能证据，也不是零样本迁移证据；Office 1仅作为候选站点。
- 对其他数据源不可得的证明。未核验Zenodo、路侧充电记录或其他入口；本轮结论不覆盖这些来源。
- 实测功率、输入到达延迟、运行收益或计量映射。

## 6. 正文与证据入口

- 正文`研究局限与后续工作`以一句说明：ACN时间范围核验未发现晚于既有时期的记录，后续独立验证需另行取得兼容数据，Office 1仍待节点和字段核查。完整快照、其他数据源不可得等边界保留在本文件和证据控制台，不堆入正文。
- `data-availability.md`、`claim-evidence-map.md`、`material-passport.md`的当前入口已登记本材料及其哈希。
- 前次WebFetch失败记录保留原文，并在文首加2026-10-19后续状态说明；旧“未知”结论不撤销。

## 7. 未执行操作

本轮未训练、未连接远端、未下载会话时序、未查询或保存凭据、未修改正式DOCX、未暂存或提交Git。
