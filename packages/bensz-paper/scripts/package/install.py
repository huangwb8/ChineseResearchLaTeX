#!/usr/bin/env python3
"""
bensz-paper 版本管理安装器
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path


def _load_shared_module():
    try:
        import package_version_manager as module

        return module
    except ImportError:
        for parent in Path(__file__).resolve().parents:
            helper_dir = parent / "scripts"
            if (helper_dir / "package_version_manager.py").exists():
                sys.path.insert(0, str(helper_dir))
                import package_version_manager as module

                return module
        raise


package_version_manager = _load_shared_module()

PACKAGE_NAME = "bensz-paper"
PACKAGE_DIR = Path(__file__).resolve().parents[2]
PRIMARY_LAUNCHER = "bpaper"


def get_bin_dir(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Local" / "Programs" / PRIMARY_LAUNCHER
    return Path.home() / ".local" / "bin"


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
    import subprocess

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
            "\n".join(
                [
                    "@echo off",
                    f'set "BPAPER_SCRIPT={launcher_src}"',
                    "where py >nul 2>nul",
                    "if %ERRORLEVEL% EQU 0 (",
                    '  py -3 "%BPAPER_SCRIPT%" %*',
                    "  exit /b %ERRORLEVEL%",
                    ")",
                    'python "%BPAPER_SCRIPT%" %*',
                    "",
                ]
            ),
            encoding="utf-8",
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


def remove_launcher(bin_dir: Path, dry_run: bool) -> None:
    for name in (PRIMARY_LAUNCHER, f"{PRIMARY_LAUNCHER}.cmd"):
        launcher = bin_dir / name
        if launcher.exists() or launcher.is_symlink():
            if dry_run:
                print(f"  [dry-run] rm {launcher}")
            else:
                launcher.unlink()
                print(f"✓ Removed launcher: {launcher}")


class PaperPackageManager(package_version_manager.VersionedPackageManager):
    def __init__(
        self,
        *,
        cwd: Path | None = None,
        texmfhome_override: str | None = None,
        bin_dir_override: str | None = None,
        skip_python_deps: bool = False,
    ) -> None:
        super().__init__(
            spec=package_version_manager.PackageSpec(
                package_name=PACKAGE_NAME,
                source_marker="bensz-paper.sty",
                dependency_package_names=("bensz-fonts",),
            ),
            cwd=cwd,
            texmfhome_override=texmfhome_override,
            package_dir_override=PACKAGE_DIR,
        )
        self.bin_dir_override = bin_dir_override
        self.skip_python_deps = skip_python_deps

    def after_activate(self, commit: str, dry_run: bool = False) -> None:
        dest = self._target_install_dir()
        bin_dir = get_bin_dir(self.bin_dir_override)
        install_launcher(dest, bin_dir, dry_run)
        install_python_deps(dest, dry_run, self.skip_python_deps)

    def after_uninstall(self, dry_run: bool = False) -> None:
        remove_launcher(get_bin_dir(self.bin_dir_override), dry_run)

    def status_details(self) -> list[str]:
        lines: list[str] = []
        launcher = get_bin_dir(self.bin_dir_override) / PRIMARY_LAUNCHER
        lines.append(
            f"launcher={launcher if launcher.exists() or launcher.is_symlink() else '(missing)'}"
        )
        missing = [
            name for name in ("yaml", "docx")
            if importlib.util.find_spec(name) is None
        ]
        if missing:
            lines.append(f"python_deps=missing {', '.join(missing)}")
        else:
            lines.append("python_deps=satisfied")
        return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="bensz-paper 版本管理安装器")
    parser.add_argument("--texmfhome", metavar="PATH")
    parser.add_argument("--bin-dir", metavar="PATH")
    parser.add_argument("--skip-python-deps", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--ref", default="main")
    install_parser.add_argument("--mirror", default="github", choices=["github", "gitee", "auto"])
    install_parser.add_argument("--source", choices=["local", "github", "gitee"])
    install_parser.add_argument("--path", help="本地源码路径（仅 --source local 时使用）")
    install_parser.add_argument("--no-activate", action="store_true")
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.add_argument("--force", action="store_true")

    use_parser = subparsers.add_parser("use")
    use_parser.add_argument("--ref", required=True)
    use_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("status")

    subparsers.add_parser("check")

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--dry-run", action="store_true")

    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("--dry-run", action="store_true")

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    argv = list(sys.argv[1:] if argv is None else argv)
    commands = {"install", "use", "status", "check", "rollback", "uninstall"}
    if "--status" in argv:
        argv = ["status", *[arg for arg in argv if arg != "--status"]]
    elif "--uninstall" in argv:
        argv = ["uninstall", *[arg for arg in argv if arg != "--uninstall"]]
    elif not argv:
        argv = ["install", "--source", "local"]
    elif argv[0] not in commands and not any(arg in commands for arg in argv[1:]):
        argv = ["install", "--source", "local", *argv]

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        args = parser.parse_args(["install", "--source", "local", *argv])

    if args.command == "install" and args.source is None:
        args.source = "local" if args.path or "--ref" not in argv else "github"
    return args


def build_manager(args: argparse.Namespace) -> PaperPackageManager:
    return PaperPackageManager(
        cwd=Path.cwd(),
        texmfhome_override=getattr(args, "texmfhome", None),
        bin_dir_override=getattr(args, "bin_dir", None),
        skip_python_deps=getattr(args, "skip_python_deps", False),
    )


def print_status(manager: PaperPackageManager) -> None:
    status = manager.status()
    print("bensz-paper — status")
    print()
    print(f"Package dir: {status['package_dir']}")
    print(f"Exists     : {'yes' if status['exists'] else 'no'}")
    print(f"Current    : {json.dumps(status['current'], ensure_ascii=False) if status['current'] else '(none)'}")
    print(f"kpsewhich  : {status['kpsewhich'] or '(not found)'}")
    for line in status["details"]:
        print(f"Detail     : {line}")


def main(argv: list[str] | None = None) -> None:
    package_version_manager.configure_windows_stdio_utf8()
    args = parse_args(argv)
    manager = build_manager(args)

    try:
        if args.command in {"status", "check"}:
            print_status(manager)
            return
        if args.command == "install":
            result = manager.install(
                ref=args.ref,
                source=args.source,
                mirror=args.mirror,
                activate=not args.no_activate,
                dry_run=args.dry_run,
                force=args.force,
                path=args.path,
            )
        elif args.command == "use":
            result = manager.use(args.ref, dry_run=args.dry_run)
        elif args.command == "rollback":
            result = manager.rollback(dry_run=args.dry_run)
        elif args.command == "uninstall":
            result = manager.uninstall(dry_run=args.dry_run)
        else:
            raise package_version_manager.InstallError(f"不支持的命令：{args.command}")
    except package_version_manager.InstallError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
