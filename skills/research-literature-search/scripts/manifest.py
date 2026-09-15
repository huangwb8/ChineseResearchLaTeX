#!/usr/bin/env python3
"""Manifest creation and safe artifact hashing for search bundles."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from candidate_schema import SCHEMA_VERSION
from rls_contract import CONTRACT_VERSION


SEARCH_SKILL_VERSION = "1.0.4"
ARTIFACT_NAMES = (
    "candidates_raw",
    "candidates_normalized",
    "candidates_deduped",
    "provenance",
    "dedupe_map",
    "search_log",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(path: Path, root: Path) -> str:
    resolved_root = Path(root).resolve()
    resolved = Path(path).resolve()
    try:
        rel = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"artifact path escapes bundle root: {path}") from exc
    if rel == Path(".") or any(part in {"", ".", ".."} for part in rel.parts):
        raise ValueError(f"artifact path is not a safe relative path: {path}")
    return rel.as_posix()


def artifact_entry(path: Path, root: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    return {"path": safe_relative(path, root), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def build_manifest(
    bundle_dir: Path,
    *,
    topic: str,
    domain: str | None,
    query_plan: Mapping[str, Any],
    filters: Mapping[str, Any],
    provider_policy: Mapping[str, Any],
    attempts: list[Mapping[str, Any]],
    counts: Mapping[str, int],
    truncation: Mapping[str, Any],
    dedupe: Mapping[str, Any],
    abstract_enrichment: Mapping[str, Any],
    status: str,
    failure_code: str | None,
    warnings: list[str],
    artifacts: Mapping[str, Path],
    search_run_id: str,
    cache: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(bundle_dir).resolve()
    artifact_payload: dict[str, Any] = {}
    for name in ARTIFACT_NAMES:
        path = artifacts.get(name)
        if path is None:
            continue
        artifact_payload[name] = artifact_entry(Path(path), root)
    query_items = list(query_plan.get("items") or query_plan.get("queries") or [])
    payload: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "candidate_schema_version": SCHEMA_VERSION,
        "search_skill_version": SEARCH_SKILL_VERSION,
        "search_run_id": search_run_id,
        "topic": topic,
        "domain": domain,
        "topic_hash": hashlib.sha256(topic.encode("utf-8")).hexdigest(),
        "query_plan": {
            "source": query_plan.get("source"),
            "sha256": query_plan.get("sha256"),
            "requested_count": int(query_plan.get("requested_count", len(query_items))),
            "accepted_count": int(query_plan.get("accepted_count", len(query_items))),
            "items": query_items,
        },
        "filters": dict(filters),
        "provider_policy": dict(provider_policy),
        "attempts": [dict(item) for item in attempts],
        "counts": {"raw": 0, "normalized": 0, "deduped": 0, "failed": 0, "dropped": 0, **dict(counts)},
        "truncation": {"applied": False, "limit": None, "dropped_count": 0, **dict(truncation)},
        "dedupe": dict(dedupe),
        "abstract_enrichment": dict(abstract_enrichment),
        "artifacts": artifact_payload,
        "status": status,
        "failure_code": failure_code,
        "warnings": sorted({str(item) for item in warnings if str(item).strip()}),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cache": dict(cache or {"mode": "disabled"}),
    }
    return payload


def manifest_sha256(path: Path) -> str:
    return sha256_file(path)
