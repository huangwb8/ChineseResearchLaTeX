#!/usr/bin/env python3
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


REPO_OWNER = "huangwb8"
REPO_NAME = "ChineseResearchLaTeX"
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


class InstallError(RuntimeError):
    pass


@dataclass(frozen=True)
class PackageSpec:
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
    return Path.home() / ".ChineseResearchLaTeX"


def configure_windows_stdio_utf8() -> None:
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
    return bool(installed_version and target_version and installed_version == target_version and not force)


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


def run_mktexlsr(texmfhome: Path, dry_run: bool) -> tuple[str, str | None]:
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
    import hashlib

    digest = hashlib.sha256()
    for file_path in sorted(path for path in directory.rglob("*") if path.is_file()):
        if any(part in EXCLUDE_NAMES for part in file_path.parts) or file_path.suffix == ".pyc":
            continue
        digest.update(str(file_path.relative_to(directory)).encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def prefer_gitee_for_auto() -> bool:
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
    if mirror in {"github", "gitee"}:
        return (mirror,)
    if mirror == "auto":
        return ("gitee", "github") if prefer_gitee_for_auto() else ("github", "gitee")
    raise InstallError(f"不支持的镜像：{mirror}")


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


class VersionedPackageManager:
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
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _safe_ref_name(self, ref: str) -> str:
        return urllib.parse.quote(ref, safe="").replace("%", "_")

    def _json_load(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _json_dump(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _github_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ChineseResearchLaTeX-install.py",
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _download_file(self, url: str, destination: Path) -> None:
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                destination.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            raise InstallError(f"下载失败：{exc.code} {url}") from exc
        except urllib.error.URLError as exc:
            raise InstallError(f"无法下载资源：{url}") from exc

    def _try_fetch_text(self, url: str) -> str | None:
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                return response.read().decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError):
            return None

    def _locate_repo_root(self, extract_dir: Path) -> Path:
        children = [path for path in extract_dir.iterdir() if path.is_dir()]
        if len(children) == 1:
            return children[0]
        for candidate in children:
            if (candidate / "packages" / self.spec.package_name / "package.json").exists():
                return candidate
        raise InstallError(f"无法从快照中定位仓库根目录：{extract_dir}")

    def _resolve_local_package_dir(self, source_path: Path) -> Path:
        source_path = source_path.resolve()
        if (source_path / "package.json").exists():
            return source_path
        candidate = source_path / "packages" / self.spec.package_name
        if (candidate / "package.json").exists():
            return candidate
        raise InstallError(f"无法从本地路径定位包目录：{source_path}")

    def _load_package_metadata(self, package_dir: Path) -> dict[str, Any]:
        package_json = package_dir / "package.json"
        if not package_json.exists():
            raise InstallError(f"未找到包元数据：{package_json}")
        return json.loads(package_json.read_text(encoding="utf-8"))

    def _target_install_dir(self) -> Path:
        return get_texmfhome(self.texmfhome_override) / self.spec.resolved_package_subpath()

    def _find_dependency_dirs(self, package_dir: Path) -> dict[str, Path]:
        found: dict[str, Path] = {}
        packages_root = package_dir.parent
        for slug in self.spec.dependency_package_names:
            candidate = packages_root / slug
            if candidate.exists():
                found[slug] = candidate
        return found

    def _state(self) -> dict[str, Any]:
        return self._json_load(self.state_file, {})

    def _save_state(self, payload: dict[str, Any]) -> None:
        self._json_dump(self.state_file, payload)

    def _installed_package_version(self) -> str | None:
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
        return self.cache_root / commit

    def _cache_metadata(self, commit: str) -> dict[str, Any]:
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
        return None

    def after_uninstall(self, dry_run: bool = False) -> None:
        return None

    def status_details(self) -> list[str]:
        return []

    def _activate_commit(self, commit: str, dry_run: bool = False) -> dict[str, Any]:
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
        target_dir = self._target_install_dir()
        self.after_activate(commit, dry_run=True)
        return {
            "action": "activate",
            "commit": commit,
            "install_path": str(target_dir),
            "dry_run": True,
        }

    def _cached_ref(self, ref: str) -> dict[str, Any] | None:
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
        cached = self._cached_ref(ref)
        if cached is None:
            return self.install(ref=ref, source="github", mirror="github", activate=True, dry_run=dry_run)
        activation = self._activate_commit(cached["resolved_commit"], dry_run=dry_run)
        cached = dict(cached)
        cached["activation"] = activation
        return cached

    def rollback(self, dry_run: bool = False) -> dict[str, Any]:
        state = self._state()
        history = list(state.get("history") or [])
        if not history:
            raise InstallError("没有可回退的历史版本")
        previous = history[0]
        activation = self._activate_commit(previous, dry_run=dry_run)
        return {"rolled_back_to": previous, "activation": activation}

    def uninstall(self, dry_run: bool = False) -> dict[str, Any]:
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
        state = self._state().get("current")
        if not state:
            return {"status": "no_active_version", "active": None}
        target_dir = self._target_install_dir()
        if not target_dir.exists():
            return {"status": "mismatch", "reason": "安装目录不存在", "active": state}
        return {"status": "match", "active": state}

    def list_cached(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if not self.cache_root.exists():
            return items
        for commit_dir in sorted(self.cache_root.iterdir(), key=lambda d: d.name):
            metadata_file = commit_dir / "metadata.json"
            if metadata_file.exists():
                items.append(self._json_load(metadata_file, {}))
        return items

    def prune(self, *, dry_run: bool = False) -> dict[str, Any]:
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
    """可混入 VersionedPackageManager 的项目级版本锁定能力。"""

    lockfile_name: str
    template_ids: tuple[str, ...] = ()

    def _find_project_root(self) -> Path:
        for candidate in [self.cwd, *self.cwd.parents]:  # type: ignore[attr-defined]
            if (candidate / self.lockfile_name).exists():
                return candidate
            if (candidate / "main.tex").exists() and (candidate / "extraTex" / "@config.tex").exists():
                return candidate
        return self.cwd  # type: ignore[attr-defined]

    def _lockfile_path(self) -> Path:
        return self._find_project_root() / self.lockfile_name

    def _detect_template_id(self, project_root: Path) -> str:
        return ""

    def read_lockfile(self) -> dict[str, Any]:
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            raise InstallError(f"当前目录未锁定版本：{lockfile}")
        return self._json_load(lockfile, {})  # type: ignore[attr-defined]

    def pin(self, ref: str | None = None, *, dry_run: bool = False) -> dict[str, Any]:
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
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            return {"removed": False, "path": str(lockfile)}
        if not dry_run:
            lockfile.unlink()
        return {"removed": True, "path": str(lockfile)}

    def check(self) -> dict[str, Any]:
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
