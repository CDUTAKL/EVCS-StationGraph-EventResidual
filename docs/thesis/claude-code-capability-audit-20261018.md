# Claude Code 论文交接能力独立复核（2026-10-18）

> 状态：`pending_codex_review`。本文是执行者的独立复核记录，不构成验收通过，也不改变论文评分、交付门槛或正式 DOCX。本文包含 2026-10-18 Codex 意见后的定向修订结果。

## 1. 复核范围与只读边界

复核对象为论文项目的 Claude Code 交接入口：

- `CLAUDE.md`
- `docs/thesis/blueprints/README.md`
- `docs/thesis/blueprints/template.json`
- `scripts/thesis_blueprint.py`

只读对象包括用户级 Claude skills、用户级设置、项目 `.claude/settings.local.json`、论文正文、正式 DOCX、实验数据和模型检查点。复核过程中：

- 未连接 SSH、AutoDL 或其他远程主机；未训练、未启动 GPU 作业、未联网采集数据。
- 未打印、导出或改写 `ANTHROPIC_AUTH_TOKEN`、API key、完整服务地址或 SSH 凭据；检查设置文件时只输出结构键名、规则数量和来源标签，未输出 env 值或 `settings.local.json` 中的主机值。
- 未修改用户级 `~/.claude/settings.json`、用户级插件配置、模型名或认证方式。
- 未暂存、提交、推送、重置、覆盖或清理任何既有 Git 改动。
- 未读取或修改论文正文；`research-paper-writing` skill 只做了加载核验，未执行其中写作步骤。
- 未运行完整测试套件；未启动 Claude 模型调用；未访问外网。

**边界声明：** 本项目的 `allowed_paths` 是任务约束和事后审计控制，不是操作系统级文件访问边界。Claude Code 的原生 Read/Edit/Write 工具仍可在项目工作区内写文件；Bash 沙箱只约束 Bash 命令。除非未来实现了真实的 OS 级隔离，本文不会把 `allowed_paths` 称为文件访问沙箱。

## 2. 工作区基线与最终哈希

任务开始前的 `git status --short` 显示工作区已经非常脏：大量已跟踪文件处于 `M`/`D` 状态，包含多批未跟踪的 review、revision、figure 和 thesis 输出目录；`CLAUDE.md` 在任务开始前已处于修改状态；`docs/thesis/blueprints/` 与 `scripts/thesis_blueprint.py` 在任务开始前就是未跟踪文件。

本次没有恢复、清理或重置这些既有改动。`CLAUDE.md` 只在其当前内容上追加条款，不恢复旧版本，也不把旧版本中的任何环境信息写入报告。`py_compile` 生成的 `scripts/__pycache__/thesis_blueprint.cpython-314.pyc` 已被 Git 忽略。

本轮修订后的最终哈希：

| 文件 | 任务开始时 SHA-256 | 本次最终 SHA-256 | 本次处理 |
|---|---|---|---|
| `CLAUDE.md` | `66459fd6122fc93ad9227961411a0459c1c7d9c4aa535c9ce0ab8fbca605ab98` | `dd499102b85f2643c2afa945d6da35cdce8fd36740c6656f6463d3632b6a19a2` | 增加 strictAllowlist/WebFetch 扩大白名单与 Skill 权限边界说明 |
| `docs/thesis/blueprints/README.md` | `5c2e7bacde9bef4daf368e162000d0f171d04eb65c80f9d8cbc1fe75d2fff85e` | `82644fa8663404b7247433b4b718145ec06ea371f510b6ef872303f540e99f06` | 增加本地 Bash 网络策略、版本门槛、WebFetch 规则合并与 Skill 权限边界 |
| `docs/thesis/blueprints/template.json` | `89aa5f1c230716b635cfacaa36792cf1a45917c243fda931bbc4a100c615f532` | `89aa5f1c230716b635cfacaa36792cf1a45917c243fda931bbc4a100c615f532` | 审阅后未改；默认标题和策略字段有效 |
| `scripts/thesis_blueprint.py` | `3ca8b1a37bd09293aa0a6b2259baec756d8a93475cfe970be15565416be08a25` | `e6f3f57ddeeaa2768bb5cab1a0130e0713583fc0980b5ac21159dd4290c3cc18` | strictAllowlist、版本 fail-closed、WebFetch 扩大白名单检查、通用 Skill ask、离线 self-check |

