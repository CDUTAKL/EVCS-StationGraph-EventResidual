# 最小复算说明（REV-20261022）

## 范围
本说明只支持“已保存预测的指标复算”：从归档中的预测键与标签重算指标，不加载检查点做前向推理，不重训模型，不重现训练过程。两个归档均为本地sidecar，体积较大，不随论文或Git分发；因此本包不是自包含的训练复现包。

## 归档与源身份

### SG-EXP-031
- 结果归档：`outputs/experiments/SG-EXP-031/SG-EXP-031-results.tar.gz`，122,402,069 B，SHA-256 `4eb436fbf30823d4df9b3e1be9f34652f849bdf7a130ce1c4229d9b2964f8c5f`。
- 冻结bundle：`outputs/experiments/SG-EXP-031/SG-EXP-031-bundle.tar.gz`，2,201,588 B，SHA-256 `5361c41a147592d0ea6bb14cd2282637f4906015a0dc76f4563d2b0e388b4d8a`。
- 清单成员：`SG-EXP-031/BUNDLE_MANIFEST.json`，SHA-256 `3ba32eee77da8bea6895804f5c4f1bf4924d3ff394b4aabce84c394fc482ee8b`，67项全部核验。
- 入口脚本：`scripts/jpl_relation_controls.py`，SHA-256 `ac5f7a998ad198af30f07971f929b7abc43300e7aecb9e65e645d633920b9cba`，与冻结bundle一致，但未被Git跟踪。
- 数据：SHA-256 `1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af`。
- Git基线：`fce67da891d95ae5021942e3e34fb088c1a9fc2a`；工作区补丁0字节。该提交只标识记录基线，源身份以冻结清单为准。
- 规模：12次运行，156个运行文件，173个归档校验项，每运行632,640个测试键。复算状态记为POST_HOC_DIAGNOSTIC，主差异字段为空。

### SG-EXP-032
- 结果归档：`outputs/experiments/SG-EXP-032/recovered/SG-EXP-032-results.tar.gz`，73,841,118 B，SHA-256 `b6f73aeb350db65f1d25ee59c19bcf8b316270049f46aaeee59ff971947670b3`。
- 冻结bundle：`outputs/experiments/SG-EXP-032/upload/SG-EXP-032-bundle.tar.gz`，2,612,518 B，SHA-256 `d53015b7de8150ad00efaa631449df57360c2987094c102e3f175561dee001df`。
- 清单成员：`workspace/BUNDLE_MANIFEST.json`，SHA-256 `893ca0586a7a2e79b4f5ca5ef35d2d1e2f46d84d3538d90829f5b757c9d01cc2`，91项全部核验；磁盘清单`outputs/experiments/SG-EXP-032/frozen-contract/manifest.json`，SHA-256 `e8f5b8498cc03f9c483a1a54991914ffb926d369595f3a553912298c6c1ea566`，3项核验。
- 入口脚本：`scripts/completion_target_sensitivity.py`，SHA-256 `6bb968944a4db08cb3458cf0dbdd4b07c192ce5c31cbcdefad44b9cb945ad753`，与冻结bundle一致。
- 数据：SHA-256 `5802a65e2f7f0e045d54df3359eb52e9de73c5c6f4af06c67ada7db22747293f`。
- Git身份：无经核实的历史提交号；源身份仅为文件哈希清单。
- 规模：6次运行，75个运行文件，99个归档校验项，每运行708,560个测试键；复算PASS，主差异0.008302002680088615。

## 复算入口与依赖

在本项目根目录运行（Python 3、NumPy；EPFL审计另需openpyxl）：

```bash
python3 scripts/replay_sgexp031_032_evidence.py --out replay-package.json --audit-out outputs/analysis/replay-fresh
```

`--audit-out`必须是空目录；非空即拒绝，避免覆盖既有结果。不指定时使用临时目录，最终JSON保留摘要和文件哈希。入口校验四个源/结果归档、归档内清单及逐运行文件，再调用`audit_sgexp031_results.py`与`audit_sgexp032_results.py`，固定10,000次日块重采样。输出含运行指标CSV、配对区块CSV及审计JSON。2026-10-22的保留输出位于`outputs/analysis/SG-EXP-031-032-replay-20261022/`。

运行前保留原目录布局：031源包解压内容位于`outputs/experiments/SG-EXP-031/bundle/`，结果解压内容位于`outputs/experiments/SG-EXP-031/recovered/results/SG-EXP-031/`；032冻结数据合同位于`outputs/experiments/SG-EXP-032/frozen-contract/`，结果位于`outputs/experiments/SG-EXP-032/recovered/closeout/closeout/results/formal/`。该入口依赖这些本地冻结数据与解压结果，不能只复制一个JSON便宣称可以复算。迁移时须携带上列四个归档、冻结数据合同，以及脚本使用的对应源码/结果目录；禁止用当前改写源码冒充历史源码。

实际训练源码保存在两个冻结bundle；逐运行`config_resolved.json`、`environment.json`、`run_summary.json`、`metrics.json`及`manifest.json`保存在结果归档。`reproducibility-package.json`逐一列出权重与预测文件的路径、字节数和SHA-256。本轮轻量交付包另保留源码副本、配置和环境快照；权重与预测保留在上述原归档中，按清单随包外置携带。此包支持检查资料是否完整，并提供已有预测的指标复算入口。

## 限制
- 归档为大体积本地sidecar，不随仓库分发；缺少归档时无法复算。
- 031入口脚本未被Git跟踪，032无历史提交号，二者均不能仅凭提交号重建源身份。
- 本说明不构成训练复现、检查点前向推理或新数据验证。
