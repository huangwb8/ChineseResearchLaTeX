#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

import pytest

from core.config_loader import load_config
from core.errors import QualityGateError
from core.hybrid_coordinator import HybridCoordinator


def _write_min_project(tmp_path: Path, *, extra_phrase_in_other_section: bool = False) -> None:
    (tmp_path / "extraTex").mkdir()
    tex = (
        "\\subsubsection{研究背景}\n"
        + ("国际领先\n" if extra_phrase_in_other_section else "中文\n")
        + "\\subsubsection{国内外研究现状}\n中文\n"
        + "\\subsubsection{现有研究的局限性}\n中文\n"
        + "\\subsubsection{研究切入点}\n中文\n"
    )
    (tmp_path / "extraTex" / "1.1.立项依据.tex").write_text(tex, encoding="utf-8")


def test_apply_section_blocks_on_strict_quality(tmp_path: Path) -> None:
    _write_min_project(tmp_path)
    skill_root = Path(__file__).resolve().parents[1]
    cfg = load_config(skill_root, load_user_override=False)
    coord = HybridCoordinator(skill_root=skill_root, config=cfg)

    with pytest.raises(QualityGateError):
        coord.apply_section_body(
            project_root=tmp_path,
            title="国内外研究现状",
            new_body="国际领先\\section{坏}\n",
            allow_missing_citations=True,
            strict_quality=True,
        )


def test_apply_section_strict_quality_only_checks_new_body(tmp_path: Path) -> None:
    _write_min_project(tmp_path, extra_phrase_in_other_section=True)
    skill_root = Path(__file__).resolve().parents[1]
    cfg = load_config(skill_root, load_user_override=False)
    coord = HybridCoordinator(skill_root=skill_root, config=cfg)

    result = coord.apply_section_body(
        project_root=tmp_path,
        title="国内外研究现状",
        new_body="这是新增正文，不包含危险命令。\n",
        allow_missing_citations=True,
        strict_quality=True,
    )
    assert result.changed is True

