#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "bensz-cv"
PACKAGE_SUBPATH = Path("tex") / "latex" / PACKAGE_NAME
DEPENDENCY_PACKAGE_NAMES = ("bensz-fonts",)
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def unique_existing_dirs(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        expanded = path.expanduser()
        try:
            resolved = expanded.resolve()
        except OSError:
            resolved = expanded
        key = str(resolved).lower() if platform.system() == "Windows" else str(resolved)
        if key in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(key)
        unique.append(resolved)
    return unique


def candidate_tex_bin_dirs() -> list[Path]:
    candidates: list[Path] = []
    path_env = os.environ.get("PATH", "")
    candidates.extend(Path(item) for item in path_env.split(os.pathsep) if item)

    for env_name in ("TEXBIN", "TEXLIVE_BIN", "MIKTEX_BIN"):
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(Path(env_value))

    system = platform.system()
    if system == "Darwin":
        candidates.extend([Path("/Library/TeX/texbin"), Path("/usr/local/bin"), Path("/opt/homebrew/bin")])
        texlive_root = Path("/usr/local/texlive")
        if texlive_root.exists():
            candidates.extend(path for path in texlive_root.glob("*/bin/*") if path.is_dir())
    elif system == "Windows":
        for root in (
            os.environ.get("LOCALAPPDATA"),
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
        ):
            if not root:
                continue
            base = Path(root)
            candidates.extend(
                [
                    base / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
                    base / "Programs" / "MiKTeX" / "miktex" / "bin",
                    base / "MiKTeX" / "miktex" / "bin" / "x64",
                    base / "MiKTeX" / "miktex" / "bin",
                ]
            )
        system_drive = os.environ.get("SystemDrive", Path.home().drive or "C:")
        texlive_root = Path(f"{system_drive}\\texlive")
        if texlive_root.exists():
            candidates.extend(path for path in texlive_root.glob("*\\bin\\win32") if path.is_dir())
            candidates.extend(path for path in texlive_root.glob("*\\bin\\windows") if path.is_dir())
    else:
        candidates.extend([Path("/usr/local/bin"), Path("/usr/bin"), Path("/bin")])
        for root in (Path("/usr/local/texlive"), Path("/opt/texlive"), Path.home() / ".TinyTeX"):
            if root.exists():
                candidates.extend(path for path in root.glob("*/bin/*") if path.is_dir())

    return unique_existing_dirs(candidates)


def resolve_executable(*names: str) -> str | None:
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    for directory in candidate_tex_bin_dirs():
        for name in names:
            resolved = shutil.which(name, path=str(directory))
            if resolved:
                return resolved
    return None


def find_package_source() -> Path:
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    if not (pkg_dir / f"{PACKAGE_NAME}.cls").exists():
        raise FileNotFoundError(f"Package source not found at: {pkg_dir}")
    return pkg_dir


def get_texmfhome(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env_val = os.environ.get("TEXMFHOME")
    if env_val:
        return Path(env_val).expanduser().resolve()
    try:
        kpsewhich = resolve_executable("kpsewhich")
        if not kpsewhich:
            raise FileNotFoundError("kpsewhich not found")
        result = subprocess.run(
            [kpsewhich, "--var-value", "TEXMFHOME"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).expanduser().resolve()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "texmf"
    return Path.home() / "texmf"


def run_mktexlsr(texmfhome: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] mktexlsr {texmfhome}")
        return
    for command in ("mktexlsr", "texhash"):
        executable = resolve_executable(command)
        if executable:
            subprocess.run([executable, str(texmfhome)], check=False, capture_output=True)
            return
    initexmf = resolve_executable("initexmf")
    if initexmf:
        subprocess.run([initexmf, "--update-fndb"], check=False, capture_output=True)


def install_tree(src: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            if any(p in EXCLUDE_NAMES for p in f.parts) or f.suffix == ".pyc":
                continue
            print(f"  {f.relative_to(src)}")
        return

    dest.mkdir(parents=True, exist_ok=True)
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        if any(p in EXCLUDE_NAMES for p in f.parts) or f.suffix == ".pyc":
            continue
        target = dest / f.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)


def install_dependencies(src: Path, texmfhome: Path, dry_run: bool) -> None:
    packages_root = src.parent
    for dependency in DEPENDENCY_PACKAGE_NAMES:
        dependency_src = packages_root / dependency
        if not dependency_src.exists():
            continue
        dependency_dest = texmfhome / "tex" / "latex" / dependency
        print(f"  Dependency: {dependency_src} -> {dependency_dest}")
        install_tree(dependency_src, dependency_dest, dry_run)


def do_install(args: argparse.Namespace) -> int:
    src = find_package_source()
    texmfhome = get_texmfhome(args.texmfhome)
    dest = texmfhome / PACKAGE_SUBPATH

    print("bensz-cv — install")
    print(f"  Source : {src}")
    print(f"  Dest   : {dest}")
    if args.dry_run:
        print("  Mode   : dry-run")
    print()

    install_dependencies(src, texmfhome, args.dry_run)
    install_tree(src, dest, args.dry_run)
    run_mktexlsr(texmfhome, args.dry_run)
    return 0


def do_status(args: argparse.Namespace) -> int:
    texmfhome = get_texmfhome(args.texmfhome)
    dest = texmfhome / PACKAGE_SUBPATH
    print("bensz-cv — status")
    print()
    print(f"Package dir: {dest}")
    print(f"Exists     : {'yes' if dest.exists() else 'no'}")
    kpsewhich = resolve_executable("kpsewhich")
    if kpsewhich:
        result = subprocess.run(
            [kpsewhich, f"{PACKAGE_NAME}.cls"],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"kpsewhich  : {result.stdout.strip() or '(not found)'}")
    return 0


def do_uninstall(args: argparse.Namespace) -> int:
    texmfhome = get_texmfhome(args.texmfhome)
    dest = texmfhome / PACKAGE_SUBPATH
    print("bensz-cv — uninstall")
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
    parser = argparse.ArgumentParser(description="bensz-cv 本地安装工具")
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
