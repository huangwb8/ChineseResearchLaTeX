#!/usr/bin/env python3
"""毕业论文项目统一构建工具。

支持功能：
- **PDF 构建**：自动执行 xelatex + bibtex/biber + xelatex x2 编译链路，
  中间文件隔离到 ``.latex-cache/`` 目录，最终 PDF 输出到项目根目录。
- **缓存清理**：一键清除 ``.latex-cache/`` 及根目录下的 LaTeX 中间文件。
- **像素级 PDF 比较**：将待测 PDF 与基线 PDF 逐页光栅化后做像素差异比对，
  适用于模板迁移后的版式回归验收。自动生成 diff 图片和 JSON 比较报告。

典型用法::

    # 构建论文 PDF
    python thesis_project_tool.py build --project-dir projects/thesis-smu-master

    # 清理编译缓存
    python thesis_project_tool.py clean --project-dir projects/thesis-smu-master

    # 与基线 PDF 做像素级比较验收
    python thesis_project_tool.py compare \\
        --project-dir projects/thesis-smu-master \\
        --baseline-pdf tests/baseline.pdf \\
        --dpi 144
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# bensz-thesis 公共包源码根目录（即 packages/bensz-thesis/）
PACKAGE_DIR = Path(__file__).resolve().parents[1]
# bensz-fonts 共享字体包目录，构建时注入 TEXINPUTS 以便 xelatex 找到字体文件
FONTS_PACKAGE_DIR = PACKAGE_DIR.parent / "bensz-fonts"
# LaTeX 编译中间文件的隔离目录名
CACHE_DIRNAME = ".latex-cache"
# 用于检测 main.tex 顶部的直通 PDF 指令：
#   % BENSZ_PASSTHROUGH_PDF: /path/to/prebuilt.pdf
# 匹配成功后直接复制指定 PDF，跳过完整的 xelatex 编译流程
PDF_PASSTHROUGH_PATTERN = re.compile(r"^\s*%\s*BENSZ_PASSTHROUGH_PDF:\s*(.+?)\s*$")
# 编译完成后需要从项目根目录清理的中间文件扩展名
ROOT_ARTIFACT_PATTERNS = (
    "*.aux",
    "*.log",
    "*.out",
    "*.toc",
    "*.lof",
    "*.lot",
    "*.bbl",
    "*.blg",
    "*.fls",
    "*.fdb_latexmk",
    "*.bcf",
    "*.run.xml",
    "*.nav",
    "*.snm",
    "*.vrb",
    "*.synctex.gz",
    "*.synctex(busy)",
    "*.dvi",
    "*.xdv",
)
# 各工具在 macOS / Linux 常见安装路径的候选列表，用于 PATH 中找不到时的回退定位
TOOL_CANDIDATES = {
    "xelatex": (
        "/Library/TeX/texbin/xelatex",
        "/usr/local/texlive/2024/bin/universal-darwin/xelatex",
        "/usr/local/texlive/2024/bin/x86_64-linux/xelatex",
    ),
    "bibtex": (
        "/Library/TeX/texbin/bibtex",
        "/usr/local/texlive/2024/bin/universal-darwin/bibtex",
        "/usr/local/texlive/2024/bin/x86_64-linux/bibtex",
    ),
    "biber": (
        "/Library/TeX/texbin/biber",
        "/usr/local/texlive/2024/bin/universal-darwin/biber",
        "/usr/local/texlive/2024/bin/x86_64-linux/biber",
    ),
    "pdftoppm": (
        "/opt/homebrew/bin/pdftoppm",
        "/usr/local/bin/pdftoppm",
    ),
}


class BuildError(RuntimeError):
    """PDF 渲染过程中出现的致命错误（编译失败、缺失工具等）。"""
    pass


def configure_windows_stdio_utf8() -> None:
    """在 Windows 平台上将 stdout/stderr 重配置为 UTF-8 编码，避免中文乱码。"""
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def is_project_root(path: Path) -> bool:
    """判断给定路径是否为有效的 thesis 项目根目录（需包含 main.tex 和 extraTex/）。"""
    return (path / "main.tex").exists() and (path / "extraTex").exists()


def find_project_root(start: Path | None = None) -> Path:
    """从指定路径向上逐级搜索，定位包含 main.tex 和 extraTex/ 的项目根目录。"""
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "无法定位 thesis 项目根目录。请在项目目录内运行，或使用 --project-dir 显式指定。"
    )


def resolve_project_dir(project_dir: Path | None) -> Path:
    """解析并验证项目目录路径，支持显式指定或自动搜索。"""
    if project_dir is None:
        return find_project_root()
    candidate = project_dir.expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"项目目录不存在：{candidate}")
    if candidate.is_file():
        candidate = candidate.parent
    if is_project_root(candidate):
        return candidate
    return find_project_root(candidate)


def resolve_tex_file(project_dir: Path, tex_file: str) -> Path:
    """解析并验证主 TeX 文件路径，要求文件存在于项目根目录下。"""
    candidate = (project_dir / tex_file).resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"TeX 主文件不存在：{candidate}")
    if candidate.parent != project_dir:
        raise BuildError("当前渲染器仅支持项目根目录下的主 TeX 文件。")
    return candidate


def detect_passthrough_pdf(tex_path: Path, project_dir: Path) -> Path | None:
    """检测 main.tex 顶部的 BENSZ_PASSTHROUGH_PDF 直通指令。

    当 main.tex 首部 20 行内存在形如 ``% BENSZ_PASSTHROUGH_PDF: path/to/file.pdf``
    的注释时，直接复制该 PDF 作为构建输出，跳过完整的 xelatex 编译流程。
    此机制主要用于 CI 环境中复用预编译好的 PDF，避免重复编译或缺少字体时出错。

    Args:
        tex_path: main.tex 的完整路径。
        project_dir: 项目根目录，用于解析相对 PDF 路径。

    Returns:
        直通 PDF 的绝对路径；若未检测到指令则返回 None。
    """
    try:
        lines = tex_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return None
    for line in lines[:20]:
        match = PDF_PASSTHROUGH_PATTERN.match(line)
        if not match:
            continue
        candidate = (project_dir / match.group(1).strip()).expanduser().resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"直通 PDF 不存在：{candidate}")
        return candidate
    return None


def resolve_executable(name: str) -> str:
    """查找可执行文件路径，优先使用 PATH，回退到 TOOL_CANDIDATES 中的候选路径。"""
    resolved = shutil.which(name)
    if resolved:
        return resolved
    for candidate in TOOL_CANDIDATES.get(name, ()):
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"未找到可执行文件：{name}")


def build_texinputs(prefixes: list[Path], existing: str) -> str:
    """构建 TEXINPUTS 环境变量值，将公共包和字体包目录注入 LaTeX 搜索路径。"""
    normalized = [f"{path.resolve()}//" for path in prefixes]
    normalized.append("")
    if existing:
        normalized.append(existing)
    return os.pathsep.join(normalized)


def clean_root_artifacts(project_dir: Path, tex_stem: str) -> None:
    """清理项目根目录下匹配 ROOT_ARTIFACT_PATTERNS 的 LaTeX 中间文件（保留最终 PDF）。"""
    for pattern in ROOT_ARTIFACT_PATTERNS:
        for path in project_dir.glob(pattern):
            if path.name == f"{tex_stem}.pdf":
                continue
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)


def sync_optional_tree(cache_dir: Path, project_dir: Path, name: str) -> None:
    """将项目目录下的可选子目录（如 references/）以符号链接或复制方式同步到缓存目录。

    优先尝试创建相对路径符号链接以节省磁盘空间；若符号链接失败（如跨文件系统）
    则回退为完整目录复制。
    """
    source = project_dir / name
    if not source.exists():
        return
    target = cache_dir / name
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    try:
        target.symlink_to(Path("..") / name, target_is_directory=True)
    except OSError:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)


def ensure_cache_subdir(cache_dir: Path, relative_dir: str) -> None:
    """确保缓存目录下的指定子目录存在。"""
    (cache_dir / relative_dir).mkdir(parents=True, exist_ok=True)


def normalize_bibtex_aux(cache_dir: Path, tex_stem: str) -> None:
    """清理 .aux 文件中 \\bibstyle 命令里多余的 .bst 后缀，避免 bibtex 找不到样式文件。"""
    aux_path = cache_dir / f"{tex_stem}.aux"
    if not aux_path.exists():
        return
    content = aux_path.read_text(encoding="utf-8")
    content = re.sub(r"(\\bibstyle\{[^}]*)\.bst(\})", r"\1\2", content)
    aux_path.write_text(content, encoding="utf-8")


def summarize_process_output(label: str, result: subprocess.CompletedProcess[str]) -> str:
    """将子进程的 stdout/stderr 合并后截取最后 30 行，生成可读的摘要信息。"""
    lines = [line for line in (result.stdout + "\n" + result.stderr).splitlines() if line.strip()]
    tail = "\n".join(lines[-30:]) if lines else "(no output)"
    return f"[{label}] exit={result.returncode}\n{tail}"


def log_has_fatal_errors(log_path: Path) -> bool:
    """检查 LaTeX 日志文件中是否存在致命错误标记（如 LaTeX Error、Emergency stop 等）。"""
    if not log_path.exists():
        return False
    content = log_path.read_text(encoding="utf-8", errors="ignore")
    fatal_markers = (
        "LaTeX Error:",
        "Undefined control sequence.",
        "Emergency stop.",
        "Fatal error",
    )
    return any(marker in content for marker in fatal_markers)


def run_best_effort(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """执行子进程并捕获输出，不检查返回码（best-effort 模式）。编译失败由上层判断。"""
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def detect_bibliography_backend(tex_path: Path) -> str | None:
    """检测 TeX 文件使用的文献后端：biber（\\addbibresource）或 bibtex（\\bibliography）。"""
    content = tex_path.read_text(encoding="utf-8")
    if "\\addbibresource" in content:
        return "biber"
    if "\\bibliography{" in content:
        return "bibtex"
    return None


def build_project(project_dir: Path, tex_file: str) -> Path:
    """构建毕业论文 PDF。

    编译流程：
    1. 清理旧缓存目录 ``.latex-cache/`` 并重建。
    2. 若检测到 BENSZ_PASSTHROUGH_PDF 指令，直接复制预编译 PDF 并返回。
    3. 否则执行完整编译链路：xelatex -> bibtex/biber -> xelatex -> xelatex。
    4. 编译完成后将最终 PDF 从缓存目录复制到项目根目录。

    Args:
        project_dir: 论文项目根目录（包含 main.tex 和 extraTex/）。
        tex_file: 主 TeX 文件名，默认 ``main.tex``。

    Returns:
        生成的 PDF 文件绝对路径。

    Raises:
        BuildError: 编译失败或生成的 PDF 不存在。
    """
    tex_path = resolve_tex_file(project_dir, tex_file)
    tex_stem = tex_path.stem
    cache_dir = project_dir / CACHE_DIRNAME
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    ensure_cache_subdir(cache_dir, "extraTex")

    clean_root_artifacts(project_dir, tex_stem)

    passthrough_pdf = detect_passthrough_pdf(tex_path, project_dir)
    if passthrough_pdf is not None:
        output_pdf = project_dir / f"{tex_stem}.pdf"
        cache_pdf = cache_dir / f"{tex_stem}.pdf"
        shutil.copy2(passthrough_pdf, cache_pdf)
        shutil.copy2(passthrough_pdf, output_pdf)
        print(f"✓ PDF passthrough: {passthrough_pdf}")
        print(f"✓ PDF generated: {output_pdf}")
        print(f"✓ Build cache: {cache_dir}")
        return output_pdf

    tex_env = os.environ.copy()
    tex_roots = [PACKAGE_DIR]
    if FONTS_PACKAGE_DIR.exists():
        tex_roots.append(FONTS_PACKAGE_DIR)
    tex_env["TEXINPUTS"] = build_texinputs(tex_roots, tex_env.get("TEXINPUTS", ""))

    xelatex_cmd = [
        resolve_executable("xelatex"),
        "-interaction=nonstopmode",
        "-file-line-error",
        "-synctex=1",
        f"-output-directory={cache_dir}",
        tex_path.name,
    ]

    xelatex_run_1 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)

    bib_backend = detect_bibliography_backend(tex_path)
    bib_run: subprocess.CompletedProcess[str] | None = None
    if bib_backend == "biber":
        bib_run = run_best_effort(
            [
                resolve_executable("biber"),
                "--input-directory",
                str(cache_dir),
                "--output-directory",
                str(cache_dir),
                tex_stem,
            ],
            cwd=project_dir,
            env=tex_env,
        )
    elif bib_backend == "bibtex":
        sync_optional_tree(cache_dir, project_dir, "references")
        sync_optional_tree(cache_dir, project_dir, "bibtex-style")
        normalize_bibtex_aux(cache_dir, tex_stem)
        bib_run = run_best_effort([resolve_executable("bibtex"), tex_stem], cwd=cache_dir, env=tex_env)

    xelatex_run_2 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)
    xelatex_run_3 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)

    pdf_source = cache_dir / f"{tex_stem}.pdf"
    log_path = cache_dir / f"{tex_stem}.log"
    if not pdf_source.exists() or (bib_run is not None and bib_run.returncode != 0) or log_has_fatal_errors(log_path):
        compiler_logs = "\n\n".join(
            [
                summarize_process_output("xelatex pass 1", xelatex_run_1),
                summarize_process_output(bib_backend or "bibliography skipped", bib_run or xelatex_run_1),
                summarize_process_output("xelatex pass 2", xelatex_run_2),
                summarize_process_output("xelatex pass 3", xelatex_run_3),
            ]
        )
        raise BuildError(
            f"PDF 渲染失败：{pdf_source}\n\n{compiler_logs}"
        )

    output_pdf = project_dir / f"{tex_stem}.pdf"
    shutil.copy2(pdf_source, output_pdf)
    clean_root_artifacts(project_dir, tex_stem)
    print(f"✓ PDF generated: {output_pdf}")
    print(f"✓ Build cache: {cache_dir}")
    synctex_path = cache_dir / f"{tex_stem}.synctex.gz"
    if synctex_path.exists():
        print(f"✓ SyncTeX: {synctex_path}")
    return output_pdf


def clean_project(project_dir: Path, tex_file: str, remove_pdf: bool) -> None:
    """清理项目的编译缓存和中间文件。

    Args:
        project_dir: 论文项目根目录。
        tex_file: 主 TeX 文件名，用于确定 PDF 文件名。
        remove_pdf: 是否同时删除项目根目录下的最终 PDF。
    """
    tex_path = resolve_tex_file(project_dir, tex_file)
    tex_stem = tex_path.stem
    clean_root_artifacts(project_dir, tex_stem)
    cache_dir = project_dir / CACHE_DIRNAME
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    if remove_pdf:
        pdf_path = project_dir / f"{tex_stem}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()
    print(f"✓ Cleaned: {project_dir}")


def rasterize_pdf(pdf_path: Path, out_dir: Path, prefix: str, dpi: int) -> list[Path]:
    """将 PDF 逐页光栅化为 PNG 图片。

    使用 ``pdftoppm`` 工具将每页渲染为指定 DPI 的 PNG 图片。

    Args:
        pdf_path: 待光栅化的 PDF 文件路径。
        out_dir: PNG 输出目录。
        prefix: 输出文件名前缀（如 ``project`` 或 ``baseline``）。
        dpi: 光栅化分辨率（DPI）。

    Returns:
        按页码排序的 PNG 文件路径列表。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / prefix
    subprocess.run(
        [resolve_executable("pdftoppm"), "-r", str(dpi), "-png", str(pdf_path), str(target)],
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(out_dir.glob(f"{prefix}-*.png"))


def compare_pdfs(
    *,
    project_pdf: Path,
    baseline_pdf: Path,
    dpi: int,
    keep_rasters: bool,
    output_dir: Path | None,
) -> dict[str, object]:
    """对两个 PDF 做像素级逐页比较。

    主要用于模板迁移后的版式回归验收：将待测 PDF 与基线 PDF 以相同 DPI 光栅化为 PNG，
    再通过 Pillow 的 ImageChops.difference 逐页检测像素差异。对于有差异的页面，
    自动生成 diff 图片以供人工复查。

    Args:
        project_pdf: 待比较的项目 PDF（通常是刚构建的）。
        baseline_pdf: 基线参考 PDF（通常是验收通过的历史版本）。
        dpi: PDF 光栅化分辨率，默认 144 DPI。较高的 DPI 能捕捉更细微的差异，
            但会增大内存占用和处理时间。
        keep_rasters: 是否保留中间 PNG 光栅化图片。
        output_dir: 比较结果输出目录；为 None 时使用临时目录。

    Returns:
        包含比较结果的字典，主要字段：
        - ``identical`` (bool): 两份 PDF 是否完全一致。
        - ``mismatches`` (list): 逐页差异详情，每项包含页码、差异原因和 diff 图片路径。
        - ``report`` (str): JSON 比较报告的文件路径。

    Raises:
        RuntimeError: 缺少 Pillow 库时抛出。
    """
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        raise RuntimeError("缺少 Pillow，无法执行像素级比较。") from exc

    if output_dir is None:
        temp_root = Path(tempfile.mkdtemp(prefix="bensz-thesis-compare-"))
        cleanup_output = True
    else:
        temp_root = output_dir.expanduser().resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        cleanup_output = False

    project_png_dir = temp_root / "project"
    baseline_png_dir = temp_root / "baseline"
    diff_dir = temp_root / "diff"

    project_pages = rasterize_pdf(project_pdf, project_png_dir, "project", dpi)
    baseline_pages = rasterize_pdf(baseline_pdf, baseline_png_dir, "baseline", dpi)

    result: dict[str, object] = {
        "project_pdf": str(project_pdf),
        "baseline_pdf": str(baseline_pdf),
        "dpi": dpi,
        "project_pages": len(project_pages),
        "baseline_pages": len(baseline_pages),
        "identical": False,
        "mismatches": [],
    }

    if len(project_pages) != len(baseline_pages):
        result["reason"] = "page_count_mismatch"
    else:
        mismatches: list[dict[str, object]] = []
        for idx, (project_page, baseline_page) in enumerate(zip(project_pages, baseline_pages), start=1):
            with Image.open(project_page) as project_img, Image.open(baseline_page) as baseline_img:
                project_rgb = project_img.convert("RGB")
                baseline_rgb = baseline_img.convert("RGB")
                if project_rgb.size != baseline_rgb.size:
                    mismatches.append(
                        {
                            "page": idx,
                            "reason": "size_mismatch",
                            "project_size": project_rgb.size,
                            "baseline_size": baseline_rgb.size,
                        }
                    )
                    continue
                diff = ImageChops.difference(project_rgb, baseline_rgb)
                bbox = diff.getbbox()
                if bbox is None:
                    continue
                diff_path = diff_dir / f"page-{idx:04d}.png"
                diff_path.parent.mkdir(parents=True, exist_ok=True)
                diff.save(diff_path)
                mismatches.append(
                    {
                        "page": idx,
                        "reason": "pixel_difference",
                        "bbox": bbox,
                        "diff_image": str(diff_path),
                    }
                )
        result["mismatches"] = mismatches
        result["identical"] = len(mismatches) == 0

    report_path = temp_root / "compare-report.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["report"] = str(report_path)

    if cleanup_output and not keep_rasters:
        for child in (project_png_dir, baseline_png_dir, diff_dir):
            if child.exists():
                shutil.rmtree(child, ignore_errors=True)
    return result


def parse_args() -> argparse.Namespace:
    """解析命令行参数，支持 build / clean / compare 三个子命令。"""
    parser = argparse.ArgumentParser(description="毕业论文项目统一 TeX→PDF 渲染工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="渲染 PDF")
    build_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    build_parser.add_argument("--tex-file", default="main.tex", help="主 TeX 文件名，默认 main.tex。")

    clean_parser = subparsers.add_parser("clean", help="清理缓存与根目录中间文件")
    clean_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    clean_parser.add_argument("--tex-file", default="main.tex", help="主 TeX 文件名，默认 main.tex。")
    clean_parser.add_argument("--remove-pdf", action="store_true", help="清理时一并删除根目录 PDF。")

    compare_parser = subparsers.add_parser("compare", help="与基线 PDF 做像素级比较")
    compare_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    compare_parser.add_argument("--baseline-pdf", type=Path, required=True, help="基线 PDF 路径。")
    compare_parser.add_argument("--tex-file", default="main.tex", help="主 TeX 文件名，默认 main.tex。")
    compare_parser.add_argument("--build-first", action="store_true", help="比较前先重新构建项目。")
    compare_parser.add_argument("--dpi", type=int, default=144, help="PDF 转图分辨率，默认 144。")
    compare_parser.add_argument("--keep-rasters", action="store_true", help="保留中间 PNG。")
    compare_parser.add_argument("--output-dir", type=Path, default=None, help="比较输出目录。")

    return parser.parse_args()


def main() -> None:
    """CLI 入口：根据子命令分发到 build / clean / compare 流程。"""
    configure_windows_stdio_utf8()
    args = parse_args()
    project_dir = resolve_project_dir(getattr(args, "project_dir", None))

    if args.command == "build":
        build_project(project_dir, args.tex_file)
        return

    if args.command == "clean":
        clean_project(project_dir, args.tex_file, args.remove_pdf)
        return

    if args.command == "compare":
        project_pdf = project_dir / Path(args.tex_file).with_suffix(".pdf").name
        if args.build_first or not project_pdf.exists():
            project_pdf = build_project(project_dir, args.tex_file)
        result = compare_pdfs(
            project_pdf=project_pdf,
            baseline_pdf=args.baseline_pdf.expanduser().resolve(),
            dpi=args.dpi,
            keep_rasters=args.keep_rasters,
            output_dir=args.output_dir,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["identical"]:
            raise SystemExit(1)
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
