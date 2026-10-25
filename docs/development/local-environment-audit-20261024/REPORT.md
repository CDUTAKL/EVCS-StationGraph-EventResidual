# 本地环境误重建：核查与纠正

## 2026-10-24恢复执行补记（2026-10-25备份复核）

本节更新于2026-10-24 20:00（Asia/Shanghai）。下文第1—6节记录了首次核查时的状态；当时项目`.venv`仍是Python 3.14.5的事故后重建环境。随后已按历史运行清单建立隔离候选、完成验证，并切换为项目当前`.venv`。因此，下文第3、4、6节的“当前环境”数据已由本补记取代；它们仍保留为时间记录，不代表现在状态。

**当前结论：已按可验证的历史运行记录重建项目环境，并完成范围明确的功能验证；不能称为事故前环境的完美或逐字节恢复。**没有事故发生前一刻的完整备份或快照。能确认的是Python 3.12.14 ARM64，以及历史清单中的61项固定依赖均版本匹配。项目源码按当前工作区安装为editable包；没有把工作区回退到清单中的旧Git提交。

| 当前核验项 | 结果 |
| --- | --- |
| 项目`.venv`解释器 | Python 3.12.14，ARM64；路径仍为项目原`.venv` |
| 历史61项固定依赖 | 61/61版本一致；无版本差异。`uv`识别63个唯一包名（另含pip与当前项目editable安装）；`importlib.metadata`会把项目editable包在`.dist-info`和源码树`.egg-info`各枚举一次 |
| 依赖关系 | `uv pip check --python .venv/bin/python`通过 |
| 代表性能力 | 项目CLI、torch CPU前后向、SciPy线性规划、Tigramite、Matplotlib、python-docx、openpyxl工作簿往返等检查通过 |
| 核心非训练测试 | 6个测试文件，70通过、0失败 |
| 已归档SG-EXP-031/032预测复算 | 在切换后复核通过；031标记`POST_HOC_DIAGNOSTIC`，032通过。仅复算保存的预测，未加载检查点、未推理、未训练 |
| 事故后环境回退副本 | 逐项核验24,217个文件SHA-256与3个符号链接目标；无缺失、无额外项、无哈希不符，详见`postincident-backup-verification.json` |
| 研究源文件 | 本轮未改动正文、实验数据、检查点、依赖声明或实验结果 |

仍有两项无法按历史原样恢复：旧`environment.txt`还记录了指向临时目录的`artifact_tool_v2`引用，以及指向历史Git提交`fce67da...`的editable项目安装。前者路径已失效且不是常规研究依赖；后者代码状态与当前工作区不相同，恢复它会覆盖当前项目代码，所以没有这样做。这两项不影响当前`.venv`的基本项目功能，但意味着不能称为历史环境完全复刻。

原Python 3.14.5事故后环境已完整移至`/Users/xushuyuan/.local/share/evcs-environments/incident-20261024/venv-postincident-python3145`以备回退。保存目录的24,220个文件/链接条目列于同目录`postincident-venv-backup-manifest.json`；操作步骤见`BACKUP-RESTORE.md`。该清单描述保存下来的目录内容，不是事故前`.venv`的对照快照。

最新机器记录：`restored-environment.json`、`candidate-validation.json`、`restored-nontraining-tests.xml`、`archived-prediction-recheck-restored.json`、`postincident-backup-verification.json`。2026-10-25重新核对回退副本，24,220项清单与磁盘实际项目完全一致，文件哈希和链接目标全部通过。本补记不表示每个历史训练环境或GPU环境已复现；项目实验仍应遵循各实验自己的源码、数据和环境合同。

首次核查记录：2026-10-24。责任：Codex。结论（限首次核查时）：**当时项目核心代码经过有限范围验证可运行，但环境没有完整恢复，不得宣称事故前环境已经复原。**后续恢复执行状态见本文件开头补记。

## 1. 错误及根因

文档工具缺少依赖时，在项目目录执行了遗漏`--no-project`的`uv run --with ...`。uv发现项目并进入环境解析/同步过程，替换了原`.venv`；首次选择的x86_64解释器又无法匹配所需torch发行包。随后按无上限的项目依赖下限重建为ARM64 Python 3.14.5，使包版本发生漂移。

这是两个连续错误：文档任务越界修改研究环境；随后未先找历史清单，就以新版本安装和少量导入检查判断恢复情况。此前“没有完整包版本快照”的表述过于笼统，现予纠正。

## 2. 找回的历史依据

`outputs/experiments/SG-EXP-032/local-smoke/mrg_full/seed-2024/environment.json`记载Mac ARM64 Python 3.12.14、torch 2.13.0、numpy 2.3.5；同目录`environment.txt`包含61项固定版本，以及可编辑项目和临时artifact运行时引用。SG-EXP-019本地smoke目录也保存了对应清单。

这些是历史运行记录，**不是10月23日误操作前一刻的完整环境备份**。它们足以证明版本漂移并提供恢复候选，不能证明其间没有安装过其他包。本机`tmutil listlocalsnapshots /`未列出本地快照；未据此推断其他备份位置必定不存在。

