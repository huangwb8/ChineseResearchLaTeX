#!/usr/bin/env python3
"""
semantic_scholar_search.py - Semantic Scholar 检索并生成 papers.jsonl

定位：
  - 作为“语义增强补充源”，不承担高频主力负载（避免 100/min 的零配置限流）
  - 与 api_cache.py + rate_limiter.py 集成，提升稳定性与可复现性
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore

from api_cache import CacheStorage
from config_loader import get_api_config, load_config
from exponential_backoff_retry import ExponentialBackoffRetry
from rate_limiter import RateLimiter


_DOI_RE = re.compile(r"(10\\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)


def _normalize_doi(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    s = re.sub(r"^https?://(dx\\.)?doi\\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\\s*", "", s, flags=re.IGNORECASE).strip()
    m = _DOI_RE.search(s)
    return (m.group(1) if m else s).lower()


def _paper_to_minimal(p: Dict[str, Any]) -> Dict[str, Any]:
    external = p.get("externalIds") or {}
    doi = _normalize_doi(str(external.get("DOI") or p.get("doi") or ""))

    authors = []
    for a in (p.get("authors") or [])[:10]:
        if isinstance(a, dict):
            name = str(a.get("name") or "").strip()
            if name:
                authors.append(name)
        elif isinstance(a, str):
            authors.append(a.strip())

    venue = str(p.get("venue") or p.get("journal") or "").strip()
    year = p.get("year")
    url = str(p.get("url") or "").strip()
    if not url:
        pid = str(p.get("paperId") or "").strip()
        if pid:
            url = f"https://www.semanticscholar.org/paper/{pid}"

    return {
        "title": str(p.get("title") or "").strip(),
        "doi": doi,
        "abstract": str(p.get("abstract") or "").strip(),
        "venue": venue,
        "year": year,
        "url": url,
        "authors": authors,
        "source": "semantic_scholar",
    }


def search_semantic_scholar(
    query: str,
    max_results: int = 50,
    *,
    api_key: Optional[str] = None,
    timeout: Optional[int] = None,
    cache_dir: Optional[Path] = None,
    rate_limiter: Optional[RateLimiter] = None,
    retry: Optional[ExponentialBackoffRetry] = None,
) -> List[Dict[str, Any]]:
    if not query.strip():
        return []

    cfg = load_config()
    api_cfg = get_api_config("semantic_scholar", cfg)
    base_url = str(api_cfg.get("base_url") or "https://api.semanticscholar.org/graph/v1").rstrip("/")
    timeout = int(timeout or api_cfg.get("timeout", 10))

    rate_limiter = rate_limiter or RateLimiter((cfg.get("search") or {}).get("rate_limit_protection") or {})
    retry = retry or ExponentialBackoffRetry(((cfg.get("search") or {}).get("rate_limit_protection") or {}).get("retry") or {})

    if api_key is None:
        api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    headers = {"Accept": "application/json", "User-Agent": "ChineseResearchLaTeX systematic-literature-review"}
    if api_key:
        headers["x-api-key"] = api_key

    # 统一走缓存（若开启）
    cache = CacheStorage(cache_dir=cache_dir, ttl=86400) if cache_dir is not None else None

    endpoint = f"{base_url}/paper/search"
    limit = min(100, max(1, int(max_results)))
    fields = "title,abstract,year,authors,venue,externalIds,url,paperId"

    def do_request(offset: int) -> Dict[str, Any]:
        params = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "fields": fields,
        }
        if cache is not None:
            cached = cache.get(endpoint, params)
            if cached is not None:
                return cached

        st = rate_limiter.can_call("semantic_scholar")
        if not st.can_call:
            raise RuntimeError(st.reason or "semantic_scholar rate-limited")

        resp = requests.get(endpoint, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        if cache is not None:
            cache.set(endpoint, params, data)

        rate_limiter.record_call("semantic_scholar")
        return data

    out: list[dict] = []
    offset = 0
    while len(out) < max_results:
        data = retry.call(do_request, offset)
        items = data.get("data") or []
        if not items:
            break
        for item in items:
            if isinstance(item, dict):
                out.append(_paper_to_minimal(item))
            if len(out) >= max_results:
                break
        # Semantic Scholar 会返回 total/next 等字段；这里做最小分页逻辑
        offset += len(items)
        if len(items) < limit:
            break

    # 去重（优先 DOI）
    seen = set()
    deduped: list[dict] = []
    for p in out:
        key = p.get("doi") or f'{p.get("title","").strip().lower()}::{p.get("year")}'
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(p)
        if len(deduped) >= max_results:
            break

    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Semantic Scholar and write papers.jsonl")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--output", required=True, type=Path, help="Output .jsonl path")
    parser.add_argument("--max-results", type=int, default=50, help="Max results (default: 50)")
    parser.add_argument("--cache-dir", type=Path, default=None, help="API cache directory path (optional)")
    args = parser.parse_args()

    papers = search_semantic_scholar(
        query=args.query,
        max_results=args.max_results,
        cache_dir=args.cache_dir,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    print(json.dumps({"query": args.query, "written": len(papers), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

