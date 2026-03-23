from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


package_version_manager = _load_module(
    "project_package_version_manager",
    REPO_ROOT / "scripts" / "package_version_manager.py",
)
paper_install_script = _load_module(
    "project_paper_install_script",
    REPO_ROOT / "packages" / "bensz-paper" / "scripts" / "package" / "install.py",
)
thesis_install_script = _load_module(
    "project_thesis_install_script",
    REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "package" / "install.py",
)
cv_install_script = _load_module(
    "project_cv_install_script",
    REPO_ROOT / "packages" / "bensz-cv" / "scripts" / "package" / "install.py",
)


def _make_fake_package(root: Path, package_name: str, version: str, marker_file: str) -> Path:
    package_dir = root / package_name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "package.json").write_text(
        json.dumps({"name": package_name, "version": version}, ensure_ascii=False),
        encoding="utf-8",
    )
    (package_dir / marker_file).write_text(f"{package_name} {version}\n", encoding="utf-8")
    (package_dir / "scripts").mkdir(exist_ok=True)
    return package_dir


def test_versioned_package_manager_install_and_rollback_for_local_sources(tmp_path: Path):
    spec = package_version_manager.PackageSpec(
        package_name="demo-package",
        source_marker="demo-package.sty",
    )
    manager = package_version_manager.VersionedPackageManager(
        spec=spec,
        cwd=tmp_path,
        texmfhome_override=str(tmp_path / "texmf"),
        state_root_override=tmp_path / ".demo-state",
    )

    v1_dir = _make_fake_package(tmp_path / "src", "demo-package", "p_v1", "demo-package.sty")
    v2_dir = _make_fake_package(tmp_path / "src2", "demo-package", "p_v2", "demo-package.sty")

    first = manager.install(source="local", path=str(v1_dir))
    second = manager.install(source="local", path=str(v2_dir))
    rollback = manager.rollback()

    dest = tmp_path / "texmf" / "tex" / "latex" / "demo-package" / "demo-package.sty"
    assert first["package_version"] == "p_v1"
    assert second["package_version"] == "p_v2"
    assert rollback["activation"]["commit"] == first["resolved_commit"]
    assert dest.read_text(encoding="utf-8") == "demo-package p_v1\n"


def test_versioned_package_manager_installed_version_ignores_other_texmfhome(tmp_path: Path):
    spec = package_version_manager.PackageSpec(
        package_name="demo-package",
        source_marker="demo-package.sty",
    )
    manager = package_version_manager.VersionedPackageManager(
        spec=spec,
        cwd=tmp_path,
        texmfhome_override=str(tmp_path / "texmf-a"),
        state_root_override=tmp_path / ".demo-state",
    )
    manager._save_state(
        {
            "current": {
                "package_version": "p_v1",
                "install_path": str(tmp_path / "texmf-b" / "tex" / "latex" / "demo-package"),
            }
        }
    )

    assert manager._installed_package_version() is None


def test_versioned_package_manager_defaults_under_chineseresearchlatex_home():
    spec = package_version_manager.PackageSpec(
        package_name="demo-package",
        source_marker="demo-package.sty",
    )
    manager = package_version_manager.VersionedPackageManager(spec=spec)

    assert manager.state_root == Path.home() / ".ChineseResearchLaTeX" / "demo-package"


def test_versioned_package_manager_dry_run_does_not_persist_cache_or_state(tmp_path: Path):
    spec = package_version_manager.PackageSpec(
        package_name="demo-package",
        source_marker="demo-package.sty",
    )
    state_root = tmp_path / ".demo-state"
    manager = package_version_manager.VersionedPackageManager(
        spec=spec,
        cwd=tmp_path,
        texmfhome_override=str(tmp_path / "texmf"),
        state_root_override=state_root,
    )
    package_dir = _make_fake_package(tmp_path / "src", "demo-package", "p_v1", "demo-package.sty")

    result = manager.install(source="local", path=str(package_dir), dry_run=True)

    assert result["activation"]["dry_run"] is True
    assert manager._state() == {}
    assert not any(state_root.joinpath("cache", "commits").glob("*"))


def test_package_installers_support_versioned_cli_and_legacy_status_flag():
    args = paper_install_script.parse_args(["install", "--ref", "main"])
    assert args.command == "install"
    assert args.ref == "main"
    assert args.mirror == "github"

    legacy = paper_install_script.parse_args(["--status"])
    assert legacy.command == "status"

    thesis_args = thesis_install_script.parse_args(["use", "--ref", "v1.2.3"])
    assert thesis_args.command == "use"
    assert thesis_args.ref == "v1.2.3"

    cv_args = cv_install_script.parse_args(["rollback"])
    assert cv_args.command == "rollback"
