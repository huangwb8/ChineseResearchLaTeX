#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
from pathlib import Path

from core.example_matcher import recommend_examples


def test_recommend_examples_prefers_cs_for_privacy_query(tmp_path: Path) -> None:
    skill_root = tmp_path / "skill"
    ex_dir = skill_root / "examples" / "cs"
    ex_dir.mkdir(parents=True, exist_ok=True)
    (ex_dir / "example_001.tex").write_text(
        "\\subsubsection{研究背景}\n隐私 联邦学习 推理 时延\n",
        encoding="utf-8",
    )
    (ex_dir / "example_001.metadata.yaml").write_text(
        "category: cs\nkeywords: [隐私, 联邦学习, 推理]\ndescription: 测试示例\n",
        encoding="utf-8",
    )

    matches = recommend_examples(skill_root=skill_root, query="联邦学习 隐私 推理", top_k=1)
    assert matches
    assert matches[0].category == "cs"

    if importlib.util.find_spec("yaml") is not None:
        assert matches[0].description == "测试示例"

