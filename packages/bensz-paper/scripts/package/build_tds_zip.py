#!/usr/bin/env python3
"""将 bensz-paper 公共包打包为 TDS（TeX Directory Structure）兼容 ZIP。

生成的 ZIP 文件可直接解压到用户级 texmf 树（如 ~/texmf/），
然后运行 mktexlsr 使 kpathsea 识别新安装的包文件。

ZIP 内部结构遵循 TDS 规范：
  tex/latex/bensz-paper/   — bensz-paper 公共包所有文件
  tex/latex/bensz-fonts/   — bensz-fonts 依赖包（仅 sty 文件）

自动排除 __pycache__、.pyc、.DS_Store 等非发布文件。
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

# bensz-paper 的运行时依赖包列表，打包时会一并包含这些包的 sty 文件
DEPENDENCY_PACKAGE_NAMES = ("bensz-fonts",)


def configure_windows_stdio_utf8() -> None:
    """在 Windows 上将 stdout/stderr 重编码为 UTF-8，避免中文输出乱码。"""
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

def looks_like_distribution_root(path: Path) -> bool:
    """判断给定路径是否为 TDS 源码根（仓库根、texmf 根或直接包含 .sty 的目录）。"""
    repo_package = path / "packages" / "bensz-paper"
    installed_package = path / "tex" / "latex" / "bensz-paper"
    direct_package = path / "bensz-paper.sty"
    return repo_package.exists() or installed_package.exists() or direct_package.exists()


def find_distribution_root(start: Path | None = None) -> Path:
    """Walk upward until a TDS source root is found."""
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if looks_like_distribution_root(candidate):
            return candidate
    raise FileNotFoundError(
        "Cannot find TDS source root. Run inside the repository, inside a texmf tree, "
        "or pass --project-dir explicitly."
    )


def resolve_texmf_source(project_dir: Path) -> Path:
    """从项目根目录中定位 bensz-paper 包源码目录。

    按优先级探测三个候选位置：
    1. 仓库内 packages/bensz-paper/
    2. texmf 树内 tex/latex/bensz-paper/
    3. 直接包含 bensz-paper.sty 的目录
    """
    repo_package = project_dir / "packages" / "bensz-paper"
    if repo_package.exists():
        return repo_package

    installed_package = project_dir / "tex" / "latex" / "bensz-paper"
    if installed_package.exists():
        return installed_package

    if (project_dir / "bensz-paper.sty").exists():
        return project_dir

    raise FileNotFoundError(f"bensz-paper source directory not found under: {project_dir}")


def resolve_dependency_sources(project_dir: Path) -> list[tuple[str, Path]]:
    """查找依赖包的源码目录，返回 (包名, 路径) 列表。用于将依赖包一并打入 TDS ZIP。"""
    sources: list[tuple[str, Path]] = []
    for dependency in DEPENDENCY_PACKAGE_NAMES:
        candidates = (
            project_dir / "packages" / dependency,
            project_dir / "tex" / "latex" / dependency,
        )
        for candidate in candidates:
            if (candidate / f"{dependency}.sty").exists():
                sources.append((dependency, candidate))
                break
    return sources


def build_tds_zip(project_dir: Path, output_path: Path) -> None:
    """构建 TDS 兼容 ZIP 文件。

    将 bensz-paper 包和所有依赖包的文件按 TDS 路径规范写入 ZIP。
    输出结构：tex/latex/<包名>/<文件>。
    自动跳过 __pycache__、.pyc、.DS_Store。
    """
    package_src = resolve_texmf_source(project_dir)
    dependency_sources = resolve_dependency_sources(project_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for src_file in sorted(package_src.rglob('*')):
            if not src_file.is_file():
                continue
            if "__pycache__" in src_file.parts or src_file.suffix == ".pyc" or src_file.name == ".DS_Store":
                continue

            arcname = Path("tex") / "latex" / "bensz-paper" / src_file.relative_to(package_src)
            zf.write(src_file, arcname)
            print(f'  + {arcname}')
        for dependency, dependency_src in dependency_sources:
            for src_file in sorted(dependency_src.rglob('*')):
                if not src_file.is_file():
                    continue
                if "__pycache__" in src_file.parts or src_file.suffix == ".pyc" or src_file.name == ".DS_Store":
                    continue
                arcname = Path("tex") / "latex" / dependency / src_file.relative_to(dependency_src)
                zf.write(src_file, arcname)
                print(f'  + {arcname}')

    print(f'\n✓ TDS zip created: {output_path}')
    print(
        '\nTo install, extract into your local texmf tree and run mktexlsr:\n'
        f'  unzip {output_path} -d ~/texmf/\n'
        '  mktexlsr ~/texmf/'
    )


def parse_args() -> argparse.Namespace:
    """解析命令行参数，支持 --output 和 --project-dir 选项。"""
    parser = argparse.ArgumentParser(
        description='Package bensz-paper as a TDS zip.'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=None,
        help='Output zip path (default: dist/bensz-paper.tds.zip)'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=None,
        help='Repository root, package root, or texmf root directory.'
    )
    return parser.parse_args()


def main() -> None:
    """命令行入口：定位源码根目录并生成 TDS ZIP。"""
    configure_windows_stdio_utf8()
    args = parse_args()
    project_dir = find_distribution_root(args.project_dir)
    output = args.output or project_dir / 'dist' / 'bensz-paper.tds.zip'
    build_tds_zip(project_dir, output)


if __name__ == '__main__':
    main()
