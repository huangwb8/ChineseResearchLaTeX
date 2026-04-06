#!/usr/bin/env python3
"""中英文简历项目统一构建工具。

支持 zh/en 双语变体的 XeLaTeX -> BibTeX -> XeLaTeX x2 编译流程，
并提供基于 Pillow 的像素级 PDF 比较验收能力，用于简历版式回归检测。

子命令：
  build    渲染 PDF（支持 --variant all/zh/en）
  clean    清理缓存与中间文件
  compare  与基线 PDF 做像素级比较
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

# bensz-cv 公共包根目录（packages/bensz-cv）
PACKAGE_DIR = Path(__file__).resolve().parents[1]
# bensz-fonts 共享字体包根目录（packages/bensz-fonts），用于注入 TEXINPUTS
FONTS_PACKAGE_DIR = PACKAGE_DIR.parent / "bensz-fonts"
# LaTeX 中间产物缓存目录名，放在项目根目录下
CACHE_DIRNAME = ".latex-cache"
# 项目根目录下需要清理的 LaTeX 中间文件扩展名
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
# 语种变体到 TeX 主文件的映射：zh -> main-zh.tex，en -> main-en.tex
VARIANT_TO_TEX = {
    "zh": "main-zh.tex",
    "en": "main-en.tex",
}
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
    "pdftoppm": (
        "/opt/homebrew/bin/pdftoppm",
        "/usr/local/bin/pdftoppm",
    ),
}


class BuildError(RuntimeError):
    """简历构建过程中的错误，如编译失败或文件缺失。"""
    pass


def configure_windows_stdio_utf8() -> None:
    """在 Windows 上将 stdout/stderr 编码切换为 UTF-8，避免中文乱码。"""
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def is_project_root(path: Path) -> bool:
    """判断路径是否为合法的 CV 项目根目录（需同时包含 main-zh.tex 和 main-en.tex）。"""
    return (path / "main-zh.tex").exists() and (path / "main-en.tex").exists()


def find_project_root(start: Path | None = None) -> Path:
    """从给定路径向上逐级搜索 CV 项目根目录。"""
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "无法定位 CV 项目根目录。请在项目目录内运行，或使用 --project-dir 显式指定。"
    )


def resolve_project_dir(project_dir: Path | None) -> Path:
    """解析项目目录：显式指定时直接验证，否则从 cwd 向上自动搜索。"""
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


def resolve_tex_file(project_dir: Path, tex_file: str | None, variant: str) -> Path:
    """根据变体名或显式文件名定位 TeX 主文件，并校验其位于项目根目录下。"""
    if tex_file is not None:
        candidate = (project_dir / tex_file).resolve()
    else:
        if variant == "all":
            raise BuildError("variant=all 时必须逐个展开，不能直接解析为单个 tex 文件。")
        candidate = (project_dir / VARIANT_TO_TEX[variant]).resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"TeX 主文件不存在：{candidate}")
    if candidate.parent != project_dir:
        raise BuildError("当前渲染器仅支持项目根目录下的主 TeX 文件。")
    return candidate


def resolve_executable(name: str) -> str:
    """查找可执行文件：先 PATH，再 TOOL_CANDIDATES 硬编码路径。"""
    resolved = shutil.which(name)
    if resolved:
        return resolved
    for candidate in TOOL_CANDIDATES.get(name, ()):
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"未找到可执行文件：{name}")


def build_texinputs(prefixes: list[Path], existing: str) -> str:
    """构建 TEXINPUTS 环境变量值，将公共包和字体目录注入 TeX 搜索路径。"""
    normalized = [f"{path.resolve()}//" for path in prefixes]
    normalized.append("")
    if existing:
        normalized.append(existing)
    return os.pathsep.join(normalized)


def clean_root_artifacts(project_dir: Path, tex_stem: str) -> None:
    """清理项目根目录下的 LaTeX 中间文件（跳过同名 PDF）。"""
    for pattern in ROOT_ARTIFACT_PATTERNS:
        for path in project_dir.glob(pattern):
            if path.name == f"{tex_stem}.pdf":
                continue
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)


def sync_optional_tree(cache_dir: Path, project_dir: Path, name: str) -> None:
    """将项目目录下的可选子目录（如 references/）同步到缓存目录，优先用符号链接。"""
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
        target.symlink_to(source.resolve(), target_is_directory=True)
    except OSError:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)


def normalize_bibtex_aux(cache_dir: Path, tex_stem: str) -> None:
    """清理 .aux 文件中 \\bibstyle 命令里多余的 .bst 后缀，避免 bibtex 找不到样式文件。"""
    aux_path = cache_dir / f"{tex_stem}.aux"
    if not aux_path.exists():
        return
    content = aux_path.read_text(encoding="utf-8")
    content = re.sub(r"(\\bibstyle\{[^}]*)\.bst(\})", r"\1\2", content)
    aux_path.write_text(content, encoding="utf-8")


def summarize_process_output(label: str, result: subprocess.CompletedProcess[str]) -> str:
    """将子进程的 stdout/stderr 合并后截取末尾 30 行，用于构建错误报告。"""
    lines = [line for line in (result.stdout + "\n" + result.stderr).splitlines() if line.strip()]
    tail = "\n".join(lines[-30:]) if lines else "(no output)"
    return f"[{label}] exit={result.returncode}\n{tail}"


def log_has_fatal_errors(log_path: Path) -> bool:
    """扫描 LaTeX .log 文件是否包含致命错误标记。"""
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
    """以 best-effort 模式运行子进程，不抛异常，由调用方检查返回码。"""
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def build_single(project_dir: Path, tex_path: Path) -> Path:
    """单语种完整构建流程。

    编译链路：xelatex -> bibtex -> xelatex -> xelatex。
    中间产物隔离到 .latex-cache/<tex_stem>/ 目录下，
    最终 PDF 复制回项目根目录，并保留 SyncTeX 文件以支持编辑器跳转。

    Args:
        project_dir: CV 项目根目录。
        tex_path: TeX 主文件路径（需位于项目根目录下）。

    Returns:
        生成的 PDF 文件路径。

    Raises:
        BuildError: 编译失败或 BibTeX 出错时抛出，附带各 pass 日志。
    """
    tex_stem = tex_path.stem
    cache_dir = project_dir / CACHE_DIRNAME / tex_stem
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    clean_root_artifacts(project_dir, tex_stem)

    tex_env = os.environ.copy()
    tex_roots = [PACKAGE_DIR]
    if FONTS_PACKAGE_DIR.exists():
        tex_roots.append(FONTS_PACKAGE_DIR)
    tex_env["TEXINPUTS"] = build_texinputs(tex_roots, tex_env.get("TEXINPUTS", ""))

    xelatex_cmd = [
        resolve_executable("xelatex"),
        "-interaction=nonstopmode",
        "-file-line-error",
        "-recorder",
        "-synctex=1",
        f"-output-directory={cache_dir}",
        tex_path.name,
    ]

    xelatex_run_1 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)
    sync_optional_tree(cache_dir, project_dir, "references")
    normalize_bibtex_aux(cache_dir, tex_stem)
    bib_run = run_best_effort([resolve_executable("bibtex"), tex_stem], cwd=cache_dir, env=tex_env)
    xelatex_run_2 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)
    xelatex_run_3 = run_best_effort(xelatex_cmd, cwd=project_dir, env=tex_env)

    pdf_source = cache_dir / f"{tex_stem}.pdf"
    log_path = cache_dir / f"{tex_stem}.log"
    if not pdf_source.exists() or bib_run.returncode != 0 or log_has_fatal_errors(log_path):
        compiler_logs = "\n\n".join(
            [
                summarize_process_output("xelatex pass 1", xelatex_run_1),
                summarize_process_output("bibtex", bib_run),
                summarize_process_output("xelatex pass 2", xelatex_run_2),
                summarize_process_output("xelatex pass 3", xelatex_run_3),
            ]
        )
        raise BuildError(f"PDF 渲染失败：{pdf_source}\n\n{compiler_logs}")

    output_pdf = project_dir / f"{tex_stem}.pdf"
    shutil.copy2(pdf_source, output_pdf)
    clean_root_artifacts(project_dir, tex_stem)
    print(f"✓ PDF generated: {output_pdf}")
    print(f"✓ Build cache: {cache_dir}")
    synctex_path = cache_dir / f"{tex_stem}.synctex.gz"
    if synctex_path.exists():
        print(f"✓ SyncTeX: {synctex_path}")
    return output_pdf


def build_project(project_dir: Path, variant: str, tex_file: str | None) -> list[Path]:
    """项目级构建入口，支持 --variant all/zh/en。

    - variant="all" 时依次构建 zh 和 en 两个变体；
    - 指定 tex_file 时直接编译该文件，忽略 variant。

    Args:
        project_dir: CV 项目根目录。
        variant: 语种变体（all/zh/en）。
        tex_file: 显式指定的 TeX 主文件名，优先于 variant。

    Returns:
        所有成功生成的 PDF 路径列表。
    """
    if tex_file is not None:
        return [build_single(project_dir, resolve_tex_file(project_dir, tex_file, variant))]
    variants = ["zh", "en"] if variant == "all" else [variant]
    return [build_single(project_dir, resolve_tex_file(project_dir, None, name)) for name in variants]


def clean_project(project_dir: Path, variant: str, tex_file: str | None, remove_pdf: bool) -> None:
    """清理指定变体的缓存目录和根目录中间文件；可选删除最终 PDF。"""
    tex_paths: list[Path]
    if tex_file is not None:
        tex_paths = [resolve_tex_file(project_dir, tex_file, variant)]
    else:
        variants = ["zh", "en"] if variant == "all" else [variant]
        tex_paths = [resolve_tex_file(project_dir, None, name) for name in variants]
    for tex_path in tex_paths:
        tex_stem = tex_path.stem
        clean_root_artifacts(project_dir, tex_stem)
        cache_dir = project_dir / CACHE_DIRNAME / tex_stem
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        if remove_pdf:
            pdf_path = project_dir / f"{tex_stem}.pdf"
            if pdf_path.exists():
                pdf_path.unlink()
    if (project_dir / CACHE_DIRNAME).exists() and not any((project_dir / CACHE_DIRNAME).iterdir()):
        (project_dir / CACHE_DIRNAME).rmdir()
    print(f"✓ Cleaned: {project_dir}")


def rasterize_pdf(pdf_path: Path, out_dir: Path, prefix: str, dpi: int) -> list[Path]:
    """使用 pdftoppm 将 PDF 逐页光栅化为 PNG 图片，用于后续像素级比较。"""
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
    """将项目 PDF 与基线 PDF 做像素级比较，用于简历版式回归验收。

    流程：两份 PDF 分别用 pdftoppm 光栅化为 PNG，再用 Pillow 逐页
    做 ImageChops.difference 差异检测。结果写入 compare-report.json。

    Args:
        project_pdf: 待验收的项目 PDF 路径。
        baseline_pdf: 基线（参考）PDF 路径。
        dpi: 光栅化分辨率，默认 144。
        keep_rasters: 是否保留中间 PNG 图片。
        output_dir: 比较输出目录，为 None 时使用临时目录。

    Returns:
        包含 identical、mismatches、report 等字段的比较结果字典。
    """
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        raise RuntimeError("缺少 Pillow，无法执行像素级比较。") from exc

    if output_dir is None:
        temp_root = Path(tempfile.mkdtemp(prefix="bensz-cv-compare-"))
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
    """解析命令行参数，支持 build/clean/compare 三个子命令。"""
    parser = argparse.ArgumentParser(description="简历项目统一 TeX→PDF 渲染工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="渲染 PDF")
    build_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    build_parser.add_argument("--variant", choices=("zh", "en", "all"), default="all", help="构建语种。")
    build_parser.add_argument("--tex-file", default=None, help="主 TeX 文件名，默认按 variant 推断。")

    clean_parser = subparsers.add_parser("clean", help="清理缓存与根目录中间文件")
    clean_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    clean_parser.add_argument("--variant", choices=("zh", "en", "all"), default="all", help="清理语种。")
    clean_parser.add_argument("--tex-file", default=None, help="主 TeX 文件名，默认按 variant 推断。")
    clean_parser.add_argument("--remove-pdf", action="store_true", help="清理时一并删除根目录 PDF。")

    compare_parser = subparsers.add_parser("compare", help="与基线 PDF 做像素级比较")
    compare_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    compare_parser.add_argument("--variant", choices=("zh", "en"), required=True, help="待比较语种。")
    compare_parser.add_argument("--baseline-pdf", type=Path, required=True, help="基线 PDF 路径。")
    compare_parser.add_argument("--tex-file", default=None, help="主 TeX 文件名，默认按 variant 推断。")
    compare_parser.add_argument("--build-first", action="store_true", help="比较前先重新构建项目。")
    compare_parser.add_argument("--dpi", type=int, default=144, help="PDF 转图分辨率，默认 144。")
    compare_parser.add_argument("--keep-rasters", action="store_true", help="保留中间 PNG。")
    compare_parser.add_argument("--output-dir", type=Path, default=None, help="比较输出目录。")

    return parser.parse_args()


def main() -> None:
    """CLI 入口：根据子命令分发到 build/clean/compare 处理函数。"""
    configure_windows_stdio_utf8()
    args = parse_args()
    project_dir = resolve_project_dir(getattr(args, "project_dir", None))

    if args.command == "build":
        build_project(project_dir, args.variant, args.tex_file)
        return

    if args.command == "clean":
        clean_project(project_dir, args.variant, args.tex_file, args.remove_pdf)
        return

    if args.command == "compare":
        tex_path = resolve_tex_file(project_dir, args.tex_file, args.variant)
        project_pdf = project_dir / f"{tex_path.stem}.pdf"
        if args.build_first or not project_pdf.exists():
            project_pdf = build_single(project_dir, tex_path)
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
