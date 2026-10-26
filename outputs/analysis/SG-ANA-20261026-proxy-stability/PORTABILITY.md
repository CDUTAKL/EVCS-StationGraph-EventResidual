# 当前集成副本的路径与来源规则

本目录是项目内的轻量集成副本，不携带50个大输入文件；`analyze.py`从项目的已冻结预测和数据集读取输入。因此，完整移出项目后若不提供同一来源工件，分析不会运行。

## 两种路径

- `source_path`、`source_archive`和`source_member`逐字来自哈希核验过的冻结清单，描述原始出处；`frozen_package_path`保留冻结包内的相对项。
- `lookup_path_hint`和`lookup_archive_hint`是适配仓库迁移的相对定位提示，不替代原始来源字段。`lookup_path`、`lookup_archive`和`lookup_root`记录本次实际解析位置。切换`EVCS_PROJECT_ROOT`只能改变查找记录。

`make_manifest.py`在写入前逐项验证50个输入的SHA-256与字节数；缺失、内容不符或历史来源字段漂移时以非零状态退出，保留原manifest。普通重建从锁文件读取原始来源；`--reconcile-from-frozen-manifest`只用于一次性校正，且必须匹配冻结清单SHA并逐项匹配输入清单及内容哈希。若要迁移成自包含包，应先把输入复制到包内并验证哈希，再让manifest记录`lookup_root=package`，同时保留不变的原始`source_*`字段。

不会把分析输入副本写入论文仓库。需要自包含交付时，应在仓库外建立隔离副本，按锁文件核验来源后再打包。

## 验证

在临时副本中用包内符号链接模拟已迁移输入，并设置`EVCS_PROJECT_ROOT=/nonexistent`：所有来源字段须保持不变，lookup字段应指向包内路径；移除输入或改动一个字节时，工具须非零退出且不改写manifest。该验收不触碰当前冻结分析包。
