#!/usr/bin/env python3
"""
[已弃用] NSFC 公共包旧版安装/版本管理入口。

本文件已弃用，仅作为向后兼容保留。请使用以下替代入口：

- 包级安装器：``packages/bensz-nsfc/scripts/package/install.py``
- 根级统一安装器：``scripts/install.py``（支持远程执行，可同时安装多个 bensz-* 包）

旧版入口的核心逻辑仍在本文件中维护，新功能应优先添加到 ``package/install.py``。
"""
from __future__ import annotations

import argparse
import hashlib
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_OWNER = "huangwb8"  # GitHub / Gitee 仓库所有者
REPO_NAME = "ChineseResearchLaTeX"  # 仓库名称
PACKAGE_SLUG = "bensz-nsfc"  # 包目录名，同时用作安装目标子目录名
PACKAGE_NAME = "bensz-nsfc-common"  # 核心宏包名（对应 .sty 文件前缀）
DEPENDENCY_PACKAGE_SLUGS = ("bensz-fonts",)  # 安装时需一并处理的依赖包
PACKAGE_SOURCE_RELATIVE = Path("packages") / PACKAGE_SLUG  # 包在仓库中的相对路径
LOCKFILE_NAME = ".nsfc-version"  # 项目级版本锁定文件名
PACKAGE_DIR = Path(__file__).resolve().parents[1]  # 本脚本所在包的根目录（packages/bensz-nsfc/）


def get_project_state_home() -> Path:
    """返回项目级状态目录 ``~/.ChineseResearchLaTeX/``，用于集中存放各 bensz-* 包的缓存与状态。"""
    return Path.home() / ".ChineseResearchLaTeX"


def should_skip_reinstall(
    installed_version: str | None,
    target_version: str | None,
    *,
    force: bool,
) -> bool:
    """判断是否应跳过重复安装。当已安装版本与目标版本一致且未强制覆盖时返回 True。"""
    return bool(installed_version and target_version and installed_version == target_version and not force)


def discover_repo_root() -> Path:
    """从 PACKAGE_DIR 向上搜索，定位包含 ``packages/bensz-nsfc/package.json`` 的仓库根目录。若未找到则回退到上两级目录。"""
    for candidate in [PACKAGE_DIR, *PACKAGE_DIR.parents]:
        if (candidate / "packages" / PACKAGE_SLUG / "package.json").exists():
            return candidate
    return PACKAGE_DIR.parents[1]


def unique_existing_dirs(paths: list[Path]) -> list[Path]:
    """对路径列表去重并过滤掉不存在的目录。Windows 下做大小写不敏感比较。"""
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
    """收集系统中所有可能的 TeX 二进制目录，覆盖 PATH、环境变量、macOS / Windows / Linux 平台默认路径及 TeX Live / MiKTeX 安装位置。"""
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

    return unique_existing_dirs(candidates)


def resolve_executable(*names: str) -> str | None:
    """按名称搜索可执行文件：先尝试 ``shutil.which``，再遍历 ``candidate_tex_bin_dirs()`` 返回的目录。"""
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


class InstallError(RuntimeError):
    pass


def mirror_archive_url(mirror: str, ref: str) -> str:
    quoted_ref = urllib.parse.quote(ref, safe="")
    if mirror == "github":
        return f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/zipball/{quoted_ref}"
    if mirror == "gitee":
        return f"https://gitee.com/{REPO_OWNER}/{REPO_NAME}/repository/archive/{quoted_ref}.zip"
    raise InstallError(f"不支持的镜像：{mirror}")


def mirror_raw_url(mirror: str, ref: str, path: str) -> str:
    quoted_ref = urllib.parse.quote(ref, safe="")
    normalized_path = path.lstrip("/")
    if mirror == "github":
        return f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{quoted_ref}/{normalized_path}"
    if mirror == "gitee":
        return f"https://gitee.com/{REPO_OWNER}/{REPO_NAME}/raw/{quoted_ref}/{normalized_path}"
    raise InstallError(f"不支持的镜像：{mirror}")


def iter_mirrors(mirror: str) -> tuple[str, ...]:
    if mirror in {"github", "gitee"}:
        return (mirror,)
    if mirror == "auto":
        return ("gitee", "github")
    raise InstallError(f"不支持的镜像：{mirror}")


