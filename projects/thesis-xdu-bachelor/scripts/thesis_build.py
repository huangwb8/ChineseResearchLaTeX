#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def get_installed_package_root() -> Path | None:
    kpsewhich = subprocess.run(
        ["kpsewhich", "bensz-thesis.sty"],
        capture_output=True,
        text=True,
        check=False,
    )
    if kpsewhich.returncode != 0 or not kpsewhich.stdout.strip():
        return None
    return Path(kpsewhich.stdout.strip()).expanduser().resolve().parent


def iter_script_candidates() -> list[Path]:
    candidates = [
        PROJECT_DIR.parent.parent / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py",
    ]
    package_root = get_installed_package_root()
    if package_root is not None:
        candidates.append(package_root / "scripts" / "thesis_project_tool.py")
    return candidates


def main() -> int:
    script_path = next((path for path in iter_script_candidates() if path.exists()), None)
    if script_path is None:
        print("未找到 bensz-thesis 构建脚本。请先安装 bensz-thesis，或在完整仓库中运行本项目。", file=sys.stderr)
        return 1
    args = sys.argv[1:] or ["build", "--project-dir", str(PROJECT_DIR)]
    result = subprocess.run([sys.executable, str(script_path), *args], cwd=PROJECT_DIR)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
