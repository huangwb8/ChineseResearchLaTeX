#!/usr/bin/env python3
"""bensz-paper 版本管理安装器。

基于 ``scripts/package_version_manager.py`` 提供的 VersionedPackageManager 框架，
实现 bensz-paper 公共包的安装、卸载、版本切换、回退与状态查询。

也可通过根级统一安装器 ``scripts/install.py`` 以 delegate 模式间接调用。

子命令：install / uninstall / use / rollback / check / clean / list

典型用法::

    python install.py install --ref v1.3.5
    python install.py install --ref main --mirror gitee
    python install.py rollback
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
    """动态加载 package_version_manager 模块。

    优先尝试 import，失败后沿父目录向上搜索 scripts/package_version_manager.py。
    这使得 install.py 既可以在仓库内直接运行，也可以作为独立脚本分发。
    """
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
# 包源码根目录：install.py 位于 scripts/package/ 下，向上两级即为 packages/bensz-paper/
PACKAGE_DIR = Path(__file__).resolve().parents[2]
# 命令行 launcher 名称，安装后用户可通过 bpaper 命令调用构建工具
PRIMARY_LAUNCHER = "bpaper"


def get_bin_dir(override: str | None = None) -> Path:
    """解析 launcher 安装目标目录。优先使用 override 参数，否则按平台选择默认路径。"""
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Local" / "Programs" / PRIMARY_LAUNCHER
    return Path.home() / ".local" / "bin"


def install_python_deps(dest: Path, dry_run: bool, skip: bool) -> None:
    """检查并安装 bensz-paper 所需的 Python 依赖（pyyaml、python-docx）。

    仅当 requirements.txt 存在且 importlib 检测到缺失模块时才执行 pip install。
    在非虚拟环境中自动添加 --user 标志。
    """
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
    """创建 bpaper 命令行 launcher。

    macOS/Linux：创建符号链接 bin_dir/bpaper -> dest/bpaper。
    Windows：生成 .cmd 批处理文件，优先使用 py -3 启动器。
    """
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
    """移除 bpaper launcher（符号链接和 .cmd 文件都会清理）。"""
    for name in (PRIMARY_LAUNCHER, f"{PRIMARY_LAUNCHER}.cmd"):
        launcher = bin_dir / name
        if launcher.exists() or launcher.is_symlink():
            if dry_run:
                print(f"  [dry-run] rm {launcher}")
            else:
                launcher.unlink()
                print(f"✓ Removed launcher: {launcher}")


class PaperPackageManager(package_version_manager.VersionedPackageManager):
    """bensz-paper 专用版本管理器。

    继承 VersionedPackageManager 基类，实现以下扩展：
    - after_activate：安装完成后创建 launcher 和安装 Python 依赖。
    - after_uninstall：卸载后清理 launcher。
    - status_details：报告 launcher 状态和 Python 依赖满足情况。

    包依赖声明：bensz-paper 依赖 bensz-fonts 字体包。
    """
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
        """安装激活后的钩子：创建命令行 launcher 并检查 Python 依赖。"""
        dest = self._target_install_dir()
        bin_dir = get_bin_dir(self.bin_dir_override)
        install_launcher(dest, bin_dir, dry_run)
        install_python_deps(dest, dry_run, self.skip_python_deps)

    def after_uninstall(self, dry_run: bool = False) -> None:
        """卸载后的钩子：移除命令行 launcher。"""
        remove_launcher(get_bin_dir(self.bin_dir_override), dry_run)

    def status_details(self) -> list[str]:
        """返回额外的状态信息行，用于 status/check 子命令的输出。"""
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
    """构建命令行参数解析器，定义 install/use/status/check/rollback/uninstall 六个子命令。"""
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
    """解析命令行参数，兼容旧版 --status / --uninstall 标志式调用。

    无参数时默认执行 install --source local（仓库内开发模式）。
    """
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
    """根据命令行参数构建 PaperPackageManager 实例。"""
    return PaperPackageManager(
        cwd=Path.cwd(),
        texmfhome_override=getattr(args, "texmfhome", None),
        bin_dir_override=getattr(args, "bin_dir", None),
        skip_python_deps=getattr(args, "skip_python_deps", False),
    )


def print_status(manager: PaperPackageManager) -> None:
    """打印 bensz-paper 的安装状态摘要（路径、版本、kpsewhich 结果、launcher 状态）。"""
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
    """命令行入口：分发到对应子命令并输出结果 JSON。"""
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
