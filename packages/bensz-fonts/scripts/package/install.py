#!/usr/bin/env python3
"""bensz-fonts 字体基础包安装器。

将 ``packages/bensz-fonts/`` 中的字体资产安装到用户本地 TEXMFHOME 目录。
采用 texmfhome 模式（直接复制文件），不依赖 package_version_manager 框架。

字体包是其他 bensz-* 包的基础依赖，通常应最先安装。

典型用法::

    python install.py install           # 从本地仓库安装
    python install.py install --ref v4.0.0  # 从远程仓库安装指定版本
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "bensz-fonts"
# 安装到 TEXMFHOME 下的子路径
PACKAGE_SUBPATH = Path("tex") / "latex" / PACKAGE_NAME
# 复制文件树时跳过的目录和文件名
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def unique_existing_dirs(paths: list[Path]) -> list[Path]:
    """对路径列表去重并过滤不存在的目录，Windows 下不区分大小写。"""
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
    """收集系统中所有可能的 TeX 可执行文件目录候选。

    搜索来源包括：PATH 环境变量、TEXBIN/TEXLIVE_BIN/MIKTEX_BIN 环境变量、
    以及各平台（macOS/Windows/Linux）的常见 TeX 发行版安装路径。
    """
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
    """在 PATH 和 candidate_tex_bin_dirs 中查找可执行文件，返回第一个匹配的完整路径。"""
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
    """定位 bensz-fonts 源码根目录（从本脚本向上三级，即 packages/bensz-fonts/）。"""
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    if not (pkg_dir / f"{PACKAGE_NAME}.sty").exists():
        raise FileNotFoundError(f"Package source not found at: {pkg_dir}")
    return pkg_dir


def get_texmfhome(override: str | None = None) -> Path:
    """解析 TEXMFHOME 路径，优先级：显式参数 > 环境变量 > kpsewhich 查询 > 平台默认值。"""
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
    """刷新 TeX 文件名数据库，依次尝试 mktexlsr、texhash（TeX Live）或 initexmf（MiKTeX）。"""
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
    """将源码目录树递归复制到目标路径，排除 __pycache__、.DS_Store 和 .pyc 文件。

    dry-run 模式下仅打印将要复制的文件列表。
    """
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
    """执行安装：将 bensz-fonts 源码复制到 TEXMFHOME 并刷新文件名数据库。

    Args:
        args: 命令行参数，包含 texmfhome（可选覆盖路径）和 dry_run 标志。

    Returns:
        退出码，0 表示成功。
    """
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
    """检查 bensz-fonts 安装状态：目标目录是否存在、kpsewhich 是否能发现 .sty 文件。

    Args:
        args: 命令行参数，包含 texmfhome（可选覆盖路径）。

    Returns:
        退出码，0 表示成功。
    """
    texmfhome = get_texmfhome(args.texmfhome)
    dest = texmfhome / PACKAGE_SUBPATH
    print("bensz-fonts — status")
    print()
    print(f"Package dir: {dest}")
    print(f"Exists     : {'yes' if dest.exists() else 'no'}")
    kpsewhich = resolve_executable("kpsewhich")
    if kpsewhich:
        result = subprocess.run(
            [kpsewhich, f"{PACKAGE_NAME}.sty"],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"kpsewhich  : {result.stdout.strip() or '(not found)'}")
    return 0


def do_uninstall(args: argparse.Namespace) -> int:
    """卸载 bensz-fonts：删除 TEXMFHOME 下的安装目录并刷新文件名数据库。

    Args:
        args: 命令行参数，包含 texmfhome（可选覆盖路径）和 dry_run 标志。

    Returns:
        退出码，0 表示成功。
    """
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
    """解析命令行参数：默认执行安装，--status 查看状态，--uninstall 卸载。"""
    parser = argparse.ArgumentParser(description="bensz-fonts 本地安装工具")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--status", action="store_true", help="检查安装状态")
    action.add_argument("--uninstall", action="store_true", help="卸载")
    parser.add_argument("--dry-run", action="store_true", help="预览，不实际写入")
    parser.add_argument("--texmfhome", metavar="PATH", help="覆盖 TEXMFHOME 路径")
    return parser.parse_args()


def main() -> None:
    """CLI 入口：根据参数分发到 install/status/uninstall 操作。"""
    args = parse_args()
    if args.status:
        sys.exit(do_status(args))
    if args.uninstall:
        sys.exit(do_uninstall(args))
    sys.exit(do_install(args))


if __name__ == "__main__":
    main()
