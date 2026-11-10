# ACN-A-TIER-20261102

本目录归档 2026-11-02 ACN A 档取数可行性验证与测试期 15 min 半计量标签构造的归档证据（含 15 min 分箱标签）。原始工作缓存为 `.cache/acn-a-tier/`；本包是逐字节复制后的权威归档副本，原缓存保留为本地工作目录。

## 1. 目的与来源

- **目的**：验证 ACN-Data REST API `/ts` 能否按 `connectionTime` 窗口精准取数，并在 2021-03-12 → 2021-09-14 的 Caltech 测试期上，为论文的 10 个节点构造 15 min 半计量标签。
- **接口**：`https://ev.caltech.edu/api/v1/sessions/caltech/ts`（ACN-Data / Caltech）。
- **认证**：脚本运行时从 macOS Keychain 服务 `acn-api` 读取 token；token 不写入日志、JSON 或 Git。
- **时间**：可行性汇总 `feasibility.json` 生成于 `2026-11-02T08:45:57+00:00`；分箱取数日志同为 2026-11-02。
- **论文落点**：`docs/thesis/acn-timeseries-audit-20261102/c-a-tier-results.md`；图件来源见 `docs/thesis/revision-20261102-delivery/figure-proposals.md` 与 `outputs/figures/manifest.json`。

## 2. 目录与文件

| 路径 | 内容 | Git |
| --- | --- | --- |
| `feasibility.json` | 15 次只读探测的结构化汇总：`where` 语义、体积/耗时、取数计划、遥测覆盖与风险 | 入仓 |
| `notes.md` | 可行性结论、`where` 日期格式陷阱、体积账、数据缺口与推荐取数策略 | 入仓 |
| `revaluation.json` | 冻结预测在半计量标签子集上的复评指标（6 个模型×种子组合） | 入仓 |
| `session_stats.csv` | 1,200 条可用会话的逐会话统计：片数、样本数、反推电压、两种积分能量与相对误差 | 入仓 |
| `test_window_manifest.csv` | 测试窗内 10 节点 2,606 条会话清单（`sessionID`/`spaceID`/`connectionTime`/月份） | 入仓 |
| `no_current.csv` | 41 条 `chargingCurrent` 为空、无法构造电流分箱的会话 | 入仓 |
| `probe_results.jsonl` | 每次探测的 URL（不含 token）、状态码、耗时、字节数、`_meta` 与字段名 | 入仓 |
| `items_probe.jsonl` | 探测返回的逐会话元数据（电流/时间戳/pilot 点数等） | 入仓 |
| `raw_item_sketch.json` | 单条原始记录结构草图（`userInputs`、遥测键等） | 入仓 |
| `_p5.json`、`_p6.json` | 两个关键探测（RFC1123 窗口、按 `sessionID` 过滤）的请求/响应元数据 | 入仓 |
| `_sample_sids.json` | 探测用 20 个会话 ID 样本 | 入仓 |
| `_probe_count.txt` | API 探测预算计数器（本次 15） | 入仓 |
| `fetch_bins.log`、`fetch_bins2.log` | 分箱取数进度日志；最终 `FINISHED 1241 of 1241` | 入仓 |
| `inputs/bins.csv` | 22,105 行 15 min 分箱标签；列 `e208_kwh`（固定 208 V）、`eeff_kwh`（能量匹配电压）、`uniform_kwh`（电量均摊） | 入仓（2.2 MB；CRLF 由 `.gitattributes` 保留） |
| `inputs/static_paths.json` | 56,680 条 Caltech 静态时序文件路径索引（ACN-Data-Static；三站合计 85,877 条） | **不入仓**，哈希锁定 |

脚本不在本目录，位于 `scripts/acn_a_tier/`：

| 脚本 | 作用 |
| --- | --- |
| `probe.py` | 只读探测 `/ts`，写入 `probe_results.jsonl`、`items_probe.jsonl`、`_probe_count.txt` |
| `build_manifest.py` | 从本地 checkpoint 构建 `test_window_manifest.csv` |
| `assemble_feasibility.py` | 由探测记录与清单汇总 `feasibility.json`，不手填数字 |
| `fetch_bins.py` | 按 7 个月窗口取数，构造 `bins.csv`、`session_stats.csv`、`no_current.csv` |

## 3. 关键结果