本轮后续修订前的上一版哈希（第一轮复核结束）：`CLAUDE.md` `e2d93766992333587bebf6f5cee8adfcfae62718d01c7f6491eb2da586509fb3`、`README.md` `4b1d778e833c993df8d9beb4af3401690937a55cc6f8b737900dd603a8313d96`、`scripts/thesis_blueprint.py` `12380ac314b30be5d8769b71e1f977dd2ead8498acb1980c8ba7cacff356221d`。上表保留任务开始基线以便追溯；`template.json` 未改。

## 3. 场景核验结果

| 场景 | 状态 | 实际证据 |
|---|---|---|
| 蓝图 `claude_skills` 名称、`SKILL.md` 与资源检查 | 通过（静态） | `skill_details()`（`scripts/thesis_blueprint.py:106`）解析项目级再用户级 skill，校验 frontmatter `name`/`description`，并解析反引号中的 `assets/`、`references/`、`scripts/`、`agents/`、`tests/` 资源；缺失资源会使 `validate`/`prepare` 失败。`validate_blueprint()`（`:248`）调用该检查。 |
| 只在蓝图指定 skill 时开放 Skill 工具 | 通过（静态） | `selected_tools()`（`:946`）仅在 `claude_skills` 非空时把 `Skill` 加入 `--tools`（`:951`）。`build_session_settings()`（`:957`）不添加 `Skill(<name>)` allow 规则；它加入通用 `Skill` ask 规则（`:992`）。Claude Code 的权限顺序为 deny → ask → allow，匹配的 ask 优先于 allow，因此所有 Skill 调用（包括蓝图列出的 skill）都需要人工确认。 |
| 指定 skill 的权限是硬白名单吗 | 受限（所有 Skill 调用需人工确认；不是按名称硬拒绝） | 通用 `Skill` ask 规则（`:992`）使所有 Skill 调用，包括蓝图列出的 skill，都需要人工确认；精确 `Skill(<name>)` allow 规则已移除，因为它们在通用 ask 下无法预先放行。未列 skill 没有按名称硬拒绝的规则；用户批准后，未列 skill 仍可能被调用。任务包/`CLAUDE.md` 的“只加载列出 skill”仍是指令级约束。 |
| 本地 Bash 使用失败即停止的沙箱 | 通过（静态 + 离线自检；未执行真实沙箱网络命令） | 本地含 Bash 时设置 `sandbox.enabled=true`、`failIfUnavailable=true`、`allowUnsandboxedCommands=false`、`autoAllowBashIfSandboxed=false`；`build_session_settings()` 见 `:957-1030`。 |
| 本地 Bash 默认无网络 | 通过（静态 + 离线自检） | `network_access_allowed=false` 时保留 `allowedDomains: []`（`:1017`），加入 `deniedDomains: ["*"]`（`:1022`），并设置 `strictAllowlist: true`（`:1018`）。自检 `local_no_network` 通过。 |
| 本地 Bash 白名单联网 | 通过（静态 + 离线自检） | `network_access_allowed=true` 时只把蓝图 `network_domains` 放入 `allowedDomains`（`:1017`），并设置 `strictAllowlist: true`（`:1018`）；不再依赖“未列主机只提示”的弱策略。自检 `local_whitelist_network` 通过。 |
| `strictAllowlist` 版本要求 | 通过（本地证据） | 本地 changelog `2.1.219` 条目明确“Added `sandbox.network.strictAllowlist` setting”（`~/.claude/cache/changelog.md:3952-3955`）。本机 `claude --version` 为 `2.1.302 (Claude Code)`。`claude_version()`（`:923`）解析本地版本；`build_session_settings()` 对低于 `(2,1,219)` 或无法解析的版本抛错，不会静默退回旧策略。自检 `old_version_rejected`、`min_version_accepted` 通过。 |
| `strictAllowlist` 的实际范围 | 通过（本地 schema 证据） | CLI 2.1.302 的设置 schema 描述：`strictAllowlist` 让沙箱确定性拒绝未列入 `allowedDomains` 的主机而不是提示；只对 sandboxed commands 生效，WebFetch 等 in-process 工具不受它约束；只从 user、managed/policy 或 CLI `--settings` 读取，项目设置被忽略。README/CLAUDE.md 已按此写明。 |
| WebFetch/设置规则扩大 Bash 白名单 | 通过（静态 + 离线自检） | `settings_expansion_hosts()`（`:856-884`）从单个设置文档提取 `sandbox.network.allowedDomains` 和 `permissions.allow` 中的 `WebFetch(domain:...)`；`sandbox_expansion_rules()`（`:886`）汇总来源标签；`uncovered_sandbox_expansions()`（`:903`）要求它们在 `network_domains` 中逐字出现，否则 `build_session_settings()` 抛错（`:1007-1015`）。自检 `webfetch_rule_discovered`、`webfetch_expansion_rejected`、`webfetch_declared_allowed` 通过。当前设置扫描结果为 0 条扩大规则。 |
| 远程任务显式联网授权并在每次 Bash 前人工确认 | 通过（静态 + 离线自检；未连接远程） | `validate_blueprint()` 要求 `remote_execution_allowed=true` 时同时 `network_access_allowed=true`（`:331`），并要求远程提供非空 `network_domains`（`:335`）。远程模式加入 `ask: ["Bash"]`，不设置本地 sandbox，启动参数为 `--permission-mode manual`；自检 `remote_task` 通过。 |
| 远程 `network_domains` 的性质 | 受限 | 远程不使用本地 Bash 沙箱，也没有 `strictAllowlist`；`network_domains` 只是任务授权清单，逐条 Bash 人工确认是实际门槛。它不是远程侧强制网络 ACL。README/CLAUDE.md 已明确。 |
| 插件/MCP 会话隔离 | 通过（静态） | `enabled_plugin_names()`（`:844-854`）读取用户、项目、项目本地设置中的 `enabledPlugins` 并在 `--settings` overlay 中全部置为 `false`；启动时使用 `--strict-mcp-config` 且不提供 `--mcp-config`（`:1045`）。当前检查到 37 个启用插件，项目 `.claude/settings.local.json` 只有 `permissions.allow`（8 条规则）；未打印其值。 |
| Git 权限与交接控制文件 | 通过（静态） | `git_mutations_allowed=false` 时 deny `Bash(git *)`，为 true 时改为 ask；`allowed_path_error()`（`:201`）拒绝 `.git/`、`.claude/`、`.ssh/`、`.gitignore`、`scripts/thesis_blueprint.py`、`docs/thesis/blueprints/`、任务包目录、原始数据目录和凭据类文件名。 |
| 任务报告回收逻辑 | 受限 | `collect` 通过 Git 脏路径、允许路径哈希、受保护任务包哈希和报告字段做回收；`verify_protected_package()`（`:791`）会在启动 Claude Code 前重新校验 `blueprint.json`、`context-snapshot.json` 和 `EXECUTION_PACKET.md`。仍未覆盖 Git 忽略路径；baseline/state 仍是工作区内的自引用记录；既有脏文件使用 size/mtime 指纹。 |
| 当前会话加载 `research-paper-writing` | 通过（实际） | 通过 Skill 工具加载成功，返回 base directory `~/.claude/skills/research-paper-writing`；未读取论文正文，未执行写作步骤。 |
| 论文相关 skill 符号链接与资源路径 | 通过（实际只读核对；文档已修正） | 5 个用户级 skill 是指向 kit 或 `~/.codex/skills` 的符号链接；逐个解析真实目录并检查反引号资源，除 cdut 外均无缺失。`README.md` 与 `CLAUDE.md` 已加入真实路径解析规则。 |
| cdut 学校格式 skill | 失败（模式不可用，fail-closed） | `~/.claude/skills/cdut-professional-master-thesis-format/assets/` 只有 `.gitkeep`，缺少 `assets/cdut-professional-master-20230905.docx`；`validate`/`prepare` 会拒绝任何引用该 skill 的蓝图。未创建空模板，未复制未经确认的 DOCX，未宣称完成模板对照。 |
| Word/PDF 收尾 | 受限 | `pwsh`/`powershell` 均未找到；`/Applications/Microsoft Word.app` 不存在；`soffice` 存在，但 LibreOffice 转换不等价于 Word 字段更新与 Word 渲染视觉验收。 |
| `unrecognized_model` 诊断 | 受限（仅诊断，未解决） | 本地 `~/.claude/settings.json` 的 `model` 为 `deepseek-flash[1M]`；当前会话标识为 `deepseek-flash[1m]`；诊断中的模型名为 `deepseek-flash[1m]`。未打印 env 值；没有本地证据能确定服务端认可的模型标识，因此未修改模型、认证或 provider 配置。 |
| 端到端 `new → validate → prepare → execute → collect` | 受限（未执行） | `execute` 需要交互终端并启动 Claude Code 模型调用；本次只执行离线自检和指定轻量核验，没有创建任务蓝图，也没有真实回收 `execution-report.json`/`collection-report.json`。 |

