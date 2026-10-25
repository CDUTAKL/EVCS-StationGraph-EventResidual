# Claude Code执行任务包

任务编号：SYNC-20261019-CANONICAL-DOCX
任务类型：delivery_audit；对应12流程阶段：第12步：正式交付文件同步与复核
目标：将已完成全页视觉验收且与最新正文哈希对应的候选DOCX，同步为仓库正式论文文件；只解决正式交付文件仍为旧稿、学号未填与当前验收稿不一致的问题，不改论文正文或实验内容。

## 开始前
只依据本任务包的冻结摘录和蓝图列出的材料工作。不要从聊天历史、归档计划或整份实验登记表重建当前状态。正文源稿为`docs/thesis/thesis-manuscript.md`。

## 可写范围
- `outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx`
- 以上路径是任务约束和事后审计范围，不是操作系统级文件隔离；不要写入未列路径，也不要把Git忽略路径当作可审计输出。

## 锁定主张与口径
- 本任务只同步交付文件，不构成论文内容修订、实验新增或评分提升。
- 作者确认的学号为2024050524；未知官方字段必须保持空白。
- 不得修改已验收候选DOCX；只能将其原样复制到正式输出路径。
- 签名与签署日期必须真实线下完成，不得代签或生成。

## 执行步骤
1. 核对只读源候选DOCX的路径与SHA-256必须和canonical-sync-inputs.md记录一致；不对源候选进行编辑。
2. 将候选DOCX按字节原样复制到唯一授权的正式论文路径，不进行格式转换、压缩、重写或内容编辑。
3. 计算源文件与正式目标文件SHA-256并进行DOCX ZIP完整性检查；确认两者哈希完全相同。
4. 在execution-report.json逐项记录源/目标路径、复制命令、两个SHA-256、ZIP检查结果；不得宣称新PDF已生成或验收。

## 指定Claude Code Skills
- 本任务未指定Claude Code专用skill；如需技能支持，先在报告中说明阻塞，不要假定Codex全局skill已自动安装到Claude Code。

## 验收条件
- 唯一变更路径为正式论文DOCX；候选源文件和正文稿件均未改变。
- 正式DOCX与已验收候选DOCX的SHA-256完全一致，ZIP完整性检查无损坏。
- 未知封面字段保持空白；未生成签名或签署日期。
- 执行报告明确本任务只同步文件，不代表行政签署完成、PDF重新导出、全页复验或论文评分。

## 操作权限
- 训练：False；远程执行：False；联网：False；Git提交/暂存：False。
- 除非明确列入允许范围，不得启动训练、远程作业、联网采集、Git暂存/提交或覆盖正式Word。不得使用绕过权限的启动方式。
- 不得修改`.git/`、`.claude/settings*.json`、凭据文件或交接控制文件；如需修改，停止并报告。
- 只运行蓝图列出的检查：cp -- docs/thesis/revision-20261019-nontraining/thesis-delivery-final-restored-noline.docx outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx, shasum -a 256 docs/thesis/revision-20261019-nontraining/thesis-delivery-final-restored-noline.docx outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx, unzip -t outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx。未列检查时不要新增或运行测试。
- Bash网络主机白名单：无。空数组表示Bash无网络；WebSearch/WebFetch须单独取得工具权限。

## 冻结的证据摘录

### 证据控制台

#### docs/thesis/revision-20261019-nontraining/wps-visual-acceptance.md — 查看已验收候选稿的封面与签署边界，避免把旧待确认信息当作当前状态。
定位：`{"kind": "markdown_heading", "value": "封面、声明与签署"}`；来源SHA-256：`fc2963e03f0c549f5c9abdd09e8e39874788ffbf82f79e1a03217e35166098b0`
```text
## 封面、声明与签署

封面已保留并填写本地材料能够一致确认的论文题目、作者、导师、学位类别和专业领域。内封面中的学号为 `2024050524`，与当前候选稿副本一致；另有旧构建脚本记录 `2023050482`，存在冲突，因此本次没有自行改号，须由作者按学籍信息确认。分类号、UDC、密级、送审/答辩/授位日期、答辩委员会主席等未能从可信材料唯一确认的字段继续留空。

原创性声明、版权授权中的作者与导师签名以及日期必须由本人和导师真实签署，本次不代签、不生成仿真签名。相应页面版面通过，但行政签署状态仍未完成。取得正确学号及封面元数据并完成真实签署后，如修改DOCX，必须重新导出并重新验收新PDF。

```

#### docs/thesis/revision-20261019-nontraining/status.md — 核对本轮DOCX/PDF交付对象、全页验收记录及尚待签署事项。
定位：`{"kind": "markdown_heading", "value": "Word/WPS 视觉验收结论"}`；来源SHA-256：`86927351df2b3d5c20e4858ddcc0cf480237262553e9924f37523085f6e9f212`
```text
## Word/WPS 视觉验收结论

当前WPS候选PDF已重新导出并通过版面验收：104页全页以120 dpi逐页查看；目录在PDF第7–10页，116项页码全部匹配；没有额外空白页；第3、4页分别为模板要求的原创性声明和版权授权；46张图有效分辨率最低1201.0 PPI；PDF中9种字体均已嵌入。正文、表格、公式和图件未见明显裁切、拉伸或压缩模糊。源DOCX在本机仍可能显示缺字体警告，但最终PDF字体已嵌入。封面已填写能够确认的资料；学号在当前候选与旧脚本之间存在冲突，其他官方分类/日期字段也需核实；声明签名须作者和导师真实完成。因此版面验收通过，正式签署和元数据核实仍待责任人，不将其伪报为已完成。详情见`wps-visual-acceptance.md`、`toc-page-verification-noline-hires.json`、`highres-restoration-noline.json`和`visual-qa-final-wps-noline/`。

```

