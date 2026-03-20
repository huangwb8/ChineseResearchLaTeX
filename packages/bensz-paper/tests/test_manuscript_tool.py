from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SCRIPTS_DIR = REPO_ROOT / "packages" / "bensz-paper" / "scripts"
if str(PACKAGE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SCRIPTS_DIR))

import manuscript_tool


def test_collect_extra_tex_inputs_follows_main_tex_order(tmp_path):
    project_dir = tmp_path / "paper-demo"
    (project_dir / "extraTex" / "front").mkdir(parents=True)
    (project_dir / "extraTex" / "body").mkdir(parents=True)
    (project_dir / "extraTex" / "back").mkdir(parents=True)

    (project_dir / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\begin{document}",
                r"\input{extraTex/front/frontmatter.tex}",
                r"\input{extraTex/body/introduction}",
                r"\input{ignored/not-part-of-docx.tex}",
                r"\input{extraTex/back/figure-legends.tex}",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "extraTex" / "front" / "frontmatter.tex").write_text("front", encoding="utf-8")
    (project_dir / "extraTex" / "body" / "introduction.tex").write_text("body", encoding="utf-8")
    (project_dir / "extraTex" / "back" / "figure-legends.tex").write_text("back", encoding="utf-8")

    inputs = manuscript_tool.collect_extra_tex_inputs(project_dir)

    assert inputs == [
        Path("extraTex/front/frontmatter.tex"),
        Path("extraTex/body/introduction.tex"),
        Path("extraTex/back/figure-legends.tex"),
    ]


def test_collect_extra_tex_inputs_ignores_commented_inputs(tmp_path):
    project_dir = tmp_path / "paper-demo"
    (project_dir / "extraTex" / "body").mkdir(parents=True)

    (project_dir / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\begin{document}",
                r"% \input{extraTex/body/commented-out.tex}",
                r"\input{extraTex/body/kept.tex} % keep this one",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "extraTex" / "body" / "kept.tex").write_text("kept", encoding="utf-8")

    inputs = manuscript_tool.collect_extra_tex_inputs(project_dir)

    assert inputs == [Path("extraTex/body/kept.tex")]


def test_pandoc_latex_to_markdown_preserves_headings_and_citations():
    latex = "\n".join(
        [
            r"\section{Results}",
            r"Text with \supercite{KeyA,KeyB} and \texttt{inline code}.",
            r"\subsection*{Inner}",
            r"More text.",
            "",
        ]
    )

    markdown = manuscript_tool.pandoc_latex_to_markdown(latex)

    assert "# Results" in markdown
    assert "[@KeyA; @KeyB]" in markdown
    assert "## Inner" in markdown
    assert "`inline code`" in markdown


def test_build_markdown_for_docx_reads_extra_tex_without_source_manifest(tmp_path):
    project_dir = tmp_path / "paper-demo"
    (project_dir / "extraTex" / "front").mkdir(parents=True)
    (project_dir / "extraTex" / "body").mkdir(parents=True)
    (project_dir / "extraTex" / "back").mkdir(parents=True)

    (project_dir / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\begin{document}",
                r"\input{extraTex/front/frontmatter.tex}",
                r"\input{extraTex/body/introduction.tex}",
                r"\input{extraTex/back/figure-legends.tex}",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "extraTex" / "front" / "frontmatter.tex").write_text(
        "\n".join(
            [
                r"\begin{center}",
                r"\textbf{Template Example}",
                "",
                r"Author One\textsuperscript{1}",
                r"\end{center}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "extraTex" / "body" / "introduction.tex").write_text(
        "\n".join(
            [
                r"\section{Introduction}",
                r"Body text with \supercite{Demo2026}.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "extraTex" / "back" / "figure-legends.tex").write_text(
        "\n".join(
            [
                r"\section*{Figure legends}",
                r"Legend text.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    markdown = manuscript_tool.build_markdown_for_docx(project_dir)

    assert "Template Example" in markdown
    assert "Author One" in markdown
    assert "# Introduction" in markdown
    assert "[@Demo2026]" in markdown
    assert "# Figure legends" in markdown


def test_remove_legacy_docx_intermediates_cleans_old_cache(tmp_path):
    cache_dir = tmp_path / ".latex-cache"
    (cache_dir / "extraTex" / "body").mkdir(parents=True)
    (cache_dir / "main.md").write_text("legacy markdown", encoding="utf-8")
    (cache_dir / "extraTex" / "body" / "intro.tex").write_text("legacy tex", encoding="utf-8")

    manuscript_tool.remove_legacy_docx_intermediates(cache_dir)

    assert not (cache_dir / "main.md").exists()
    assert not (cache_dir / "extraTex").exists()