## 4. 本轮 Codex 意见的落实

### 4.1 本地 Bash 网络策略

- 版本证据：本地 changelog `2.1.219` 条目明确加入 `sandbox.network.strictAllowlist`（`~/.claude/cache/changelog.md:3952-3955`）；本机 CLI 为 `2.1.302`。
- 本地 Bash 沙箱配置统一加入 `strictAllowlist: true`（`scripts/thesis_blueprint.py:1018`）。
- `network_access_allowed=false`：`allowedDomains: []`（`:1017`）+ `deniedDomains: ["*"]`（`:1022`）+ `strictAllowlist: true`。
- `network_access_allowed=true`：`allowedDomains` 只来自蓝图 `network_domains`（`:1017`）+ `strictAllowlist: true`；未列主机是确定性拒绝，而不是提示。
- `claude_version()`（`:923`）读取本地 `claude --version`；`build_session_settings()` 对 `< 2.1.219` 或无法解析的版本抛错（`:1000-1006`），不静默退回弱策略。
- 范围说明：`strictAllowlist` 只约束沙箱 Bash，不约束 WebSearch/WebFetch；远程任务不使用本地沙箱，`network_domains` 仅是授权清单，不是远程网络 ACL。README/CLAUDE.md 已按此修正。

### 4.2 WebFetch 与设置规则的扩大白名单检查

