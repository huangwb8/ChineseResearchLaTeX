#!/usr/bin/env python3
"""
compile_latex_with_bibtex.py - 使用 xelatex + bibtex 编译 LaTeX 为 PDF

工作流（BibTeX + .bst）：
  xelatex -> bibtex -> xelatex -> xelatex
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from config_loader import load_config  # type: ignore
except Exception:
    load_config = None  # 脚本独立运行时允许缺省配置


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_ROOT / "latex-template" / "nature-reviews-template.tex"


def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _find_tex_bin() -> str | None:
    """Find TeX binary directory and return its path.

    Returns:
        Path to TeX bin directory (e.g., /usr/local/texlive/2024/bin/universal-darwin)
        or None if not found.
    """
    # 先尝试使用 which 找到 xelatex 的路径
    xelatex_path = shutil.which("xelatex")
    if xelatex_path:
        xelatex_path = Path(xelatex_path).resolve()
        bin_dir = xelatex_path.parent
        # 验证目录中有 xelatex 可执行文件
        if (bin_dir / "xelatex").exists():
            return str(bin_dir)

    # 如果 which 找不到，尝试常见的 TeX Live 安装路径
    common_paths = [
        "/usr/local/texlive/2024/bin/universal-darwin",
        "/usr/local/texlive/2024/bin/x86_64-darwin",
        "/usr/local/texlive/2024/bin/arm64-darwin",
        "/Library/TeX/Distributions/Programs/texbin",  # MacTeX 实际二进制目录
        "/Library/TeX/texbin",  # MacTeX 符号链接
        "/usr/texbin",  # 旧版 MacTeX
    ]

    for path in common_paths:
        if Path(path).exists() and (Path(path) / "xelatex").exists():
            return path

    return None


def _setup_tex_inputs(work_dir: Path, template_dir: Path) -> dict[str, str]:
    """Setup TEXINPUTS environment variable for LaTeX compilation.

    Strategy:
    - Append template_dir to the beginning of TEXINPUTS (preserve system paths)
    - Same for BSTINPUTS
    - No file copying required.

    Args:
        work_dir: Working directory (for clarity, not directly used)
        template_dir: Directory containing template files (.tex, .bst)

    Returns:
        dict with TEXINPUTS and BSTINPUTS environment variables
    """
    # 跨平台路径分隔符
    separator = ";" if sys.platform == "win32" else ":"

    def _kpathsea_preserve_default(path: str) -> str:
        """Ensure kpathsea preserves the default search path.

        In TeX Live (kpathsea), a trailing path separator means "append the
        system default paths". Without it, setting TEXINPUTS/BSTINPUTS can
        accidentally hide the standard tree (e.g., article.cls).
        """
        path = path or ""
        if not path.endswith(separator):
            path = path + separator
        return path

    # 在现有的 TEXINPUTS 前面追加 template_dir
    # 格式：template_dir:系统默认
    current_texinputs = _kpathsea_preserve_default(os.environ.get("TEXINPUTS", ""))
    texinputs = f"{template_dir}{separator}{current_texinputs}"

    # 在现有的 BSTINPUTS 前面追加 template_dir
    current_bstinputs = _kpathsea_preserve_default(os.environ.get("BSTINPUTS", ""))
    bstinputs = f"{template_dir}{separator}{current_bstinputs}"

    return {"TEXINPUTS": texinputs, "BSTINPUTS": bstinputs}


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run command with optional environment variables.

    For TeX commands (xelatex/bibtex), we use shell=True to preserve
    all TeX environment variables while still being able to set TEXINPUTS/BSTINPUTS.
    """
    # 检查是否是 TeX 命令（在路径转换之前）
    is_tex_cmd = cmd and cmd[0] in ("xelatex", "bibtex")

    # 使用绝对路径调用 xelatex/bibtex，避免依赖 PATH
    if is_tex_cmd:
        tex_bin = _find_tex_bin()
        if tex_bin:
            cmd = [str(Path(tex_bin) / cmd[0])] + cmd[1:]

    # 对于 TeX 命令，使用 shell=True 来确保环境变量正确传递
    if is_tex_cmd and env:
        # 构建带环境变量的 shell 命令
        # Use shlex.quote to avoid breaking when paths contain spaces/single quotes.
        env_strs = [f"{k}={shlex.quote(v)}" for k, v in env.items()]
        cmd_str = " ".join(env_strs) + " " + " ".join(shlex.quote(c) for c in cmd)
        proc = subprocess.run(cmd_str, cwd=cwd, text=True, capture_output=True, shell=True)
    else:
        # 非 TeX 命令或无环境变量，直接调用
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=merged_env)

    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  cwd: {cwd}\n"
            f"  stdout:\n{proc.stdout}\n"
            f"  stderr:\n{proc.stderr}\n"
        )


