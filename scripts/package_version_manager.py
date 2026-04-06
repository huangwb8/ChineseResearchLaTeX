#!/usr/bin/env python3
"""公共包版本管理共享框架。

本模块为 bensz-nsfc、bensz-paper、bensz-thesis、bensz-cv 等 LaTeX 公共包提供统一的
版本管理基础设施。各包的 install.py 通过组合 VersionedPackageManager 与可选的
ProjectLockMixin 来获得完整的安装、切换、回退、清理和项目级版本锁定能力。

典型用法::

    from package_version_manager import VersionedPackageManager, PackageSpec

    spec = PackageSpec(package_name="bensz-nsfc", source_marker="bensz-nsfc-common.sty")
    manager = VersionedPackageManager(spec)
    manager.install(ref="v3.5.1")
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# GitHub 仓库归属信息，用于拼接远程下载 URL
REPO_OWNER = "huangwb8"
REPO_NAME = "ChineseResearchLaTeX"

# 复制文件树时跳过的目录和文件名
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


class InstallError(RuntimeError):
    """安装过程中的业务异常，用于向用户报告可读的错误信息。"""
    pass


@dataclass(frozen=True)
class PackageSpec:
    """公共包的规格描述，定义包名、安装路径和依赖关系。

    Attributes:
        package_name: 包名，如 ``bensz-nsfc``
        source_marker: 用于 kpsewhich 检测的源文件标识，如 ``bensz-nsfc-common.sty``
        dependency_package_names: 该包依赖的其他包名（会随主包一起安装到 TEXMFHOME）
        package_subpath: 安装到 TEXMFHOME 下的子路径；默认为 ``tex/latex/<package_name>``
        state_dir_name: 状态目录名；默认与 package_name 相同
    """
    package_name: str
    source_marker: str
    dependency_package_names: tuple[str, ...] = ()
    package_subpath: Path | None = None
    state_dir_name: str | None = None

    def resolved_package_subpath(self) -> Path:
        if self.package_subpath is not None:
            return self.package_subpath
        return Path("tex") / "latex" / self.package_name

    def resolved_state_dir_name(self) -> str:
        return self.state_dir_name or self.package_name


def get_project_state_home() -> Path:
    """返回项目级状态根目录 ``~/.ChineseResearchLaTeX/``。"""
    return Path.home() / ".ChineseResearchLaTeX"


def configure_windows_stdio_utf8() -> None:
    """在 Windows 平台上将 stdout/stderr 重编码为 UTF-8，避免中文乱码。"""
    import sys

    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def should_skip_reinstall(
    installed_version: str | None,
    target_version: str | None,
    *,
    force: bool,
) -> bool:
    """判断是否可以跳过重复安装。当已安装版本与目标版本相同且未指定 force 时返回 True。"""
    return bool(installed_version and target_version and installed_version == target_version and not force)


def unique_existing_dirs(paths: list[Path]) -> list[Path]:
    """对路径列表去重并过滤掉不存在的目录，Windows 下路径比较不区分大小写。"""
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
    """收集系统中所有可能存在 TeX 可执行文件的目录（PATH + 常见安装路径）。"""
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
    """按优先级在 PATH 和 TeX 专属目录中查找可执行文件，返回绝对路径或 None。"""
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


def get_texmfhome(override: str | None = None) -> Path:
    """解析 TEXMFHOME 路径。优先级：显式参数 > 环境变量 > kpsewhich 查询 > 平台默认值。"""
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


def run_mktexlsr(texmfhome: Path, dry_run: bool) -> tuple[str, str | None]:
    """运行 mktexlsr / texhash / initexmf 刷新 TeX 文件名数据库。

    Returns:
        (status, command) 元组。status 为 ``"ok"``、``"dry-run"``、``"failed"`` 或 ``"missing"``。
    """
    if dry_run:
        return ("dry-run", "mktexlsr")
    for command in ("mktexlsr", "texhash"):
        executable = resolve_executable(command)
        if not executable:
            continue
        try:
            subprocess.run([executable, str(texmfhome)], check=True, capture_output=True)
            return ("ok", command)
        except subprocess.CalledProcessError:
            continue
    initexmf = resolve_executable("initexmf")
    if initexmf:
        try:
            subprocess.run([initexmf, "--update-fndb"], check=True, capture_output=True)
            return ("ok", "initexmf --update-fndb")
        except subprocess.CalledProcessError:
            return ("failed", "initexmf --update-fndb")
    return ("missing", None)


def copy_tree(src: Path, dest: Path, dry_run: bool = False) -> int:
    """递归复制文件树，跳过 __pycache__、.DS_Store 和 .pyc 文件。返回复制的文件数。"""
    copied = 0
    for file_path in sorted(src.rglob("*")):
        if not file_path.is_file():
            continue
        if any(part in EXCLUDE_NAMES for part in file_path.parts) or file_path.suffix == ".pyc":
            continue
        if not dry_run:
            target = dest / file_path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target)
        copied += 1
    return copied


def hash_directory(directory: Path) -> str:
    """计算目录内容的 SHA-256 摘要，用于生成缓存提交标识。"""
    import hashlib

    digest = hashlib.sha256()
    for file_path in sorted(path for path in directory.rglob("*") if path.is_file()):
        if any(part in EXCLUDE_NAMES for part in file_path.parts) or file_path.suffix == ".pyc":
            continue
        digest.update(str(file_path.relative_to(directory)).encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def prefer_gitee_for_auto() -> bool:
    """根据系统 locale 环境变量推断是否应优先使用 Gitee 镜像。"""
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


def iter_mirrors(mirror: str) -> tuple[str, ...]:
    """将镜像策略展开为有序镜像列表。``auto`` 会根据 locale 排序。"""
    if mirror in {"github", "gitee"}:
        return (mirror,)
    if mirror == "auto":
        return ("gitee", "github") if prefer_gitee_for_auto() else ("github", "gitee")
    raise InstallError(f"不支持的镜像：{mirror}")


def mirror_archive_url(mirror: str, ref: str) -> str:
    """根据镜像类型拼接仓库快照的 zip 下载地址。"""
    quoted_ref = urllib.parse.quote(ref, safe="")
    if mirror == "github":
        return f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/zipball/{quoted_ref}"
    if mirror == "gitee":
        return f"https://gitee.com/{REPO_OWNER}/{REPO_NAME}/repository/archive/{quoted_ref}.zip"
    raise InstallError(f"不支持的镜像：{mirror}")


def mirror_raw_url(mirror: str, ref: str, path: str) -> str:
    """根据镜像类型拼接单个文件的 raw 下载地址。"""
    quoted_ref = urllib.parse.quote(ref, safe="")
    normalized_path = path.lstrip("/")
    if mirror == "github":
        return f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{quoted_ref}/{normalized_path}"
    if mirror == "gitee":
        return f"https://gitee.com/{REPO_OWNER}/{REPO_NAME}/raw/{quoted_ref}/{normalized_path}"
    raise InstallError(f"不支持的镜像：{mirror}")


class VersionedPackageManager:
    """带缓存与版本历史管理的公共包安装器基类。

    各 bensz-* 包的 install.py 通过实例化此类并传入对应的 PackageSpec 来获得完整的
    版本管理能力。核心命令包括：

    - ``install``：从 GitHub / Gitee / 本地路径下载并激活指定版本
    - ``use``：激活已缓存的版本（若未缓存则自动安装）
    - ``rollback``：回退到上一次激活的版本
    - ``prune``：清理不再需要的缓存版本
    - ``status`` / ``check``：查询当前安装状态

    缓存目录结构::

        ~/.ChineseResearchLaTeX/<package>/
        ├── state.json              # 全局状态（当前激活版本 + 历史列表）
        ├── cache/
        │   ├── commits/
        │   │   └── <commit>/       # 每个缓存版本一个目录
        │   │       ├── package/    # 包文件副本
        │   │       ├── dependencies/  # 依赖包副本
        │   │       └── metadata.json  # 版本元数据
        │   └── refs/
        │       └── <ref>.json      # ref -> commit 的映射
        └── ...

    metadata.json 主要字段::

        package_name     包名
        requested_ref    用户请求的 ref（如 v3.5.1 或 main）
        resolved_commit  解析后的缓存标识
        source           来源（github / gitee / local）
        package_version  package.json 中的 version 字段
        cached_at        缓存创建时间（ISO 8601）
        package_dir      缓存目录中包文件的路径
        dependency_dirs  依赖包路径字典

    state.json 主要字段::

        current          当前激活版本信息（commit、ref、source、package_version、install_path）
        history          历史激活版本的 commit 列表（最多 20 条）
    """

    def __init__(
        self,
        spec: PackageSpec,
        *,
        cwd: Path | None = None,
        texmfhome_override: str | None = None,
        state_root_override: Path | None = None,
        package_dir_override: Path | None = None,
    ) -> None:
        self.spec = spec
        self.cwd = (cwd or Path.cwd()).resolve()
        self.texmfhome_override = texmfhome_override
        self.package_dir = (
            package_dir_override.resolve()
            if package_dir_override is not None
            else Path(__file__).resolve().parents[1] / "packages" / spec.package_name
        )
        self.repo_root = self.package_dir.parents[1]
        self.state_root = (
            state_root_override or (get_project_state_home() / spec.resolved_state_dir_name())
        ).resolve()
        self.cache_root = self.state_root / "cache" / "commits"
        self.refs_root = self.state_root / "cache" / "refs"
        self.state_file = self.state_root / "state.json"
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.refs_root.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        """返回当前 UTC 时间的 ISO 8601 字符串（秒精度）。"""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _safe_ref_name(self, ref: str) -> str:
        """将 ref 转换为文件系统安全的名称（URL 编码后替换 % 为 _）。"""
        return urllib.parse.quote(ref, safe="").replace("%", "_")

    def _json_load(self, path: Path, default: Any) -> Any:
        """从 JSON 文件加载数据，文件不存在时返回 default。"""
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _json_dump(self, path: Path, payload: Any) -> None:
        """将数据以 UTF-8 缩进格式写入 JSON 文件，自动创建父目录。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _github_headers(self) -> dict[str, str]:
        """构建 GitHub API 请求头，若环境变量中有 token 则自动附加认证。"""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ChineseResearchLaTeX-install.py",
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _download_file(self, url: str, destination: Path) -> None:
        """下载文件到指定路径，附带 GitHub API 认证头。"""
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                destination.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            raise InstallError(f"下载失败：{exc.code} {url}") from exc
        except urllib.error.URLError as exc:
            raise InstallError(f"无法下载资源：{url}") from exc

    def _try_fetch_text(self, url: str) -> str | None:
        """尝试下载文本内容，网络异常时返回 None 而非抛出异常。"""
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                return response.read().decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError):
            return None

    def _locate_repo_root(self, extract_dir: Path) -> Path:
        """从解压后的快照目录中定位仓库根目录（支持单子目录或带 packages/ 的结构）。"""
        children = [path for path in extract_dir.iterdir() if path.is_dir()]
        if len(children) == 1:
            return children[0]
        for candidate in children:
            if (candidate / "packages" / self.spec.package_name / "package.json").exists():
                return candidate
        raise InstallError(f"无法从快照中定位仓库根目录：{extract_dir}")

    def _resolve_local_package_dir(self, source_path: Path) -> Path:
        """从本地路径（包目录或仓库根目录）定位包含 package.json 的包目录。"""
        source_path = source_path.resolve()
        if (source_path / "package.json").exists():
            return source_path
        candidate = source_path / "packages" / self.spec.package_name
        if (candidate / "package.json").exists():
            return candidate
        raise InstallError(f"无法从本地路径定位包目录：{source_path}")

    def _load_package_metadata(self, package_dir: Path) -> dict[str, Any]:
        """读取并解析包目录下的 package.json 元数据文件。"""
        package_json = package_dir / "package.json"
        if not package_json.exists():
            raise InstallError(f"未找到包元数据：{package_json}")
        return json.loads(package_json.read_text(encoding="utf-8"))

    def _target_install_dir(self) -> Path:
        """返回 TEXMFHOME 下该包的目标安装路径。"""
        return get_texmfhome(self.texmfhome_override) / self.spec.resolved_package_subpath()

    def _find_dependency_dirs(self, package_dir: Path) -> dict[str, Path]:
        """在包的兄弟目录中查找依赖包（如 bensz-fonts）的路径。"""
        found: dict[str, Path] = {}
        packages_root = package_dir.parent
        for slug in self.spec.dependency_package_names:
            candidate = packages_root / slug
            if candidate.exists():
                found[slug] = candidate
        return found

    def _state(self) -> dict[str, Any]:
        """加载全局状态（当前激活版本 + 历史列表）。"""
        return self._json_load(self.state_file, {})

    def _save_state(self, payload: dict[str, Any]) -> None:
        """持久化全局状态到 state.json。"""
        self._json_dump(self.state_file, payload)

    def _installed_package_version(self) -> str | None:
        """检测当前已安装的包版本。优先从 TEXMFHOME 下的 package.json 读取，其次从 state.json 推断。"""
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
        """从远程镜像获取指定 ref 对应的 package.json version 字段。"""
        raw_path = f"packages/{self.spec.package_name}/package.json"
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

    def _download_snapshot(self, ref: str, mirror: str) -> tuple[Path, Path, str]:
        """下载仓库快照并解压，返回 (临时目录, 包目录, 实际使用的镜像名)。"""
        last_error = None
        for current_mirror in iter_mirrors(mirror):
            temp_dir = Path(tempfile.mkdtemp(prefix=f"{self.spec.package_name}-"))
            archive = temp_dir / "snapshot.zip"
            extract_dir = temp_dir / "extract"
            try:
                self._download_file(mirror_archive_url(current_mirror, ref), archive)
                with zipfile.ZipFile(archive) as bundle:
                    bundle.extractall(extract_dir)
                repo_root = self._locate_repo_root(extract_dir)
                package_dir = repo_root / "packages" / self.spec.package_name
                if not package_dir.exists():
                    raise InstallError(f"快照中缺少 packages/{self.spec.package_name}")
                return temp_dir, package_dir, current_mirror
            except Exception as exc:  # noqa: BLE001
                shutil.rmtree(temp_dir, ignore_errors=True)
                last_error = f"{current_mirror}: {exc}"
        raise InstallError(f"无法下载 {self.spec.package_name}（ref={ref}, mirror={mirror}）。最后错误：{last_error}")

    def _cache_root_for(self, commit: str) -> Path:
        """返回指定 commit 对应的缓存根目录。"""
        return self.cache_root / commit

    def _cache_metadata(self, commit: str) -> dict[str, Any]:
        """加载指定 commit 的缓存元数据（metadata.json）。"""
        return self._json_load(self._cache_root_for(commit) / "metadata.json", {})

    def _cache_package(
        self,
        package_dir: Path,
        *,
        requested_ref: str,
        resolved_commit: str,
        source: str,
        dependency_dirs: dict[str, Path],
    ) -> dict[str, Any]:
        """将包文件及依赖写入本地缓存并生成 metadata.json。

        如果该 commit 的缓存已存在，会先清除再重新写入。同时会在 refs/ 下
        创建 ref -> commit 的映射文件，供后续 ``use`` 命令快速查找。

        Args:
            package_dir: 包文件的源目录
            requested_ref: 用户请求的 ref（如 ``v3.5.1``）
            resolved_commit: 解析后的缓存提交标识
            source: 来源标识（``github`` / ``gitee`` / ``local``）
            dependency_dirs: 依赖包路径字典 {slug: path}

        Returns:
            缓存元数据字典（与 metadata.json 内容一致）
        """
        cache_root = self._cache_root_for(resolved_commit)
        if cache_root.exists():
            shutil.rmtree(cache_root)
        cached_package_dir = cache_root / "package"
        cached_package_dir.mkdir(parents=True, exist_ok=True)
        copy_tree(package_dir, cached_package_dir)

        cached_dependencies: dict[str, str] = {}
        for slug, dependency_dir in dependency_dirs.items():
            cached_dependency_dir = cache_root / "dependencies" / slug
            cached_dependency_dir.mkdir(parents=True, exist_ok=True)
            copy_tree(dependency_dir, cached_dependency_dir)
            cached_dependencies[slug] = str(cached_dependency_dir)

        metadata = {
            "package_name": self.spec.package_name,
            "requested_ref": requested_ref,
            "resolved_commit": resolved_commit,
            "source": source,
            "package_version": self._load_package_metadata(package_dir).get("version"),
            "cached_at": self._timestamp(),
            "package_dir": str(cached_package_dir),
            "dependency_dirs": cached_dependencies,
        }
        self._json_dump(cache_root / "metadata.json", metadata)
        self._json_dump(
            self.refs_root / f"{self._safe_ref_name(requested_ref)}.json",
            {"requested_ref": requested_ref, "resolved_commit": resolved_commit, "source": source},
        )
        return metadata

    def _preview_metadata(
        self,
        package_dir: Path,
        *,
        requested_ref: str,
        resolved_commit: str,
        source: str,
        dependency_dirs: dict[str, Path],
    ) -> dict[str, Any]:
        """在 dry-run 模式下生成预览元数据（不写入磁盘）。"""
        return {
            "package_name": self.spec.package_name,
            "requested_ref": requested_ref,
            "resolved_commit": resolved_commit,
            "source": source,
            "package_version": self._load_package_metadata(package_dir).get("version"),
            "cached_at": self._timestamp(),
            "package_dir": str(package_dir),
            "dependency_dirs": {slug: str(path) for slug, path in dependency_dirs.items()},
            "dry_run": True,
        }

    def after_activate(self, commit: str, dry_run: bool = False) -> None:
        """激活后的钩子方法，子类可覆盖以执行额外操作（如写入 .nsfc-version）。"""
        return None

    def after_uninstall(self, dry_run: bool = False) -> None:
        """卸载后的钩子方法，子类可覆盖以执行额外清理操作。"""
        return None

    def status_details(self) -> list[str]:
        """返回额外的状态信息行，子类可覆盖。"""
        return []

    def _activate_commit(self, commit: str, dry_run: bool = False) -> dict[str, Any]:
        """将缓存的包文件激活（复制）到 TEXMFHOME 目标目录。

        激活流程：
        1. 读取 commit 对应的缓存元数据
        2. 清空目标安装目录并复制包文件
        3. 复制依赖包到 TEXMFHOME 对应子目录
        4. 运行 mktexlsr 刷新 TeX 文件名数据库
        5. 更新 state.json（current + history）

        Args:
            commit: 要激活的缓存提交标识
            dry_run: 若为 True，只返回预览信息不实际操作

        Returns:
            激活操作结果字典（包含 action、commit、install_path 等字段）
        """
        metadata = self._cache_metadata(commit)
        if not metadata:
            raise InstallError(f"未找到缓存版本：{commit}")

        target_dir = self._target_install_dir()
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if dry_run:
            activation = {
                "action": "activate",
                "commit": commit,
                "install_path": str(target_dir),
                "dry_run": True,
            }
            self.after_activate(commit, dry_run=True)
            return activation

        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        copy_tree(Path(metadata["package_dir"]), target_dir)

        texmfhome = get_texmfhome(self.texmfhome_override)
        for slug, dependency_dir in (metadata.get("dependency_dirs") or {}).items():
            dependency_target = texmfhome / "tex" / "latex" / slug
            if dependency_target.exists():
                shutil.rmtree(dependency_target)
            dependency_target.mkdir(parents=True, exist_ok=True)
            copy_tree(Path(dependency_dir), dependency_target)

        refresh_status, refresh_command = run_mktexlsr(texmfhome, False)
        self.after_activate(commit, dry_run=False)

        state = self._state()
        current = state.get("current") or {}
        history = list(state.get("history") or [])
        previous_commit = current.get("commit")
        ordered_history = [item for item in ([previous_commit] + history) if item and item != commit]

        activation = {
            "action": "activate",
            "commit": commit,
            "install_path": str(target_dir),
            "refresh_status": refresh_status,
            "refresh_command": refresh_command,
            "activated_at": self._timestamp(),
        }
        state["current"] = {
            "commit": commit,
            "requested_ref": metadata.get("requested_ref"),
            "source": metadata.get("source"),
            "package_version": metadata.get("package_version"),
            "install_path": str(target_dir),
            "activated_at": activation["activated_at"],
        }
        state["history"] = ordered_history[:20]
        self._save_state(state)
        return activation

    def _preview_activation(self, commit: str) -> dict[str, Any]:
        """在 dry-run 模式下预览激活操作的结果。"""
        target_dir = self._target_install_dir()
        self.after_activate(commit, dry_run=True)
        return {
            "action": "activate",
            "commit": commit,
            "install_path": str(target_dir),
            "dry_run": True,
        }

    def _cached_ref(self, ref: str) -> dict[str, Any] | None:
        """查找 ref 对应的缓存元数据。先查 refs 映射，再直接尝试 commit 目录。"""
        data = self._json_load(self.refs_root / f"{self._safe_ref_name(ref)}.json", None)
        if data and self._cache_root_for(data["resolved_commit"]).exists():
            return self._cache_metadata(data["resolved_commit"])
        if self._cache_root_for(ref).exists():
            return self._cache_metadata(ref)
        return None

    def install(
        self,
        *,
        ref: str = "main",
        source: str = "github",
        mirror: str = "github",
        activate: bool = True,
        dry_run: bool = False,
        force: bool = False,
        path: str | None = None,
    ) -> dict[str, Any]:
        """安装指定版本的公共包。

        安装流程：
        1. 根据 source 参数决定从本地路径或远程仓库获取包文件
        2. 对比已安装版本与目标版本，相同则跳过（除非 force=True）
        3. 将包文件写入本地缓存（commit 级别）
        4. 若 activate=True，将缓存文件复制到 TEXMFHOME 并刷新 TeX 数据库

        Args:
            ref: 目标版本标识（tag 名或分支名），默认 ``main``
            source: 来源类型，``local`` 从本地路径，其余走远程下载
            mirror: 镜像策略（``github`` / ``gitee`` / ``auto``）
            activate: 是否在缓存后立即激活到 TEXMFHOME
            dry_run: 若为 True，只返回预览信息不实际操作
            force: 强制重新安装，即使版本相同
            path: 当 source=local 时指定的本地路径

        Returns:
            安装结果字典（包含 requested_ref、package_version、activation 等字段）
        """
        if source == "local":
            package_dir = self._resolve_local_package_dir(Path(path or self.package_dir))
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
            commit = f"local-{hash_directory(package_dir)[:12]}"
            if dry_run:
                metadata = self._preview_metadata(
                    package_dir,
                    requested_ref=ref,
                    resolved_commit=commit,
                    source="local",
                    dependency_dirs=dependency_dirs,
                )
            elif force or not self._cache_root_for(commit).exists():
                metadata = self._cache_package(
                    package_dir,
                    requested_ref=ref,
                    resolved_commit=commit,
                    source="local",
                    dependency_dirs=dependency_dirs,
                )
            else:
                metadata = self._cache_metadata(commit)
        else:
            effective_mirror = source if source in {"github", "gitee"} else mirror
            target_version = self._fetch_remote_package_version(ref, effective_mirror)
            installed_version = self._installed_package_version()
            if should_skip_reinstall(installed_version, target_version, force=force):
                return {
                    "requested_ref": ref,
                    "source": effective_mirror,
                    "package_version": target_version,
                    "installed_version": installed_version,
                    "skipped": True,
                    "reason": "same_version",
                }

            temp_dir, package_dir, actual_mirror = self._download_snapshot(ref, effective_mirror)
            try:
                dependency_dirs = self._find_dependency_dirs(package_dir)
                commit = f"{actual_mirror}-{hash_directory(package_dir)[:12]}"
                if dry_run:
                    metadata = self._preview_metadata(
                        package_dir,
                        requested_ref=ref,
                        resolved_commit=commit,
                        source=actual_mirror,
                        dependency_dirs=dependency_dirs,
                    )
                elif force or not self._cache_root_for(commit).exists():
                    metadata = self._cache_package(
                        package_dir,
                        requested_ref=ref,
                        resolved_commit=commit,
                        source=actual_mirror,
                        dependency_dirs=dependency_dirs,
                    )
                else:
                    metadata = self._cache_metadata(commit)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if activate:
            metadata = dict(metadata)
            if dry_run and metadata.get("dry_run"):
                metadata["activation"] = self._preview_activation(metadata["resolved_commit"])
            else:
                metadata["activation"] = self._activate_commit(metadata["resolved_commit"], dry_run=dry_run)
        return metadata

    def use(self, ref: str, dry_run: bool = False) -> dict[str, Any]:
        """激活已缓存的版本。若该 ref 未缓存，则自动触发安装后再激活。

        Args:
            ref: 目标版本标识
            dry_run: 若为 True，只返回预览信息

        Returns:
            包含 activation 信息的结果字典
        """
        cached = self._cached_ref(ref)
        if cached is None:
            return self.install(ref=ref, source="github", mirror="github", activate=True, dry_run=dry_run)
        activation = self._activate_commit(cached["resolved_commit"], dry_run=dry_run)
        cached = dict(cached)
        cached["activation"] = activation
        return cached

    def rollback(self, dry_run: bool = False) -> dict[str, Any]:
        """回退到上一次激活的版本（从 state.json 的 history 列表取第一个）。

        Args:
            dry_run: 若为 True，只返回预览信息

        Returns:
            包含 rolled_back_to 和 activation 的结果字典

        Raises:
            InstallError: 当没有可回退的历史版本时
        """
        state = self._state()
        history = list(state.get("history") or [])
        if not history:
            raise InstallError("没有可回退的历史版本")
        previous = history[0]
        activation = self._activate_commit(previous, dry_run=dry_run)
        return {"rolled_back_to": previous, "activation": activation}

    def uninstall(self, dry_run: bool = False) -> dict[str, Any]:
        """从 TEXMFHOME 中卸载当前包并清除激活状态。"""
        target_dir = self._target_install_dir()
        result = {"target": str(target_dir), "removed": target_dir.exists(), "dry_run": dry_run}
        if target_dir.exists() and not dry_run:
            shutil.rmtree(target_dir)
            run_mktexlsr(get_texmfhome(self.texmfhome_override), False)
        self.after_uninstall(dry_run=dry_run)
        if not dry_run:
            state = self._state()
            current = state.get("current") or {}
            install_path = current.get("install_path")
            if install_path and Path(install_path).expanduser() == target_dir:
                state["current"] = None
                self._save_state(state)
        return result

    def status(self) -> dict[str, Any]:
        """查询当前安装状态，包括安装目录是否存在、当前激活版本和 kpsewhich 检测结果。"""
        target_dir = self._target_install_dir()
        kpsewhich = resolve_executable("kpsewhich")
        kpsewhich_result = None
        if kpsewhich:
            env = os.environ.copy()
            if self.texmfhome_override:
                env["TEXMFHOME"] = str(get_texmfhome(self.texmfhome_override))
            result = subprocess.run(
                [kpsewhich, self.spec.source_marker],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            kpsewhich_result = result.stdout.strip() or None
        return {
            "package_name": self.spec.package_name,
            "package_dir": str(target_dir),
            "exists": target_dir.exists(),
            "current": self._state().get("current"),
            "kpsewhich": kpsewhich_result,
            "details": self.status_details(),
        }

    def check(self) -> dict[str, Any]:
        """校验当前激活版本的一致性（状态记录与安装目录是否匹配）。"""
        state = self._state().get("current")
        if not state:
            return {"status": "no_active_version", "active": None}
        target_dir = self._target_install_dir()
        if not target_dir.exists():
            return {"status": "mismatch", "reason": "安装目录不存在", "active": state}
        return {"status": "match", "active": state}

    def list_cached(self) -> list[dict[str, Any]]:
        """列出所有已缓存版本的元数据。"""
        items: list[dict[str, Any]] = []
        if not self.cache_root.exists():
            return items
        for commit_dir in sorted(self.cache_root.iterdir(), key=lambda d: d.name):
            metadata_file = commit_dir / "metadata.json"
            if metadata_file.exists():
                items.append(self._json_load(metadata_file, {}))
        return items

    def prune(self, *, dry_run: bool = False) -> dict[str, Any]:
        """清理不再需要的缓存版本。仅保留当前激活版本和历史列表中的版本。

        Args:
            dry_run: 若为 True，只返回将被清理的列表但不实际删除

        Returns:
            包含 kept（保留列表）和 removed（已清理列表）的结果字典
        """
        state = self._state()
        current = state.get("current") or {}
        keep = {item for item in [current.get("commit")] + list(state.get("history") or []) if item}
        removed: list[str] = []
        if not self.cache_root.exists():
            return {"kept": sorted(keep), "removed": removed}
        for commit_dir in self.cache_root.iterdir():
            if commit_dir.name in keep:
                continue
            removed.append(commit_dir.name)
            if not dry_run:
                shutil.rmtree(commit_dir, ignore_errors=True)
        return {"kept": sorted(keep), "removed": sorted(removed)}


class ProjectLockMixin:
    """可混入 VersionedPackageManager 的项目级版本锁定能力。

    项目级版本锁定允许单个 LaTeX 项目（如 projects/NSFC_Young/）将其依赖的公共包版本
    固定到特定 commit，确保团队协作和 CI 环境下的一致性。

    锁定机制通过项目根目录下的锁文件（如 ``.nsfc-version``）实现。锁文件是 JSON 格式，
    记录了 ref、commit、package_name、package_version 等字段。

    提供的命令：
    - ``pin``：将当前激活版本写入锁文件
    - ``sync``：根据锁文件安装并激活指定版本
    - ``check``：校验当前激活版本与锁文件是否一致
    - ``unpin``：删除锁文件

    子类需要设置 ``lockfile_name`` 属性（如 ``".nsfc-version"``）和可选的
    ``template_ids`` 属性。
    """

    lockfile_name: str  # 锁文件名，如 ".nsfc-version"
    template_ids: tuple[str, ...] = ()  # 支持的模板标识列表

    def _find_project_root(self) -> Path:
        """从当前工作目录向上搜索，定位包含锁文件或 LaTeX 入口文件的项目根目录。"""
        for candidate in [self.cwd, *self.cwd.parents]:  # type: ignore[attr-defined]
            if (candidate / self.lockfile_name).exists():
                return candidate
            if (candidate / "main.tex").exists() and (candidate / "extraTex" / "@config.tex").exists():
                return candidate
        return self.cwd  # type: ignore[attr-defined]

    def _lockfile_path(self) -> Path:
        """返回锁文件的完整路径。"""
        return self._find_project_root() / self.lockfile_name

    def _detect_template_id(self, project_root: Path) -> str:
        """检测项目使用的模板标识，子类可覆盖。默认返回空字符串。"""
        return ""

    def read_lockfile(self) -> dict[str, Any]:
        """读取并解析锁文件内容。锁文件不存在时抛出 InstallError。"""
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            raise InstallError(f"当前目录未锁定版本：{lockfile}")
        return self._json_load(lockfile, {})  # type: ignore[attr-defined]

    def pin(self, ref: str | None = None, *, dry_run: bool = False) -> dict[str, Any]:
        """将指定版本锁定到项目目录下的锁文件。

        如果提供了 ref，则查找或安装该 ref 的缓存版本；否则使用当前激活版本。
        锁文件写入后，团队成员可通过 ``sync`` 命令恢复到相同版本。

        Args:
            ref: 要锁定的版本标识，None 表示锁定当前激活版本
            dry_run: 若为 True，只返回预览信息不写入锁文件

        Returns:
            锁文件内容字典
        """
        project_root = self._find_project_root()
        state = self._state().get("current")  # type: ignore[attr-defined]
        metadata: dict[str, Any]
        if ref:
            metadata = self._cached_ref(ref) or self.install(ref=ref, activate=False, dry_run=dry_run)  # type: ignore[attr-defined]
        elif state:
            metadata = self._cache_metadata(state["commit"])  # type: ignore[attr-defined]
        else:
            raise InstallError("当前没有激活版本，也没有提供 --ref")

        template_id = self._detect_template_id(project_root)
        template_meta = metadata.get("templates", {}).get(template_id, {}) if template_id else {}
        payload: dict[str, Any] = {
            "ref": ref or metadata.get("requested_ref"),
            "commit": metadata["resolved_commit"],
            "package_name": metadata.get("package_name", self.spec.package_name),  # type: ignore[attr-defined]
            "package_version": metadata.get("package_version"),
        }
        if template_id:
            payload["template_id"] = template_id
            payload["template_version"] = template_meta.get("template_version")
        if not dry_run:
            self._json_dump(self._lockfile_path(), payload)  # type: ignore[attr-defined]
        return payload

    def sync(self, *, dry_run: bool = False) -> dict[str, Any]:
        """根据锁文件同步安装版本。若缓存中已有对应 commit 则直接激活，否则重新安装。

        Args:
            dry_run: 若为 True，只返回预览信息

        Returns:
            包含 lockfile 和 activation 的结果字典
        """
        lock = self.read_lockfile()
        commit = lock.get("commit")
        if not commit:
            raise InstallError("锁文件缺少 commit")
        if self._cache_root_for(commit).exists():  # type: ignore[attr-defined]
            activation = self._activate_commit(commit, dry_run=dry_run)  # type: ignore[attr-defined]
            return {"lockfile": lock, "activation": activation}
        requested = lock.get("ref") or commit
        return self.install(ref=requested, activate=True, dry_run=dry_run)  # type: ignore[attr-defined]

    def unpin(self, *, dry_run: bool = False) -> dict[str, Any]:
        """删除项目目录下的版本锁文件。"""
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            return {"removed": False, "path": str(lockfile)}
        if not dry_run:
            lockfile.unlink()
        return {"removed": True, "path": str(lockfile)}

    def check(self) -> dict[str, Any]:
        """校验当前激活版本与锁文件的一致性。

        比较维度包括 commit、package_version 和可选的 template_version。
        返回的 status 字段含义：
        - ``unlocked``：项目未锁定版本
        - ``match``：当前激活版本与锁文件完全一致
        - ``mismatch``：存在不一致或未激活任何版本
        """
        state = self._state().get("current")  # type: ignore[attr-defined]
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            return {"status": "unlocked", "active": state}
        lock = self._json_load(lockfile, {})  # type: ignore[attr-defined]
        if not state:
            return {"status": "mismatch", "reason": "未激活任何版本", "lockfile": lock}

        commit_match = state.get("commit") == lock.get("commit")
        package_match = state.get("package_version") == lock.get("package_version")
        template_match = True
        template_id = lock.get("template_id")
        if template_id:
            cached = self._cache_metadata(lock["commit"]) if self._cache_root_for(lock["commit"]).exists() else None  # type: ignore[attr-defined]
            if cached:
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
