#!/usr/bin/env python3
"""
ChineseResearchLaTeX — 统一 LaTeX 包安装器

本脚本是 ChineseResearchLaTeX 项目的统一安装入口，负责将 packages/ 下的公共 LaTeX 包
安装到用户本地 TEXMFHOME 目录。支持远程执行（``curl | python3 -``），用户无需克隆整个仓库。

支持安装的包
-----------
- bensz-fonts  : 共享字体基础包，集中托管字体资产并提供统一字体 API（直接安装到 texmf）
- bensz-nsfc   : NSFC 公共包，三套国自然模板的共享样式基础（委托安装）
- bensz-paper   : SCI 论文公共包，支持 PDF / DOCX 双输出（委托安装）
- bensz-thesis  : 毕业论文公共包，支持硕士/博士论文模板与像素级验收脚本（委托安装）
- bensz-cv      : 学术简历公共包，支持中英文简历模板与像素级验收脚本（委托安装）

安装模式
--------
- **texmfhome 模式**：直接下载仓库快照（zip），将包文件复制到 TEXMFHOME（适用于 bensz-fonts）
- **delegate 模式**：下载各包自带的 install.py 委托安装器，由后者完成实际安装逻辑；
  委托安装器依赖 ``scripts/package_version_manager.py`` 支持模块，会一并下载到临时目录

典型用法
--------
远程安装（无需克隆仓库）::

  # macOS / Linux / WSL — 安装所有公共包
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \\
    | python3 - install --ref v4.0.0

  # 使用 Gitee 镜像下载包体（脚本本身仍可从 GitHub 获取）
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \\
    | python3 - install --packages bensz-paper --mirror gitee --ref v4.0.0

  # Windows PowerShell
  (Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py' -UseBasicParsing).Content \\
    | python - install --ref v4.0.0

  # 强制重装所有公共包（即使已安装相同版本）
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \\
    | python3 - install --ref v4.0.0 --force

本地开发（在仓库根目录）::

  python3 scripts/install.py install --ref v4.0.0
  python3 scripts/install.py install --packages bensz-paper --mirror gitee --ref v4.0.0
  python3 scripts/install.py list

版本跳过机制
------------
安装前会先检查目标包的本地已安装版本与远端 package.json 中的版本：若版本一致且未指定
``--force``，则跳过重复安装，避免不必要的网络下载。
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

# GitHub / Gitee 仓库标识，用于拼接 raw 文件 URL 和仓库快照下载地址
REPO_OWNER = "huangwb8"
REPO_NAME = "ChineseResearchLaTeX"


def configure_windows_stdio_utf8() -> None:
    """在 Windows 上将 stdout / stderr 重新配置为 UTF-8 编码，避免中文输出乱码。"""
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class RemoteRepo:
    """远端代码托管仓库的连接信息（GitHub 或 Gitee）。

    Attributes:
        name: 仓库名称标识，如 ``"github"`` 或 ``"gitee"``
        raw_base: raw 文件下载基础 URL
        archive_base: 仓库快照（zip）下载 URL 模板，使用 ``{ref}`` 占位符
    """
    name: str
    raw_base: str
    archive_base: str

    def raw_url(self, ref: str, path: str) -> str:
        """拼接 raw 文件下载 URL。对 ref 中的特殊字符做 URL 编码。"""
        quoted_ref = urllib.parse.quote(ref, safe="")
        normalized = path.lstrip("/")
        return f"{self.raw_base}/{quoted_ref}/{normalized}"

    def archive_url(self, ref: str) -> str:
        """拼接仓库快照（zip archive）下载 URL。"""
        quoted_ref = urllib.parse.quote(ref, safe="")
        return self.archive_base.format(ref=quoted_ref)


SUPPORTED_PACKAGES: dict[str, dict] = {
    # 所有可安装的公共包注册表。
    # 每个条目定义了包名、安装模式（delegate / texmfhome）、仓库内路径、依赖关系等信息。
    # install_mode 含义：
    #   - "texmfhome": 直接下载仓库快照并复制到 TEXMFHOME（适用于无独立安装器的纯资源包）
    #   - "delegate": 下载包级 install.py 委托安装器，由后者完成实际安装逻辑
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
        "delegate_support_files": ["scripts/package_version_manager.py"],
    },
    "bensz-paper": {
        "installer_path": "packages/bensz-paper/scripts/package/install.py",
        "description": "SCI 论文公共包——支持 PDF / DOCX 双输出",
        "install_mode": "delegate",
        "dependencies": ["bensz-fonts"],
        "delegate_support_files": ["scripts/package_version_manager.py"],
    },
    "bensz-thesis": {
        "installer_path": "packages/bensz-thesis/scripts/package/install.py",
        "description": "毕业论文公共包——支持硕士/博士论文模板与像素级验收脚本",
        "install_mode": "delegate",
        "dependencies": ["bensz-fonts"],
        "delegate_support_files": ["scripts/package_version_manager.py"],
    },
    "bensz-cv": {
        "installer_path": "packages/bensz-cv/scripts/package/install.py",
        "description": "学术简历公共包——支持中英文简历模板与像素级验收脚本",
        "install_mode": "delegate",
        "dependencies": ["bensz-fonts"],
        "delegate_support_files": ["scripts/package_version_manager.py"],
    },
}


def default_requested_packages() -> list[str]:
    """返回所有已注册包名列表，用作 ``--packages`` 参数的默认值。"""
    return list(SUPPORTED_PACKAGES)


def should_skip_reinstall(
    installed_version: str | None,
    target_version: str | None,
    *,
    force: bool,
) -> bool:
    """判断是否应跳过重复安装。

    当本地已安装版本与目标版本一致且未指定 ``--force`` 时返回 True。
    """
    return bool(installed_version and target_version and installed_version == target_version and not force)


def build_remote_repo(mirror: str) -> RemoteRepo:
    """根据镜像名称构建对应的 RemoteRepo 实例。

    Args:
        mirror: 镜像名称，目前支持 ``"github"`` 和 ``"gitee"``

    Raises:
        ValueError: 不支持的镜像名称
    """
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
    """根据系统 locale 环境变量推断是否应优先使用 Gitee 镜像。

    当检测到 LANG / LC_ALL / LC_CTYPE / TZ 中含有 zh_cn、china 或 asia/shanghai
    等 locale 关键字时返回 True。
    """
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
    """根据 ``--mirror`` 参数返回一个或多个 RemoteRepo 实例列表。

    - ``"github"`` / ``"gitee"``: 只返回对应镜像
    - ``"auto"``: 根据 locale 自动推断优先镜像（中国大陆优先 Gitee）
    """
    if mirror in {"github", "gitee"}:
        return [build_remote_repo(mirror)]
    if mirror != "auto":
        raise ValueError(f"Unsupported mirror: {mirror}")
    ordered = ["gitee", "github"] if _prefer_gitee_for_auto() else ["github", "gitee"]
    return [build_remote_repo(name) for name in ordered]


def resolve_requested_packages(packages: list[str]) -> list[str]:
    """解析用户请求的包列表，递归展开依赖关系并去重，保持拓扑序。

    例如用户只请求 ``bensz-nsfc``，会自动补齐其依赖 ``bensz-fonts`` 并置于前面。
    """
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
    """构建 HTTP 请求头。对 GitHub URL 自动附加 ``GITHUB_TOKEN`` / ``GH_TOKEN`` 认证。"""
    headers = {"User-Agent": "ChineseResearchLaTeX-install.py"}
    if "github" in url:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_text(url: str) -> str:
    """下载 URL 内容并返回解码后的文本。失败时直接终止程序。"""
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        _die(f"下载失败：{exc.code} {url}")
    except urllib.error.URLError as exc:
        _die(f"无法访问远端：{url} — {exc.reason}")


def _try_fetch_text(url: str) -> str | None:
    """尝试下载 URL 内容。成功返回文本，失败返回 None（不终止程序）。"""
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def _fetch_bytes(url: str, dest: Path) -> None:
    """下载 URL 内容并写入目标文件。失败时直接终止程序。"""
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
    except urllib.error.HTTPError as exc:
        _die(f"下载失败：{exc.code} {url}")
    except urllib.error.URLError as exc:
        _die(f"无法下载资源：{url} — {exc.reason}")


def _try_fetch_bytes(url: str, dest: Path) -> bool:
    """尝试下载 URL 内容并写入目标文件。成功返回 True，失败返回 False。"""
    req = urllib.request.Request(url, headers=_headers(url))
    try:
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
        return True
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def _die(msg: str) -> None:
    """向 stderr 输出错误信息并终止程序（退出码 1）。"""
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def _unique_existing_dirs(paths: list[Path]) -> list[Path]:
    """对路径列表去重（解析后比较），只保留实际存在的目录。"""
    unique: list[Path] = []
    seen: set[str] = set()  # 用于去重的已解析路径集合
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
    """收集系统中可能存在 TeX 可执行文件的候选目录。

    搜索来源包括：PATH 环境变量、TEXBIN/TEXLIVE_BIN/MIKTEX_BIN 环境变量、
    各平台默认安装路径（macOS MacTeX、Windows MiKTeX/TeX Live、Linux TeX Live/TinyTeX）。
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
    """在 PATH 和候选 TeX 目录中查找可执行文件。按名称优先级依次尝试。"""
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
    """解析 TEXMFHOME 路径，优先级为：CLI 覆盖 > 环境变量 > kpsewhich > 平台默认。

    macOS 默认为 ``~/Library/texmf``，其他平台默认为 ``~/texmf``。
    """
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
    """安装完成后刷新 TeX 文件名数据库（ls-R）。

    依次尝试 mktexlsr、texhash、initexmf，返回 (状态, 命令名)。
    状态为 ``"ok"`` / ``"failed"`` / ``"missing"``。
    """
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
    """在解压后的仓库快照目录中定位仓库根目录（包含 ``packages/<package_name>`` 的目录）。"""
    candidates = [extract_root, *[path for path in extract_root.iterdir() if path.is_dir()]]
    for candidate in candidates:
        if (candidate / "packages" / package_name).exists():
            return candidate
    raise FileNotFoundError("快照中未找到仓库根目录")