当前Codex捆绑运行时仍提供ARM64 Python 3.12.14；另一个工作流kit环境中有torch 2.13.0，但numpy、pandas也不同，不能直接冒充原项目环境。本轮未改动该环境。

## 3. 版本与能力差异

| 项目 | 历史本地运行记录 | 当前`.venv` |
| --- | --- | --- |
| Python | 3.12.14 | 3.14.5 |
| torch | 2.13.0 | 2.14.1 |
| numpy | 2.3.5 | 2.5.4 |
| pandas | 2.2.3 | 3.1.0 |
| statsmodels | 0.14.6 | 0.15.0 |
| xgboost | 3.3.0 | 3.4.1 |
| scipy | 1.18.0 | 1.18.1 |

相对上述历史61项固定版本，当前缺少34项，17项版本不同。当前安装31个分发包；比较不把临时artifact源码目录或可编辑项目引用计为固定版本。

缺失项包括matplotlib、python-docx、openpyxl、lxml、Pillow、scikit-learn、tigramite、pypdf、pdfplumber等。它们会阻断依赖这些库的绘图、文档、工作簿、PCMCI等入口；未运行对应入口生成新科研结果。`defusedxml`也未安装在项目环境中，它应保留在独立文档工具环境。

`pyproject.toml`多数只有版本下限，因此依赖自洽不代表历史一致。服务器与云实验requirements属于不同Python/CUDA合同，不能拿来直接覆盖Mac环境。

## 4. 实际执行的检查

| 检查 | 结果与范围 |
| --- | --- |
| `uv pip check --python .venv/bin/python` | 31包依赖自洽；本命令没有执行安装或同步 |
| 项目CLI `--help` | 返回码0；仅验证入口可加载 |
| 6个测试文件 | 70通过、0失败、0错误；包含模型形状/梯度、AGCRN、GraphWaveNet、窗口与预测键、关系图、误差分解；不是全量测试 |
| SG-EXP-031/032来源和预测复算 | 18次运行通过；031核对156个运行文件、173项归档校验，032核对75个运行文件；冻结源码清单和归档验证通过 |
| SG-EXP-032核心差值 | 0.008302002680088615，保持原结论的差值方向；这里只复算既有预测 |
| 当前审计前后环境元数据 | 86个METADATA/RECORD文件哈希全部一致；不等于全磁盘备份 |
| 项目依赖声明 | 对4份依赖声明执行Git差异检查，无差异 |
| 论文MD、最终Word/PDF | 哈希与本轮交付记录所记数值一致，见`current-environment.json` |

测试使用`PYTHONDONTWRITEBYTECODE=1`，关闭pytest缓存，临时文件写入测试目录。测试包含合成张量的前后向运算，不包含优化器训练或正式实验。来源复核使用`scripts/replay_sgexp031_032_evidence.py`，只读既有预测并写新审计记录，没有加载检查点、重新推理、训练或联网。

## 5. 防止再次发生的改动

- 新增根目录`AGENTS.md`，把`.venv`设为项目受保护状态；文档任务不授权修改环境。
- 同步`CLAUDE.md`，使Claude Code执行者也遵守相同规则。
- 临时工具使用捆绑文档运行时；确需uv时，在仓库外临时目录指定已核查解释器，并显式使用`--no-project --no-config`。
- 新增`scripts/audit_local_environment.py`：只读环境清单与哈希，可用于变更前保存证据；拒绝覆写已有报告或写入`.venv`。
- 合法环境维护也必须先备份、后建立独立候选环境，再核验；禁止为了尝试一个方案先替换唯一环境。

这些是项目执行规则和审计手段，**不是操作系统级写保护**，不能声称可拦截任意外部命令。执行者仍须逐条遵守。

## 6. 恢复状态与后续路径

本轮完成检查、证据保存、差异核算与规则补正，**没有继续安装、卸载或替换`.venv`**。可用性只确认到上述范围；历史前向预测的跨版本一致性尚未验证，不应在此环境中生成替代正式数字。

若开展完整恢复，使用现存ARM64 Python 3.12.14建立独立候选环境，按`historical-recovery-candidate.txt`固定版本安装。该文件排除了失效的临时artifact路径和可编辑源码引用，项目源码须另按任务合同绑定。完成依赖、文档/绘图/分析能力、70项核心测试及既有预测复算，再依据真实检查点权限核验前向差异；通过后保留当前环境备份并切换。即使通过，结论也应写为“按历史记录重建并验证”，不能写“逐字节恢复事故前环境”。

## 证据文件

- `current-environment.json`：解释器、完整包版本、86个元数据哈希、历史差异、7个来源哈希核对及交付文件哈希。
- `current-pinned-packages.txt`：当前31项安装版本，仅为事故后状态留档。
- `historical-recovery-candidate.txt`：61项历史固定版本，候选而非已安装环境。
- `capabilities.json`：缺失模块和CLI入口检查。
- `nontraining-tests.xml`：70项测试结果。
- `archived-prediction-recheck.json`：18次既有运行的来源与指标复算记录。
- `environment-unchanged-during-audit.json`：审计前后元数据一致性。
