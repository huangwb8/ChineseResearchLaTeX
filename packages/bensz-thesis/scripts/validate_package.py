#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_DIR.parents[1]


def validate_required_files() -> list[str]:
    required = [
        "bensz-thesis.sty",
        "bthesis-core.sty",
        "profiles/bthesis-profile-thesis-smu-master.def",
        "profiles/bthesis-profile-thesis-sysu-doctor.def",
        "profiles/bthesis-profile-thesis-ucas-doctor.def",
        "styles/bthesis-style-thesis-smu-master.tex",
        "styles/bthesis-style-thesis-sysu-doctor.tex",
        "styles/bthesis-style-thesis-ucas-doctor.tex",
        "styles/ucas/ucasDissertation.cls",
        "styles/ucas/ucasInfo.sty",
        "styles/ucas/ucasSilence.sty",
        "README.md",
        "scripts/thesis_project_tool.py",
        "scripts/package/install.py",
        "scripts/package/build_tds_zip.py",
    ]
    return [entry for entry in required if not (PACKAGE_DIR / entry).exists()]


def compile_project(project_name: str) -> dict[str, object]:
    cmd = [
        sys.executable,
        str(PACKAGE_DIR / "scripts" / "thesis_project_tool.py"),
        "build",
        "--project-dir",
        str(REPO_ROOT / "projects" / project_name),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "command": cmd,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 bensz-thesis 公共包")
    parser.add_argument("--skip-compile", action="store_true")
    args = parser.parse_args()

    missing = validate_required_files()
    if missing:
        print(json.dumps({"status": "error", "missing_files": missing}, ensure_ascii=False, indent=2))
        return 1

    status: dict[str, object] = {
        "status": "ok",
        "package": "bensz-thesis",
    }
    if not args.skip_compile:
        for project_name in ("thesis-smu-master", "thesis-sysu-doctor", "thesis-ucas-doctor"):
            result = compile_project(project_name)
            status[f"{project_name}_compile"] = result
            if result["returncode"] != 0:
                status["status"] = "error"
                print(json.dumps(status, ensure_ascii=False, indent=2))
                return 1

    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
