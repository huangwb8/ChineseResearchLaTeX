#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from core.writing_coach import CoachInput, _fallback_markdown, _infer_stage


def test_infer_stage_skeleton_when_empty() -> None:
    stage = _infer_stage(tex_text="", tier1={"structure_ok": False, "word_count": 0}, word_target=4000, tol=200)
    assert stage == "skeleton"


def test_infer_stage_draft_when_too_short() -> None:
    stage = _infer_stage(
        tex_text="x",
        tier1={"structure_ok": True, "word_count": 500, "citation_ok": True, "forbidden_phrases_hits": [], "avoid_commands_hits": []},
        word_target=4000,
        tol=200,
    )
    assert stage == "draft"


def test_infer_stage_revise_when_citation_or_quality_issues() -> None:
    stage = _infer_stage(
        tex_text="x",
        tier1={"structure_ok": True, "word_count": 2500, "citation_ok": False, "forbidden_phrases_hits": [], "avoid_commands_hits": []},
        word_target=4000,
        tol=200,
    )
    assert stage == "revise"


def test_infer_stage_polish_when_wordcount_off() -> None:
    stage = _infer_stage(
        tex_text="x",
        tier1={"structure_ok": True, "word_count": 5200, "citation_ok": True, "forbidden_phrases_hits": [], "avoid_commands_hits": []},
        word_target=4000,
        tol=200,
    )
    assert stage == "polish"


def test_infer_stage_final_when_ready() -> None:
    stage = _infer_stage(
        tex_text="x",
        tier1={"structure_ok": True, "word_count": 4050, "citation_ok": True, "forbidden_phrases_hits": [], "avoid_commands_hits": []},
        word_target=4000,
        tol=200,
    )
    assert stage == "final"


def test_fallback_markdown_contains_actionable_blocks() -> None:
    inp = CoachInput(stage="draft", info_form_text="", tex_text="x", tier1={"structure_ok": True, "citation_ok": True, "word_count": 1000}, term_matrix_md="")
    md = _fallback_markdown(inp, "draft")
    assert "## 本轮只做三件事" in md
    assert "## 需要你补充/确认的问题" in md
    assert "## 下一步可直接复制的写作提示词" in md

