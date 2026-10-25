# Git 版本管理工作流

## 1. 管理目标

Git 用于保存源代码、实验配置、测试、轻量数据清单和研究文档的演化历史。
原始数据、节点张量、模型权重、预测长表和完整实验输出由实验归档管理，不直接
提交到 Git。这样既能复现代码版本，也能避免仓库被大型文件和敏感数据污染。

## 2. 纳入与排除范围

应纳入 Git：

- `src/` 下的实现代码；
- `configs/` 下的项目配置和实验配置；
- `scripts/` 下的统一执行与汇总脚本；
- `tests/` 下的自动化测试；
- `docs/`、`README.md` 和轻量数据清单；
- `.gitignore`、`.gitattributes`、`pyproject.toml`。

不得纳入 Git：

- `.venv/`、缓存、日志和编辑器状态；
- `data/external/`、`data/interim/`、`data/processed/` 中的实际数据；
- `outputs/` 中的训练结果；
- `*.pt`、`*.pth`、`*.ckpt`、`*.npz` 等权重或张量；
- 密码、令牌、私钥、云端登录命令和含凭据的环境文件。

正式实验只在文档或清单中登记代码提交号、配置、数据清单哈希和远程工件校验和。

## 3. 分支与提交约定

- `main`：始终保持测试通过，可作为正式实验起点。
- `feature/<主题>`：新增模型、数据处理或评价功能。
- `fix/<主题>`：修复缺陷，不改变既定研究口径。
- `experiment/<编号>`：需要改动配置或代码的正式实验准备。
- `docs/<主题>`：仅修改说明、登记表或论文证据文档。

提交信息使用“类型: 简短说明”的形式：

```text
feat: 增加自适应图模型
fix: 修复四格加权还原
test: 增加预测键唯一性检查
exp: 新增 SG-EXP-006 敏感性配置
docs: 更新正式实验运行手册
```

一次提交只处理一个可解释目的。禁止把代码改动、数据更新和无关排版混为一次
提交。

## 4. 每次修改流程

1. 从干净的 `main` 创建主题分支。
2. 先更新或新增实验配置，避免在代码中硬编码实验差异。
3. 对关键边界先补测试，再实施最小修改。
4. 运行全部测试和冒烟实验。
5. 检查 `git diff`，确认没有数据、权重、输出或敏感信息。
6. 提交代码，并在正式实验登记表中记录提交号。
7. 正式实验完成后，只提交指标摘要、清单和校验和，不提交大型工件。

## 5. 提交前最低检查

```bash
.venv/bin/python -m compileall -q src scripts tests
.venv/bin/pytest -q
git status --short
git diff --check
```

正式实验开始前还必须核对：

- 实验编号、配置和三随机种子是否一致；
- 数据切分和预测键是否与登记表一致；
- 输出目录是否带有实验编号和运行时间；
- 环境快照、解析后配置、指标、预测文件和校验和是否齐全；
- 冒烟结果是否明确标记为不可用于论文结论。

## 6. 远程训练规则

远程机器接收的是明确提交号对应的代码快照。训练前记录：

```text
git_commit
experiment_id
resolved_config
data_manifest_sha256
environment_snapshot
```

远程训练结束后，将完整工件归档到指定存储位置，并把归档路径、状态和校验和写入
实验登记表。不要把云端密码、SSH 私钥或临时访问令牌写入仓库。

## 7. 正式论文稿件的版本发布

论文以`docs/thesis/thesis-manuscript.md`为正文源稿；证据表、实验与数据登记、图件源文件、生成脚本和审计清单一并随内容修订提交。仓库已将正式 Word 固定在`outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx`，沿用这一稳定路径保存经核准的正式稿。候选 DOCX 保存在对应修订目录，并标为`candidate`；候选稿不得覆盖正式稿或打正式发布标签。

PDF和重复候选DOCX体积较大。正式版本默认在 Git 中保留正式 Word、正文源稿及轻量发布清单；1200 PPI分页证明PDF单独归档。已提交的PDF审计JSON记录PDF本身的SHA-256、页数、图像数、有效PPI下限及文本一致性结果，发布manifest再锁定该审计JSON的哈希。当前仓库未配置Git LFS，因此不要把每轮大型PDF和候选Word全部提交进历史。只提交一个稳定正式Word版本；后续正式修订产生的Git版本由提交历史保留。

### 候选稿清单

在仓库根目录执行。候选清单记录源稿、证据表、Word/PDF及各项交付审计的哈希，同时标记当时的分支、HEAD和工作区状态；工作区脏时仍可生成，但状态只能是`candidate`：