- CLI schema 描述确认 `allowedDomains` 会与 `WebFetch(domain:...)` allow 规则合并；`strictAllowlist` 的说明还指出项目设置的 `allowedDomains`/WebFetch 规则会被排除，且它只从 user、managed/policy 或 CLI `--settings` 读取。
- `settings_expansion_hosts()`（`:856-884`）从单个设置文档中提取 `sandbox.network.allowedDomains` 和 `permissions.allow` 里的 `WebFetch(domain:...)`；`sandbox_expansion_rules()`（`:886-896`）汇总 user/project/project-local 设置并附带来源标签。
- `uncovered_sandbox_expansions()`（`:903-920`）要求这些主机/模式在 `network_domains` 中逐字出现（大小写不敏感，忽略末尾点）；不满足则 `build_session_settings()` 抛错（`:1007-1015`），不会静默扩大白名单。
- 匹配是保守的精确匹配：`network_domains` 里的通配符不会自动覆盖更窄的 WebFetch 规则；需要逐字声明。
- 项目级规则在 `strictAllowlist` 开启时会从沙箱白名单中排除，但启动逻辑仍对 project-local 规则 fail closed，避免依赖这一细节。
- 当前设置扫描：用户设置 allow 规则 0 条、WebFetch 域规则 0 条；项目设置缺失；项目本地设置 allow 规则 8 条、WebFetch 域规则 0 条；`sandbox_expansion_rules()` 最终计数 0。未打印任何主机值。
- 错误消息只报告来源标签和数量，不打印 `settings.local.json` 中的主机名。
- managed/policy 设置不在脚本读取范围内；如果它们添加 allowlist 条目，需要人工另行核对。

### 4.3 Skill 权限边界

