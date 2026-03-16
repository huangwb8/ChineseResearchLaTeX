#!/usr/bin/env python3
"""
将 `packages/bensz-paper/` 打包为 TDS（TeX Directory Structure）兼容 ZIP。
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

DEPENDENCY_PACKAGE_NAMES = ("bensz-fonts",)

def looks_like_distribution_root(path: Path) -> bool:
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
    """Build a TDS-compliant zip from the local package directory."""
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
    args = parse_args()
    project_dir = find_distribution_root(args.project_dir)
    output = args.output or project_dir / 'dist' / 'bensz-paper.tds.zip'
    build_tds_zip(project_dir, output)


if __name__ == '__main__':
    main()
