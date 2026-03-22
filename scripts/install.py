#!/usr/bin/env python3
"""
ChineseResearchLaTeX — 统一 LaTeX 包安装器

支持远程执行（无需克隆仓库）：

  # macOS / Linux / WSL
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \
    | python3 - install --ref v4.0.0

  # 使用 Gitee 镜像下载包体（脚本本身仍可从 GitHub 获取）
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \
    | python3 - install --packages bensz-paper --mirror gitee --ref v4.0.0

  # 强制重装所有公共包
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \
    | python3 - install --ref v4.0.0 --force

也可本地执行（在仓库根目录）：
  python3 scripts/install.py install --ref v4.0.0
  python3 scripts/install.py install --packages bensz-paper --mirror gitee --ref v4.0.0
  python3 scripts/install.py list
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO_OWNER = "huangwb8"
REPO_NAME = "ChineseResearchLaTeX"


def configure_windows_stdio_utf8() -> None:
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class RemoteRepo:
    name: str
    raw_base: str
    archive_base: str

    def raw_url(self, ref: str, path: str) -> str:
        quoted_ref = urllib.parse.quote(ref, safe="")
        normalized = path.lstrip("/")
        return f"{self.raw_base}/{quoted_ref}/{normalized}"

    def archive_url(self, ref: str) -> str:
        quoted_ref = urllib.parse.quote(ref, safe="")
        return self.archive_base.format(ref=quoted_ref)


SUPPORTED_PACKAGES: dict[str, dict] = {
    "bensz-fonts": {
        "installer_path": None,
        "description": "共享字体基础包——集中托管字体资产并提供统一字体 API",
        "install_mode": "texmfhome",
        "package_subdir": "packages/bensz-fonts",
        "dependencies": [],
    },
    "bensz-nsfc": {
        "installer_path": "packages/bensz-nsfc/scripts/install.py",
        "description": "NSFC 公共包——三套国自然模板的共享样式基础",
        "install_mode": "delegate",
        "dependencies": ["bensz-fonts"],
    },
    "bensz-paper": {
        "installer_path": None,
        "description": "SCI 论文公共包——支持 PDF / DOCX 双输出",
        "install_mode": "texmfhome",
        "package_subdir": "packages/bensz-paper",
        "dependencies": ["bensz-fonts"],
    },
    "bensz-thesis": {
        "installer_path": None,
        "description": "毕业论文公共包——支持硕士/博士论文模板与像素级验收脚本",
        "install_mode": "texmfhome",
        "package_subdir": "packages/bensz-thesis",
        "dependencies": ["bensz-fonts"],
    },
    "bensz-cv": {
        "installer_path": None,
        "description": "学术简历公共包——支持中英文简历模板与像素级验收脚本",
        "install_mode": "texmfhome",
        "package_subdir": "packages/bensz-cv",
        "dependencies": ["bensz-fonts"],
    },
}


def default_requested_packages() -> list[str]:
    return list(SUPPORTED_PACKAGES)


def should_skip_reinstall(
    installed_version: str | None,
    target_version: str | None,
    *,
    force: bool,
) -> bool:
    return bool(installed_version and target_version and installed_version == target_version and not force)


def build_remote_repo(mirror: str) -> RemoteRepo:
    if mirror == "github":
        return RemoteRepo(
            name="github",
            raw_base=f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}",
            archive_base=f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/zipball/{{ref}}",
        )
    if mirror == "gitee":
        return RemoteRepo(
            name="gitee",
            raw_base=f"https://gitee.com/{REPO_OWNER}/{REPO_NAME}/raw",
            archive_base=f"https://gitee.com/{REPO_OWNER}/{REPO_NAME}/repository/archive/{{ref}}.zip",
        )
    raise ValueError(f"Unsupported mirror: {mirror}")


def _prefer_gitee_for_auto() -> bool:
    locale_hint = " ".join(
        value
        for value in (
            os.environ.get("LANG", ""),
            os.environ.get("LC_ALL", ""),
            os.environ.get("LC_CTYPE", ""),
            os.environ.get("TZ", ""),
        )
        if value
    ).lower()
    return any(token in locale_hint for token in ("zh_cn", "china", "asia/shanghai"))


def iter_remote_repos(mirror: str) -> list[RemoteRepo]:
    if mirror in {"github", "gitee"}:
        return [build_remote_repo(mirror)]
    if mirror != "auto":
        raise ValueError(f"Unsupported mirror: {mirror}")
    ordered = ["gitee", "github"] if _prefer_gitee_for_auto() else ["github", "gitee"]
    return [build_remote_repo(name) for name in ordered]


def resolve_requested_packages(packages: list[str]) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()

    def add_package(name: str) -> None:
        if name not in SUPPORTED_PACKAGES:
            _die(f"不支持的包名：{name}。可选：{', '.join(SUPPORTED_PACKAGES)}")
        for dependency in SUPPORTED_PACKAGES[name].get("dependencies", []):
            add_package(dependency)
        if name not in seen:
            resolved.append(name)
            seen.add(name)

    for package in packages:
        add_package(package)
    return resolved


def _headers(url: str) -> dict[str, str]:
    headers = {"User-Agent": "ChineseResearchLaTeX-install.py"}
    if "github" in url:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        _die(f"下载失败：{exc.code} {url}")
    except urllib.error.URLError as exc:
        _die(f"无法访问远端：{url} — {exc.reason}")


def _try_fetch_text(url: str) -> str | None:
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def _fetch_bytes(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
    except urllib.error.HTTPError as exc:
        _die(f"下载失败：{exc.code} {url}")
    except urllib.error.URLError as exc:
        _die(f"无法下载资源：{url} — {exc.reason}")


def _try_fetch_bytes(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
        return True
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def _die(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def _unique_existing_dirs(paths: list[Path]) -> list[Path]:
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


def _candidate_tex_bin_dirs() -> list[Path]:
    candidates: list[Path] = []
    path_env = os.environ.get("PATH", "")
    candidates.extend(Path(item) for item in path_env.split(os.pathsep) if item)

    for env_name in ("TEXBIN", "TEXLIVE_BIN", "MIKTEX_BIN"):
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(Path(env_value))

    system = platform.system()
    if system == "Darwin":
        candidates.extend(
            [
                Path("/Library/TeX/texbin"),
                Path("/usr/local/bin"),
                Path("/opt/homebrew/bin"),
            ]
        )
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

    return _unique_existing_dirs(candidates)


def _resolve_executable(*names: str) -> str | None:
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    for directory in _candidate_tex_bin_dirs():
        for name in names:
            resolved = shutil.which(name, path=str(directory))
            if resolved:
                return resolved
    return None


def _texmfhome(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env_value = os.environ.get("TEXMFHOME")
    if env_value:
        return Path(env_value).expanduser().resolve()
    try:
        kpsewhich = _resolve_executable("kpsewhich")
        if not kpsewhich:
            raise FileNotFoundError("kpsewhich not found")
        result = subprocess.run(
            [kpsewhich, "--var-value=TEXMFHOME"],
            capture_output=True,
            text=True,
            check=True,
        )
        path = Path(result.stdout.strip())
        if path != Path(""):
            return path.expanduser().resolve()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "texmf"
    return Path.home() / "texmf"


def _refresh_texmf(texmfhome: Path) -> tuple[str, str]:
    attempted = False
    for command in ("mktexlsr", "texhash"):
        executable = _resolve_executable(command)
        if not executable:
            continue
        attempted = True
        try:
            subprocess.run(
                [executable, str(texmfhome)],
                check=True,
                capture_output=True,
                text=True,
            )
            return "ok", command
        except subprocess.CalledProcessError:
            continue
    initexmf = _resolve_executable("initexmf")
    if initexmf:
        attempted = True
        try:
            subprocess.run(
                [initexmf, "--update-fndb"],
                check=True,
                capture_output=True,
                text=True,
            )
            return "ok", "initexmf"
        except subprocess.CalledProcessError:
            pass
    if attempted:
        return "failed", ""
    return "missing", ""


def _locate_repo_root(extract_root: Path, package_name: str) -> Path:
    candidates = [extract_root, *[path for path in extract_root.iterdir() if path.is_dir()]]
    for candidate in candidates:
        if (candidate / "packages" / package_name).exists():
            return candidate
    raise FileNotFoundError("快照中未找到仓库根目录")


def _load_package_metadata(package_dir: Path) -> dict:
    package_json = package_dir / "package.json"
    if not package_json.exists():
        return {}
    return json.loads(package_json.read_text(encoding="utf-8"))


def _installed_package_version(package_name: str, texmfhome_override: str | None = None) -> str | None:
    package_json = _texmfhome(texmfhome_override) / "tex" / "latex" / package_name / "package.json"
    if not package_json.exists():
        return None
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    version = payload.get("version")
    return str(version) if version else None


def _fetch_remote_package_metadata(package_name: str, ref: str, mirror: str) -> tuple[dict, str] | None:
    raw_path = f"packages/{package_name}/package.json"
    for repo in iter_remote_repos(mirror):
        content = _try_fetch_text(repo.raw_url(ref, raw_path))
        if content is None:
            continue
        try:
            return json.loads(content), repo.name
        except json.JSONDecodeError:
            continue
    return None


def _install_bensz_nsfc(
    ref: str,
    extra: list[str],
    mirror: str,
    texmfhome: str | None = None,
    force: bool = False,
) -> None:
    content = None
    chosen_repo = None
    for repo in iter_remote_repos(mirror):
        url = repo.raw_url("main", "packages/bensz-nsfc/scripts/install.py")
        content = _try_fetch_text(url)
        if content is not None:
            chosen_repo = repo
            break

    if content is None or chosen_repo is None:
        _die("无法下载 bensz-nsfc 安装器，请检查网络或改用 --mirror github/gitee")

    print(f"  📥 下载 bensz-nsfc 安装器（{chosen_repo.name}）…")
    with tempfile.NamedTemporaryFile(
        suffix=".py",
        delete=False,
        mode="w",
        encoding="utf-8",
        prefix="bensz-nsfc-installer-",
    ) as temp_file:
        temp_file.write(content)
        installer = temp_file.name

    try:
        cmd = [sys.executable, installer]
        if texmfhome:
            cmd.extend(["--texmfhome", texmfhome])
        cmd.extend(["install", "--ref", ref, "--mirror", mirror])
        if force:
            cmd.append("--force")
        cmd += extra
        print(f"  ▶ {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        _die(f"bensz-nsfc 安装失败（退出码 {exc.returncode}）")
    finally:
        os.unlink(installer)


def _copy_package_tree(pkg_src: Path, dest: Path) -> int:
    copied = 0
    for path in pkg_src.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".DS_Store"} for part in path.parts) or path.suffix == ".pyc":
            continue
        target = dest / path.relative_to(pkg_src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def _download_repo_snapshot(package_name: str, ref: str, mirror: str) -> tuple[Path, Path, str]:
    last_error = None
    for repo in iter_remote_repos(mirror):
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"{package_name}-install-"))
        archive = tmp_dir / "snapshot.zip"
        extract = tmp_dir / "extract"
        if not _try_fetch_bytes(repo.archive_url(ref), archive):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            last_error = f"{repo.name}:{repo.archive_url(ref)}"
            continue

        try:
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extract)
            repo_root = _locate_repo_root(extract, package_name)
            package_dir = repo_root / "packages" / package_name
            if not package_dir.exists():
                raise FileNotFoundError(f"快照中缺少 packages/{package_name} 目录")
            return tmp_dir, package_dir, repo.name
        except Exception as exc:  # noqa: BLE001
            shutil.rmtree(tmp_dir, ignore_errors=True)
            last_error = f"{repo.name}:{exc}"

    _die(f"无法下载 {package_name}（ref={ref}, mirror={mirror}）。最后错误：{last_error}")


def _install_texmf_package(
    package_name: str,
    ref: str,
    mirror: str,
    texmfhome_override: str | None = None,
    force: bool = False,
) -> None:
    texmfhome = _texmfhome(texmfhome_override)
    remote_metadata_result = _fetch_remote_package_metadata(package_name, ref, mirror)
    if remote_metadata_result is not None:
        remote_metadata, metadata_mirror = remote_metadata_result
        target_version = remote_metadata.get("version")
        installed_version = _installed_package_version(package_name, texmfhome_override)
        if should_skip_reinstall(installed_version, target_version, force=force):
            print(
                "  ⏭️  检测到已安装相同版本："
                f"{package_name} {installed_version}（ref={ref}, source={metadata_mirror}），跳过重复安装"
            )
            return

    print(f"  📥 下载仓库快照（{ref}）…")
    tmp_dir, pkg_src, actual_mirror = _download_repo_snapshot(package_name, ref, mirror)
    try:
        package_metadata = _load_package_metadata(pkg_src)
        target_version = package_metadata.get("version")
        installed_version = _installed_package_version(package_name, texmfhome_override)
        if should_skip_reinstall(installed_version, target_version, force=force):
            print(
                "  ⏭️  检测到已安装相同版本："
                f"{package_name} {installed_version}（ref={ref}, source={actual_mirror}），跳过重复安装"
            )
            return
        dest = texmfhome / "tex" / "latex" / package_name
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        copied = _copy_package_tree(pkg_src, dest)

        print(f"  ✔ 已从 {actual_mirror} 复制 {copied} 个文件到 {dest}")
        refresh_status, refresh_command = _refresh_texmf(texmfhome)
        if refresh_status == "ok":
            print(f"  ✔ {refresh_command} 已刷新")
        elif refresh_status == "missing":
            print("  ℹ️  未找到 `mktexlsr` / `texhash` / `initexmf`，请手动刷新 TeX 文件数据库")
        else:
            print("  ⚠️  `mktexlsr` / `texhash` / `initexmf` 执行失败，请手动刷新 TeX 文件数据库")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def cmd_list() -> None:
    print("支持的 LaTeX 包（来自 packages/ 目录）：\n")
    for name, info in SUPPORTED_PACKAGES.items():
        deps = info.get("dependencies", [])
        dependency_note = f"（依赖：{', '.join(deps)}）" if deps else ""
        print(f"  {name}")
        print(f"    {info['description']} {dependency_note}".rstrip())
    print()
    print("安装示例：")
    print("  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \\")
    print("    | python3 - install --ref v4.0.0")
    print("  python3 scripts/install.py install --ref v4.0.0 --force")
    print("  python3 scripts/install.py install --packages bensz-paper --mirror gitee --ref v4.0.0")


def cmd_install(
    packages: list[str],
    ref: str,
    extra: list[str],
    mirror: str,
    texmfhome: str | None = None,
    force: bool = False,
) -> None:
    ordered_packages = resolve_requested_packages(packages)
    if ordered_packages != packages:
        print(f"ℹ️  自动补齐依赖后的安装顺序：{', '.join(ordered_packages)}")

    for pkg in ordered_packages:
        info = SUPPORTED_PACKAGES[pkg]
        print(f"\n{'=' * 50}")
        print(f"📦 安装 {pkg}：{info['description']}")
        print(f"{'=' * 50}")

        if info["install_mode"] == "delegate":
            _install_bensz_nsfc(ref, extra, mirror, texmfhome=texmfhome, force=force)
        elif info["install_mode"] == "texmfhome":
            _install_texmf_package(pkg, ref, mirror, texmfhome_override=texmfhome, force=force)

    print(f"\n{'=' * 50}")
    print("✅ 所有包安装完成！")
    print(f"{'=' * 50}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ChineseResearchLaTeX 统一 LaTeX 包安装器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="列出所有支持安装的包")

    inst = sub.add_parser("install", help="安装一个或多个包")
    inst.add_argument(
        "--packages",
        default=",".join(default_requested_packages()),
        help="要安装的包，逗号分隔（默认：安装所有公共包）。可选：bensz-fonts,bensz-nsfc,bensz-paper,bensz-thesis,bensz-cv",
    )
    inst.add_argument(
        "--ref",
        default="main",
        help="版本 tag 或分支，例如 v4.0.0（默认：main）",
    )
    inst.add_argument(
        "--mirror",
        choices=("github", "gitee", "auto"),
        default="github",
        help="下载镜像，默认 github；中国大陆可显式传 --mirror gitee",
    )
    inst.add_argument(
        "--texmfhome",
        help="覆盖 TEXMFHOME 安装目录；当 TeX 未加入 PATH 或需安装到自定义 texmf 树时使用",
    )
    inst.add_argument(
        "--force",
        action="store_true",
        help="即使检测到已安装相同版本，也强制重新安装",
    )
    inst.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="透传给子安装器的额外参数（仅 bensz-nsfc 有效）",
    )

    return parser


def main() -> None:
    configure_windows_stdio_utf8()
    parser = build_parser()

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "install":
        requested = [item.strip() for item in args.packages.split(",") if item.strip()]
        cmd_install(
            requested,
            args.ref,
            args.extra or [],
            args.mirror,
            texmfhome=args.texmfhome,
            force=args.force,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
