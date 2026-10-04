from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from pypdf import PdfReader, PdfWriter


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


thesis_project_tool = _load_module(
    "project_thesis_project_tool",
    REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py",
)


@pytest.mark.parametrize("backend", ["biber", "bibtex", None])
def test_detect_class_managed_bibliography(tmp_path: Path, backend):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text("\\documentclass{xduugthesis}\n", encoding="utf-8")
    cache = tmp_path / ".latex-cache"
    cache.mkdir()
    if backend == "biber":
        (cache / "main.bcf").write_text("<bcf:controlfile/>", encoding="utf-8")
    elif backend == "bibtex":
        (cache / "main.aux").write_text("\\bibdata{references/references}\n", encoding="utf-8")
    else:
        (cache / "main.aux").write_text("\\relax\n", encoding="utf-8")
    assert thesis_project_tool.detect_bibliography_backend(main_tex, cache) == backend


@pytest.mark.parametrize("command,backend", [
    ("\\addbibresource{refs.bib}", "biber"),
    ("\\bibliography{refs}", "bibtex"),
])
def test_explicit_bibliography_detection_remains_supported(tmp_path: Path, command, backend):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(command, encoding="utf-8")
    assert thesis_project_tool.detect_bibliography_backend(main_tex) == backend


@pytest.mark.parametrize("message,fatal", [
    ('Package fontspec Error: The font "SimSun" cannot be found.', True),
    ("LaTeX Error: Missing document.", True),
    ("LaTeX Font Warning: Size substitutions", False),
])
def test_fatal_log_detection_includes_font_errors(tmp_path: Path, message, fatal):
    log = tmp_path / "main.log"
    log.write_text(message, encoding="utf-8")
    assert thesis_project_tool.log_has_fatal_errors(log) is fatal


def test_build_project_supports_passthrough_pdf(tmp_path: Path):
    source_pdf = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595.304, height=841.89)
    with source_pdf.open("wb") as fh:
        writer.write(fh)

    main_tex = tmp_path / "main.tex"
    main_tex.write_text(
        "% BENSZ_PASSTHROUGH_PDF: source.pdf\n"
        "\\documentclass{ctexart}\n"
        "\\begin{document}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    (tmp_path / "extraTex").mkdir()

    output_pdf = thesis_project_tool.build_project(tmp_path, "main.tex")

    assert output_pdf == tmp_path / "main.pdf"
    assert output_pdf.exists()
    assert output_pdf.read_bytes() == source_pdf.read_bytes()
    assert len(PdfReader(str(output_pdf)).pages) == 1