def _ensure_bibliographystyle(tex_file: Path, default_style: str | None) -> None:
    """Ensure the tex contains a \\bibliographystyle line; if missing, inject default before \\bibliography."""
    if not default_style:
        return

    text = tex_file.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\\bibliographystyle\{[^}]+\}", text):
        return

    style_line = f"\\bibliographystyle{{{default_style}}}\n"
    m = re.search(r"\\bibliography\{", text)
    if m:
        text = text[: m.start()] + style_line + text[m.start() :]
    else:
        text = text.rstrip() + "\n\n" + style_line
    tex_file.write_text(text, encoding="utf-8")


def _verify_bst_in_template(tex_file: Path) -> list[str]:
    """Verify that required .bst files exist in the skill's latex-template directory.

    Strategy: parse \\bibliographystyle{...}, and verify the .bst file exists
    in the template dir (to be resolved via BSTINPUTS). Does NOT copy files.

    Returns:
        List of verified .bst file paths (for logging/debugging)

    Raises:
        FileNotFoundError: if required .bst file not found in template directory
    """
    template_dir = SKILL_ROOT / "latex-template"
    text = tex_file.read_text(encoding="utf-8", errors="replace")
    styles = re.findall(r"\\bibliographystyle\{([^}]+)\}", text)
    verified: list[str] = []

    for style in styles:
        if "/" in style or "\\" in style:
            continue  # Skip if style includes a path
        bst_name = f"{style}.bst"
        source = template_dir / bst_name
        if source.exists():
            verified.append(str(source))
        else:
            raise FileNotFoundError(
                f"❌ .bst 文件未找到：{bst_name}\n"
                f"   模板目录：{template_dir}\n"
                f"   请确认 systematic-literature-review/latex-template/ 目录包含该文件。"
            )
    return verified


def _ensure_template(tex_file: Path, configured_template: Path | None) -> Path | None:
    """Ensure the LaTeX template exists; copy from skill bundle if relative path is missing."""
    tex_dir = tex_file.parent

    candidates: list[Path] = []
    target: Path | None = None

    if configured_template:
        if configured_template.is_absolute():
            target = configured_template
            candidates.append(configured_template)
        else:
            target = tex_dir / configured_template
            candidates.append(tex_dir / configured_template)
            candidates.append(SKILL_ROOT / configured_template)
    # 默认回退模板
    candidates.append(DEFAULT_TEMPLATE)
    if target is None and DEFAULT_TEMPLATE.exists():
        target = tex_dir / DEFAULT_TEMPLATE.name
    if target and target.is_absolute() and not target.exists() and DEFAULT_TEMPLATE.exists():
        # 绝对路径缺失时退化为工作目录下的默认模板
        target = tex_dir / DEFAULT_TEMPLATE.name

    for cand in candidates:
        if not cand:
            continue
        if cand.exists():
            if target and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(cand.read_bytes())
                print(f"  ✓ 模板已同步到工作目录: {target}", file=sys.stderr)
            return target if target else cand

    if target:
        print(f"⚠️ 模板未找到，已尝试路径: {candidates}", file=sys.stderr)
    return target


