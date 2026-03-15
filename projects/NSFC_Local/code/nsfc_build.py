#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
STATE_FILE = Path.home() / ".bensz-nsfc" / "state.json"


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


def iter_script_candidates() -> list[Path]:
    candidates: list[Path] = [
        PROJECT_DIR.parent.parent / "packages" / "bensz-nsfc" / "scripts" / "nsfc_project_tool.py",
        PROJECT_DIR / "packages" / "bensz-nsfc" / "scripts" / "nsfc_project_tool.py",
    ]

    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            install_path = ((state.get("current") or {}).get("install_path"))
            if install_path:
                candidates.append(Path(install_path) / "scripts" / "nsfc_project_tool.py")
        except json.JSONDecodeError:
            pass

    texmf_home = get_texmf_home()
    if texmf_home is not None:
        candidates.append(texmf_home / "tex" / "latex" / "bensz-nsfc" / "scripts" / "nsfc_project_tool.py")

    return candidates


def main() -> int:
    script_path = next((path for path in iter_script_candidates() if path.exists()), None)
    if script_path is None:
        print(
            "未找到 nsfc_project_tool.py。请先安装 bensz-nsfc 包，或在完整仓库中运行本项目。",
            file=sys.stderr,
        )
        return 1

    args = sys.argv[1:] or ["build", "--project-dir", str(PROJECT_DIR)]
    result = subprocess.run([sys.executable, str(script_path), *args], cwd=PROJECT_DIR)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
