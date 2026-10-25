# AdaptiveGraph 三检查点 CUDA 前向复核

日期：2026-10-15。任务为既有 SG-EXP-004 检查点复算，无训练、无重新选模、无阈值调整。

## 环境与材料

- 独立环境：服务器 `/root/autodl-tmp/evcs-replay-torch241-cu121`，Python 3.12.3、PyTorch 2.4.1+cu121、CUDA build 12.1、RTX 4090 D。
- 原训练记录中可核对的 PyTorch/CUDA 版本已匹配；原 GPU 型号未记录，不能宣称整台原机器完全复原。
- 输入包 SHA-256：`9e0df8d6c001fbc83538cfa28524aa259938f903b5dad844d2961eb727867e71`。服务器端传输哈希一致。
- 输入 64 个文件哈希通过。三个种子各 712360 个测试预测键；键唯一性、顺序、真值和事件标签通过脚本检查。
- 本地结果：`outputs/analysis/AdaptiveGraph-CUDA-20261015/`。远端：`ssh://root@connect.westc.seetacloud.com:24376/root/autodl-tmp/AdaptiveGraph-CUDA-replay-20261014/replay-cuda-20261015`。
- 回收结果清单 13 个文件哈希通过；另保存运行日志、依赖版本清单和独立算术核验。

## 逐键核验

逐键绝对容差保持 5×10⁻⁶；下列值为与原归档预测的最大绝对差异。

| 种子 | 原生 CPU | 原生 CUDA | 固定 CUDA 邻接后的 CPU | CUDA/固定邻接核验 |
|---|---:|---:|---:|---|
| 2024 | 0.091234691 | 7.46515×10⁻⁷ | 9.26700×10⁻⁷ | 通过 |
| 2025 | 0.058963018 | 6.16016×10⁻⁷ | 7.33231×10⁻⁷ | 通过 |
| 2026 | 0.015293041 | 5.60034×10⁻⁷ | 7.33798×10⁻⁷ | 通过 |

CUDA 复算全局 MAE 分别为 0.014130932448、0.013963644011、0.013795250139，与归档值的绝对差异均小于 7×10⁻¹⁰。独立核验从回收数组重新计算最大逐键差异、全局 MAE 和换边行，结果一致。

## 失败原因与结论范围

CPU/CUDA 分别有 7、8、9 行选择不同邻居，所有换边均发生于 CPU 检测到的 top-k 截断位置并列候选行。将 CUDA 实选邻接固定到 CPU 模型后，三个种子均恢复归档匹配。因此本轮支持：并列 top-k 的后端选边差异足以解释本轮原生 CPU 的复算偏差，原归档预测可由冻结检查点在匹配的 CUDA 软件版本下复现。

此前 macOS/PyTorch 2.13 CPU 的三次失败保持历史记录；其误差与本轮 Linux/PyTorch 2.4.1 CPU 不同，不能混用或覆盖。当前结果提供后端选边机制的直接证据，不宣称所有历史环境偏差来源均已逐一排除。

本轮不产生新性能增益、不增加关系或 MDP 的独立贡献证据，不进行显著性检验或自动加分。原训练 git_commit 为空，恢复源码快照认证的限制仍保留。论文正文及 DOCX 本轮未改写，待纳入复现说明时应引用本报告和独立核验 JSON。

## 可重复执行

远端冻结包目录内运行：

```sh
PYTHONDONTWRITEBYTECODE=1 /root/autodl-tmp/evcs-replay-torch241-cu121/bin/python replay_adaptivegraph_cuda_20261014.py --component legacy --manifest MANIFEST.json --out replay-cuda-20261015
```

输出目录必须不存在，重复执行须使用新目录。本地独立核验：`scripts/verify_adaptivegraph_cuda_20261015.py`。证据详见 `status.json`、`independent-verification.json`、逐种子预测数组和邻接数组。
