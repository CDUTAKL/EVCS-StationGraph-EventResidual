# 本地依赖环境处理记录

2026-10-23，文档解包工具缺少 `defusedxml`。Codex 使用 `uv run --with ...` 时遗漏 `--no-project`，导致 uv 进入项目解析流程并重建 `.venv`。随后因默认选到 x86_64 Python、没有匹配的 torch 发行包而停止。此操作不应发生。

处理结果：

- 文档工具改为 `uv run --no-project --python /opt/homebrew/opt/python@3.14/bin/python3.14 --with defusedxml --with lxml ...`，依赖保存在隔离工具环境中。
- 项目 `.venv` 使用本机 ARM64 Python 3.14.5，根据 `pyproject.toml` 的基础及 dev、decision、baselines 可选依赖重建；包版本见 `reconstructed-local-environment.txt`。
- 2026-10-24，torch、numpy、pandas、PyYAML、scipy、statsmodels、lightgbm、xgboost、pytest 的导入均成功，记录见 `environment-import-check.json`。没有运行训练或项目测试套件。
- 本轮意外生成的 `uv.lock` 移至 `tmp/uv-lock-created-during-layout-20261023.lock`，未纳入项目锁文件。
- 没有修改实验配置、数据、检查点、远端训练环境或历史环境归档。

原 `.venv` 没有本轮开始前的完整包版本快照，因此这是按项目声明重建的可用开发环境，不能称为原环境逐版本恢复，也不能作为历史训练的复现环境。执行实验应继续使用对应实验封存的环境与源码合同。
