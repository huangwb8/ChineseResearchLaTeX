#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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

PACKAGE_NAME = "bensz-thesis"
PACKAGE_DIR = Path(__file__).resolve().parents[2]


class ThesisPackageManager(package_version_manager.VersionedPackageManager):
    def __init__(self, *, cwd: Path | None = None, texmfhome_override: str | None = None) -> None:
        super().__init__(
            spec=package_version_manager.PackageSpec(
                package_name=PACKAGE_NAME,
                source_marker="bensz-thesis.sty",
                dependency_package_names=("bensz-fonts",),
            ),
            cwd=cwd,
            texmfhome_override=texmfhome_override,
            package_dir_override=PACKAGE_DIR,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="bensz-thesis 版本管理安装器")
    parser.add_argument("--texmfhome", metavar="PATH")
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

    args = build_parser().parse_args(argv)
    if args.command == "install" and args.source is None:
        args.source = "local" if args.path or "--ref" not in argv else "github"
    return args


def build_manager(args: argparse.Namespace) -> ThesisPackageManager:
    return ThesisPackageManager(cwd=Path.cwd(), texmfhome_override=getattr(args, "texmfhome", None))


def print_status(manager: ThesisPackageManager) -> None:
    status = manager.status()
    print("bensz-thesis — status")
    print()
    print(f"Package dir: {status['package_dir']}")
    print(f"Exists     : {'yes' if status['exists'] else 'no'}")
    print(f"Current    : {json.dumps(status['current'], ensure_ascii=False) if status['current'] else '(none)'}")
    print(f"kpsewhich  : {status['kpsewhich'] or '(not found)'}")


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
