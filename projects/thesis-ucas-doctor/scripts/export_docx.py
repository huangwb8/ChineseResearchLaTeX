#!/usr/bin/env python3
"""将 thesis-ucas-doctor 的 LaTeX 源尽量转换为可编辑的 Word（docx）。

设计目标：
1. 优先用源码而不是 PDF 提取，以提升结构和公式可保真度。
2. 对复杂 LaTeX 环境做可控降级，避免 pandoc 直接解析失败。
3. 通过 --reference-doc 套用学校 Word 模板样式。
4. 转换后自动做样式归一化与质量报告（标题层级/段落样式/版面参数）。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from docx import Document as DocxDocument  # type: ignore
except Exception:
    DocxDocument = None


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = {"w": W_NS}
DEFAULT_REFERENCE_DOC_NAMES = [
    "中国科学院大学资环学科群研究生学位论文word模板.docx",
    "附件2 中国科学院大学学位论文word模板2024.10.23——建议使用office 2021及以上版本.docx",
]
DEFAULT_REFERENCE_DOC_DIRS = [
    ("docs", "official"),
    (),
    ("docs",),
]


def _w_attr(key: str) -> str:
    return f"{{{W_NS}}}{key}"


def discover_reference_doc(project_dir: Path, explicit: Optional[Path]) -> Path:
    if explicit is not None:
        raw_candidate = explicit.expanduser()
        candidates = [raw_candidate]
        if not raw_candidate.is_absolute():
            candidates.append(project_dir / raw_candidate)

        checked: List[Path] = []
        for candidate in candidates:
            resolved = candidate.resolve()
            checked.append(resolved)
            if resolved.exists():
                return resolved

        checked_display = ", ".join(str(path) for path in checked)
        raise FileNotFoundError(f"--reference-doc 指向的文件不存在。已检查: {checked_display}")

    candidates: List[Path] = []
    for name in DEFAULT_REFERENCE_DOC_NAMES:
        for rel_dir in DEFAULT_REFERENCE_DOC_DIRS:
            candidates.append(project_dir.joinpath(*rel_dir, name))

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    available = sorted(p.name for p in project_dir.glob("*.docx"))
    available_official = sorted(p.name for p in (project_dir / "docs" / "official").glob("*.docx"))
    available_docs = sorted(p.name for p in (project_dir / "docs").glob("*.docx"))
    hint = f" 当前项目根目录可见 docx: {available}" if available else ""
    hint_official = f" docs/official 可见 docx: {available_official}" if available_official else ""
    hint_docs = f" docs/ 可见 docx: {available_docs}" if available_docs else ""
    raise FileNotFoundError(
        "未找到参考 Word 模板。请将资环 Word 模板放在项目 docs/official/，"
        "或显式传入 --reference-doc。"
        + hint
        + hint_official
        + hint_docs
    )


def parse_braced(text: str, start: int) -> Tuple[str, int]:
    if start >= len(text) or text[start] != "{":
        raise ValueError("parse_braced expects '{' at start")

    depth = 0
    i = start
    out: List[str] = []

    while i < len(text):
        ch = text[i]
        if ch == "\\":
            if i + 1 < len(text):
                out.append(text[i : i + 2])
                i += 2
                continue
            out.append(ch)
            i += 1
            continue

        if ch == "{":
            depth += 1
            if depth > 1:
                out.append(ch)
            i += 1
            continue

        if ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(out), i + 1
            out.append(ch)
            i += 1
            continue

        out.append(ch)
        i += 1

    raise ValueError("unbalanced braces")


def parse_macro_args(text: str, macro: str, n_args: int) -> Optional[List[str]]:
    pat = re.compile(r"\\" + re.escape(macro) + r"\s*")
    m = pat.search(text)
    if not m:
        return None

    i = m.end()
    args: List[str] = []
    for _ in range(n_args):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            return None
        value, i = parse_braced(text, i)
        args.append(value)
    return args


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(line)
    return "\n".join(lines)


def flatten_texorpdfstring(text: str) -> str:
    pattern = re.compile(r"\\texorpdfstring\s*\{")

    while True:
        m = pattern.search(text)
        if not m:
            break
        try:
            _, p1 = parse_braced(text, m.end() - 1)
            while p1 < len(text) and text[p1].isspace():
                p1 += 1
            if p1 >= len(text) or text[p1] != "{":
                break
            arg2, p2 = parse_braced(text, p1)
        except Exception:
            break

        text = text[: m.start()] + arg2 + text[p2:]

    return text


def parse_graphicspaths(text: str) -> List[str]:
    cleaned = strip_comments(text)
    paths: List[str] = []
    pattern = re.compile(r"\\graphicspath\s*\{")
    for match in pattern.finditer(cleaned):
        try:
            payload, _ = parse_braced(cleaned, match.end() - 1)
        except Exception:
            continue
        for inner in re.finditer(r"\{([^{}]+)\}", payload):
            entry = inner.group(1).strip()
            if entry:
                paths.append(entry)
    return paths


def build_graphic_search_dirs(project_dir: Path, main_text: str) -> List[Path]:
    search_dirs: List[Path] = [Path(".")]
    for raw in parse_graphicspaths(main_text):
        search_dirs.append(Path(raw))
    if (project_dir / "assets").exists():
        search_dirs.append(Path("assets"))

    deduped: List[Path] = []
    seen: set[str] = set()
    for rel in search_dirs:
        key = rel.as_posix()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rel)
    return deduped


def resolve_graphics_path(
    image_ref: str,
    project_dir: Path,
    source_dir: Path,
    graphic_search_dirs: Iterable[Path],
) -> str:
    candidate_text = image_ref.strip()
    if not candidate_text or "://" in candidate_text:
        return candidate_text

    candidate_path = Path(candidate_text)
    if candidate_path.is_absolute():
        return candidate_text if candidate_path.exists() else candidate_text

    try:
        source_rel = source_dir.resolve().relative_to(project_dir.resolve())
    except ValueError:
        source_rel = Path(".")

    search_roots: List[Path] = [Path("."), source_rel]
    search_roots.extend(graphic_search_dirs)

    deduped_roots: List[Path] = []
    seen_roots: set[str] = set()
    for root in search_roots:
        key = root.as_posix()
        if key in seen_roots:
            continue
        seen_roots.add(key)
        deduped_roots.append(root)

    suffixes = [""] if candidate_path.suffix else ["", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".svg"]
    for root in deduped_roots:
        for suffix in suffixes:
            rel_candidate = root / candidate_path
            if suffix:
                rel_candidate = rel_candidate.with_suffix(suffix)
            absolute_candidate = project_dir / rel_candidate
            if absolute_candidate.exists():
                return rel_candidate.as_posix()

    return candidate_text


def latex_inline_to_text(text: str) -> str:
    text = text.replace("\\LaTeX", "LaTeX")
    text = text.replace("\\quad", " ")
    text = text.replace("\\~{}", "~")
    text = text.replace("\\\\", " / ")

    for cmd in ["textbf", "textit", "emph", "underline", "texttt", "mbox", "textrm"]:
        text = re.sub(r"\\" + cmd + r"\{([^{}]*)\}", r"\1", text)

    text = re.sub(r"\\textsubscript\{([^{}]*)\}", r"_\1", text)
    text = re.sub(r"\\url\{([^{}]*)\}", r"<\1>", text)
    text = re.sub(r"\\path\{([^{}]*)\}", r"`\1`", text)
    text = re.sub(r"\\verb(.)(.*?)\1", r"`\2`", text)

    text = re.sub(r"\\gls\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\autoref\{([^{}]*)\}", r"见 \1", text)

    def _cite_repl(m: re.Match[str]) -> str:
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        if not keys:
            return ""
        return "[" + "; ".join(f"@{k}" for k in keys) + "]"

    text = re.sub(r"\\cite\{([^{}]+)\}", _cite_repl, text)
    text = re.sub(r"\\[a-zA-Z@]+\*?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def convert_abstract_file(text: str) -> str:
    text = strip_comments(text)
    abs_args = parse_macro_args(text, "abstract", 2)
    kw_args = parse_macro_args(text, "keywords", 2)

    lines: List[str] = []
    if abs_args:
        lines.append("# 摘要")
        lines.append("")
        lines.append(latex_inline_to_text(abs_args[0]))
        lines.append("")
        lines.append("# Abstract")
        lines.append("")
        lines.append(latex_inline_to_text(abs_args[1]))
        lines.append("")

    if kw_args:
        lines.append("## 关键词")
        lines.append("")
        lines.append(latex_inline_to_text(kw_args[0]))
        lines.append("")
        lines.append("## Keywords")
        lines.append("")
        lines.append(latex_inline_to_text(kw_args[1]))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def convert_info_file(text: str) -> str:
    text = strip_comments(text)
    title = parse_macro_args(text, "title", 2) or ["", ""]
    degree_level = parse_macro_args(text, "degreeLevel", 1) or [""]
    author = parse_macro_args(text, "author", 2) or ["", ""]
    supervisor = parse_macro_args(text, "supervisor", 3) or ["", "", ""]
    degree_type = parse_macro_args(text, "degreeType", 2) or ["", ""]
    subject = parse_macro_args(text, "subject", 2) or ["", ""]
    institute = parse_macro_args(text, "institute", 2) or ["", ""]
    grad_year = parse_macro_args(text, "gradYear", 1) or [""]
    grad_month = parse_macro_args(text, "gradMonth", 2) or ["", ""]

    lines = [
        "# 论文信息",
        "",
        f"- 中文题目：{latex_inline_to_text(title[0])}",
        f"- 英文题目：{latex_inline_to_text(title[1])}",
        f"- 学位层次：{latex_inline_to_text(degree_level[0])}",
        f"- 作者：{latex_inline_to_text(author[0])} / {latex_inline_to_text(author[1])}",
        f"- 导师：{latex_inline_to_text(supervisor[0])} / {latex_inline_to_text(supervisor[1])}",
        f"- 导师单位：{latex_inline_to_text(supervisor[2])}",
        f"- 学位类别：{latex_inline_to_text(degree_type[0])} / {latex_inline_to_text(degree_type[1])}",
        f"- 学科专业：{latex_inline_to_text(subject[0])} / {latex_inline_to_text(subject[1])}",
        f"- 培养单位：{latex_inline_to_text(institute[0])} / {latex_inline_to_text(institute[1])}",
        f"- 毕业时间：{latex_inline_to_text(grad_year[0])}-{latex_inline_to_text(grad_month[0])}",
        "",
    ]
    return "\n".join(lines)


def replace_env_blocks(text: str, env_name: str, replacer) -> str:
    pattern = re.compile(
        r"\\begin\{" + re.escape(env_name) + r"\}(.*?)\\end\{" + re.escape(env_name) + r"\}",
        re.S,
    )
    return pattern.sub(lambda m: replacer(m.group(1)), text)


def convert_body_tex(
    text: str,
    project_dir: Path,
    source_dir: Path,
    graphic_search_dirs: Iterable[Path],
) -> str:
    text = strip_comments(text)
    text = flatten_texorpdfstring(text)

    text = re.sub(r"\\mintinline\{[^{}]+\}\{([^{}]*)\}", lambda m: f"`{m.group(1)}`", text)
    text = re.sub(
        r"\\mint\{([^{}]+)\}\{([^{}]*)\}",
        lambda m: f"\n\n> 代码（{m.group(1)}）：`{m.group(2)}`\n\n",
        text,
    )
    text = re.sub(
        r"\\inputminted(?:\[[^\]]*\])?\{([^{}]+)\}\{([^{}]+)\}",
        lambda m: f"\n\n```{m.group(1)}\n[代码来自 {m.group(2)}]\n```\n\n",
        text,
    )

    def _equation_repl(block: str) -> str:
        block = re.sub(r"\\label\{[^{}]*\}", "", block)
        block = block.strip()
        if not block:
            return ""
        return f"\n\n$$\n{block}\n$$\n\n"

    text = replace_env_blocks(text, "equation", _equation_repl)

    def _figure_repl(block: str) -> str:
        cap = ""
        m_bi = re.search(r"\\bicaption\{([^{}]*)\}\{([^{}]*)\}", block)
        if m_bi:
            cap = latex_inline_to_text(m_bi.group(1))
        else:
            m_cap = re.search(r"\\caption\{([^{}]*)\}", block)
            if m_cap:
                cap = latex_inline_to_text(m_cap.group(1))

        m_img = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}", block)
        if m_img:
            img = resolve_graphics_path(m_img.group(1), project_dir, source_dir, graphic_search_dirs)
            return f"\n\n![{cap}]({img})\n\n"
        if cap:
            return f"\n\n> 图：{cap}\n\n"
        return "\n\n> 图：内容略\n\n"

    text = replace_env_blocks(text, "figure", _figure_repl)

    def _caption_only(prefix: str):
        def _inner(block: str) -> str:
            m_bi = re.search(r"\\bicaption\{([^{}]*)\}\{([^{}]*)\}", block)
            if m_bi:
                cap = latex_inline_to_text(m_bi.group(1))
            else:
                m_cap = re.search(r"\\caption\{([^{}]*)\}", block)
                cap = latex_inline_to_text(m_cap.group(1)) if m_cap else ""
            if cap:
                return f"\n\n> {prefix}：{cap}（需在 Word 中人工整理）\n\n"
            return f"\n\n> {prefix}：内容略（需在 Word 中人工整理）\n\n"

        return _inner

    text = replace_env_blocks(text, "table", _caption_only("表"))
    text = replace_env_blocks(text, "algorithm", _caption_only("算法"))
    text = replace_env_blocks(text, "listing", _caption_only("代码"))

    text = re.sub(r"\\begin\{(?:tabularx?|refsection|enumerate|itemize|algorithmic)\}[^\n]*", "", text)
    text = re.sub(r"\\end\{(?:tabularx?|refsection|enumerate|itemize|algorithmic)\}", "", text)
    text = re.sub(r"\\nocite\{[^{}]*\}", "", text)
    text = re.sub(r"\\printbibliography(?:\[[^\]]*\])?", "\n\n> 文献列表请在 Word 中按模板粘贴补全。\n\n", text)
    text = text.replace("\\acknowledgementsDate", "")

    heading_map = {
        "chapter": "#",
        "section": "##",
        "subsection": "###",
        "subsubsection": "###",
        "section*": "###",
        "subsection*": "###",
    }

    for cmd, h in heading_map.items():
        pattern = re.compile(r"\\" + re.escape(cmd) + r"\{([^{}]*)\}")
        text = pattern.sub(lambda m: f"\n\n{h} {latex_inline_to_text(m.group(1))}\n\n", text)

    text = re.sub(r"^[ \t]*\\item[ \t]*", "- ", text, flags=re.M)
    text = text.replace("\\\\", "\n")

    new_lines = []
    in_math = False
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            new_lines.append(line)
            continue

        if stripped == "$$":
            in_math = not in_math
            new_lines.append(line)
            continue

        if in_code or in_math:
            new_lines.append(line.rstrip())
            continue

        new_lines.append(latex_inline_to_text(line))

    text = "\n".join(new_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def parse_main_includes(main_tex: str) -> List[str]:
    includes: List[str] = []
    for m in re.finditer(r"\\(?:input|include)\{([^{}]+)\}", strip_comments(main_tex)):
        name = m.group(1).strip()
        if not name.endswith(".tex"):
            name += ".tex"
        includes.append(name)
    return includes


def render_markdown(project_dir: Path, tex_file: Path) -> str:
    main_text = tex_file.read_text(encoding="utf-8")
    include_files = parse_main_includes(main_text)
    graphic_search_dirs = build_graphic_search_dirs(project_dir, main_text)

    chunks: List[str] = [
        "# 学位论文（LaTeX 源转换稿）",
        "",
        "说明：本文件由 LaTeX 源自动转换，复杂表格/算法/代码块可能需要人工微调。",
        "",
    ]

    skip_names = {"config-pre.tex"}
    inserted_reference_heading = False
    for rel in include_files:
        if Path(rel).name in skip_names:
            continue
        p = (project_dir / rel).resolve()
        if not p.exists():
            chunks.append(f"> 警告：未找到文件 {rel}")
            chunks.append("")
            continue

        raw = p.read_text(encoding="utf-8")
        if p.name == "info.tex":
            chunks.append(convert_info_file(raw))
        elif p.name == "abstract.tex":
            chunks.append(convert_abstract_file(raw))
            chunks.extend(
                [
                    "# 目录",
                    "",
                    "> 目录域请在 Word 中右键更新。",
                    "",
                    "# 图表目录",
                    "",
                    "## 图目录",
                    "",
                    "> 图目录请在 Word 中右键更新。",
                    "",
                    "## 表目录",
                    "",
                    "> 表目录请在 Word 中右键更新。",
                    "",
                ]
            )
        else:
            if not inserted_reference_heading and p.name in {
                "appendix.tex",
                "appendix1.tex",
                "acknowledgements.tex",
                "cv.tex",
            }:
                chunks.extend(
                    [
                        "# 参考文献",
                        "",
                        "> 文献列表请在 Word 中按模板粘贴补全。",
                        "",
                    ]
                )
                inserted_reference_heading = True
            chunks.append(convert_body_tex(raw, project_dir, p.parent, graphic_search_dirs))
        chunks.append("")

    if not inserted_reference_heading:
        chunks.extend(
            [
                "# 参考文献",
                "",
                "> 文献列表请在 Word 中按模板粘贴补全。",
                "",
            ]
        )

    return "\n".join(chunks).strip() + "\n"


def run_pandoc(
    markdown_path: Path,
    output_docx: Path,
    reference_doc: Path,
    project_dir: Path,
    bibliography: Iterable[Path],
) -> None:
    if shutil.which("pandoc") is None:
        raise FileNotFoundError("未找到 pandoc，可先安装 pandoc 后再运行 DOCX 导出。")

    with TemporaryDirectory(prefix="thesis-docx-bib-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        sanitized_bibs: List[Path] = []
        for bib in bibliography:
            if not bib.exists():
                continue
            cleaned = strip_comments(bib.read_text(encoding="utf-8"))
            sanitized_path = tmp_root / bib.name
            sanitized_path.write_text(cleaned, encoding="utf-8")
            sanitized_bibs.append(sanitized_path)

        cmd = [
            "pandoc",
            str(markdown_path),
            "--from=markdown+tex_math_dollars+raw_tex",
            "--to=docx",
            "--standalone",
            f"--reference-doc={reference_doc}",
            f"--resource-path={project_dir}",
            "--citeproc",
            "-o",
            str(output_docx),
        ]

        for bib in sanitized_bibs:
            cmd.append(f"--bibliography={bib}")

        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir)
        if proc.returncode != 0:
            raise RuntimeError(
                "pandoc 转换失败\n"
                f"cmd: {' '.join(cmd)}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}\n"
            )


def _twip_to_cm(value: str) -> str:
    try:
        return f"{(float(value) * 2.54 / 1440):.2f}"
    except Exception:
        return "NA"


def _analyze_docx_styles(docx_path: Path) -> Dict[str, object]:
    style_name_by_id: Dict[str, str] = {}
    style_name_to_id: Dict[str, str] = {}
    style_ids: set[str] = set()
    usage: Counter[str] = Counter()
    usage_body: Counter[str] = Counter()
    layout: Dict[str, str] = {}
    style_props: Dict[str, Dict[str, str]] = {}
    body_paragraphs: List[Tuple[str, str]] = []

    with zipfile.ZipFile(docx_path, "r") as zf:
        styles_xml = zf.read("word/styles.xml")
        styles_root = ET.fromstring(styles_xml)
        for st in styles_root.findall("w:style", W):
            if st.get(_w_attr("type"), "") != "paragraph":
                continue
            sid = st.get(_w_attr("styleId"), "")
            if not sid:
                continue
            style_ids.add(sid)
            name_node = st.find("w:name", W)
            sname = name_node.get(_w_attr("val"), sid) if name_node is not None else sid
            style_name_by_id[sid] = sname
            style_name_to_id[sname.casefold()] = sid

            ppr = st.find("w:pPr", W)
            rpr = st.find("w:rPr", W)
            spacing = ppr.find("w:spacing", W) if ppr is not None else None
            ind = ppr.find("w:ind", W) if ppr is not None else None
            jc = ppr.find("w:jc", W) if ppr is not None else None
            fonts = rpr.find("w:rFonts", W) if rpr is not None else None
            sz = rpr.find("w:sz", W) if rpr is not None else None
            style_props[sid] = {
                "line": spacing.get(_w_attr("line"), "") if spacing is not None else "",
                "lineRule": spacing.get(_w_attr("lineRule"), "") if spacing is not None else "",
                "before": spacing.get(_w_attr("before"), "") if spacing is not None else "",
                "after": spacing.get(_w_attr("after"), "") if spacing is not None else "",
                "firstLine": ind.get(_w_attr("firstLine"), "") if ind is not None else "",
                "left": ind.get(_w_attr("left"), "") if ind is not None else "",
                "jc": jc.get(_w_attr("val"), "") if jc is not None else "",
                "font_ascii": fonts.get(_w_attr("ascii"), "") if fonts is not None else "",
                "font_hAnsi": fonts.get(_w_attr("hAnsi"), "") if fonts is not None else "",
                "font_eastAsia": fonts.get(_w_attr("eastAsia"), "") if fonts is not None else "",
                "size_half_points": sz.get(_w_attr("val"), "") if sz is not None else "",
            }

        for name in zf.namelist():
            if not name.endswith(".xml"):
                continue
            if not (
                name == "word/document.xml"
                or name.startswith("word/header")
                or name.startswith("word/footer")
                or name in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}
            ):
                continue
            data = zf.read(name)
            try:
                root = ET.fromstring(data)
            except Exception:
                continue
            for para in root.findall(".//w:p", W):
                ppr = para.find("w:pPr", W)
                if ppr is None:
                    continue
                pstyle = ppr.find("w:pStyle", W)
                if pstyle is None:
                    continue
                sid = pstyle.get(_w_attr("val"), "")
                if sid:
                    usage[sid] += 1

        try:
            doc_root = ET.fromstring(zf.read("word/document.xml"))
            for para in doc_root.findall(".//w:body//w:p", W):
                ppr = para.find("w:pPr", W)
                sid = ""
                if ppr is not None:
                    pstyle = ppr.find("w:pStyle", W)
                    if pstyle is not None:
                        sid = pstyle.get(_w_attr("val"), "")
                if sid:
                    usage_body[sid] += 1
                text = "".join(t.text or "" for t in para.findall(".//w:t", W)).strip()
                if text:
                    body_paragraphs.append((sid, text))
        except Exception:
            pass

        try:
            doc_root = ET.fromstring(zf.read("word/document.xml"))
            sect = doc_root.find(".//w:sectPr", W)
            if sect is not None:
                pg_sz = sect.find("w:pgSz", W)
                pg_mar = sect.find("w:pgMar", W)
                if pg_sz is not None:
                    layout["page_w_twip"] = pg_sz.get(_w_attr("w"), "")
                    layout["page_h_twip"] = pg_sz.get(_w_attr("h"), "")
                if pg_mar is not None:
                    layout["margin_top_twip"] = pg_mar.get(_w_attr("top"), "")
                    layout["margin_bottom_twip"] = pg_mar.get(_w_attr("bottom"), "")
                    layout["margin_left_twip"] = pg_mar.get(_w_attr("left"), "")
                    layout["margin_right_twip"] = pg_mar.get(_w_attr("right"), "")
                    layout["margin_header_twip"] = pg_mar.get(_w_attr("header"), "")
                    layout["margin_footer_twip"] = pg_mar.get(_w_attr("footer"), "")
        except Exception:
            pass

    unknown = Counter({sid: cnt for sid, cnt in usage.items() if sid not in style_ids})
    return {
        "style_ids": style_ids,
        "style_name_by_id": style_name_by_id,
        "style_name_to_id": style_name_to_id,
        "usage": usage,
        "usage_body": usage_body,
        "unknown": unknown,
        "layout": layout,
        "style_props": style_props,
        "body_paragraphs": body_paragraphs,
    }


def _resolve_style_id(
    style_ids: set[str],
    style_name_to_id: Dict[str, str],
    preferred_ids: List[str],
    preferred_names: List[str],
    fallback: str,
) -> str:
    for sid in preferred_ids:
        if sid in style_ids:
            return sid
    for name in preferred_names:
        sid = style_name_to_id.get(name.casefold())
        if sid and sid in style_ids:
            return sid
    if fallback in style_ids:
        return fallback
    return next(iter(style_ids))


def _build_style_remap(style_info: Dict[str, object]) -> Dict[str, str]:
    style_ids = style_info["style_ids"]  # type: ignore[assignment]
    style_name_to_id = style_info["style_name_to_id"]  # type: ignore[assignment]

    normal_id = _resolve_style_id(style_ids, style_name_to_id, ["a", "Normal"], ["normal"], "a")
    caption_id = _resolve_style_id(
        style_ids,
        style_name_to_id,
        ["ae", "Caption", "caption"],
        ["caption"],
        normal_id,
    )
    h1_id = _resolve_style_id(style_ids, style_name_to_id, ["1", "Heading1"], ["heading 1"], normal_id)
    h2_id = _resolve_style_id(style_ids, style_name_to_id, ["2", "Heading2"], ["heading 2"], normal_id)
    h3_id = _resolve_style_id(style_ids, style_name_to_id, ["3", "Heading3"], ["heading 3"], normal_id)
    h4_id = _resolve_style_id(style_ids, style_name_to_id, ["4", "Heading4"], ["heading 4"], normal_id)

    return {
        "FirstParagraph": normal_id,
        "First Paragraph": normal_id,
        "BodyText": normal_id,
        "Body Text": normal_id,
        "Compact": normal_id,
        "BlockText": normal_id,
        "Block Text": normal_id,
        "Bibliography": normal_id,
        "ImageCaption": caption_id,
        "Image Caption": caption_id,
        "Heading1": h1_id,
        "Heading2": h2_id,
        "Heading3": h3_id,
        "Heading4": h4_id,
    }


def _normalize_paragraph_styles_with_python_docx(docx_path: Path, remap: Dict[str, str]) -> Tuple[int, bool]:
    if DocxDocument is None:
        return 0, False

    doc = DocxDocument(str(docx_path))
    changed = 0
    for para in doc.paragraphs:
        ppr = para._p.pPr
        if ppr is None or ppr.pStyle is None:
            continue
        sid = ppr.pStyle.val
        if sid in remap:
            ppr.pStyle.val = remap[sid]
            changed += 1

    if changed:
        doc.save(str(docx_path))
    return changed, True


def _rewrite_docx_styles_xml(docx_path: Path, remap: Dict[str, str]) -> Counter[str]:
    replaced: Counter[str] = Counter()

    with NamedTemporaryFile(delete=False, suffix=".docx", dir=str(docx_path.parent)) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(
            tmp_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    try:
                        root = ET.fromstring(data)
                        changed = False
                        for pstyle in root.findall(".//w:pStyle", W):
                            sid = pstyle.get(_w_attr("val"), "")
                            if sid in remap:
                                pstyle.set(_w_attr("val"), remap[sid])
                                replaced[sid] += 1
                                changed = True
                        if changed:
                            data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    except Exception:
                        pass
                zout.writestr(item, data)

        tmp_path.replace(docx_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    return replaced


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "").replace("　", "")


def _count_keywords(line: str) -> int:
    if "：" in line:
        payload = line.split("：", 1)[1]
    elif ":" in line:
        payload = line.split(":", 1)[1]
    else:
        payload = line
    parts = [p.strip() for p in re.split(r"[，,、;；]", payload) if p.strip()]
    return len(parts)


def _extract_labeled_value(body_paragraphs: List[Tuple[str, str]], labels: List[str]) -> Optional[str]:
    labels_norm = [_norm(x) for x in labels]
    for _, text in body_paragraphs:
        raw = text.strip()
        if not raw:
            continue
        nt = _norm(raw)
        for label in labels_norm:
            if not nt.startswith(label):
                continue
            if "：" in raw:
                return raw.split("：", 1)[1].strip()
            if ":" in raw:
                return raw.split(":", 1)[1].strip()
            tail = raw[len(label) :].strip()
            return tail.lstrip("：: ").strip()
    return None


def _count_nonspace_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def _count_ascii_letters(text: str) -> int:
    return len(re.findall(r"[A-Za-z]", text or ""))


def _style_level_from_name(style_name: str, prefix: str) -> Optional[int]:
    norm = re.sub(r"[\s_-]+", "", (style_name or "").casefold())
    m = re.fullmatch(re.escape(prefix) + r"(\d+)", norm)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _spec_checks(after: Dict[str, object]) -> List[Tuple[str, str, str]]:
    layout = after["layout"]  # type: ignore[assignment]
    usage_body = after["usage_body"]  # type: ignore[assignment]
    style_name_by_id = after["style_name_by_id"]  # type: ignore[assignment]
    style_name_to_id = after["style_name_to_id"]  # type: ignore[assignment]
    style_props = after["style_props"]  # type: ignore[assignment]
    body_paragraphs = after["body_paragraphs"]  # type: ignore[assignment]

    checks: List[Tuple[str, str, str]] = []

    a4_ok = layout.get("page_w_twip") == "11906" and layout.get("page_h_twip") == "16838"
    checks.append(
        (
            "纸张A4(210x297mm, 表3)",
            "PASS" if a4_ok else "WARN",
            f"{layout.get('page_w_twip')} x {layout.get('page_h_twip')} twip",
        )
    )

    margin_ok = (
        layout.get("margin_top_twip") == "1440"
        and layout.get("margin_bottom_twip") == "1440"
        and layout.get("margin_left_twip") == "1797"
        and layout.get("margin_right_twip") == "1797"
        and layout.get("margin_header_twip") == "851"
        and layout.get("margin_footer_twip") == "851"
    )
    checks.append(
        (
            "页边距与页眉页脚距离(表3)",
            "PASS" if margin_ok else "WARN",
            "top/bottom={}/{} left/right={}/{} header/footer={}/{}".format(
                layout.get("margin_top_twip"),
                layout.get("margin_bottom_twip"),
                layout.get("margin_left_twip"),
                layout.get("margin_right_twip"),
                layout.get("margin_header_twip"),
                layout.get("margin_footer_twip"),
            ),
        )
    )

    normal_id = style_name_to_id.get("normal", "a")
    normal = style_props.get(normal_id, {})
    normal_font_ok = "宋体" in normal.get("font_eastAsia", "") and (
        "Times New Roman" in normal.get("font_ascii", "") or "Times New Roman" in normal.get("font_hAnsi", "")
    )
    checks.append(
        (
            "正文样式字体(宋体+Times New Roman, 表7)",
            "PASS" if normal_font_ok else "WARN",
            "eastAsia={} ascii={} hAnsi={}".format(
                normal.get("font_eastAsia", ""),
                normal.get("font_ascii", ""),
                normal.get("font_hAnsi", ""),
            ),
        )
    )

    normal_para_ok = normal.get("line") == "300" and normal.get("firstLine") == "200"
    checks.append(
        (
            "正文样式行距/首行缩进(1.25倍/两字符, 表7)",
            "PASS" if normal_para_ok else "WARN",
            f"line={normal.get('line', '')}, firstLine={normal.get('firstLine', '')}",
        )
    )

    h4 = style_name_to_id.get("heading 4", "4")
    h4_count = int(usage_body.get(h4, 0))
    checks.append(("正文是否超过三级标题(0083)", "PASS" if h4_count == 0 else "WARN", f"Heading4 count={h4_count}"))

    toc_level_over_count = 0
    toc_entry_count = 0
    for sid, cnt in usage_body.items():
        if cnt <= 0:
            continue
        level = _style_level_from_name(style_name_by_id.get(sid, sid), "toc")
        if level is None:
            continue
        toc_entry_count += int(cnt)
        if level > 3:
            toc_level_over_count += int(cnt)
    if toc_entry_count == 0:
        checks.append(("目录是否超过三级标题(0036)", "WARN", "未检测到目录域，建议在 Word 中更新目录后复检"))
    else:
        checks.append(
            (
                "目录是否超过三级标题(0036)",
                "PASS" if toc_level_over_count == 0 else "WARN",
                f"目录项 {toc_entry_count} 条，超三级 {toc_level_over_count} 条",
            )
        )

    numbered_over3 = 0
    numbered_pat = re.compile(r"^\d+(?:\.\d+){3,}(?:\s|$)")
    for sid, text in body_paragraphs:
        level = _style_level_from_name(style_name_by_id.get(sid, sid), "heading")
        if level is None:
            continue
        if numbered_pat.match(text.strip()):
            numbered_over3 += 1
    checks.append(
        (
            "标题编号是否超过三级(0083)",
            "PASS" if numbered_over3 == 0 else "WARN",
            f"检测到四级及以上编号标题 {numbered_over3} 处",
        )
    )

    zh_title = _extract_labeled_value(body_paragraphs, ["中文题目", "论文题目"])
    if zh_title:
        zh_len = _count_nonspace_chars(zh_title)
        checks.append(("中文题目长度(≤25字/符, 0016)", "PASS" if zh_len <= 25 else "WARN", f"当前 {zh_len}"))
    else:
        checks.append(("中文题目长度(≤25字/符, 0016)", "WARN", "未自动识别“中文题目”字段"))

    en_title = _extract_labeled_value(body_paragraphs, ["英文题目"])
    if en_title:
        en_letters = _count_ascii_letters(en_title)
        checks.append(("英文题目长度(≤150字母, 0016)", "PASS" if en_letters <= 150 else "WARN", f"当前约 {en_letters}"))
    else:
        checks.append(("英文题目长度(≤150字母, 0016)", "WARN", "未自动识别“英文题目”字段"))

    norm_texts = [_norm(t) for _, t in body_paragraphs]
    required = ["摘要", "Abstract", "参考文献", "致谢"]
    for sec in required:
        has = any(t == _norm(sec) or sec in t for t in norm_texts)
        checks.append((f"章节存在：{sec}", "PASS" if has else "WARN", "已检测" if has else "未检测到"))

    has_toc = any(t == "目录" for t in norm_texts) or toc_entry_count > 0
    toc_detail = "已检测到目录标题/目录域" if has_toc else "建议在 Word 中更新目录域"
    checks.append(("章节存在：目录", "PASS" if has_toc else "WARN", toc_detail))

    has_lot = any(t in {"图目录", "表目录", "图表目录"} for t in norm_texts)
    checks.append(("章节存在：图表目录", "PASS" if has_lot else "WARN", "已检测" if has_lot else "建议在 Word 中补图表目录"))

    zh_kw_count = -1
    en_kw_count = -1
    zh_abstract_chars = -1
    try:
        idx_zh = next(i for i, t in enumerate(norm_texts) if t == "摘要")
        idx_en = next(i for i, t in enumerate(norm_texts[idx_zh + 1 :], start=idx_zh + 1) if t.lower() == "abstract")
        zh_lines: List[str] = []
        for _, t in body_paragraphs[idx_zh + 1 : idx_en]:
            nt = _norm(t)
            nt_cf = nt.casefold()
            if nt.startswith("关键词") or nt_cf.startswith("keywords") or nt_cf.startswith("keyword"):
                continue
            if nt:
                zh_lines.append(t.strip())
        zh_abstract_chars = len(re.sub(r"\s+", "", "".join(zh_lines)))
    except Exception:
        pass

    for i, (_, t) in enumerate(body_paragraphs):
        nt = _norm(t)
        if nt.startswith("关键词"):
            zh_kw_count = _count_keywords(t)
            if zh_kw_count <= 1 and i + 1 < len(body_paragraphs):
                ntext = body_paragraphs[i + 1][1].strip()
                if ntext:
                    zh_kw_count = _count_keywords(ntext)
        nt_cf = nt.casefold()
        if nt_cf.startswith("keywords") or nt_cf.startswith("keyword"):
            en_kw_count = _count_keywords(t)
            if en_kw_count <= 1 and i + 1 < len(body_paragraphs):
                ntext = body_paragraphs[i + 1][1].strip()
                if ntext:
                    en_kw_count = _count_keywords(ntext)

    if zh_abstract_chars >= 0:
        ok = 1500 <= zh_abstract_chars <= 3000
        checks.append(("中文摘要字数(1500-3000, 0032)", "PASS" if ok else "WARN", f"当前约 {zh_abstract_chars} 字"))
    else:
        checks.append(("中文摘要字数(1500-3000, 0032)", "WARN", "未能自动识别摘要边界"))

    if zh_kw_count >= 0:
        ok = 3 <= zh_kw_count <= 6
        checks.append(("中文关键词数量(3-6, 0033)", "PASS" if ok else "WARN", f"当前 {zh_kw_count} 个"))
    else:
        checks.append(("中文关键词数量(3-6, 0033)", "WARN", "未检测到“关键词”行"))

    if en_kw_count >= 0:
        ok = 3 <= en_kw_count <= 6
        checks.append(("英文关键词数量(3-6, 0033)", "PASS" if ok else "WARN", f"当前 {en_kw_count} 个"))
    else:
        checks.append(("英文关键词数量(3-6, 0033)", "WARN", "未检测到“Key Words/Keywords”行"))

    return checks


def _write_quality_report(
    report_path: Path,
    docx_path: Path,
    remap: Dict[str, str],
    py_changed: int,
    python_docx_available: bool,
    xml_changed: Counter[str],
    before: Dict[str, object],
    after: Dict[str, object],
) -> None:
    before_unknown = before["unknown"]  # type: ignore[assignment]
    after_unknown = after["unknown"]  # type: ignore[assignment]
    before_usage = before["usage"]  # type: ignore[assignment]
    after_usage = after["usage"]  # type: ignore[assignment]
    style_name_by_id = after["style_name_by_id"]  # type: ignore[assignment]
    layout = after["layout"]  # type: ignore[assignment]
    style_name_to_id = after["style_name_to_id"]  # type: ignore[assignment]

    h1 = style_name_to_id.get("heading 1", "1")
    h2 = style_name_to_id.get("heading 2", "2")
    h3 = style_name_to_id.get("heading 3", "3")
    h4 = style_name_to_id.get("heading 4", "4")

    lines = [
        "# DOCX 质量报告",
        "",
        f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 文件：`{docx_path}`",
        "",
        "## 样式修正摘要",
        "",
        f"- python-docx 可用：`{'yes' if python_docx_available else 'no'}`",
        f"- python-docx 直接修正段落数：`{py_changed}`",
        f"- XML 全局修正段落数：`{sum(xml_changed.values())}`",
        f"- 修正规则数：`{len(remap)}`",
        "",
        "## 未知样式对比",
        "",
        f"- 修正前未知样式引用：`{sum(before_unknown.values())}`",
    ]

    for sid, cnt in before_unknown.most_common(20):
        lines.append(f"  - `{sid}`: {cnt}")

    lines.append(f"- 修正后未知样式引用：`{sum(after_unknown.values())}`")
    for sid, cnt in after_unknown.most_common(20):
        lines.append(f"  - `{sid}`: {cnt}")

    lines.extend(
        [
            "",
            "## 标题层级统计",
            "",
            f"- Heading 1（`{h1}`）：`{after_usage.get(h1, 0)}`",
            f"- Heading 2（`{h2}`）：`{after_usage.get(h2, 0)}`",
            f"- Heading 3（`{h3}`）：`{after_usage.get(h3, 0)}`",
            f"- Heading 4（`{h4}`）：`{after_usage.get(h4, 0)}`",
            "",
            "## 版面参数（首个分节）",
            "",
            f"- 纸张（twip）：`{layout.get('page_w_twip', 'NA')} x {layout.get('page_h_twip', 'NA')}`",
            f"- 纸张（cm）：`{_twip_to_cm(layout.get('page_w_twip', ''))} x {_twip_to_cm(layout.get('page_h_twip', ''))}`",
            f"- 页边距上/下（twip）：`{layout.get('margin_top_twip', 'NA')} / {layout.get('margin_bottom_twip', 'NA')}`",
            f"- 页边距左/右（twip）：`{layout.get('margin_left_twip', 'NA')} / {layout.get('margin_right_twip', 'NA')}`",
            "",
            "## 样式分布（Top 12）",
            "",
            "| 样式ID | 样式名 | 修正前 | 修正后 |",
            "|---|---|---:|---:|",
        ]
    )

    top_ids = [sid for sid, _ in after_usage.most_common(12)]
    for sid, _ in before_usage.most_common(12):
        if sid not in top_ids:
            top_ids.append(sid)
        if len(top_ids) >= 12:
            break

    for sid in top_ids[:12]:
        lines.append(
            "| `{sid}` | {name} | {b} | {a} |".format(
                sid=sid,
                name=style_name_by_id.get(sid, sid),
                b=before_usage.get(sid, 0),
                a=after_usage.get(sid, 0),
            )
        )

    checks = _spec_checks(after)
    lines.extend(
        [
            "",
            "## 资环规范一致性检查（自动）",
            "",
            "- 依据：`中国科学院大学资源与环境学位评定分委员会研究生学位论文撰写具体要`（2023）",
            "",
        ]
    )
    lines.append("| 检查项 | 结果 | 说明 |")
    lines.append("|---|---|---|")
    for item, status, detail in checks:
        lines.append(f"| {item} | {status} | {detail} |")

    lines.extend(
        [
            "",
            "## 后处理说明",
            "",
            (
                "- 当前环境已启用 `python-docx`，会先做段落级样式修正，"
                "再做 XML 全局样式归一化。"
                if python_docx_available
                else "- 当前环境未启用 `python-docx`，本次仅执行 XML 全局样式归一化。"
            ),
        ]
    )

    lines.extend(["", "## 样式映射规则", ""])
    for src, dst in remap.items():
        lines.append(f"- `{src}` -> `{dst}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_docx_styles(docx_path: Path, report_path: Path) -> None:
    before = _analyze_docx_styles(docx_path)
    remap = _build_style_remap(before)
    py_changed, python_docx_available = _normalize_paragraph_styles_with_python_docx(docx_path, remap)
    xml_changed = _rewrite_docx_styles_xml(docx_path, remap)
    after = _analyze_docx_styles(docx_path)
    _write_quality_report(
        report_path,
        docx_path,
        remap,
        py_changed,
        python_docx_available,
        xml_changed,
        before,
        after,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export thesis LaTeX source to docx with reference template.")
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parents[1], help="论文项目目录")
    parser.add_argument("--tex-file", type=str, default="main.tex", help="主 tex 文件名")
    parser.add_argument("--reference-doc", type=Path, default=None, help="参考 Word 模板 .docx")
    parser.add_argument("--output", type=Path, default=None, help="输出 docx 路径")
    parser.add_argument("--markdown-output", type=Path, default=None, help="中间 markdown 路径")
    parser.add_argument("--quality-report", type=Path, default=None, help="质量报告路径")
    parser.add_argument(
        "--skip-style-normalization",
        action="store_true",
        help="仅导出 docx，不做样式归一化与质量报告",
    )
    parser.add_argument(
        "--postprocess-only-docx",
        type=Path,
        default=None,
        help="仅对已有 docx 做样式归一化与质量报告，不重新跑 pandoc",
    )
    args = parser.parse_args()

    if args.postprocess_only_docx is not None:
        docx_path = args.postprocess_only_docx.resolve()
        if not docx_path.exists():
            raise FileNotFoundError(f"待处理 docx 不存在: {docx_path}")
        report_path = (
            args.quality_report.resolve()
            if args.quality_report
            else docx_path.with_name(f"{docx_path.stem}_质量报告.md")
        )
        normalize_docx_styles(docx_path, report_path)
        print(f"[OK] postprocess docx: {docx_path}")
        print(f"[OK] quality report: {report_path}")
        return 0

    project_dir = args.project_dir.resolve()
    tex_file = (project_dir / args.tex_file).resolve()
    reference_doc = discover_reference_doc(project_dir, args.reference_doc)

    if not tex_file.exists():
        raise FileNotFoundError(f"主文件不存在: {tex_file}")
    tex_stem = tex_file.stem
    output_docx = args.output.resolve() if args.output else (project_dir / f"{tex_stem}_from_tex_资环模板.docx")
    markdown_path = (
        args.markdown_output.resolve()
        if args.markdown_output
        else (project_dir / f"{tex_stem}_from_tex_word_source.md")
    )

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    output_docx.parent.mkdir(parents=True, exist_ok=True)

    md_text = render_markdown(project_dir, tex_file)
    markdown_path.write_text(md_text, encoding="utf-8")

    bibliography = list((project_dir / "bibs").glob("*.bib"))
    run_pandoc(markdown_path, output_docx, reference_doc, project_dir, bibliography)

    if not args.skip_style_normalization:
        report_path = (
            args.quality_report.resolve()
            if args.quality_report
            else output_docx.with_name(f"{output_docx.stem}_质量报告.md")
        )
        normalize_docx_styles(output_docx, report_path)
        print(f"[OK] quality report: {report_path}")

    print(f"[OK] markdown: {markdown_path}")
    print(f"[OK] docx: {output_docx}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
