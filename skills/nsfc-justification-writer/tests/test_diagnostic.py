#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from core.diagnostic import run_tier1


def test_run_tier1_detects_structure_citations_quality_and_doi(tmp_path: Path) -> None:
    (tmp_path / "references").mkdir(parents=True, exist_ok=True)
    # A 存在但缺 doi；B 缺失
    (tmp_path / "references" / "t.bib").write_text(
        "@article{A,\n  title={x},\n  year={2020},\n}\n",
        encoding="utf-8",
    )

    tex = (
        "\\subsubsection{研究背景}\n"
        "这里写国际领先是不合适的。\n"
        "\\subsubsection{国内外研究现状}\n"
        "\\section{BAD}\n"
        "这里引用 \\cite{A,B}。\n"
        "\\subsubsection{现有研究的局限性}\n"
        "正文。\n"
    )
    config = {
        "structure": {
            "expected_subsubsections": ["研究背景", "国内外研究现状", "现有研究的局限性", "研究切入点"],
            "strict_title_match": True,
            "min_subsubsection_count": 4,
        },
        "targets": {"bib_globs": ["references/*.bib"]},
        "quality": {"forbidden_phrases": ["国际领先"], "avoid_commands": ["\\section"]},
    }

    report = run_tier1(tex_text=tex, project_root=tmp_path, config=config)
    assert report.structure_ok is False
    assert report.citation_ok is False
    assert report.missing_citation_keys == ["B"]
    assert report.missing_doi_keys == ["A"]
    assert report.forbidden_phrases_hits == ["国际领先"]
    assert report.avoid_commands_hits == ["\\section"]

