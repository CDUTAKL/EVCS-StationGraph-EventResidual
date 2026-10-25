# Claude Code执行任务包

任务编号：SMOKE-20261018-fixed-e2e
任务类型：other；对应12流程阶段：11/12辅助工具冒烟
目标：验证自动任务提示、授权输出、本地Bash和自动回收；仅读合成文本与本任务控制文件。

## 开始前
只依据本任务包的冻结摘录和蓝图列出的材料工作。不要从聊天历史、归档计划或整份实验登记表重建当前状态。正文源稿为`docs/thesis/thesis-manuscript.md`。

## 可写范围
- `tmp/claude-code-fixed-e2e-20261018/output.txt`
- 以上路径是任务约束和事后审计范围，不是操作系统级文件隔离；不要写入未列路径，也不要把Git忽略路径当作可审计输出。

## 锁定主张与口径
- 不得读取或修改论文、实验、检查点及其他项目材料。

## 执行步骤
1. 读取本任务包冻结的合成摘录，在唯一授权输出文件写入令牌 handoff-fixed-e2e-ok，末尾换行。
2. 仅运行checks_to_run指定的两条命令，记录真实退出码；无网沙箱拒绝curl为预期结果，不要绕过沙箱或重试。
3. 填写同目录execution-report.json。本次专门测试兼容性：changed_paths同时列出输出文件和本报告自身的项目相对路径；不要改其他任务包文件。完成后停止，等待操作者退出会话。

## 指定Claude Code Skills
- 本任务未指定Claude Code专用skill；如需技能支持，先在报告中说明阻塞，不要假定Codex全局skill已自动安装到Claude Code。

## 验收条件
- 输出恰为handoff-fixed-e2e-ok加换行
- Python退出0且curl明确被沙箱拒绝
- 报告如实填写模型、执行结果，无数字或主张变化
- 任务包自身报告路径不导致误报，自动回收到awaiting_codex_review

## 操作权限
- 训练：False；远程执行：False；联网：False；Git提交/暂存：False。
- 除非明确列入允许范围，不得启动训练、远程作业、联网采集、Git暂存/提交或覆盖正式Word。不得使用绕过权限的启动方式。
- 不得修改`.git/`、`.claude/settings*.json`、凭据文件或交接控制文件；如需修改，停止并报告。
- 只运行蓝图列出的检查：python3 -c 'print("local_bash_smoke_ok")', curl --head --connect-timeout 3 --max-time 5 https://example.com。未列检查时不要新增或运行测试。
- Bash网络主机白名单：无。空数组表示Bash无网络；WebSearch/WebFetch须单独取得工具权限。

## 冻结的证据摘录

### 直接证据

#### tmp/claude-code-fixed-e2e-20261018/fixture.md — 纯合成测试令牌
定位：`{"kind": "whole_file"}`；来源SHA-256：`8141aefaa1ca23892fdf69d67401d5eb1f32c101d275664bdcdaad3fc2934074`
```text
# Synthetic fixture

Expected output token: handoff-fixed-e2e-ok
This fixture contains no thesis or experimental content.

```

## 完成报告
在`docs/thesis/blueprints/tasks/SMOKE-20261018-fixed-e2e/execution-report.json`填写Claude Code工作报告。changed_paths使用项目根目录相对路径，仅列实际工作区改动，不必列报告自身；列出证据来源、检查、未解决事项，以及所有数字或主张变化。报告只供Codex复检，不代表验收。
在`model`字段填写当前Claude Code会话实际报告的模型标识；`user_reported_model`只是操作者标签。若provider返回`unrecognized_model`，把原始模型名和诊断写入`unresolved`，不要猜测或自动替换模型。
如证据不足、需要扩大修改范围或发生未授权操作，停止继续并在报告中说明。
