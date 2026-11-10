# ACN 设备功率锚定分析：报告与新增分析归档（2026-11-10）

本目录收录 2026-11 上旬完成的 ACN-Data Static 设备功率锚定分析的全部**文字报告**，以及两项**新增分析**（跨车场功率覆盖率普查、标签伪影诊断）的脚本与汇总结果，外加 2021 独立测试期核验报告与论文 5.4 节补充文字。所有数字可由所引脚本与结果 CSV 复算。

**研究性质**：全部为论文主模型**训练时期内**的探索性标签口径核验（2021 报告为独立测试期复核），不是独立测试集上的模型预测效果比较。

## 文件清单

| 文件 | 内容 | 关键数字 |
|---|---|---|
| `ACN设备功率锚定分析报告.md` | v3 主报告：双通道锚定（累计电表差分 A / 功率积分 B）、同样本对照、外推三层判断、复现材料清单 | 2,599→2,335 会话；TVD 中位 0.398→0.179（−54.9%）；节点 MAE −46.5%（A）/ −48.6%（B）；同样本 1,830 会话两通道总量比 0.9693；完成后电量占比 均分 24.075%（加权）vs 电表 0.051% / 功率 0.0029% |
| `ACN功率覆盖率普查报告.md` | 附录 B：七个车场 85,877 个文件按车场×年份分层抽样 420 个的功率覆盖率普查 | 96.9% 文件内部覆盖率 ≥0.95（中位 1.0）；JPL 2018–2019 功率列全空、仅 2020 起可用；CG1 2018-04 无文件为数据源 artifact |
| `标签伪影诊断报告.md` | 附录 C：解释第 4 章非零层排序相关 0.420 的逐键诊断 | 伪非零键率 50.2%→12.4%（4,741→979 kWh）；完成后主导键误差占比 34.4%→5.4%；事件边界键伪非零 29.2%→7.9%；按占桩比分层 18.7%→77.1% vs 截断 2.3%–17.6% |
| `2021测试期核验报告.md` | 2021-03-12~09-14 独立测试期两项核验（标签总量标定/电压推断稳定性 + 完成后电量占比） | 总量最大偏差 0.85%；208V 节点推断电压中位 224.1V（r=−0.017）；CA-321 为真实 120V 回路（渐近 122.4V，“82 条低压会话”身份确证）；半计量完成后占比 1.45% vs 均分 37.2%（208V 中位 0.73%，CA-321 恒定 0.9A） |
| `论文5.4节补充文字与审稿回复.md` | 可直接并入论文的 5 段补充文字 + 评审意见 1–10 逐条回复 | 独立测试期复核段（回应“训练期内核验”边界）；意见 9/10 为新增回复 |
| `scripts/coverage_survey.py` | 附录 B 普查脚本（分层抽样、CDN 下载、逐文件指标、汇总一体；种子 20261110） | 依赖 `/tmp/garage_files.json` 清单（GitHub API 抓取） |
| `scripts/label_artifact.py` | 附录 C 伪影诊断脚本（与 extended_analysis 同口径：严格完成时刻、60s 缺口、覆盖率 ≥0.95 子集 n=1,795） | 输出逐键明细、分层、节点与汇总 |
| `results_survey/` | 普查结果：`survey_summary.csv`（分层汇总）、`survey_meta.json`（来源/种子/口径）、`survey_files.csv`（350 行逐文件指标） | — |
| `results_artifact/` | 伪影诊断结果：`artifact_summary.json`、`artifact_idle_strata.csv`、`artifact_node.csv` | 逐键 `artifact_bins.csv`（7.7 MB）与会话级 `artifact_sessions.csv`（313 KB）因体积不入仓，可由脚本复现 |

## 与其他分支的关系（避免重复入仓）

- **核心脚本与基准结果**：`anchor_analysis.py`、`extended_analysis.py`、`download_static.py`、`make_figures.py` 及 `results/`（node_*、sensitivity_*、multiscale_*、mechanism_*、representativeness_*、uncertainty_*、after_done_exact_summary、extended_summary.json）、图件 `fig_E1`–`fig_E5` 已完整收录于分支 **`codex/acn-anchor-v3-extensions-20261110`** 的 `docs/thesis/evidence/acn-anchor-extensions-v3-20261110/`（含 SHA256SUMS 与 source_manifest.json 哈希锁定）。该处 `extended_analysis.py` 默认输入路径已改为包内相对路径，计算逻辑未改。本分支不重复收录，以该分支为这两个脚本的入仓版本。
- **2021 测试期数据**：逐箱 `bins.csv`（22,105 行，SHA-256 4557f1c7…832f）、`session_stats.csv`、`no_current.csv`、`fetch_bins.py`、锁文件等已收录于 PR #2 分支 `archive/acn-a-tier-20261102`（`outputs/analysis/ACN-A-TIER-20261102/`）。本分支基于该分支提交 a2b2e84。

## 未入仓内容（及原因）

| 内容 | 原因 |
|---|---|
| 89 MB v3 复现 ZIP、2,341 个原始时序文件、会话 JSON | 原始数据不入 Git（哈希锁定于 source_manifest / 锁文件） |
| `results_extended/extended_stores.pkl`（56 MB） | 脚本运行检查点，可复现 |
| `results/session_anchor.csv`（769 KB）、`results/download_manifest.csv`（276 KB） | 运行输出/逐文件清单，可由脚本重新生成；清单哈希已锁定 |
| `results_artifact/artifact_bins.csv`（7.7 MB）、`artifact_sessions.csv`（313 KB） | 体大且可由 `label_artifact.py` 复现 |
| `results/fig1`–`fig7` PNG | 可由 `make_figures.py` 重新生成（fig_E1–E5 已在 codex 分支入仓） |
| ACN API token | 仅存于用户本机 Keychain，绝不写入磁盘/Git/日志 |

## 运行方式（新增的两个脚本）

```bash
# 附录 B 普查（需先由 GitHub API 抓取 /tmp/garage_files.json 清单）
python3 scripts/coverage_survey.py

# 附录 C 标签伪影诊断（需原始时序目录与会话 JSON，路径由环境变量指定）
ACN_SESSIONS=/path/to/acndata_sessions-2.json ACN_TS_DIR=/path/to/static \
  python3 scripts/label_artifact.py
```

`label_artifact.py` 复用 `extended_analysis` 的口径与函数，需与入仓于 codex 分支的 `extended_analysis.py`、`anchor_analysis.py` 同目录放置。
