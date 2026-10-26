# SG-ANA-20261026-PROXY-STABILITY

本目录是已查看Caltech测试期上的代理标签敏感性复评材料。它复用冻结预测，不含新训练、网络访问或原始会话。48份预测与2个数据集不在此复制；50项输入的冻结包路径、原始`source_*`字段、SHA-256和字节数保存在`source-provenance.lock.json`。

## 复算

在仓库根目录运行：

```bash
EVCS_PROJECT_ROOT="$(git rev-parse --show-toplevel)" PYTHONDONTWRITEBYTECODE=1 python3 outputs/analysis/SG-ANA-20261026-proxy-stability/analyze.py
```

脚本读取原仓库中已登记的预测和两个数据集，并把派生结果写回本目录。环境需有兼容的Python、NumPy和Matplotlib。该复算会重新计算已有预测的标签敏感性指标；不训练模型，也不访问ACN API。

检查图表来源清单：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 outputs/analysis/SG-ANA-20261026-proxy-stability/make_manifest.py --check
```

在指标或输出发生变化后，可先核实锁定来源，再重建当前 manifest：

```bash
EVCS_PROJECT_ROOT="$(git rev-parse --show-toplevel)" PYTHONDONTWRITEBYTECODE=1 python3 outputs/analysis/SG-ANA-20261026-proxy-stability/make_manifest.py
```

来源保护规则见[provenance-regeneration-guard.md](../../../docs/thesis/revision-20261026-proxy-stability/provenance-regeneration-guard.md)。锁文件逐字保留冻结清单中的`source_path`、`source_archive`和`source_member`；供仓库迁移时定位的相对提示另存为`lookup_*_hint`，每次实际查找的位置写入manifest的`lookup_path`、`lookup_archive`和`lookup_root`。普通重建不能改变原始来源字段；来源缺失或哈希不符时脚本失败，不写manifest，也不会把`/nonexistent`登记成来源。只有显式使用`--reconcile-from-frozen-manifest`，且给定清单哈希与锁定值一致时，才可执行一次来源字段校正。当前外部冻结包不做修改。

## 结论边界

比较对象为12种均匀标签训练配置、同一组已查看测试键和两套会话代理标签。总体MAE排名相关为0.993（先对三种子MAE取均值再排序），逐种子相关均值为0.974；按评价标签定义的非零组分别为0.420和0.000。结果不能证明代理目标与实测功率等价，不能作为未见时期确认，也不改变关系组件受控增量与完整模型分层表现的区别。

原始冻结分析包与本地代码副本不是新的独立实验或样本。论文正文落点为§3.8.5、表3-16、图3-17和附表A-2。
