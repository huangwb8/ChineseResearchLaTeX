#!/usr/bin/env python3
"""将 bensz-cv 公共包及其依赖（bensz-fonts）打包为 TDS（TeX Directory Structure）格式的 zip。

输出文件结构遵循 tex/latex/<package-name>/ 的标准布局，
可直接解压到 TEXMFHOME 或用于 CTAN / Overleaf 分发。
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

PACKAGE_NAME = "bensz-cv"
# bensz-cv 依赖的共享包列表，打包时一并纳入
DEPENDENCY_PACKAGE_NAMES = ("bensz-fonts",)
# 打包时排除的目录名和文件模式
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def find_package_dir(project_dir: Path) -> Path:
    """在仓库中定位 bensz-cv 源码目录，依次尝试 packages/、直接子目录、tex/latex/ 三种路径。"""
    repo_package = project_dir / "packages" / PACKAGE_NAME
    direct_package = project_dir / PACKAGE_NAME
    installed_package = project_dir / "tex" / "latex" / PACKAGE_NAME
    for candidate in (repo_package, direct_package, installed_package):
        if (candidate / f"{PACKAGE_NAME}.cls").exists():
            return candidate
    raise FileNotFoundError(f"{PACKAGE_NAME} source directory not found under: {project_dir}")


def iter_files(package_src: Path):
    """遍历源码目录中的所有文件，排除 __pycache__、.DS_Store 和 .pyc。"""
    for path in sorted(package_src.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_NAMES for part in path.parts) or path.suffix == ".pyc":
            continue
        yield path


def find_dependency_dirs(project_dir: Path) -> list[tuple[str, Path]]:
    """查找依赖包的源码目录（如 bensz-fonts），用于一并打入 TDS zip。"""
    found: list[tuple[str, Path]] = []
    for dependency in DEPENDENCY_PACKAGE_NAMES:
        for candidate in (
            project_dir / "packages" / dependency,
            project_dir / "tex" / "latex" / dependency,
        ):
            if (candidate / f"{dependency}.sty").exists():
                found.append((dependency, candidate))
                break
    return found


def build_zip(project_dir: Path, output: Path) -> Path:
    """构建 TDS 格式 zip，包含 bensz-cv 及其依赖包的所有文件。"""
    package_src = find_package_dir(project_dir)
    dependency_dirs = find_dependency_dirs(project_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for src_file in iter_files(package_src):
            arcname = Path("tex") / "latex" / PACKAGE_NAME / src_file.relative_to(package_src)
            zf.write(src_file, arcname=arcname)
        for dependency, dependency_src in dependency_dirs:
            for src_file in iter_files(dependency_src):
                arcname = Path("tex") / "latex" / dependency / src_file.relative_to(dependency_src)
                zf.write(src_file, arcname=arcname)
    return output


def main() -> None:
    """CLI 入口：解析参数并执行 TDS zip 打包。"""
    parser = argparse.ArgumentParser(description="Package bensz-cv as a TDS zip.")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(), help="Project or repo root.")
    parser.add_argument("--output", type=Path, default=None, help="Output zip path.")
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    output = args.output or project_dir / "dist" / "bensz-cv.tds.zip"
    zip_path = build_zip(project_dir, output.expanduser().resolve())
    print(zip_path)


if __name__ == "__main__":
    main()
