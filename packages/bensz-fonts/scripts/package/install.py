#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "bensz-fonts"
PACKAGE_SUBPATH = Path("tex") / "latex" / PACKAGE_NAME
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def find_package_source() -> Path:
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    if not (pkg_dir / f"{PACKAGE_NAME}.sty").exists():
        raise FileNotFoundError(f"Package source not found at: {pkg_dir}")
    return pkg_dir


def get_texmfhome(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env_val = os.environ.get("TEXMFHOME")
    if env_val:
        return Path(env_val).expanduser().resolve()
    try:
        result = subprocess.run(
            ["kpsewhich", "--var-value", "TEXMFHOME"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).expanduser().resolve()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return Path.home() / "texmf"


def run_mktexlsr(texmfhome: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] mktexlsr {texmfhome}")
        return
    if shutil.which("mktexlsr"):
        subprocess.run(["mktexlsr", str(texmfhome)], check=False, capture_output=True)


def install_tree(src: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        for file_path in sorted(src.rglob("*")):
            if not file_path.is_file():
                continue
            if any(part in EXCLUDE_NAMES for part in file_path.parts) or file_path.suffix == ".pyc":
                continue
            print(f"  {file_path.relative_to(src)}")
        return

    dest.mkdir(parents=True, exist_ok=True)
    for file_path in src.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in EXCLUDE_NAMES for part in file_path.parts) or file_path.suffix == ".pyc":
            continue
        target = dest / file_path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)


def do_install(args: argparse.Namespace) -> int:
    src = find_package_source()
    texmfhome = get_texmfhome(args.texmfhome)
    dest = texmfhome / PACKAGE_SUBPATH

    print("bensz-fonts — install")
    print(f"  Source : {src}")
    print(f"  Dest   : {dest}")
    if args.dry_run:
        print("  Mode   : dry-run")
    print()

    install_tree(src, dest, args.dry_run)
    run_mktexlsr(texmfhome, args.dry_run)
    return 0


def do_status(args: argparse.Namespace) -> int:
    texmfhome = get_texmfhome(args.texmfhome)
    dest = texmfhome / PACKAGE_SUBPATH
    print("bensz-fonts — status")
    print()
    print(f"Package dir: {dest}")
    print(f"Exists     : {'yes' if dest.exists() else 'no'}")
    if shutil.which("kpsewhich"):
        result = subprocess.run(
            ["kpsewhich", f"{PACKAGE_NAME}.sty"],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"kpsewhich  : {result.stdout.strip() or '(not found)'}")
    return 0


def do_uninstall(args: argparse.Namespace) -> int:
    texmfhome = get_texmfhome(args.texmfhome)
    dest = texmfhome / PACKAGE_SUBPATH
    print("bensz-fonts — uninstall")
    print(f"  Target : {dest}")
    if args.dry_run:
        print("  Mode   : dry-run")
    print()
    if dest.exists():
        if args.dry_run:
            print(f"  [dry-run] rm -rf {dest}")
        else:
            shutil.rmtree(dest)
            run_mktexlsr(texmfhome, False)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="bensz-fonts 本地安装工具")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--status", action="store_true", help="检查安装状态")
    action.add_argument("--uninstall", action="store_true", help="卸载")
    parser.add_argument("--dry-run", action="store_true", help="预览，不实际写入")
    parser.add_argument("--texmfhome", metavar="PATH", help="覆盖 TEXMFHOME 路径")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.status:
        sys.exit(do_status(args))
    if args.uninstall:
        sys.exit(do_uninstall(args))
    sys.exit(do_install(args))


if __name__ == "__main__":
    main()
