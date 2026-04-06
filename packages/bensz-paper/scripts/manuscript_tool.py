#!/usr/bin/env python3
"""SCI 论文构建工具核心模块（bensz-paper 公共包配套脚本）。

支持 PDF + DOCX 双输出：

PDF 构建流程：
  XeLaTeX → Biber → XeLaTeX → XeLaTeX
  中间文件隔离到 .latex-cache/，最终 PDF 复制到项目根目录。

DOCX 构建流程（多步转换管线）：
  LaTeX → Markdown（pandoc）
    ↓ 先转 Markdown 是为了让 pandoc 的 --citeproc + CSL 处理
      引用格式（如 Nature、Science 等期刊特有格式）。
  Markdown → HTML5+MathML（pandoc --mathml --citeproc）
    ↓ HTML5 中间步骤的目的是让数学公式转为 MathML，
      再由 pandoc 从 HTML 生成 DOCX 时自动转为 OMML（Office MathML），
      这比直接从 Markdown/LaTeX 转 DOCX 的公式兼容性好得多。
  HTML5 → DOCX（pandoc，可选 reference.docx 样式模板）
    ↓ 最后调用 fix_docx_spacing() 修复行距/段间距/缩进，
      使其尽量接近 LaTeX PDF 版式。

外部依赖：
- xelatex：TeX 排版引擎（TeX Live）
- biber：参考文献处理
- pandoc：格式转换核心
- soffice（可选）：LibreOffice 命令行，用于从 DOCX 生成 Word 风格 PDF
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

from fix_docx_spacing import fix_docx_spacing

VERSION = "1.3.6"
DOCX_FRONTMATTER_CENTER_START = "BENSZ_DOCX_FRONTMATTER_CENTER_START"
DOCX_FRONTMATTER_CENTER_END = "BENSZ_DOCX_FRONTMATTER_CENTER_END"
# 用于判定目录是否为项目根的标记文件
PROJECT_ROOT_MARKERS = ("main.tex",)
# 匹配 main.tex 中的 \input{extraTex/...} 引用，用于收集 DOCX 所需的正文片段
EXTRA_TEX_INPUT_PATTERN = re.compile(r"\\input\{(extraTex/[^}]+)\}")
# 匹配 LaTeX 引用命令（supercite/cite/autocite 等）及其花括号内的 citation keys。
# 在 LaTeX→Markdown 转换前，将引用替换为占位符，避免 pandoc 误解析；
# 转换完成后再将占位符还原为 CSL 可识别的 [@key] 格式。
CITATION_PATTERN = re.compile(
    r"\\(supercite|cite|autocite|parencite|textcite|citep|citet)\{([^}]*)\}"
)
# 外部工具的候选路径：当 PATH 中找不到时，按此列表逐一探测。
# 主要覆盖 macOS（TeX Live、Homebrew）和 Linux（TeX Live）的常见安装位置。
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
    """执行外部命令并返回 stdout。命令失败时抛出 subprocess.CalledProcessError。"""
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
    """在 Windows 上将 stdout/stderr 重编码为 UTF-8，避免中文输出乱码。"""
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
    """执行外部命令但不检查返回码。用于 xelatex/biber 等可能产生非零退出码但仍生成有效输出的工具。"""
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def collect_extra_tex_inputs(project_dir: Path) -> list[Path]:
    """从 main.tex 中提取 \\input{extraTex/...} 引用的文件路径列表（按出现顺序）。

    遍历 main.tex 每一行，跳过 TeX 注释后，用正则匹配 \\input{extraTex/xxx}，
    确保引用的文件实际存在。返回相对路径列表，供 DOCX 管线逐文件转换。
    """
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        raise FileNotFoundError(f"Missing main.tex: {main_tex}")

    ordered_inputs: list[Path] = []
    main_tex_text = []
    for line in main_tex.read_text(encoding="utf-8").splitlines():
        comment_index = None
        for index, char in enumerate(line):
            if char == "%" and (index == 0 or line[index - 1] != "\\"):
                comment_index = index
                break
        main_tex_text.append(line if comment_index is None else line[:comment_index])

    for matched_path in EXTRA_TEX_INPUT_PATTERN.findall("\n".join(main_tex_text)):
        rel_path = Path(matched_path)
        if rel_path.suffix != ".tex":
            rel_path = rel_path.with_suffix(".tex")
        source_path = project_dir / rel_path
        if not source_path.exists():
            raise FileNotFoundError(f"Missing extraTex source referenced by main.tex: {source_path}")
        ordered_inputs.append(rel_path)
    return ordered_inputs


def _replace_latex_citations_with_tokens(latex_text: str) -> tuple[str, dict[str, str]]:
    """将 LaTeX 引用命令替换为占位符，返回 (处理后的文本, 占位符映射表)。

    占位符生成规则：
    - 格式为 CITETOKEN{序号}，序号从 0001 开始零填充为 4 位。
    - 每个 \\cite{key1,key2} 被替换为一个占位符。
    - 映射表值为 CSL 格式的引用标记 [@key1]; [@key2]，
      在 pandoc 转换完成后再替换回去，使 --citeproc 能正确处理。

    这样做是因为 pandoc 直接处理 LaTeX 引用时容易与数学模式等语法冲突，
    先替换为纯文本占位符可以避免干扰。
    """
    placeholder_map: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        token = f"CITETOKEN{len(placeholder_map) + 1:04d}"
        keys = [part.strip() for part in match.group(2).split(",") if part.strip()]
        placeholder_map[token] = "[" + "; ".join(f"@{key}" for key in keys) + "]"
        return token

    return CITATION_PATTERN.sub(repl, latex_text), placeholder_map


_SUP_TAG_RE = re.compile(r"<sup>(.*?)</sup>", re.DOTALL)


def _convert_sup_tags_to_superscript(md_text: str) -> str:
    """将 HTML <sup> 标签转换为 pandoc 原生上标语法 ^text^。

    pandoc 从 LaTeX 转 Markdown 时，上标内容可能被输出为 <sup>...</sup>，
    需要转回 pandoc 原生语法才能在后续 HTML5→DOCX 步骤中正确处理。
    """

    def _replace_sup(match: re.Match[str]) -> str:
        content = match.group(1)
        return f"^{content}^"

    return _SUP_TAG_RE.sub(_replace_sup, md_text)


def _normalize_frontmatter_markdown(md_text: str) -> str:
    """清理 frontmatter.tex 转出的 Markdown，并为作者居中块植入显式 DOCX 标记。

    现有 Pandoc 链路会把 LaTeX 的 center 环境保留成 fenced div（::: center）
    或旧式 HTML div，但 HTML→DOCX 这一步不会自动把容器映射成 Word 段落居中。
    因此这里将 center 环境中的首段提升为 H1 标题，并把其余居中段落包裹为显式
    标记，供 fix_docx_spacing() 在最终 DOCX 中精准写入段落级居中属性。
    """

    def _split_markdown_paragraphs(lines: list[str]) -> list[str]:
        paragraphs: list[str] = []
        current: list[str] = []

        for line in lines:
            if line.strip():
                current.append(line.rstrip())
                continue
            if current:
                paragraphs.append("\n".join(current).strip())
                current = []
        if current:
            paragraphs.append("\n".join(current).strip())
        return paragraphs

    normalized_blocks: list[str] = []
    buffered_lines: list[str] = []
    title_promoted = False
    source_lines = md_text.splitlines()
    index = 0

    def _emit_regular_lines(lines: list[str]) -> None:
        nonlocal title_promoted
        for paragraph in _split_markdown_paragraphs(lines):
            collapsed = " ".join(paragraph.split())
            if (
                not title_promoted
                and collapsed.startswith("**")
                and collapsed.endswith("**")
                and len(collapsed) > 4
            ):
                normalized_blocks.append("# " + collapsed[2:-2].strip())
                title_promoted = True
            else:
                normalized_blocks.append(paragraph)

    def _emit_center_block(lines: list[str]) -> None:
        nonlocal title_promoted
        paragraphs = _split_markdown_paragraphs(lines)
        if not paragraphs:
            return

        first_paragraph = " ".join(paragraphs[0].split())
        if (
            not title_promoted
            and first_paragraph.startswith("**")
            and first_paragraph.endswith("**")
            and len(first_paragraph) > 4
        ):
            normalized_blocks.append("# " + first_paragraph[2:-2].strip())
            title_promoted = True
            remaining_paragraphs = paragraphs[1:]
        else:
            normalized_blocks.append(paragraphs[0])
            remaining_paragraphs = paragraphs[1:]

        if remaining_paragraphs:
            normalized_blocks.append(DOCX_FRONTMATTER_CENTER_START)
            normalized_blocks.extend(remaining_paragraphs)
            normalized_blocks.append(DOCX_FRONTMATTER_CENTER_END)

    while index < len(source_lines):
        stripped = source_lines[index].strip()
        if stripped in {"::: center", "<div class=\"center\">"}:
            if buffered_lines:
                _emit_regular_lines(buffered_lines)
                buffered_lines = []

            closing_marker = ":::" if stripped.startswith(":::") else "</div>"
            center_lines: list[str] = []
            index += 1
            while index < len(source_lines) and source_lines[index].strip() != closing_marker:
                center_lines.append(source_lines[index])
                index += 1
            _emit_center_block(center_lines)
            index += 1
            continue

        if stripped in {":::", "</div>"}:
            index += 1
            continue

        buffered_lines.append(source_lines[index])
        index += 1

    if buffered_lines:
        _emit_regular_lines(buffered_lines)

    return "\n\n".join(block for block in normalized_blocks if block.strip()).strip()


def pandoc_latex_to_markdown(latex_text: str) -> str:
    """将 LaTeX 源码转为 Markdown，保留数学公式和引用占位符。

    为何先转 Markdown 而不是直接转 DOCX：
    - Markdown 作为中间格式，让 pandoc 的 --citeproc 和 --csl 能正确处理
      各种期刊的引用格式（Nature、Science 等 CSL 样式表）。
    - 使用 pandoc 原生 Markdown 方言（而非 GFM），使 TeX 数学公式保持
      $...$ / $$...$$ 形式，不会被 pandoc 过早渲染为其他格式。

    流程：
    1. 将 LaTeX 引用命令替换为占位符（避免 pandoc 误解析）。
    2. pandoc latex → markdown+raw_html。
    3. 将占位符还原为 [@key] 格式。
    4. 将 <sup> 标签转为 pandoc 上标语法。
    """
    prepared_text, placeholder_map = _replace_latex_citations_with_tokens(latex_text)
    # Use Pandoc's native markdown dialect instead of GFM so TeX math stays
    # as `$...$` / `$$...$$` and can be promoted into MathML/OMML later.
    markdown = run_cmd(
        [
            resolve_executable("pandoc"),
            "-f",
            "latex",
            "-t",
            "markdown+raw_html",
        ],
        input_text=prepared_text,
    ).strip()
    for token, replacement in placeholder_map.items():
        markdown = markdown.replace(token, replacement)
    markdown = _convert_sup_tags_to_superscript(markdown)
    return markdown.strip() + "\n" if markdown.strip() else ""


def build_docx_from_markdown(
    manuscript_md: str,
    docx_path: Path,
    csl_path: Path,
    bibliography_path: Path,
    reference_doc: Path | None = None,
) -> None:
    """从 Markdown 生成 DOCX，采用 Markdown→HTML5+MathML→DOCX 两步管线。

    为何不直接 Markdown→DOCX：
    - pandoc 的 DOCX writer 在当前工具链中不能可靠地将 TeX 数学公式
      提升为 OMML（Office MathML）。
    - 通过 HTML5 + MathML 中间步骤，pandoc 先将公式转为 MathML，
      再从 HTML 输入读取时自动将 MathML 转为 DOCX 原生 OMML 公式，
      转换可靠度显著提高。

    参数：
        manuscript_md: 合并后的 Markdown 正文（含 [@key] 引用标记）
        docx_path: 输出 DOCX 文件路径
        csl_path: CSL 引用样式表路径（如 nature.csl）
        bibliography_path: BibTeX 参考文献数据库路径
        reference_doc: 可选的 Word 参考模板（reference.docx），用于继承样式
    """
    pandoc = resolve_executable("pandoc")
    with tempfile.TemporaryDirectory(prefix="paper-docx-html-") as tmp_dir:
        html_path = Path(tmp_dir) / "manuscript.html"
        # Pandoc's DOCX writer in our current toolchain does not reliably
        # promote TeX math from markdown into OMML. Converting through
        # HTML5 + MathML yields native Word equations while preserving CSL output.
        html_cmd = [
            pandoc,
            "-",
            "-f",
            "markdown+raw_html+superscript",
            "-t",
            "html5",
            "--mathml",
            "--citeproc",
            "--csl",
            str(csl_path),
            "--bibliography",
            str(bibliography_path),
            "-o",
            str(html_path),
        ]
        run_cmd(html_cmd, input_text=manuscript_md)

        docx_cmd = [pandoc, str(html_path), "-f", "html"]
        if reference_doc is not None and reference_doc.exists():
            docx_cmd.extend(["--reference-doc", str(reference_doc)])
        docx_cmd.extend(["-o", str(docx_path)])
        run_cmd(docx_cmd)


def is_project_root(path: Path) -> bool:
    """判断目录是否为项目根（依据是否存在 main.tex 标记文件）。"""
    return any((path / marker).exists() for marker in PROJECT_ROOT_MARKERS)


def find_project_root(start: Path | None = None) -> Path:
    """从给定路径向上遍历，找到包含 main.tex 的项目根目录。"""
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "Cannot find project root. Run inside the manuscript project tree or "
        "pass --project-dir explicitly."
    )


def resolve_project_dir(project_dir: Path | None) -> Path:
    """从 CLI 参数或当前工作目录解析出有效的项目根目录。"""
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
    """查找外部工具的可执行路径。优先使用 PATH（shutil.which），再按 TOOL_CANDIDATES 逐一探测。"""
    resolved = shutil.which(name)
    if resolved:
        return resolved
    for candidate in TOOL_CANDIDATES.get(name, ()):
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"Required executable not found: {name}")


def build_texinputs(prefixes: list[Path], existing: str) -> str:
    """构建 TEXINPUTS 环境变量值，将指定目录前缀和已有值拼接为 TeX 搜索路径。"""
    normalized = [f"{path.resolve()}//" for path in prefixes]
    normalized.append("")
    if existing:
        normalized.append(existing)
    return os.pathsep.join(normalized)


def resolve_tex_search_roots(project_dir: Path) -> list[Path]:
    """解析 TeX 搜索路径根目录列表，用于设置 TEXINPUTS 环境变量。

    按优先级探测三个来源：
    1. 项目内 texmf/tex/latex（项目本地 texmf 树）
    2. bensz-paper 公共包源码目录（包含 bml-core.sty 等）
    3. bensz-fonts 字体包目录（包含 bensz-fonts.sty）
    """
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
    """将子进程的 stdout/stderr 合并后取最后 20 行，用于构建编译失败时的诊断摘要。"""
    lines = [line for line in (result.stdout + "\n" + result.stderr).splitlines() if line.strip()]
    tail = "\n".join(lines[-20:]) if lines else "(no output)"
    return f"[{label}] exit={result.returncode}\n{tail}"


def remove_legacy_docx_intermediates(cache_dir: Path) -> None:
    """清理旧版构建流程遗留的 DOCX 中间文件（main.md 和 extraTex/ 目录）。"""
    legacy_markdown = cache_dir / "main.md"
    legacy_extra_tex = cache_dir / "extraTex"

    if legacy_markdown.exists():
        legacy_markdown.unlink()
    if legacy_extra_tex.exists():
        shutil.rmtree(legacy_extra_tex)


def build_markdown_for_docx(project_dir: Path) -> str:
    """将项目 extraTex/ 下所有 LaTeX 正文片段转为 Markdown 并合并为单一文档。

    流程：
    1. 从 main.tex 收集 \\input{extraTex/...} 的有序文件列表。
    2. 逐文件调用 pandoc_latex_to_markdown() 转为 Markdown。
    3. 对 frontmatter.tex 特殊处理（去除 div 标签、提升标题）。
    4. 用空行拼接所有片段，返回完整的 Markdown 正文。
    """
    parts: list[str] = []

    for rel_path in collect_extra_tex_inputs(project_dir):
        source_text = (project_dir / rel_path).read_text(encoding="utf-8").strip()
        if not source_text:
            continue
        markdown = pandoc_latex_to_markdown(source_text).strip()
        if not markdown:
            continue
        if rel_path.name == "frontmatter.tex":
            markdown = _normalize_frontmatter_markdown(markdown)
        parts.append(markdown)

    if not parts:
        raise RuntimeError(f"No DOCX source fragments found under {project_dir / 'extraTex'}")

    return "\n\n".join(parts).rstrip() + "\n"


def build_project(project_dir: Path) -> None:
    """完整的 PDF + DOCX 构建入口。

    构建流程：
    1. PDF 构建：xelatex → biber → xelatex → xelatex，中间文件隔离到 .latex-cache/。
    2. DOCX 构建：
       a. 收集 extraTex/ 下所有正文片段，转为 Markdown。
       b. 通过 HTML5+MathML 中间步骤生成 DOCX（含 CSL 引用处理和 OMML 公式）。
       c. 调用 fix_docx_spacing() 修复行距/段间距/缩进。
    3. Word 风格 PDF（可选）：如果检测到 soffice，从 DOCX 生成一份 Word 排版 PDF
       保存到 .latex-cache/main.word.pdf。
    """
    print(f"Building project: {project_dir}")

    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        raise FileNotFoundError(f"Missing main.tex: {main_tex}")

    print("Building PDF...")
    cache_dir = project_dir / ".latex-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    remove_legacy_docx_intermediates(cache_dir)

    tex_env = os.environ.copy()
    tex_roots = resolve_tex_search_roots(project_dir)
    if tex_roots:
        tex_env["TEXINPUTS"] = build_texinputs(tex_roots, tex_env.get("TEXINPUTS", ""))
        print("TeX search roots:")
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
    manuscript_md = build_markdown_for_docx(project_dir)

    reference_doc = project_dir / "artifacts" / "reference.docx"

    csl_path = project_dir / "artifacts" / "manuscript.csl"
    if not csl_path.exists():
        raise FileNotFoundError(f"Missing CSL file: {csl_path}")

    docx_path = project_dir / "main.docx"
    build_docx_from_markdown(
        manuscript_md=manuscript_md,
        docx_path=docx_path,
        csl_path=csl_path,
        bibliography_path=project_dir / "references" / "refs.bib",
        reference_doc=reference_doc,
    )
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
    """解析命令行参数。支持 build 子命令和 --project-dir 选项。"""
    parser = argparse.ArgumentParser(description="Build manuscript PDF and DOCX from local sources.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("command", choices=["build"], help="Command to execute")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory. Defaults to the nearest parent containing main.tex.",
    )
    return parser.parse_args()


def main() -> None:
    """命令行入口：解析参数后执行 build 子命令。"""
    configure_windows_stdio_utf8()
    args = parse_args()
    if args.command == "build":
        project_dir = resolve_project_dir(args.project_dir)
        build_project(project_dir)
        return
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