def _load_package_metadata(package_dir: Path) -> dict:
    """从包目录的 ``package.json`` 中加载版本等元数据。文件不存在时返回空字典。"""
    package_json = package_dir / "package.json"
    if not package_json.exists():
        return {}
    return json.loads(package_json.read_text(encoding="utf-8"))


def _installed_package_version(package_name: str, texmfhome_override: str | None = None) -> str | None:
    """读取本地 TEXMFHOME 中已安装包的版本号（从 ``package.json`` 的 ``version`` 字段获取）。

    Returns:
        已安装版本号字符串，或 None（未安装或 metadata 损坏时）。
    """
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
    """从远端获取包的 ``package.json`` 元数据。

    按 iter_remote_repos 返回的镜像优先级依次尝试下载。

    Returns:
        成功时返回 (metadata_dict, repo_name) 元组，全部失败返回 None。
    """
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


def _check_skip_reinstall(
    package_name: str,
    ref: str,
    mirror: str,
    *,
    texmfhome_override: str | None = None,
    force: bool = False,
) -> tuple[str, str] | None:
    """检查是否可以跳过重复安装。

    对比远端 package.json 中的版本与本地已安装版本：若一致且未指定 ``--force``，
    返回 (installed_version, mirror_name) 表示应跳过；否则返回 None 表示需要安装。
    """
    remote_metadata_result = _fetch_remote_package_metadata(package_name, ref, mirror)
    if remote_metadata_result is None:
        return None

    remote_metadata, metadata_mirror = remote_metadata_result
    target_version = remote_metadata.get("version")
    installed_version = _installed_package_version(package_name, texmfhome_override)
    if not should_skip_reinstall(installed_version, target_version, force=force):
        return None
    return installed_version, metadata_mirror


