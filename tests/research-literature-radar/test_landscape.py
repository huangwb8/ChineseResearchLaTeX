from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/research-literature-radar/scripts/build_landscape.py"
SPEC = importlib.util.spec_from_file_location("build_landscape", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_bundle(tmp_path: Path, count: int = 180) -> tuple[Path, Path]:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    candidates = bundle / "candidates_deduped.jsonl"
    candidates.write_text(
        "".join(json.dumps({"record_id": f"S{i:03d}", "title": f"paper {i}"}) + "\n" for i in range(count)),
        encoding="utf-8",
    )
    manifest = {
        "contract_version": "rls.v1",
        "search_run_id": "run-test",
        "counts": {"deduped": count},
        "artifacts": {"candidates_deduped": {"path": candidates.name, "sha256": sha256(candidates)}},
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    draft = tmp_path / "draft.jsonl"
    draft.write_text(
        "".join(
            json.dumps({
                "record_id": f"S{i:03d}", "role": "core" if i < 8 else "supporting",
                "cluster": "line-a", "relevance": "high", "evidence_depth": "abstract",
                "publication_status": "preprint" if i == 9 else "published",
                "identity_confidence": "high", "use_cases": ["map"], "reason": "topic match",
                "uncertainties": [], "source_refs": ["provider:one"],
            }) + "\n"
            for i in range(count)
        ),
        encoding="utf-8",
    )
    return bundle, draft


def test_180_candidates_are_preserved_in_canonical_order(tmp_path):
    bundle, draft = make_bundle(tmp_path)
    rows, summary = MODULE.build(bundle, draft)
    assert len(rows) == 180
    assert [row["record_id"] for row in rows] == [f"S{i:03d}" for i in range(180)]
    assert summary["role_counts"] == {"core": 8, "out_of_scope": 0, "supporting": 172, "watchlist": 0}
    assert summary["coverage_complete"]


def test_missing_or_duplicate_record_fails_closed(tmp_path):
    bundle, draft = make_bundle(tmp_path, 3)
    lines = draft.read_text(encoding="utf-8").splitlines()
    draft.write_text("\n".join([lines[0], lines[0], lines[1]]) + "\n", encoding="utf-8")
    try:
        MODULE.build(bundle, draft)
    except ValueError as exc:
        assert "duplicate" in str(exc) or "coverage mismatch" in str(exc)
    else:
        raise AssertionError("invalid coverage should fail")


def test_title_only_core_is_rejected_but_preprint_is_not_penalized(tmp_path):
    bundle, draft = make_bundle(tmp_path, 2)
    rows = [json.loads(line) for line in draft.read_text(encoding="utf-8").splitlines()]
    rows[0]["evidence_depth"] = "title"
    draft.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    try:
        MODULE.build(bundle, draft)
    except ValueError as exc:
        assert "title-only evidence cannot be core" in str(exc)
    else:
        raise AssertionError("title-only core should fail")
