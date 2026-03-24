from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


install_script = _load_module("project_install_script", REPO_ROOT / "scripts" / "install.py")
nsfc_install_script = _load_module(
    "project_nsfc_install_script",
    REPO_ROOT / "packages" / "bensz-nsfc" / "scripts" / "install.py",
)
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


def test_repo_level_pytest_cache_is_redirected_under_tests():
    pytest_ini = REPO_ROOT / "pytest.ini"

    assert pytest_ini.exists(), "pytest 配置必须留在仓库根目录，不能简单挪到 tests/ 子目录"
    content = pytest_ini.read_text(encoding="utf-8")

    assert "[pytest]" in content
    assert "cache_dir = tests/.pytest_cache" in content


def test_default_requested_packages_covers_all_supported_packages():
    assert install_script.default_requested_packages() == list(install_script.SUPPORTED_PACKAGES)


def test_should_skip_reinstall_when_versions_match_without_force():
    assert install_script.should_skip_reinstall("p_v20260322", "p_v20260322", force=False) is True
    assert install_script.should_skip_reinstall("p_v20260322", "p_v20260322", force=True) is False
    assert install_script.should_skip_reinstall("p_v20260322", "p_v20260323", force=False) is False


def test_build_parser_defaults_to_installing_all_packages():
    parser = install_script.build_parser()
    args = parser.parse_args(["install"])

    assert args.packages == ",".join(install_script.default_requested_packages())
    assert args.force is False


def test_cmd_install_passes_force_to_package_installers(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, bool]] = []

    monkeypatch.setattr(
        install_script,
        "_install_delegated_package",
        lambda package_name, ref, extra, mirror, texmfhome=None, force=False: calls.append(
            (package_name, force)
        ),
    )

    install_script.cmd_install(
        ["bensz-paper", "bensz-nsfc"],
        "main",
        [],
        "github",
        texmfhome="/tmp/texmf",
        force=True,
    )

    assert ("bensz-paper", True) in calls
    assert ("bensz-nsfc", True) in calls


def test_version_managed_packages_use_delegate_install_mode():
    for package_name in ("bensz-nsfc", "bensz-paper", "bensz-thesis", "bensz-cv"):
        assert install_script.SUPPORTED_PACKAGES[package_name]["install_mode"] == "delegate"
        assert install_script.SUPPORTED_PACKAGES[package_name]["installer_path"]


def test_nsfc_should_skip_reinstall_when_versions_match_without_force():
    assert nsfc_install_script.should_skip_reinstall("p_v20260315", "p_v20260315", force=False) is True
    assert nsfc_install_script.should_skip_reinstall("p_v20260315", "p_v20260315", force=True) is False
    assert nsfc_install_script.should_skip_reinstall("p_v20260315", "p_v20260316", force=False) is False


def test_nsfc_installed_version_ignores_state_from_other_texmfhome(tmp_path: Path):
    texmfhome = tmp_path / "texmf-a"
    manager = nsfc_install_script.NSFCPackageManager(cwd=tmp_path, texmfhome_override=str(texmfhome))
    other_install = tmp_path / "texmf-b" / "tex" / "latex" / "bensz-nsfc"
    manager._save_state(
        {
            "current": {
                "package_version": "p_v20260315",
                "install_path": str(other_install),
            }
        }
    )

    assert manager._installed_package_version() is None


def test_nsfc_state_root_is_under_chineseresearchlatex_home():
    manager = nsfc_install_script.NSFCPackageManager()

    assert manager.state_root == Path.home() / ".ChineseResearchLaTeX" / "bensz-nsfc"


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


def test_pack_project_preserves_ucas_thesis_project_files(tmp_path: Path):
    project_dir = REPO_ROOT / "projects" / "thesis-ucas-doctor"
    zip_path = pack_release.pack_project(project_dir, tmp_path, "v-test")

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    assert "main.tex" in names
    assert "chapter1.tex" in names
    assert "extraTex/chapter1.tex" in names
    assert "bibs/references.bib" in names
    assert "template.json" in names
    assert "source-baseline.pdf" not in names
    assert "scripts/export_docx.py" not in names


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
    assert pack_release.select_overleaf_font_files(
        REPO_ROOT / "projects" / "thesis-ucas-doctor"
    ) == {
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
