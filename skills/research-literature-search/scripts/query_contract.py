#!/usr/bin/env python3
"""Versioned query input contract shared by search producers and consumers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "rls.v1"


class QueryInputError(ValueError):
    """Raised when a query payload cannot be safely consumed."""


@dataclass(frozen=True)
class QueryPlan:
    queries: list[dict[str, str]]
    requested_count: int
    source: str = ""
    sha256: str = ""

    @property
    def accepted_count(self) -> int:
        return len(self.queries)


def normalize_output_stem(raw: str) -> str:
    stem = re.sub(r'[\\/:*?"<>|]+', "", str(raw or "").strip())
    stem = re.sub(r"\s+", "-", stem)
    return stem[:80] or "topic"


def legacy_output_stems(raw: str) -> list[str]:
    value = str(raw or "").strip()
    old = re.sub(r'[\\/:*?"<>|]+', "", value)
    # Historical review runner accidentally preserved whitespace in legacy stems;
    # keep that probe path read-only so old checkpoints remain discoverable.
    old = re.sub(r"\s+", "-", old)[:80] or "topic"
    canonical = normalize_output_stem(value)
    return [item for item in dict.fromkeys([old]) if item != canonical]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_item(item: Any, index: int) -> dict[str, str] | None:
    if isinstance(item, str):
        query = item.strip()
        return {"query": query, "rationale": ""} if query else None
    if isinstance(item, dict):
        query = str(item.get("query") or "").strip()
        if not query:
            return None
        rationale = str(item.get("rationale") or "").strip()
        return {"query": query, "rationale": rationale}
    raise QueryInputError(
        f"查询 JSON 第 {index} 项格式错误：只支持字符串或含 query/rationale 的对象"
    )


def normalize_query_payload(
    data: Any,
    *,
    min_queries: int = 5,
    max_queries: int = 25,
    source: str = "查询输入",
    source_path: str = "",
    source_sha256: str = "",
) -> QueryPlan:
    if min_queries < 1 or max_queries < min_queries:
        raise QueryInputError(
            f"查询数量配置无效：min_queries={min_queries}, max_queries={max_queries}"
        )
    items = data.get("queries") if isinstance(data, dict) else data
    if isinstance(data, dict) and "queries" not in data:
        raise QueryInputError('查询 JSON 对象必须包含 "queries" 数组')
    if not isinstance(items, list):
        raise QueryInputError("查询 JSON 必须是数组，或包含 queries 数组的对象")

    queries: list[dict[str, str]] = []
    for index, item in enumerate(items, 1):
        normalized = _normalize_item(item, index)
        if normalized is None:
            continue
        query_id = f"q{len(queries) + 1:02d}"
        queries.append({
            "query_id": query_id,
            "ordinal": str(len(queries) + 1),
            **normalized,
        })

    accepted = len(queries)
    if accepted < min_queries:
        raise QueryInputError(
            f"{source} 的有效查询至少需要 {min_queries} 条，空查询剔除后仅 {accepted} 条"
        )
    if accepted > max_queries:
        raise QueryInputError(f"{source} 的有效查询至多允许 {max_queries} 条，当前 {accepted} 条")
    return QueryPlan(
        queries=queries,
        requested_count=len(items),
        source=source_path or source,
        sha256=source_sha256,
    )


def load_query_plan(path: Path, *, min_queries: int = 5, max_queries: int = 25) -> QueryPlan:
    source = Path(path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise QueryInputError(f"查询文件不存在或不是普通文件：{source}")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QueryInputError(f"无法解析查询 JSON：{source}（{exc}）") from exc
    return normalize_query_payload(
        data,
        min_queries=min_queries,
        max_queries=max_queries,
        source=str(source),
        source_path=str(source),
        source_sha256=sha256_file(source),
    )
