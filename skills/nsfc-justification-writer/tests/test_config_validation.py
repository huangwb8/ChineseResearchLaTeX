#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

import pytest

from core.config_loader import load_config, validate_config


def test_validate_config_accepts_repo_default_config() -> None:
    skill_root = Path(__file__).resolve().parents[1]
    cfg = load_config(skill_root, load_user_override=False)
    assert validate_config(skill_root=skill_root, config=cfg) == []


def test_validate_config_reports_type_errors(tmp_path: Path) -> None:
    bad = {
        "skill_info": {"name": "x", "version": "1.0"},
        "targets": {"justification_tex": "a.tex", "bib_globs": "references/*.bib"},
        "structure": {"expected_subsubsections": "研究背景", "min_subsubsection_count": "4"},
        "quality": {"forbidden_phrases": ["国际领先"], "avoid_commands": ["\\\\section"]},
        "word_count": {"target": 4000, "tolerance": 200},
        "ai": {"enabled": True, "tier2_chunk_size": "12000"},
        "prompts": {},
    }
    errs = validate_config(skill_root=tmp_path, config=bad)
    assert any("targets.bib_globs" in e for e in errs)
    assert any("structure.(expected_subsubsections|recommended_subsubsections)" in e for e in errs)
    assert any("structure.min_subsubsection_count" in e for e in errs)
    assert any("ai.tier2_chunk_size" in e for e in errs)


def test_validate_config_allows_empty_terminology_dimensions(tmp_path: Path) -> None:
    cfg = {
        "skill_info": {"name": "x", "version": "1.0"},
        "targets": {"justification_tex": "a.tex", "bib_globs": ["references/*.bib"]},
        "structure": {"expected_subsubsections": ["研究背景"], "min_subsubsection_count": 1},
        "quality": {"high_risk_examples": ["国际领先"], "avoid_commands": ["\\\\section"]},
        "word_count": {"target": 4000, "tolerance": 200, "mode": "cjk_only"},
        "ai": {"enabled": False},
        "prompts": {},
        "terminology": {"dimensions": {}},
    }
    assert validate_config(skill_root=tmp_path, config=cfg) == []


def test_load_config_raises_on_invalid_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skill_root = Path(__file__).resolve().parents[1]
    override = tmp_path / "override.yaml"
    override.write_text("structure:\n  min_subsubsection_count: 0\n", encoding="utf-8")

    monkeypatch.setenv("NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE", "1")
    with pytest.raises(ValueError):
        load_config(skill_root, override_path=str(override), load_user_override=False)
