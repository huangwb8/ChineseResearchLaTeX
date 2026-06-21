#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from common import allocate_unique_run_id, ensure_dir, generate_run_id, is_within, load_config, resolve_path, skill_root


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
        "workspace_inside_project_root": is_within(project_root, workspace_base),
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
    default_hidden_dir = str(config["workspace"]["hidden_dir"])
    workspace_base = (
        resolve_path(args.workspace_base, base=project_root)
        if args.workspace_base
        else (project_root / default_hidden_dir).resolve()
    )
    run_id = args.run_id or allocate_unique_run_id(workspace_base, generate_run_id(config))
    workspace_root = ensure_dir(workspace_base / run_id)

    for subdir in config["workspace"]["subdirs"]:
        ensure_dir(workspace_root / str(subdir))

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
