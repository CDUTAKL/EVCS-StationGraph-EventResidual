# SG-EXP-019 数据核验运行手册

工作目录：`/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual`。
执行目标：local_mac；无远程训练、无付费资源。

## 已执行

1. `.venv/bin/python -m pytest tests/test_visibility_v2.py -p no:cacheprovider --tb=short`：占位实现阶段9项失败；实现后9项通过。
2. `.venv/bin/python scripts/audit_visibility_v2.py`：来源校验、重构复算、参数/图隔离、16个原点输入/规则/模型前向不变性检查后生成独立schema数据；不覆盖旧数据。
3. `.venv/bin/python scripts/audit_visibility_v2.py --verify`：通过冻结源文件和输出哈希复核。
4. `.venv/bin/python scripts/verify_visibility_v2.py`：全网格独立事件计数、标签成熟度、能量守恒、旧边界及本地数据库存复核通过，44项相关测试通过。

构建脚本仅从零创建输出目录，已存在时拒绝覆盖。已有产物只用--verify检查；需要重建则使用新的版本/输出，不删除原证据。

## 输入与产物

输入及哈希见`outputs/visibility/SG-DATA-006-eventtime-v1/manifest.json`。
数据/配置/报告位于同目录；独立核验位于`outputs/visibility/SG-DATA-006-eventtime-v1-verification/`。
产物保存在本地输出目录；未同步远程。输出目录受.gitignore影响，Git代码留档不能替代数据归档。

## 训练前契约门（未执行）

- 明确校验schema、feature_names、节点顺序、切分和数据哈希；拒绝旧7通道检查点。
- 接入单独的tuning与calibration数据集；新三分量原点规则不得由旧engine重新拟合。
- 只使用训练前缀图与标准化；同协议消融及基线共享键、信息权限和调参预算。
- local_mac进行CPU前向/反向/导出冒烟，再确认remote_desktop_4060硬件、环境与路径。
- 每个远程实验保存配置、环境、日志、检查点、预测、退出码及SHA-256；登记远程URI/status并回收本地索引。
- 云端仅为获准备选，必须记录费用资源、完整证据归档和关机/释放状态。

边界：事件即时可见是假设；没有实测延迟、独立新测试或预测性能结论。完整技术协议见`SG-DATA-006-visibility-audit-and-protocol.md`。
