#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from core.diagnostic import run_tier1
from core.wordcount import count_cjk_chars


def test_count_cjk_chars_ignores_comments() -> None:
    tex = "中文%注释中文\n更多中文"
    # 注释后的“中文”不计数：实际应计 2（中文）+4（更多中文）=6
    assert count_cjk_chars(tex).cjk_count == 6


def test_run_tier1_structure_and_citations(tmp_path: Path) -> None:
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "t.bib").write_text("@article{Key,\n}\n", encoding="utf-8")

    tex = (
        "\\subsubsection{研究背景}\n中文\n"
        "\\subsubsection{国内外研究现状}\n\\cite{Key}\n"
        "\\subsubsection{现有研究的局限性}\n中文\n"
        "\\subsubsection{研究切入点}\n中文\n"
    )
    config = {
        "structure": {
            "expected_subsubsections": ["研究背景", "国内外研究现状", "现有研究的局限性", "研究切入点"],
            "strict_title_match": True,
            "min_subsubsection_count": 4,
        },
        "targets": {"bib_globs": ["references/*.bib"]},
        "quality": {"forbidden_phrases": [], "avoid_commands": []},
    }
    report = run_tier1(tex_text=tex, project_root=tmp_path, config=config)
    assert report.structure_ok is True
    assert report.citation_ok is True
