#!/usr/bin/env python3
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

REPO_OWNER = "huangwb8"
REPO_NAME = "ChineseResearchLaTeX"
PACKAGE_SLUG = "bensz-nsfc"
PACKAGE_NAME = "bensz-nsfc-common"
DEPENDENCY_PACKAGE_SLUGS = ("bensz-fonts",)
PACKAGE_SOURCE_RELATIVE = Path("packages") / PACKAGE_SLUG
LOCKFILE_NAME = ".nsfc-version"
PACKAGE_DIR = Path(__file__).resolve().parents[1]


def should_skip_reinstall(
    installed_version: str | None,
    target_version: str | None,
    *,
    force: bool,
) -> bool:
    return bool(installed_version and target_version and installed_version == target_version and not force)


def discover_repo_root() -> Path:
    for candidate in [PACKAGE_DIR, *PACKAGE_DIR.parents]:
        if (candidate / "packages" / PACKAGE_SLUG / "package.json").exists():
            return candidate
    return PACKAGE_DIR.parents[1]


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
    def __init__(self, cwd: Path | None = None, texmfhome_override: str | None = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()
        self.texmfhome_override = texmfhome_override
        self.package_dir = PACKAGE_DIR
        self.repo_root = discover_repo_root()
        self.state_root = Path.home() / ".bensz-nsfc"
        self.cache_root = self.state_root / "cache" / "commits"
        self.refs_root = self.state_root / "cache" / "refs"
        self.state_file = self.state_root / "state.json"
        self.registry_file = self.state_root / "registry.json"
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

    def _fetch_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers=self._github_headers())
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise InstallError(f"GitHub API 请求失败：{exc.code} {url}") from exc
        except urllib.error.URLError as exc:
            raise InstallError(f"无法访问远端资源：{url}") from exc

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

    def _load_package_metadata(self, package_dir: Path) -> dict[str, Any]:
        package_json = package_dir / "package.json"
        if not package_json.exists():
            raise InstallError(f"未找到包元数据：{package_json}")
        return json.loads(package_json.read_text(encoding="utf-8"))

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
        found: dict[str, Path] = {}
        packages_root = package_dir.parent
        for slug in DEPENDENCY_PACKAGE_SLUGS:
            candidate = packages_root / slug
            if candidate.exists():
                found[slug] = candidate
        return found

    def _hash_directory(self, directory: Path) -> str:
        digest = hashlib.sha256()
        for file_path in sorted(p for p in directory.rglob("*") if p.is_file()):
            digest.update(str(file_path.relative_to(directory)).encode("utf-8"))
            digest.update(file_path.read_bytes())
        return digest.hexdigest()

    def _resolve_local_package_dir(self, source_path: Path) -> Path:
        source_path = source_path.resolve()
        if (source_path / "package.json").exists():
            return source_path
        candidate = source_path / PACKAGE_SOURCE_RELATIVE
        if (candidate / "package.json").exists():
            return candidate
        raise InstallError(f"无法从本地路径定位包目录：{source_path}")

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
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
        metadata_file = self.cache_root / commit / "metadata.json"
        if not metadata_file.exists():
            raise InstallError(f"缓存元数据不存在：{metadata_file}")
        return self._json_load(metadata_file, {})

    def _download_github_snapshot(self, commit: str) -> tuple[Path, Path]:
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
        return self._get_texmf_home() / "tex" / "latex" / PACKAGE_SLUG

    def _state(self) -> dict[str, Any]:
        return self._json_load(self.state_file, {})

    def _save_state(self, payload: dict[str, Any]) -> None:
        self._json_dump(self.state_file, payload)

    def _write_runtime_file(self, package_dir: Path) -> None:
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
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            raise InstallError(f"当前目录未锁定版本：{lockfile}")
        return self._json_load(lockfile, {})

    def sync(self, dry_run: bool = False) -> dict[str, Any]:
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
        previous = self._state().get("previous_commit")
        if not previous:
            raise InstallError("没有可回退的上一版本")
        if not self._cache_root_for(previous).exists():
            raise InstallError(f"上一版本缓存不存在：{previous}")
        activation = self._activate_commit(previous, dry_run=dry_run)
        return {"rolled_back_to": previous, "activation": activation}

    def uninstall(self, dry_run: bool = False) -> dict[str, Any]:
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
        state = self._state()
        current = state.get("current")
        result = {"current": current, "previous_commit": state.get("previous_commit")}
        if current and self._cache_root_for(current["commit"]).exists():
            result["cached_metadata"] = self._cache_metadata(current["commit"])
        return result

    def list_cached(self) -> list[dict[str, Any]]:
        items = []
        for commit_dir in sorted(self.cache_root.iterdir(), key=lambda item: item.name):
            metadata_file = commit_dir / "metadata.json"
            if metadata_file.exists():
                items.append(self._json_load(metadata_file, {}))
        return items

    def list_remote(self) -> dict[str, Any]:
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
        resolved = self._resolve_ref(ref)
        metadata = self._cached_ref(ref)
        return {"resolved": resolved, "cached": metadata}

    def unpin(self, dry_run: bool = False) -> dict[str, Any]:
        lockfile = self._lockfile_path()
        if not lockfile.exists():
            return {"removed": False, "path": str(lockfile)}
        if not dry_run:
            lockfile.unlink()
        return {"removed": True, "path": str(lockfile)}

    def prune(self, dry_run: bool = False) -> dict[str, Any]:
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
