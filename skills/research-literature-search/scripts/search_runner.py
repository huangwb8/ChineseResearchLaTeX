#!/usr/bin/env python3
"""CLI and library entry point for ``research-literature-search``.

The runner owns retrieval, normalization, provenance, canonical deduplication and
the manifest contract.  Relevance scoring and review writing deliberately stay
outside this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from candidate_schema import normalize_record
    from dedupe_papers import dedupe_records
    from manifest import ARTIFACT_NAMES, SEARCH_SKILL_VERSION, build_manifest, write_json
    from normalize_papers import write_jsonl
    from query_contract import QueryInputError, load_query_plan
    from rls_contract import CONTRACT_VERSION
    from validate_bundle import validate_bundle
    from providers import search_crossref, search_openalex, search_semantic_scholar
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from candidate_schema import normalize_record
    from dedupe_papers import dedupe_records
    from manifest import ARTIFACT_NAMES, SEARCH_SKILL_VERSION, build_manifest, write_json
    from normalize_papers import write_jsonl
    from query_contract import QueryInputError, load_query_plan
    from rls_contract import CONTRACT_VERSION
    from validate_bundle import validate_bundle
    from providers import search_crossref, search_openalex, search_semantic_scholar


ProviderFn = Callable[..., list[dict[str, Any]]]
DEFAULT_PROVIDER_ORDER = ["mcp", "openalex", "semantic_scholar", "crossref", "duckduckgo"]
SUPPORTED_PROVIDERS = {"openalex", "semantic_scholar", "crossref"}
RETRIEVAL_STRATEGY = "priority-fallback-topup"
TOPUP_THRESHOLD = 0.7
PREPRINT_PROFILES = {
    "computer_science": {"include_preprints": True, "preprint_priority": "high", "published_version_preferred": True},
    "mathematics": {"include_preprints": True, "preprint_priority": "high", "published_version_preferred": True},
    "biology": {"include_preprints": True, "preprint_priority": "medium", "published_version_preferred": True},
    "medicine": {"include_preprints": True, "preprint_priority": "low", "published_version_preferred": True},
    "general": {"include_preprints": True, "preprint_priority": "medium", "published_version_preferred": True},
}


def resolve_preprint_profile(domain: str | None, profile: str = "auto") -> tuple[str, dict[str, Any]]:
    """Resolve a conservative domain policy without deleting preprints."""
    requested = (profile or "auto").strip().lower().replace("-", "_")
    if requested == "auto":
        text = (domain or "").lower()
        if any(token in text for token in ("computer", "software", "informatics", "cs")):
            requested = "computer_science"
        elif any(token in text for token in ("math", "mathematics", "theorem")):
            requested = "mathematics"
        elif any(token in text for token in ("medicine", "clinical", "medical", "health")):
            requested = "medicine"
        elif any(token in text for token in ("biology", "biomedical", "life science", "molecular")):
            requested = "biology"
        else:
            requested = "general"
    if requested not in PREPRINT_PROFILES:
        raise ValueError(f"unknown preprint domain profile: {profile}")
    return requested, dict(PREPRINT_PROFILES[requested])


def _safe_error(exc: BaseException) -> str:
    """Return a bounded, credential-free provider error for audit logs."""
    message = str(exc).replace("\n", " ").strip()
    message = re.sub(r"(?i)(api[_-]?key|token|password|secret)=([^&\s]+)", r"\1=[redacted]", message)
    message = re.sub(r"(?i)bearer\s+[^\s]+", "Bearer [redacted]", message)
    message = re.sub(r"https?://[^\s]+", "<url>", message)
    return message[:500] or exc.__class__.__name__


def _policy_fingerprint(order: list[str], options: Mapping[str, Any]) -> str:
    safe = {
        key: value for key, value in options.items()
        if key.lower() not in {"api_key", "apikey", "token", "password", "secret", "mailto"}
    }
    payload = json.dumps({"provider_order": order, "options": safe}, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _failed_result(*, topic: str, output_dir: Path, code: str, warning: str) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "candidate_schema_version": "rls.paper.v1",
        "search_skill_version": SEARCH_SKILL_VERSION,
        "search_run_id": uuid.uuid4().hex,
        "topic": topic,
        "status": "failed",
        "failure_code": code,
        "warnings": [warning],
        "output_dir": str(Path(output_dir).expanduser()),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def _safe_bundle_dir(path: Path, scope_root: Path | None) -> Path:
    root = Path(path).expanduser().resolve()
    if scope_root is not None:
        scope = Path(scope_root).expanduser().resolve()
        try:
            root.relative_to(scope)
        except ValueError as exc:
            raise ValueError(f"output path escapes scope root: {root}") from exc
    root.mkdir(parents=True, exist_ok=True)
    return root


def _provider_registry(overrides: Mapping[str, ProviderFn] | None = None) -> dict[str, ProviderFn]:
    return {"openalex": search_openalex, "semantic_scholar": search_semantic_scholar, "crossref": search_crossref, **dict(overrides or {})}


def _raw_envelope(raw: dict[str, Any], *, provider: str, query_id: str, rank: int) -> dict[str, Any]:
    # Keep enough information to locate an input without persisting an entire API response.
    fields = {key: raw.get(key) for key in ("id", "title", "display_name", "doi", "year", "publication_year", "venue", "journal", "url", "abstract", "externalIds") if raw.get(key) is not None}
    return {"provider": provider, "provider_record_id": raw.get("id") or raw.get("DOI") or raw.get("doi"), "query_id": query_id, "rank": rank, "fields": fields}


def _filter_record(record: dict[str, Any], filters: Mapping[str, Any]) -> bool:
    year = record.get("year")
    if filters.get("min_year") is not None and (year is None or year < int(filters["min_year"])):
        return False
    if filters.get("max_year") is not None and (year is None or year > int(filters["max_year"])):
        return False
    if filters.get("exclude_preprints") and bool((record.get("publication") or {}).get("is_preprint")):
        return False
    allowed_types = filters.get("publication_types")
    if allowed_types:
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]
        kind = (record.get("publication") or {}).get("publication_type")
        if not kind or kind not in set(allowed_types):
            return False
    language = filters.get("language") or filters.get("languages")
    if language:
        allowed = {str(item).lower() for item in (language if isinstance(language, (list, tuple, set)) else [language])}
        actual = str((record.get("publication") or {}).get("language") or record.get("language") or "").lower()
        if not actual or actual not in allowed:
            return False
    if filters.get("open_access") is not None:
        actual_oa = (record.get("publication") or {}).get("is_open_access")
        if actual_oa is None:
            actual_oa = record.get("is_open_access")
        if bool(actual_oa) != bool(filters.get("open_access")):
            return False
    return True


def run_search(
    *,
    topic: str,
    query_file: Path,
    output_dir: Path,
    domain: str | None = None,
    filters: Mapping[str, Any] | None = None,
    provider_order: list[str] | None = None,
    max_results_per_query: int = 50,
    max_total: int = 500,
    fallback_enabled: bool = True,
    scope_root: Path | None = None,
    provider_functions: Mapping[str, ProviderFn] | None = None,
    provider_options: Mapping[str, Any] | None = None,
    query_source: str | None = None,
    preprint_profile: str = "auto",
) -> dict[str, Any]:
    try:
        bundle = _safe_bundle_dir(output_dir, scope_root)
    except (OSError, ValueError) as exc:
        # Do not create anything outside the caller's scope.  Returning a
        # structured failure lets both the CLI and orchestrators report a
        # stable failure_code without leaking a traceback.
        return _failed_result(topic=topic, output_dir=output_dir, code="path_violation", warning=_safe_error(exc))
    filters = dict(filters or {})
    try:
        resolved_profile, preprint_policy = resolve_preprint_profile(domain, preprint_profile)
    except ValueError as exc:
        return _failed_result(topic=topic, output_dir=output_dir, code="contract_invalid", warning=_safe_error(exc))
    order = list(dict.fromkeys(provider_order or DEFAULT_PROVIDER_ORDER))
    if not order:
        order = list(DEFAULT_PROVIDER_ORDER)
    registry = _provider_registry(provider_functions)
    options = dict(provider_options or {})
    policy_fingerprint = _policy_fingerprint(order, options)
    try:
        if max_results_per_query < 1 or max_total < 1:
            raise ValueError("max_results_per_query and max_total must be >= 1")
    except (TypeError, ValueError) as exc:
        result = _failed_result(topic=topic, output_dir=output_dir, code="contract_invalid", warning=_safe_error(exc))
        write_json(bundle / "manifest.json", result)
        return result
    warnings: list[str] = []
    attempts: list[dict[str, Any]] = []
    empty_records = 0
    invalid_records = 0
    normalization_failed = 0
    run_id = uuid.uuid4().hex
    paths = {name: bundle / {"candidates_raw": "candidates_raw.jsonl", "candidates_normalized": "candidates_normalized.jsonl", "candidates_deduped": "candidates_deduped.jsonl", "provenance": "provenance.jsonl", "dedupe_map": "dedupe_map.json", "search_log": "search_log.json"}[name] for name in ARTIFACT_NAMES}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        plan = load_query_plan(query_file, min_queries=int(options.pop("min_queries", 5)), max_queries=int(options.pop("max_queries", 25)))
    except QueryInputError as exc:
        # Still emit an inspectable failed manifest with empty artifacts.
        for name, path in paths.items():
            if name.endswith("jsonl"):
                path.write_text("", encoding="utf-8")
            elif name == "dedupe_map":
                write_json(path, {"schema_version": "rls.dedupe.v1", "edges": []})
            else:
                write_json(path, {"search_mode": "multi_query", "error": str(exc)})
        failed = build_manifest(bundle, topic=topic, domain=domain, query_plan={"source": str(query_file), "sha256": None, "requested_count": 0, "accepted_count": 0, "items": []}, filters=filters, provider_policy={"requested_order": order, "effective_order": order}, attempts=[], counts={"failed": 1}, truncation={}, dedupe={}, abstract_enrichment={"mode": "disabled"}, status="failed", failure_code="contract_invalid", warnings=[str(exc)], artifacts=paths, search_run_id=run_id)
        write_json(bundle / "manifest.json", failed)
        return failed

    raw_rows: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    query_logs: list[dict[str, Any]] = []
    for query in plan.queries:
        query_id = query["query_id"]
        text = query["query"]
        query_attempts: list[dict[str, Any]] = []
        hits: list[tuple[str, dict[str, Any]]] = []
        # Compatibility policy: priority order with fallback/top-up, matching
        # the pre-split review pipeline rather than a full provider union.
        for provider in order:
            if provider not in SUPPORTED_PROVIDERS:
                item = {"provider": provider, "status": "skipped", "results": 0, "reason": "host tool required"}
                query_attempts.append(item)
                attempts.append({"query_id": query_id, **item})
                warnings.append(f"{query_id}/{provider}: skipped ({item['reason']})")
                continue
            fn = registry.get(provider)
            if fn is None:
                item = {"provider": provider, "status": "skipped", "results": 0, "reason": "adapter unavailable"}
                query_attempts.append(item)
                attempts.append({"query_id": query_id, **item})
                warnings.append(f"{query_id}/{provider}: skipped ({item['reason']})")
                continue
            if hits and not fallback_enabled:
                break
            try:
                kwargs = {"max_results": max_results_per_query - len(hits), **options}
                if filters.get("min_year") is not None:
                    kwargs["min_year"] = filters["min_year"]
                if filters.get("max_year") is not None:
                    kwargs["max_year"] = filters["max_year"]
                result = fn(text, **kwargs)
                if result is None:
                    item = {"provider": provider, "status": "empty", "results": 0, "empty_records": 1, "invalid_records": 0}
                    query_attempts.append(item)
                    attempts.append({"query_id": query_id, **item})
                    empty_records += 1
                    warnings.append(f"{query_id}/{provider}: provider returned an empty record result")
                    continue
                if not isinstance(result, (list, tuple)):
                    raise TypeError(f"provider returned {type(result).__name__}, expected list")
                valid_result: list[dict[str, Any]] = []
                empty_count = 0
                invalid_count = 0
                for candidate in result:
                    if candidate is None:
                        empty_count += 1
                    elif isinstance(candidate, dict):
                        valid_result.append(candidate)
                    else:
                        invalid_count += 1
                empty_records += empty_count
                invalid_records += invalid_count
                item_status = "partial" if empty_count or invalid_count else "success"
                item = {
                    "provider": provider,
                    "status": item_status,
                    "results": len(valid_result),
                    "empty_records": empty_count,
                    "invalid_records": invalid_count,
                }
                query_attempts.append(item)
                attempts.append({"query_id": query_id, **item})
                if empty_count or invalid_count:
                    details = []
                    if empty_count:
                        details.append(f"{empty_count} empty")
                    if invalid_count:
                        details.append(f"{invalid_count} invalid")
                    warnings.append(f"{query_id}/{provider}: skipped " + ", ".join(details) + " record(s)")
                hits.extend((provider, row) for row in valid_result)
                # OpenAlex is the main source; only supplement if clearly below target.
                if len(hits) >= max(5, int(max_results_per_query * TOPUP_THRESHOLD)):
                    break
            except Exception as exc:  # noqa: BLE001
                item = {"provider": provider, "status": "error", "results": 0, "error": _safe_error(exc)}
                query_attempts.append(item)
                attempts.append({"query_id": query_id, **item})
                warnings.append(f"{query_id}/{provider}: {exc}")
        for rank, (provider, raw) in enumerate(hits[:max_results_per_query], 1):
            raw_rows.append(_raw_envelope(raw, provider=provider, query_id=query_id, rank=rank))
            try:
                record = normalize_record(raw, provider=provider, query_id=query_id, rank=rank, fallback_index=len(normalized) + 1)
            except ValueError as exc:
                normalization_failed += 1
                warnings.append(f"{query_id}/{provider}/rank{rank}: normalization failed: {exc}")
                continue
            if _filter_record(record, filters):
                normalized.append(record)
        query_logs.append({"query_id": query_id, "query": text, "rationale": query.get("rationale", ""), "returned": len(hits), "attempts": query_attempts})

    dedupe_params = {"title_similarity_threshold": float(options.pop("title_similarity", .92)), "token_jaccard_threshold": float(options.pop("token_jaccard", .80)), "year_window": int(options.pop("year_window", 1))}
    canonical, edges = dedupe_records(normalized, title_similarity=dedupe_params["title_similarity_threshold"], token_threshold=dedupe_params["token_jaccard_threshold"], year_window=dedupe_params["year_window"])
    dropped = 0
    if max_total > 0 and len(canonical) > max_total:
        dropped = len(canonical) - max_total
        canonical = canonical[:max_total]
        warnings.append(f"候选池达到总量上限，截断 {dropped} 条")
    write_jsonl(paths["candidates_raw"], raw_rows)
    write_jsonl(paths["candidates_normalized"], normalized)
    write_jsonl(paths["candidates_deduped"], canonical)
    provenance_rows: list[dict[str, Any]] = []
    for record in canonical:
        for source in record.get("sources") or []:
            provenance_rows.append({"record_id": record.get("record_id"), **source, "query_matches": record.get("query_matches", [])})
    write_jsonl(paths["provenance"], sorted(provenance_rows, key=lambda item: (str(item.get("record_id")), str(item.get("provider")), int(item.get("rank") or 0))))
    write_json(paths["dedupe_map"], {"schema_version": "rls.dedupe.v1", "input_count": len(normalized), "output_count": len(canonical), "merged_count": len(edges), "edges": edges})
    status = "success" if canonical and not warnings else ("partial_success" if canonical else "failed")
    failure_code = None if canonical else ("no_valid_candidates" if empty_records or invalid_records or normalization_failed else "no_provider")
    log = {"search_mode": "multi_query", "query_source": query_source or str(query_file), "requested_query_count": plan.requested_count, "accepted_query_count": plan.accepted_count, "fallback_reason": "", "total_returned": len(raw_rows), "total_unique": len(canonical), "empty_records": empty_records, "invalid_records": invalid_records, "normalization_failed": normalization_failed, "queries": query_logs, "attempts": attempts, "warnings": sorted(set(warnings))}
    log["retrieval_strategy"] = RETRIEVAL_STRATEGY
    log["topup_threshold"] = TOPUP_THRESHOLD
    write_json(paths["search_log"], log)
    manifest = build_manifest(bundle, topic=topic, domain=domain, query_plan={"source": plan.source, "sha256": plan.sha256, "requested_count": plan.requested_count, "accepted_count": plan.accepted_count, "items": plan.queries}, filters=filters, provider_policy={"requested_order": order, "effective_order": order, "fallback_enabled": fallback_enabled, "config_fingerprint": policy_fingerprint, "preprint_profile": resolved_profile, "preprint_policy": preprint_policy}, attempts=attempts, counts={"raw": len(raw_rows), "normalized": len(normalized), "deduped": len(canonical), "failed": sum(1 for item in attempts if item["status"] == "error"), "empty_records": empty_records, "invalid_records": invalid_records, "normalization_failed": normalization_failed, "dropped": dropped}, truncation={"applied": dropped > 0, "limit": max_total, "dropped_count": dropped}, dedupe={"parameters": dedupe_params, "map_path": "dedupe_map.json", "canonical_merges": len(edges)}, abstract_enrichment={"mode": "disabled", "attempted": 0, "filled": 0, "missing": sum(1 for item in canonical if item.get("abstract_status") == "missing")}, status=status, failure_code=failure_code, warnings=warnings, artifacts=paths, search_run_id=run_id, cache={"mode": "disabled"})
    manifest["provider_policy"]["retrieval_strategy"] = RETRIEVAL_STRATEGY
    manifest["provider_policy"]["topup_threshold"] = TOPUP_THRESHOLD
    write_json(bundle / "manifest.json", manifest)
    return manifest


def enrich_abstracts(input_path: Path, output_path: Path, *, max_papers: int = 200, min_chars: int = 80, timeout: float = 3, fetchers: Mapping[str, ProviderFn] | None = None) -> dict[str, Any]:
    rows = _read_jsonl(input_path)
    output = [dict(row) for row in rows]
    attempted = filled = 0
    registry = _provider_registry(fetchers)
    for row in output[: max_papers if max_papers > 0 else len(output)]:
        abstract = row.get("abstract")
        if isinstance(abstract, str) and len(abstract.strip()) >= min_chars:
            row["abstract_status"] = "present"
            continue
        attempted += 1
        row["abstract_status"] = "attempted"
        provenance: dict[str, Any] = {"method": "post_selection", "attempts": []}
        title = str(row.get("title") or "")
        doi = str(row.get("doi") or (row.get("identifiers") or {}).get("doi") or "")
        for source, query in (("crossref", doi), ("semantic_scholar", title), ("openalex", title)):
            if not query or source not in registry:
                continue
            try:
                hits = registry[source](query, max_results=5, timeout=timeout) or []
                provenance["attempts"].append({"source": source, "status": "success", "count": len(hits)})
                found = next((item.get("abstract") for item in hits if isinstance(item, dict) and isinstance(item.get("abstract"), str) and len(item["abstract"].strip()) >= min_chars), None)
                if found:
                    row["abstract"] = found.strip()
                    row["abstract_status"] = "present"
                    row["abstract_provenance"] = {"source": source, "method": "post_selection", "attempts": len(provenance["attempts"])}
                    filled += 1
                    break
            except Exception as exc:  # noqa: BLE001
                provenance["attempts"].append({"source": source, "status": "error", "error": _safe_error(exc)})
        if row.get("abstract_status") != "present":
            row["abstract_status"] = "missing"
            row["abstract_provenance"] = provenance
        row.setdefault("quality_warnings", [])
        if row.get("abstract_status") == "missing" and "missing_abstract" not in row["quality_warnings"]:
            row["quality_warnings"].append("missing_abstract")
    _write_jsonl(output_path, output)
    summary = {"mode": "selected", "attempted": attempted, "filled": filled, "missing": sum(1 for row in output if row.get("abstract_status") == "missing"), "min_abstract_chars": min_chars, "max_papers_total": max_papers}
    write_json(output_path.with_suffix(output_path.suffix + ".summary.json"), summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or validate research-literature-search bundles")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--topic", required=True)
    run.add_argument("--domain")
    run.add_argument("--query-file", "--queries", dest="query_file", required=True, type=Path)
    run.add_argument("--output-dir", "--output", dest="output_dir", required=True, type=Path)
    run.add_argument("--scope-root", type=Path)
    run.add_argument("--max-results-per-query", type=int, default=50)
    run.add_argument("--max-total", type=int, default=500)
    run.add_argument("--min-year", type=int)
    run.add_argument("--max-year", type=int)
    run.add_argument("--exclude-preprints", action="store_true")
    run.add_argument("--provider-order", "--providers", help="逗号分隔的 provider 顺序")
    run.add_argument("--domain-profile", default="auto", help="preprint 领域政策：auto/computer_science/mathematics/biology/medicine/general")
    run.add_argument("--publication-type", action="append", dest="publication_types", default=[])
    run.add_argument("--language", action="append", dest="languages", default=[])
    run.add_argument("--open-access", action="store_true", dest="open_access")
    run.add_argument("--no-open-access-filter", action="store_false", dest="open_access_filter")
    run.set_defaults(open_access_filter=False)
    run.add_argument("--no-fallback", action="store_true")
    run.add_argument("--min-queries", type=int, default=5)
    run.add_argument("--max-queries", type=int, default=25)
    run.add_argument("--query-source", default="direct_cli")
    enrich = sub.add_parser("enrich-abstracts")
    enrich.add_argument("--input", required=True, type=Path)
    enrich.add_argument("--output", required=True, type=Path)
    enrich.add_argument("--max-papers", type=int, default=200)
    enrich.add_argument("--min-abstract-chars", type=int, default=80)
    validate = sub.add_parser("validate")
    validate.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "run":
        filters = {"min_year": args.min_year, "max_year": args.max_year, "exclude_preprints": args.exclude_preprints}
        if args.publication_types:
            filters["publication_types"] = args.publication_types
        if args.languages:
            filters["languages"] = args.languages
        if args.open_access_filter or args.open_access:
            filters["open_access"] = bool(args.open_access)
        provider_order = [item.strip() for item in args.provider_order.split(",") if item.strip()] if args.provider_order else None
        manifest = run_search(topic=args.topic, domain=args.domain, query_file=args.query_file, output_dir=args.output_dir, scope_root=args.scope_root, filters=filters, provider_order=provider_order, max_results_per_query=args.max_results_per_query, max_total=args.max_total, fallback_enabled=not args.no_fallback, provider_options={"min_queries": args.min_queries, "max_queries": args.max_queries}, preprint_profile=args.domain_profile)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0 if manifest.get("status") in {"success", "partial_success"} else 1
    if args.command == "enrich-abstracts":
        print(json.dumps(enrich_abstracts(args.input, args.output, max_papers=args.max_papers, min_chars=args.min_abstract_chars, timeout=3), ensure_ascii=False, indent=2))
        return 0
    errors = validate_bundle(args.bundle)
    if errors:
        for error in errors:
            print(f"✗ {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "valid", "bundle": str(args.bundle.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
