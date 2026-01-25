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

    # 获取摘要：优先从 OpenAlex
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

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

    # 仅在“单篇查找”等场景使用：不对批量检索启用，避免逐条触发多源 API。
    if abstract_fetcher is not None and (not abstract or len(str(abstract).strip()) < 80):
        filled = None
        try:
            if doi:
                filled = abstract_fetcher.fetch_by_doi(doi, topic=topic)
            if (not filled) and paper.get("title"):
                filled = abstract_fetcher.fetch_by_title(str(paper.get("title") or ""), topic=topic)
        except Exception:
            filled = None
        if filled and isinstance(filled, str):
            paper["abstract"] = filled.strip()

    return paper


def _enrich_missing_abstracts(
    papers: list[Dict[str, Any]],
    *,
    topic: str,
    cache_dir: Optional[Path],
    retry_rounds: int,
    backoff_base_seconds: float,
    min_abstract_chars: int,
    max_papers_total: int,
    abstract_timeout: int,
) -> None:
    """
    对缺失摘要的条目做“有限补齐”：
      - 仅处理 abstract 缺失/过短的条目
      - 每篇文献最多 retry_rounds 轮（每轮内部会按来源优先级尝试多个 API）
      - 仍失败则标记质量提示，供后续阶段“尽量不引用”
    """
    if AbstractFetcher is None:
        return
    if not papers:
        return

    max_papers_total = int(max_papers_total)
    retry_rounds = max(0, int(retry_rounds))
    min_abstract_chars = max(0, int(min_abstract_chars))
    backoff_base_seconds = float(backoff_base_seconds)

    # 初始化 fetcher（优先复用 cache_dir，减少重复请求/限流风险）
    fetcher = AbstractFetcher(timeout=int(abstract_timeout), cache_dir=cache_dir)

    # 优先补齐：有 DOI 的缺摘要文献
    def _needs(p: Dict[str, Any]) -> bool:
        a = p.get("abstract") or ""
        return not isinstance(a, str) or len(a.strip()) < min_abstract_chars

    candidates = [p for p in papers if _needs(p)]
    candidates.sort(key=lambda p: (0 if (p.get("doi") or "") else 1, -int(p.get("year") or 0)))
    if max_papers_total > 0:
        candidates = candidates[:max_papers_total]

    for p in candidates:
        doi = str(p.get("doi") or "").strip()
        title = str(p.get("title") or "").strip()

        filled = False
        attempts = 0
        for r in range(max(1, retry_rounds)):
            attempts += 1
            abstract = None
            if doi:
                abstract = fetcher.fetch_by_doi(doi, topic=topic)
            if not abstract and title:
                abstract = fetcher.fetch_by_title(title, topic=topic)
            if abstract and isinstance(abstract, str) and len(abstract.strip()) >= min_abstract_chars:
                p["abstract"] = abstract.strip()
                p["abstract_status"] = "present"
                p["abstract_enrichment"] = {"attempts": attempts, "filled": True}
                filled = True
                break
            # 退避：避免重试风暴
            if r < max(0, retry_rounds - 1):
                time.sleep(max(0.0, backoff_base_seconds) * (2**r))

        if not filled:
            # 保持原有 abstract（可能为空/过短），并标记提示
            p["abstract_status"] = "missing"
            p["quality_warnings"] = list(p.get("quality_warnings") or [])
            if "missing_abstract" not in p["quality_warnings"]:
                p["quality_warnings"].append("missing_abstract")
            p["abstract_enrichment"] = {"attempts": attempts, "filled": False}


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
    enrich_abstracts: Optional[bool] = None,  # None=follow config.yaml; True/False=explicit override
    abstract_timeout: Optional[int] = None,
    cache_dir: Optional[Path] = None,  # API 缓存目录
) -> list[Dict[str, Any]]:
    try:
        import requests  # type: ignore
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Missing dependency: requests. Install it to use OpenAlex auto-search.\n"
            "  pip install requests"
        ) from e

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
                out.append(_work_to_paper(work, abstract_fetcher=None, topic=query))
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

    # 摘要补齐（有限上限 + 有限重试）
    # - enrich_abstracts=None：按 config.yaml 的 search.abstract_enrichment.enabled 决定
    # - enrich_abstracts=True/False：显式覆盖
    cfg: dict[str, Any] = {}
    if load_config is not None:
        try:
            cfg = load_config()
        except Exception:
            cfg = {}
    search_cfg = cfg.get("search", {}) if isinstance(cfg, dict) else {}
    ae = (search_cfg.get("abstract_enrichment") or {}) if isinstance(search_cfg.get("abstract_enrichment"), dict) else {}

    do_enrich = bool(ae.get("enabled", False)) if enrich_abstracts is None else bool(enrich_abstracts)
    if do_enrich:
        timeout_seconds = int(ae.get("timeout_seconds", abstract_timeout or 3))
        _enrich_missing_abstracts(
            deduped,
            topic=query,
            cache_dir=cache_dir,
            retry_rounds=int(ae.get("retry_rounds", 3)),
            backoff_base_seconds=float(ae.get("backoff_base_seconds", 0.5)),
            min_abstract_chars=int(ae.get("min_abstract_chars", 80)),
            max_papers_total=int(ae.get("max_papers_total", 200)),
            abstract_timeout=timeout_seconds,
        )

    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Search OpenAlex and write papers.jsonl")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--output", required=True, type=Path, help="Output .jsonl path")
    parser.add_argument("--max-results", type=int, default=200, help="Max results to write (default: 200)")
    parser.add_argument("--mailto", default=None, help="Optional contact email for OpenAlex polite pool")
    parser.add_argument("--min-year", type=int, default=None, help="Filter: min publication year")
    parser.add_argument("--max-year", type=int, default=None, help="Filter: max publication year")
    # 摘要补齐开关：默认跟随 config.yaml；可用 CLI 显式覆盖
    parser.add_argument(
        "--enrich-abstracts",
        dest="enrich_abstracts",
        action="store_const",
        const=True,
        default=None,
        help="Force enable multi-source abstract enrichment (default: follow config.yaml)",
    )
    parser.add_argument(
        "--no-enrich-abstracts",
        dest="enrich_abstracts",
        action="store_const",
        const=False,
        help="Force disable multi-source abstract enrichment",
    )
    parser.add_argument(
        "--abstract-timeout",
        type=int,
        default=None,
        help="Optional: override abstract enrichment API timeout seconds (default: config.yaml or 3)",
    )
    parser.add_argument("--cache-dir", type=Path, default=None, help="API cache directory path (default: no caching)")
    args = parser.parse_args()

    papers = search_openalex(
        query=args.query,
        max_results=args.max_results,
        mailto=args.mailto,
        min_year=args.min_year,
        max_year=args.max_year,
        cache_dir=args.cache_dir,
        enrich_abstracts=args.enrich_abstracts,
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
