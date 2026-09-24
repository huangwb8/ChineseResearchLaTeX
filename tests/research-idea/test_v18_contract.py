"""v18 审计闭环契约的确定性回归。"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/research-idea/scripts"))

from edge_rules import applicability_errors  # noqa: E402


def test_edge_applicability_is_single_valued():
    assert applicability_errors(
        "bensz.research-ideation.review", "bensz.research-ideation.reporting",
        [{"verifier_id": "bensz.research.hypothesis-merit", "facts": {"applicability": "applicable"}}],
    )
    assert applicability_errors(
        "bensz.research-ideation.review", "bensz.research-ideation.reporting",
        [{"verifier_id": "bensz.research.hypothesis-merit", "facts": {"applicability": "not_applicable"}}],
    ) == []
