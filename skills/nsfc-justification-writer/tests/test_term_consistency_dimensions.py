#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from core.term_consistency import CrossChapterValidator


def test_cross_chapter_validator_supports_dimensions(tmp_path: Path) -> None:
    f1 = tmp_path / "a.tex"
    f2 = tmp_path / "b.tex"
    f1.write_text("患者 AUC\n", encoding="utf-8")
    f2.write_text("病例 准确率\n", encoding="utf-8")

    terminology = {
        "dimensions": {
            "研究对象": {"研究对象": ["患者", "病例"]},
            "指标": {"AUC": ["AUC"], "准确率": ["准确率"]},
        }
    }
    v = CrossChapterValidator(files={"章1": f1, "章2": f2}, terminology_config=terminology)
    md = v.to_markdown()
    assert "## 研究对象" in md
    assert "## 指标" in md

