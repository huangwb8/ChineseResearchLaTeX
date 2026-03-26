from __future__ import annotations

import importlib.util
import sys
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


export_docx = _load_module(
    "project_thesis_ucas_export_docx",
    REPO_ROOT / "projects" / "thesis-ucas-doctor" / "scripts" / "export_docx.py",
)


def test_parse_main_includes_ignores_commented_inputs():
    main_tex = "\n".join(
        [
            r"\documentclass{article}",
            r"% \input{extraTex/commented.tex}",
            r"\input{extraTex/kept}",
            r"\include{extraTex/also-kept.tex} % keep this one",
            "",
        ]
    )

    assert export_docx.parse_main_includes(main_tex) == [
        "extraTex/kept.tex",
        "extraTex/also-kept.tex",
    ]


def test_discover_reference_doc_rejects_missing_explicit_path(tmp_path: Path):
    missing = tmp_path / "missing-template.docx"

    with pytest.raises(FileNotFoundError, match="--reference-doc"):
        export_docx.discover_reference_doc(tmp_path, missing)


def test_discover_reference_doc_accepts_project_relative_path(tmp_path: Path):
    official_dir = tmp_path / "docs" / "official"
    official_dir.mkdir(parents=True)
    reference_doc = official_dir / "template.docx"
    reference_doc.write_bytes(b"fake-docx")

    resolved = export_docx.discover_reference_doc(tmp_path, Path("docs/official/template.docx"))

    assert resolved == reference_doc.resolve()


def test_convert_body_tex_preserves_aligned_math_environment(tmp_path: Path):
    project_dir = tmp_path / "ucas"
    source_dir = project_dir / "extraTex"
    source_dir.mkdir(parents=True)

    latex = "\n".join(
        [
            r"\begin{equation}\label{eq:test}",
            r"    \begin{aligned}",
            r"        a &= b + c \\",
            r"        d &= e + f",
            r"    \end{aligned}",
            r"\end{equation}",
            "",
        ]
    )

    markdown = export_docx.convert_body_tex(latex, project_dir, source_dir, [Path("assets")])

    assert "$$" in markdown
    assert r"\begin{aligned}" in markdown
    assert r"\end{aligned}" in markdown
    assert r"\label{eq:test}" not in markdown


def test_render_markdown_resolves_graphicspath_images(tmp_path: Path):
    project_dir = tmp_path / "ucas"
    (project_dir / "extraTex").mkdir(parents=True)
    (project_dir / "assets").mkdir()
    (project_dir / "assets" / "pngtest.png").write_bytes(b"fake-png")

    (project_dir / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\graphicspath{{assets/}}",
                r"\begin{document}",
                r"\input{extraTex/chapter1.tex}",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "extraTex" / "chapter1.tex").write_text(
        "\n".join(
            [
                r"\chapter{图片}",
                r"\begin{figure}",
                r"  \includegraphics[width=0.5\textwidth]{pngtest}",
                r"  \caption{示例图片}",
                r"\end{figure}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    markdown = export_docx.render_markdown(project_dir, project_dir / "main.tex")

    assert "![示例图片](assets/pngtest.png)" in markdown


def test_render_markdown_resolves_graphicspath_subdirectories(tmp_path: Path):
    project_dir = tmp_path / "ucas"
    (project_dir / "extraTex").mkdir(parents=True)
    (project_dir / "assets" / "figures").mkdir(parents=True)
    (project_dir / "assets" / "figures" / "foo.png").write_bytes(b"fake-png")

    (project_dir / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\graphicspath{{assets/}}",
                r"\begin{document}",
                r"\input{extraTex/chapter1.tex}",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "extraTex" / "chapter1.tex").write_text(
        "\n".join(
            [
                r"\chapter{图片}",
                r"\begin{figure}",
                r"  \includegraphics[width=0.5\textwidth]{figures/foo}",
                r"  \caption{分组图片}",
                r"\end{figure}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    markdown = export_docx.render_markdown(project_dir, project_dir / "main.tex")

    assert "![分组图片](assets/figures/foo.png)" in markdown
