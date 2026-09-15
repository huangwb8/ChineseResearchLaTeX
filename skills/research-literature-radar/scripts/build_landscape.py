#!/usr/bin/env python3
"""Validate and finalize an AI-authored landscape against an RLS bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROLES = {"core", "supporting", "watchlist", "out_of_scope"}
RELEVANCE = {"high", "medium", "low", "none", "uncertain"}
EVIDENCE_DEPTHS = {"title", "abstract", "fulltext"}
PUBLICATION_STATUSES = {"preprint", "published", "unknown"}
IDENTITY_CONFIDENCE = {"high", "medium", "low", "conflict"}
SCHEMA = "research-literature-landscape-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{line_no}: invalid JSON ({exc})") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path.name}:{line_no}: record must be an object")
        rows.append(value)
    return rows


def safe_artifact(bundle: Path, manifest: dict[str, Any], name: str) -> Path:
    entry = (manifest.get("artifacts") or {}).get(name)
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
        raise ValueError(f"manifest missing artifact: {name}")
    relative = Path(entry["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe artifact path: {name}")
    path = (bundle / relative).resolve()
    if not path.is_relative_to(bundle) or not path.is_file():
        raise ValueError(f"artifact unavailable: {name}")
    if sha256_file(path) != entry.get("sha256"):
        raise ValueError(f"artifact hash mismatch: {name}")
    return path


def validate_row(row: dict[str, Any]) -> list[str]:
    record_id = row.get("record_id")
    errors: list[str] = []
    for field, allowed in (
        ("role", ROLES),
        ("relevance", RELEVANCE),
        ("evidence_depth", EVIDENCE_DEPTHS),
        ("publication_status", PUBLICATION_STATUSES),
        ("identity_confidence", IDENTITY_CONFIDENCE),
    ):
        if row.get(field) not in allowed:
            errors.append(f"{record_id}: invalid {field}={row.get(field)!r}")
    if not isinstance(row.get("cluster"), str) or not row["cluster"].strip():
        errors.append(f"{record_id}: cluster is required")
    if not isinstance(row.get("reason"), str) or not row["reason"].strip():
        errors.append(f"{record_id}: reason is required")
    for field in ("use_cases", "uncertainties", "source_refs"):
        value = row.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"{record_id}: {field} must be a string array")
    if row.get("evidence_depth") == "title" and row.get("role") == "core":
        errors.append(f"{record_id}: title-only evidence cannot be core; use watchlist")
    if row.get("publication_status") == "preprint" and row.get("relevance") == "none" and row.get("reason") == "preprint":
        errors.append(f"{record_id}: preprint status cannot be the relevance reason")
    return errors


def build(bundle: Path, draft_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bundle = bundle.expanduser().resolve()
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("contract_version") != "rls.v1":
        raise ValueError("unsupported search manifest contract")
    candidates_path = safe_artifact(bundle, manifest, "candidates_deduped")
    candidates = read_jsonl(candidates_path)
    draft = read_jsonl(draft_path)
    candidate_ids = [row.get("record_id") for row in candidates]
    draft_ids = [row.get("record_id") for row in draft]
    if any(not isinstance(value, str) or not value for value in candidate_ids):
        raise ValueError("canonical candidates contain an empty record_id")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("canonical candidates contain duplicate record_id values")
    if len(draft_ids) != len(set(draft_ids)):
        raise ValueError("landscape draft contains duplicate record_id values")
    missing = sorted(set(candidate_ids) - set(draft_ids))
    extra = sorted(set(draft_ids) - set(candidate_ids))
    if missing or extra:
        raise ValueError(f"landscape coverage mismatch: missing={missing} extra={extra}")
    by_id = {row["record_id"]: row for row in draft}
    output: list[dict[str, Any]] = []
    errors: list[str] = []
    for rank, candidate in enumerate(candidates, 1):
        row = dict(by_id[candidate["record_id"]])
        row["schema"] = SCHEMA
        row["canonical_rank"] = rank
        errors.extend(validate_row(row))
        output.append(row)
    if errors:
        raise ValueError("; ".join(errors))
    expected_count = int((manifest.get("counts") or {}).get("deduped", -1))
    if expected_count != len(output):
        raise ValueError(f"manifest count mismatch: expected={expected_count} actual={len(output)}")
    counts = Counter(row["role"] for row in output)
    summary = {
        "schema": SCHEMA,
        "search_run_id": manifest.get("search_run_id"),
        "search_manifest_sha256": sha256_file(manifest_path),
        "canonical_candidates_sha256": sha256_file(candidates_path),
        "canonical_count": len(output),
        "role_counts": {role: counts.get(role, 0) for role in sorted(ROLES)},
        "coverage_complete": sum(counts.values()) == len(output),
    }
    return output, summary


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path, help="research-literature-search bundle")
    parser.add_argument("--draft", required=True, type=Path, help="AI-authored landscape JSONL")
    parser.add_argument("--output", required=True, type=Path, help="final literature-landscape.jsonl")
    parser.add_argument("--summary", required=True, type=Path, help="landscape-summary.json")
    args = parser.parse_args()
    try:
        rows, summary = build(args.bundle, args.draft.expanduser().resolve())
        atomic_write(args.output.expanduser().resolve(), "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        atomic_write(args.summary.expanduser().resolve(), json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"landscape error: {exc}")
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
