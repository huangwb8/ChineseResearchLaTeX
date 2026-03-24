from __future__ import annotations

import importlib.util
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


thesis_tool = _load_module(
    "bensz_thesis_project_tool",
    REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py",
)


def test_detect_default_tex_file_for_main_extra_tex_layout():
    project_dir = REPO_ROOT / "projects" / "thesis-smu-master"

    assert thesis_tool.detect_default_tex_file(project_dir) == "main.tex"


def test_detect_default_tex_file_for_legacy_thesis_layout():
    project_dir = REPO_ROOT / "projects" / "thesis-ucas-resource-env"

    assert thesis_tool.detect_default_tex_file(project_dir) == "Thesis.tex"


def test_resolve_project_dir_supports_legacy_thesis_layout_from_subdir():
    project_dir = REPO_ROOT / "projects" / "thesis-ucas-resource-env"

    assert thesis_tool.resolve_project_dir(project_dir / "scripts") == project_dir


def test_resolve_tex_file_auto_detects_legacy_thesis_main_file():
    project_dir = REPO_ROOT / "projects" / "thesis-ucas-resource-env"
    tex_path = thesis_tool.resolve_tex_file(project_dir, None)

    assert tex_path == project_dir / "Thesis.tex"
