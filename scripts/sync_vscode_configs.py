#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"
TEMPLATES_DIR = Path(__file__).resolve().parent / "vscode"
WORKSPACE_TEMPLATE = TEMPLATES_DIR / "project.code-workspace.json"
SETTINGS_TEMPLATES = {
    "nsfc": TEMPLATES_DIR / "nsfc.settings.json",
    "paper": TEMPLATES_DIR / "paper.settings.json",
    "thesis": TEMPLATES_DIR / "thesis.settings.json",
    "cv": TEMPLATES_DIR / "cv.settings.json",
}
LATEX_WORKSHOP_LAUNCHER_TEMPLATE = TEMPLATES_DIR / "latex_workshop_build.lua"


def infer_project_profile(project_name: str) -> str | None:
    if project_name.startswith("NSFC_"):
        return "nsfc"
    if project_name.startswith("paper-"):
        return "paper"
    if project_name.startswith("thesis-"):
        return "thesis"
    if project_name.startswith("cv-"):
        return "cv"
    return None


def discover_projects() -> list[Path]:
    return sorted(path for path in PROJECTS_DIR.iterdir() if path.is_dir())


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8").rstrip() + "\n"


def ensure_text(path: Path, content: str, check_only: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return False
    if check_only:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def sync_project(project_dir: Path, *, check_only: bool) -> list[str]:
    profile = infer_project_profile(project_dir.name)
    if profile is None:
        return [f"SKIP {project_dir.relative_to(REPO_ROOT)} (unknown profile)"]

    workspace_content = load_template(WORKSPACE_TEMPLATE)
    settings_content = load_template(SETTINGS_TEMPLATES[profile])
    launcher_content = load_template(LATEX_WORKSHOP_LAUNCHER_TEMPLATE)

    targets = [
        (project_dir / f"{project_dir.name}.code-workspace", workspace_content),
        (project_dir / ".vscode" / "settings.json", settings_content),
        (project_dir / "scripts" / "latex_workshop_build.lua", launcher_content),
    ]

    messages: list[str] = []
    for target, content in targets:
        changed = ensure_text(target, content, check_only)
        relpath = target.relative_to(REPO_ROOT)
        if changed and check_only:
            messages.append(f"MISMATCH {relpath}")
        elif changed:
            messages.append(f"UPDATED {relpath}")
        else:
            messages.append(f"OK {relpath}")
    return messages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="同步 projects/ 下各项目的 VS Code 工作区与 .vscode/settings.json 固定配置。"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查是否与 scripts/vscode/ 模板一致；若存在漂移则返回非零退出码。",
    )
    parser.add_argument(
        "--project",
        action="append",
        default=[],
        help="仅同步指定项目目录名，可重复传入多次。",
    )
    return parser.parse_args()


def resolve_selected_projects(selected_names: list[str]) -> list[Path]:
    projects = {path.name: path for path in discover_projects()}
    if not selected_names:
        return list(projects.values())

    missing = [name for name in selected_names if name not in projects]
    if missing:
        raise FileNotFoundError(f"未找到项目目录：{', '.join(missing)}")
    return [projects[name] for name in selected_names]


def main() -> int:
    args = parse_args()
    try:
        selected_projects = resolve_selected_projects(args.project)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    has_mismatch = False
    for project_dir in selected_projects:
        for message in sync_project(project_dir, check_only=args.check):
            print(message)
            if message.startswith("MISMATCH "):
                has_mismatch = True

    if args.check and has_mismatch:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
