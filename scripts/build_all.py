#!/usr/bin/env python3
"""
编译所有 LaTeX 项目的主文档
Support: NSFC_Young, NSFC_General, NSFC_Local
"""

import os
import subprocess
import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 需要编译的项目
PROJECTS = ["NSFC_Young", "NSFC_General", "NSFC_Local"]


def build_project(project_name: str) -> bool:
    """编译单个项目"""
    project_dir = ROOT_DIR / "projects" / project_name
    main_tex = project_dir / "main.tex"

    if not main_tex.exists():
        print(f"⚠️  跳过 {project_name}: main.tex 不存在")
        return False

    print(f"🔨 正在编译 {project_name}...")

    # 使用 xelatex 编译（支持中文）
    result = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "main.tex"],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✅ {project_name} 编译成功")
        return True
    else:
        print(f"❌ {project_name} 编译失败")
        print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
        return False


def main():
    """主函数"""
    print("🚀 开始编译所有项目...\n")

    success_count = 0
    for project in PROJECTS:
        if build_project(project):
            success_count += 1
        print()

    print(f"📊 编译完成: {success_count}/{len(PROJECTS)} 成功")
    sys.exit(0 if success_count == len(PROJECTS) else 1)


if __name__ == "__main__":
    main()
