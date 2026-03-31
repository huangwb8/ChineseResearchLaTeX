from pathlib import Path
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SCRIPTS_DIR = REPO_ROOT / "packages" / "bensz-paper" / "scripts"
if str(PACKAGE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SCRIPTS_DIR))

import manuscript_tool


def test_package_version_matches_cli_version():
    scripts_init = PACKAGE_SCRIPTS_DIR / "__init__.py"
    namespace: dict[str, str] = {}
    exec(scripts_init.read_text(encoding="utf-8"), namespace)

    assert namespace["__version__"] == manuscript_tool.VERSION


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


def test_pandoc_latex_to_markdown_preserves_frontmatter_superscripts():
    latex = "\n".join(
        [
            r"Author One\textsuperscript{1†}, Author Two\textsuperscript{2*}",
            r"\noindent\textsuperscript{1}Department A",
            r"\noindent\textsuperscript{2}Department B",
            "",
        ]
    )

    markdown = manuscript_tool.pandoc_latex_to_markdown(latex)
    normalized = " ".join(markdown.split())

    assert "Author One^1†^, Author Two^2*^" in normalized
    assert "^1^Department A" in normalized
    assert "^2^Department B" in normalized


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


def test_build_markdown_for_docx_frontmatter_superscripts_survive_docx_roundtrip(tmp_path):
    project_dir = tmp_path / "paper-demo"
    (project_dir / "extraTex" / "front").mkdir(parents=True)

    (project_dir / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\begin{document}",
                r"\input{extraTex/front/frontmatter.tex}",
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
                r"Author One\textsuperscript{1†}, Author Two\textsuperscript{2*}",
                r"\end{center}",
                "",
                r"\noindent\textsuperscript{1}Department A\par",
                r"\noindent\textsuperscript{2}Department B\par",
                "",
            ]
        ),
        encoding="utf-8",
    )

    markdown = manuscript_tool.build_markdown_for_docx(project_dir)
    docx_path = tmp_path / "frontmatter.docx"
    manuscript_tool.run_cmd(
        [
            manuscript_tool.resolve_executable("pandoc"),
            "-",
            "-f",
            "markdown+raw_html+superscript",
            "-o",
            str(docx_path),
        ],
        input_text=markdown,
    )
    manuscript_tool.fix_docx_spacing(docx_path)

    doc = Document(docx_path)
    author_para = next(para for para in doc.paragraphs if "Author One" in para.text)
    affiliation_para = next(para for para in doc.paragraphs if "Department A" in para.text)
    second_affiliation_para = next(para for para in doc.paragraphs if "Department B" in para.text)

    assert any(run.text == "1†" and run.font.superscript for run in author_para.runs)
    assert any(run.text == "2*" and run.font.superscript for run in author_para.runs)
    assert any(run.text == "1" and run.font.superscript for run in affiliation_para.runs)
    assert any(run.text == "2" and run.font.superscript for run in second_affiliation_para.runs)


def test_remove_legacy_docx_intermediates_cleans_old_cache(tmp_path):
    cache_dir = tmp_path / ".latex-cache"
    (cache_dir / "extraTex" / "body").mkdir(parents=True)
    (cache_dir / "main.md").write_text("legacy markdown", encoding="utf-8")
    (cache_dir / "extraTex" / "body" / "intro.tex").write_text("legacy tex", encoding="utf-8")

    manuscript_tool.remove_legacy_docx_intermediates(cache_dir)

    assert not (cache_dir / "main.md").exists()
    assert not (cache_dir / "extraTex").exists()


def test_fix_docx_spacing_keeps_title_centered_and_left_aligns_section_headings(tmp_path):
    docx_path = tmp_path / "heading-alignment.docx"
    doc = Document()
    doc.styles["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("Template Example Title", style="Heading 1")
    doc.add_paragraph("Template author list", style="Normal")
    doc.add_paragraph("Introduction", style="Heading 1")
    doc.add_paragraph("Body paragraph.", style="Normal")
    doc.save(docx_path)

    manuscript_tool.fix_docx_spacing(docx_path)

    fixed_doc = Document(docx_path)
    title_para = fixed_doc.paragraphs[0]
    section_para = fixed_doc.paragraphs[2]

    assert title_para.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert section_para.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.LEFT


def test_paper_sci_01_csl_keeps_three_authors_before_et_al(tmp_path):
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text(
        "\n".join(
            [
                "@article{Demo2026,",
                (
                    "  author = {Alpha, Alice and Beta, Bob and Gamma, Carol and "
                    "Delta, David and Epsilon, Erin and Zeta, Frank},"
                ),
                "  title = {Synthetic Reference for CSL Regression},",
                "  journal = {Journal of Regression Tests},",
                "  year = {2026},",
                "  volume = {12},",
                "  pages = {34--56},",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    docx_path = tmp_path / "bibliography.docx"
    csl_path = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "manuscript.csl"
    reference_doc = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "reference.docx"

    manuscript_tool.run_cmd(
        [
            manuscript_tool.resolve_executable("pandoc"),
            "-",
            "-f",
            "markdown",
            "--citeproc",
            "--csl",
            str(csl_path),
            "--bibliography",
            str(bib_path),
            "--reference-doc",
            str(reference_doc),
            "-o",
            str(docx_path),
        ],
        input_text="Body text with a citation [@Demo2026].\n",
    )

    doc = Document(docx_path)
    bibliography_para = next(para for para in doc.paragraphs if "Synthetic reference for CSL regression" in para.text)

    assert "Alpha, A. et al." not in bibliography_para.text
    assert "Alpha, A., Beta, B., Gamma, C." in bibliography_para.text
    assert "et al." in bibliography_para.text
    assert "Delta, D." not in bibliography_para.text
