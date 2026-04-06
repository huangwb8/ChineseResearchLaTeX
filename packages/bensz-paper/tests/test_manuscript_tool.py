from pathlib import Path
import sys
from zipfile import ZipFile

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SCRIPTS_DIR = REPO_ROOT / "packages" / "bensz-paper" / "scripts"
if str(PACKAGE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SCRIPTS_DIR))

import manuscript_tool


def _read_document_xml(docx_path: Path) -> str:
    with ZipFile(docx_path) as archive:
        return archive.read("word/document.xml").decode("utf-8", errors="replace")


def _build_docx_via_production_pipeline(markdown: str, docx_path: Path, tmp_path: Path) -> None:
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text("", encoding="utf-8")
    csl_path = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "manuscript.csl"
    reference_doc = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "reference.docx"

    manuscript_tool.build_docx_from_markdown(
        manuscript_md=markdown,
        docx_path=docx_path,
        csl_path=csl_path,
        bibliography_path=bib_path,
        reference_doc=reference_doc,
    )
    manuscript_tool.fix_docx_spacing(docx_path)


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

    assert "Author One^1†^, Author Two^2\\*^" in normalized
    assert "^1^Department A" in normalized
    assert "^2^Department B" in normalized


def test_convert_sup_tags_to_superscript_preserves_escaped_asterisk():
    markdown = manuscript_tool._convert_sup_tags_to_superscript(
        r"<sup>\*</sup>Correspondence: template.author@example.org."
    )

    assert markdown == r"^\*^Correspondence: template.author@example.org."


def test_pandoc_latex_to_markdown_converts_simple_tables():
    latex = "\n".join(
        [
            r"\section{Methods}",
            r"\begin{table}[htbp]",
            r"\centering",
            r"\caption{Demo table}",
            r"\begin{tabular}{ll}",
            r"\hline",
            r"Item & Value \\",
            r"\hline",
            r"A & 1 \\",
            r"B & 2 \\",
            r"\hline",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )

    markdown = manuscript_tool.pandoc_latex_to_markdown(latex)

    assert "# Methods" in markdown
    assert "Item   Value" in markdown
    assert "A      1" in markdown
    assert "Demo table" in markdown


def test_pandoc_latex_to_markdown_keeps_standard_math_syntax():
    latex = r"Inline $\rho$ and $\Delta$. Display: $$\log_{10}(x+1)$$."

    markdown = manuscript_tool.pandoc_latex_to_markdown(latex)

    assert "$`\\rho`$" not in markdown
    assert "$`\\Delta`$" not in markdown
    assert "``` math" not in markdown
    assert r"$\rho$" in markdown
    assert r"$\Delta$" in markdown
    assert r"$$\log_{10}(x+1)$$" in markdown


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


def test_normalize_frontmatter_markdown_marks_centered_author_block():
    markdown = "\n".join(
        [
            "::: center",
            "**Template Example**",
            "",
            "Author One^1^, Author Two^2^",
            ":::",
            "",
            "^1^Department A",
            "",
        ]
    )

    normalized = manuscript_tool._normalize_frontmatter_markdown(markdown)

    assert normalized.splitlines()[0] == "# Template Example"
    assert manuscript_tool.DOCX_FRONTMATTER_CENTER_START in normalized
    assert "Author One^1^, Author Two^2^" in normalized
    assert manuscript_tool.DOCX_FRONTMATTER_CENTER_END in normalized
    assert "^1^Department A" in normalized


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
    _build_docx_via_production_pipeline(markdown, docx_path, tmp_path)

    doc = Document(docx_path)
    author_para = next(para for para in doc.paragraphs if "Author One" in para.text)
    affiliation_para = next(para for para in doc.paragraphs if "Department A" in para.text)
    second_affiliation_para = next(para for para in doc.paragraphs if "Department B" in para.text)

    assert author_para.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert affiliation_para.paragraph_format.alignment != WD_ALIGN_PARAGRAPH.CENTER
    assert second_affiliation_para.paragraph_format.alignment != WD_ALIGN_PARAGRAPH.CENTER
    assert manuscript_tool.DOCX_FRONTMATTER_CENTER_START not in "\n".join(
        para.text for para in doc.paragraphs
    )
    assert manuscript_tool.DOCX_FRONTMATTER_CENTER_END not in "\n".join(
        para.text for para in doc.paragraphs
    )
    assert any(run.text == "1†" and run.font.superscript for run in author_para.runs)
    assert any(run.text == "2*" and run.font.superscript for run in author_para.runs)
    assert any(run.text == "1" and run.font.superscript for run in affiliation_para.runs)
    assert any(run.text == "2" and run.font.superscript for run in second_affiliation_para.runs)


def test_build_markdown_for_docx_correspondence_asterisk_survives_docx_roundtrip(tmp_path):
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
                r"\end{center}",
                "",
                r"\noindent\textsuperscript{*}Correspondence: template.author@example.org.\par",
                "",
            ]
        ),
        encoding="utf-8",
    )

    markdown = manuscript_tool.build_markdown_for_docx(project_dir)
    docx_path = tmp_path / "correspondence.docx"
    _build_docx_via_production_pipeline(markdown, docx_path, tmp_path)

    correspondence_para = next(
        para for para in Document(docx_path).paragraphs if "Correspondence:" in para.text
    )

    assert "^*^" not in correspondence_para.text
    assert any(run.text == "*" and run.font.superscript for run in correspondence_para.runs)


