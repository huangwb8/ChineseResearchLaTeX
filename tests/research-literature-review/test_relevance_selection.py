from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/research-literature-review/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("select_references", SCRIPTS / "select_references.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def paper(index: int, score: float, *, role: str = "supporting", abstract: bool = True, preprint: bool = False):
    return {
        "record_id": f"S{index:03d}",
        "title": f"paper {index}",
        "year": 2026,
        "score": score,
        "abstract": ("evidence " * 20) if abstract else "",
        "evidence_role": role,
        "publication_status": "preprint" if preprint else "published",
    }


def select(rows, *, purpose="standard-review"):
    return MODULE._select_papers(
        rows,
        min_refs=80,
        max_refs=150,
        target_refs=115,
        high_score_min=0.6,
        high_score_max=0.8,
        min_abstract_chars=80,
        min_score=5.0,
        purpose=purpose,
    )


def test_low_relevance_rows_do_not_fill_115_target():
    rows = [paper(i, 8.0) for i in range(65)] + [paper(i + 65, 3.0) for i in range(50)]
    selected, rationale = select(rows)
    assert len(selected) == 65
    assert rationale["target_shortfall"] == 50
    assert rationale["score_distribution"]["low_score_count"] == 0
    assert rationale["stop_reason"] == "eligible_evidence_exhausted"


def test_seventeen_qualified_papers_are_a_valid_soft_target_result():
    selected, rationale = select([paper(i, 7.0) for i in range(17)])
    assert len(selected) == 17
    assert rationale["qualified_candidates"] == 17
    assert "qualified_references_below_soft_target:98" in rationale["evidence_gaps"]


def test_novelty_check_keeps_single_source_preprint_neighbor_for_enrichment():
    rows = [paper(1, 9.0, role="direct-neighbor", abstract=False, preprint=True), paper(2, 8.0)]
    selected, rationale = select(rows, purpose="novelty-check")
    assert selected[0]["record_id"] == "S001"
    assert selected[0]["publication_status"] == "preprint"
    assert selected[0]["do_not_cite"] is True
    assert "title_only_records_require_enrichment" in rationale["evidence_gaps"]