- `selected_tools()` 仅在 `claude_skills` 非空时把 `Skill` 放进 `--tools`（`:946-951`）。
- `build_session_settings()` 不添加 `Skill(<name>)` allow 规则（`allow_rules` 为空，`:973`）；它添加通用 `Skill` ask 规则（`:992`）。
- Claude Code 的权限顺序为 deny → ask → allow，匹配的 ask 优先于 allow，具体规则不会覆盖通用规则。因此通用 `Skill` ask 使所有 Skill 调用（包括蓝图列出的 skill）都需要人工确认；精确 `Skill(name)` allow 无法预先放行，已移除。
- 未列 skill 没有按名称硬拒绝的规则；CLI 不提供“拒绝除这些名字外所有未知 skill”的内置规则。用户批准后，未列 skill 仍可能被调用；“只加载列出 skill”是任务包/`CLAUDE.md` 的指令级约束。
- 未禁用全部 skills：没有使用 `--disable-slash-commands`，没有把 `Skill` 放入 deny；离线自检断言 `Skill` 不在 deny 中。
- 未改变 DeepSeek 模型、认证或 provider 配置。
- 离线自检只验证配置形状（`Skill` 工具是否开放、ask 规则是否存在、allow 规则是否为空），不验证运行时权限引擎；真实提示行为未在本次会话中执行。

## 5. 修改的文件

| 文件 | 修改内容 |
|---|---|
| `scripts/thesis_blueprint.py` | 新增 `strictAllowlist`、2.1.219 版本门槛与 fail-closed；新增 user/project/local `sandbox.network.allowedDomains` 与 `WebFetch(domain:...)` 扩大白名单检查；新增通用 `Skill` ask 门槛并移除无实际作用的 `Skill(<name>)` allow 规则；新增离线 `self-check` 子命令与 11 个启动配置场景；保留任务包完整性、skill 资源冻结、allowed_paths 和插件隔离逻辑。 |
| `docs/thesis/blueprints/README.md` | 补充 strictAllowlist 版本要求、本地无网/白名单联网策略、WebFetch 规则合并与 fail-closed、远程 `network_domains` 的授权清单性质、Skill 权限的人工确认边界和 `self-check` 命令。 |
| `CLAUDE.md` | 补充本地 Bash 版本门槛与 strictAllowlist、WebFetch/设置规则扩大白名单的 fail-closed 要求、远程网络清单不是 ACL、Skill 权限不是硬白名单。 |
| `docs/thesis/blueprints/template.json` | 审阅后未改；默认标题 `研究问题`、`论文核心结论权限` 在当前证据文件中存在，策略字段与模板结构有效。 |
| `docs/thesis/claude-code-capability-audit-20261018.md` | 本报告，更新证据、版本要求、行号、限制与自检结果。 |

没有修改允许范围之外的文件、全局配置、凭据或权限规则。没有修改论文正文、正式 DOCX、实验数据或模型检查点。

## 6. 执行的核验

| 命令/检查 | 结果 |
|---|---|
| `python3 -m py_compile scripts/thesis_blueprint.py` | 通过 |
| `python3 -m json.tool docs/thesis/blueprints/template.json` | 通过 |
| `python3 scripts/thesis_blueprint.py --help` | 通过；显示 `new/validate/prepare/execute/collect/run/self-check` |
| `python3 scripts/thesis_blueprint.py self-check` | 11/11 通过：`local_no_network`、`local_whitelist_network`、`webfetch_rule_discovered`、`webfetch_expansion_rejected`、`webfetch_declared_allowed`、`remote_task`、`skills_declared_requires_confirmation`、`skills_unspecified_not_exposed`、`old_version_rejected`、`min_version_accepted`、`launch_command_shape` |
| `git diff --check` | 返回码 0 |
| 当前会话只读加载 `research-paper-writing` | 通过；未读取论文正文，未执行写作步骤 |
| `claude --version` | `2.1.302 (Claude Code)` |
| 当前设置规则扫描 | `sandbox_expansion_rules()` 计数 0；启用插件 37 个 |

`self-check` 是离线构造检查：不启动 Claude 模型、不访问外网、不连接远程主机。它验证的是 `Skill` 工具是否只在蓝图声明 Skill 时开放、通用 `Skill` ask 是否存在、`Skill(name)` allow 是否为空，以及本地沙箱/远程/版本等配置形状；它不验证真实沙箱网络行为，不验证 CLI 权限引擎的运行时交互，也不验证用户批准/拒绝后的实际 skill 调用结果。`git diff --check` 只覆盖已跟踪差异；`README.md`、`template.json`、`scripts/thesis_blueprint.py` 和本报告在当前工作区是未跟踪文件，因此该命令没有覆盖它们。

## 7. 未解决问题与限制

