#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def get_installed_package_root() -> Path | None:
    for candidate in ("bensz-cv.cls", "resume.cls"):
        kpsewhich = subprocess.run(
            ["kpsewhich", candidate],
            capture_output=True,
            text=True,
            check=False,
        )
        if kpsewhich.returncode != 0:
            continue
        value = kpsewhich.stdout.strip()
        if value:
            return Path(value).expanduser().resolve().parent
    return None


def iter_script_candidates() -> list[Path]:
    candidates = [
        PROJECT_DIR.parent.parent / "packages" / "bensz-cv" / "scripts" / "cv_project_tool.py",
    ]
    package_root = get_installed_package_root()
    if package_root is not None:
        candidates.append(package_root / "scripts" / "cv_project_tool.py")
    return candidates


def normalize_path_args(args: list[str], invocation_cwd: Path) -> list[str]:
    normalized = list(args)
    path_flags = {"--project-dir", "--baseline-pdf", "--output-dir"}
    for idx, value in enumerate(normalized[:-1]):
        if value not in path_flags:
            continue
        candidate = Path(normalized[idx + 1])
        if candidate.is_absolute():
            continue
        normalized[idx + 1] = str((invocation_cwd / candidate).resolve())
    return normalized


def main() -> int:
    script_path = next((path for path in iter_script_candidates() if path.exists()), None)
    if script_path is None:
        print(
            "未找到 bensz-cv 构建脚本。请先安装 bensz-cv，或在完整仓库中运行本项目。",
            file=sys.stderr,
        )
        return 1

    invocation_cwd = Path.cwd()
    args = sys.argv[1:] or ["build", "--project-dir", str(PROJECT_DIR), "--variant", "all"]
    args = normalize_path_args(args, invocation_cwd)
    result = subprocess.run([sys.executable, str(script_path), *args], cwd=PROJECT_DIR)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
