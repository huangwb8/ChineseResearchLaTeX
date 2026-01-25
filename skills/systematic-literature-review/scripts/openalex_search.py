#!/usr/bin/env python3
"""
openalex_search.py - 使用 OpenAlex 进行快速检索并生成 papers.jsonl

用途：
  - 为 systematic-literature-review 的 Pipeline（阶段 1）提供"自动检索"能力
  - 生成符合 Pipeline 要求的最小字段

输出 JSONL（每行一个 paper）字段：
  - title, doi, abstract, venue, year, url
  - authors (list[str]): 简化的作者名称列表（前10位）
  - authorships (list[dict]): 原始 authorships 数据（保留完整结构）
"""

import argparse
import json
import logging
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 配置与多源检索（用于“单一查询”场景的自动降级）
try:
    from config_loader import load_config
except ImportError:
    load_config = None  # type: ignore[assignment]

try:
    from semantic_scholar_search import search_semantic_scholar
except ImportError:
    search_semantic_scholar = None  # type: ignore[assignment]

try:
    from crossref_search import search_crossref
except ImportError:
    search_crossref = None  # type: ignore[assignment]

try:
    from rate_limiter import RateLimiter
    from exponential_backoff_retry import ExponentialBackoffRetry
except ImportError:
    RateLimiter = None  # type: ignore[assignment]
    ExponentialBackoffRetry = None  # type: ignore[assignment]

# 导入多源摘要获取模块
try:
    from multi_source_abstract import AbstractFetcher
except ImportError:
    AbstractFetcher = None  # type: ignore[misc,assignment]


def _normalize_doi(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE).strip()
    return raw.lower()


def _reconstruct_abstract(abstract_inverted_index: Optional[Dict[str, Any]]) -> str:
    if not abstract_inverted_index:
        return ""
    positions: Dict[int, str] = {}
    for token, idxs in abstract_inverted_index.items():
        for idx in idxs:
            if idx not in positions:
                positions[idx] = token
    if not positions:
        return ""
    return " ".join(positions[i] for i in sorted(positions))


def _work_to_paper(work: Dict[str, Any], abstract_fetcher: Optional["AbstractFetcher"] = None, topic: str = "") -> Dict[str, Any]:
    doi = _normalize_doi(work.get("doi") or "")
    venue = ""
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = source.get("display_name") or ""

    # 提取作者信息：从 OpenAlex 的 authorships 字段获取作者名称
    # 限制为前10位作者，避免过多作者影响性能和存储
    authorships = work.get("authorships") or []
    authors: list[str] = []
    if isinstance(authorships, list):
        for authorship in authorships[:10]:
            if isinstance(authorship, dict):
                author_dict = authorship.get("author") or {}
                name = author_dict.get("display_name") or ""
                if name:
                    authors.append(str(name).strip())

    # 获取摘要：优先从 OpenAlex，若缺失则从备用 API 补充
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    # 如果 OpenAlex 没有摘要且启用了备用获取器，尝试从其他 API 获取
    if not abstract and abstract_fetcher is not None and doi:
        abstract = abstract_fetcher.fetch_by_doi(doi, topic=topic)

    paper = {
        "title": work.get("title") or "",
        "doi": doi,
        "abstract": abstract,
        "venue": venue,
        "year": work.get("publication_year"),
        "url": work.get("id") or work.get("primary_location", {}).get("landing_page_url") or "",
        "authors": authors,          # 简化的作者名称列表，供 BibTeX 生成使用
        "authorships": authorships,  # 保留原始 authorships 数据，供后续处理使用
    }
    return paper


def get_work_by_doi(
    doi: str,
    mailto: Optional[str] = None,
    abstract_fetcher: Optional["AbstractFetcher"] = None,
    topic: str = "",
    cache_dir: Optional[Path] = None,  # API 缓存目录
) -> Optional[Dict[str, Any]]:
    """
    Lookup a single work by DOI and return the minimal "paper" dict used by the pipeline.

    Notes:
    - Useful for ensuring sentinel papers are included in the candidate pool.
    - Best-effort: returns None if not found or network error.
    - If abstract_fetcher is provided, will attempt to fetch missing abstracts from backup APIs.
    """
    doi = _normalize_doi(doi)
    if not doi:
        return None

    try:
        import requests  # type: ignore
    except ModuleNotFoundError:
        return None

    from urllib.parse import quote, urlencode

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "pipelines/skills systematic-literature-review openalex-search",
            "Accept": "application/json",
        }
    )

    candidates = [
        f"https://api.openalex.org/works/doi:{quote(doi, safe='')}",
        f"https://api.openalex.org/works?{urlencode({'filter': f'doi:https://doi.org/{doi}', 'per-page': '1'})}",
    ]
    params = {"mailto": mailto} if mailto else None

    for url in candidates:
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "results" in data:
                results = data.get("results") or []
                if results and isinstance(results[0], dict):
                    return _work_to_paper(results[0], abstract_fetcher=abstract_fetcher, topic=topic)
                continue
            if isinstance(data, dict) and data.get("id"):
                return _work_to_paper(data, abstract_fetcher=abstract_fetcher, topic=topic)
        except Exception:
            continue

    return None