- **取数可行，但有条件**（`FEASIBLE_WITH_CONDITIONS`）：`where` 真实生效，且只有 `connectionTime` 有索引。
- **日期格式是硬约束**：`where` 只认 RFC1123（如 `"Fri, 12 Mar 2021 00:00:00 GMT"`）；ISO-8601 不报错、返回 200、`_meta.total=0`。
- **规模**：测试窗 2,606 条会话；10 节点目标会话 1,241 条；7 个自然月窗口、29 页、约 477.8 MiB、约 6.5 分钟。
- **电流覆盖**：1,200/1,241（96.7%）取到可用电流；41 条为空，列入 `no_current.csv`。
- **关键缺口**：车位 `11900388`（station `2-39-81-4550`）在 107/107 条抽样记录中 `chargingCurrent` 与 `pilotSignal` 均为 `null`，却占测试窗 833/2,606（32.0%）会话。
- **电压假设**：A 档无电压采样，用 `kWhDelivered / ∫I dt` 反推等效电压，中位 **223.8 V**；固定 208 V 的能量偏差中位 **−7.1%**，故标签采用能量匹配电压。
- **形态差异**：半计量与均摊标签的 TV 中位 **0.504**，逐片平均绝对差中位 **0.277 kWh/15 min**。
- **子集复评**：87,884 个测试键（占 708,560 的 **12.4%**，偏向活跃时段）；MRG-GCN 代理标签 MAE 约 **0.277–0.281**，半计量标签约 **0.436–0.438**；容量近似 TCN 同向，排序未翻转。

## 4. 边界

1. **“半计量”不是独立计量**：电流来自设备上报，A 档没有电压采样，电压是能量匹配反推值，不能称为实测功率。
2. **子集复评不是全局复评**：只覆盖 12.4% 的测试键且偏向活跃时段，不能外推到全局 MAE 或模型排名。
3. **不改变冻结结果**：本包不重训、不改预测、不改论文现有全局 MAE 与排序；它衡量的是标签敏感度。
4. **原始采样序列未保存**：仅保留 15 min 分箱与逐会话统计，原始数组不落盘。
5. **许可与再分发**：ACN-Data 的使用受官方数据集条款约束；本包只归档派生统计与探测元数据，不包含原始高频时序。

## 5. 复现

在仓库根目录运行：

```bash
# 1) 只读探测（会消耗 API 预算，写入 .cache/acn-a-tier/）
python3 -B scripts/acn_a_tier/probe.py <experiment>

# 2) 从本地 checkpoint 构建测试窗清单
python3 -B scripts/acn_a_tier/build_manifest.py

# 3) 汇总探测结果为 feasibility.json
python3 -B scripts/acn_a_tier/assemble_feasibility.py

# 4) 取数并构造 15 min 分箱（写入 .cache/acn-a-tier/）
python3 -B scripts/acn_a_tier/fetch_bins.py
```

注意事项：

- 脚本保留**原始运行路径**。`fetch_bins.py` 的 `ROOT` 硬编码为作者本机仓库路径，移植到其他机器时需改为仓库根目录；其余三个脚本使用仓库根目录下的相对路径。
- `build_manifest.py` 与 `assemble_feasibility.py` 依赖 `.cache/acn-audit-20261102/checkpoint_caltech_windowed.json`（约 3.6 MB，未入仓）；其 SHA-256 与字节数登记在 `source-provenance.lock.json` 的 `external_dependencies`。
- 运行需要 macOS `security` 命令与 Keychain 中的 `acn-api` 条目；其他平台需替换 `token()` 实现。
- 探测有预算上限：`probe.py` 读取并递增 `_probe_count.txt`（本次 15 次）。
- 复跑会写入 `.cache/acn-a-tier/`，不会改写本归档包；本包文件是 2026-11-02 运行的冻结副本。

## 6. Git 策略与来源锁定

- 仓库 `.gitignore` 默认规定原始、中间与正式数据不进入 Git。本包对 `inputs/bins.csv`（2.2 MB，15 min 半计量标签）做了一次显式、路径限定的例外，因为它是 A 档标签敏感度结论的核心证据；`inputs/static_paths.json`（7.8 MB）仍按默认规则留在仓外并哈希锁定。
- 入仓文件与 `.cache/acn-a-tier/` 中的对应文件逐字节相同；全部文件（含 `inputs/`）的 SHA-256 与字节数见 `source-provenance.lock.json`。
- `inputs/static_paths.json` 仍在 `.gitignore` 中排除，不会进入版本库；`inputs/bins.csv` 已纳入 Git，并由 `.gitattributes` 的 `-text` 规则保持 CRLF 字节稳定。
- `.cache/acn-a-tier/` 原目录保留，现有论文文档中的历史路径引用仍然可以解析；本包路径是后续引用的权威位置。
