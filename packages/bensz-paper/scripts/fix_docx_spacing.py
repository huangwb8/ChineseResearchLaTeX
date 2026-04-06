#!/usr/bin/env python3
r"""
修复 DOCX 文件的行间距和段间距，使其尽量接近 LaTeX 输出。

LaTeX 参数（权威来源：texmf/.../profiles/bml-profile-bensz-manu-01.def）：
- 行距：\setstretch{1.5}  →  ONE_POINT_FIVE
- 段首缩进：\parindent = 1.5em（12pt × 1.5 = 18pt）
  - heading 后第一段：Pt(0)（titlespacing* 抑制）
  - Abstract 节所有段：Pt(0)（摘要环境无缩进）
  - 其余 body 段落（第二段起）：Pt(18)
- 段间距：\parskip = 0.2\baselineskip
    ≈ 0.2 × (12pt × 1.5) = 0.2 × 18pt = 3.6pt  →  近似取 Pt(4)

注意：DOCX 段间距（4pt）是对 LaTeX parskip（3.6pt）的近似，
两者在视觉上接近但不完全等价。详见 docs/package/BenszManuscriptLaTeX.md
"PDF 与 DOCX 对齐策略"一节。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

PROJECT_ROOT_MARKERS = ("main.tex",)


# DOCX spacing constants — keep in sync with bml-profile-bensz-manu-01.def
# LaTeX: \setstretch{1.5}
DOCX_LINE_SPACING_RULE = WD_LINE_SPACING.ONE_POINT_FIVE
# LaTeX: \parindent = 1.5em → 12pt × 1.5 = 18pt (body paragraphs, 2nd onwards)
DOCX_BODY_INDENT = Pt(18)
DOCX_NO_INDENT   = Pt(0)    # heading后第一段 & Abstract节所有段
# LaTeX: \parskip = 0.2\baselineskip ≈ 3.6pt → rounded to 4pt for Word
DOCX_SPACE_AFTER = Pt(4)
DOCX_SPACE_BEFORE = Pt(0)
# Abstract section heading text — used to suppress indentation for the whole section
ABSTRACT_HEADING = "Abstract"
# References section heading text — inserted before Bibliography paragraphs if absent
REFERENCES_HEADING = "References"
REFERENCES_HEADING_STYLE = "Heading 1"
FIGURE_LEGENDS_HEADINGS = ("Figure legends", "Figure titles and legends")
SUPPLEMENTARY_HEADINGS = ("Supplementary materials", "Supplemental information titles and legends")


def _normalize_heading_text(value: str) -> str:
    return " ".join(value.split()).strip().lower()


# Section headings whose body paragraphs should all be flush left (no first-line indent)
NO_INDENT_SECTIONS = {
    _normalize_heading_text(heading)
    for heading in (ABSTRACT_HEADING, *FIGURE_LEGENDS_HEADINGS, *SUPPLEMENTARY_HEADINGS)
}
DEFAULT_DOCX_TABLE_STYLES = {"Normal Table"}
DEFAULT_DOCX_TABLE_BORDERS = {
    "top": {"val": "single", "sz": "8", "space": "0", "color": "auto"},
    "bottom": {"val": "single", "sz": "8", "space": "0", "color": "auto"},
    "insideH": {"val": "single", "sz": "8", "space": "0", "color": "auto"},
    "left": {"val": "nil"},
    "right": {"val": "nil"},
    "insideV": {"val": "nil"},
}


def configure_windows_stdio_utf8() -> None:
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def is_project_root(path: Path) -> bool:
    """Return True when the directory looks like a manuscript project root."""
    return any((path / marker).exists() for marker in PROJECT_ROOT_MARKERS)


def find_project_root(start: Path | None = None) -> Path:
    """Walk upward until a manuscript project root is found."""
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "Cannot find project root. Run inside the manuscript project tree or "
        "pass --project-dir explicitly."
    )


def resolve_project_dir(project_dir: Path | None) -> Path:
    """Resolve the manuscript project directory from CLI input or the current working tree."""
    if project_dir is None:
        return find_project_root()

    candidate = project_dir.expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Project directory not found: {candidate}")
    if candidate.is_file():
        candidate = candidate.parent
    if is_project_root(candidate):
        return candidate
    return find_project_root(candidate)


def _add_references_heading_if_missing(
    doc: "Document", heading_text: str = REFERENCES_HEADING
) -> None:
    """确保 References 在 DOCX 中始终是 Heading 1，并位于第一个 Bibliography 段落前。"""
    first_bib = next(
        (p for p in doc.paragraphs if p.style.name == "Bibliography"), None
    )
    if first_bib is None:
        return

    heading = _find_heading_paragraph(doc, (heading_text,))
    if heading is None:
        heading = doc.add_heading(heading_text, level=1)
        heading_elem = heading._element
        heading_elem.getparent().remove(heading_elem)
        first_bib._element.addprevious(heading_elem)
        print(f"✓ 已插入 '{heading_text}' 标题")
    else:
        body_elem = first_bib._element.getparent()
        children = list(body_elem)
        if children.index(heading._element) > children.index(first_bib._element):
            body_elem.remove(heading._element)
            first_bib._element.addprevious(heading._element)
            print(f"✓ 已将现有 '{heading_text}' 标题移动到参考文献前")

    if heading.style.name != REFERENCES_HEADING_STYLE:
        heading.style = doc.styles[REFERENCES_HEADING_STYLE]
        print(f"✓ 已将 '{heading_text}' 标题样式统一为 {REFERENCES_HEADING_STYLE}")


def _find_heading_paragraph(doc: "Document", headings: tuple[str, ...] | list[str] | set[str]):
    normalized_headings = {_normalize_heading_text(heading) for heading in headings}
    return next(
        (
            para
            for para in doc.paragraphs
            if para.style.name.startswith("Heading")
            and _normalize_heading_text(para.text) in normalized_headings
        ),
        None,
    )


def _reorder_references_before_figure_legends(
    doc: "Document",
    references_heading: str = REFERENCES_HEADING,
    figure_legends_headings: tuple[str, ...] = FIGURE_LEGENDS_HEADINGS,
) -> None:
    """将 References 节（标题 + 所有 Bibliography 段落）移动到 Figure legends 前。

    Pandoc citeproc 默认将参考文献追加至文档末尾，但 SCI 手稿惯例是
    References 位于正文之后、Figure legends 之前。
    """
    paras = doc.paragraphs

    # Locate the References heading
    ref_heading_para = _find_heading_paragraph(doc, (references_heading,))
    if ref_heading_para is None:
        return  # Nothing to move

    # Locate the Figure legends heading
    fig_legends_para = _find_heading_paragraph(doc, figure_legends_headings)
    if fig_legends_para is None:
        return  # No Figure legends section found

    # Collect ALL Bibliography paragraph elements via python-docx style
    # resolution (raw XML pStyle may use an opaque ID like "af4" instead of
    # the human-readable name "Bibliography").
    bib_elements = [p._element for p in paras if p.style.name == "Bibliography"]
    if not bib_elements:
        return

    body_elem = ref_heading_para._element.getparent()
    children = list(body_elem)
    fig_idx = children.index(fig_legends_para._element)

    # Only skip if heading AND every Bibliography entry are already before Figure legends
    ref_idx = children.index(ref_heading_para._element)
    all_before = ref_idx < fig_idx and all(
        children.index(e) < fig_idx for e in bib_elements
    )
    if all_before:
        return

    # Build the block: References heading + all Bibliography paragraphs
    ref_block = [ref_heading_para._element] + bib_elements

    for elem in ref_block:
        body_elem.remove(elem)

    anchor = fig_legends_para._element
    for elem in ref_block:
        anchor.addprevious(elem)

    print(f"✓ 已将 References 节移动到 '{fig_legends_para.text.strip()}' 前")


def _find_table_borders_element(table) -> OxmlElement | None:
    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        return None

    for child in tbl_pr.iterchildren():
        if child.tag == qn("w:tblBorders"):
            return child
    return None


def _ensure_default_horizontal_table_borders(table) -> None:
    style_name = table.style.name if table.style else ""
    if style_name not in DEFAULT_DOCX_TABLE_STYLES:
        return
    if _find_table_borders_element(table) is not None:
        return

    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        return

    borders = OxmlElement("w:tblBorders")
    for edge, attrs in DEFAULT_DOCX_TABLE_BORDERS.items():
        element = OxmlElement(f"w:{edge}")
        for attr_name, value in attrs.items():
            element.set(qn(f"w:{attr_name}"), value)
        borders.append(element)
    tbl_pr.append(borders)


def fix_docx_spacing(docx_path: Path) -> None:
    """修复 DOCX 文件的行间距和段间距。"""
    print(f"正在修复: {docx_path}")

    doc = Document(docx_path)

    # Insert "References" heading before bibliography if absent
    _add_references_heading_if_missing(doc)

    # Move References section before Figure legends (matches PDF layout)
    _reorder_references_before_figure_legends(doc)

    total_paragraphs = 0
    fixed_paragraphs = 0

    in_no_indent_section = False  # True for Abstract, Figure legends, Supplementary materials
    prev_was_heading     = True   # 文档起始视为 heading 后，首段不缩进
    seen_section_heading = False  # 见到第一个 H2+ 之前（frontmatter）不缩进
    seen_title_heading   = False  # 首个 Heading 1 是论文标题，保持居中

    for para in doc.paragraphs:
        total_paragraphs += 1
        style_name = para.style.name if para.style else ""
        is_heading = style_name.startswith("Heading")
        is_bibliography = style_name == "Bibliography"

        pf = para.paragraph_format
        pf.line_spacing_rule = DOCX_LINE_SPACING_RULE
        pf.space_after  = DOCX_SPACE_AFTER
        pf.space_before = DOCX_SPACE_BEFORE

        if is_heading:
            if style_name == "Heading 1" and not seen_title_heading:
                pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
                seen_title_heading = True
            else:
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if style_name != "Heading 1":
                seen_section_heading = True
            in_no_indent_section = _normalize_heading_text(para.text) in NO_INDENT_SECTIONS
            prev_was_heading = True
            pf.first_line_indent = DOCX_NO_INDENT
        elif is_bibliography:
            # Reference list: flush left, no indent.  Replace tab characters
            # with a single space so the gap between the citation number and
            # text is uniform (style-level tab-stops create oversized gaps
            # once hanging indent is removed).
            pf.first_line_indent = DOCX_NO_INDENT
            pf.left_indent       = DOCX_NO_INDENT
            for run in para.runs:
                if "\t" in run.text:
                    run.text = run.text.replace("\t", "")
            prev_was_heading = False
        else:
            if not seen_section_heading or in_no_indent_section or prev_was_heading:
                pf.first_line_indent = DOCX_NO_INDENT
            else:
                pf.first_line_indent = DOCX_BODY_INDENT
            prev_was_heading = False

        fixed_paragraphs += 1

    for table in doc.tables:
        _ensure_default_horizontal_table_borders(table)

    doc.save(docx_path)

    print(f"✓ 已处理 {fixed_paragraphs}/{total_paragraphs} 个段落")
    print(f"✓ 文件已保存: {docx_path}")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Fix paragraph spacing in manuscript DOCX output.")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory. Defaults to the nearest parent containing main.tex.",
    )
    parser.add_argument(
        "--docx",
        type=Path,
        default=None,
        help="Explicit DOCX file path. Overrides --project-dir/main.docx when provided.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip writing a .backup copy before modifying the DOCX file.",
    )
    return parser.parse_args()


def main() -> None:
    """主函数。"""
    configure_windows_stdio_utf8()
    args = parse_args()
    if args.docx is not None:
        docx_path = args.docx.expanduser().resolve()
        project_dir = docx_path.parent
    else:
        project_dir = resolve_project_dir(args.project_dir)
        docx_path = project_dir / "main.docx"

    if not docx_path.exists():
        print(f"错误: 找不到文件 {docx_path}")
        print("请先运行: bml build")
        return

    if not args.no_backup:
        backup_path = docx_path.with_suffix(".docx.backup")
        shutil.copy2(docx_path, backup_path)
        print(f"✓ 已备份原文件: {backup_path}\n")

    # 修复文档
    fix_docx_spacing(docx_path)

    if not args.no_backup:
        print("\n提示: 如需恢复原文件，请运行:")
        print(f"  cp \"{backup_path}\" \"{docx_path}\"")


if __name__ == '__main__':
    main()
