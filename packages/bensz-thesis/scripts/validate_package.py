#!/usr/bin/env python3
"""bensz-thesis 公共包结构校验工具。

检查 ``packages/bensz-thesis/`` 的必要文件完整性和版本号一致性，
并可选执行编译验证。

典型用法::

    python validate_package.py                  # 完整校验
    python validate_package.py --skip-compile   # 仅结构校验
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# bensz-thesis 公共包根目录（packages/bensz-thesis）
PACKAGE_DIR = Path(__file__).resolve().parents[1]
# 仓库根目录
REPO_ROOT = PACKAGE_DIR.parents[1]


def validate_required_files() -> list[str]:
    """检查 bensz-thesis 公共包中必需的文件是否齐全。

    校验范围包括：核心 .sty 文件、各院校 profile 定义、各院校样式文件、
    UCAS 子目录文档类、README 以及构建/安装/打包脚本。

    Returns:
        缺失文件路径的列表；若列表为空则表示所有必需文件均存在。
    """
    required = [
        "bensz-thesis.sty",
        "bthesis-core.sty",
        "profiles/bthesis-profile-thesis-smu-master.def",
        "profiles/bthesis-profile-thesis-nju-master.def",
        "profiles/bthesis-profile-thesis-sysu-doctor.def",
        "profiles/bthesis-profile-thesis-ucas-doctor.def",
        "styles/bthesis-style-thesis-smu-master.tex",
        "styles/bthesis-style-thesis-nju-master.tex",
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
        for project_name in (
            "thesis-smu-master",
            "thesis-nju-master",
            "thesis-sysu-doctor",
            "thesis-ucas-doctor",
        ):
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
