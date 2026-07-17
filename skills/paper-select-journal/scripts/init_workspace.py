#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from common import allocate_unique_run_id, ensure_dir, generate_run_id, is_within, load_config, resolve_path, skill_root, write_text


def default_task_workspace(project_root: Path, config: dict, run_id: str) -> tuple[Path, Path]:
    workspace_cfg = config["workspace"]
    task_base = project_root / workspace_cfg.get("task_root_dir", ".bensz-api")
    task_prefix = str(workspace_cfg.get("task_prefix", "task")).strip("-") or "task"
    skill_name = str(workspace_cfg.get("task_label", "paper-select-journal")).strip("-")
    task_root = task_base / f"{task_prefix}-{run_id}-{skill_name}"
    return task_root, task_root / skill_name


def write_task_readme(task_root: Path, skill_name: str) -> None:
    readme = task_root / "README.md"
    if not readme.exists():
        write_text(
            readme,
            "# BenszAPI 任务工作区\n\n"
            f"- 本轮 skill：`{skill_name}`\n"
            "- 中间文件位于本任务的 `input/`、`output/` 和 `log/` 分类目录。\n",
        )


def build_manifest(
    *,
    config: dict,
    project_root: Path,
    workspace_base: Path,
    workspace_root: Path,
    run_id: str,
) -> dict:
    reports_cfg = config["reports"]
    return {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "skill_root": str(skill_root()),
        "project_root": str(project_root),
        "workspace_base": str(workspace_base),
        "workspace_root": str(workspace_root),
        "run_id": run_id,
        "workspace_inside_project_root": is_within(project_root, workspace_root),
        "workspace_contract": config["workspace"].get("workspace_contract", "legacy-explicit-workspace"),
        "catalog_xlsx": str((skill_root() / config["assets"]["catalog_xlsx"]).resolve()),
        "final_report": str((workspace_root / reports_cfg["final_report"]).resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化 paper-select-journal 隐藏工作区")
    parser.add_argument("--project-root", default=".", help="用户当前项目根目录")
    parser.add_argument("--workspace-base", default="", help="自定义隐藏工作区根目录")
    parser.add_argument("--run-id", default="", help="显式指定 run 目录名")
    args = parser.parse_args()

    config = load_config()
    project_root = resolve_path(args.project_root)
    skill_name = str(config["workspace"].get("task_label", "paper-select-journal"))
    if args.workspace_base:
        workspace_base = resolve_path(args.workspace_base, base=project_root)
        run_id = args.run_id or allocate_unique_run_id(workspace_base, generate_run_id(config))
        workspace_root = ensure_dir(workspace_base / run_id)
    else:
        requested_run_id = args.run_id or generate_run_id(config)
        task_root, workspace_root = default_task_workspace(project_root, config, requested_run_id)
        if not args.run_id:
            task_root = ensure_dir(task_root.parent) / allocate_unique_run_id(task_root.parent, task_root.name)
            workspace_root = task_root / skill_name
            run_id = task_root.name.removeprefix("task-").removesuffix(f"-{skill_name}")
        else:
            run_id = requested_run_id
        workspace_base = task_root
        ensure_dir(workspace_root)
        write_task_readme(task_root, skill_name)

    for subdir in config["workspace"]["subdirs"]:
        ensure_dir(workspace_root / str(subdir))

    if args.workspace_base:
        latest_run = workspace_base / config["workspace"]["latest_run_pointer"]
        ensure_dir(workspace_base)
        latest_run.write_text(run_id + "\n", encoding="utf-8")

    manifest = build_manifest(
        config=config,
        project_root=project_root,
        workspace_base=workspace_base,
        workspace_root=workspace_root,
        run_id=run_id,
    )
    manifest_path = workspace_root / config["reports"]["run_manifest"]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"project_root={project_root}")
    print(f"workspace_base={workspace_base}")
    print(f"workspace_root={workspace_root}")
    print(f"run_id={run_id}")
    print(f"manifest={manifest_path}")
    if not manifest["workspace_inside_project_root"]:
        print("warning=workspace_base 位于 project_root 之外；只有用户明确指定时才应这样做")


if __name__ == "__main__":
    main()
