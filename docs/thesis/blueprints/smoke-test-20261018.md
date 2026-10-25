# 蓝图接口修复与合成文本端到端复检（2026-10-18）

本次仅验证协作接口，不评价论文、不包含论文正文或实验结果。此前能力审计中的离线自检结论不替代本报告的真实运行证据。

## 修复

1. `build_launch_command` 将任务提示作为独立位置参数传入，放在可变长 `--disallowedTools` 选项之前。原实现虽接收 `prompt`，却未加入命令；直接在命令末尾追加又会被工具选项吞入。
2. 报告校验将当前任务的 `execution-report.json` 视为任务包元数据，兼容执行者在 `changed_paths` 中列出自身报告的情况。仅豁免调用方给定的精确报告路径，其他任务包文件、虚报路径及漏报实际改动仍须报错；任务包保护哈希与异常文件检查保持执行。任务包说明同步明确：通常无需列报告自身。

## 验证证据

- 修复前回归检查复现两个失败：提示未传入；报告校验不接受自身报告路径参数。
- 修复后离线自检 12/12 通过，包含提示唯一性和参数顺序、自列报告兼容、漏报实际输出拒绝、其他任务报告路径拒绝。Python 编译通过。
- 实际执行入口：`python3 scripts/thesis_blueprint.py run SMOKE-20261018-fixed-e2e`，Claude Code 2.1.302，会话模型标识 `deepseek-flash[1m]`（界面显示；执行报告同步自报）。
- 启动后界面直接显示任务包读取指令，Claude 随即读取任务包；未手动复制初始任务提示。
- 合成输出逐字节复检为 `handoff-fixed-e2e-ok\n`。
- 本地 Python 命令退出 0，打印 `local_bash_smoke_ok`。
- 禁网策略下 curl 退出 56，响应 `403`、`X-Proxy-Error: blocked-by-allowlist`，并记录 `deny network-outbound example.com:443 (host is on the deny list)`。这是该检查的预期拒绝结果。
- 执行者报告特意同时列出输出和自身报告路径。会话正常退出后，启动器自动回收，退出码 0，状态 `awaiting_codex_review`。
- 独立复核回收报告：授权工作区改动 1 项；范围外变化、异常任务包文件、受保护文件变化及执行报告错误均为 0；Git HEAD 与冻结基线一致。

证据保留在 [任务包](tasks/SMOKE-20261018-fixed-e2e/EXECUTION_PACKET.md)、[执行报告](tasks/SMOKE-20261018-fixed-e2e/execution-report.json) 和 [回收报告](tasks/SMOKE-20261018-fixed-e2e/collection-report.json)。冻结基线保留运行前已有的工作区状态，不应将它误作本次新增改动。

## 人工介入与结论边界

本次维持 manual 权限模式。操作者逐次批准授权输出、两条指定 Bash 检查及执行报告写入，最后输入 `/exit` 关闭会话，触发自动回收。Claude 曾额外申请 `ls` 与 `shasum` 的组合命令；操作者拒绝，提醒仅执行任务包指定检查后，Claude 按范围继续。该额外命令未执行；这说明任务指令仍需权限监督，不能将本次结果描述为完全无人值守执行。

Codex 已复核合成输出及回收结果：本次针对两处接口问题的端到端冒烟通过。任务状态保留为 `awaiting_codex_review`，不将工具交接状态改写为论文或正式交付验收结论。本次未重复验证白名单目标主机的实际连通性，也不据此消除上一轮代理超时的限制。

本轮复检代码 SHA-256：`48c63933aa061fe2ea56183ab1b077afb65078de5e060141169e731cb43ddacf`。
