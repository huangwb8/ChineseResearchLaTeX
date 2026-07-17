#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


DEFAULT_CONFIG = {
    "workspace": {
        "task_root_dir": ".bensz-api",
        "task_prefix": "task",
        "task_label": "research-idea",
        "workspace_contract": "bensz-api-task-v1",
        "run_prefix": "",
        "timestamp_format": "%Y%m%d-%H%M",
        "subdirs": [
            "input",
            "output",
            "log",
            "theme",
            "candidates",
            "novelty",
            "parallel-vibe",
            "agent-reviews",
            "synthesis",
            "drafts",
            "logs",
        ],
    },
    "output": {
        "filename_template": "Research-Idea_{repo}_{pr}_{timestamp}.md",
        "timestamp_format": "%Y%m%d%H%M%S",
        "unsafe_filename_chars": '/\\:*?"<>|',
        "fallback_repo": "repo",
        "fallback_pr": "manual",
    },
    "dependencies": {
        "required_skills": [
            "research-topic-extractor",
            "research-literature-review",
            "parallel-vibe",
        ],
        "legacy_skill_aliases": {
            "research-topic-extractor": ["get-review-theme"],
            "research-literature-review": ["systematic-literature-review"],
        },
        "search_roots": [
            ".",
            "~/.codex/skills",
            "~/.claude/skills",
            "/Volumes/2T01/Cache/.codex/skills",
        ],
    },
    "tests": {"default_dir": ".bensz-api/skills/research-idea/tests"},
}


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    config_path = skill_root() / "config.yaml"
    if yaml is None and config_path.exists():
        raise SystemExit("缺少 PyYAML，无法读取 research-idea/config.yaml；请安装 pyyaml 后重试")
    if not config_path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = copy.deepcopy(DEFAULT_CONFIG)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            merged = config[key].copy()
            merged.update(value)
            config[key] = merged
        else:
            config[key] = value
    return config


def run_git(cwd: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def detect_repo_name(cwd: Path, fallback: str) -> str:
    remote = run_git(cwd, ["config", "--get", "remote.origin.url"])
    if remote:
        tail = remote.rstrip("/").rsplit("/", 1)[-1]
        if tail.endswith(".git"):
            tail = tail[:-4]
        if tail:
            return tail
    top = run_git(cwd, ["rev-parse", "--show-toplevel"])
    if top:
        return Path(top).name
    return cwd.name or fallback


def detect_pr_name(cwd: Path, fallback: str) -> str:
    branch = run_git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch and branch != "HEAD":
        return branch
    return fallback


def sanitize(value: str, *, unsafe_chars: str, fallback: str, max_len: int = 80) -> str:
    value = unicodedata.normalize("NFKC", value.strip() or fallback)
    cleaned = "".join(
        "-" if ch in set(unsafe_chars) or unicodedata.category(ch)[0] == "C" else ch
        for ch in value
    )
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip(" .-_")
    cleaned = (cleaned or fallback)[:max_len].strip(" .-_")
    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "LPT1"}
    if cleaned.upper() in reserved:
        cleaned = f"{cleaned}-file"
    return cleaned or fallback


def resolve_dir(path: str | None, *, default: Path) -> Path:
    if path is None:
        return default.resolve()
    return Path(path).expanduser().resolve()


def ensure_within(base: Path, child: Path, label: str) -> None:
    try:
        child.relative_to(base)
    except ValueError as exc:
        raise SystemExit(f"{label} 默认必须位于当前工作目录内: {child}") from exc


def ensure_hidden_workspace(path: Path, label: str) -> None:
    parts = path.parts
    if path.name.startswith(".") or ".bensz-api" in parts:
        return
    raise SystemExit(f"{label} 必须位于隐藏目录内，推荐 .bensz-api/skills/research-idea: {path}")


def ensure_not_nested(parent: Path, child: Path, label: str) -> None:
    try:
        child.relative_to(parent)
    except ValueError:
        return
    raise SystemExit(f"{label} 不得位于隐藏工作区内: {child}")


def allocate_unique_run_id(workspace_base: Path, run_id: str) -> str:
    if not (workspace_base / run_id).exists():
        return run_id
    for idx in range(2, 100):
        candidate = f"{run_id}-{idx:02d}"
        if not (workspace_base / candidate).exists():
            return candidate
    raise SystemExit(f"无法在 {workspace_base} 下分配唯一工作目录: {run_id}")