class NSFCPackageManager:
    """NSFC 公共包版本管理器，负责下载、缓存、安装、激活、锁定与回退。

    核心职责：
    - 从 GitHub / Gitee 下载指定版本快照并缓存到本地
    - 将缓存的包文件部署到 ``TEXMFHOME/tex/latex/bensz-nsfc/``
    - 管理项目级版本锁定文件 ``.nsfc-version``
    - 支持多版本切换与回退

    状态文件布局（``~/.ChineseResearchLaTeX/bensz-nsfc/``）：
    - ``cache/commits/<commit>/`` — 各版本的包文件与元数据
    - ``cache/refs/<ref>.json`` — ref → commit 的解析映射
    - ``state.json`` — 当前激活版本状态
    """

    def __init__(self, cwd: Path | None = None, texmfhome_override: str | None = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()
        self.texmfhome_override = texmfhome_override
        self.package_dir = PACKAGE_DIR
        self.repo_root = discover_repo_root()
        self.state_root = get_project_state_home() / "bensz-nsfc"
        self.cache_root = self.state_root / "cache" / "commits"
        self.refs_root = self.state_root / "cache" / "refs"
        self.state_file = self.state_root / "state.json"
        self.registry_file = self.state_root / "registry.json"
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.refs_root.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        """返回当前 UTC 时间的 ISO 8601 格式字符串（秒精度），用于元数据时间戳。"""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _safe_ref_name(self, ref: str) -> str:
        """将 ref 转换为文件系统安全的字符串（URL 编码后将 % 替换为 _）。"""
        return urllib.parse.quote(ref, safe="").replace("%", "_")

    def _json_load(self, path: Path, default: Any) -> Any:
        """从 JSON 文件加载数据；文件不存在时返回 default。"""
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _json_dump(self, path: Path, payload: Any) -> None:
        """将 payload 序列化为 UTF-8 JSON 写入文件，自动创建父目录。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _github_headers(self) -> dict[str, str]:
        """构建 GitHub API 请求头，自动注入 ``GITHUB_TOKEN`` / ``GH_TOKEN`` 环境变量。"""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ChineseResearchLaTeX-install.py",
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _fetch_json(self, url: str) -> Any:
        """从远程 URL 获取并解析 JSON 响应。失败时抛出 InstallError。"""
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise InstallError(f"GitHub API 请求失败：{exc.code} {url}") from exc
        except urllib.error.URLError as exc:
            raise InstallError(f"无法访问远端资源：{url}") from exc

    def _download_file(self, url: str, destination: Path) -> None:
        """下载远程文件到本地路径。失败时抛出 InstallError。"""
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                destination.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            raise InstallError(f"下载失败：{exc.code} {url}") from exc
        except urllib.error.URLError as exc:
            raise InstallError(f"无法下载资源：{url}") from exc

    def _try_fetch_text(self, url: str) -> str | None:
        """尝试从远程 URL 获取文本内容；网络错误时返回 None 而非抛出异常。"""
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                return response.read().decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError):
            return None

    def _load_package_metadata(self, package_dir: Path) -> dict[str, Any]:
        """从 ``package.json`` 加载包元数据（版本号、模板信息等）。"""
        package_json = package_dir / "package.json"
        if not package_json.exists():
            raise InstallError(f"未找到包元数据：{package_json}")
        return json.loads(package_json.read_text(encoding="utf-8"))

    def _installed_package_version(self) -> str | None:
        """检测当前已安装到 TEXMFHOME 的包版本号。优先从 package.json 读取，回退到状态文件。"""
        target_install_dir = self._target_install_dir().resolve()
        package_json = target_install_dir / "package.json"
        if package_json.exists():
            try:
                payload = json.loads(package_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            version = payload.get("version")
            if version:
                return str(version)

        current = self._state().get("current") or {}
        install_path = current.get("install_path")
        if install_path:
            try:
                resolved_install_path = Path(install_path).expanduser().resolve()
            except OSError:
                resolved_install_path = Path(install_path).expanduser()
            if resolved_install_path == target_install_dir:
                version = current.get("package_version")
                return str(version) if version else None
        return None

    def _fetch_remote_package_version(self, ref: str, mirror: str) -> str | None:
        """从远程仓库的 ``package.json`` 获取指定 ref 对应的版本号。按镜像优先级逐一尝试。"""
        raw_path = f"{PACKAGE_SOURCE_RELATIVE.as_posix()}/package.json"
        for current_mirror in iter_mirrors(mirror):
            content = self._try_fetch_text(mirror_raw_url(current_mirror, ref, raw_path))
            if content is None:
                continue
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                continue
            version = payload.get("version")
            if version:
                return str(version)
        return None

    def _find_dependency_dirs(self, package_dir: Path) -> dict[str, Path]:
        """在包目录的兄弟目录中查找 ``DEPENDENCY_PACKAGE_SLUGS`` 列出的依赖包路径。"""
        found: dict[str, Path] = {}
        packages_root = package_dir.parent
        for slug in DEPENDENCY_PACKAGE_SLUGS:
            candidate = packages_root / slug
            if candidate.exists():
                found[slug] = candidate
        return found

    def _hash_directory(self, directory: Path) -> str:
        """递归计算目录内容的 SHA-256 哈希值，用于本地安装场景的版本标识。"""
        digest = hashlib.sha256()
        for file_path in sorted(p for p in directory.rglob("*") if p.is_file()):
            digest.update(str(file_path.relative_to(directory)).encode("utf-8"))
            digest.update(file_path.read_bytes())
        return digest.hexdigest()

    def _resolve_local_package_dir(self, source_path: Path) -> Path:
        """从用户指定的本地路径定位包目录，支持直接指向包目录或仓库根目录。"""
        source_path = source_path.resolve()
        if (source_path / "package.json").exists():
            return source_path
        candidate = source_path / PACKAGE_SOURCE_RELATIVE
        if (candidate / "package.json").exists():
            return candidate
        raise InstallError(f"无法从本地路径定位包目录：{source_path}")

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        """将用户提供的 ref（tag、分支名、commit SHA 或 local- 前缀）解析为包含 commit SHA 的元数据字典。

        解析顺序：
        1. ``local-`` 前缀直接从本地缓存读取
        2. 已缓存的 ref 映射文件
        3. 通过 GitHub API 实时查询
        """
        if ref.startswith("local-"):
            metadata = self._json_load(self.cache_root / ref / "metadata.json", None)
            if metadata is None:
                raise InstallError(f"本地缓存版本不存在：{ref}")
            return metadata

        cached = self._json_load(self.refs_root / f"{self._safe_ref_name(ref)}.json", None)
        if cached and (self.cache_root / cached["resolved_commit"]).exists():
            return cached

        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{urllib.parse.quote(ref, safe='')}"
        payload = self._fetch_json(url)
        resolved = {
            "requested_ref": ref,
            "resolved_commit": payload["sha"],
            "commit_date": payload.get("commit", {}).get("committer", {}).get("date"),
            "source": "github",
            "resolved_at": self._timestamp(),
        }
        self._json_dump(self.refs_root / f"{self._safe_ref_name(ref)}.json", resolved)
        return resolved

    def _cache_metadata(self, commit: str) -> dict[str, Any]:
        """从本地缓存读取指定 commit 的元数据（版本号、来源、时间戳等）。"""
        metadata_file = self.cache_root / commit / "metadata.json"
        if not metadata_file.exists():
            raise InstallError(f"缓存元数据不存在：{metadata_file}")
        return self._json_load(metadata_file, {})

    def _download_github_snapshot(self, commit: str) -> tuple[Path, Path]:
        """从 GitHub 下载指定 commit 的仓库快照（zipball），解压后定位 bensz-nsfc 包目录。

        Returns:
            (临时目录路径, 包目录路径) 的二元组。调用方负责清理临时目录。
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="bensz-nsfc-"))
        archive_path = temp_dir / "snapshot.zip"
        extract_dir = temp_dir / "extract"
        self._download_file(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/zipball/{commit}",
            archive_path,
        )
        with zipfile.ZipFile(archive_path) as bundle:
            bundle.extractall(extract_dir)
        extracted_roots = [path for path in extract_dir.iterdir() if path.is_dir()]
        if not extracted_roots:
            raise InstallError("下载的快照中没有找到仓库根目录")
        package_dir = extracted_roots[0] / PACKAGE_SOURCE_RELATIVE
        if not package_dir.exists():
            raise InstallError(f"快照中缺少包目录：{PACKAGE_SOURCE_RELATIVE}")
        return temp_dir, package_dir

    def _download_mirrored_snapshot(self, ref: str, mirror: str) -> tuple[Path, Path, str]:
        """通过指定镜像源下载仓库快照，支持 auto 模式自动按 ``gitee → github`` 顺序尝试。

        Returns:
            (临时目录路径, 包目录路径, 实际使用的镜像名) 的三元组。
        """
        last_error = None
        for current_mirror in iter_mirrors(mirror):
            temp_dir = Path(tempfile.mkdtemp(prefix=f"{PACKAGE_SLUG}-{current_mirror}-"))
            archive_path = temp_dir / "snapshot.zip"
            extract_dir = temp_dir / "extract"
            try:
                self._download_file(mirror_archive_url(current_mirror, ref), archive_path)
                with zipfile.ZipFile(archive_path) as bundle:
                    bundle.extractall(extract_dir)
                extracted_roots = [extract_dir, *[path for path in extract_dir.iterdir() if path.is_dir()]]
                package_dir = None
                for root in extracted_roots:
                    candidate = root / PACKAGE_SOURCE_RELATIVE
                    if candidate.exists():
                        package_dir = candidate
                        break
                if package_dir is None:
                    raise InstallError(f"快照中缺少包目录：{PACKAGE_SOURCE_RELATIVE}")
                return temp_dir, package_dir, current_mirror
            except Exception as exc:  # noqa: BLE001
                shutil.rmtree(temp_dir, ignore_errors=True)
                last_error = exc
        raise InstallError(f"无法通过镜像下载 {ref}：{last_error}") from last_error

    def _download_release_snapshot(self, ref: str, commit: str) -> tuple[Path, Path]:
        """尝试从 GitHub Release 下载 TDS zip 资产；若无可用资产则回退到 ``_download_github_snapshot()``。"""
        releases = self._fetch_json(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases")
        release = next((item for item in releases if item.get("tag_name") == ref), None)
        if release:
            asset = next(
                (
                    item
                    for item in release.get("assets", [])
                    if item.get("name", "").endswith(".zip") and "tds" in item.get("name", "")
                ),
                None,
            )
            if asset and asset.get("browser_download_url"):
                temp_dir = Path(tempfile.mkdtemp(prefix="bensz-nsfc-release-"))
                archive_path = temp_dir / asset["name"]
                extract_dir = temp_dir / "extract"
                self._download_file(asset["browser_download_url"], archive_path)
                with zipfile.ZipFile(archive_path) as bundle:
                    bundle.extractall(extract_dir)
                package_dir = extract_dir / "tex" / "latex" / PACKAGE_SLUG
                if package_dir.exists():
                    return temp_dir, package_dir
        return self._download_github_snapshot(commit)

    def _cache_package(
        self,
        package_dir: Path,
        requested_ref: str,
        resolved_commit: str,
        source: str,
        dependency_dirs: dict[str, Path] | None = None,
    ) -> dict[str, Any]:
        """将下载的包文件和依赖复制到本地缓存目录，并写入版本元数据。

        Args:
            package_dir: 下载/解压后的包文件目录
            requested_ref: 用户请求的原始 ref（tag、分支名等）
            resolved_commit: 解析后的 commit SHA
            source: 来源标识（github / gitee / local / release）
            dependency_dirs: 依赖包的 ``{slug: Path}`` 映射

        Returns:
            写入缓存的元数据字典
        """
        commit_root = self.cache_root / resolved_commit
        package_target = commit_root / "package"
        if package_target.exists():
            shutil.rmtree(package_target)
        package_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package_dir, package_target)
        dependencies_root = commit_root / "dependencies"
        if dependencies_root.exists():
            shutil.rmtree(dependencies_root)
        for slug, dependency_dir in (dependency_dirs or {}).items():
            shutil.copytree(dependency_dir, dependencies_root / slug)
        package_metadata = self._load_package_metadata(package_dir)
        payload = {
            "requested_ref": requested_ref,
            "resolved_commit": resolved_commit,
            "source": source,
            "cached_at": self._timestamp(),
            "package_name": package_metadata.get("name", PACKAGE_NAME),
            "package_version": package_metadata.get("version"),
            "templates": package_metadata.get("templates", {}),
            "installer": package_metadata.get("installer", {}),
            "dependencies": sorted((dependency_dirs or {}).keys()),
        }
        self._json_dump(commit_root / "metadata.json", payload)
        if requested_ref:
            self._json_dump(self.refs_root / f"{self._safe_ref_name(requested_ref)}.json", payload)
        return payload

    def _get_texmf_home(self) -> Path:
        """解析 TEXMFHOME 路径，优先级：命令行覆盖 > 环境变量 > kpsewhich 查询 > 平台默认值。"""
        if self.texmfhome_override:
            return Path(self.texmfhome_override).expanduser().resolve()

        env_value = os.environ.get("TEXMFHOME")
        if env_value:
            return Path(env_value).expanduser().resolve()

        kpsewhich = resolve_executable("kpsewhich")
        if kpsewhich:
            result = subprocess.run(
                [kpsewhich, "-var-value", "TEXMFHOME"],
                check=False,
                capture_output=True,
                text=True,
            )
            value = result.stdout.strip()
            if result.returncode == 0 and value:
                return Path(value).expanduser()

        system = platform.system()
        if system == "Darwin":
            return Path.home() / "Library" / "texmf"
        return Path.home() / "texmf"

    def _refresh_texmf(self, texmf_home: Path) -> None:
        """刷新 TeX 文件名数据库（依次尝试 mktexlsr / texhash / initexmf），确保新安装的包可被 TeX 引擎发现。"""
        for command in ("mktexlsr", "texhash"):
            executable = resolve_executable(command)
            if not executable:
                continue
            subprocess.run([executable, str(texmf_home)], check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            return
        initexmf = resolve_executable("initexmf")
        if initexmf:
            subprocess.run([initexmf, "--update-fndb"], check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def _target_install_dir(self) -> Path:
        """返回 bensz-nsfc 包在 TEXMFHOME 中的目标安装路径（``TEXMFHOME/tex/latex/bensz-nsfc/``）。"""
        return self._get_texmf_home() / "tex" / "latex" / PACKAGE_SLUG

    def _state(self) -> dict[str, Any]:
        """加载当前安装状态（激活版本、commit、路径等）。"""
        return self._json_load(self.state_file, {})

    def _save_state(self, payload: dict[str, Any]) -> None:
        """持久化安装状态到 ``state.json``。"""
        self._json_dump(self.state_file, payload)

    def _write_runtime_file(self, package_dir: Path) -> None:
        """在安装目录生成 ``bensz-nsfc-runtime.def``，写入包根目录、资源目录、字体目录与 BibTeX 样式的绝对路径，供 LaTeX 编译时引用。"""
        runtime_file = package_dir / "bensz-nsfc-runtime.def"
        package_root = package_dir.resolve().as_posix() + "/"
        assets_dir = package_root + "assets/"
        fonts_package_dir = package_dir.parent / "bensz-fonts"
        if (fonts_package_dir / "bensz-fonts.sty").exists():
            assets_fonts_dir = fonts_package_dir.resolve().as_posix() + "/fonts/"
        else:
            assets_fonts_dir = assets_dir + "fonts/"
        asset_bib_style_base = assets_dir + "bibtex-style/gbt7714-nsfc"
        runtime_file.write_text(
            "\n".join(
                [
                    "% Auto-generated by packages/bensz-nsfc/scripts/install.py. Do not edit manually.",
                    f"\\renewcommand{{\\NSFCPackageRootDir}}{{{package_root}}}",
                    f"\\renewcommand{{\\NSFCAssetsDir}}{{{assets_dir}}}",
                    f"\\renewcommand{{\\NSFCAssetFontsDir}}{{{assets_fonts_dir}}}",
                    f"\\renewcommand{{\\NSFCAssetBibStyleBase}}{{{asset_bib_style_base}}}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _activate_commit(self, commit: str, dry_run: bool = False) -> dict[str, Any]:
        """将指定 commit 的缓存包部署到 TEXMFHOME 目标目录，并更新安装状态。

        部署步骤：
        1. 复制依赖包（如 bensz-fonts）到 TEXMFHOME
        2. 复制主包文件到目标目录
        3. 写入运行时路径文件 ``bensz-nsfc-runtime.def``
        4. 刷新 TeX 文件名数据库
        5. 更新 ``state.json``（记录当前版本与上一版本）

        Args:
            commit: 要激活的 commit SHA 或 local- 前缀标识
            dry_run: 若为 True，仅返回将要执行的操作而不实际写入
        """
        metadata = self._cache_metadata(commit)
        target = self._target_install_dir()
        texmf_home = self._get_texmf_home()
        if dry_run:
            return {
                "action": "activate",
                "commit": commit,
                "target": str(target),
                "texmf_home": str(texmf_home),
            }

        target.parent.mkdir(parents=True, exist_ok=True)
        dependencies_root = self.cache_root / commit / "dependencies"
        for slug in DEPENDENCY_PACKAGE_SLUGS:
            dependency_source = dependencies_root / slug
            if not dependency_source.exists():
                continue
            dependency_target = target.parent / slug
            if dependency_target.exists():
                shutil.rmtree(dependency_target)
            shutil.copytree(dependency_source, dependency_target)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.cache_root / commit / "package", target)
        self._write_runtime_file(target)
        self._refresh_texmf(texmf_home)

        state = self._state()
        current = state.get("current", {})
        previous_commit = current.get("commit")
        if previous_commit and previous_commit != commit:
            state["previous_commit"] = previous_commit
        state["current"] = {
            "commit": commit,
            "requested_ref": metadata.get("requested_ref"),
            "package_version": metadata.get("package_version"),
            "package_name": metadata.get("package_name"),
            "activated_at": self._timestamp(),
            "install_path": str(target),
            "texmf_home": str(texmf_home),
        }
        self._save_state(state)
        return state["current"]

    def install(
        self,
        ref: str,
        source: str = "github",
        mirror: str = "github",
        activate: bool = True,
        force: bool = False,
        dry_run: bool = False,
        local_path: Path | None = None,
    ) -> dict[str, Any]:
        """安装指定版本的 bensz-nsfc 公共包。

        安装流程：
        1. 根据 source 参数选择安装来源（local / mirror / github）
        2. 检测是否可跳过（已安装相同版本且未强制覆盖）
        3. 下载快照、缓存到本地、（可选）激活到 TEXMFHOME

        Args:
            ref: 版本标识（tag、分支名、commit SHA）
            source: 来源类型 — ``github``（默认）、``release``（优先 TDS 资产）、``local``（本地路径）
            mirror: 镜像源 — ``github``（默认）、``gitee``、``auto``（先 gitee 后 github）
            activate: 是否在下载后立即激活到 TEXMFHOME
            force: 是否强制重新安装（忽略版本一致性检查）
            dry_run: 仅模拟，不实际下载或写入
            local_path: source=local 时的本地包路径或仓库根路径

        Returns:
            包含版本元数据、缓存信息和激活结果的字典
        """
        if source == "local":
            if local_path is None:
                raise InstallError("本地安装模式必须提供 --path")
            package_dir = self._resolve_local_package_dir(local_path)
            target_version = self._load_package_metadata(package_dir).get("version")
            installed_version = self._installed_package_version()
            if should_skip_reinstall(installed_version, target_version, force=force):
                return {
                    "requested_ref": ref,
                    "source": "local",
                    "package_version": target_version,
                    "installed_version": installed_version,
                    "skipped": True,
                    "reason": "same_version",
                }
            dependency_dirs = self._find_dependency_dirs(package_dir)
            commit = f"local-{self._hash_directory(package_dir)[:12]}"
            cached = self._cache_root_for(commit)
            if force or not cached.exists():
                self._cache_package(package_dir, ref or commit, commit, "local", dependency_dirs)
            metadata = self._cache_metadata(commit)
        elif mirror != "github":
            target_version = self._fetch_remote_package_version(ref, mirror)
            installed_version = self._installed_package_version()
            if should_skip_reinstall(installed_version, target_version, force=force):
                return {
                    "requested_ref": ref,
                    "source": mirror,
                    "package_version": target_version,
                    "installed_version": installed_version,
                    "skipped": True,
                    "reason": "same_version",
                }
            temp_dir, package_dir, actual_mirror = self._download_mirrored_snapshot(ref, mirror)
            dependency_dirs = self._find_dependency_dirs(package_dir)
            commit = f"{actual_mirror}-{self._hash_directory(package_dir)[:12]}"
            if force or not self._cache_root_for(commit).exists():
                if dry_run:
                    return {
                        "action": "download",
                        "requested_ref": ref,
                        "resolved_commit": commit,
                        "source": actual_mirror,
                    }
                try:
                    self._cache_package(package_dir, ref, commit, actual_mirror, dependency_dirs)
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                shutil.rmtree(temp_dir, ignore_errors=True)
            metadata = self._cache_metadata(commit)
        else:
            target_version = self._fetch_remote_package_version(ref, mirror)
            installed_version = self._installed_package_version()
            if should_skip_reinstall(installed_version, target_version, force=force):
                return {
                    "requested_ref": ref,
                    "source": source,
                    "package_version": target_version,
                    "installed_version": installed_version,
                    "skipped": True,
                    "reason": "same_version",
                }
            resolved = self._resolve_ref(ref)
            commit = resolved["resolved_commit"]
            if force or not self._cache_root_for(commit).exists():
                if dry_run:
                    return {
                        "action": "download",
                        "requested_ref": ref,
                        "resolved_commit": commit,
                        "source": source,
                    }
                if source == "release":
                    temp_dir, package_dir = self._download_release_snapshot(ref, commit)
                    dependency_dirs = self._find_dependency_dirs(package_dir)
                    if not dependency_dirs:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        temp_dir, package_dir = self._download_github_snapshot(commit)
                        dependency_dirs = self._find_dependency_dirs(package_dir)
                else:
                    temp_dir, package_dir = self._download_github_snapshot(commit)
                    dependency_dirs = self._find_dependency_dirs(package_dir)
                try:
                    self._cache_package(package_dir, ref, commit, source, dependency_dirs)
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            metadata = self._cache_metadata(commit)

        if activate:
            activation = self._activate_commit(commit, dry_run=dry_run)
            metadata["activation"] = activation
        return metadata

    def _cache_root_for(self, commit: str) -> Path:
        return self.cache_root / commit

    def _cached_ref(self, ref: str) -> dict[str, Any] | None:
        data = self._json_load(self.refs_root / f"{self._safe_ref_name(ref)}.json", None)
        if data and self._cache_root_for(data["resolved_commit"]).exists():
            return data
        if self._cache_root_for(ref).exists():
            return self._cache_metadata(ref)
        return None

    def use(self, ref: str, dry_run: bool = False) -> dict[str, Any]:
        cached = self._cached_ref(ref)
        if cached is None:
            return self.install(ref=ref, activate=True, dry_run=dry_run)
        activation = self._activate_commit(cached["resolved_commit"], dry_run=dry_run)
        cached["activation"] = activation
        return cached

    def _find_project_root(self) -> Path:
        for candidate in [self.cwd, *self.cwd.parents]:
            if (candidate / LOCKFILE_NAME).exists():
                return candidate
            if (candidate / "main.tex").exists() and (candidate / "extraTex" / "@config.tex").exists():
                return candidate
        return self.cwd

    def _lockfile_path(self) -> Path:
        return self._find_project_root() / LOCKFILE_NAME

    def _detect_template_id(self, project_root: Path) -> str:
        config_file = project_root / "extraTex" / "@config.tex"
        if config_file.exists():
            content = config_file.read_text(encoding="utf-8", errors="ignore")
            for template_id in ("general", "local", "young"):
                if f"type={template_id}" in content:
                    return template_id
        mapping = {
            "NSFC_General": "general",
            "NSFC_Local": "local",
            "NSFC_Young": "young",
        }
        return mapping.get(project_root.name, "general")

    def pin(self, ref: str | None, dry_run: bool = False) -> dict[str, Any]:
        """将当前或指定版本锁定到项目级 ``.nsfc-version`` 文件。

        锁定内容包含：ref、commit、包版本、模板类型与模板版本。
        后续可通过 ``sync`` 命令在其他环境中复现相同版本。

        Args:
            ref: 要锁定的版本标识；为 None 时锁定当前激活版本
            dry_run: 仅模拟，不实际写入锁文件
        """
        project_root = self._find_project_root()
        state = self._state().get("current")
        metadata: dict[str, Any]
        if ref:
            metadata = self._cached_ref(ref) or self.install(ref=ref, activate=False, dry_run=dry_run)
        elif state:
            metadata = self._cache_metadata(state["commit"])
        else:
            raise InstallError("当前没有激活版本，也没有提供 --ref")

        template_id = self._detect_template_id(project_root)
        template_meta = metadata.get("templates", {}).get(template_id, {})
        payload = {
            "ref": ref or metadata.get("requested_ref"),
            "commit": metadata["resolved_commit"],
            "package_name": metadata.get("package_name", PACKAGE_NAME),
            "package_version": metadata.get("package_version"),
            "template_id": template_id,
            "template_version": template_meta.get("template_version"),
        }
        if not dry_run:
            self._json_dump(self._lockfile_path(), payload)
        return payload

    def read_lockfile(self) -> dict[str, Any]:
        """读取项目级 ``.nsfc-version`` 锁文件内容。文件不存在时抛出 InstallError。"""
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            raise InstallError(f"当前目录未锁定版本：{lockfile}")
        return self._json_load(lockfile, {})

    def sync(self, dry_run: bool = False) -> dict[str, Any]:
        """根据项目锁文件 ``.nsfc-version`` 激活对应版本。若本地缓存已有则直接激活，否则重新下载。"""
        lock = self.read_lockfile()
        commit = lock.get("commit")
        if not commit:
            raise InstallError("锁文件缺少 commit")
        if self._cache_root_for(commit).exists():
            activation = self._activate_commit(commit, dry_run=dry_run)
            return {"lockfile": lock, "activation": activation}
        requested = lock.get("ref") or commit
        return self.install(ref=requested, activate=True, dry_run=dry_run)

    def check(self) -> dict[str, Any]:
        """检查当前激活版本与项目锁文件的一致性。

        比对三个维度：commit SHA、包版本号、模板版本号。
        返回 ``match``（一致）、``mismatch``（不一致）或 ``unlocked``（未锁定）状态。
        """
        state = self._state().get("current")
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            return {"status": "unlocked", "active": state}
        lock = self._json_load(lockfile, {})
        if not state:
            return {"status": "mismatch", "reason": "未激活任何版本", "lockfile": lock}

        commit_match = state.get("commit") == lock.get("commit")
        package_match = state.get("package_version") == lock.get("package_version")
        cached = self._cache_metadata(lock["commit"]) if self._cache_root_for(lock["commit"]).exists() else None
        template_id = lock.get("template_id")
        template_match = True
        if cached and template_id:
            template_match = cached.get("templates", {}).get(template_id, {}).get("template_version") == lock.get("template_version")
        status = "match" if commit_match and package_match and template_match else "mismatch"
        return {
            "status": status,
            "active": state,
            "lockfile": lock,
            "checks": {
                "commit": commit_match,
                "package_version": package_match,
                "template_version": template_match,
            },
        }

    def rollback(self, dry_run: bool = False) -> dict[str, Any]:
        """回退到上一个激活版本（从 state.json 中的 previous_commit 字段读取）。"""
        previous = self._state().get("previous_commit")
        if not previous:
            raise InstallError("没有可回退的上一版本")
        if not self._cache_root_for(previous).exists():
            raise InstallError(f"上一版本缓存不存在：{previous}")
        activation = self._activate_commit(previous, dry_run=dry_run)
        return {"rolled_back_to": previous, "activation": activation}

    def uninstall(self, dry_run: bool = False) -> dict[str, Any]:
        """卸载已安装的 bensz-nsfc 包（删除 TEXMFHOME 下的目标目录并刷新文件名数据库）。"""
        target = self._target_install_dir()
        if dry_run:
            return {"action": "uninstall", "target": str(target)}
        if target.exists():
            shutil.rmtree(target)
        self._refresh_texmf(self._get_texmf_home())
        state = self._state()
        state["current"] = None
        self._save_state(state)
        return {"removed": str(target)}

    def status(self) -> dict[str, Any]:
        """返回当前安装状态概要（当前版本、上一版本、缓存元数据）。"""
        state = self._state()
        current = state.get("current")
        result = {"current": current, "previous_commit": state.get("previous_commit")}
        if current and self._cache_root_for(current["commit"]).exists():
            result["cached_metadata"] = self._cache_metadata(current["commit"])
        return result

    def list_cached(self) -> list[dict[str, Any]]:
        """列出所有本地缓存的版本及其元数据，按 commit 名排序。"""
        items = []
        for commit_dir in sorted(self.cache_root.iterdir(), key=lambda item: item.name):
            metadata_file = commit_dir / "metadata.json"
            if metadata_file.exists():
                items.append(self._json_load(metadata_file, {}))
        return items

    def list_remote(self) -> dict[str, Any]:
        """从 GitHub 获取所有 Release 和 Tag 列表，并缓存到本地 registry。"""
        releases = self._fetch_json(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases")
        tags = self._fetch_json(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/tags?per_page=100")
        payload = {
            "fetched_at": self._timestamp(),
            "releases": [
                {
                    "tag_name": item.get("tag_name"),
                    "published_at": item.get("published_at"),
                    "prerelease": item.get("prerelease"),
                }
                for item in releases
            ],
            "tags": [item.get("name") for item in tags],
        }
        self._json_dump(self.registry_file, payload)
        return payload

    def info(self, ref: str) -> dict[str, Any]:
        """查询指定 ref 的解析信息和本地缓存状态。"""
        resolved = self._resolve_ref(ref)
        metadata = self._cached_ref(ref)
        return {"resolved": resolved, "cached": metadata}

    def unpin(self, dry_run: bool = False) -> dict[str, Any]:
        """删除项目级 ``.nsfc-version`` 锁文件。"""
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            return {"removed": False, "path": str(lockfile)}
        if not dry_run:
            lockfile.unlink()
        return {"removed": True, "path": str(lockfile)}

    def prune(self, dry_run: bool = False) -> dict[str, Any]:
        """清理不再需要的本地缓存版本。保留当前激活版本、上一版本以及所有项目锁文件引用的版本。"""
        state = self._state()
        keep = {
            item
            for item in (
                state.get("previous_commit"),
                (state.get("current") or {}).get("commit"),
            )
            if item
        }
        for lockfile in self.repo_root.rglob(LOCKFILE_NAME):
            try:
                keep.add(json.loads(lockfile.read_text(encoding="utf-8")).get("commit"))
            except json.JSONDecodeError:
                continue

        removed: list[str] = []
        for commit_dir in self.cache_root.iterdir():
            if commit_dir.name in keep:
                continue
            removed.append(commit_dir.name)
            if not dry_run:
                shutil.rmtree(commit_dir, ignore_errors=True)
        return {"kept": sorted(item for item in keep if item), "removed": sorted(removed)}


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器，支持 install / use / pin / sync / check / rollback 等子命令。"""
    parser = argparse.ArgumentParser(description="NSFC 公共包安装/切换/锁定工具")
    parser.add_argument(
        "--texmfhome",
        help="覆盖 TEXMFHOME 安装目录；当 TeX 未加入 PATH 或需安装到自定义 texmf 树时使用",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--ref", required=True)
    install_parser.add_argument("--source", choices=("github", "release", "local"), default="github")
    install_parser.add_argument("--mirror", choices=("github", "gitee", "auto"), default="github")
    install_parser.add_argument("--path", type=Path)
    install_parser.add_argument("--force", action="store_true")
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.add_argument("--no-activate", action="store_true")

    use_parser = subparsers.add_parser("use")
    use_parser.add_argument("--ref", required=True)
    use_parser.add_argument("--dry-run", action="store_true")

    pin_parser = subparsers.add_parser("pin")
    pin_parser.add_argument("--ref")
    pin_parser.add_argument("--dry-run", action="store_true")

    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--dry-run", action="store_true")

    check_parser = subparsers.add_parser("check")

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--dry-run", action="store_true")

    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("status")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--remote", action="store_true")

    info_parser = subparsers.add_parser("info")
    info_parser.add_argument("--ref", required=True)

    unpin_parser = subparsers.add_parser("unpin")
    unpin_parser.add_argument("--dry-run", action="store_true")

    prune_parser = subparsers.add_parser("prune")
    prune_parser.add_argument("--dry-run", action="store_true")

    return parser


def main() -> int:
    """CLI 入口：解析命令行参数，分发到 NSFCPackageManager 对应方法，输出 JSON 结果。

    启动时会发出 DeprecationWarning，提示用户迁移到 ``package/install.py``。
    """
    import warnings

    warnings.warn(
        "packages/bensz-nsfc/scripts/install.py 已弃用，请使用 "
        "packages/bensz-nsfc/scripts/package/install.py",
        DeprecationWarning,
        stacklevel=2,
    )
    print(
        "⚠️  注意：本入口已弃用，推荐使用 "
        "packages/bensz-nsfc/scripts/package/install.py",
        file=sys.stderr,
    )
    parser = build_parser()
    args = parser.parse_args()
    manager = NSFCPackageManager(texmfhome_override=args.texmfhome)

    try:
        if args.command == "install":
            result = manager.install(
                ref=args.ref,
                source=args.source,
                mirror=args.mirror,
                activate=not args.no_activate,
                force=args.force,
                dry_run=args.dry_run,
                local_path=args.path,
            )
        elif args.command == "use":
            result = manager.use(args.ref, dry_run=args.dry_run)
        elif args.command == "pin":
            result = manager.pin(args.ref, dry_run=args.dry_run)
        elif args.command == "sync":
            result = manager.sync(dry_run=args.dry_run)
        elif args.command == "check":
            result = manager.check()
        elif args.command == "rollback":
            result = manager.rollback(dry_run=args.dry_run)
        elif args.command == "uninstall":
            result = manager.uninstall(dry_run=args.dry_run)
        elif args.command == "status":
            result = manager.status()
        elif args.command == "list":
            result = manager.list_remote() if args.remote else manager.list_cached()
        elif args.command == "info":
            result = manager.info(args.ref)
        elif args.command == "unpin":
            result = manager.unpin(dry_run=args.dry_run)
        elif args.command == "prune":
            result = manager.prune(dry_run=args.dry_run)
        else:
            raise InstallError(f"不支持的命令：{args.command}")
    except InstallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "check":
        return 0 if result.get("status") in {"match", "unlocked"} else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
