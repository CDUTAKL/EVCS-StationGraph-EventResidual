# ACN v3 扩展分析：复核归档

本目录保存 Kimi 完成的五项扩展分析脚本、汇总结果和图件，并记录 Codex 对结果口径的复核。它是**训练期内的标签核验材料**，不是论文主测试集的独立功率预测评价，也尚未回填正文。

## 核心结论

在 Caltech California Garage 的 2018-05-01 至 2018-06-11 设备记录窗口内，完成时刻截断标签相较接入—断开均分标签，与设备上报序列构造的 15 分钟电量分布更接近。这个方向在积分阈值、节点/全站聚合和不同设备上报量口径中均出现；具体降幅随指标、样本和参考序列而变。

五项分析的结果、比较对象与限制见 [`reviewed-extension-report.md`](reviewed-extension-report.md)。

## 结果口径

- **A：累计电量参考序列**，由设备上报 `Energy Delivered (kWh)` 处理后差分构造。
- **B：功率积分参考序列**，由设备上报 `Power (kW)` 的分段线性积分构造。
- A 和 B 来自同一静态数据导出；没有独立校准证书，不能称为两个独立仪器基准。
- v3 扩展脚本采用固定 60 s 缺口阈值，并使用自身的样本筛选与汇总口径。v4 报告采用不同的自适应缺口规则和修正后的边界处理。**不要合并 v3 与 v4 数字，也不要把 v3 附录中的敏感性结果称为 v4 主结果的重复复现。**
- 个别 v3 汇总表的测量参考序列不同：`sensitivity_max_gap.csv` 的缺口阈值分析使用 B；`sensitivity_coverage.csv`、`sensitivity_bin_offset.csv`、`sensitivity_meter_edge.csv` 以及 `multiscale_metrics.csv` 使用 A，其中部分样本是按 B 的功率覆盖率筛选。引用时必须同时报告参考序列与样本口径。
- bootstrap 输出中的 `p_boot=0.0` 表示有限次重抽样中未观察到反向样本，不是精确的零概率。复核报告以重抽样区间和实际重抽样单位为主，不引用 `p=0` 或据此作无限精度的显著性表述。
- `idle_ratio` 回归是控制所列变量后的条件关联分析；分层结果支持均分偏差随完成后占桩时长增加而上升，但不能单独建立因果关系。

## 数据和文件管理

输入原始会话 JSON、2,341 个时序文件及完整 ZIP 不存入 Git。输入 ZIP SHA-256 为 `7cf0426040ce3f443304368cc8b09329d45af38182986d2f747e954b2778a079`；ACN-Data-Static 来源提交为 `abb7cf15cc7108913e965d4375cc7270d532b65f`。原包中的逐文件下载清单本身以 SHA-256 登记在 [`source_manifest.json`](source_manifest.json)，且整个 ZIP 哈希固定。54 MB 的 `extended_stores.pkl`、逐会话输出、倾向得分明细、运行日志和临时 PID 文件均不纳入 Git。

完整原始包仍保存在用户提供的 Git 外目录 `/Users/xushuyuan/Downloads/acn_anchor-3/`。报告与复现代码来源文件的哈希见 [`source_manifest.json`](source_manifest.json)，本目录文件哈希见 [`SHA256SUMS`](SHA256SUMS)。

## 复算

需要先从用户持有的原始包解压会话 JSON 和静态时序文件，再显式提供路径。项目没有冻结本次运行的 Python 依赖锁文件，因此这里登记代码和输入身份，不宣称已在另一环境完成逐字节复算。

```bash
ACN_SESSIONS=/path/to/acndata_sessions-2.json \
ACN_TS_DIR=/path/to/california_garage_01 \
ACN_EXTENDED_OUT=/path/to/results_extended \
python3 scripts/extended_analysis.py
```

`extended_analysis.py` 从同目录导入 `anchor_analysis.py`。`download_static.py` 可在取得原始会话清单后按来源提交重新获取时序；下载行为受网络可用性影响。该命令会生成逐会话中间文件和较大的 pickle 检查点，不应直接在论文仓库根目录运行。
