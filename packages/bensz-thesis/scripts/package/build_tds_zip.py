#!/usr/bin/env python3
"""打包 bensz-thesis 为 TDS（TeX Directory Structure）兼容 ZIP。

将 ``packages/bensz-thesis/`` 及其依赖包 ``bensz-fonts/`` 中的运行时文件
按 TDS 目录布局打包为可分发的 zip 文件。

典型用法::

    python build_tds_zip.py            # 输出到 dist/bensz-thesis-{version}-tds.zip
    python build_tds_zip.py --out /tmp/bensz-thesis.zip
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

PACKAGE_NAME = "bensz-thesis"
# bensz-thesis 的前置依赖包列表，打包时会一并纳入
DEPENDENCY_PACKAGE_NAMES = ("bensz-fonts",)
# 打包时需要排除的目录名和文件名
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def find_package_dir(project_dir: Path) -> Path:
    """在项目目录中查找 bensz-thesis 包源码目录。

    按优先级依次搜索仓库源码路径、直接子目录路径和已安装的 TDS 路径。

    Args:
        project_dir: 项目根目录或仓库根目录。

    Returns:
        包含 bensz-thesis.sty 的包源码目录。

    Raises:
        FileNotFoundError: 所有候选路径均未找到包。
    """
    repo_package = project_dir / "packages" / PACKAGE_NAME
    direct_package = project_dir / PACKAGE_NAME
    installed_package = project_dir / "tex" / "latex" / PACKAGE_NAME
    for candidate in (repo_package, direct_package, installed_package):
        if (candidate / f"{PACKAGE_NAME}.sty").exists():
            return candidate
    raise FileNotFoundError(f"{PACKAGE_NAME} source directory not found under: {project_dir}")


def iter_files(package_src: Path):
    """遍历包目录中的所有文件，排除 __pycache__、.DS_Store 和 .pyc 文件。"""
    for path in sorted(package_src.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_NAMES for part in path.parts) or path.suffix == ".pyc":
            continue
        yield path


def find_dependency_dirs(project_dir: Path) -> list[tuple[str, Path]]:
    """在项目目录中查找所有依赖包的源码目录。

    Args:
        project_dir: 项目根目录或仓库根目录。

    Returns:
        列表，每项为 (依赖包名, 依赖包源码路径) 的元组。
    """
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
    """将 bensz-thesis 包及其依赖打包为 TDS 格式的 zip 文件。

    生成的 zip 内部路径遵循 ``tex/latex/<package-name>/...`` 结构，
    可直接解压到 TEXMFHOME 目录供 LaTeX 使用。

    Args:
        project_dir: 项目根目录或仓库根目录。
        output: 输出 zip 文件路径。

    Returns:
        生成的 zip 文件路径。
    """
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
    parser = argparse.ArgumentParser(description="Package bensz-thesis as a TDS zip.")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(), help="Project or repo root.")
    parser.add_argument("--output", type=Path, default=None, help="Output zip path.")
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    output = args.output or project_dir / "dist" / "bensz-thesis.tds.zip"
    zip_path = build_zip(project_dir, output.expanduser().resolve())
    print(zip_path)


if __name__ == "__main__":
    main()
