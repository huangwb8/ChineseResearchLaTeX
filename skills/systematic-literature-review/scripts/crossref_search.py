#!/usr/bin/env python3
"""
crossref_search.py - Crossref 检索并生成 papers.jsonl

定位：
  - 作为 DOI 权威验证/补全源，也可作为检索兜底（零配置）
  - Crossref 的摘要覆盖不稳定，通常用于元数据与 DOI 校验
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore

from api_cache import CacheStorage
from config_loader import get_api_config, load_config
from exponential_backoff_retry import ExponentialBackoffRetry


_DOI_RE = re.compile(r"(10\\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)


def _normalize_doi(raw: str) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    s = re.sub(r"^https?://(dx\\.)?doi\\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\\s*", "", s, flags=re.IGNORECASE).strip()
    m = _DOI_RE.search(s)
    return (m.group(1) if m else s).lower()


def _extract_year(item: Dict[str, Any]) -> Optional[int]:
    issued = item.get("issued") or {}
    parts = (issued.get("date-parts") or []) if isinstance(issued, dict) else []
    if parts and isinstance(parts, list) and parts[0] and isinstance(parts[0], list):
        try:
            return int(parts[0][0])
        except Exception:
            return None
    return None


def _item_to_paper(item: Dict[str, Any]) -> Dict[str, Any]:
    title_list = item.get("title") or []
    title = ""
    if isinstance(title_list, list) and title_list:
        title = str(title_list[0] or "").strip()
    elif isinstance(title_list, str):
        title = title_list.strip()

    doi = _normalize_doi(item.get("DOI") or item.get("doi") or "")

    container = item.get("container-title") or []
    venue = ""
    if isinstance(container, list) and container:
        venue = str(container[0] or "").strip()
    elif isinstance(container, str):
        venue = container.strip()

    authors = []
    for a in (item.get("author") or [])[:10]:
        if not isinstance(a, dict):
            continue
        given = str(a.get("given") or "").strip()
        family = str(a.get("family") or "").strip()
        name = " ".join([p for p in [given, family] if p]).strip()
        if name:
            authors.append(name)

    abstract = str(item.get("abstract") or "").strip()
    url = str(item.get("URL") or item.get("url") or "").strip()
    year = _extract_year(item)

    return {
        "title": title,
        "doi": doi,
        "abstract": abstract,
        "venue": venue,
        "year": year,
        "url": url,
        "authors": authors,
        "source": "crossref",
    }


def search_crossref(
    query: str,
    max_results: int = 50,
    *,
    timeout: Optional[int] = None,
    cache_dir: Optional[Path] = None,
    retry: Optional[ExponentialBackoffRetry] = None,
    mailto: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not query.strip():
        return []

    cfg = load_config()
    api_cfg = get_api_config("crossref", cfg) if "crossref" in (cfg.get("api") or {}) else {}
    base_url = str(api_cfg.get("base_url") or "https://api.crossref.org").rstrip("/")
    timeout = int(timeout or api_cfg.get("timeout", 10))

    retry = retry or ExponentialBackoffRetry(((cfg.get("search") or {}).get("rate_limit_protection") or {}).get("retry") or {})
    cache = CacheStorage(cache_dir=cache_dir, ttl=86400) if cache_dir is not None else None

    endpoint = f"{base_url}/works"
    rows = min(1000, max(1, int(max_results)))

    headers = {"Accept": "application/json", "User-Agent": "ChineseResearchLaTeX systematic-literature-review"}

    # DOI 查询：优先走权威直查，避免 query 模糊匹配
    doi_in_query = _normalize_doi(query)
    if doi_in_query and doi_in_query.startswith("10."):
        doi_endpoint = f"{base_url}/works/{doi_in_query}"

        def do_doi_request() -> Dict[str, Any]:
            params: Dict[str, Any] = {}
            if mailto:
                params["mailto"] = mailto
            if cache is not None:
                cached = cache.get(doi_endpoint, params)
                if cached is not None:
                    return cached
            resp = requests.get(doi_endpoint, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if cache is not None:
                cache.set(doi_endpoint, params, data)
            return data

        data = retry.call(do_doi_request)
        item = (data.get("message") or {}) if isinstance(data, dict) else {}
        if isinstance(item, dict) and item.get("DOI"):
            return [_item_to_paper(item)]

    def do_request() -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "rows": rows,
            "query": query,
        }
        if mailto:
            params["mailto"] = mailto

        if cache is not None:
            cached = cache.get(endpoint, params)
            if cached is not None:
                return cached

        resp = requests.get(endpoint, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if cache is not None:
            cache.set(endpoint, params, data)
        return data

    data = retry.call(do_request)
    items = (((data.get("message") or {}).get("items")) or []) if isinstance(data, dict) else []
    out: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            out.append(_item_to_paper(item))
        if len(out) >= max_results:
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
    parser = argparse.ArgumentParser(description="Search Crossref and write papers.jsonl")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--output", required=True, type=Path, help="Output .jsonl path")
    parser.add_argument("--max-results", type=int, default=50, help="Max results (default: 50)")
    parser.add_argument("--cache-dir", type=Path, default=None, help="API cache directory path (optional)")
    args = parser.parse_args()

    papers = search_crossref(query=args.query, max_results=args.max_results, cache_dir=args.cache_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    print(json.dumps({"query": args.query, "written": len(papers), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