def default_task_workspace(cwd: Path, config: dict, run_id: str) -> tuple[Path, Path]:
    task_base = cwd / config.get("task_root_dir", ".bensz-api")
    task_prefix = str(config.get("task_prefix", "task")).strip("-") or "task"
    skill_name = str(config.get("task_label", "research-idea")).strip("-")
    task_root = task_base / f"{task_prefix}-{run_id}-{skill_name}"
    return task_root, task_root / skill_name


def write_task_readme(task_root: Path, skill_name: str) -> None:
    task_root.mkdir(parents=True, exist_ok=True)
    readme = task_root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# BenszAPI 任务工作区\n\n"
            f"- 本轮 skill：`{skill_name}`\n"
            "- 输入引用、临时结果和日志分别保存于该 skill 的 input/output/log。\n",
            encoding="utf-8",
        )


def find_skill(skill_name: str, search_roots: list[str], cwd: Path) -> Path | None:
    candidates: list[Path] = []
    for root in search_roots:
        root_path = (cwd if root == "." else Path(root).expanduser()).resolve()
        candidates.append(root_path / skill_name / "SKILL.md")
    for env_name in ("CODEX_HOME", "CLAUDE_HOME"):
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(Path(env_value).expanduser().resolve() / "skills" / skill_name / "SKILL.md")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def check_dependencies(config: dict, cwd: Path) -> dict[str, str]:
    dependency_config = config.get("dependencies", {})
    required = dependency_config.get("required_skills", [])
    aliases = dependency_config.get("legacy_skill_aliases", {}) or {}
    search_roots = dependency_config.get("search_roots", ["."])
    found: dict[str, str] = {}
    missing: list[str] = []
    for skill_name in required:
        candidates = [skill_name, *[str(item) for item in aliases.get(skill_name, [])]]
        path = None
        resolved_name = skill_name
        for candidate_name in candidates:
            path = find_skill(candidate_name, search_roots, cwd)
            if path is not None:
                resolved_name = candidate_name
                break
        if path is None:
            missing.append(skill_name)
        else:
            found[skill_name] = str(path.parent)
            if resolved_name != skill_name:
                found[f"{skill_name}__legacy_alias"] = resolved_name
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            "缺少 research-idea 必需依赖 skill: "
            f"{joined}。请先安装到当前仓库、~/.codex/skills 或 ~/.claude/skills。"
        )
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化 research-idea 隐藏工作区")
    parser.add_argument("--input-label", required=True, help="资料或主题的简短标签")
    parser.add_argument("--cwd", default=".", help="用户当前工作目录，默认当前目录")
    parser.add_argument("--workspace-dir", help="显式兼容工作区根目录；默认使用任务级 BenszAPI 工作区")
    parser.add_argument("--output-dir", help="最终 Markdown 输出目录，默认 <cwd>")
    parser.add_argument("--test-dir", help="测试区目录，默认 <cwd>/.bensz-api/skills/research-idea/tests")
    parser.add_argument("--with-test-dir", action="store_true", help="创建测试区；普通用户运行默认不创建")
    parser.add_argument("--repo-name", help="覆盖自动识别的 GitHub 仓库名")
    parser.add_argument("--pr-name", help="覆盖自动识别的 PR/分支名")
    parser.add_argument("--run-id", help="运行 ID，默认 YYYYMMDD-HHMM")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的最终报告路径")
    parser.add_argument("--skip-dependency-check", action="store_true", help="仅测试脚本时跳过依赖 skill 检查")
    args = parser.parse_args()

    config = load_config()
    workspace_config = config["workspace"]
    output_config = config["output"]
    tests_config = config["tests"]

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.exists() or not cwd.is_dir():
        raise SystemExit(f"cwd 不存在或不是目录: {cwd}")
    dependency_paths = {} if args.skip_dependency_check else check_dependencies(config, cwd)

    unsafe_chars = output_config["unsafe_filename_chars"]
    repo = sanitize(
        args.repo_name or detect_repo_name(cwd, output_config["fallback_repo"]),
        unsafe_chars=unsafe_chars,
        fallback=output_config["fallback_repo"],
    )
    pr = sanitize(
        args.pr_name or detect_pr_name(cwd, output_config["fallback_pr"]),
        unsafe_chars=unsafe_chars,
        fallback=output_config["fallback_pr"],
    )
    input_label = sanitize(args.input_label, unsafe_chars=unsafe_chars, fallback="input")
    run_timestamp = dt.datetime.now().strftime(workspace_config["timestamp_format"])
    output_timestamp = dt.datetime.now().strftime(output_config["timestamp_format"])
    run_prefix = workspace_config["run_prefix"]
    if args.workspace_dir:
        workspace_base = resolve_dir(args.workspace_dir, default=cwd)
        ensure_hidden_workspace(workspace_base, "workspace_dir")
        run_id = args.run_id or allocate_unique_run_id(workspace_base, f"{run_prefix}{run_timestamp}")
        workspace_dir = workspace_base / run_id
    else:
        requested_run_id = args.run_id or f"{run_prefix}{run_timestamp}"
        task_root, workspace_dir = default_task_workspace(cwd, workspace_config, requested_run_id)
        if args.run_id:
            run_id = requested_run_id
        else:
            task_root = task_root.parent / allocate_unique_run_id(task_root.parent, task_root.name)
            workspace_dir = task_root / str(workspace_config["task_label"])
            run_id = task_root.name.removeprefix("task-").removesuffix(f"-{workspace_config['task_label']}")
        workspace_base = task_root
        write_task_readme(task_root, str(workspace_config["task_label"]))
    if not re.fullmatch(rf"{re.escape(run_prefix)}[A-Za-z0-9_.-]+", run_id):
        raise SystemExit(f"run-id 必须只包含字母、数字、点、下划线和连字符")
    output_dir = resolve_dir(args.output_dir, default=cwd)
    test_dir = resolve_dir(args.test_dir, default=cwd / tests_config["default_dir"])
    output_filename = output_config["filename_template"].format(
        repo=repo,
        pr=pr,
        timestamp=output_timestamp,
    )
    output_path = output_dir / output_filename

    ensure_within(cwd, workspace_dir, "workspace_dir")
    if args.output_dir is None:
        ensure_within(cwd, output_path, "output_path")
    ensure_not_nested(workspace_base, output_path, "output_path")
    if workspace_dir.exists():
        raise SystemExit(f"run 工作区已存在，拒绝复用以避免串稿: {workspace_dir}")
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"输出文件已存在，拒绝覆盖；如确认覆盖请添加 --overwrite: {output_path}")

    for subdir in workspace_config["subdirs"]:
        (workspace_dir / subdir).mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.with_test_dir:
        ensure_within(cwd, test_dir, "test_dir")
        test_dir.mkdir(parents=True, exist_ok=True)
    workspace_base.mkdir(parents=True, exist_ok=True)

    manifest = {
        "skill": "research-idea",
        "input_label": input_label,
        "repo": repo,
        "pr": pr,
        "run_id": run_id,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "cwd": str(cwd),
        "workspace_dir": str(workspace_dir),
        "output_path": str(output_path),
        "output_exists": output_path.exists(),
        "test_dir": str(test_dir) if args.with_test_dir else "",
        "dependency_paths": dependency_paths,
        "intermediate_policy": "All intermediate files must stay inside workspace_dir.",
    }
    manifest_path = workspace_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.workspace_dir:
        (workspace_base / "latest-run.txt").write_text(run_id + "\n", encoding="utf-8")

    candidate_schema = {
        "candidates": [
            {
                "id": "C1",
                "question": "明确、关键、可研究的科学问题",
                "hypothesis": "可被数据、实验或观察推翻的科学假设",
                "predictions": ["假设成立时应观察到的结果"],
                "falsification": ["能推翻该假设的结果"],
                "novelty_status": "未研究 / 部分研究但关键缺口存在 / 已充分研究",
            }
        ]
    }
    (workspace_dir / "candidates" / "candidate-schema.json").write_text(
        json.dumps(candidate_schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"workspace_dir={workspace_dir}")
    print(f"output_path={output_path}")
    if args.with_test_dir:
        print(f"test_dir={test_dir}")
    print(f"manifest_path={manifest_path}")


if __name__ == "__main__":
    main()
