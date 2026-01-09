#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from core.latex_parser import parse_subsubsections, replace_subsubsection_body


def test_parse_subsubsections_basic() -> None:
    tex = "\\subsubsection{A}\nfoo\n\\subsubsection{B}\nbar\n"
    secs = parse_subsubsections(tex)
    assert [s.title for s in secs] == ["A", "B"]
    assert secs[0].body_text(tex).strip().startswith("foo")
    assert secs[1].body_text(tex).strip().startswith("bar")


def test_replace_subsubsection_body() -> None:
    tex = "\\subsubsection{A}\nold\n\\subsubsection{B}\nkeep\n"
    new_tex, changed = replace_subsubsection_body(tex, "A", "new content")
    assert changed is True
    assert "\\subsubsection{A}" in new_tex
    assert "new content" in new_tex
    assert "old" not in new_tex
    assert "keep" in new_tex
