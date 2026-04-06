#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

PROJECT_DIR = Path(__file__).resolve().parents[1]
DOCX_OUTPUT = PROJECT_DIR / "main.docx"
SECTION_HEADINGS = {
    "summary",
    "abstract",
    "introduction",
    "results",
    "discussion",
    "methods",
    "star methods",
    "references",
    "figure legends",
    "figure titles and legends",
    "supplementary materials",
    "supplemental information titles and legends",
    "additional information",
}


def get_installed_package_root() -> Path | None:
    kpsewhich = subprocess.run(
        ["kpsewhich", "bensz-paper.sty"],
        capture_output=True,
        text=True,
        check=False,
    )
    if kpsewhich.returncode != 0:
        return None
    value = kpsewhich.stdout.strip()
    if not value:
        return None
    return Path(value).expanduser().resolve().parent


def iter_script_candidates() -> list[Path]:
    candidates = [
        PROJECT_DIR.parent.parent / "packages" / "bensz-paper" / "scripts" / "paper_project_tool.py",
    ]
    package_root = get_installed_package_root()
    if package_root is not None:
        candidates.append(package_root / "scripts" / "paper_project_tool.py")
        candidates.append(package_root / "scripts" / "manuscript_tool.py")
    return candidates


def _normalize_heading_text(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _fix_docx_heading_alignment(docx_path: Path) -> None:
    if not docx_path.exists():
        return

    doc = Document(docx_path)
    paragraphs = list(doc.paragraphs)
    first_heading1_index = next(
        (
            index
            for index, para in enumerate(paragraphs)
            if para.text.strip() and para.style and para.style.name == "Heading 1"
        ),
        None,
    )
    if first_heading1_index is None:
        return

    first_heading1 = paragraphs[first_heading1_index]

    has_body_before_first_heading = any(
        para.text.strip() and (not para.style or not para.style.name.startswith("Heading"))
        for para in paragraphs[:first_heading1_index]
    )
    is_section_heading = _normalize_heading_text(first_heading1.text) in SECTION_HEADINGS

    if has_body_before_first_heading or is_section_heading:
        first_heading1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        doc.save(docx_path)


def main() -> int:
    script_path = next((path for path in iter_script_candidates() if path.exists()), None)
    if script_path is None:
        print(
            "未找到 bensz-paper 构建脚本。请先安装 bensz-paper，或在完整仓库中运行本项目。",
            file=sys.stderr,
        )
        return 1

    args = sys.argv[1:] or ["build", "--project-dir", str(PROJECT_DIR)]
    result = subprocess.run([sys.executable, str(script_path), *args], cwd=PROJECT_DIR)
    if result.returncode == 0:
        _fix_docx_heading_alignment(DOCX_OUTPUT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
