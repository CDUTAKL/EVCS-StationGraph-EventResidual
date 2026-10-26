# 2026-10-26 Git LFS迁移与正式文件入口

迁移前本地main为2b0d9edb6e1d11b7c331eb305ce092915b576c7c，公开远端main为6b2df008cd051bc7a7f0d05a2a746c62be215cc7。未推送范围共194个提交；仅8个提交因大文件存储方式改变而产生新SHA，映射逐行保存在commit-map.csv。已发布祖先未改写，上传采用正常快进推送。

完整原历史已保存为Git bundle并通过git bundle verify：大小911103725字节，SHA-256为49a80b206ab0c9ded1b8a969ab5a5071283ed287e4f5a532449c0a2ee1278939。本机位置记录在backup-manifest.json；备份不纳入Git。原仓库保留archive/main-pre-lfs-20261026引用，迁移在独立副本进行。

migration-audit.json核对迁移前后2237个HEAD文件：除.gitattributes和3个二进制路径变为LFS指针外，其余Git blob及文件模式保持一致。历史中3个唯一的超过100MiB的普通Git对象均找到字节相同的LFS对象；待推送范围不再包含超限普通Git对象。工具为官方Git LFS 3.8.1，下载摘要与官方发布资产一致。

## 正式稿

outputs/thesis下只保留同题名的正式论文.docx与正式论文.pdf两个稳定入口，均由LFS管理。最终Word与1200PPI以上PDF的内容摘要见final-artifacts.json；两者来自已经验收的v5候选稿，正文和图件内容未因迁移改变。以后通过Git提交恢复版本，日常不继续堆叠完整v编号副本。

## 原来源ID如何使用

已有manifest、训练记录和评分材料中的source_commit保留原值，不批量改写。若原SHA属于本次8个被迁移的提交，先按commit-map.csv解析到新SHA；需要原提交对象时，可从保留的原历史bundle恢复。迁移校验确认源码和分析结果字节未变。旧SHA与新SHA不同，只反映Word/PDF改为内容指针后的提交身份变化。

## 验证边界

本报告记录本地历史迁移与文件字节核对。远端Git引用和LFS对象的实际上传/下载结果另记。原始会话、预测文件和数据集仍位于Git之外；.venv未复制或改动。