```bash
python3 scripts/thesis_release.py create \
  --version thesis-candidate-2026-10-17-rev3 \
  --status candidate \
  --artifact manuscript=docs/thesis/thesis-manuscript.md \
  --artifact evidence-map=docs/thesis/claim-evidence-map.md \
  --artifact docx=docs/thesis/revision-20261017-content-refinement/thesis-revision-candidate-rev3.docx \
  --artifact pdf=docs/thesis/revision-20261017-content-refinement/wps-pagination-proof-1200dpi.pdf \
  --artifact toc=docs/thesis/revision-20261017-content-refinement/toc-map-wps-verified-20261017-content-refinement.json \
  --artifact docx-audit=docs/thesis/revision-20261017-content-refinement/docx-audit-rev3.json \
  --artifact figure-audit=docs/thesis/revision-20261017-content-refinement/figure-sync-rev3.json \
  --artifact pdf-audit=docs/thesis/revision-20261017-content-refinement/pdf-audit-rev3.json \
  --artifact delivery-audit=docs/thesis/revision-20261017-content-refinement/delivery-audit.md \
  --output docs/thesis/revision-20261017-content-refinement/git-release-manifest-candidate.json

python3 scripts/thesis_release.py verify \
  docs/thesis/revision-20261017-content-refinement/git-release-manifest-candidate.json
```

### 正式发布

1. 在修订分支完成人工内容审读、WPS目录/分页验收和图件检查。确认正式Word由当前源稿生成，核对数字、图表与审计清单。
2. 逐项检查 `git status --short` 和 `git diff --`；只暂存本轮批准的正文、证据、图件源文件/生成代码、正式Word及审计记录。使用明确路径执行`git add -- <路径...>`，不使用`git add .`。
3. 提交内容版本。候选文件仍保存在修订目录；只有正式确认时，才把核准DOCX复制到上述稳定正式路径并与对应源稿一起提交。
4. 在工作区干净、发布文件已提交后，用`--status release`生成正式manifest。该模式拒绝脏工作区和未跟踪/已修改的发布输入。以下示例假设 rev3 已正式核准、正式 Word 已写入稳定路径，且所列审计清单已纳入内容提交：

```bash
python3 scripts/thesis_release.py create \
  --version thesis-2026-10-17 \
  --status release \
  --artifact manuscript=docs/thesis/thesis-manuscript.md \
  --artifact evidence-map=docs/thesis/claim-evidence-map.md \
  --artifact official-docx=outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx \
  --artifact docx-audit=docs/thesis/revision-20261017-content-refinement/docx-audit-rev3.json \
  --artifact figure-audit=docs/thesis/revision-20261017-content-refinement/figure-sync-rev3.json \
  --artifact pdf-audit=docs/thesis/revision-20261017-content-refinement/pdf-audit-rev3.json \
  --output docs/thesis/releases/thesis-2026-10-17.json

git add -- docs/thesis/releases/thesis-2026-10-17.json
git commit -m "docs: 登记论文交付版本 thesis-2026-10-17"
git tag -a thesis-2026-10-17 -m "正式论文交付 2026-10-17"
python3 scripts/thesis_release.py verify \
  docs/thesis/releases/thesis-2026-10-17.json --require-clean
```

标签指向的提交包含发布manifest；manifest的`source_commit`记录生成清单时已提交的正文与交付物版本。正式标签不得移动或复用；后续修改应生成新提交和新标签。不要在当前大量未提交改动未完成逐项清点时批量暂存或创建正式标签。

工具`scripts/thesis_release.py`只负责哈希清单生成与校验，不替代学术内容审核、Word/WPS全页验收或正式发布判断。它不自动暂存、提交、覆盖正式Word或创建标签。

## 8. Codex蓝图与Claude Code执行

论文修订通过[任务蓝图接口](../thesis/blueprints/README.md)交接。Codex按当前证据控制台为单项任务选取材料、范围和验收条件；`scripts/thesis_blueprint.py`冻结所选摘录与工作区基线，并可在交互终端启动Claude Code。Claude Code沿用本机已配置的模型（用户报告当前为DeepSeek），无需复制聊天记录。默认不给任务开放Shell/网络/远程工具；蓝图明确列出检查或授权操作后，启动参数才开放相应工具，并保留Claude Code的常规权限确认。文件范围核验是事后审计护栏，不是操作系统级隔离；如任务开放Shell，仍须检查实际差异。

```bash
python3 scripts/thesis_blueprint.py new --id REV-YYYYMMDD-topic \
  --title "本次修订目标" --type content_revision --stage 11
python3 scripts/thesis_blueprint.py validate REV-YYYYMMDD-topic
python3 scripts/thesis_blueprint.py run REV-YYYYMMDD-topic
```

蓝图由Codex按任务补全；`run`依次准备证据包、启动Claude Code并回收报告。也可分别运行`prepare`、`execute`和`collect`。回收脚本对照任务开始时的工作区状态报告文件变化及越界修改，不把已有未提交差异误算为本次交付。每个任务使用唯一ID，已回收的包不覆盖。Claude Code不自动提交；Codex必须复核报告、差异、证据映射和受影响的12流程门槛后，才更新论文交付清单或评分材料。

该接口是12流程各阶段共用的执行交接层，不新增评分量表或研究阶段。模型调用需要启动本机Claude Code并消耗其当前配置的额度；自动化覆盖蓝图校验、任务包生成、调用和差异回收，复检与最终接受仍由Codex负责。当前仓库存在较多未提交变更，因此接口记录任务前基线并禁止自动Git写操作；独立worktree模式待建立稳定提交基线后再启用。
