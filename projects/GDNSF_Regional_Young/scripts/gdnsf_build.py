#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_DIR.parents[1]


def _texinputs(project_dir: Path) -> str:
    candidates = [
        project_dir,
        REPO_ROOT / "packages" / "bensz-fonts",
        REPO_ROOT / "packages" / "bensz-fonts" / "fonts",
    ]
    existing = [str(path.resolve()) for path in candidates if path.exists()]
    return os.pathsep.join([*existing, ""])


def _run(command: list[str], project_dir: Path, env: dict[str, str]) -> int:
    print("+ " + " ".join(command))
    result = subprocess.run(command, cwd=project_dir, env=env)
    return result.returncode


def build(project_dir: Path, tex_file: str) -> int:
    project_dir = project_dir.resolve()
    tex_path = (project_dir / tex_file).resolve()
    if not tex_path.exists():
        print(f"找不到 TeX 文件：{tex_path}", file=sys.stderr)
        return 2

    cache_dir = project_dir / ".latex-cache"
    cache_dir.mkdir(exist_ok=True)
    jobname = tex_path.stem

    env = os.environ.copy()
    env["TEXINPUTS"] = _texinputs(project_dir) + os.pathsep + env.get("TEXINPUTS", "")

    xelatex = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-recorder",
        f"-output-directory={cache_dir}",
        tex_path.name,
    ]

    for _ in range(2):
        code = _run(xelatex, project_dir, env)
        if code != 0:
            return code

    source_pdf = cache_dir / f"{jobname}.pdf"
    target_pdf = project_dir / f"{jobname}.pdf"
    if not source_pdf.exists():
        print(f"未生成 PDF：{source_pdf}", file=sys.stderr)
        return 1
    shutil.copy2(source_pdf, target_pdf)
    print(f"已生成：{target_pdf}")
    return 0


def clean(project_dir: Path) -> int:
    project_dir = project_dir.resolve()
    cache_dir = project_dir / ".latex-cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    for suffix in (".aux", ".log", ".out", ".toc", ".synctex.gz", ".xdv"):
        for path in project_dir.glob(f"*{suffix}"):
            path.unlink()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GDNSF project build helper")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="build project PDF")
    build_parser.add_argument("--project-dir", default=str(PROJECT_DIR))
    build_parser.add_argument("--tex-file", default="main.tex")

    clean_parser = subparsers.add_parser("clean", help="remove LaTeX cache")
    clean_parser.add_argument("--project-dir", default=str(PROJECT_DIR))

    args = parser.parse_args(argv)
    if args.command is None:
        args.command = "build"
        args.project_dir = str(PROJECT_DIR)
        args.tex_file = "main.tex"
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    project_dir = Path(args.project_dir)
    if args.command == "build":
        return build(project_dir, args.tex_file)
    if args.command == "clean":
        return clean(project_dir)
    print(f"未知命令：{args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