def compile_pdf(tex_file: Path, output_pdf: Path | None, keep_aux: bool, template_path: Path | None = None) -> Path:
    tex_file = tex_file.resolve()
    if not tex_file.exists():
        raise FileNotFoundError(f"TeX file not found: {tex_file}")

    if not _check_tool("xelatex"):
        raise RuntimeError("xelatex not found (required). Please install TeX Live / MacTeX / MiKTeX.")
    if not _check_tool("bibtex"):
        raise RuntimeError("bibtex not found (required for .bst workflow). Please install a TeX distribution with bibtex.")

    work_dir = tex_file.parent

    default_style = "gbt7714-nsfc"
    if load_config:
        try:
            cfg = load_config()
            latex_cfg = cfg.get("latex") if isinstance(cfg, dict) else {}
            if isinstance(latex_cfg, dict):
                ds = latex_cfg.get("bibliographystyle")
                if isinstance(ds, str) and ds.strip():
                    default_style = ds.strip()
        except Exception:
            default_style = "gbt7714-nsfc"

    _ensure_bibliographystyle(tex_file, default_style)

    # 验证 .bst 文件存在于模板目录（v3.6 优化：不再复制到工作目录）
    verified_bsts = _verify_bst_in_template(tex_file)
    if verified_bsts:
        print(f"  ✓ 已验证 .bst 文件：{', '.join([Path(p).name for p in verified_bsts])}", file=sys.stderr)

    # 设置环境变量引用模板目录（v3.5 优化：不再复制模板文件）
    template_dir = SKILL_ROOT / "latex-template"
    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    env = _setup_tex_inputs(work_dir, template_dir)
    print(f"  模板目录: {template_dir}", file=sys.stderr)
    print(f"  TEXINPUTS: {env['TEXINPUTS']}", file=sys.stderr)
    print(f"  BSTINPUTS: {env['BSTINPUTS']}", file=sys.stderr)

    base = tex_file.stem

    try:
        # 1) xelatex
        _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_file.name], cwd=work_dir, env=env)
        # 2) bibtex
        _run(["bibtex", base], cwd=work_dir, env=env)
        # 3) xelatex
        _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_file.name], cwd=work_dir, env=env)
        # 4) xelatex
        _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_file.name], cwd=work_dir, env=env)

        produced_pdf = work_dir / f"{base}.pdf"
        if not produced_pdf.exists():
            raise RuntimeError(f"PDF not produced: {produced_pdf}")

        final_pdf = produced_pdf
        if output_pdf is not None:
            output_pdf = output_pdf.resolve()
            if output_pdf != produced_pdf:
                output_pdf.parent.mkdir(parents=True, exist_ok=True)
                produced_pdf.replace(output_pdf)
                final_pdf = output_pdf
    finally:
        # 无论编译成功与否，都执行清理（除非 keep_aux=True）
        if not keep_aux:
            # LaTeX 中间文件后缀清单（按包分类）
            aux_suffixes = [
                # 核心中间文件
                ".aux", ".bbl", ".blg", ".log",
                # hyperref 包
                ".out",
                # 目录相关
                ".toc", ".lot", ".lof",
                # 索引相关
                ".idx", ".ind", ".ilg",
                # 交叉引用
                ".synctex.gz", ".synctex",
                # 其他常见中间文件
                ".fls", ".fdb_latexmk", ".auxlock",
                # 某些包的特殊输出（如 .og 可能是某种变体）
                ".og", ".gz",
            ]

            cleaned = []
            for suffix in aux_suffixes:
                p = work_dir / f"{base}{suffix}"
                if p.exists():
                    try:
                        p.unlink()
                        cleaned.append(suffix)
                    except Exception as e:
                        print(f"  ⚠️ 无法删除 {p.name}: {e}", file=sys.stderr)

            if cleaned:
                print(f"  ✓ 已清理中间文件：{', '.join(cleaned)}", file=sys.stderr)

    return final_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile LaTeX to PDF using xelatex+bibtex.")
    parser.add_argument("tex_file", type=Path, help="Input .tex file")
    parser.add_argument("output_pdf", nargs="?", default=None, help="Optional output .pdf path")
    parser.add_argument("--keep-aux", action="store_true", help="Keep auxiliary files")
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Optional LaTeX template path (default: from config.yaml latex.template_path)",
    )
    args = parser.parse_args()

    # 从 config.yaml 读取模板配置（支持 override）
    latex_template = args.template
    if latex_template is None and load_config:
        try:
            cfg = load_config()
            latex_cfg = cfg.get("latex") if isinstance(cfg, dict) else {}
            if isinstance(latex_cfg, dict):
                tp = latex_cfg.get("template_path_override") or latex_cfg.get("template_path")
                if tp:
                    latex_template = Path(tp)
        except Exception:
            latex_template = None

    output_pdf = Path(args.output_pdf) if args.output_pdf else None
    pdf = compile_pdf(args.tex_file, output_pdf, keep_aux=args.keep_aux, template_path=latex_template)
    print(f"✓ PDF generated: {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
