"""⚠️ 已废弃（2026-09-20）：fig5_5 的生成已迁移至 batch_priority_results.pcmci()。

本脚本原产出三面板“验证网络图”版 fig5_5_pcmci_validation_network（圆环网络 +
验证漏斗 + 节点级堆叠条，画布 10.6 in，堆叠条用 hatch="///"/"..."/"xx" 纹理）。
该版本与同章 fig5_9 的纯色配色不统一，且 10.6 in 超出论文版心（5.59 in），
故由 batch_priority_results.py 的 pcmci() 重绘版取代（5.59 in 版心尺寸、
纯色 + 单元内符号、全程无 hatch）——处理方式与 fig5_3、fig5_7 的先例一致。

两个脚本写同一文件名且都不报错，谁后运行谁生效：运行本脚本会静默覆盖正确版本。
为杜绝这一覆盖，绘图代码已整体删除，直接运行即抛出异常。

数据来源（重绘版仍读同一文件）：outputs/analysis/pcmci/pcmci_summary.json
"""

if __name__ == "__main__":
    raise RuntimeError(
        "batch14_pcmci_network 已废弃（2026-09-20）：请勿运行。图5-5 由 "
        "scripts/figures/batch_priority_results.py 的 pcmci() 生成"
        "（见 scripts/figures/figure_manifest.py 的 FINAL_SCRIPTS）。"
    )
