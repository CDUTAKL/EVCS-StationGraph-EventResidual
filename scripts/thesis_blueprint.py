#!/usr/bin/env python3
"""Create, validate, prepare, execute, and collect thesis task packets.

Uses only the Python standard library. It does not commit files or make the
acceptance decision; Codex reviews every returned task packet.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
TASKS = Path("docs/thesis/blueprints/tasks")
TEMPLATE = Path("docs/thesis/blueprints/template.json")
TASK_TYPES = {
    "content_revision",
    "evidence_audit",
    "literature_review",
    "experiment_design",
    "figure_revision",
    "delivery_audit",
    "scoring",
    "other",
}
PACKAGE_FILES = {
    "blueprint.json",
    "context-snapshot.json",
    "EXECUTION_PACKET.md",
    "execution-report.json",
    "baseline.json",
    "state.json",
    "collection-report.json",
}
MAX_SOURCE_CHARS = 100_000
SKILL_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,79}")
STRICT_ALLOWLIST_MIN_VERSION = (2, 1, 219)
SETTINGS_SOURCES = (
    ("用户设置", Path.home() / ".claude" / "settings.json"),
    ("项目设置", ROOT / ".claude" / "settings.json"),
    ("项目本地设置", ROOT / ".claude" / "settings.local.json"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("无法读取JSON文件 {}: {}".format(path, exc)) from exc
    if not isinstance(value, dict):
        raise ValueError("JSON顶层必须是对象: {}".format(path))
    return value


def project_path(raw: str, must_exist: bool = False) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("路径必须是项目内相对路径且不能包含..: {}".format(raw))
    resolved = (ROOT / candidate).resolve(strict=must_exist)
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("路径解析后越出项目目录: {}".format(raw))
    return resolved


def claude_skill_path(name: str) -> Path:
    """Resolve one explicitly requested Claude Code skill without following arbitrary names."""
    if not SKILL_NAME_RE.fullmatch(name):
        raise ValueError("Claude skill名称格式无效: {}".format(name))
    candidates = [ROOT / ".claude" / "skills" / name, Path.home() / ".claude" / "skills" / name]
    for candidate in candidates:
        skill_file = candidate / "SKILL.md"
        if skill_file.is_file():
            return skill_file.resolve(strict=True)
    raise ValueError("未找到Claude skill {}/SKILL.md（检查项目或用户级.claude/skills）".format(name))


def skill_details(name: str) -> Tuple[Path, str, List[Tuple[str, Path]]]:
    """Validate one explicitly requested skill and resolve its referenced resources."""
    path = claude_skill_path(name)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("skill {}无法读取: {}".format(name, exc)) from exc
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", content, flags=re.DOTALL)
    if not match:
        raise ValueError("skill {}缺少有效YAML frontmatter".format(name))
    frontmatter = match.group(1)
    declared_name = re.search(r"^name:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", frontmatter, re.MULTILINE)
    description = re.search(r"^description:\s*(\S.*)$", frontmatter, re.MULTILINE)
    if not declared_name or declared_name.group(1).strip() != name:
        raise ValueError("skill目录名与frontmatter name不一致: {}".format(name))
    if not description:
        raise ValueError("skill {}缺少非空description（Claude发现/调用所需）".format(name))
    missing_resources = []
    resources: List[Tuple[str, Path]] = []
    skill_root = path.parent
    skill_kit_root = skill_root.parent.parent if skill_root.parent.name == "skills" else None
    for resource in re.findall(r"`((?:assets|references|scripts|agents|tests)/[^`\s]+)`", content):
        resource = resource.rstrip(".,;:)")
        candidate_roots = [skill_root]
        if skill_kit_root is not None and resource.startswith(("scripts/", "tests/", "agents/")):
            candidate_roots.append(skill_kit_root)
        found = next((root / resource for root in candidate_roots if (root / resource).exists()), None)
        if found is None:
            missing_resources.append(resource)
        else:
            resources.append((resource, found))
    if missing_resources:
        raise ValueError(
            "skill {}引用的资源缺失: {}；该skill当前不可用，禁止创建空占位资源".format(
                name, ", ".join(sorted(set(missing_resources)))
            )
        )
    return path, content, resources


def validate_skill(name: str) -> Path:
    return skill_details(name)[0]


def skill_resource_hash_map(names: Iterable[str]) -> Dict[str, str]:
    """Hash every referenced skill file with portable labels, never absolute paths."""
    result: Dict[str, str] = {}
    for name in names:
        for label, resource in skill_details(name)[2]:
            if resource.is_file():
                result["{}:{}".format(name, label)] = sha256_file(resource)
            elif resource.is_dir():
                for child in sorted(resource.rglob("*")):
                    if child.is_file():
                        child_label = label.rstrip("/") + "/" + child.relative_to(resource).as_posix()
                        result["{}:{}".format(name, child_label)] = sha256_file(child)
    return result


def relpath(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def task_dir(task_id_or_path: str) -> Path:
    candidate = Path(task_id_or_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if ROOT.resolve() not in resolved.parents:
            raise ValueError("任务目录必须位于项目内")
        return resolved
    if candidate.exists() and candidate.is_dir():
        return candidate.resolve()
    if "/" in task_id_or_path or "\\" in task_id_or_path:
        return project_path(task_id_or_path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,79}", task_id_or_path):
        raise ValueError("任务ID只能包含字母、数字、点、下划线和连字符")
    return (ROOT / TASKS / task_id_or_path).resolve()


def source_arg(raw: str, purpose: str) -> Dict[str, Any]:
    path_text, marker, selector = raw.rpartition("#")
    if not marker:
        path_text = raw
        locator = {"kind": "whole_file"}
    elif selector.startswith("L") and "-L" in selector:
        match = re.fullmatch(r"L([1-9][0-9]*)-L([1-9][0-9]*)", selector)
        if not match:
            raise ValueError("行范围格式应为 path#L起始-L结束")
        locator = {"kind": "line_range", "start": int(match.group(1)), "end": int(match.group(2))}
    else:
        locator = {"kind": "markdown_heading", "value": selector}
    project_path(path_text, must_exist=True)
    return {"path": Path(path_text).as_posix(), "locator": locator, "purpose": purpose}


def allowed_path_error(raw: str, task_directory: Path) -> Optional[str]:
    """Fail closed on allowed paths that would bypass scope or handoff controls."""
    try:
        resolved = project_path(raw)
    except (ValueError, OSError) as exc:
        return str(exc)
    root = ROOT.resolve()
    if resolved == root:
        return "allowed_paths不能是项目根目录: {}".format(raw)
    normalized = raw.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts:
        return "allowed_paths路径无效: {}".format(raw)
    first = parts[0]
    if first == "~":
        return "allowed_paths必须是项目内相对路径，不能使用家目录简写: {}".format(raw)
    if any(char in first for char in "*?["):
        return "allowed_paths首段不能包含通配符，避免放开整个项目: {}".format(raw)
    if first in {".git", ".claude", ".ssh"}:
        return "禁止把Git/Claude设置/SSH路径列为可写范围: {}".format(raw)
    filename = parts[-1]
    if (
        filename == ".env"
        or filename.startswith(".env.")
        or filename.endswith((".pem", ".key", ".p12", ".pfx"))
        or filename.startswith("id_rsa")
    ):
        return "禁止把凭据类路径列为可写范围: {}".format(raw)
    for prefix in ("data/external", "data/interim", "data/processed"):
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return "禁止把原始数据路径列为可写范围: {}".format(raw)
    try:
        task_prefix = relpath(task_directory).rstrip("/") + "/"
    except ValueError:
        task_prefix = ""
    if task_prefix and (normalized == task_prefix.rstrip("/") or normalized.startswith(task_prefix)):
        return "allowed_paths不能包含任务包目录: {}".format(raw)
    if parts == ("scripts",):
        return "allowed_paths不能直接放开整个scripts目录: {}".format(raw)
    for control in ("scripts/thesis_blueprint.py", ".gitignore"):
        if fnmatch.fnmatchcase(control, normalized):
            return "禁止把交接控制文件列为可写范围: {}".format(raw)
    if normalized == "docs/thesis/blueprints" or normalized.startswith("docs/thesis/blueprints/"):
        return "禁止把交接控制文件列为可写范围: {}".format(raw)
    return None


def validate_blueprint(bp: Dict[str, Any], directory: Path) -> List[str]:
    errors: List[str] = []
    required_strings = ["task_id", "title", "task_type", "workflow_stage", "objective"]
    for key in required_strings:
        if not isinstance(bp.get(key), str) or not bp[key].strip():
            errors.append("{}必须是非空字符串".format(key))
    if bp.get("schema_version") != 1:
        errors.append("schema_version必须为1")
    if bp.get("task_type") not in TASK_TYPES:
        errors.append("task_type必须属于{}".format(sorted(TASK_TYPES)))
    task_id = bp.get("task_id", "")
    if task_id and directory.name != task_id:
        errors.append("目录名{}与task_id {}不一致".format(directory.name, task_id))

    for field in ("context_sources", "evidence_sources"):
        sources = bp.get(field)
        if not isinstance(sources, list):
            errors.append("{}必须是数组".format(field))
            continue
        for index, source in enumerate(sources):
            label = "{}[{}]".format(field, index)
            if not isinstance(source, dict):
                errors.append("{}必须是对象".format(label))
                continue
            if not isinstance(source.get("path"), str) or not source.get("path"):
                errors.append("{}.path必须是非空字符串".format(label))
                continue
            try:
                path = project_path(source["path"], must_exist=True)
            except (ValueError, OSError) as exc:
                errors.append("{}.path无效: {}".format(label, exc))
                continue
            if not path.is_file():
                errors.append("{}.path必须指向文件".format(label))
            locator = source.get("locator")
            if not isinstance(locator, dict) or locator.get("kind") not in {
                "whole_file", "markdown_heading", "line_range"
            }:
                errors.append("{}.locator.kind须为whole_file、markdown_heading或line_range".format(label))
            elif locator.get("kind") == "markdown_heading" and not str(locator.get("value", "")).strip():
                errors.append("{}.locator.value不能为空".format(label))
            elif locator.get("kind") == "line_range":
                start, end = locator.get("start"), locator.get("end")
                if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
                    errors.append("{}.locator行号范围无效".format(label))
            if not isinstance(source.get("purpose"), str) or not source.get("purpose", "").strip():
                errors.append("{}.purpose必须说明读取用途".format(label))

    allowed = bp.get("allowed_paths")
    if not isinstance(allowed, list) or not allowed:
        errors.append("allowed_paths不能为空，列出本任务可写的文件或目录")
    else:
        for item in allowed:
            if not isinstance(item, str) or not item:
                errors.append("allowed_paths只能包含非空路径字符串")
                continue
            error = allowed_path_error(item, directory)
            if error:
                errors.append(error)

    for key in ("locked_claims", "steps", "acceptance_criteria", "deliverables"):
        value = bp.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append("{}必须是字符串数组".format(key))
        elif key in {"steps", "acceptance_criteria", "deliverables"} and not value:
            errors.append("{}不能为空".format(key))
    policy = bp.get("execution_policy")
    if not isinstance(policy, dict):
        errors.append("execution_policy必须是对象")
    else:
        for key in ("training_allowed", "remote_execution_allowed", "network_access_allowed", "git_mutations_allowed"):
            if not isinstance(policy.get(key), bool):
                errors.append("execution_policy.{}必须是布尔值".format(key))
        checks = policy.get("checks_to_run")
        if not isinstance(checks, list) or any(not isinstance(item, str) or not item.strip() for item in checks):
            errors.append("execution_policy.checks_to_run必须是非空字符串组成的数组（允许空数组）")
        domains = policy.get("network_domains", [])
        if not isinstance(domains, list) or any(
            not isinstance(domain, str) or not re.fullmatch(r"(?:\*\.)?[A-Za-z0-9.-]+", domain)
            for domain in domains
        ):
            errors.append("execution_policy.network_domains须为主机名数组，不含协议、路径或凭据")
        if policy.get("remote_execution_allowed") is True and policy.get("network_access_allowed") is not True:
            errors.append("远程执行需要同时显式设置network_access_allowed=true")
        if domains and policy.get("network_access_allowed") is not True:
            errors.append("network_domains非空时必须同时设置network_access_allowed=true")
        if policy.get("remote_execution_allowed") is True and not domains:
            errors.append("远程执行必须在network_domains中列出主机白名单")
    if not bp.get("context_sources") and not bp.get("evidence_sources"):
        errors.append("至少选择一项当前证据控制台或直接证据，并指定精确定位")
    skills = bp.get("claude_skills", [])
    if not isinstance(skills, list) or any(not isinstance(item, str) for item in skills):
        errors.append("claude_skills必须是skill名称数组")
    else:
        if len(skills) != len(set(skills)):
            errors.append("claude_skills不能重复")
        for name in skills:
            try:
                validate_skill(name)
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def extract_source(source: Dict[str, Any]) -> Dict[str, Any]:
    path = project_path(source["path"], must_exist=True)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    locator = source["locator"]
    kind = locator["kind"]
    if kind == "whole_file":
        excerpt = text
    elif kind == "line_range":
        lines = text.splitlines()
        start, end = locator["start"], locator["end"]
        if end > len(lines):
            raise ValueError("{}只含{}行，请修正行范围".format(source["path"], len(lines)))
        excerpt = "\n".join(lines[start - 1 : end])
    else:
        target = str(locator["value"]).strip()
        lines = text.splitlines()
        matches: List[Tuple[int, int, int]] = []
        for index, line in enumerate(lines):
            match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if match and match.group(2).strip() == target:
                matches.append((index, len(match.group(1)), index + 1))
        if len(matches) != 1:
            raise ValueError("{}中标题“{}”匹配{}处，必须唯一".format(source["path"], target, len(matches)))
        start, level, _ = matches[0]
        end = len(lines)
        for index in range(start + 1, len(lines)):
            match = re.match(r"^(#{1,6})\s+", lines[index])
            if match and len(match.group(1)) <= level:
                end = index
                break
        excerpt = "\n".join(lines[start:end])
    if len(excerpt) > MAX_SOURCE_CHARS:
        raise ValueError("摘录{}字符，超过{}；请缩小定位范围，避免把整篇材料塞入任务包".format(len(excerpt), MAX_SOURCE_CHARS))
    return {
        "path": source["path"],
        "purpose": source["purpose"],
        "locator": locator,
        "source_sha256": sha256_bytes(raw),
        "excerpt_sha256": sha256_bytes(excerpt.encode("utf-8")),
        "excerpt": excerpt,
    }


def git_bytes(args: Sequence[str]) -> bytes:
    result = subprocess.run(["git", *args], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError("git {} 失败: {}".format(" ".join(args), result.stderr.decode("utf-8", "replace").strip()))
    return result.stdout


def git_head() -> str:
    return git_bytes(["rev-parse", "HEAD"]).decode("ascii").strip()


def dirty_paths(excluded_prefix: Optional[str] = None) -> List[str]:
    tracked = git_bytes(["diff", "--name-only", "--no-renames", "-z", "HEAD"]).decode("utf-8", "surrogateescape")
    untracked = git_bytes(["ls-files", "--others", "--exclude-standard", "-z"]).decode("utf-8", "surrogateescape")
    paths = set(part for part in tracked.split("\0") + untracked.split("\0") if part)
    if excluded_prefix:
        prefix = excluded_prefix.rstrip("/") + "/"
        paths = {item for item in paths if item != excluded_prefix and not item.startswith(prefix)}
    return sorted(paths)


def stat_record(path: Path, include_hash: bool) -> Dict[str, Any]:
    if not path.exists() and not path.is_symlink():
        return {"exists": False}
    info = path.lstat()
    record: Dict[str, Any] = {
        "exists": True,
        "kind": "symlink" if path.is_symlink() else "file" if path.is_file() else "other",
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
    }
    if path.is_symlink():
        record["target"] = os.readlink(str(path))
    elif path.is_file() and include_hash:
        record["sha256"] = sha256_file(path)
    return record


def matches_allowed(path: str, allowed: Iterable[str]) -> bool:
    for pattern in allowed:
        normalized = pattern.replace("\\", "/")
        if path == normalized or fnmatch.fnmatchcase(path, normalized):
            return True
        if normalized.endswith("/") and path.startswith(normalized):
            return True
        if not any(char in normalized for char in "*?[") and path.startswith(normalized.rstrip("/") + "/"):
            return True
    return False


def read_task_files(directory: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    bp_path = directory / "blueprint.json"
    bp = read_json(bp_path)
    errors = validate_blueprint(bp, directory)
    if errors:
        raise ValueError("蓝图校验失败:\n- " + "\n- ".join(errors))
    return bp, read_json(directory / "state.json") if (directory / "state.json").exists() else {}, read_json(directory / "baseline.json") if (directory / "baseline.json").exists() else {}


def cmd_new(args: argparse.Namespace) -> int:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,79}", args.id):
        raise ValueError("任务ID只能包含字母、数字、点、下划线和连字符")
    directory = ROOT / TASKS / args.id
    if directory.exists():
        raise ValueError("任务目录已存在，不覆盖: {}".format(relpath(directory)))
    bp = read_json(ROOT / TEMPLATE)
    bp["task_id"] = args.id
    bp["title"] = args.title or ""
    bp["task_type"] = args.type
    bp["workflow_stage"] = args.stage or ""
    bp["objective"] = args.objective or ""
    bp["allowed_paths"] = list(args.allow or [])
    if args.context:
        bp["context_sources"].extend(source_arg(item, "Codex为本任务选择的证据控制台摘录") for item in args.context)
    if args.evidence:
        bp["evidence_sources"] = [source_arg(item, "Codex为本任务选择的直接证据摘录") for item in args.evidence]
    directory.mkdir(parents=True)
    atomic_json(directory / "blueprint.json", bp)
    atomic_json(directory / "state.json", {"task_id": args.id, "status": "draft", "created_at": now()})
    print("已创建蓝图: {}".format(relpath(directory / "blueprint.json")))
    print("补齐title、workflow_stage、objective、allowed_paths、steps、acceptance_criteria和所需证据定位后运行 validate。")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    directory = task_dir(args.task)
    bp = read_json(directory / "blueprint.json")
    errors = validate_blueprint(bp, directory)
    if errors:
        print("蓝图未通过校验:")
        for item in errors:
            print("- {}".format(item))
        return 2
    for source in bp["context_sources"] + bp["evidence_sources"]:
        try:
            extract_source(source)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            errors.append("{}: {}".format(source.get("path"), exc))
    if errors:
        print("来源定位未通过校验:")
        for item in errors:
            print("- {}".format(item))
        return 2
    print("蓝图和{}项来源定位通过结构校验。".format(len(bp["context_sources"]) + len(bp["evidence_sources"])))
    print("此命令只校验结构与定位，不评价证据是否支持主张。")
    return 0


def prompt_text(bp: Dict[str, Any], directory: Path, context: Dict[str, Any]) -> str:
    lines = [
        "# Claude Code执行任务包",
        "",
        "任务编号：{}".format(bp["task_id"]),
        "任务类型：{}；对应12流程阶段：{}".format(bp["task_type"], bp["workflow_stage"]),
        "目标：{}".format(bp["objective"]),
        "",
        "## 开始前",
        "只依据本任务包的冻结摘录和蓝图列出的材料工作。不要从聊天历史、归档计划或整份实验登记表重建当前状态。正文源稿为`docs/thesis/thesis-manuscript.md`。",
        "",
        "## 可写范围",
    ]
    lines.extend("- `{}`".format(item) for item in bp["allowed_paths"])
    lines.append("- 以上路径是任务约束和事后审计范围，不是操作系统级文件隔离；不要写入未列路径，也不要把Git忽略路径当作可审计输出。")
    lines += ["", "## 锁定主张与口径"]
    lines.extend("- {}".format(item) for item in bp["locked_claims"])
    lines += ["", "## 执行步骤"]
    lines.extend("{}. {}".format(index, item) for index, item in enumerate(bp["steps"], 1))
    skills = bp.get("claude_skills", [])
    if skills:
        lines += ["", "## 指定Claude Code Skills"]
        lines.extend("- 本任务明确要求调用`{}` skill；请通过Claude Code的Skill工具加载并遵循其适用步骤。".format(name) for name in skills)
        lines += [
            "- 只加载上面列出的skill；不要调用未列出的skill。",
            "- skill中的相对路径不要按项目根目录解释：先解析skill真实目录（`realpath ~/.claude/skills/<name>`）；skill自身资源在其目录下，kit级脚本/文档在kit根目录下。",
            "- 命名skill不会自动授予Bash；若skill步骤需要运行脚本，蓝图必须把对应命令列入`checks_to_run`，否则只做只读分析并在报告中说明。",
            "- skill的`SKILL.md`和引用资源已在prepare时冻结哈希；若发现资源缺失或被改动，停止并报告，不要创建空占位文件。",
        ]
    else:
        lines += ["", "## 指定Claude Code Skills", "- 本任务未指定Claude Code专用skill；如需技能支持，先在报告中说明阻塞，不要假定Codex全局skill已自动安装到Claude Code。"]
    lines += ["", "## 验收条件"]
    lines.extend("- {}".format(item) for item in bp["acceptance_criteria"])
    lines += ["", "## 操作权限"]
    policy = bp["execution_policy"]
    lines += [
        "- 训练：{}；远程执行：{}；联网：{}；Git提交/暂存：{}。".format(
            policy["training_allowed"], policy["remote_execution_allowed"],
            policy["network_access_allowed"], policy["git_mutations_allowed"]
        ),
        "- 除非明确列入允许范围，不得启动训练、远程作业、联网采集、Git暂存/提交或覆盖正式Word。不得使用绕过权限的启动方式。",
        "- 不得修改`.git/`、`.claude/settings*.json`、凭据文件或交接控制文件；如需修改，停止并报告。",
        "- 只运行蓝图列出的检查：{}。未列检查时不要新增或运行测试。".format(", ".join(policy["checks_to_run"]) or "无"),
        "- Bash网络主机白名单：{}。空数组表示Bash无网络；WebSearch/WebFetch须单独取得工具权限。".format(", ".join(policy.get("network_domains", [])) or "无"),
        "",
        "## 冻结的证据摘录",
    ]
    for group, items in (("证据控制台", context["context_sources"]), ("直接证据", context["evidence_sources"])):
        if not items:
            continue
        lines += ["", "### {}".format(group)]
        for item in items:
            lines += [
                "",
                "#### {} — {}".format(item["path"], item["purpose"]),
                "定位：`{}`；来源SHA-256：`{}`".format(json.dumps(item["locator"], ensure_ascii=False), item["source_sha256"]),
            ]
            longest = max((len(match.group(0)) for match in re.finditer(r"`+", item["excerpt"])), default=0)
            fence = "`" * max(3, longest + 1)
            lines += [fence + "text", item["excerpt"], fence]
    lines += ["", "## 完成报告"]
    lines += [
        "在`{}`填写Claude Code工作报告。changed_paths使用项目根目录相对路径，仅列实际工作区改动，不必列报告自身；列出证据来源、检查、未解决事项，以及所有数字或主张变化。报告只供Codex复检，不代表验收。".format(relpath(directory / "execution-report.json")),
        "在`model`字段填写当前Claude Code会话实际报告的模型标识；`user_reported_model`只是操作者标签。若provider返回`unrecognized_model`，把原始模型名和诊断写入`unresolved`，不要猜测或自动替换模型。",
        "如证据不足、需要扩大修改范围或发生未授权操作，停止继续并在报告中说明。",
        "",
    ]
    return "\n".join(lines)


def snapshot_dirty(excluded_task_dir: Path, allowed: Sequence[str]) -> Dict[str, Any]:
    excluded = relpath(excluded_task_dir)
    entries: Dict[str, Any] = {}
    for raw in dirty_paths(excluded_prefix=excluded):
        path = project_path(raw)
        include_hash = matches_allowed(raw, allowed)
        entries[raw] = stat_record(path, include_hash=include_hash)
    return {"head": git_head(), "paths": entries, "captured_at": now()}


def state_write(directory: Path, status: str, **extra: Any) -> None:
    path = directory / "state.json"
    current = read_json(path) if path.exists() else {"task_id": directory.name}
    current.update({"status": status, "updated_at": now()})
    current.update(extra)
    atomic_json(path, current)


def cmd_prepare(args: argparse.Namespace) -> int:
    directory = task_dir(args.task)
    bp = read_json(directory / "blueprint.json")
    errors = validate_blueprint(bp, directory)
    if errors:
        raise ValueError("蓝图校验失败:\n- " + "\n- ".join(errors))
    if (directory / "baseline.json").exists() and not args.refresh:
        raise ValueError("任务已准备过。若尚未执行且确需重建基线，显式使用--refresh")
    state_path = directory / "state.json"
    state = read_json(state_path) if state_path.exists() else {}
    if (directory / "collection-report.json").exists():
        raise ValueError("已有回收报告；请保留本轮任务包并为后续工作创建新任务ID")
    if state.get("status") not in {"draft", "ready", "execution_not_started"}:
        raise ValueError("任务状态为{}，不能覆盖已有执行包".format(state.get("status")))
    context_items = [extract_source(item) for item in bp["context_sources"]]
    evidence_items = [extract_source(item) for item in bp["evidence_sources"]]
    context = {
        "task_id": bp["task_id"],
        "frozen_at": now(),
        "context_sources": context_items,
        "evidence_sources": evidence_items,
    }
    atomic_json(directory / "context-snapshot.json", context)
    atomic_json(directory / "execution-report.json", {
        "task_id": bp["task_id"],
        "executor": "Claude Code",
        "model": "",
        "user_reported_model": bp["execution_policy"].get("user_reported_model", ""),
        "summary": "",
        "changed_paths": [],
        "evidence_used": [],
        "claim_or_number_changes": [],
        "checks": [],
        "unresolved": [],
        "blockers": [],
    })
    packet = prompt_text(bp, directory, context)
    (directory / "EXECUTION_PACKET.md").write_text(packet, encoding="utf-8")
    baseline = snapshot_dirty(directory, bp["allowed_paths"])
    baseline["allowed_paths"] = bp["allowed_paths"]
    baseline["protected_package_hashes"] = {
        filename: sha256_file(directory / filename)
        for filename in ("blueprint.json", "context-snapshot.json", "EXECUTION_PACKET.md")
    }
    baseline["source_hashes"] = {
        item["path"]: item["source_sha256"]
        for item in context_items + evidence_items
    }
    selected_skills = bp.get("claude_skills", [])
    baseline["claude_skill_hashes"] = {
        name: sha256_file(validate_skill(name)) for name in selected_skills
    }
    baseline["claude_skill_resource_hashes"] = skill_resource_hash_map(selected_skills)
    baseline["selected_excerpt_characters"] = sum(
        len(item["excerpt"]) for item in context_items + evidence_items
    )
    atomic_json(directory / "baseline.json", baseline)
    state_write(
        directory,
        "ready",
        prepared_at=now(),
        baseline_head=baseline["head"],
        baseline_sha256=sha256_file(directory / "baseline.json"),
    )
    print("任务包已准备: {}".format(relpath(directory / "EXECUTION_PACKET.md")))
    print("冻结{}项控制台摘录、{}项直接证据；允许修改{}项路径；基线HEAD {}".format(
        len(context_items), len(evidence_items), len(bp["allowed_paths"]), baseline["head"][:12]
    ))
    print("冻结证据摘录共{}字符（不含任务指令和Claude Code稳定规则）。".format(baseline["selected_excerpt_characters"]))
    print("接下来运行 execute；没有启动模型调用。")
    return 0


def current_snapshot(directory: Path, baseline: Dict[str, Any]) -> Dict[str, Any]:
    allowed = baseline["allowed_paths"]
    excluded = relpath(directory)
    paths: Dict[str, Any] = {}
    for raw in dirty_paths(excluded_prefix=excluded):
        path = project_path(raw)
        old = baseline["paths"].get(raw, {})
        include_hash = matches_allowed(raw, allowed) or "sha256" in old
        paths[raw] = stat_record(path, include_hash=include_hash)
    return {"head": git_head(), "paths": paths, "captured_at": now()}


def changes_since_baseline(baseline: Dict[str, Any], current: Dict[str, Any]) -> List[Dict[str, Any]]:
    changes = []
    before, after = baseline["paths"], current["paths"]
    for path in sorted(set(before) | set(after)):
        if before.get(path) != after.get(path):
            changes.append({"path": path, "before": before.get(path), "after": after.get(path)})
    return changes


def report_errors(
    report: Any, task_id: str, actual_paths: Sequence[str],
    own_report_path: Optional[str] = None,
) -> List[str]:
    errors: List[str] = []
    if not isinstance(report, dict):
        return ["execution-report.json顶层必须是对象"]
    if report.get("task_id") != task_id:
        errors.append("execution-report.task_id与蓝图不一致")
    if not isinstance(report.get("summary"), str) or not report.get("summary", "").strip():
        errors.append("execution-report.summary尚未填写")
    list_fields = ("changed_paths", "evidence_used", "claim_or_number_changes", "checks", "unresolved", "blockers")
    for field in list_fields:
        if not isinstance(report.get(field), list):
            errors.append("execution-report.{}必须是数组".format(field))
    claimed = set(report.get("changed_paths", [])) if isinstance(report.get("changed_paths"), list) else set()
    # The mutable executor report is package metadata, excluded from workspace
    # snapshots. Tolerate only this exact task's self-reported report path;
    # protected and unexpected package files remain independently audited.
    if own_report_path is not None:
        claimed.discard(own_report_path)
    actual = set(actual_paths)
    missing = sorted(actual - claimed)
    invented = sorted(claimed - actual)
    if missing:
        errors.append("报告漏列实际改动: {}".format(", ".join(missing)))
    if invented:
        errors.append("报告列出但未检测到的改动: {}".format(", ".join(invented)))
    return errors


def cmd_collect(args: argparse.Namespace) -> int:
    directory = task_dir(args.task)
    bp, state, baseline = read_task_files(directory)
    if not baseline:
        raise ValueError("未找到冻结基线，请先运行prepare")
    current = current_snapshot(directory, baseline)
    changes = changes_since_baseline(baseline, current)
    allowed_changes = [item for item in changes if matches_allowed(item["path"], bp["allowed_paths"])]
    out_of_scope = [item for item in changes if not matches_allowed(item["path"], bp["allowed_paths"])]
    current_head_changed = current["head"] != baseline["head"]
    committed_paths: List[str] = []
    if current_head_changed:
        committed_paths = sorted(set(
            part for part in git_bytes([
                "diff", "--name-only", "--no-renames", "-z", baseline["head"], current["head"]
            ]).decode("utf-8", "surrogateescape").split("\0") if part
        ))
    package_prefix = relpath(directory).rstrip("/") + "/"
    package_files = {
        relpath(path)[len(package_prefix):]
        for path in directory.rglob("*") if path.is_file()
    }
    unexpected_package_files = sorted(package_files - PACKAGE_FILES)
    protected_changes = []
    for filename, expected_hash in baseline.get("protected_package_hashes", {}).items():
        path = directory / filename
        if not path.exists() or sha256_file(path) != expected_hash:
            protected_changes.append(filename)
    if state.get("baseline_sha256") != sha256_file(directory / "baseline.json"):
        protected_changes.append("baseline.json")
    report_path = directory / "execution-report.json"
    try:
        executor_report = read_json(report_path)
    except ValueError as exc:
        executor_report = {}
        report_read_error = str(exc)
    else:
        report_read_error = ""
    changed_names = [item["path"] for item in changes]
    executor_errors = report_errors(executor_report, bp["task_id"], changed_names, relpath(report_path))
    if report_read_error:
        executor_errors.append(report_read_error)
    if not isinstance(executor_report.get("model"), str) or not executor_report.get("model", "").strip():
        executor_errors.append("execution-report.model未记录")
    if current_head_changed:
        status = "baseline_changed"
    elif out_of_scope or unexpected_package_files or protected_changes:
        status = "scope_violation"
    elif executor_errors:
        status = "report_incomplete"
    else:
        status = "awaiting_codex_review"
    result = {
        "schema_version": 1,
        "task_id": bp["task_id"],
        "status": status,
        "collected_at": now(),
        "baseline_head": baseline["head"],
        "current_head": current["head"],
        "committed_changes_since_baseline": committed_paths,
        "allowed_changes": allowed_changes,
        "out_of_scope_changes": out_of_scope,
        "unexpected_package_files": unexpected_package_files,
        "protected_package_changes": protected_changes,
        "executor_report_errors": executor_errors,
        "executor_report": executor_report,
        "acceptance": "pending_codex_review",
        "note": "本报告记录差异和交接状态，不替代证据审阅、评分或最终验收。",
    }
    atomic_json(directory / "collection-report.json", result)
    state_write(directory, status, collected_at=now())
    print("回收完成，状态: {}".format(status))
    print("授权范围内变化{}项，范围外变化{}项。".format(len(allowed_changes), len(out_of_scope)))
    if committed_paths:
        print("基线后提交涉及{}个路径；HEAD变化时本轮交接不通过，需人工核查。".format(len(committed_paths)))
    print("报告: {}".format(relpath(directory / "collection-report.json")))
    if executor_errors:
        for error in executor_errors:
            print("- {}".format(error))
    return 0 if status == "awaiting_codex_review" else 3


def verify_protected_package(directory: Path, baseline: Dict[str, Any]) -> None:
    for filename, expected_hash in baseline.get("protected_package_hashes", {}).items():
        path = directory / filename
        if not path.exists() or sha256_file(path) != expected_hash:
            raise ValueError("任务包文件在prepare后被修改，未启动Claude Code: {}".format(filename))


def verify_unchanged_since_prepare(directory: Path, baseline: Dict[str, Any]) -> None:
    verify_protected_package(directory, baseline)
    current = current_snapshot(directory, baseline)
    changes = changes_since_baseline(baseline, current)
    if current["head"] != baseline["head"] or changes:
        paths = [item["path"] for item in changes]
        raise ValueError(
            "准备后工作区发生变化，未启动Claude Code。HEAD变化={}，路径变化={}。请先人工确认并重新prepare。".format(
                current["head"] != baseline["head"], paths[:30]
            )
        )
    for path, expected in baseline.get("source_hashes", {}).items():
        if sha256_file(project_path(path, must_exist=True)) != expected:
            raise ValueError("准备后证据源已变化，请重新prepare: {}".format(path))
    skill_hashes = baseline.get("claude_skill_hashes", {})
    selected_skills = list(skill_hashes)
    for name, expected in skill_hashes.items():
        try:
            current_hash = sha256_file(validate_skill(name))
        except ValueError as exc:
            raise ValueError("准备后Claude skill不可用，请重新prepare: {}".format(exc)) from exc
        if current_hash != expected:
            raise ValueError("准备后Claude skill已变化，请重新prepare: {}".format(name))
    if "claude_skill_resource_hashes" in baseline and skill_resource_hash_map(selected_skills) != baseline["claude_skill_resource_hashes"]:
        raise ValueError("准备后Claude skill引用资源已变化，请重新prepare")


def settings_documents() -> List[Tuple[str, Dict[str, Any]]]:
    """Load user/project/project-local settings without printing their values."""
    documents: List[Tuple[str, Dict[str, Any]]] = []
    for label, path in SETTINGS_SOURCES:
        if not path.is_file():
            continue
        try:
            documents.append((label, read_json(path)))
        except ValueError as exc:
            raise ValueError("无法读取{}以检查插件/网络扩大规则".format(label)) from exc
    return documents


def enabled_plugin_names() -> List[str]:
    """Collect plugin names enabled in user, project, and project-local settings."""
    names = set()
    for _, data in settings_documents():
        plugins = data.get("enabledPlugins")
        if isinstance(plugins, dict):
            names.update(name for name, enabled in plugins.items() if enabled)
        elif isinstance(plugins, list):
            names.update(str(name) for name in plugins)
    return sorted(str(name) for name in names)


def settings_expansion_hosts(data: Dict[str, Any]) -> List[str]:
    """Extract allowlist-widening hosts from one settings document."""
    hosts: List[str] = []
    sandbox = data.get("sandbox")
    if isinstance(sandbox, dict):
        network = sandbox.get("network")
        if isinstance(network, dict):
            allowed = network.get("allowedDomains")
            if isinstance(allowed, list):
                for host in allowed:
                    if isinstance(host, str) and host.strip():
                        hosts.append(host.strip())
    permissions = data.get("permissions")
    if isinstance(permissions, dict):
        allow = permissions.get("allow")
        if isinstance(allow, list):
            for rule in allow:
                if not isinstance(rule, str):
                    continue
                match = re.fullmatch(
                    r"\s*WebFetch\(\s*domain\s*:\s*([^)]+?)\s*\)\s*", rule
                )
                if match:
                    hosts.append(match.group(1).strip())
                elif re.match(r"^\s*WebFetch\s*\(", rule):
                    # An unparsed WebFetch rule may still carry a domain; fail closed.
                    hosts.append("<unparsed-webfetch-rule>")
    return hosts


def sandbox_expansion_rules() -> List[Tuple[str, str]]:
    """Collect settings rules that can widen the sandbox Bash allowlist.

    Host values are returned only for comparison; callers report source labels
    and counts, never the hostnames from settings.local.json.
    """
    rules: List[Tuple[str, str]] = []
    for label, data in settings_documents():
        for host in settings_expansion_hosts(data):
            rules.append((label, host))
    return rules


def normalize_allowlist_host(value: str) -> str:
    return value.strip().lower().rstrip(".")


def uncovered_sandbox_expansions(
    declared_domains: Sequence[str],
    expansion_rules: Sequence[Tuple[str, str]],
) -> List[str]:
    """Return source labels for rules not literally declared in network_domains.

    Matching is intentionally exact (case-insensitive, trailing dot ignored);
    a broader wildcard is not treated as covering a narrower declared host.
    """
    declared = {
        normalize_allowlist_host(domain)
        for domain in declared_domains
        if isinstance(domain, str) and domain.strip()
    }
    return [
        label for label, host in expansion_rules
        if normalize_allowlist_host(host) not in declared
    ]


def claude_version(executable: str) -> Tuple[int, int, int]:
    """Read the local CLI version without starting a model call."""
    try:
        result = subprocess.run(
            [executable, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(
            "无法执行claude --version；本地Bash沙箱要求strictAllowlist（2.1.219+），未启动"
        ) from exc
    text = (result.stdout + result.stderr).decode("utf-8", "replace")
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if result.returncode != 0 or not match:
        raise ValueError(
            "无法确认Claude Code版本；本地Bash沙箱要求strictAllowlist（2.1.219+），未启动"
        )
    return tuple(int(part) for part in match.groups())


def selected_tools(policy: Dict[str, Any], skill_names: Sequence[str]) -> List[str]:
    tools = ["Read", "Edit", "Write", "Glob", "Grep"]
    if policy["checks_to_run"] or policy["training_allowed"] or policy["remote_execution_allowed"]:
        tools.append("Bash")
    if skill_names:
        tools.append("Skill")
    if policy["network_access_allowed"]:
        tools.extend(["WebSearch", "WebFetch"])
    return tools


def build_session_settings(
    policy: Dict[str, Any],
    available_tools: Sequence[str],
    plugin_overrides: Dict[str, bool],
    skill_names: Sequence[str],
    expansion_rules: Sequence[Tuple[str, str]],
    version: Optional[Tuple[int, int, int]],
) -> Dict[str, Any]:
    """Build the per-session settings overlay without launching Claude Code."""
    domains = (
        [domain for domain in policy.get("network_domains", []) if isinstance(domain, str)]
        if policy["network_access_allowed"]
        else []
    )
    ask_rules: List[str] = []
    deny_rules: List[str] = ["mcp__*"]
    allow_rules: List[str] = []

    if policy["remote_execution_allowed"]:
        ask_rules.append("Bash")
    elif "Bash" in available_tools:
        deny_rules.extend(["Bash(ssh *)", "Bash(rsync *)", "Bash(scp *)"])
    if policy["git_mutations_allowed"]:
        ask_rules.append("Bash(git *)")
    else:
        deny_rules.append("Bash(git *)")
    if policy["network_access_allowed"]:
        ask_rules.extend(["WebSearch", "WebFetch"])
    if skill_names:
        # Claude Code evaluates deny -> ask -> allow, and a matching ask rule
        # takes precedence over any specific allow rule. This generic ask rule
        # therefore requires confirmation for every Skill invocation, including
        # the skills declared in the blueprint. There is no "deny every skill
        # except this list" rule for unknown names, so unlisted skills are not
        # hard-denied by name; the user may still approve them.
        ask_rules.append("Skill")

    session_settings: Dict[str, Any] = {
        "enabledPlugins": plugin_overrides,
        "permissions": {"allow": allow_rules, "ask": ask_rules, "deny": deny_rules},
    }

    if "Bash" in available_tools and not policy["remote_execution_allowed"]:
        if version is None or version < STRICT_ALLOWLIST_MIN_VERSION:
            minimum = ".".join(str(part) for part in STRICT_ALLOWLIST_MIN_VERSION)
            current = "未知" if version is None else ".".join(str(part) for part in version)
            raise ValueError(
                "本地Bash沙箱要求Claude Code {}及以上以支持sandbox.network.strictAllowlist；"
                "当前版本{}，未启动".format(minimum, current)
            )
        uncovered = uncovered_sandbox_expansions(domains, expansion_rules)
        if uncovered:
            labels = "、".join(sorted(set(uncovered)))
            raise ValueError(
                "检测到{}条可能扩大Bash沙箱白名单的设置规则（来源：{}）；"
                "为避免未声明的Bash网络主机进入strictAllowlist白名单，未启动".format(
                    len(uncovered), labels
                )
            )
        network_policy: Dict[str, Any] = {
            "allowedDomains": domains,
            "strictAllowlist": True,
        }
        if not policy["network_access_allowed"]:
            # Keep the deny-all policy in addition to the empty allowlist.
            network_policy["deniedDomains"] = ["*"]
        session_settings["sandbox"] = {
            "enabled": True,
            "failIfUnavailable": True,
            "allowUnsandboxedCommands": False,
            "autoAllowBashIfSandboxed": False,
            "network": network_policy,
        }
    return session_settings


def build_launch_command(
    executable: str,
    model: Optional[str],
    prompt: str,
    available_tools: Sequence[str],
    session_settings: Dict[str, Any],
) -> List[str]:
    command = [executable]
    if model:
        command.extend(["--model", model])
    command.extend(["--tools", ",".join(available_tools)])
    command.extend(["--permission-mode", "manual", "--settings", json.dumps(session_settings)])
    command.append("--strict-mcp-config")
    # Variadic --disallowedTools would consume a trailing positional prompt.
    command.append(prompt)
    deny_rules = session_settings["permissions"]["deny"]
    if deny_rules:
        command.extend(["--disallowedTools", ",".join(deny_rules)])
    return command


def _self_check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def self_check_launch_config() -> int:
    """Exercise launch-config construction without a model call or network."""
    base_policy: Dict[str, Any] = {
        "training_allowed": False,
        "remote_execution_allowed": False,
        "network_access_allowed": False,
        "git_mutations_allowed": False,
        "checks_to_run": ["true"],
        "network_domains": [],
    }
    failures: List[str] = []

    def check(name: str, func: Any) -> None:
        try:
            func()
            print("PASS {}".format(name))
        except Exception as exc:
            failures.append(name)
            print("FAIL {}: {}".format(name, exc))

    def local_no_network() -> None:
        policy = dict(base_policy)
        tools = selected_tools(policy, [])
        settings = build_session_settings(policy, tools, {}, [], [], (2, 1, 302))
        network = settings["sandbox"]["network"]
        _self_check(network["allowedDomains"] == [], "allowedDomains应为空")
        _self_check(network["deniedDomains"] == ["*"], "应保留deny-all")
        _self_check(network["strictAllowlist"] is True, "strictAllowlist应为true")

    def local_whitelist_network() -> None:
        policy = dict(base_policy)
        policy["network_access_allowed"] = True
        policy["network_domains"] = ["api.example.com"]
        tools = selected_tools(policy, [])
        settings = build_session_settings(policy, tools, {}, [], [], (2, 1, 302))
        network = settings["sandbox"]["network"]
        _self_check(network["allowedDomains"] == ["api.example.com"], "白名单应只含声明主机")
        _self_check("deniedDomains" not in network, "联网任务不应有deny-all")
        _self_check(network["strictAllowlist"] is True, "strictAllowlist应为true")

    def webfetch_rule_discovered() -> None:
        hosts = settings_expansion_hosts({
            "sandbox": {"network": {"allowedDomains": ["api.example.com"]}},
            "permissions": {"allow": ["WebFetch(domain:other.example.com)"]},
        })
        _self_check("api.example.com" in hosts, "应发现sandbox allowedDomains")
        _self_check("other.example.com" in hosts, "应发现WebFetch domain规则")
        policy = dict(base_policy)
        policy["network_access_allowed"] = True
        policy["network_domains"] = ["api.example.com"]
        tools = selected_tools(policy, [])
        try:
            build_session_settings(
                policy, tools, {}, [], [("测试设置", host) for host in hosts], (2, 1, 302)
            )
        except ValueError:
            return
        raise AssertionError("发现未声明WebFetch规则后应fail closed")

    def webfetch_expansion_rejected() -> None:
        policy = dict(base_policy)
        policy["network_access_allowed"] = True
        policy["network_domains"] = ["api.example.com"]
        tools = selected_tools(policy, [])
        try:
            build_session_settings(
                policy, tools, {}, [], [("项目本地设置", "other.example.com")], (2, 1, 302)
            )
        except ValueError:
            return
        raise AssertionError("未声明的WebFetch规则应fail closed")

    def webfetch_declared_allowed() -> None:
        policy = dict(base_policy)
        policy["network_access_allowed"] = True
        policy["network_domains"] = ["api.example.com"]
        tools = selected_tools(policy, [])
        settings = build_session_settings(
            policy, tools, {}, [], [("用户设置", "api.example.com")], (2, 1, 302)
        )
        _self_check(settings["sandbox"]["network"]["allowedDomains"] == ["api.example.com"], "声明主机应通过")

    def remote_task() -> None:
        policy = dict(base_policy)
        policy["remote_execution_allowed"] = True
        policy["network_access_allowed"] = True
        policy["network_domains"] = ["remote.example.com"]
        tools = selected_tools(policy, [])
        settings = build_session_settings(policy, tools, {}, [], [], None)
        _self_check("sandbox" not in settings, "远程任务不应有本地sandbox")
        _self_check("Bash" in settings["permissions"]["ask"], "远程Bash应要求确认")

    def skills_declared_requires_confirmation() -> None:
        policy = dict(base_policy)
        policy["checks_to_run"] = []
        skill_names = ["research-paper-writing"]
        tools = selected_tools(policy, skill_names)
        settings = build_session_settings(policy, tools, {}, skill_names, [], None)
        _self_check("Skill" in tools, "指定skill时应开放Skill工具")
        _self_check("Skill" in settings["permissions"]["ask"], "所有Skill调用应要求人工确认")
        _self_check(
            not any(rule.startswith("Skill(") for rule in settings["permissions"]["allow"]),
            "不应添加无实际作用的Skill(name) allow规则",
        )
        _self_check("Skill" not in settings["permissions"]["deny"], "不应禁用全部skill")

    def skills_unspecified_not_exposed() -> None:
        policy = dict(base_policy)
        policy["checks_to_run"] = []
        tools = selected_tools(policy, [])
        settings = build_session_settings(policy, tools, {}, [], [], None)
        _self_check("Skill" not in tools, "未指定skill时不应开放Skill工具")
        _self_check(
            not any(rule.startswith("Skill(") for rule in settings["permissions"]["allow"]),
            "未指定skill时不应有Skill规则",
        )
        _self_check("Skill" not in settings["permissions"]["ask"], "未指定skill时不应有Skill门槛")

    def old_version_rejected() -> None:
        policy = dict(base_policy)
        tools = selected_tools(policy, [])
        try:
            build_session_settings(policy, tools, {}, [], [], (2, 1, 218))
        except ValueError:
            return
        raise AssertionError("2.1.219以下版本应fail closed")

    def min_version_accepted() -> None:
        policy = dict(base_policy)
        tools = selected_tools(policy, [])
        settings = build_session_settings(policy, tools, {}, [], [], (2, 1, 219))
        _self_check(settings["sandbox"]["network"]["strictAllowlist"] is True, "2.1.219应支持strictAllowlist")

    def launch_command_shape() -> None:
        policy = dict(base_policy)
        policy["checks_to_run"] = []
        tools = selected_tools(policy, [])
        settings = build_session_settings(policy, tools, {}, [], [], None)
        command = build_launch_command("claude", None, "prompt", tools, settings)
        _self_check("--permission-mode" in command and "manual" in command, "应使用manual权限模式")
        _self_check("--strict-mcp-config" in command, "应隔离MCP")
        _self_check("--settings" in command, "应传递会话设置overlay")
        _self_check(command.count("prompt") == 1, "任务提示必须作为独立参数传入且仅传一次")
        _self_check(command.index("prompt") < command.index("--disallowedTools"), "提示必须位于可变长工具选项之前")

    def report_self_path() -> None:
        own_report = "docs/thesis/blueprints/tasks/SMOKE/execution-report.json"
        output = "tmp/smoke/output.txt"
        report = dict(task_id="SMOKE", summary="synthetic", changed_paths=[output, own_report],
                      evidence_used=[], claim_or_number_changes=[], checks=[], unresolved=[], blockers=[])
        _self_check(not report_errors(report, "SMOKE", [output], own_report), "报告自列路径不应被误判")
        report["changed_paths"] = [own_report]
        _self_check(bool(report_errors(report, "SMOKE", [output], own_report)), "真实改动漏报仍须拒绝")
        report["changed_paths"] = [output, own_report, "docs/thesis/blueprints/tasks/OTHER/execution-report.json"]
        _self_check(bool(report_errors(report, "SMOKE", [output], own_report)), "不得豁免其他任务文件")

    for name, func in (
        ("local_no_network", local_no_network),
        ("local_whitelist_network", local_whitelist_network),
        ("webfetch_rule_discovered", webfetch_rule_discovered),
        ("webfetch_expansion_rejected", webfetch_expansion_rejected),
        ("webfetch_declared_allowed", webfetch_declared_allowed),
        ("remote_task", remote_task),
        ("skills_declared_requires_confirmation", skills_declared_requires_confirmation),
        ("skills_unspecified_not_exposed", skills_unspecified_not_exposed),
        ("old_version_rejected", old_version_rejected),
        ("min_version_accepted", min_version_accepted),
        ("launch_command_shape", launch_command_shape),
        ("report_self_path", report_self_path),
    ):
        check(name, func)
    if failures:
        print("启动配置自检失败: {}".format(", ".join(failures)), file=sys.stderr)
        return 2
    print("启动配置自检通过（仅检查配置形状，不验证运行时权限引擎；未启动模型、未访问网络）")
    return 0


def cmd_self_check(args: argparse.Namespace) -> int:
    return self_check_launch_config()


def launch_claude(directory: Path, model: Optional[str], on_started: Optional[Any] = None) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("Claude Code交互执行需要终端。请在本机Terminal运行本命令；无需手工复制蓝图。")
    executable = shutil.which("claude")
    if not executable:
        raise ValueError("没有找到claude命令。请先安装或配置Claude Code，再运行execute。")
    packet = relpath(directory / "EXECUTION_PACKET.md")
    prompt = (
        "请先读取项目中的 {} 并严格按任务包执行。完成后填写同目录的 execution-report.json；"
        "保持Claude Code正常权限确认，不要绕过权限。".format(packet)
    )
    blueprint = read_json(directory / "blueprint.json")
    policy = blueprint["execution_policy"]
    skill_names = blueprint.get("claude_skills", [])
    available_tools = selected_tools(policy, skill_names)
    plugin_overrides = {name: False for name in enabled_plugin_names()}
    use_local_sandbox = "Bash" in available_tools and not policy["remote_execution_allowed"]
    version = claude_version(executable) if use_local_sandbox else None
    expansion_rules = sandbox_expansion_rules() if use_local_sandbox else []
    session_settings = build_session_settings(
        policy, available_tools, plugin_overrides, skill_names, expansion_rules, version
    )
    statusline = ROOT / "scripts" / "thesis_blueprint_statusline.py"
    statusline_command = " ".join(
        shlex.quote(part) for part in (sys.executable, str(statusline), "--task", directory.name)
    )
    # This is an overlay for this task's Claude process only; user-level Claude
    # settings and the user's configured provider are left untouched.
    session_settings["statusLine"] = {"type": "command", "command": statusline_command}
    command = build_launch_command(executable, model, prompt, available_tools, session_settings)
    process = subprocess.Popen(command, cwd=str(ROOT))
    if on_started is not None:
        on_started(process.pid)
    return process.wait()


def cmd_execute(args: argparse.Namespace) -> int:
    directory = task_dir(args.task)
    bp, state, baseline = read_task_files(directory)
    if not baseline or state.get("status") != "ready":
        raise ValueError("任务必须先prepare，且当前状态应为ready")
    if state.get("baseline_sha256") != sha256_file(directory / "baseline.json"):
        raise ValueError("冻结基线完整性校验失败；未启动Claude Code")
    verify_unchanged_since_prepare(directory, baseline)
    state_write(directory, "executing", execution_started_at=now())
    try:
        code = launch_claude(
            directory,
            args.model,
            on_started=lambda pid: state_write(directory, "executing", claude_pid=pid),
        )
    except Exception:
        state_write(directory, "execution_not_started", execution_error="Claude Code未启动或启动前检查失败")
        raise
    state_write(directory, "returned" if code == 0 else "execution_interrupted", claude_exit_code=code, execution_finished_at=now())
    print("Claude Code退出码: {}".format(code))
    collect_args = argparse.Namespace(task=args.task)
    collect_code = cmd_collect(collect_args)
    return code if code else collect_code


def cmd_run(args: argparse.Namespace) -> int:
    prepare_code = cmd_prepare(argparse.Namespace(task=args.task, refresh=False))
    if prepare_code:
        return prepare_code
    return cmd_execute(argparse.Namespace(task=args.task, model=args.model))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="论文修订蓝图与Claude Code任务包接口")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new = subparsers.add_parser("new", help="从模板建立蓝图目录")
    new.add_argument("--id", required=True)
    new.add_argument("--title", default="")
    new.add_argument("--type", choices=sorted(TASK_TYPES), default="content_revision")
    new.add_argument("--stage", default="")
    new.add_argument("--objective", default="")
    new.add_argument("--allow", action="append", default=[], help="可写相对路径；可重复")
    new.add_argument("--context", action="append", default=[], help="console来源 path 或 path#标题 / path#L起始-L结束")
    new.add_argument("--evidence", action="append", default=[], help="直接证据来源 path 或 path#标题 / path#L起始-L结束")
    new.set_defaults(func=cmd_new)

    validate = subparsers.add_parser("validate", help="校验蓝图和来源定位")
    validate.add_argument("task")
    validate.set_defaults(func=cmd_validate)

    prepare = subparsers.add_parser("prepare", help="冻结任务证据并生成精简执行包")
    prepare.add_argument("task")
    prepare.add_argument("--refresh", action="store_true", help="仅用于尚未执行的任务，重建准备包")
    prepare.set_defaults(func=cmd_prepare)

    execute = subparsers.add_parser("execute", help="在交互终端启动Claude Code")
    execute.add_argument("task")
    execute.add_argument("--model", default=None, help="可选Claude Code模型别名；默认沿用本机配置")
    execute.set_defaults(func=cmd_execute)

    collect = subparsers.add_parser("collect", help="回收报告并计算相对任务基线的实际差异")
    collect.add_argument("task")
    collect.set_defaults(func=cmd_collect)

    run = subparsers.add_parser("run", help="prepare、启动Claude Code并自动collect")
    run.add_argument("task")
    run.add_argument("--model", default=None, help="可选Claude Code模型别名；默认沿用本机配置")
    run.set_defaults(func=cmd_run)

    self_check = subparsers.add_parser("self-check", help="不启动模型/网络，检查启动配置构造")
    self_check.set_defaults(func=cmd_self_check)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print("错误: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
