#!/usr/bin/env python3
"""
convert_latex_to_word.py - 将 LaTeX（.tex + .bib）导出为 Word（.docx）

说明：
  - 输入为 LaTeX 源码（BibTeX/bst 或 biblatex 均可）
  - Word 导出使用 pandoc；对复杂宏包/自定义命令支持有限
  - 该脚本的目标是“可交付的可编辑版本”，不保证 100% 还原排版
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from path_scope import get_effective_scope_root, resolve_and_check

try:
    from config_loader import load_config  # type: ignore
except Exception:
    load_config = None  # 允许脱离 pipeline_runner 独立使用


def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _prepare_reference(reference: Path, destination: Path) -> Path:
    """只替换默认宋体的已知本机回退；用户的其它字体保持原样。"""
    if not _check_tool("fc-list"):
        return reference
    proc = subprocess.run(["fc-list", "--format=%{family}\n"], text=True, capture_output=True)
    families = {name.strip() for line in proc.stdout.splitlines() for name in line.split(",")}
    # macOS 的 LibreOffice 对 Songti SC 英文别名可能误替换，优先其本地化 family 名。
    chosen = next((font for font in ("SimSun", "宋体-简", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC")
                   if font in families), None)
    if proc.returncode or chosen in (None, "SimSun"):
        return reference
    with zipfile.ZipFile(reference) as original, zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as updated:
        for item in original.infolist():
            content = original.read(item.filename)
            if item.filename == "word/styles.xml":
                content = content.replace(b'w:eastAsia="SimSun"', f'w:eastAsia="{chosen}"'.encode())
            updated.writestr(item, content)
    print(f"Word 中文字体：{chosen}（本机缺少 SimSun 时的宋体回退）", file=sys.stderr)
    return destination


def convert(tex_file: Path, bib_file: Path, output_docx: Path) -> None:
    tex_file = tex_file.resolve()
    bib_file = bib_file.resolve()
    output_docx = output_docx.resolve()

    if not tex_file.exists():
        raise FileNotFoundError(f"TeX file not found: {tex_file}")
    if not bib_file.exists():
        raise FileNotFoundError(f"Bib file not found: {bib_file}")
    if not _check_tool("pandoc"):
        raise RuntimeError("pandoc not found (required). Please install pandoc: https://pandoc.org/installing.html")

    output_docx.parent.mkdir(parents=True, exist_ok=True)

    # 读取配置：latex.pandoc_options + word.* 导出选项
    pandoc_opts = []
    reference = None
    if load_config:
        try:
            cfg = load_config()
            latex_cfg = cfg.get("latex") if isinstance(cfg, dict) else {}
            if isinstance(latex_cfg, dict):
                extra = latex_cfg.get("pandoc_options") or []
                if isinstance(extra, list):
                    pandoc_opts.extend([str(x) for x in extra if str(x).strip()])
            word_cfg = cfg.get("word") if isinstance(cfg, dict) else {}
            if isinstance(word_cfg, dict):
                csl = word_cfg.get("csl_path", "references/latex-template/review-numeric.csl")
                csl_path = Path(__file__).resolve().parents[1] / csl
                if not csl_path.is_file():
                    raise FileNotFoundError(f"Word 引文样式缺失：{csl_path.name}")
                pandoc_opts.append(f"--csl={csl_path}")
                reference = Path(__file__).resolve().parents[1] / word_cfg.get("reference_docx", "references/latex-template/review-reference.docx")
                if not reference.is_file():
                    raise FileNotFoundError("Word 参考样式文件缺失")
                shift = word_cfg.get("heading_level_shift")
                if isinstance(shift, int):
                    pandoc_opts.append(f"--shift-heading-level-by={shift}")
                if word_cfg.get("include_toc"):
                    pandoc_opts.append("--toc")
                if word_cfg.get("include_numbering"):
                    pandoc_opts.append("--number-sections")
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Word 配置无效：{exc}") from exc

    # pandoc 对 LaTeX 引用的解析能力有限：
    # - 对 biblatex 命令通常能保留为占位或转为文本
    # - 加 --citeproc + --bibliography 可在部分场景下生成参考文献
    cmd = [
        "pandoc",
        str(tex_file),
        "-o",
        str(output_docx),
        "--from=latex",
        "--standalone",
        "--citeproc",
        f"--bibliography={bib_file}",
        f"--lua-filter={Path(__file__).resolve().parents[1] / 'references/latex-template/review-word.lua'}",
    ] + pandoc_opts

    # 只按文稿实际字符选择中文标签，不把所有主题固定成中文。
    if re.search(r"[\u4e00-\u9fff]", tex_file.read_text(encoding="utf-8")):
        cmd += ["--metadata=lang:zh-CN", "--metadata=reference-section-title:参考文献"]

    with tempfile.TemporaryDirectory(prefix=".word-style-", dir=output_docx.parent) as temporary:
        if reference is not None:
            prepared = _prepare_reference(reference, Path(temporary) / "reference.docx")
            cmd.append(f"--reference-doc={prepared}")
        proc = subprocess.run(cmd, text=True, capture_output=True, cwd=tex_file.parent)
    if proc.returncode != 0:
        raise RuntimeError(
            "pandoc failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stdout:\n{proc.stdout}\n"
            f"  stderr:\n{proc.stderr}\n"
        )

    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
        if re.search(r"(?:citation .* not found|Could not (?:find|fetch|convert)|could not (?:find|fetch|convert))", proc.stderr):
            raise RuntimeError("Word 导出有引文、图片或内容转换缺失；请处理 Pandoc 警告")

    if not output_docx.exists():
        raise RuntimeError(f"docx not produced: {output_docx}")
    with zipfile.ZipFile(output_docx) as archive:
        if not archive.read("word/document.xml"):
            raise RuntimeError("Word 正文为空")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert LaTeX (.tex + .bib) to Word (.docx) via pandoc.")
    parser.add_argument("tex_file", type=Path, help="Input .tex file")
    parser.add_argument("bib_file", type=Path, help="Input .bib file (BibTeX)")
    parser.add_argument("output_docx", type=Path, help="Output .docx file")
    parser.add_argument(
        "--scope-root",
        type=Path,
        default=None,
        help="工作目录隔离根目录（可选；默认从环境变量 SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT 读取）",
    )
    args = parser.parse_args()

    scope_root = get_effective_scope_root(args.scope_root)
    if scope_root is not None:
        args.tex_file = resolve_and_check(args.tex_file, scope_root, must_exist=True)
        args.bib_file = resolve_and_check(args.bib_file, scope_root, must_exist=True)
        args.output_docx = resolve_and_check(args.output_docx, scope_root, must_exist=False)

    convert(args.tex_file, args.bib_file, args.output_docx)
    print(f"✓ Word generated: {args.output_docx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
