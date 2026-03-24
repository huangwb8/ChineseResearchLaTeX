#!/usr/bin/env python3
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

PACKAGE_DIR = Path(__file__).resolve().parents[1]
FONTS_PACKAGE_DIR = PACKAGE_DIR.parent / "bensz-fonts"
CACHE_DIRNAME = ".latex-cache"
DEFAULT_TEX_MAIN = "main.tex"
LEGACY_TEX_MAIN = "Thesis.tex"
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
    pass


def configure_windows_stdio_utf8() -> None:
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def has_main_extra_tex_layout(path: Path) -> bool:
    return (path / DEFAULT_TEX_MAIN).exists() and (path / "extraTex").exists()


def has_legacy_thesis_layout(path: Path) -> bool:
    return (
        (path / LEGACY_TEX_MAIN).exists()
        and (path / ".latexmkrc").exists()
        and (path / "template.json").exists()
    )


def is_project_root(path: Path) -> bool:
    return has_main_extra_tex_layout(path) or has_legacy_thesis_layout(path)


def find_project_root(start: Path | None = None) -> Path:
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "无法定位 thesis 项目根目录。支持布局：`main.tex + extraTex/` 或 `template.json + Thesis.tex + .latexmkrc`。"
    )


def resolve_project_dir(project_dir: Path | None) -> Path:
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


def detect_default_tex_file(project_dir: Path) -> str:
    if has_main_extra_tex_layout(project_dir):
        return DEFAULT_TEX_MAIN
    if has_legacy_thesis_layout(project_dir):
        return LEGACY_TEX_MAIN
    raise FileNotFoundError(f"无法为 thesis 项目自动识别主 TeX 文件：{project_dir}")


def resolve_tex_file(project_dir: Path, tex_file: str | None) -> Path:
    if tex_file is None:
        tex_file = detect_default_tex_file(project_dir)
    candidate = (project_dir / tex_file).resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"TeX 主文件不存在：{candidate}")
    if candidate.parent != project_dir:
        raise BuildError("当前渲染器仅支持项目根目录下的主 TeX 文件。")
    return candidate


def resolve_executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    for candidate in TOOL_CANDIDATES.get(name, ()):
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"未找到可执行文件：{name}")


def build_texinputs(prefixes: list[Path], existing: str) -> str:
    normalized = [f"{path.resolve()}//" for path in prefixes]
    normalized.append("")
    if existing:
        normalized.append(existing)
    return os.pathsep.join(normalized)


def clean_root_artifacts(project_dir: Path, tex_stem: str) -> None:
    for pattern in ROOT_ARTIFACT_PATTERNS:
        for path in project_dir.glob(pattern):
            if path.name == f"{tex_stem}.pdf":
                continue
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)


def sync_optional_tree(cache_dir: Path, project_dir: Path, name: str) -> None:
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


def normalize_bibtex_aux(cache_dir: Path, tex_stem: str) -> None:
    aux_path = cache_dir / f"{tex_stem}.aux"
    if not aux_path.exists():
        return
    content = aux_path.read_text(encoding="utf-8")
    content = re.sub(r"(\\bibstyle\{[^}]*)\.bst(\})", r"\1\2", content)
    aux_path.write_text(content, encoding="utf-8")


def summarize_process_output(label: str, result: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in (result.stdout + "\n" + result.stderr).splitlines() if line.strip()]
    tail = "\n".join(lines[-30:]) if lines else "(no output)"
    return f"[{label}] exit={result.returncode}\n{tail}"


def log_has_fatal_errors(log_path: Path) -> bool:
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
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def detect_bibliography_backend(tex_path: Path) -> str | None:
    content = tex_path.read_text(encoding="utf-8")
    if "\\addbibresource" in content:
        return "biber"
    if "\\bibliography{" in content:
        return "bibtex"
    return None


def build_project(project_dir: Path, tex_file: str | None) -> Path:
    tex_path = resolve_tex_file(project_dir, tex_file)
    tex_stem = tex_path.stem
    cache_dir = project_dir / CACHE_DIRNAME
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


def clean_project(project_dir: Path, tex_file: str | None, remove_pdf: bool) -> None:
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
    parser = argparse.ArgumentParser(description="毕业论文项目统一 TeX→PDF 渲染工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="渲染 PDF")
    build_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    build_parser.add_argument(
        "--tex-file",
        default=None,
        help="主 TeX 文件名。省略时自动识别（如 main.tex 或 Thesis.tex）。",
    )

    clean_parser = subparsers.add_parser("clean", help="清理缓存与根目录中间文件")
    clean_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    clean_parser.add_argument(
        "--tex-file",
        default=None,
        help="主 TeX 文件名。省略时自动识别（如 main.tex 或 Thesis.tex）。",
    )
    clean_parser.add_argument("--remove-pdf", action="store_true", help="清理时一并删除根目录 PDF。")

    compare_parser = subparsers.add_parser("compare", help="与基线 PDF 做像素级比较")
    compare_parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    compare_parser.add_argument("--baseline-pdf", type=Path, required=True, help="基线 PDF 路径。")
    compare_parser.add_argument(
        "--tex-file",
        default=None,
        help="主 TeX 文件名。省略时自动识别（如 main.tex 或 Thesis.tex）。",
    )
    compare_parser.add_argument("--build-first", action="store_true", help="比较前先重新构建项目。")
    compare_parser.add_argument("--dpi", type=int, default=144, help="PDF 转图分辨率，默认 144。")
    compare_parser.add_argument("--keep-rasters", action="store_true", help="保留中间 PNG。")
    compare_parser.add_argument("--output-dir", type=Path, default=None, help="比较输出目录。")

    return parser.parse_args()


def main() -> None:
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
        tex_path = resolve_tex_file(project_dir, args.tex_file)
        project_pdf = project_dir / tex_path.with_suffix(".pdf").name
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