def test_build_docx_from_markdown_promotes_math_to_omml(tmp_path):
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text(
        "\n".join(
            [
                "@article{Demo2026,",
                "  author = {Alpha, Alice and Beta, Bob},",
                "  title = {Synthetic Math Regression},",
                "  journal = {Journal of Regression Tests},",
                "  year = {2026},",
                "  doi = {10.1234/demo.2026.002},",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    docx_path = tmp_path / "math.docx"
    csl_path = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "manuscript.csl"
    reference_doc = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "reference.docx"
    markdown = "\n".join(
        [
            "Body text with a citation [@Demo2026]. Inline $\\rho$ and $\\Delta$.",
            "",
            "Display:",
            "$$\\log_{10}(x+1)$$",
            "",
        ]
    )

    manuscript_tool.build_docx_from_markdown(
        manuscript_md=markdown,
        docx_path=docx_path,
        csl_path=csl_path,
        bibliography_path=bib_path,
        reference_doc=reference_doc,
    )

    document_xml = _read_document_xml(docx_path)
    assert document_xml.count("<m:oMath") >= 3
    assert "\\rho" not in document_xml
    assert "\\Delta" not in document_xml
    assert "\\log_{10}(x+1)" not in document_xml
    assert "`" not in document_xml


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


def test_fix_docx_spacing_reorders_references_before_figure_titles_and_legends(tmp_path):
    docx_path = tmp_path / "references-order.docx"
    doc = Document()
    doc.styles.add_style("Bibliography", WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("Introduction", style="Heading 1")
    doc.add_paragraph("Body paragraph.", style="Normal")
    doc.add_paragraph("Figure titles and legends", style="Heading 1")
    doc.add_paragraph("Figure legend paragraph.", style="Normal")
    doc.add_paragraph("[1]\tReference one.", style="Bibliography")
    doc.add_paragraph("[2]\tReference two.", style="Bibliography")
    doc.save(docx_path)

    manuscript_tool.fix_docx_spacing(docx_path)

    fixed_doc = Document(docx_path)
    paragraphs = [para for para in fixed_doc.paragraphs if para.text.strip()]
    paragraph_texts = [para.text.strip() for para in paragraphs]
    first_bibliography_index = next(
        index for index, para in enumerate(paragraphs) if para.style.name == "Bibliography"
    )
    last_bibliography_index = max(
        index for index, para in enumerate(paragraphs) if para.style.name == "Bibliography"
    )
    references_heading = next(para for para in paragraphs if para.text.strip() == "References")

    assert paragraph_texts.index("References") < paragraph_texts.index("Figure titles and legends")
    assert paragraph_texts.index("References") < first_bibliography_index
    assert last_bibliography_index < paragraph_texts.index("Figure titles and legends")
    assert references_heading.style.name == "Heading 1"


def test_fix_docx_spacing_promotes_existing_references_heading_to_heading_1(tmp_path):
    docx_path = tmp_path / "references-heading-level.docx"
    doc = Document()
    doc.styles.add_style("Bibliography", WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("Introduction", style="Heading 1")
    doc.add_paragraph("Body paragraph.", style="Normal")
    doc.add_paragraph("References", style="Heading 2")
    doc.add_paragraph("1. Reference one.", style="Bibliography")
    doc.save(docx_path)

    manuscript_tool.fix_docx_spacing(docx_path)

    fixed_doc = Document(docx_path)
    references_heading = next(para for para in fixed_doc.paragraphs if para.text.strip() == "References")

    assert references_heading.style.name == "Heading 1"


def test_fix_docx_spacing_keeps_alias_tail_sections_flush_left(tmp_path):
    docx_path = tmp_path / "tail-alias-indent.docx"
    doc = Document()
    doc.add_paragraph("Title", style="Heading 1")
    doc.add_paragraph("Front matter", style="Normal")
    doc.add_paragraph("Figure titles and legends", style="Heading 1")
    doc.add_paragraph("Figure legend paragraph.", style="Normal")
    doc.add_paragraph("Supplemental information titles and legends", style="Heading 1")
    doc.add_paragraph("Supplement paragraph.", style="Normal")
    doc.save(docx_path)

    manuscript_tool.fix_docx_spacing(docx_path)

    fixed_doc = Document(docx_path)
    figure_para = next(para for para in fixed_doc.paragraphs if para.text == "Figure legend paragraph.")
    supplement_para = next(para for para in fixed_doc.paragraphs if para.text == "Supplement paragraph.")

    assert figure_para.paragraph_format.first_line_indent.pt == 0
    assert supplement_para.paragraph_format.first_line_indent.pt == 0


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


def test_paper_sci_01_csl_prints_single_doi_without_duplicate_url(tmp_path):
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text(
        "\n".join(
            [
                "@article{Demo2026,",
                "  author = {Alpha, Alice and Beta, Bob and Gamma, Carol},",
                "  title = {Synthetic DOI Regression},",
                "  journal = {Journal of Regression Tests},",
                "  year = {2026},",
                "  doi = {10.1234/demo.2026.001},",
                "  url = {https://doi.org/10.1234/demo.2026.001},",
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

    bibliography_para = next(
        para
        for para in Document(docx_path).paragraphs
        if "synthetic doi regression" in para.text.lower()
    )

    assert "doi:10.1234/demo.2026.001" in bibliography_para.text.replace(" ", "").lower()
    assert "https://doi.org/10.1234/demo.2026.001" not in bibliography_para.text.lower()


def test_paper_sci_01_csl_keeps_reference_number_and_text_in_single_paragraph(tmp_path):
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text(
        "\n".join(
            [
                "@article{Demo2026,",
                (
                    "  author = {Alpha, Alice and Beta, Bob and Gamma, Carol and "
                    "Delta, David},"
                ),
                "  title = {Synthetic Reference Layout Regression},",
                "  journal = {Journal of Regression Tests},",
                "  year = {2026},",
                "  volume = {12},",
                "  pages = {34--56},",
                "  doi = {10.1234/demo.2026.123},",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    docx_path = tmp_path / "bibliography-layout.docx"
    csl_path = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "manuscript.csl"
    reference_doc = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "reference.docx"

    manuscript_tool.build_docx_from_markdown(
        manuscript_md="Body text with a citation [@Demo2026].\n",
        docx_path=docx_path,
        csl_path=csl_path,
        bibliography_path=bib_path,
        reference_doc=reference_doc,
    )

    bibliography_paragraphs = [
        para for para in Document(docx_path).paragraphs if para.style.name == "Bibliography" and para.text.strip()
    ]

    assert len(bibliography_paragraphs) == 1
    assert bibliography_paragraphs[0].text.startswith("1. ")
    assert "Synthetic reference layout regression" in bibliography_paragraphs[0].text


def test_fix_docx_spacing_adds_visible_horizontal_borders_to_normal_tables(tmp_path):
    docx_path = tmp_path / "table.docx"
    csl_path = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "manuscript.csl"
    reference_doc = REPO_ROOT / "projects" / "paper-sci-01" / "artifacts" / "reference.docx"

    manuscript_tool.run_cmd(
        [
            manuscript_tool.resolve_executable("pandoc"),
            "-",
            "-f",
            "markdown",
            "--reference-doc",
            str(reference_doc),
            "--csl",
            str(csl_path),
            "-o",
            str(docx_path),
        ],
        input_text="| A | B |\n| --- | --- |\n| 1 | 2 |\n",
    )

    manuscript_tool.fix_docx_spacing(docx_path)

    xml = _read_document_xml(docx_path)
    assert "<w:tblBorders>" in xml
    assert '<w:top w:val="single"' in xml
    assert '<w:bottom w:val="single"' in xml
    assert '<w:insideH w:val="single"' in xml
    assert '<w:left w:val="nil"' in xml
    assert '<w:right w:val="nil"' in xml
    assert '<w:insideV w:val="nil"' in xml


def test_fix_docx_spacing_preserves_existing_table_border_overrides(tmp_path):
    docx_path = tmp_path / "custom-table.docx"
    doc = Document()
    table = doc.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    table.cell(1, 0).text = "1"
    table.cell(1, 1).text = "2"

    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge, value in (
        ("top", "double"),
        ("bottom", "double"),
        ("left", "single"),
        ("right", "single"),
        ("insideH", "double"),
        ("insideV", "single"),
    ):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), value)
        borders.append(element)
    tbl_pr.append(borders)
    doc.save(docx_path)

    manuscript_tool.fix_docx_spacing(docx_path)

    xml = _read_document_xml(docx_path)
    assert '<w:top w:val="double"' in xml
    assert '<w:bottom w:val="double"' in xml
    assert '<w:insideH w:val="double"' in xml
    assert '<w:insideV w:val="single"' in xml
    assert '<w:left w:val="single"' in xml
    assert '<w:right w:val="single"' in xml


def test_bml_bibliography_prefers_doi_without_printing_urls():
    bibliography_style = (REPO_ROOT / "packages" / "bensz-paper" / "bml-bibliography.sty").read_text(
        encoding="utf-8"
    )

    assert "url=false" in bibliography_style
    assert "doi=true" in bibliography_style
    assert r"\clearfield{url}\clearfield{urlyear}\clearfield{urlmonth}\clearfield{urlday}" in bibliography_style


def test_paper_sci_01_main_tex_keeps_project_level_doi_only_guard():
    main_tex = (REPO_ROOT / "projects" / "paper-sci-01" / "main.tex").read_text(encoding="utf-8")

    assert r"\ExecuteBibliographyOptions{url=false, doi=true}" in main_tex
    assert r"\AtEveryBibitem{\clearfield{url}\clearfield{urlyear}\clearfield{urlmonth}\clearfield{urlday}}" in main_tex
    assert r"\section{References}" in main_tex
    assert r"\printbibliography[heading=none]" in main_tex


def test_paper_sci_01_bib_data_drops_doi_mirror_urls():
    refs_bib = (REPO_ROOT / "projects" / "paper-sci-01" / "references" / "refs.bib").read_text(
        encoding="utf-8"
    )

    assert "https://doi.org/" not in refs_bib