### 直接证据

#### docs/thesis/revision-20261019-nontraining/canonical-sync-inputs.md — 作者确认的学号和留空字段、候选稿哈希与本任务边界。
定位：`{"kind": "whole_file"}`；来源SHA-256：`26ce39abeb0f44196d8eadee94fe1bdf0f549302858e33a425990932d141f8c6`
```text
# 正式论文文件同步输入（2026-10-19）

作者在本轮对话确认：学号为 **2024050524**；分类号、UDC、密级、送审/答辩/授位日期和答辩委员会主席暂时未知，先留空。原创性声明和版权授权页的作者、导师签名及日期由双方线下真实签署。

计划同步的已验收源文件：docs/thesis/revision-20261019-nontraining/thesis-delivery-final-restored-noline.docx，SHA-256 `54749d10bc365dd60862cb9fef030baec9a07530f5a791e47f6a224e84502f9b`。该DOCX的全页WPS验收记录为docs/thesis/revision-20261019-nontraining/wps-visual-acceptance.md；对应的高分辨率PDF为docs/thesis/revision-20261019-nontraining/thesis-delivery-final-wps-noline-hires.pdf，SHA-256 `12603acfeb9c0a129b206359d8c4fa7d58d67d161b108389f10b72f0fce95e06`。源稿docs/thesis/thesis-manuscript.md SHA-256 `451642e15e0fc51343acabf84e727b5079d8a1f2243c0ab8d8542adeed8b9b42`，与验收记录中的正文SHA一致。

本任务只将上述已验收DOCX的字节内容复制到仓库正式论文路径，不改候选源文件，不改正文、图表、公式、引用或任何实验/数据；不得填入未知封面字段，不得生成签名或日期。完成后由Codex核对目标与源文件哈希，再从正式论文路径集中导出并验收新PDF。

```

#### docs/thesis/revision-20261019-nontraining/wps-visual-acceptance.md — 确认将复用的候选DOCX与已验收PDF及其哈希。
定位：`{"kind": "markdown_heading", "value": "验收对象"}`；来源SHA-256：`fc2963e03f0c549f5c9abdd09e8e39874788ffbf82f79e1a03217e35166098b0`
```text
## 验收对象

- DOCX：`thesis-delivery-final-restored-noline.docx`
- DOCX SHA-256：`54749d10bc365dd60862cb9fef030baec9a07530f5a791e47f6a224e84502f9b`
- WPS 原始导出：`thesis-delivery-final-wps-noline.pdf`（104页）
- 高分辨率交付 PDF：`thesis-delivery-final-wps-noline-hires.pdf`
- PDF SHA-256：`12603acfeb9c0a129b206359d8c4fa7d58d67d161b108389f10b72f0fce95e06`
- 正文稿 SHA-256：`451642e15e0fc51343acabf84e727b5079d8a1f2243c0ab8d8542adeed8b9b42`
- 全页检查图：104页均以120 dpi、993×1404像素渲染，并逐页查看；图片哈希和页码见 `visual-qa-final-wps-noline/full-page-renders.json` 与 `manual-review.json`。

```

#### docs/thesis/revision-20261019-nontraining/codex-review.md — 核实正式文件与已验收候选之间的交付状态差异。
定位：`{"kind": "markdown_heading", "value": "DOCX候选与交付门槛"}`；来源SHA-256：`7a9835709db4f2b6be27b87297364ab72842000f4a23e8a316e5d349c8196753`
```text
## DOCX候选与交付门槛

候选文件：`thesis-candidate.docx`，源稿SHA-256为`451642e15e0fc51343acabf84e727b5079d8a1f2243c0ab8d8542adeed8b9b42`；DOCX SHA-256为`83add737fe61cfa461b6cabf628455127b2202bb88678eda7ce381e627a1b0ce`。

`docx-candidate-audit.json`为PASS：27个编号显示公式均为原生公式并按章排序；46/46张图的嵌入哈希与顺序对应；按版面尺寸计算的最低有效分辨率为1200.7 PPI。候选包完整性检查通过。

WPS PDF的104页已逐页复核。正文页未见明显裁切、拉伸或严重模糊；PDF第7–10页目录没有页码或引导点，目录一致性未通过。另有封面字段与签名未完成、PDF第4页空白用途未确认、WPS缺失字体提示未解决，以及WPS与LibreOffice分页相差21页等问题。因此DOCX仍是候选稿，最终交付验收未通过。机械审计文件中的`visual_page_acceptance: NOT_PERFORMED`反映生成该审计时尚无人工视觉验收；当前人工结果以`wps-visual-acceptance.md`和`visual-qa-wps/manual-review.json`为准。

```

## 完成报告
在`docs/thesis/blueprints/tasks/SYNC-20261019-CANONICAL-DOCX/execution-report.json`填写Claude Code工作报告。changed_paths使用项目根目录相对路径，仅列实际工作区改动，不必列报告自身；列出证据来源、检查、未解决事项，以及所有数字或主张变化。报告只供Codex复检，不代表验收。
在`model`字段填写当前Claude Code会话实际报告的模型标识；`user_reported_model`只是操作者标签。若provider返回`unrecognized_model`，把原始模型名和诊断写入`unresolved`，不要猜测或自动替换模型。
如证据不足、需要扩大修改范围或发生未授权操作，停止继续并在报告中说明。