1. **未执行端到端运行。** 没有创建真实任务蓝图，也没有运行 `prepare → execute → collect`；运行时闭环只完成了离线配置构造和 skill 加载核验。
2. **未执行真实沙箱网络运行。** `strictAllowlist` 的配置形状已由离线自检覆盖，但未在真实沙箱中验证“未列主机被确定性拒绝”。最终状态仍需 Codex 或后续受控运行确认。
3. **`allowed_paths` 不是 OS 级边界。** 原生 Write/Edit 仍可在项目工作区写文件；`collect` 是事后差异审计。
4. **Git 忽略路径不可见。** `collect` 使用 `git ls-files --others --exclude-standard`，写入被 Git 忽略的路径不会出现在回收差异中。
5. **回收记录是自引用的。** `baseline.json`/`state.json` 位于任务包内；如果执行者同时改写两者，单靠 `collect` 不能提供防篡改保证。
6. **远程 `network_domains` 不是 ACL。** 远程任务不使用本地沙箱，逐条 Bash 人工确认是实际门槛；不能把该清单描述为远程侧强制网络过滤。
7. **`strictAllowlist` 不约束 WebFetch。** 它只约束 sandboxed Bash；WebSearch/WebFetch 仍由工具权限控制。
8. **WebFetch 扩大白名单检查是保守精确匹配。** 逻辑上被通配符覆盖的主机仍会被拒绝；需要逐字声明。项目级规则在 strictAllowlist 下本会被排除，但启动逻辑仍选择 fail closed。managed/policy 设置不在脚本读取范围内。
9. **Skill 权限不是硬白名单。** 当前实现保留通用 `Skill` ask，所有 Skill 调用（包括蓝图列出的 skill）都需要人工确认；未列 skill 没有按名称硬拒绝的规则，用户批准后仍可能被调用。离线自检只验证配置形状，不验证运行时权限引擎或真实提示行为。任务包的“只加载列出 skill”是指令级约束。
10. **Skill 资源冻结依赖反引号扫描。** 只有匹配 `assets/`、`references/`、`scripts/`、`agents/`、`tests/` 的反引号路径会被哈希；纯文本提到但未加反引号的资源不会被冻结。
11. **Git 忽略路径与既有脏文件指纹。** 对任务开始前已脏且不在允许范围内的文件，使用 size/mtime 指纹；内容变化但大小和 mtime 不变的情况不会被发现。
12. **`allowed_paths` 通配符较宽。** 使用 `fnmatch.fnmatchcase`，`*` 可以跨 `/`；建议蓝图使用精确文件或目录路径。
13. **cdut 学校格式模式不可用。** 缺少 `assets/cdut-professional-master-20230905.docx`；候选模板哈希不一致且未确认权威性；未复制、未伪造。
14. **macOS Word/PDF 收尾不可用。** 无 `pwsh`/`powershell` 和 Microsoft Word；`soffice` 存在但不等于 Word 字段更新与视觉验收。
15. **`unrecognized_model` 未解决。** 未找到服务端认可模型标识的本地证据，保留现状；未猜测、未自动替换。
16. **工作区基线很脏。** 大量既有 `M`/`D`/`??` 改动仍在；未重置、暂存、提交或推送。Codex 复核时应查看工作区实际文件（包括未跟踪文件），不能只依赖 `git diff`。

## 8. 结论与交接

本轮修订按 Codex 意见补齐了本地 Bash 的 `strictAllowlist` 策略、2.1.219 版本 fail-closed、WebFetch/设置规则扩大白名单的启动前拦截，以及通用 `Skill` ask 人工确认门槛（精确 `Skill(name)` allow 已移除）。离线 `self-check` 覆盖了本地无网、本地白名单联网、WebFetch 规则发现与扩大白名单拒绝、远程任务、指定/未指定 skill、旧版本拒绝、最低版本接受和启动命令形状，全部通过；它只验证配置形状，不验证运行时权限引擎。

但本次没有真实沙箱网络运行，也没有端到端 `prepare → execute → collect` 闭环；学校格式模式仍因模板缺失不可用，Word/PDF 收尾在 macOS 上受限，`unrecognized_model` 只有诊断、没有解决方案。最终状态继续为 `pending_codex_review`，不宣布验收通过，交由 Codex 复核实际改动、证据和未解决问题。
