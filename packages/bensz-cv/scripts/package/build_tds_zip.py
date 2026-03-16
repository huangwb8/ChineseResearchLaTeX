#!/usr/bin/env python3
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

PACKAGE_NAME = "bensz-cv"
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def find_package_dir(project_dir: Path) -> Path:
    repo_package = project_dir / "packages" / PACKAGE_NAME
    direct_package = project_dir / PACKAGE_NAME
    installed_package = project_dir / "tex" / "latex" / PACKAGE_NAME
    for candidate in (repo_package, direct_package, installed_package):
        if (candidate / f"{PACKAGE_NAME}.cls").exists():
            return candidate
    raise FileNotFoundError(f"{PACKAGE_NAME} source directory not found under: {project_dir}")


def iter_files(package_src: Path):
    for path in sorted(package_src.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_NAMES for part in path.parts) or path.suffix == ".pyc":
            continue
        yield path


def build_zip(project_dir: Path, output: Path) -> Path:
    package_src = find_package_dir(project_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for src_file in iter_files(package_src):
            arcname = Path("tex") / "latex" / PACKAGE_NAME / src_file.relative_to(package_src)
            zf.write(src_file, arcname=arcname)
    return output


def main() -> None:
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
