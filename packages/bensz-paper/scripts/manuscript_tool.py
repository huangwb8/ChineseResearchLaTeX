#!/usr/bin/env python3
"""
SCI manuscript build tool bundled with bensz-paper.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Pt

VERSION = "1.2.0"
PROJECT_ROOT_MARKERS = ("main.tex", "references/meta.yaml")
TOOL_CANDIDATES = {
    "xelatex": (
        "/Library/TeX/texbin/xelatex",
        "/usr/local/texlive/2024/bin/universal-darwin/xelatex",
        "/usr/local/texlive/2024/bin/x86_64-linux/xelatex",
    ),
    "biber": (
        "/Library/TeX/texbin/biber",
        "/usr/local/texlive/2024/bin/universal-darwin/biber",
        "/usr/local/texlive/2024/bin/x86_64-linux/biber",
    ),
    "pandoc": ("/opt/homebrew/bin/pandoc", "/usr/local/bin/pandoc"),
    "soffice": (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
    ),
}


def run_cmd(args: list[str], cwd: Path | None = None, input_text: str | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def configure_windows_stdio_utf8() -> None:
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run_best_effort(
    args: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def pandoc_markdown_to_latex(md_text: str) -> str:
    placeholder_map: dict[str, str] = {}

    def cite_repl(match: re.Match[str]) -> str:
        token = f"CITETOKEN{len(placeholder_map) + 1:04d}"
        keys = [part.strip().lstrip("@") for part in match.group(1).split(";") if part.strip()]
        placeholder_map[token] = "\\supercite{" + ",".join(keys) + "}"
        return token

    md_text = re.sub(r"\[([^\]]*@[^\]]+)\]", cite_repl, md_text)
    latex = run_cmd(
        [resolve_executable("pandoc"), "-f", "gfm+raw_html", "-t", "latex"],
        input_text=md_text,
    )
    latex = latex.strip()
    for token, replacement in placeholder_map.items():
        latex = latex.replace(token, replacement)
        latex = latex.replace("{" + token + "}", replacement)
    latex = latex.replace("\\textbackslash{}", "\\")
    return latex.strip() + "\n"


def _add_references_heading_if_missing(doc: "Document", heading_text: str = "References") -> None:
    first_bib = next((p for p in doc.paragraphs if p.style.name == "Bibliography"), None)
    if first_bib is None:
        return

    already_exists = any(
        p.style.name.startswith("Heading") and p.text.strip().lower() == heading_text.lower()
        for p in doc.paragraphs
    )
    if already_exists:
        return

    heading = doc.add_heading(heading_text, level=2)
    heading_elem = heading._element
    heading_elem.getparent().remove(heading_elem)
    first_bib._element.addprevious(heading_elem)


def _reorder_references_before_figure_legends(
    doc: "Document",
    references_heading: str = "References",
    figure_legends_heading: str = "Figure legends",
) -> None:
    paras = doc.paragraphs
    ref_heading_para = next(
        (
            p
            for p in paras
            if p.style.name.startswith("Heading")
            and p.text.strip().lower() == references_heading.lower()
        ),
        None,
    )
    if ref_heading_para is None:
        return

    fig_legends_para = next(
        (
            p
            for p in paras
            if p.style.name.startswith("Heading")
            and p.text.strip().lower() == figure_legends_heading.lower()
        ),
        None,
    )
    if fig_legends_para is None:
        return

    bib_elements = [p._element for p in paras if p.style.name == "Bibliography"]
    if not bib_elements:
        return

    body_elem = ref_heading_para._element.getparent()
    children = list(body_elem)
    fig_idx = children.index(fig_legends_para._element)
    ref_idx = children.index(ref_heading_para._element)
    all_before = ref_idx < fig_idx and all(children.index(e) < fig_idx for e in bib_elements)
    if all_before:
        return

    ref_block = [ref_heading_para._element] + bib_elements
    for elem in ref_block:
        body_elem.remove(elem)

    anchor = fig_legends_para._element
    for elem in ref_block:
        anchor.addprevious(elem)


def fix_docx_spacing(docx_path: Path) -> None:
    body_indent = Pt(18)
    no_indent = Pt(0)
    no_indent_sections = {"Abstract", "Figure legends", "Supplementary materials"}

    doc = Document(docx_path)
    _add_references_heading_if_missing(doc)
    _reorder_references_before_figure_legends(doc)

    in_no_indent_section = False
    prev_was_heading = True
    seen_section_heading = False

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        is_heading = style_name.startswith("Heading")
        is_bibliography = style_name == "Bibliography"

        pf = para.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        pf.space_after = Pt(4)
        pf.space_before = Pt(0)

        if is_heading:
            if style_name != "Heading 1":
                seen_section_heading = True
            in_no_indent_section = para.text.strip() in no_indent_sections
            prev_was_heading = True
            pf.first_line_indent = no_indent
        elif is_bibliography:
            pf.first_line_indent = no_indent
            pf.left_indent = no_indent
            for run in para.runs:
                if "\t" in run.text:
                    run.text = run.text.replace("\t", "")
            prev_was_heading = False
        else:
            if not seen_section_heading or in_no_indent_section or prev_was_heading:
                pf.first_line_indent = no_indent
            else:
                pf.first_line_indent = body_indent
            prev_was_heading = False

    doc.save(docx_path)


def is_project_root(path: Path) -> bool:
    return any((path / marker).exists() for marker in PROJECT_ROOT_MARKERS)


def find_project_root(start: Path | None = None) -> Path:
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "Cannot find project root. Run inside the manuscript project tree or "
        "pass --project-dir explicitly."
    )


def resolve_project_dir(project_dir: Path | None) -> Path:
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


def resolve_executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    for candidate in TOOL_CANDIDATES.get(name, ()):
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"Required executable not found: {name}")


def build_texinputs(prefixes: list[Path], existing: str) -> str:
    normalized = [f"{path.resolve()}//" for path in prefixes]
    normalized.append("")
    if existing:
        normalized.append(existing)
    return os.pathsep.join(normalized)


def resolve_tex_search_roots(project_dir: Path) -> list[Path]:
    roots: list[Path] = []

    project_tex_root = project_dir / "texmf" / "tex" / "latex"
    if project_tex_root.exists():
        roots.append(project_tex_root)

    package_root = Path(__file__).resolve().parents[1]
    if (package_root / "bml-core.sty").exists() and package_root not in roots:
        roots.append(package_root)

    fonts_package_root = package_root.parent / "bensz-fonts"
    if (fonts_package_root / "bensz-fonts.sty").exists() and fonts_package_root not in roots:
        roots.append(fonts_package_root)

    return roots


def summarize_process_output(label: str, result: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in (result.stdout + "\n" + result.stderr).splitlines() if line.strip()]
    tail = "\n".join(lines[-20:]) if lines else "(no output)"
    return f"[{label}] exit={result.returncode}\n{tail}"


def _shift_heading_levels(md_text: str, shift: int = 1) -> str:
    result = []
    for line in md_text.splitlines():
        match = re.match(r"^(#{1,6})(\s.*|$)", line)
        if match:
            new_level = min(len(match.group(1)) + shift, 6)
            line = "#" * new_level + match.group(2)
        result.append(line)
    return "\n".join(result)


def build_markdown_for_docx(project_dir: Path, meta: dict, manifest: list[dict]) -> str:
    manuscript = meta["manuscript"]
    lines: list[str] = [f"# {manuscript['title']}", ""]

    authors = []
    for item in manuscript["authors"]:
        markers = "".join(item["markers"])
        authors.append(f"{item['name']}<sup>{markers}</sup>")
    if authors:
        if len(authors) > 1:
            lines.append(", ".join(authors[:-1]) + ", and " + authors[-1] + ".")
        else:
            lines.append(authors[0])
        lines.append("")

    for marker, content in manuscript["affiliations"].items():
        lines.append(f"<sup>{marker}</sup>{content}")
        lines.append("")

    for line in manuscript.get("equal_contribution", []):
        lines.append(f"<sup>†</sup>{line}")
        lines.append("")

    if manuscript.get("correspondence"):
        lines.append(f"*Correspondence:* {manuscript['correspondence']}")
        lines.append("")

    if manuscript.get("running_title"):
        lines.append(f"Running title: {manuscript['running_title']}")
        lines.append("")

    for node in manifest:
        if node["kind"] == "single":
            lines.append(f"## {node['title']}")
            lines.append("")
            md_path = project_dir / node["path"]
            content = md_path.read_text(encoding="utf-8").strip()
            lines.append(_shift_heading_levels(content, shift=1))
            lines.append("")
        else:
            lines.append(f"## {node['title']}")
            lines.append("")
            for child in node.get("children", []):
                lines.append(f"### {child['title']}")
                lines.append("")
                md_path = project_dir / child["path"]
                content = md_path.read_text(encoding="utf-8").strip()
                lines.append(_shift_heading_levels(content, shift=2))
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_author_line(authors: list[dict[str, object]]) -> str:
    rendered = []
    for item in authors:
        markers = "".join(f"\\textsuperscript{{{latex_escape(str(marker))}}}" for marker in item["markers"])
        rendered.append(f"{latex_escape(item['name'])}{markers}")
    return ", ".join(rendered)


def render_frontmatter_tex(meta: dict) -> str:
    manuscript = meta["manuscript"]
    title = latex_escape(manuscript["title"])
    lines = [
        "{",
        "\\thispagestyle{fancy}",
        "\\begin{center}",
        f"{{\\bfseries\\fontsize{{15.12}}{{20}}\\selectfont {title}\\par}}",
        "\\vspace{1.2\\baselineskip}",
        _render_author_line(manuscript["authors"]) + "\\par",
        "\\end{center}",
        "",
        "\\sloppy",
    ]

    for marker, content in manuscript["affiliations"].items():
        lines.append(
            f"\\noindent\\textsuperscript{{{latex_escape(str(marker))}}}{latex_escape(content)}\\par"
        )
    for line in manuscript.get("equal_contribution", []):
        lines.append(f"\\noindent\\textsuperscript{{†}}{latex_escape(line)}\\par")
    if manuscript.get("correspondence"):
        lines.append(
            f"\\noindent\\textsuperscript{{*}}Correspondence: {latex_escape(manuscript['correspondence'])}.\\par"
        )
    if manuscript.get("running_title"):
        lines.append(f"\\noindent Running title: {latex_escape(manuscript['running_title'])}\\par")
    lines.extend(["\\fussy", "}"])
    return "\n".join(lines) + "\n"


def render_single_node_latex(project_dir: Path, node: dict) -> str:
    md_path = project_dir / node["path"]
    content = md_path.read_text(encoding="utf-8").strip()
    body = pandoc_markdown_to_latex(content) if content else ""
    title = latex_escape(node["title"])
    slug = node.get("slug", "")

    if slug == "abstract":
        heading = f"\\section*{{{title}}}\n"
    elif slug in {"figure-legends", "supplementary-materials"}:
        heading = f"\\section*{{{title}}}\n"
    else:
        heading = f"\\section{{{title}}}\n"
    return heading + body


def render_group_node_latex(project_dir: Path, node: dict) -> str:
    title = latex_escape(node["title"])
    parts = [f"\\section*{{{title}}}", ""]
    for child in node.get("children", []):
        child_title = latex_escape(child["title"])
        md_path = project_dir / child["path"]
        content = md_path.read_text(encoding="utf-8").strip()
        body = pandoc_markdown_to_latex(content) if content else ""
        parts.append(f"\\subsection*{{{child_title}}}")
        parts.append(body.rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def generate_latex_inputs(project_dir: Path, cache_dir: Path, meta: dict, manifest: list[dict]) -> None:
    frontmatter_target = cache_dir / "extraTex" / "front" / "frontmatter.tex"
    write_text(frontmatter_target, render_frontmatter_tex(meta))

    for node in manifest:
        tex_target = cache_dir / node["tex_path"]
        if node["kind"] == "single":
            write_text(tex_target, render_single_node_latex(project_dir, node))
        else:
            write_text(tex_target, render_group_node_latex(project_dir, node))


def build_project(project_dir: Path) -> None:
    print(f"Building project: {project_dir}")

    meta_path = project_dir / "references" / "meta.yaml"
    manifest_path = project_dir / "artifacts" / "source" / "manifest.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing metadata file: {meta_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest file: {manifest_path}")

    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    print("Building PDF...")
    cache_dir = project_dir / ".latex-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    generate_latex_inputs(project_dir, cache_dir, meta, manifest_data)

    tex_env = os.environ.copy()
    tex_roots = resolve_tex_search_roots(project_dir)
    if tex_roots:
        tex_env["TEXINPUTS"] = build_texinputs([cache_dir, *tex_roots], tex_env.get("TEXINPUTS", ""))
        print("TeX search roots:")
        print(f"  - {cache_dir}")
        for root in tex_roots:
            print(f"  - {root}")

    xelatex_cmd = [
        resolve_executable("xelatex"),
        "-interaction=nonstopmode",
        "-file-line-error",
        "-synctex=1",
        f"-output-directory={cache_dir}",
        "main.tex",
    ]

    xelatex_run_1 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)
    biber_run = run_best_effort(
        [
            resolve_executable("biber"),
            "--input-directory",
            str(cache_dir),
            "--output-directory",
            str(cache_dir),
            "main",
        ],
        cwd=project_dir,
        env=tex_env,
    )
    xelatex_run_2 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)
    xelatex_run_3 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)

    pdf_source = cache_dir / "main.pdf"
    if not pdf_source.exists():
        compiler_logs = "\n\n".join(
            [
                summarize_process_output("xelatex pass 1", xelatex_run_1),
                summarize_process_output("biber", biber_run),
                summarize_process_output("xelatex pass 2", xelatex_run_2),
                summarize_process_output("xelatex pass 3", xelatex_run_3),
            ]
        )
        raise RuntimeError(
            f"PDF compilation failed. Expected output not found: {pdf_source}\n\n{compiler_logs}"
        )

    for label, result in (
        ("xelatex pass 1", xelatex_run_1),
        ("biber", biber_run),
        ("xelatex pass 2", xelatex_run_2),
        ("xelatex pass 3", xelatex_run_3),
    ):
        if result.returncode != 0:
            print(f"Warning: {label} exited with code {result.returncode}; output PDF was still generated.")

    shutil.copy2(pdf_source, project_dir / "main.pdf")
    print(f"✓ PDF generated: {project_dir / 'main.pdf'}")

    print("Building DOCX...")
    manuscript_md = build_markdown_for_docx(project_dir, meta, manifest_data)
    manuscript_md_path = cache_dir / "main.md"
    write_text(manuscript_md_path, manuscript_md)

    reference_doc = project_dir / "artifacts" / "reference.docx"
    reference_doc_arg = ["--reference-doc", str(reference_doc)] if reference_doc.exists() else []

    csl_path = project_dir / "artifacts" / "manuscript.csl"
    if not csl_path.exists():
        raise FileNotFoundError(f"Missing CSL file: {csl_path}")

    docx_path = project_dir / "main.docx"
    pandoc_cmd = [
        resolve_executable("pandoc"),
        str(manuscript_md_path),
        "-f",
        "markdown+raw_html",
        "--citeproc",
        *reference_doc_arg,
        "--csl",
        str(csl_path),
        "--bibliography",
        str(project_dir / "references" / "refs.bib"),
        "-o",
        str(docx_path),
    ]
    run_cmd(pandoc_cmd, cwd=project_dir)
    print(f"✓ DOCX generated: {docx_path}")

    print("Fixing DOCX spacing...")
    fix_docx_spacing(docx_path)
    print("✓ DOCX spacing fixed")

    soffice = shutil.which("soffice") or next(
        (candidate for candidate in TOOL_CANDIDATES["soffice"] if Path(candidate).exists()),
        None,
    )
    if soffice:
        try:
            with tempfile.TemporaryDirectory(prefix="paper-word-pdf-") as tmp_dir:
                word_pdf_dir = Path(tmp_dir)
                run_cmd(
                    [
                        soffice,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(word_pdf_dir),
                        str(docx_path),
                    ],
                    cwd=project_dir,
                )
                generated_word_pdf = word_pdf_dir / "main.pdf"
                if generated_word_pdf.exists():
                    shutil.copy2(generated_word_pdf, cache_dir / "main.word.pdf")
                    print(f"✓ Word-based PDF generated: {cache_dir / 'main.word.pdf'}")
        except Exception as exc:
            print(f"Note: Could not generate Word-based PDF: {exc}")

    print("\n✓ Build complete!")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build manuscript PDF and DOCX from local sources.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("command", choices=["build"], help="Command to execute")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory. Defaults to the nearest parent containing main.tex or meta.yaml.",
    )
    return parser.parse_args()


def main() -> None:
    configure_windows_stdio_utf8()
    args = parse_args()
    if args.command == "build":
        project_dir = resolve_project_dir(args.project_dir)
        build_project(project_dir)
        return
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
