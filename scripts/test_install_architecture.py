from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


install_script = _load_module("project_install_script", REPO_ROOT / "scripts" / "install.py")
pack_release = _load_module("project_pack_release", REPO_ROOT / "scripts" / "pack_release.py")


def test_resolve_requested_packages_adds_bensz_fonts_dependency():
    assert install_script.resolve_requested_packages(["bensz-paper"]) == [
        "bensz-fonts",
        "bensz-paper",
    ]


def test_resolve_requested_packages_deduplicates_fonts_and_preserves_order():
    assert install_script.resolve_requested_packages(
        ["bensz-cv", "bensz-fonts", "bensz-paper"]
    ) == [
        "bensz-fonts",
        "bensz-cv",
        "bensz-paper",
    ]


def test_build_remote_repo_supports_gitee_endpoints():
    repo = install_script.build_remote_repo("gitee")

    assert repo.name == "gitee"
    assert repo.raw_url("main", "scripts/install.py") == (
        "https://gitee.com/huangwb8/ChineseResearchLaTeX/raw/main/scripts/install.py"
    )
    assert repo.archive_url("v4.0.2") == (
        "https://gitee.com/huangwb8/ChineseResearchLaTeX/repository/archive/v4.0.2.zip"
    )


def test_build_remote_repo_keeps_github_as_default_source():
    repo = install_script.build_remote_repo("github")

    assert repo.name == "github"
    assert repo.raw_url("main", "scripts/install.py") == (
        "https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py"
    )
    assert repo.archive_url("main") == (
        "https://api.github.com/repos/huangwb8/ChineseResearchLaTeX/zipball/main"
    )


def test_add_nsfc_runtime_bundle_includes_bensz_fonts(tmp_path: Path):
    zip_path = tmp_path / "nsfc-runtime.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        pack_release.add_nsfc_runtime_bundle(zf)

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    assert "bensz-fonts.sty" in names
    assert "fonts/Kaiti.ttf" in names
    assert "fonts/TimesNewRoman.ttf" in names
    assert "fonts/NotoSerifCJKsc-Regular.otf" not in names


def test_add_paper_runtime_bundle_includes_bensz_fonts(tmp_path: Path):
    project_dir = REPO_ROOT / "projects" / "paper-sci-01"
    zip_path = pack_release.pack_project_overleaf(project_dir, tmp_path, "v-test")

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    assert "bensz-fonts.sty" not in names
    assert "fonts/TimesNewRoman.ttf" not in names


def test_add_cv_runtime_bundle_includes_shared_cv_fonts(tmp_path: Path):
    zip_path = tmp_path / "cv-runtime.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        pack_release.add_cv_runtime_bundle(zf)

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    assert "bensz-fonts.sty" in names
    assert "fonts/NotoSerifCJKsc-Regular.otf" in names
    assert "fonts/AdobeSongStd-Light.otf" not in names


def test_select_overleaf_fonts_matches_project_requirements():
    assert pack_release.select_overleaf_font_files(REPO_ROOT / "projects" / "NSFC_General") == {
        "Kaiti.ttf",
        "TimesNewRoman.ttf",
    }
    assert pack_release.select_overleaf_font_files(REPO_ROOT / "projects" / "paper-sci-01") == set()
    assert pack_release.select_overleaf_font_files(REPO_ROOT / "projects" / "thesis-smu-master") == set()
    assert pack_release.select_overleaf_font_files(REPO_ROOT / "projects" / "thesis-sysu-doctor") == {
        "TimesNewRoman.ttf",
    }
    assert pack_release.select_overleaf_font_files(REPO_ROOT / "projects" / "cv-01") == {
        "FontAwesome.otf",
        "Fontin-SmallCaps.otf",
        "NotoSerifCJKsc-Bold.otf",
        "NotoSerifCJKsc-Regular.otf",
        "texgyretermes-bold.otf",
        "texgyretermes-bolditalic.otf",
        "texgyretermes-italic.otf",
        "texgyretermes-regular.otf",
    }
