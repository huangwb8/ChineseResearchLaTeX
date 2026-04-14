from __future__ import annotations

import importlib.util
import sys
import tempfile
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


def test_delegate_install_skips_before_downloading_installer_when_versions_match(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(
        install_script,
        "_fetch_remote_package_metadata",
        lambda package_name, ref, mirror: ({"version": "v1.2.3"}, "github"),
    )
    monkeypatch.setattr(install_script, "_installed_package_version", lambda *args, **kwargs: "v1.2.3")

    def fail_if_downloading(*args, **kwargs):
        raise AssertionError("命中快速跳过后不应再下载委托安装器")

    monkeypatch.setattr(install_script, "_try_fetch_text", fail_if_downloading)

    install_script._install_delegated_package(
        "bensz-paper",
        "v1.2.3",
        [],
        "github",
    )

    captured = capsys.readouterr()
    assert "跳过重复安装" in captured.out
    assert "下载 bensz-paper 安装器" not in captured.out


def test_delegate_install_force_bypasses_fast_skip_and_downloads_installer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    installer_dir = tmp_path / "delegate-installer"
    installer_dir.mkdir()
    monkeypatch.setattr(
        install_script,
        "_fetch_remote_package_metadata",
        lambda package_name, ref, mirror: ({"version": "v1.2.3"}, "github"),
    )
    monkeypatch.setattr(install_script, "_installed_package_version", lambda *args, **kwargs: "v1.2.3")
    monkeypatch.setattr(install_script, "_download_delegate_support_files", lambda *args, **kwargs: None)
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": str(installer_dir))
    monkeypatch.setattr(
        install_script,
        "iter_remote_repos",
        lambda mirror: [install_script.build_remote_repo("github")],
    )
    monkeypatch.setattr(install_script, "_try_fetch_text", lambda url: "print('installer')\n")

    calls: list[list[str]] = []

    def fake_subprocess_run(cmd, check, env):
        calls.append(cmd)
        return None

    monkeypatch.setattr(install_script.subprocess, "run", fake_subprocess_run)

    install_script._install_delegated_package(
        "bensz-paper",
        "v1.2.3",
        [],
        "github",
        force=True,
    )

    captured = capsys.readouterr()
    assert "下载 bensz-paper 安装器" in captured.out
    assert calls, "force=True 时应继续执行委托安装器"


def test_delegate_install_falls_back_to_installer_when_remote_metadata_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    installer_dir = tmp_path / "delegate-installer"
    installer_dir.mkdir()
    monkeypatch.setattr(install_script, "_fetch_remote_package_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr(install_script, "_download_delegate_support_files", lambda *args, **kwargs: None)
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": str(installer_dir))
    monkeypatch.setattr(
        install_script,
        "iter_remote_repos",
        lambda mirror: [install_script.build_remote_repo("github")],
    )
    monkeypatch.setattr(install_script, "_try_fetch_text", lambda url: "print('installer')\n")

    calls: list[list[str]] = []

    def fake_subprocess_run(cmd, check, env):
        calls.append(cmd)
        return None

    monkeypatch.setattr(install_script.subprocess, "run", fake_subprocess_run)

    install_script._install_delegated_package(
        "bensz-paper",
        "main",
        [],
        "github",
    )

    captured = capsys.readouterr()
    assert "下载 bensz-paper 安装器" in captured.out
    assert calls, "metadata 拉取失败时应降级到原有委托安装流程"


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
    assert "extraTex/chapter1.tex" in names
    assert "extraTex/chapter2.tex" in names
    assert "extraTex/acknowledgements.tex" in names
    assert "extraTex/cv.tex" in names
    assert "chapter1.tex" not in names
    assert "bibs/references.bib" in names
    assert "template.json" in names
    assert "source-baseline.pdf" not in names
    assert "scripts/export_docx.py" in names


def test_detect_thesis_template_id_prefers_postdoc_template_identity():
    project_dir = REPO_ROOT / "projects" / "thesis-smu-postdoc"

    assert pack_release.detect_thesis_template_id(project_dir) == "thesis-smu-postdoc"


def test_build_thesis_runtime_bundle_uses_independent_postdoc_profile_and_style(tmp_path: Path):
    runtime_dir = tmp_path / "thesis-runtime"
    project_dir = REPO_ROOT / "projects" / "thesis-smu-postdoc"

    pack_release.build_thesis_runtime_bundle(runtime_dir, project_dir)

    assert (runtime_dir / "profiles" / "bthesis-profile-thesis-smu-postdoc.def").exists()
    assert (runtime_dir / "bthesis-style-thesis-smu-postdoc.tex").exists()
    assert not (runtime_dir / "profiles" / "bthesis-profile-thesis-smu-master.def").exists()
    assert not (runtime_dir / "bthesis-style-thesis-smu-master.tex").exists()


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
