#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from .latex_utils import (
    ensure_tex_suffix,
    extract_cites,
    extract_headings,
    extract_inputs,
    extract_labels,
    extract_refs,
    safe_read_text,
    strip_commands_for_summary,
)


@dataclass(frozen=True)
class TexFileInfo:
    path: str
    exists: bool
    headings: List[Dict[str, str]]
    labels: List[str]
    refs: List[str]
    cites: List[str]
    char_count: int
    summary: str


@dataclass(frozen=True)
class ProjectAnalysis:
    project_path: str
    main_tex: str
    input_files: List[str]
    extra_tex_files: List[str]
    references_bib_files: List[str]
    tex_files: Dict[str, TexFileInfo]

    def to_dict(self) -> Dict:
        return {
            "project_path": self.project_path,
            "main_tex": self.main_tex,
            "input_files": self.input_files,
            "extra_tex_files": self.extra_tex_files,
            "references_bib_files": self.references_bib_files,
            "tex_files": {k: asdict(v) for k, v in self.tex_files.items()},
        }


def _resolve_input(base_dir: Path, fragment: str) -> Path:
    frag = fragment.strip()
    frag = frag.strip('"').strip("'")
    frag = ensure_tex_suffix(frag)
    return (base_dir / frag).resolve()


def _walk_inputs(project_root: Path, main_tex_path: Path, max_depth: int = 64) -> List[Path]:
    visited: Set[Path] = set()
    ordered: List[Path] = []

    def visit(file_path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        file_path = file_path.resolve()
        if file_path in visited:
            return
        visited.add(file_path)
        ordered.append(file_path)
        if not file_path.exists():
            return

        content = safe_read_text(file_path)
        for frag in extract_inputs(content):
            child = _resolve_input(project_root, frag)
            visit(child, depth + 1)

    visit(main_tex_path, 0)
    # ordered 包含 main.tex；只返回 input 文件（不含 main）
    return [p for p in ordered if p != main_tex_path]


def analyze_project(project_root: Path) -> ProjectAnalysis:
    project_root = project_root.resolve()
    main_tex = project_root / "main.tex"
    if not main_tex.exists():
        raise FileNotFoundError(f"未找到 main.tex: {main_tex}")

    input_paths = _walk_inputs(project_root, main_tex)
    input_rel = [str(p.relative_to(project_root)).replace("\\", "/") for p in input_paths]

    extra_tex_files: List[str] = []
    extra_dir = project_root / "extraTex"
    if extra_dir.exists():
        for p in sorted(extra_dir.glob("*.tex")):
            rel = str(p.relative_to(project_root)).replace("\\", "/")
            extra_tex_files.append(rel)

    references_bib_files: List[str] = []
    ref_dir = project_root / "references"
    if ref_dir.exists():
        for p in sorted(ref_dir.glob("*.bib")):
            rel = str(p.relative_to(project_root)).replace("\\", "/")
            references_bib_files.append(rel)

    tex_files: Dict[str, TexFileInfo] = {}

    def add_tex(rel_path: str) -> None:
        abs_path = project_root / rel_path
        exists = abs_path.exists()
        content = safe_read_text(abs_path) if exists else ""
        headings = [{"level": lvl, "title": title} for (lvl, title) in extract_headings(content)]
        info = TexFileInfo(
            path=rel_path,
            exists=exists,
            headings=headings,
            labels=sorted(extract_labels(content)),
            refs=sorted(extract_refs(content)),
            cites=sorted(extract_cites(content)),
            char_count=len(content),
            summary=strip_commands_for_summary(content),
        )
        tex_files[rel_path] = info

    add_tex("main.tex")
    for rel_path in sorted(set(input_rel + extra_tex_files)):
        add_tex(rel_path)

    return ProjectAnalysis(
        project_path=str(project_root),
        main_tex="main.tex",
        input_files=input_rel,
        extra_tex_files=extra_tex_files,
        references_bib_files=references_bib_files,
        tex_files=tex_files,
    )

