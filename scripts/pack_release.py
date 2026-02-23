#!/usr/bin/env python3
"""
pack_release.py - 打包 projects/ 下各子项目为 Release Assets

用法：
  python scripts/pack_release.py --tag v3.3.0          # 仅打包
  python scripts/pack_release.py --tag v3.3.0 --upload # 打包并上传到 GitHub Release

打包规范：
  - 输出目录：./tests/release-{tag}/（如 ./tests/release-v3.3.0/）
  - 每个子项目生成独立 zip，文件名格式：{项目名}-{tag}.zip
  - zip 内仅保留 INCLUDE_ITEMS 白名单中的文件/目录：
      .vscode/  bibtex-style/  code/  extraTex/  figures/  fonts/
      references/  template/  main.pdf  main.tex  README.md
  - 不存在的白名单项自动跳过（如 .vscode/ 不存在时不报错）

严格约束：
  - 不修改 projects/ 目录内任何文件
  - zip 生成操作仅在 tests/ 目录进行
"""

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

# zip 内保留的文件/目录（与 AGENTS.md 保持一致）
INCLUDE_ITEMS = [
    ".vscode",
    "bibtex-style",
    "code",
    "extraTex",
    "figures",
    "fonts",
    "references",
    "template",
    "main.pdf",
    "main.tex",
    "README.md",
]

REPO_ROOT = Path(__file__).parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
TESTS_DIR = REPO_ROOT / "tests"


def get_git_tag() -> str:
    """从 git 获取最新 tag。"""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if result.returncode != 0:
        sys.exit("错误：无法自动获取 git tag，请通过 --tag 手动指定。")
    return result.stdout.strip()


def pack_project(project_dir: Path, output_dir: Path, tag: str) -> Path:
    """将单个子项目打包为 zip，返回 zip 路径。"""
    zip_name = f"{project_dir.name}-{tag}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item_name in INCLUDE_ITEMS:
            item_path = project_dir / item_name
            if not item_path.exists():
                continue
            if item_path.is_file():
                zf.write(item_path, arcname=item_name)
            elif item_path.is_dir():
                for file in sorted(item_path.rglob("*")):
                    if file.is_file():
                        zf.write(file, arcname=file.relative_to(project_dir))

    return zip_path


def upload_asset(tag: str, zip_path: Path) -> None:
    """通过 gh CLI 上传 zip 到 GitHub Release。"""
    result = subprocess.run(
        ["gh", "release", "upload", tag, str(zip_path), "--clobber"],
        cwd=REPO_ROOT
    )
    if result.returncode != 0:
        sys.exit(f"错误：上传 {zip_path.name} 失败。")


def main() -> None:
    parser = argparse.ArgumentParser(description="打包 Release Assets")
    parser.add_argument("--tag", help="版本 tag（如 v3.3.0），省略则自动从 git 获取")
    parser.add_argument("--upload", action="store_true", help="打包后上传到 GitHub Release")
    args = parser.parse_args()

    tag = args.tag or get_git_tag()
    output_dir = TESTS_DIR / f"release-{tag}"
    output_dir.mkdir(parents=True, exist_ok=True)

    projects = sorted(p for p in PROJECTS_DIR.iterdir() if p.is_dir())
    if not projects:
        sys.exit(f"错误：{PROJECTS_DIR} 下没有找到子项目。")

    print(f"Tag: {tag}  |  输出目录: {output_dir.relative_to(REPO_ROOT)}")
    print("-" * 50)

    zips = []
    for project in projects:
        zip_path = pack_project(project, output_dir, tag)
        size_kb = zip_path.stat().st_size // 1024
        print(f"  ✓ {zip_path.name}  ({size_kb} KB)")
        zips.append(zip_path)

    if args.upload:
        print("\n上传到 GitHub Release...")
        for zip_path in zips:
            upload_asset(tag, zip_path)
            print(f"  ↑ {zip_path.name}")

    print(f"\n完成：{len(zips)} 个 zip 已生成。")


if __name__ == "__main__":
    main()
