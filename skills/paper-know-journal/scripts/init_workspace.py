#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import copy
import json
import re
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - dependency fallback
    yaml = None


DEFAULT_CONFIG = {
        "workspace": {
        "task_root_dir": ".bensz-api",
        "task_prefix": "task",
        "task_label": "paper-know-journal",
        "workspace_contract": "bensz-api-task-v1",
        "run_prefix": "",
        "timestamp_format": "%Y%m%d-%H%M",
        "subdirs": [
            "input",
            "output",
            "log",
            "official",
            "community",
            "article-samples",
            "notes",
            "drafts",
            "logs",
            "_runtime",
        ],
    },
    "output": {
        "filename_template": "KnowJournal-{journal}.md",
        "unsafe_filename_chars": '/\\:*?"<>|',
    },
    "tests": {"default_dir": ".bensz-api/skills/paper-know-journal/tests"},
}


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    config_path = skill_root() / "config.yaml"
    if yaml is None or not config_path.exists():
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


def safe_filename(value: str, *, unsafe_chars: str) -> str:
    cleaned = "".join("-" if ch in set(unsafe_chars) else ch for ch in value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip(" .-")
    if not cleaned:
        raise SystemExit("journal 不能只包含空白或路径危险字符")
    return cleaned


def timestamp(fmt: str) -> str:
    return dt.datetime.now().strftime(fmt)


def resolve_dir(path: str | None, *, default: Path) -> Path:
    if path is None:
        return default.resolve()
    return Path(path).expanduser().resolve()


def ensure_within(base: Path, child: Path, label: str) -> None:
    try:
        child.relative_to(base)
    except ValueError as exc:
        raise SystemExit(f"{label} 必须位于当前工作目录或用户显式指定目录内: {child}") from exc


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
    skill_name = str(config.get("task_label", "paper-know-journal")).strip("-")
    task_root = task_base / f"{task_prefix}-{run_id}-{skill_name}"
    return task_root, task_root / skill_name


def write_task_readme(task_root: Path, skill_name: str) -> None:
    task_root.mkdir(parents=True, exist_ok=True)
    readme = task_root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# BenszAPI 任务工作区\n\n"
            f"- 本轮 skill：`{skill_name}`\n"
            "- 中间文件位于本任务的 `input/`、`output/` 和 `log/` 分类目录。\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化 paper-know-journal 隐藏工作区")
    parser.add_argument("--journal", required=True, help="期刊/杂志名")
    parser.add_argument("--cwd", default=".", help="用户当前工作目录，默认当前目录")
    parser.add_argument("--workspace-dir", help="显式兼容工作区根目录；默认使用任务级 BenszAPI 工作区")
    parser.add_argument("--output-dir", help="最终 Markdown 输出目录，默认 <cwd>")
    parser.add_argument("--test-dir", help="可选测试目录；普通运行不创建测试目录")
    parser.add_argument("--run-id", help="运行 ID，默认 YYYYMMDD-HHMM")
    args = parser.parse_args()
    config = load_config()
    workspace_config = config["workspace"]
    output_config = config["output"]
    tests_config = config["tests"]

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.exists() or not cwd.is_dir():
        raise SystemExit(f"cwd 不存在或不是目录: {cwd}")

    journal_slug = safe_filename(
        args.journal,
        unsafe_chars=output_config["unsafe_filename_chars"],
    )
    run_prefix = workspace_config["run_prefix"]
    default_run_id = f"{run_prefix}{timestamp(workspace_config['timestamp_format'])}"
    if args.workspace_dir:
        workspace_base = resolve_dir(args.workspace_dir, default=cwd)
        run_id = args.run_id or allocate_unique_run_id(workspace_base, default_run_id)
        workspace_dir = workspace_base / run_id
    else:
        requested_run_id = args.run_id or default_run_id
        task_root, workspace_dir = default_task_workspace(cwd, workspace_config, requested_run_id)
        if args.run_id:
            run_id = requested_run_id
        else:
            task_root = task_root.parent / allocate_unique_run_id(task_root.parent, task_root.name)
            workspace_dir = task_root / str(workspace_config["task_label"])
            run_id = task_root.name.removeprefix("task-").removesuffix(f"-{workspace_config['task_label']}")
        workspace_base = task_root
        write_task_readme(task_root, str(workspace_config["task_label"]))
    run_id_pattern = rf"{re.escape(run_prefix)}[A-Za-z0-9_.-]+"
    if not re.fullmatch(run_id_pattern, run_id):
        raise SystemExit(f"run-id 只能使用 {run_prefix}- 前缀及字母、数字、下划线、点和连字符")

    output_dir = resolve_dir(args.output_dir, default=cwd)
    test_dir = resolve_dir(args.test_dir, default=cwd / tests_config["default_dir"]) if args.test_dir else None
    output_filename = output_config["filename_template"].format(journal=journal_slug)
    output_path = output_dir / output_filename

    if args.workspace_dir is None:
        ensure_within(cwd, workspace_dir, "workspace_dir")
    if args.output_dir is None:
        ensure_within(cwd, output_path, "output_path")
    if test_dir is not None and args.test_dir is None:
        ensure_within(cwd, test_dir, "test_dir")

    for subdir in workspace_config["subdirs"]:
        (workspace_dir / subdir).mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    if test_dir is not None:
        test_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "skill": "paper-know-journal",
        "journal": args.journal,
        "journal_slug": journal_slug,
        "run_id": run_id,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "cwd": str(cwd),
        "workspace_dir": str(workspace_dir),
        "output_path": str(output_path),
        "output_exists": output_path.exists(),
        "test_dir": str(test_dir) if test_dir is not None else "",
        "intermediate_policy": "All intermediate files must stay inside workspace_dir.",
    }
    manifest_path = workspace_dir / "manifest.json"
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    manifest_path.write_text(manifest_json, encoding="utf-8")
    sources_path = workspace_dir / "sources.json"
    sources = {
        "official": [],
        "community": [],
        "article_samples": [],
        "schema": {
            "title": "页面或文章标题",
            "url": "来源链接",
            "source_type": "official/community/article_sample",
            "accessed_at": "YYYY-MM-DD",
            "key_facts": ["从该来源确认的事实"],
        },
    }
    sources_path.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.workspace_dir:
        (workspace_base / "latest-run.txt").write_text(run_id + "\n", encoding="utf-8")

    print(f"workspace_dir={workspace_dir}")
    print(f"output_path={output_path}")
    if test_dir is not None:
        print(f"test_dir={test_dir}")
    print(f"manifest_path={manifest_path}")
    print(f"sources_path={sources_path}")
    if output_path.exists():
        print("warning=output_path already exists; confirm before overwriting")


if __name__ == "__main__":
    main()
