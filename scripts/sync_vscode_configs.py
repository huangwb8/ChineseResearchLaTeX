#!/usr/bin/env python3
"""VS Code 工作区与 LaTeX Workshop 配置同步工具。

将 ``scripts/vscode/`` 下按项目类型（nsfc / paper / thesis / cv）维护的固定配置模板
同步到 ``projects/`` 下各子项目中，确保所有项目具有一致的 VS Code 工程配置。

同步内容：
  - ``*.code-workspace`` ：VS Code 工作区定义文件
  - ``.vscode/settings.json`` ：LaTeX Workshop 等扩展配置
  - LaTeX Workshop launcher 脚本（通过 ``texlua`` 转调项目级 Python wrapper）

典型用法::

    python sync_vscode_configs.py                # 同步所有项目
    python sync_vscode_configs.py --project NSFC_General  # 仅同步指定项目
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 仓库根目录
REPO_ROOT = Path(__file__).resolve().parents[1]
# projects/ 目录
PROJECTS_DIR = REPO_ROOT / "projects"
# VS Code 配置模板目录（scripts/vscode/）
TEMPLATES_DIR = Path(__file__).resolve().parent / "vscode"
# 通用工作区模板
WORKSPACE_TEMPLATE = TEMPLATES_DIR / "project.code-workspace.json"
# 按项目类型分级的 .vscode/settings.json 模板
SETTINGS_TEMPLATES = {
    "nsfc": TEMPLATES_DIR / "nsfc.settings.json",
    "paper": TEMPLATES_DIR / "paper.settings.json",
    "thesis": TEMPLATES_DIR / "thesis.settings.json",
    "cv": TEMPLATES_DIR / "cv.settings.json",
}
# LaTeX Workshop 构建 launcher 模板（texlua 脚本，跨平台转调 Python wrapper）
LATEX_WORKSHOP_LAUNCHER_TEMPLATE = TEMPLATES_DIR / "latex_workshop_build.lua"


def infer_project_profile(project_name: str) -> str | None:
    """根据项目目录名前缀推断项目类型（nsfc / paper / thesis / cv）。

    无法识别的前缀返回 None，该类项目会被同步流程跳过。
    """
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
    """扫描 ``projects/`` 目录下的所有子目录并按名称排序。"""
    return sorted(path for path in PROJECTS_DIR.iterdir() if path.is_dir())


def load_template(path: Path) -> str:
    """加载模板文件内容，去除尾部空行后统一追加一个换行符。"""
    return path.read_text(encoding="utf-8").rstrip() + "\n"


def ensure_text(path: Path, content: str, check_only: bool) -> bool:
    """确保文件内容与预期一致。

    若文件已存在且内容相同则不做任何操作；若内容不同，check_only 模式下
    返回 True 表示有差异，非 check_only 模式下直接写入。

    Returns:
        True 表示文件内容有差异（已更新或检测到漂移），False 表示内容一致
    """
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return False
    if check_only:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def sync_project(project_dir: Path, *, check_only: bool) -> list[str]:
    """将模板配置同步到单个项目目录。

    同步的三个目标文件：
    1. ``<project>/<project>.code-workspace`` - 工作区定义
    2. ``<project>/.vscode/settings.json`` - LaTeX Workshop 配置
    3. ``<project>/scripts/latex_workshop_build.lua`` - 构建 launcher

    Args:
        project_dir: 项目目录路径
        check_only: 若为 True，只检测漂移不实际写入

    Returns:
        操作消息列表（SKIP / MISMATCH / UPDATED / OK）
    """
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
    """根据命令行参数解析要同步的项目目录列表。未指定时返回全部项目。"""
    projects = {path.name: path for path in discover_projects()}
    if not selected_names:
        return list(projects.values())

    missing = [name for name in selected_names if name not in projects]
    if missing:
        raise FileNotFoundError(f"未找到项目目录：{', '.join(missing)}")
    return [projects[name] for name in selected_names]


def main() -> int:
    """脚本主入口：解析参数 -> 选定项目 -> 逐个同步 -> 汇报结果。

    在 ``--check`` 模式下，如果任何项目存在配置漂移，返回退出码 1。

    Returns:
        0 表示成功（或无漂移），1 表示存在漂移或参数错误
    """
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
