#!/usr/bin/env python3
"""Compatibility wrapper for UCAS thesis DOCX export.

The reusable implementation now lives in
``packages/bensz-thesis/scripts/thesis_docx_tool.py`` and is exposed through
``thesis_project_tool.py docx``. This wrapper keeps the historical UCAS command
available for one release cycle while delegating conversion to the common
``bensz-thesis`` DOCX path.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_DIR.parents[1]


def get_installed_package_root() -> Path | None:
    try:
        kpsewhich = subprocess.run(
            ["kpsewhich", "bensz-thesis.sty"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if kpsewhich.returncode != 0 or not kpsewhich.stdout.strip():
        return None
    return Path(kpsewhich.stdout.strip()).expanduser().resolve().parent


def iter_common_module_candidates() -> list[Path]:
    candidates = [
        REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "thesis_docx_tool.py",
    ]
    package_root = get_installed_package_root()
    if package_root is not None:
        candidates.append(package_root / "scripts" / "thesis_docx_tool.py")
    return candidates


def load_common_tool():
    module_path = next((path for path in iter_common_module_candidates() if path.exists()), None)
    if module_path is None:
        raise FileNotFoundError(
            "未找到通用 DOCX 导出模块。请在完整仓库中运行，或升级已安装的 bensz-thesis。"
        )
    spec = importlib.util.spec_from_file_location("thesis_docx_tool", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载通用 DOCX 导出模块：{module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="兼容旧入口：将 UCAS LaTeX 源导出为可编辑 Word 初稿。"
    )
    parser.add_argument("--project-dir", type=Path, default=PROJECT_DIR, help="论文项目目录。")
    parser.add_argument("--tex-file", type=str, default="main.tex", help="主 TeX 文件名。")
    parser.add_argument("--reference-doc", type=Path, default=None, help="参考 Word 模板 .docx。")
    parser.add_argument("--output", type=Path, default=None, help="输出 DOCX 路径。")
    parser.add_argument("--markdown-output", type=Path, default=None, help="兼容旧参数：复制中间 Markdown 到该路径。")
    parser.add_argument("--quality-report", type=Path, default=None, help="兼容旧参数：复制质量报告到该路径。")
    parser.add_argument(
        "--skip-style-normalization",
        action="store_true",
        help="跳过 DOCX 段落样式归一化，仅生成质量报告。",
    )
    parser.add_argument(
        "--postprocess-only-docx",
        type=Path,
        default=None,
        help="兼容旧参数：仅对已有 DOCX 做通用样式归一化与质量报告。",
    )
    return parser.parse_args()


def _resolve_explicit_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    raw = path.expanduser()
    return raw.resolve()


def _resolve_reference_doc(project_dir: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    raw = path.expanduser()
    candidates = [raw]
    if not raw.is_absolute():
        candidates.append(project_dir / raw)
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
    return raw.resolve()


def _copy_if_requested(source: Path, target: Path | None) -> None:
    if target is None:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print(f"[OK] copied: {target}")


def postprocess_only(common_tool, docx_path: Path, report_path: Path | None) -> int:
    if not docx_path.exists():
        raise FileNotFoundError(f"待处理 DOCX 不存在：{docx_path}")
    before, after, remap = common_tool.normalize_docx_styles(docx_path)
    state = common_tool.DocxExportState(docx_path.parent / ".latex-cache" / "docx")
    output_report = report_path or docx_path.with_name(f"{docx_path.stem}_docx_quality_report.md")
    common_tool.write_quality_report(
        report_path=output_report,
        docx_path=docx_path,
        markdown_path=docx_path.with_suffix(".md"),
        reference_doc=None,
        state=state,
        pandoc_version=common_tool.get_pandoc_version(),
        style_before=before,
        style_after=after,
        style_remap=remap,
        fallback_used=False,
    )
    print(f"[OK] postprocess docx: {docx_path}")
    print(f"[OK] quality report: {output_report}")
    return 0


def main() -> int:
    args = parse_args()
    common_tool = load_common_tool()
    project_dir = args.project_dir.expanduser().resolve()
    tex_stem = Path(args.tex_file).stem

    if args.postprocess_only_docx is not None:
        return postprocess_only(
            common_tool,
            _resolve_explicit_path(args.postprocess_only_docx),
            _resolve_explicit_path(args.quality_report),
        )

    output = _resolve_explicit_path(args.output)
    if output is None:
        output = project_dir / f"{tex_stem}_from_tex_资环模板.docx"
    markdown_output = _resolve_explicit_path(args.markdown_output)
    if markdown_output is None:
        markdown_output = project_dir / f"{tex_stem}_from_tex_word_source.md"
    quality_report = _resolve_explicit_path(args.quality_report)
    if quality_report is None:
        quality_report = output.with_name(f"{output.stem}_质量报告.md")

    docx_path = common_tool.export_docx_project(
        project_dir=project_dir,
        tex_file=args.tex_file,
        output=output,
        reference_doc=_resolve_reference_doc(project_dir, args.reference_doc),
        keep_markdown=False,
        skip_style_normalization=args.skip_style_normalization,
        allow_external_output=True,
    )

    cache_dir = project_dir / ".latex-cache" / "docx"
    _copy_if_requested(cache_dir / f"{tex_stem}.md", markdown_output)
    _copy_if_requested(cache_dir / f"{tex_stem}_docx_quality_report.md", quality_report)
    print(f"[OK] docx: {docx_path}")
    print("[WARN] export_docx.py is a compatibility wrapper; prefer thesis_project_tool.py docx.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
