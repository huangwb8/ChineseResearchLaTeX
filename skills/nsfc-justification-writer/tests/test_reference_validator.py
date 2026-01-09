#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from core.reference_validator import check_citations, parse_bib_keys, parse_cite_keys


def test_parse_bib_keys() -> None:
    bib = "@article{Key2020,\n  title={x},\n}\n@misc{K2,\n}\n"
    assert parse_bib_keys(bib) == {"Key2020", "K2"}


def test_parse_cite_keys() -> None:
    tex = "x \\cite{A,B} y \\citet{C} z \\citep[see][]{D}"
    assert parse_cite_keys(tex) == ["A", "B", "C", "D"]


def test_check_citations_missing(tmp_path: Path) -> None:
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "t.bib").write_text("@article{A,\n}\n", encoding="utf-8")
    tex = "x \\cite{A,B}"
    result = check_citations(tex_text=tex, project_root=tmp_path, bib_globs=["references/*.bib"])
    assert result.missing_keys == ["B"]