def _download_delegate_support_files(package_name: str, temp_dir: Path, mirror: str) -> None:
    """为委托安装模式下载额外的支持文件（如 ``package_version_manager.py``）。

    这些文件会被保存到临时目录，以便委托安装器通过 PYTHONPATH 引用。
    文件始终从 ``main`` 分支下载（而非用户指定的 ``--ref``），因为这些是通用工具模块。
    """
    support_files = SUPPORTED_PACKAGES[package_name].get("delegate_support_files", [])
    if not support_files:
        return

    for relative_path in support_files:
        content = None
        for repo in iter_remote_repos(mirror):
            content = _try_fetch_text(repo.raw_url("main", relative_path))
            if content is not None:
                break
        if content is None:
            _die(f"无法下载 {package_name} 委托安装依赖：{relative_path}")
        destination = temp_dir / Path(relative_path).name
        destination.write_text(content, encoding="utf-8")


def _install_delegated_package(
    package_name: str,
    ref: str,
    extra: list[str],
    mirror: str,
    texmfhome: str | None = None,
    force: bool = False,
) -> None:
    """以委托模式安装一个公共包。

    委托安装原理：
    1. 从远端下载该包自带的 ``install.py``（如 ``packages/bensz-nsfc/scripts/install.py``）
    2. 同时下载 ``scripts/package_version_manager.py`` 支持模块到同一临时目录
    3. 在子进程中执行委托安装器，透传 ``--ref``、``--mirror``、``--force`` 等参数
    4. 将临时目录加入 PYTHONPATH，使委托安装器能 import 支持模块
    5. 安装完成后自动清理临时目录

    Args:
        package_name: 包名，如 ``"bensz-nsfc"``
        ref: 版本 tag 或分支名
        extra: 透传给委托安装器的额外 CLI 参数
        mirror: 下载镜像（github / gitee / auto）
        texmfhome: 自定义 TEXMFHOME 路径
        force: 是否强制重装
    """
    skip_result = _check_skip_reinstall(
        package_name,
        ref,
        mirror,
        texmfhome_override=texmfhome,
        force=force,
    )
    if skip_result is not None:
        installed_version, metadata_mirror = skip_result
        print(
            "  ⏭️  检测到已安装相同版本："
            f"{package_name} {installed_version}（ref={ref}, source={metadata_mirror}），跳过重复安装"
        )
        return

    installer_path = SUPPORTED_PACKAGES[package_name]["installer_path"]
    content = None
    chosen_repo = None
    for repo in iter_remote_repos(mirror):
        url = repo.raw_url("main", installer_path)
        content = _try_fetch_text(url)
        if content is not None:
            chosen_repo = repo
            break

    if content is None or chosen_repo is None:
        _die(f"无法下载 {package_name} 安装器，请检查网络或改用 --mirror github/gitee")

    print(f"  📥 下载 {package_name} 安装器（{chosen_repo.name}）…")
    # 将委托安装器和支持模块下载到临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix=f"{package_name}-installer-"))
    installer = temp_dir / "installer.py"
    installer.write_text(content, encoding="utf-8")
    _download_delegate_support_files(package_name, temp_dir, chosen_repo.name)

    try:
        # 构建委托安装器的命令行参数
        cmd = [sys.executable, str(installer)]
        if texmfhome:
            cmd.extend(["--texmfhome", texmfhome])
        cmd.extend(["install", "--ref", ref, "--mirror", mirror])
        if force:
            cmd.append("--force")
        cmd += extra
        print(f"  ▶ {' '.join(cmd)}")
        # 将临时目录加入 PYTHONPATH，使委托安装器能 import package_version_manager 等支持模块
        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp_dir) + os.pathsep + env.get("PYTHONPATH", "")
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        _die(f"{package_name} 安装失败（退出码 {exc.returncode}）")
    finally:
        # 无论安装成功与否，都清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def _copy_package_tree(pkg_src: Path, dest: Path) -> int:
    """递归复制包目录下的所有文件到目标路径，自动跳过 __pycache__、.DS_Store 和 .pyc。

    Returns:
        复制的文件数量。
    """
    copied = 0
    for path in pkg_src.rglob("*"):
        if not path.is_file():
            continue
        # 跳过 Python 缓存和 macOS 系统文件
        if any(part in {"__pycache__", ".DS_Store"} for part in path.parts) or path.suffix == ".pyc":
            continue
        target = dest / path.relative_to(pkg_src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def _download_repo_snapshot(package_name: str, ref: str, mirror: str) -> tuple[Path, Path, str]:
    """下载仓库快照（zip archive）并解压，定位目标包目录。

    按镜像优先级依次尝试下载；成功后解压并查找 ``packages/<package_name>`` 目录。

    Returns:
        (临时目录 Path, 包源目录 Path, 实际使用的镜像名) 元组。

    Raises:
        SystemExit: 所有镜像均下载失败时终止程序。
    """
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
    """以 texmfhome 模式直接安装一个公共包。

    安装流程：
    1. 解析 TEXMFHOME 路径
    2. 检查是否需要跳过（已安装相同版本且未指定 ``--force``）
    3. 下载仓库快照（zip），解压并定位包目录
    4. 再次检查版本（快照内 package.json 的版本可能与远端 metadata 一致）
    5. 清空目标目录并递归复制包文件
    6. 刷新 TeX 文件名数据库（mktexlsr / texhash / initexmf）

    适用于没有独立安装器的纯资源包（如 bensz-fonts）。

    Args:
        package_name: 包名
        ref: 版本 tag 或分支名
        mirror: 下载镜像（github / gitee / auto）
        texmfhome_override: 自定义 TEXMFHOME 路径
        force: 是否强制重装
    """
    texmfhome = _texmfhome(texmfhome_override)
    skip_result = _check_skip_reinstall(
        package_name,
        ref,
        mirror,
        texmfhome_override=texmfhome_override,
        force=force,
    )
    if skip_result is not None:
        installed_version, metadata_mirror = skip_result
        print(
            "  ⏭️  检测到已安装相同版本："
            f"{package_name} {installed_version}（ref={ref}, source={metadata_mirror}），跳过重复安装"
        )
        return

    print(f"  📥 下载仓库快照（{ref}）…")
    tmp_dir, pkg_src, actual_mirror = _download_repo_snapshot(package_name, ref, mirror)
    try:
        # 快照下载成功后再次检查版本（用快照内的 package.json，避免快照与 metadata 不一致）
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
            shutil.rmtree(dest)  # 清空旧版本目录
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
    """列出所有支持安装的 LaTeX 公共包，显示包名、描述和依赖关系，附带安装示例命令。"""
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
    """执行安装流程：解析依赖 → 逐包安装。

    安装流程：
    1. 调用 ``resolve_requested_packages()`` 展开依赖关系，得到拓扑有序的安装列表
    2. 遍历每个包，根据其 ``install_mode`` 选择安装方式：
       - ``delegate``: 调用 ``_install_delegated_package()`` 下载委托安装器并执行
       - ``texmfhome``: 调用 ``_install_texmf_package()`` 直接复制到 TEXMFHOME
    3. 全部完成后打印成功信息

    Args:
        packages: 用户请求的包名列表（不含依赖展开）
        ref: 版本 tag 或分支名
        extra: 透传给委托安装器的额外参数
        mirror: 下载镜像（github / gitee / auto）
        texmfhome: 自定义 TEXMFHOME 路径
        force: 是否强制重装
    """
    ordered_packages = resolve_requested_packages(packages)
    if ordered_packages != packages:
        print(f"ℹ️  自动补齐依赖后的安装顺序：{', '.join(ordered_packages)}")

    for pkg in ordered_packages:
        info = SUPPORTED_PACKAGES[pkg]
        print(f"\n{'=' * 50}")
        print(f"📦 安装 {pkg}：{info['description']}")
        print(f"{'=' * 50}")

        if info["install_mode"] == "delegate":
            _install_delegated_package(pkg, ref, extra, mirror, texmfhome=texmfhome, force=force)
        elif info["install_mode"] == "texmfhome":
            _install_texmf_package(pkg, ref, mirror, texmfhome_override=texmfhome, force=force)

    print(f"\n{'=' * 50}")
    print("✅ 所有包安装完成！")
    print(f"{'=' * 50}")


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器，支持 ``list`` 和 ``install`` 两个子命令。"""
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
        help="透传给委托安装器的额外参数（对 bensz-nsfc / bensz-paper / bensz-thesis / bensz-cv 有效）",
    )

    return parser


def main() -> None:
    """CLI 入口函数：解析命令行参数并分派到对应子命令（list / install）。"""
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
