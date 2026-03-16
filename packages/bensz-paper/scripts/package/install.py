#!/usr/bin/env python3
"""
bensz-paper 本地安装工具
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "bensz-paper"
PACKAGE_SUBPATH = Path("tex") / "latex" / PACKAGE_NAME
DEPENDENCY_PACKAGE_NAMES = ("bensz-fonts",)
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}
PRIMARY_LAUNCHER = "bpaper"


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def find_package_source() -> Path:
    """Return the bensz-paper source directory."""
    # scripts/package/install.py -> scripts/package -> scripts -> pkg_root
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    if not (pkg_dir / f"{PACKAGE_NAME}.sty").exists():
        raise FileNotFoundError(
            f"Package source not found at: {pkg_dir}\n"
            "Run this script from within the repository."
        )
    return pkg_dir


def get_texmfhome(override: str | None = None) -> Path:
    """Resolve TEXMFHOME: CLI override > env var > kpsewhich > ~/texmf."""
    if override:
        return Path(override).expanduser().resolve()
    env_val = os.environ.get("TEXMFHOME")
    if env_val:
        return Path(env_val).expanduser().resolve()
    try:
        result = subprocess.run(
            ["kpsewhich", "--var-value", "TEXMFHOME"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).expanduser().resolve()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return Path.home() / "texmf"


def get_bin_dir(override: str | None = None) -> Path:
    """Resolve the directory for the bpaper launcher."""
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Local" / "Programs" / PRIMARY_LAUNCHER
    return Path.home() / ".local" / "bin"


def get_dest(texmfhome: Path) -> Path:
    return texmfhome / PACKAGE_SUBPATH


# ---------------------------------------------------------------------------
# Installation helpers
# ---------------------------------------------------------------------------

def run_mktexlsr(texmfhome: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] mktexlsr {texmfhome}")
        return
    if shutil.which("mktexlsr"):
        try:
            subprocess.run(
                ["mktexlsr", str(texmfhome)],
                check=True, capture_output=True,
            )
            print("✓ mktexlsr refreshed")
        except subprocess.CalledProcessError as exc:
            print(f"  Warning: mktexlsr failed: {exc}")
    else:
        print("  Note: mktexlsr not found — run it manually if needed.")


def install_python_deps(dest: Path, dry_run: bool, skip: bool) -> None:
    if skip:
        print("  Skipping Python dependency installation (--skip-python-deps)")
        return
    req_file = dest / "scripts" / "requirements.txt"
    if not req_file.exists():
        return
    missing = [
        name for name in ("yaml", "docx")
        if importlib.util.find_spec(name) is None
    ]
    if not missing:
        print("  Python dependencies already satisfied.")
        return
    if dry_run:
        print(f"  [dry-run] pip install -r {req_file}")
        return
    pip_cmd = [sys.executable, "-m", "pip", "install"]
    if not (os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")):
        pip_cmd.append("--user")
    pip_cmd.extend(["-r", str(req_file)])
    print("  Installing Python dependencies...")
    subprocess.run(pip_cmd, check=True)


def install_launcher(dest: Path, bin_dir: Path, dry_run: bool) -> None:
    launcher_src = dest / PRIMARY_LAUNCHER
    if platform.system() == "Windows":
        launcher_dest = bin_dir / f"{PRIMARY_LAUNCHER}.cmd"
        if dry_run:
            print(f"  [dry-run] write {launcher_dest}")
            return
        bin_dir.mkdir(parents=True, exist_ok=True)
        launcher_dest.write_text(
            f'@echo off\npython3 "{launcher_src}" %*\n', encoding="utf-8"
        )
    else:
        launcher_dest = bin_dir / PRIMARY_LAUNCHER
        if dry_run:
            print(f"  [dry-run] symlink {launcher_dest} -> {launcher_src}")
            return
        bin_dir.mkdir(parents=True, exist_ok=True)
        if launcher_dest.is_symlink() or launcher_dest.exists():
            launcher_dest.unlink()
        launcher_dest.symlink_to(launcher_src)
        launcher_src.chmod(0o755)
    print(f"✓ Launcher: {launcher_dest}")


def install_dependencies(src: Path, texmfhome: Path, dry_run: bool) -> None:
    packages_root = src.parent
    for dependency in DEPENDENCY_PACKAGE_NAMES:
        dependency_src = packages_root / dependency
        if not dependency_src.exists():
            continue
        dependency_dest = texmfhome / "tex" / "latex" / dependency
        print(f"  Dependency: {dependency_src} -> {dependency_dest}")
        if dry_run:
            for file_path in sorted(dependency_src.rglob("*")):
                if not file_path.is_file():
                    continue
                if any(part in EXCLUDE_NAMES for part in file_path.parts) or file_path.suffix == ".pyc":
                    continue
                print(f"    {file_path.relative_to(dependency_src)}")
            continue
        dependency_dest.mkdir(parents=True, exist_ok=True)
        for file_path in dependency_src.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in EXCLUDE_NAMES for part in file_path.parts) or file_path.suffix == ".pyc":
                continue
            target = dependency_dest / file_path.relative_to(dependency_src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def do_install(args: argparse.Namespace) -> int:
    src = find_package_source()
    texmfhome = get_texmfhome(args.texmfhome)
    dest = get_dest(texmfhome)
    bin_dir = get_bin_dir(args.bin_dir)
    dry_run = args.dry_run

    print("bensz-paper — install")
    print(f"  Source : {src}")
    print(f"  Dest   : {dest}")
    print(f"  {PRIMARY_LAUNCHER:<6}: {bin_dir / PRIMARY_LAUNCHER}")
    if dry_run:
        print("  Mode   : dry-run (no files will be written)")
    print()

    install_dependencies(src, texmfhome, dry_run)

    if dry_run:
        print("Files that would be installed:")
        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            if any(p in EXCLUDE_NAMES for p in f.parts) or f.suffix == ".pyc":
                continue
            print(f"  {f.relative_to(src)}")
        print()
    else:
        if src == dest:
            print("  Source is already the install destination; refreshing launcher only.")
        else:
            dest.mkdir(parents=True, exist_ok=True)
            for f in src.rglob("*"):
                if not f.is_file():
                    continue
                if any(p in EXCLUDE_NAMES for p in f.parts) or f.suffix == ".pyc":
                    continue
                target = dest / f.relative_to(src)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
            for pycache in dest.rglob("__pycache__"):
                shutil.rmtree(pycache, ignore_errors=True)
        print(f"✓ Installed to {dest}")

    install_launcher(dest, bin_dir, dry_run)
    install_python_deps(dest, dry_run, args.skip_python_deps)
    run_mktexlsr(texmfhome, dry_run)

    if not dry_run:
        print()
        print("Verify with:")
        print("  kpsewhich bensz-paper.sty")
        print("  bpaper --version")
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        if str(bin_dir) not in path_dirs:
            shell = os.environ.get("SHELL", "")
            profile = "~/.zshrc" if "zsh" in shell else "~/.bashrc"
            print()
            print(f"  Note: {bin_dir} is not on PATH.")
            print(f"  Add to {profile}:")
            print(f'    export PATH="{bin_dir}:$PATH"')
    return 0


def do_status(args: argparse.Namespace) -> int:
    texmfhome = get_texmfhome(args.texmfhome)
    dest = get_dest(texmfhome)
    bin_dir = get_bin_dir(args.bin_dir)

    print("bensz-paper — status")
    print()

    sty = dest / f"{PACKAGE_NAME}.sty"
    if sty.exists():
        print(f"✓ Package installed : {dest}")
    else:
        print(f"✗ Package NOT found : {dest}")

    if shutil.which("kpsewhich"):
        r = subprocess.run(
            ["kpsewhich", f"{PACKAGE_NAME}.sty"],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            print(f"✓ kpsewhich         : {r.stdout.strip()}")
        else:
            print("✗ kpsewhich         : not in TeX search path (run mktexlsr?)")
    else:
        print("  kpsewhich           : not found (TeX Live not installed?)")

    launcher = bin_dir / PRIMARY_LAUNCHER
    if launcher.exists() or launcher.is_symlink():
        print(f"✓ Launcher          : {launcher}")
    else:
        print(f"✗ Launcher NOT found: {launcher}")

    missing = [
        name for name in ("yaml", "docx")
        if importlib.util.find_spec(name) is None
    ]
    if not missing:
        print("✓ Python deps       : satisfied")
    else:
        print(f"✗ Python deps       : missing {', '.join(missing)}")
    return 0


def do_uninstall(args: argparse.Namespace) -> int:
    texmfhome = get_texmfhome(args.texmfhome)
    dest = get_dest(texmfhome)
    bin_dir = get_bin_dir(args.bin_dir)
    dry_run = args.dry_run

    print("bensz-paper — uninstall")
    print(f"  Target : {dest}")
    if dry_run:
        print("  Mode   : dry-run")
    print()

    removed_any = False

    if dest.exists():
        if dry_run:
            print(f"  [dry-run] rm -rf {dest}")
        else:
            shutil.rmtree(dest)
            print(f"✓ Removed: {dest}")
        removed_any = True
    else:
        print(f"  Not installed: {dest}")

    for name in (PRIMARY_LAUNCHER, f"{PRIMARY_LAUNCHER}.cmd"):
        launcher = bin_dir / name
        if launcher.exists() or launcher.is_symlink():
            if dry_run:
                print(f"  [dry-run] rm {launcher}")
            else:
                launcher.unlink()
                print(f"✓ Removed launcher: {launcher}")
            removed_any = True

    if removed_any and not dry_run:
        run_mktexlsr(texmfhome, dry_run)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="bensz-paper 本地安装工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python install.py                        # 安装\n"
            "  python install.py --status               # 检查状态\n"
            "  python install.py --uninstall            # 卸载\n"
            "  python install.py --dry-run              # 预览\n"
            "  python install.py --texmfhome ~/mytexmf  # 指定安装目录"
        ),
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--status", action="store_true", help="检查安装状态")
    action.add_argument("--uninstall", action="store_true", help="卸载")
    parser.add_argument("--dry-run", action="store_true", help="预览，不实际写入")
    parser.add_argument("--skip-python-deps", action="store_true", help="跳过 pip 依赖安装")
    parser.add_argument("--texmfhome", metavar="PATH", help="覆盖 TEXMFHOME 路径")
    parser.add_argument("--bin-dir", metavar="PATH", help="覆盖 bpaper 启动器安装目录")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.status:
        sys.exit(do_status(args))
    elif args.uninstall:
        sys.exit(do_uninstall(args))
    else:
        sys.exit(do_install(args))


if __name__ == "__main__":
    main()
