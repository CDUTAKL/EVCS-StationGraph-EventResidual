# 本地依赖环境处理记录

> **2026-10-24恢复执行更新；10月25日备份复核：**项目`.venv`已按SG-EXP-032历史运行记录重建为Python 3.12.14 ARM64，历史清单中的61项固定依赖全部版本匹配；依赖检查通过，70项核心测试通过，SG-EXP-031/032已归档预测复算通过。事故后Python 3.14.5环境的回退目录又完成24,220项文件/链接清单复核，哈希和链接目标全部通过。详见[环境审计报告](/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/docs/development/local-environment-audit-20261024/REPORT.md)。这属于按历史记录重建，不是事故前一刻环境的完美恢复：没有当时的完整环境快照，临时`artifact_tool_v2`引用未恢复，历史editable源码提交也未覆盖当前工作区。

> 2026-10-24详细复核更正：后来找到了SG-EXP-032等本地运行保存的完整`pip freeze`历史清单。此前“没有完整包版本快照”应限定为“没有误操作前一刻的完整环境备份”。当前环境相对该历史清单缺34项、17项版本不同，因此不能称为完整恢复。70项核心测试及18次既有预测复算已通过，文档/绘图/PCMCI依赖仍缺失；详见`docs/development/local-environment-audit-20261024/REPORT.md`。下文保留首次处理过程，不作为环境已完整恢复的验收依据。

2026-10-23，文档解包工具缺少 `defusedxml`。Codex 使用 `uv run --with ...` 时遗漏 `--no-project`，导致 uv 进入项目解析流程并重建 `.venv`。随后因默认选到 x86_64 Python、没有匹配的 torch 发行包而停止。此操作不应发生。

处理结果：

- 文档工具改为 `uv run --no-project --python /opt/homebrew/opt/python@3.14/bin/python3.14 --with defusedxml --with lxml ...`，依赖保存在隔离工具环境中。
- 项目 `.venv` 使用本机 ARM64 Python 3.14.5，根据 `pyproject.toml` 的基础及 dev、decision、baselines 可选依赖重建；包版本见 `reconstructed-local-environment.txt`。
- 2026-10-24，torch、numpy、pandas、PyYAML、scipy、statsmodels、lightgbm、xgboost、pytest 的导入均成功，记录见 `environment-import-check.json`。没有运行训练或项目测试套件。
- 本轮意外生成的 `uv.lock` 移至 `tmp/uv-lock-created-during-layout-20261023.lock`，未纳入项目锁文件。
- 没有修改实验配置、数据、检查点、远端训练环境或历史环境归档。

原 `.venv` 没有本轮开始前的完整包版本快照，因此这是按项目声明重建的可用开发环境，不能称为原环境逐版本恢复，也不能作为历史训练的复现环境。执行实验应继续使用对应实验封存的环境与源码合同。
