#!/usr/bin/env python3
"""Canonical ``rls.paper.v1`` records and strict validation helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA_VERSION = "rls.paper.v1"
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
IDENTIFIER_KEYS = ("doi", "pmid", "arxiv", "openalex", "semantic_scholar")


class CandidateNormalizationError(ValueError):
    """A provider candidate cannot enter the canonical schema."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def normalize_doi(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.I)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.I).strip().rstrip(".,;)")
    return raw.lower() if raw else None


def normalize_year(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 1000 <= value <= 3000 else None
    match = re.search(r"\b(1[0-9]{3}|2[0-9]{3}|3000)\b", str(value))
    return int(match.group(0)) if match else None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return bool(value)


def stable_record_id(record: dict[str, Any], *, fallback_index: int = 0) -> str:
    identifiers = record.get("identifiers") if isinstance(record.get("identifiers"), dict) else {}
    doi = normalize_doi(identifiers.get("doi") or record.get("doi"))
    if doi:
        return f"doi:{doi}"
    for key in ("pmid", "openalex", "semantic_scholar", "arxiv"):
        value = _text(identifiers.get(key) or record.get(key))
        if value:
            return f"{key}:{value.lower()}"
    title = re.sub(r"\s+", " ", str(record.get("title") or "").strip().lower())
    year = normalize_year(record.get("year"))
    payload = f"{title}|{year or ''}|{fallback_index}".encode("utf-8")
    return "title:" + hashlib.sha256(payload).hexdigest()[:24]


def _authors(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        elif isinstance(item, dict):
            nested = item.get("author") if isinstance(item.get("author"), dict) else {}
            name = item.get("name") or nested.get("display_name") or nested.get("name") or item.get("display_name")
            if not name:
                name = " ".join(str(item.get(key)).strip() for key in ("given", "family") if item.get(key))
            if name and str(name).strip():
                result.append(str(name).strip())
    return result


def _source_envelope(raw: dict[str, Any], *, provider: str, query_id: str | None, rank: int | None) -> dict[str, Any]:
    provider_id = raw.get("provider_record_id") or raw.get("id") or raw.get("openalex_id")
    envelope: dict[str, Any] = {
        "provider": provider or "unknown",
        "provider_record_id": str(provider_id) if provider_id else None,
        "first_seen_at": raw.get("first_seen_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query_id": query_id,
        "rank": rank,
        "url": raw.get("url") or raw.get("doi_url"),
    }
    return envelope


def normalize_record(
    raw: Any,
    *,
    provider: str = "unknown",
    query_id: str | None = None,
    rank: int | None = None,
    fallback_index: int = 0,
) -> dict[str, Any]:
    """Map provider/legacy fields to the canonical record plus flat compatibility view."""
    if raw is None:
        raise CandidateNormalizationError("empty_record", "candidate record is null")
    if not isinstance(raw, dict):
        raise CandidateNormalizationError("invalid_record_type", "candidate record must be an object")
    identifiers: dict[str, str | None] = {key: None for key in IDENTIFIER_KEYS}
    incoming = raw.get("identifiers") if isinstance(raw.get("identifiers"), dict) else {}
    for key in IDENTIFIER_KEYS:
        identifiers[key] = _text(incoming.get(key) or raw.get(key))
    if provider == "openalex" and not identifiers["openalex"]:
        identifiers["openalex"] = _text(raw.get("id"))
    if provider == "semantic_scholar" and not identifiers["semantic_scholar"]:
        identifiers["semantic_scholar"] = _text(raw.get("paperId") or raw.get("id"))
    if provider == "semantic_scholar":
        external = raw.get("externalIds") if isinstance(raw.get("externalIds"), dict) else {}
        identifiers["doi"] = normalize_doi(identifiers["doi"] or external.get("DOI"))
        identifiers["pmid"] = _text(identifiers["pmid"] or external.get("PubMed"))
        identifiers["arxiv"] = _text(identifiers["arxiv"] or external.get("ArXiv"))
    if provider == "crossref" and not identifiers["doi"]:
        identifiers["doi"] = normalize_doi(raw.get("DOI"))
    identifiers["doi"] = normalize_doi(identifiers["doi"])

    title_value = raw.get("title") or raw.get("display_name")
    if isinstance(title_value, list):
        title_value = title_value[0] if title_value else ""
    title = _text(title_value)
    if not title:
        raise ValueError("candidate title must be non-empty")
    year_value = raw.get("year") or raw.get("publication_year")
    if year_value is None:
        for date_key in ("published", "published-print", "issued"):
            date = raw.get(date_key)
            if isinstance(date, dict) and isinstance(date.get("date-parts"), list) and date["date-parts"]:
                parts = date["date-parts"][0]
                if isinstance(parts, list) and parts:
                    year_value = parts[0]
                    break
    year = normalize_year(year_value)
    authors = _authors(raw.get("authors") or raw.get("authorships") or raw.get("author"))
    abstract = _text(raw.get("abstract"))
    if not abstract and isinstance(raw.get("abstract_inverted_index"), dict):
        terms: list[tuple[int, str]] = []
        for token, positions in raw["abstract_inverted_index"].items():
            if isinstance(positions, list):
                terms.extend((int(pos), str(token)) for pos in positions if isinstance(pos, int))
        if terms:
            abstract = " ".join(token for _, token in sorted(terms))
    abstract_status = str(raw.get("abstract_status") or ("present" if abstract else "missing"))
    if abstract_status not in {"present", "missing", "attempted", "not_requested"}:
        abstract_status = "present" if abstract else "missing"

    publication = raw.get("publication") if isinstance(raw.get("publication"), dict) else {}
    primary_location = raw.get("primary_location") if isinstance(raw.get("primary_location"), dict) else {}
    primary_source = primary_location.get("source") if isinstance(primary_location.get("source"), dict) else {}
    venue_value = raw.get("venue") or raw.get("journal") or raw.get("container_title") or raw.get("container-title") or primary_source.get("display_name")
    if isinstance(venue_value, list):
        venue_value = venue_value[0] if venue_value else ""
    venue = _text(venue_value)
    is_preprint = publication.get("is_preprint")
    if is_preprint is None:
        probe = f"{venue or ''} {raw.get('url') or ''}".lower()
        is_preprint = any(token in probe for token in ("arxiv", "biorxiv", "medrxiv", "preprint"))
    sources = raw.get("sources") if isinstance(raw.get("sources"), list) else []
    sources = [item for item in sources if isinstance(item, dict)]
    if not sources:
        sources = [_source_envelope(raw, provider=provider, query_id=query_id, rank=rank)]
    query_matches = list(raw.get("query_matches")) if isinstance(raw.get("query_matches"), list) else []
    if query_id and query_id not in query_matches:
        query_matches.append(query_id)
    warnings = raw.get("quality_warnings") if isinstance(raw.get("quality_warnings"), list) else []
    warnings = [str(item) for item in warnings if str(item).strip()]
    # Provider payloads are not trusted.  Keep malformed DOI values out of the
    # canonical identifier while surfacing the loss for audit instead of
    # emitting a record that will fail the strict v1 validator downstream.
    if identifiers["doi"] and not DOI_RE.match(identifiers["doi"]):
        warnings.append("invalid_doi_discarded")
        identifiers["doi"] = None
    if not venue:
        warnings.append("missing_venue")
    if not abstract and "missing_abstract" not in warnings:
        warnings.append("missing_abstract")

    open_access = publication.get("is_open_access")
    if open_access is None:
        open_access = raw.get("is_open_access")
    if open_access is None and isinstance(raw.get("open_access"), dict):
        open_access = raw["open_access"].get("is_oa")
    if open_access is None and isinstance(raw.get("primary_location"), dict):
        open_access = raw["primary_location"].get("is_oa")
    open_access = _bool_or_none(open_access)

    record: dict[str, Any] = {
        "record_type": "paper",
        "schema_version": SCHEMA_VERSION,
        "record_id": str(raw.get("record_id") or ""),
        "title": title,
        "authors": authors,
        "authorships": raw.get("authorships") if isinstance(raw.get("authorships"), list) else [],
        "identifiers": identifiers,
        "venue": venue,
        "year": year,
        "published_date": _text(raw.get("published_date")),
        "online_date": _text(raw.get("online_date")),
        "url": _text(raw.get("url") or raw.get("doi_url")),
        "abstract": abstract,
        "abstract_status": abstract_status,
        "abstract_provenance": raw.get("abstract_provenance") if isinstance(raw.get("abstract_provenance"), dict) else None,
        "publication": {
            "publication_type": publication.get("publication_type") or raw.get("publication_type") or raw.get("type"),
            "is_preprint": bool(_bool_or_none(is_preprint)),
            "preprint_server": publication.get("preprint_server"),
            "peer_reviewed": publication.get("peer_reviewed"),
            "version": publication.get("version"),
            "language": publication.get("language") or raw.get("language"),
            "is_open_access": open_access,
        },
        "sources": sources,
        "provenance": raw.get("provenance") if isinstance(raw.get("provenance"), dict) else {},
        "query_matches": sorted({str(item) for item in query_matches if str(item).strip()}),
        "quality_warnings": sorted(set(warnings)),
    }
    if not record["record_id"]:
        record["record_id"] = stable_record_id(record, fallback_index=fallback_index)
    # Flat legacy view is intentionally generated at this boundary only.
    record.update({
        "doi": identifiers["doi"],
        "pmid": identifiers["pmid"],
        "openalex_id": identifiers["openalex"],
        "semantic_scholar_id": identifiers["semantic_scholar"],
        "arxiv_id": identifiers["arxiv"],
        "source": provider or (sources[0].get("provider") if sources else "unknown"),
        "language": record["publication"].get("language"),
        "is_open_access": record["publication"].get("is_open_access"),
    })
    return record


def adapt_legacy_record(raw: dict[str, Any], *, fallback_index: int = 0) -> dict[str, Any]:
    """Adapt old ``title/year/id`` rows while surfacing an audit warning."""
    record = normalize_record(raw, provider=str(raw.get("source") or "legacy"), fallback_index=fallback_index)
    warnings = set(record.get("quality_warnings") or [])
    warnings.add("legacy_adapted")
    record["quality_warnings"] = sorted(warnings)
    return record


def validate_candidate(record: Any, *, require_schema: bool = True) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be an object"]
    if require_schema and record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if record.get("record_type") != "paper":
        errors.append("record_type must be paper")
    if not isinstance(record.get("record_id"), str) or not record["record_id"].strip():
        errors.append("record_id must be non-empty string")
    if not isinstance(record.get("title"), str) or not record["title"].strip():
        errors.append("title must be non-empty string")
    if not isinstance(record.get("authors"), list) or not all(isinstance(item, str) for item in record["authors"]):
        errors.append("authors must be string array")
    identifiers = record.get("identifiers")
    if not isinstance(identifiers, dict):
        errors.append("identifiers must be object")
    else:
        for key in IDENTIFIER_KEYS:
            if key not in identifiers:
                errors.append(f"identifiers.{key} is required")
            elif identifiers.get(key) is not None and not isinstance(identifiers.get(key), str):
                errors.append(f"identifiers.{key} must be null or string")
        doi = identifiers.get("doi")
        if doi is not None and (not isinstance(doi, str) or not DOI_RE.match(doi)):
            errors.append("identifiers.doi is invalid")
    year = record.get("year")
    if year is not None and (not isinstance(year, int) or not 1000 <= year <= 3000):
        errors.append("year must be null or integer between 1000 and 3000")
    if record.get("abstract_status") not in {"present", "missing", "attempted", "not_requested"}:
        errors.append("abstract_status is invalid")
    if record.get("abstract") is not None and not isinstance(record.get("abstract"), str):
        errors.append("abstract must be null or string")
    if not isinstance(record.get("publication"), dict):
        errors.append("publication must be object")
    else:
        is_preprint = record["publication"].get("is_preprint")
        if not isinstance(is_preprint, bool):
            errors.append("publication.is_preprint must be boolean")
    if not isinstance(record.get("sources"), list) or not record.get("sources"):
        errors.append("sources must be non-empty array")
    elif any(not isinstance(item, dict) for item in record["sources"]):
        errors.append("sources entries must be objects")
    if not isinstance(record.get("query_matches"), list):
        errors.append("query_matches must be array")
    elif any(not isinstance(item, str) for item in record["query_matches"]):
        errors.append("query_matches entries must be strings")
    if not isinstance(record.get("quality_warnings"), list):
        errors.append("quality_warnings must be array")
    elif any(not isinstance(item, str) for item in record["quality_warnings"]):
        errors.append("quality_warnings entries must be strings")
    return errors


def validate_candidates(records: Iterable[Any], *, require_schema: bool = True) -> tuple[list[dict[str, Any]], list[str]]:
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(records, 1):
        record = raw if require_schema else adapt_legacy_record(raw, fallback_index=index)
        row_errors = validate_candidate(record, require_schema=require_schema)
        if row_errors:
            errors.extend([f"row {index}: {item}" for item in row_errors])
            continue
        record_id = record["record_id"]
        if record_id in seen:
            errors.append(f"row {index}: duplicate record_id {record_id}")
        seen.add(record_id)
        normalized.append(record)
    return normalized, errors
