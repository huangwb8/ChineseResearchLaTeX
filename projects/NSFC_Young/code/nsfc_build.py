#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def get_texmf_home() -> Path | None:
    kpsewhich = subprocess.run(
        ["kpsewhich", "-var-value", "TEXMFHOME"],
        capture_output=True,
        text=True,
        check=False,
    )
    if kpsewhich.returncode != 0:
        return None
    value = kpsewhich.stdout.strip()
    return Path(value).expanduser() if value else None


def get_installed_package_root() -> Path | None:
    kpsewhich = subprocess.run(
        ["kpsewhich", "bensz-nsfc-common.sty"],
        capture_output=True,
        text=True,
        check=False,
    )
    if kpsewhich.returncode != 0:
        return None
    value = kpsewhich.stdout.strip()
    if not value:
        return None
    return Path(value).expanduser().resolve().parent


def iter_script_candidates() -> list[Path]:
    candidates: list[Path] = [
        PROJECT_DIR.parent.parent / "packages" / "bensz-nsfc" / "scripts" / "nsfc_project_tool.py",
    ]

    package_root = get_installed_package_root()
    if package_root is not None:
        candidates.append(package_root / "scripts" / "nsfc_project_tool.py")

    texmf_home = get_texmf_home()
    if texmf_home is not None:
        candidates.append(texmf_home / "tex" / "latex" / "bensz-nsfc" / "scripts" / "nsfc_project_tool.py")

    return candidates


def main() -> int:
    script_path = next((path for path in iter_script_candidates() if path.exists()), None)
    if script_path is None:
        print(
            "未找到 nsfc_project_tool.py。请先按官方方式安装 bensz-nsfc 包，或在完整仓库中运行本项目。",
            file=sys.stderr,
        )
        return 1

    args = sys.argv[1:] or ["build", "--project-dir", str(PROJECT_DIR)]
    result = subprocess.run([sys.executable, str(script_path), *args], cwd=PROJECT_DIR)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
