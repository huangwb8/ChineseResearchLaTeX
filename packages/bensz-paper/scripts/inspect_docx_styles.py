#!/usr/bin/env python3
"""
检查 DOCX 文件的样式设置，特别是行间距和段间距。

LaTeX profile 参照值（bml-profile-bensz-manu-01.def）：
  行距:      ONE_POINT_FIVE  (setstretch = 1.5)
  段首缩进:  0 pt            (parindent  = 0pt)
  段后间距:  ~4 pt           (parskip    = 0.2\baselineskip ≈ 3.6pt)
  段前间距:  0 pt
"""

from __future__ import annotations

import argparse
from pathlib import Path
from docx import Document

PROJECT_ROOT_MARKERS = ("main.tex",)


def is_project_root(path: Path) -> bool:
    """Return True when the directory looks like a manuscript project root."""
    return any((path / marker).exists() for marker in PROJECT_ROOT_MARKERS)


def find_project_root(start: Path | None = None) -> Path:
    """Walk upward until a manuscript project root is found."""
    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "Cannot find project root. Run inside the manuscript project tree or "
        "pass --project-dir explicitly."
    )


def resolve_project_dir(project_dir: Path | None) -> Path:
    """Resolve the manuscript project directory from CLI input or the current working tree."""
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


def inspect_docx(docx_path: Path) -> None:
    """检查 DOCX 文件的样式设置。"""
    print(f"检查文件: {docx_path}\n")

    doc = Document(docx_path)

    # 检查样式
    print("=" * 60)
    print("样式设置:")
    print("=" * 60)

    for style in doc.styles:
        if hasattr(style, 'paragraph_format'):
            pf = style.paragraph_format
            if pf.line_spacing_rule or pf.space_after or pf.first_line_indent:
                print(f"\n样式: {style.name}")
                print(f"  行距规则: {pf.line_spacing_rule}")
                print(f"  行距值: {pf.line_spacing}")
                print(f"  段后间距: {pf.space_after}")
                print(f"  段前间距: {pf.space_before}")
                print(f"  首行缩进: {pf.first_line_indent}")

    # 检查实际段落
    print("\n" + "=" * 60)
    print("前5个段落的实际格式:")
    print("=" * 60)

    for i, para in enumerate(doc.paragraphs[:5]):
        pf = para.paragraph_format
        print(f"\n段落 {i+1}: {para.text[:50]}...")
        print(f"  样式: {para.style.name if para.style else 'None'}")
        print(f"  行距规则: {pf.line_spacing_rule}")
        print(f"  行距值: {pf.line_spacing}")
        print(f"  段后间距: {pf.space_after}")
        print(f"  段前间距: {pf.space_before}")
        print(f"  首行缩进: {pf.first_line_indent}")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Inspect reference.docx and manuscript DOCX paragraph styles.")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory. Defaults to the nearest parent containing main.tex.",
    )
    parser.add_argument(
        "--docx",
        type=Path,
        default=None,
        help="Explicit DOCX file to inspect instead of project-root/main.docx.",
    )
    parser.add_argument(
        "--reference-doc",
        type=Path,
        default=None,
        help="Explicit reference.docx path to inspect.",
    )
    return parser.parse_args()


def main() -> None:
    """主函数。"""
    args = parse_args()
    project_dir = resolve_project_dir(args.project_dir)
    reference_doc = (args.reference_doc or project_dir / "artifacts" / "reference.docx").expanduser().resolve()
    docx_path = (args.docx or project_dir / "main.docx").expanduser().resolve()

    if reference_doc.exists():
        print("检查 reference.docx:")
        print("-" * 60)
        inspect_docx(reference_doc)
        print()
    else:
        print(f"跳过 reference.docx：文件不存在 {reference_doc}\n")

    if not docx_path.exists():
        raise FileNotFoundError(f"找不到 DOCX 文件: {docx_path}")

    print("检查 main.docx:")
    print("-" * 60)
    inspect_docx(docx_path)


if __name__ == '__main__':
    main()
