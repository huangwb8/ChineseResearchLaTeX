#!/usr/bin/env python3
"""
convert_latex_to_word.py - 将 LaTeX（.tex + .bib）导出为 Word（.docx）

说明：
  - 输入为 LaTeX 源码（BibTeX/bst 或 biblatex 均可）
  - Word 导出使用 pandoc；对复杂宏包/自定义命令支持有限
  - 该脚本的目标是“可交付的可编辑版本”，不保证 100% 还原排版
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from config_loader import load_config  # type: ignore
except Exception:
    load_config = None  # 允许脱离 pipeline_runner 独立使用


def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


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
                shift = word_cfg.get("heading_level_shift")
                if isinstance(shift, int):
                    pandoc_opts.append(f"--shift-heading-level-by={shift}")
                if word_cfg.get("include_toc"):
                    pandoc_opts.append("--toc")
                if word_cfg.get("include_numbering"):
                    pandoc_opts.append("--number-sections")
        except Exception:
            pandoc_opts = []

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
    ] + pandoc_opts

    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=tex_file.parent)
    if proc.returncode != 0:
        raise RuntimeError(
            "pandoc failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stdout:\n{proc.stdout}\n"
            f"  stderr:\n{proc.stderr}\n"
        )

    if not output_docx.exists():
        raise RuntimeError(f"docx not produced: {output_docx}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert LaTeX (.tex + .bib) to Word (.docx) via pandoc.")
    parser.add_argument("tex_file", type=Path, help="Input .tex file")
    parser.add_argument("bib_file", type=Path, help="Input .bib file (BibTeX)")
    parser.add_argument("output_docx", type=Path, help="Output .docx file")
    args = parser.parse_args()

    convert(args.tex_file, args.bib_file, args.output_docx)
    print(f"✓ Word generated: {args.output_docx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
