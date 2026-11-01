"""正文集合的检查、备份和恢复；不承担科学判断或通用工作流运行时。"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

try:
    import yaml
except ImportError as exc:
    raise SystemExit("需要 Python 3.11+ 和 PyYAML：python3.11 -m pip install PyYAML") from exc

SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "nsfc-research-content-writer"
ROLES = ("research_content_tex", "innovation_tex", "yearly_plan_tex")


class RevisionError(ValueError):
    pass


def load_config() -> dict:
    try:
        config = yaml.safe_load((SKILL_ROOT / "config.yaml").read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RevisionError("config.yaml 无法解析") from exc
    if not isinstance(config, dict):
        raise RevisionError("config.yaml 必须是映射")
    targets = config.get("targets", {})
    guard = config.get("guardrails", {})
    if set(targets) != set(ROLES) or len(set(targets.values())) != len(ROLES):
        raise RevisionError("targets 必须将三个角色绑定至不同文件")
    if set(guard.get("allowed_write_files", [])) != set(targets.values()):
        raise RevisionError("写入白名单必须与三个角色完全一致")
    for rel in targets.values():
        validate_relative(rel)
        if forbidden(rel, config):
            raise RevisionError("targets 包含禁写文件")
    return config


def validate_relative(value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RevisionError("路径必须为非空正斜杠相对路径")
    rel = Path(value)
    if rel.is_absolute() or any(part in ("..", ".") for part in value.split("/")):
        raise RevisionError("拒绝绝对路径或路径穿越")
    return rel


def forbidden(rel: str, config: dict) -> bool:
    guard = config["guardrails"]
    return (rel in {"main.tex", "extraTex/@config.tex", *guard.get("forbidden_write_files", [])}
            or Path(rel).suffix.lower() in (".cls", ".sty")
            or any(Path(rel).match(p) for p in guard.get("forbidden_write_globs", [])))


def no_symlinks(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise RevisionError("拒绝符号链接路径")


def under(root: Path, value: str | Path, *, must_exist: bool = True) -> Path:
    path = Path(value)
    path = path if path.is_absolute() else root / path
    if ".." in path.parts:
        raise RevisionError("拒绝路径穿越")
    no_symlinks(path)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise RevisionError("文件越出授权目录") from exc
    if must_exist and not path.is_file():
        raise RevisionError("文件不存在或不是普通文件；请先准备模板或提案")
    return path


def task_path(value: str | Path) -> Path:
    task = Path(value).expanduser().absolute()
    no_symlinks(task)
    if not task.is_dir() or task.parent.name != ".bensz-api" or not task.name.startswith("task-"):
        raise RevisionError("必须指定已声明并创建的 .bensz-api/task-* 工作区")
    if SKILL_ROOT == task or SKILL_ROOT in task.parents:
        raise RevisionError("任务工作区不得位于 Skill 源码内")
    return task.resolve()


def project_path(value: str | Path) -> Path:
    root = Path(value).expanduser().absolute()
    no_symlinks(root)
    if not root.is_dir():
        raise RevisionError("project_root 不存在")
    return root.resolve()


def target_path(root: Path, role: str, config: dict) -> Path:
    if role not in ROLES:
        raise RevisionError("未知文件角色")
    rel = config["targets"][role]
    validate_relative(rel)
    if forbidden(rel, config) or rel not in config["guardrails"]["allowed_write_files"]:
        raise RevisionError("拒绝禁写或白名单外目标")
    return under(root, rel)


def uncomment(text: str) -> str:
    # 未转义的 % 开始注释；偶数个反斜杠后的 % 仍为注释。
    lines = []
    for line in text.splitlines():
        for i, char in enumerate(line):
            if char == "%" and (len(line[:i]) - len(line[:i].rstrip("\\"))) % 2 == 0:
                line = line[:i]
                break
        lines.append(line)
    return "\n".join(lines)


def group(text: str, start: int, opening: str, closing: str) -> tuple[str, int]:
    depth, i = 1, start + 1
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start:i + 1], i + 1
        i += 1
    raise RevisionError("LaTeX 结构命令括号不完整")


def structure(text: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """比较命令与平衡参数，不把标题同行的正文视为结构。"""
    text = uncomment(text)
    pattern = re.compile(r"\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph|"
                         r"begin|end|label|input|include|includegraphics|bibliography|addbibresource|"
                         r"documentclass|usepackage|newcommand|renewcommand|providecommand|def|"
                         r"newenvironment|renewenvironment)\b(\*?)")
    result = []
    for match in pattern.finditer(text):
        args, i = [], match.end()
        # LaTeX 允许不加花括号的宏名，不能把宏定义参数漏出结构比较。
        if match[1] in ("def", "newcommand", "renewcommand", "providecommand"):
            macro = re.match(r"\s*(\\[A-Za-z@]+)", text[i:])
            if macro:
                args.append(macro[1])
                i += macro.end()
                if match[1] == "def":
                    body = text.find("{", i)
                    if body == -1:
                        raise RevisionError("宏定义缺少正文")
                    args.append(text[i:body])
                    i = body
        while i < len(text):
            while i < len(text) and text[i].isspace():
                i += 1
            if i >= len(text) or text[i] not in "[{":
                break
            opening = text[i]
            item, i = group(text, i, opening, "]" if opening == "[" else "}")
            args.append(item)
            if opening == "{" and match[1] not in (
                "begin", "newcommand", "renewcommand", "providecommand", "def",
                "newenvironment", "renewenvironment",
            ):
                break
        result.append((match[1], match[2], tuple(args)))
    return result


def citations(text: str) -> set[str]:
    text = uncomment(text)
    keys = set()
    pattern = r"\\([Cc]ite\w*|[Pp]arencite\w*|[Tt]extcite\w*|[Aa]utocite\w*|[Ff]ootcite\w*|nocite)\*?\b"
    for match in re.finditer(pattern, text):
        i = match.end()
        while i < len(text):
            while i < len(text) and text[i].isspace():
                i += 1
            while i < len(text) and text[i] == "[":
                _, i = group(text, i, "[", "]")
                while i < len(text) and text[i].isspace():
                    i += 1
            if i >= len(text) or text[i] != "{":
                break
            raw, i = group(text, i, "{", "}")
            keys.update(k.strip() for k in raw[1:-1].split(",") if k.strip() and k.strip() != "*")
            if not match[1].lower().endswith("cites"):
                break
    return keys


def bibliography(root: Path, config: dict) -> set[str]:
    keys = set()
    for pattern in config["checks"]["bibliography_globs"]:
        validate_relative(pattern)
        for candidate in root.glob(pattern):
            path = under(root, candidate)
            text = path.read_text(encoding="utf-8")
            keys.update(re.findall(r"(?i)@(?!(?:comment|string|preamble)\b)\w+\s*\{\s*([^,\s]+)\s*,", text))
    return keys


def content_report(text: str, known: set[str], config: dict, *, content: bool = True,
                   risk: bool = True, fail_risk: bool = False) -> dict:
    clean = uncomment(text)
    errors = []
    if content and not re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?|[{}\s]", "", clean):
        errors.append("正文为空或仅含注释")
    missing = sorted(citations(text) - known) if content else []
    if missing:
        errors.append("缺失 bibkey：" + ", ".join(missing))
    phrases = [p for p in config["checks"].get("risk_phrases", []) if p in clean] if risk else []
    if fail_risk and phrases:
        errors.append("按显式词表策略拒绝：" + "、".join(phrases))
    prose = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", "", clean)
    return {"errors": errors, "risk_phrases": phrases,
            "text_units": len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", prose)),
            "page_status": "尚未核验实际页数", "semantic_status": "需 AI 复核研究设计、创新与年度关联"}


def fingerprint(path: Path) -> tuple:
    st = path.stat()
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, stat.S_IMODE(st.st_mode))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def project_key(root: Path) -> str:
    return digest(os.fsencode(root))


def make_diff(rel: str, before: bytes, after: bytes) -> str:
    return "".join(difflib.unified_diff(before.decode("utf-8").splitlines(keepends=True),
                                      after.decode("utf-8").splitlines(keepends=True),
                                      fromfile="a/" + rel, tofile="b/" + rel))


def prepare(root: Path, task: Path, manifest: Path, roles: list[str], config: dict,
            *, allow_structure: bool = False) -> tuple[list[dict], dict]:
    if len(set(roles)) != len(roles) or not roles:
        raise RevisionError("须显式指定本次授权角色，且不能重复")
    data = json.loads(under(task, manifest).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"proposals"} or not isinstance(data["proposals"], dict):
        raise RevisionError("提案须为仅含 proposals 映射的 JSON")
    if set(data["proposals"]) != set(roles):
        raise RevisionError("提案角色必须与本次授权集合完全一致")
    known, entries, reports = bibliography(root, config), [], {}
    for role in roles:
        path = target_path(root, role, config)
        before_stat = fingerprint(path)
        before = path.read_bytes()
        after = under(task, data["proposals"][role]).read_bytes()
        old, new = before.decode("utf-8"), after.decode("utf-8")
        report = content_report(new, known, config)
        if not allow_structure and structure(old) != structure(new):
            report["errors"].append("标题、层级、标签、环境或资源命令改变；需要明确结构修改授权")
        if report["errors"]:
            raise RevisionError(role + "：" + "；".join(report["errors"]))
        reports[role] = report
        entries.append({"role": role, "path": path, "relative": config["targets"][role],
                        "before": before, "after": after, "stat": before_stat})
    return entries, reports


def unchanged(entry: dict, expected: bytes, *, check_stat: bool = False) -> None:
    path = entry["path"]
    no_symlinks(path)
    if not path.is_file() or path.read_bytes() != expected or (check_stat and fingerprint(path) != entry["stat"]):
        raise RevisionError("目标在检查后发生额外修改：" + entry["relative"])


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    no_symlinks(path)
    fd, name = tempfile.mkstemp(prefix=".nsfc-revision-", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        tmp.chmod(mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def save_record(directory: Path, record: dict) -> None:
    atomic_write(directory / "record.json", (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode(), 0o600)


def apply_entries(root: Path, task: Path, entries: list[dict]) -> dict:
    changes = [e for e in entries if e["before"] != e["after"]]
    if not changes:
        return {"status": "unchanged", "changed_roles": []}
    parent = under(task, f"{SKILL_NAME}/output", must_exist=False)
    parent.mkdir(parents=True, exist_ok=True)
    directory = parent / ("revision-" + uuid.uuid4().hex)
    directory.mkdir(mode=0o700)
    (directory / "before").mkdir()
    (directory / "after").mkdir()
    record = {"project_key": project_key(root), "status": "prepared", "files": []}
    # 所有备份和提案副本落盘后才允许开始替换；记录不保存宿主绝对路径。
    for e in changes:
        for kind in ("before", "after"):
            with (directory / kind / (e["role"] + ".tex")).open("xb") as stream:
                stream.write(e[kind])
                stream.flush()
                os.fsync(stream.fileno())
        record["files"].append({"role": e["role"], "target": e["relative"],
                                "before_sha256": digest(e["before"]), "after_sha256": digest(e["after"]),
                                "mode": e["stat"][-1]})
    save_record(directory, record)
    replaced = []
    try:
        for e in entries:
            unchanged(e, e["before"], check_stat=True)
        for e in changes:
            unchanged(e, e["before"], check_stat=True)
            atomic_write(e["path"], e["after"], e["stat"][-1])
            replaced.append(e)
        for e in entries:
            unchanged(e, e["after"])
        record["status"] = "applied"
        save_record(directory, record)
    except Exception as exc:
        conflicts = []
        for e in reversed(replaced):
            try:
                unchanged(e, e["after"])
                atomic_write(e["path"], e["before"], e["stat"][-1])
            except Exception:
                conflicts.append(e["relative"])
        record["status"] = "rollback_conflict" if conflicts else "failed_restored"
        record["recovery_conflicts"] = conflicts
        try:
            save_record(directory, record)
        except OSError:
            pass
        raise RevisionError("写入失败：" + str(exc) + "；" + ("部分恢复受阻：" + "、".join(conflicts) if conflicts else "已恢复本次已替换文件")
                            + "；备份：" + directory.relative_to(task).as_posix()) from exc
    return {"status": "applied", "changed_roles": [e["role"] for e in changes],
            "backup_dir": directory.relative_to(task).as_posix()}


def read_backup(root: Path, task: Path, value: str | Path, config: dict) -> tuple[Path, dict, list[dict]]:
    directory = under(task, value, must_exist=False)
    parent = task / SKILL_NAME / "output"
    if directory.parent != parent or not re.fullmatch(r"revision-[0-9a-f]{32}", directory.name):
        raise RevisionError("备份必须为本任务的 revision-* 目录")
    record = json.loads(under(directory, "record.json").read_text(encoding="utf-8"))
    if record.get("project_key") != project_key(root):
        raise RevisionError("备份不属于当前 project_root")
    files = record.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= len(ROLES):
        raise RevisionError("备份文件集合无效")
    entries, seen = [], set()
    for item in files:
        role = item["role"]
        if role in seen or role not in ROLES or item["target"] != config["targets"][role]:
            raise RevisionError("备份角色、目标或集合不匹配")
        seen.add(role)
        before = under(directory, f"before/{role}.tex").read_bytes()
        after = under(directory, f"after/{role}.tex").read_bytes()
        if digest(before) != item["before_sha256"] or digest(after) != item["after_sha256"]:
            raise RevisionError("备份或提案副本内容损坏")
        path = target_path(root, role, config)
        entries.append({"role": role, "relative": item["target"], "path": path,
                        "before": before, "after": after, "stat": fingerprint(path)})
    return directory, record, entries


def restore(root: Path, task: Path, value: str | Path, config: dict) -> dict:
    directory, record, entries = read_backup(root, task, value, config)
    # 宕机可能只替换了部分文件，允许逐文件为 before 或 after；第三种内容一律拒绝。
    reverse = []
    for e in entries:
        current = e["path"].read_bytes()
        if current not in (e["before"], e["after"]):
            raise RevisionError("恢复冲突，当前版本有额外修改：" + e["relative"])
        reverse.append({**e, "before": current, "after": e["before"]})
    # 同一写入器先保护当前版本，恢复失败也能回到恢复前版本。
    result = apply_entries(root, task, reverse)
    result["restored_from"] = directory.relative_to(task).as_posix()
    return result