def search_openalex(
    query: str,
    max_results: int,
    mailto: Optional[str],
    min_year: Optional[int],
    max_year: Optional[int],
    enrich_abstracts: bool = False,  # 默认禁用，因时间开销大且收益有限
    abstract_timeout: int = 2,  # 减少超时时间
    cache_dir: Optional[Path] = None,  # API 缓存目录
) -> list[Dict[str, Any]]:
    try:
        import requests  # type: ignore
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Missing dependency: requests. Install it to use OpenAlex auto-search.\n"
            "  pip install requests"
        ) from e

    # 初始化多源摘要获取器（如果启用且模块可用）
    abstract_fetcher = None
    if enrich_abstracts and AbstractFetcher is not None:
        abstract_fetcher = AbstractFetcher(timeout=abstract_timeout)

    # 初始化缓存存储（如果提供了 cache_dir）
    cache_storage = None
    if cache_dir is not None:
        try:
            from api_cache import CacheStorage
            cache_storage = CacheStorage(cache_dir=cache_dir, ttl=86400)
            logger.info(f"API 缓存已启用: {cache_dir}")
        except Exception as e:
            logger.warning(f"无法初始化 API 缓存: {e}")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "pipelines/skills systematic-literature-review openalex-search",
        }
    )

    def fetch_with_cursor(search_query: str) -> list[Dict[str, Any]]:
        """
        Cursor-based pagination (preferred by OpenAlex for deep retrieval).

        Notes:
        - We still cap at max_results to avoid unbounded queries.
        - We keep a small polite delay to reduce burstiness.
        """
        url = "https://api.openalex.org/works"
        per_page = min(200, max(1, max_results))
        cursor = "*"
        out: list[Dict[str, Any]] = []

        filters = []
        if min_year is not None:
            filters.append(f"from_publication_date:{min_year}-01-01")
        if max_year is not None:
            filters.append(f"to_publication_date:{max_year}-12-31")
        filter_str = ",".join(filters) if filters else None

        while cursor and len(out) < max_results:
            params: Dict[str, Any] = {
                "search": search_query,
                "per-page": per_page,
                "cursor": cursor,
            }
            if mailto:
                params["mailto"] = mailto
            if filter_str:
                params["filter"] = filter_str

            # 尝试从缓存获取
            data = None
            if cache_storage is not None:
                cached_data = cache_storage.get(url, params)
                if cached_data is not None:
                    data = cached_data
                    logger.debug(f"缓存命中: cursor={cursor[:8]}...")

            # 缓存未命中或未启用缓存时，调用 API
            if data is None:
                resp = session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                # 保存到缓存
                if cache_storage is not None:
                    cache_storage.set(url, params, data)

            results = data.get("results", []) or []
            if not results:
                break

            for work in results:
                out.append(_work_to_paper(work, abstract_fetcher=abstract_fetcher, topic=query))
                if len(out) >= max_results:
                    break

            cursor = (data.get("meta") or {}).get("next_cursor")
            time.sleep(0.25 + random.random() * 0.25)

        return out

    papers = fetch_with_cursor(query)

    # 如果 query 含大量非 ASCII（如中文）且回收过少，尝试一个“ASCII token fallback”
    if len(papers) < min(10, max_results) and any(ord(ch) > 127 for ch in query):
        fallback_query = " ".join(re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?", query))
        fallback_query = fallback_query.replace("-", " ").strip()
        if fallback_query and fallback_query.lower() != query.lower():
            papers.extend(fetch_with_cursor(fallback_query))

    # 去重：优先 DOI，其次 title+year
    seen: set[str] = set()
    deduped: list[Dict[str, Any]] = []
    for p in papers:
        key = p["doi"] or f'{p["title"].strip().lower()}::{p.get("year")}'
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(p)
        if len(deduped) >= max_results:
            break

    # 输出摘要补充统计信息
    if abstract_fetcher is not None:
        stats = abstract_fetcher.get_statistics()
        if stats.total_papers > 0:
            import sys
            print(f"Abstract enrichment statistics:", file=sys.stderr)
            print(f"  {stats}", file=sys.stderr)

    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Search OpenAlex and write papers.jsonl")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--output", required=True, type=Path, help="Output .jsonl path")
    parser.add_argument("--max-results", type=int, default=200, help="Max results to write (default: 200)")
    parser.add_argument("--mailto", default=None, help="Optional contact email for OpenAlex polite pool")
    parser.add_argument("--min-year", type=int, default=None, help="Filter: min publication year")
    parser.add_argument("--max-year", type=int, default=None, help="Filter: max publication year")
    # 默认禁用摘要补充（时间开销大且可能触发第三方限流）；显式 --enrich-abstracts 才启用
    parser.add_argument("--enrich-abstracts", dest="enrich_abstracts", action="store_true", default=False, help="Enable multi-source abstract enrichment (default: disabled)")
    parser.add_argument("--no-enrich-abstracts", dest="enrich_abstracts", action="store_false", help="Disable multi-source abstract enrichment (kept for backward compatibility)")
    parser.add_argument("--abstract-timeout", type=int, default=5, help="Timeout for abstract enrichment APIs (default: 5)")
    parser.add_argument("--cache-dir", type=Path, default=None, help="API cache directory path (default: no caching)")
    args = parser.parse_args()

    papers = search_openalex(
        query=args.query,
        max_results=args.max_results,
        mailto=args.mailto,
        min_year=args.min_year,
        max_year=args.max_year,
        cache_dir=args.cache_dir,
        enrich_abstracts=bool(args.enrich_abstracts),
        abstract_timeout=args.abstract_timeout,
    )

    # 单一查询降级：OpenAlex 结果过少时，按 provider_priority 补齐（默认仅补到 max_results）
    if load_config is not None:
        try:
            cfg = load_config()
            search_cfg = cfg.get("search", {}) if isinstance(cfg, dict) else {}
            fallback_cfg = search_cfg.get("fallback", {}) if isinstance(search_cfg.get("fallback", {}), dict) else {}
            provider_priority = list(search_cfg.get("provider_priority") or [])
            if bool(fallback_cfg.get("enabled", False)) and len(papers) < min(10, int(args.max_results)):
                protection_cfg = search_cfg.get("rate_limit_protection", {}) if isinstance(search_cfg.get("rate_limit_protection", {}), dict) else {}
                rate_limiter = RateLimiter(protection_cfg) if RateLimiter is not None else None
                retry = ExponentialBackoffRetry((protection_cfg.get("retry") or {})) if ExponentialBackoffRetry is not None else None

                def _extend(more: list[dict]) -> None:
                    if not more:
                        return
                    papers.extend(more)

                # 尝试按优先级补齐（跳过 openalex 自身）
                for p in provider_priority:
                    if len(papers) >= int(args.max_results):
                        break
                    if p == "semantic_scholar" and search_semantic_scholar is not None:
                        need = int(args.max_results) - len(papers)
                        _extend(
                            search_semantic_scholar(
                                query=args.query,
                                max_results=min(need, 50),
                                cache_dir=args.cache_dir,
                                rate_limiter=rate_limiter,
                                retry=retry,
                            )
                        )
                    if p == "crossref" and search_crossref is not None:
                        need = int(args.max_results) - len(papers)
                        _extend(
                            search_crossref(
                                query=args.query,
                                max_results=min(need, 50),
                                cache_dir=args.cache_dir,
                                retry=retry,
                                mailto=args.mailto,
                            )
                        )

                # 去重：优先 DOI，其次 title+year
                seen: set[str] = set()
                deduped: list[Dict[str, Any]] = []
                for p in papers:
                    key = p.get("doi") or f'{str(p.get("title","")).strip().lower()}::{p.get("year")}'
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    deduped.append(p)
                    if len(deduped) >= int(args.max_results):
                        break
                papers = deduped
        except Exception:
            pass

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    print(json.dumps({"query": args.query, "written": len(papers), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
