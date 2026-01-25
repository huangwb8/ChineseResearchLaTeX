#!/usr/bin/env python3
"""
multi_query_search.py - 多查询并行检索并合并结果

用途：
  - 为 systematic-literature-review 的 Pipeline（阶段 1）提供"多查询检索"能力
  - 接收 AI 生成的查询列表，多源检索并自动降级（优先 OpenAlex，Semantic Scholar 语义增强，Crossref 兜底）
  - 去重合并结果，生成 papers.jsonl

输入：
  - --queries: JSON 文件，包含 [{"query": "...", "rationale": "..."}, ...]
  - 或 --query-list: 直接传入查询列表（JSON 字符串）

输出：
  - papers.jsonl：合并后的候选文献
  - search_log.json：检索日志（每个查询的结果量）

v1.1 - 2026-01-02 (新增查询质量评估)
v1.2 - 2026-01-25 (新增：多源检索 + 自动降级 + Semantic Scholar 限流保护)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# 导入 openalex_search.py 中的检索函数
try:
    from openalex_search import search_openalex, _work_to_paper
except ImportError:
    # 如果导入失败，定义简化版
    def search_openalex(query: str, max_results: int, **kwargs) -> List[Dict[str, Any]]:
        raise RuntimeError("无法导入 openalex_search 模块")

# 多源检索（零配置）
try:
    from semantic_scholar_search import search_semantic_scholar
except ImportError:
    search_semantic_scholar = None  # type: ignore[assignment]

try:
    from crossref_search import search_crossref
except ImportError:
    search_crossref = None  # type: ignore[assignment]

try:
    from multi_source_abstract import AbstractFetcher
except ImportError:
    AbstractFetcher = None  # type: ignore[assignment]

try:
    from config_loader import load_config
except ImportError:
    load_config = None  # type: ignore[assignment]

try:
    from provider_detector import ProviderDetector
    from rate_limiter import RateLimiter
    from global_rate_limiter import GlobalRateLimiter
    from exponential_backoff_retry import ExponentialBackoffRetry
    from api_health_monitor import APIHealthMonitor
except ImportError:
    ProviderDetector = None  # type: ignore[assignment]
    RateLimiter = None  # type: ignore[assignment]
    GlobalRateLimiter = None  # type: ignore[assignment]
    ExponentialBackoffRetry = None  # type: ignore[assignment]
    APIHealthMonitor = None  # type: ignore[assignment]


@dataclass
class ProviderAttempt:
    provider: str
    status: str  # success|error|skipped
    results: int = 0
    reason: str = ""
    error: str = ""


@dataclass
class SearchLog:
    """单次查询的日志（含质量评估）"""
    query: str
    rationale: str
    returned: int
    unique: int
    notes: str = ""
    # 质量评估字段（v1.1 新增）
    dedupe_rate: float = field(default=None)
    quality_score: float = field(default=None)
    quality_label: str = field(default=None)
    # 多源/降级信息（v1.2 新增）
    provider_used: str = field(default="")
    attempts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class QualitySummary:
    """质量评估汇总"""
    excellent: int = field(default=0)  # 优秀（score >= 0.8）
    good: int = field(default=0)       # 良好（0.6 <= score < 0.8）
    fair: int = field(default=0)       # 一般（0.4 <= score < 0.6）
    poor: int = field(default=0)       # 较差（score < 0.4）
    recommendations: List[str] = field(default_factory=list)


def _load_queries(queries_path: Optional[Path], query_list: Optional[str]) -> List[Dict[str, str]]:
    """加载查询列表"""
    if queries_path and queries_path.exists():
        raw = queries_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data.get("queries", [])

    if query_list:
        data = json.loads(query_list)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("queries", data.get("queries", []))

    # 降级方案：单一查询
    return [{"query": "deep learning", "rationale": "降级方案：硬编码查询"}]


def _dedupe_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去重：优先 DOI，其次 title+year"""
    seen: set[str] = set()
    deduped: list[dict] = []

    for p in papers:
        # 优先用 DOI
        key = p.get("doi") or ""
        if not key:
            # 降级：title + year
            title = (p.get("title") or "").strip().lower()
            year = p.get("year")
            key = f"{title}::{year}"

        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(p)

    return deduped


def _assess_query_quality(returned: int, unique: int) -> tuple[float, str]:
    """
    评估单个查询的质量

    Args:
        returned: 查询返回的文献数
        unique: 去重后的独有文献数

    Returns:
        (quality_score, quality_label)
        - quality_score: 质量评分 (0-1)
        - quality_label: 质量标签（"优秀"/"良好"/"一般"/"较差"）

    评估维度：
    1. 去重率 (dedupe_rate = unique / returned):
       - ≥ 80%: 查询精确，噪声少
       - 60-80%: 良好
       - 40-60%: 一般
       - < 40%: 查询模糊，噪声多

    2. 召回贡献 (unique):
       - ≥ 30: 高贡献
       - 15-29: 中等贡献
       - < 15: 低贡献

    质量评分公式：
    quality_score = (dedupe_rate * 0.6) + (min(unique / 50, 1.0) * 0.4)

    质量标签：
    - 优秀: score >= 0.8
    - 良好: 0.6 <= score < 0.8
    - 一般: 0.4 <= score < 0.6
    - 较差: score < 0.4
    """
    if returned == 0:
        return 0.0, "较差"

    # 计算去重率
    dedupe_rate = unique / returned

    # 计算召回贡献评分（最大 1.0）
    contribution_score = min(unique / 50.0, 1.0)

    # 综合质量评分（去重率权重 60%，召回贡献权重 40%）
    quality_score = dedupe_rate * 0.6 + contribution_score * 0.4

    # 质量标签
    if quality_score >= 0.8:
        quality_label = "优秀"
    elif quality_score >= 0.6:
        quality_label = "良好"
    elif quality_score >= 0.4:
        quality_label = "一般"
    else:
        quality_label = "较差"

    return quality_score, quality_label


def _generate_quality_summary(logs: List[SearchLog]) -> QualitySummary:
    """
    生成质量评估汇总

    Args:
        logs: 检索日志列表

    Returns:
        QualitySummary 对象，包含质量统计和改进建议
    """
    summary = QualitySummary()

    for log in logs:
        if log.quality_label == "优秀":
            summary.excellent += 1
        elif log.quality_label == "良好":
            summary.good += 1
        elif log.quality_label == "一般":
            summary.fair += 1
        elif log.quality_label == "较差":
            summary.poor += 1

    # 生成改进建议
    for log in logs:
        if log.quality_label == "较差":
            if log.dedupe_rate is not None and log.dedupe_rate < 0.4:
                summary.recommendations.append(
                    f"查询 '{log.query[:40]}...' 质量较差（去重率 {log.dedupe_rate:.1%}），"
                    f"建议优化检索词以提高精确度"
                )
            elif log.unique < 10:
                summary.recommendations.append(
                    f"查询 '{log.query[:40]}...' 召献贡献低（仅 {log.unique} 篇），"
                    f"可考虑移除或调整"
                )
        elif log.quality_label == "一般" and log.unique < 15:
            summary.recommendations.append(
                f"查询 '{log.query[:40]}...' 贡献一般（{log.unique} 篇），"
                f"可考虑优化或与其他查询合并"
            )

    return summary


def _load_search_config() -> Dict[str, Any]:
    """
    加载技能配置中的 search 段（若缺失则返回空 dict）。

    说明：
    - pipeline_runner 固定 cwd=work_dir，不能依赖相对路径读取 config.yaml；
      因此这里优先使用 config_loader.load_config（它基于 __file__ 定位）。
    """
    if load_config is None:
        return {}
    try:
        cfg = load_config()
        return cfg.get("search", {}) if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _enrich_missing_abstracts_global(
    papers: list[dict],
    *,
    topic: str,
    search_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    全局补齐摘要（有限上限 + 有限重试）。

    返回简要统计，写入 search_log 便于调试与后续写作规避“摘要缺失”文献。
    """
    ae = (search_cfg.get("abstract_enrichment") or {}) if isinstance(search_cfg.get("abstract_enrichment"), dict) else {}
    if not bool(ae.get("enabled", False)):
        return {"enabled": False}

    if AbstractFetcher is None or not papers:
        return {"enabled": True, "skipped": True, "reason": "AbstractFetcher not available or empty papers"}

    max_total = int(ae.get("max_papers_total", 200))
    retry_rounds = int(ae.get("retry_rounds", 3))
    backoff_base = float(ae.get("backoff_base_seconds", 0.5))
    min_chars = int(ae.get("min_abstract_chars", 80))

    def needs(p: dict) -> bool:
        a = p.get("abstract") or ""
        return (not isinstance(a, str)) or len(a.strip()) < min_chars

    candidates = [p for p in papers if needs(p)]
    candidates.sort(key=lambda p: (0 if (p.get("doi") or "") else 1, -int(p.get("year") or 0)))
    if max_total > 0:
        candidates = candidates[:max_total]

    fetcher = AbstractFetcher(timeout=3)

    filled = 0
    attempted = 0
    for p in candidates:
        doi = str(p.get("doi") or "").strip()
        title = str(p.get("title") or "").strip()

        attempted += 1
        ok = False
        for r in range(max(1, retry_rounds)):
            abstract = None
            if doi:
                abstract = fetcher.fetch_by_doi(doi, topic=topic)
            if not abstract and title:
                abstract = fetcher.fetch_by_title(title, topic=topic)
            if abstract and isinstance(abstract, str) and len(abstract.strip()) >= min_chars:
                p["abstract"] = abstract.strip()
                p["abstract_status"] = "present"
                p["abstract_enrichment"] = {"attempts": r + 1, "filled": True}
                ok = True
                filled += 1
                break
            if r < max(0, retry_rounds - 1):
                time.sleep(max(0.0, backoff_base) * (2**r))

        if not ok:
            p["abstract_status"] = "missing"
            p["quality_warnings"] = list(p.get("quality_warnings") or [])
            if "missing_abstract" not in p["quality_warnings"]:
                p["quality_warnings"].append("missing_abstract")
            p["abstract_enrichment"] = {"attempts": retry_rounds, "filled": False}

    missing_after = sum(1 for p in papers if needs(p))
    return {
        "enabled": True,
        "attempted": attempted,
        "filled": filled,
        "missing_after": missing_after,
        "min_abstract_chars": min_chars,
        "retry_rounds": retry_rounds,
        "max_papers_total": max_total,
    }


def _search_one_query_with_fallback(
    query: str,
    *,
    max_results: int,
    mailto: Optional[str],
    min_year: Optional[int],
    max_year: Optional[int],
    cache_dir: Optional[Path],
    search_cfg: Dict[str, Any],
    detector: Optional[Any],
    rate_limiter: Optional[Any],
    global_limiter: Optional[Any],
    retry: Optional[Any],
    health: Optional[Any],
) -> tuple[list[dict], str, list[ProviderAttempt]]:
    provider_priority = list(search_cfg.get("provider_priority") or [])
    if not provider_priority:
        provider_priority = ["openalex"]

    # 按查询类型选择“优先尝试的 provider”，再按 provider_priority 降级
    preferred = None
    if rate_limiter is not None:
        try:
            preferred = rate_limiter.recommended_provider(provider_priority, query=query)
        except Exception:
            preferred = None
    providers_to_try = []
    if preferred:
        providers_to_try.append(preferred)
    providers_to_try.extend([p for p in provider_priority if p != preferred])

    fallback_cfg = search_cfg.get("fallback", {}) if isinstance(search_cfg.get("fallback", {}), dict) else {}
    fallback_enabled = bool(fallback_cfg.get("enabled", False))

    attempts: list[ProviderAttempt] = []
    chosen_provider = ""
    supported_providers = {"openalex", "semantic_scholar", "crossref"}

    def _check_provider_available(p: str) -> tuple[bool, str]:
        if detector is None:
            return True, ""
        try:
            st = detector.detect(p)
            if not getattr(st, "available", False):
                return False, str(getattr(st, "reason", "not available"))
            return True, ""
        except Exception as e:
            return False, f"detect failed: {e}"

    def _do_search(provider: str) -> list[dict]:
        if provider == "openalex":
            return search_openalex(
                query=query,
                max_results=max_results,
                mailto=mailto,
                min_year=min_year,
                max_year=max_year,
                cache_dir=cache_dir,
                enrich_abstracts=False,  # multi_query 场景统一在全局去重后补摘要，避免 per-query 扩散请求
            )
        if provider == "semantic_scholar":
            if search_semantic_scholar is None:
                raise RuntimeError("semantic_scholar_search 未就绪（缺少模块）")
            return search_semantic_scholar(
                query=query,
                max_results=max_results,
                cache_dir=cache_dir,
                rate_limiter=rate_limiter,
                retry=retry,
            )
        if provider == "crossref":
            if search_crossref is None:
                raise RuntimeError("crossref_search 未就绪（缺少模块）")
            return search_crossref(
                query=query,
                max_results=max_results,
                cache_dir=cache_dir,
                retry=retry,
                mailto=mailto,
            )
        raise RuntimeError(f"不支持的 provider: {provider}")

    for provider in providers_to_try:
        # 注意：mcp/duckduckgo 等通常由宿主工具提供，不在脚本内实现；这里明确跳过，避免误记为“失败”。
        if provider not in supported_providers:
            attempts.append(
                ProviderAttempt(
                    provider=provider,
                    status="skipped",
                    reason="provider not supported in python script (host tool required)",
                )
            )
            continue

        ok, reason = _check_provider_available(provider)
        if not ok:
            attempts.append(ProviderAttempt(provider=provider, status="skipped", reason=reason))
            continue

        if health is not None:
            try:
                if not health.is_available(provider):
                    attempts.append(
                        ProviderAttempt(
                            provider=provider,
                            status="skipped",
                            reason=f"health blacklisted ({health.blacklist_remaining(provider)}s)",
                        )
                    )
                    continue
            except Exception:
                # 健康监控失败不阻断
                pass

        if global_limiter is not None:
            try:
                st = global_limiter.can_request()
                if not getattr(st, "can_request", False):
                    # 顺序执行场景：直接 sleep 冷却，避免直接失败
                    cooldown = int(getattr(st, "cooldown_seconds", 0) or 0)
                    attempts.append(
                        ProviderAttempt(provider=provider, status="skipped", reason=getattr(st, "reason", "global limited"))
                    )
                    if cooldown > 0:
                        time.sleep(cooldown)
            except Exception:
                pass

        if rate_limiter is not None and provider == "semantic_scholar":
            try:
                st = rate_limiter.can_call("semantic_scholar")
                if not getattr(st, "can_call", False):
                    attempts.append(ProviderAttempt(provider=provider, status="skipped", reason=getattr(st, "reason", "rate limited")))
                    # 语义源被限流时，按降级策略回到 OpenAlex
                    continue
            except Exception:
                pass

        try:
            if global_limiter is not None:
                try:
                    global_limiter.record_request()
                except Exception:
                    pass

            papers = _do_search(provider)
            attempts.append(ProviderAttempt(provider=provider, status="success", results=len(papers)))
            chosen_provider = provider
            if health is not None:
                try:
                    health.record_success(provider)
                except Exception:
                    pass

            # OpenAlex 主力 + Semantic Scholar 补齐：仅在 OpenAlex 召回不足时触发语义增强，减少限流风险
            if (
                provider == "openalex"
                and fallback_enabled
                and ("semantic_scholar" in provider_priority)
                and search_semantic_scholar is not None
                and len(papers) < max(5, int(max_results * 0.7))
            ):
                need = max(0, int(max_results) - len(papers))
                if need > 0 and rate_limiter is not None:
                    try:
                        st2 = rate_limiter.can_call("semantic_scholar")
                        if getattr(st2, "can_call", False):
                            if global_limiter is not None:
                                try:
                                    global_limiter.record_request()
                                except Exception:
                                    pass
                            more = search_semantic_scholar(
                                query=query,
                                max_results=need,
                                cache_dir=cache_dir,
                                rate_limiter=rate_limiter,
                                retry=retry,
                            )
                            attempts.append(ProviderAttempt(provider="semantic_scholar", status="success", results=len(more), reason="top-up for low recall"))
                            # merge + dedupe
                            merged = papers + more
                            papers = _dedupe_papers(merged)[:max_results]
                        else:
                            attempts.append(ProviderAttempt(provider="semantic_scholar", status="skipped", reason=getattr(st2, "reason", "rate limited")))
                    except Exception as e:
                        attempts.append(ProviderAttempt(provider="semantic_scholar", status="error", error=str(e)))

            # 若降级关闭：成功即返回；若开启：允许在 0 结果时继续尝试下一个源
            if papers or not fallback_enabled:
                return papers, chosen_provider, attempts
        except Exception as e:
            attempts.append(ProviderAttempt(provider=provider, status="error", error=str(e)))
            if health is not None:
                try:
                    health.record_failure(provider)
                except Exception:
                    pass
            continue

    return [], chosen_provider, attempts


def multi_search(
    queries: List[Dict[str, str]],
    max_results_per_query: int,
    mailto: Optional[str],
    min_year: Optional[int],
    max_year: Optional[int],
    polite_delay: tuple[float, float] = (0.5, 2.0),
    cache_dir: Optional[Path] = None,  # API 缓存目录
) -> tuple[List[Dict[str, Any]], List[SearchLog], Dict[str, Any], Dict[str, Any]]:
    """
    多查询并行检索

    Args:
        queries: 查询列表，每个元素包含 {"query": "...", "rationale": "..."}
        max_results_per_query: 每个查询最多返回结果数
        mailto: OpenAlex polite pool email
        min_year: 最小年份
        max_year: 最大年份
        polite_delay: 礼貌延迟范围（秒）
        cache_dir: API 缓存目录路径

    Returns:
        (合并后的论文列表, 检索日志列表)
    """
    all_papers: list[dict] = []
    logs: list[SearchLog] = []

    search_cfg = _load_search_config()
    fallback_cfg = search_cfg.get("fallback", {}) if isinstance(search_cfg.get("fallback", {}), dict) else {}
    protection_cfg = search_cfg.get("rate_limit_protection", {}) if isinstance(search_cfg.get("rate_limit_protection", {}), dict) else {}
    protection_enabled = bool(protection_cfg.get("enabled", True))

    detector = ProviderDetector(
        cache_ttl=int(fallback_cfg.get("detection_ttl", 300)),
        cache_enabled=bool(fallback_cfg.get("cache_detections", True)),
    ) if ProviderDetector is not None else None
    rate_limiter = RateLimiter(protection_cfg) if (RateLimiter is not None and protection_enabled) else None
    global_limiter = None
    if protection_enabled and GlobalRateLimiter is not None and isinstance(protection_cfg.get("global", {}), dict):
        gcfg = protection_cfg.get("global", {}) or {}
        if bool(gcfg.get("enabled", False)):
            global_limiter = GlobalRateLimiter(
                max_per_minute=int(gcfg.get("max_calls_per_minute", 120)),
                cooldown_on_limit=int(gcfg.get("cooldown_on_limit", 30)),
            )
    retry = ExponentialBackoffRetry((protection_cfg.get("retry") or {})) if (ExponentialBackoffRetry is not None and protection_enabled) else None
    health = APIHealthMonitor((protection_cfg.get("health_monitor") or {})) if (APIHealthMonitor is not None and protection_enabled) else None

    for i, q in enumerate(queries, 1):
        query_str = q.get("query", "")
        rationale = q.get("rationale", "")
        if not query_str:
            logs.append(SearchLog(
                query="", rationale=rationale, returned=0, unique=0, notes="查询字符串为空"
            ))
            continue

        print(f"\n[{i}/{len(queries)}] 检索: {query_str}")
        print(f"  理由: {rationale}")

        try:
            papers, provider_used, attempts = _search_one_query_with_fallback(
                query_str,
                max_results=max_results_per_query,
                mailto=mailto,
                min_year=min_year,
                max_year=max_year,
                cache_dir=cache_dir,
                search_cfg=search_cfg,
                detector=detector,
                rate_limiter=rate_limiter,
                global_limiter=global_limiter,
                retry=retry,
                health=health,
            )
            print(f"  返回: {len(papers)} 篇")
        except Exception as e:
            print(f"  ✗ 检索失败: {e}")
            logs.append(SearchLog(
                query=query_str, rationale=rationale, returned=0, unique=0, notes=f"检索失败: {e}"
            ))
            continue

        # 计算本次查询的独有贡献（去重前）
        seen_keys = {
            p.get("doi") or f'{p.get("title", "").strip().lower()}::{p.get("year")}'
            for p in all_papers
        }
        new_papers = [
            p for p in papers
            if (p.get("doi") or f'{p.get("title", "").strip().lower()}::{p.get("year")}')
               not in seen_keys
        ]
        unique_count = len(new_papers)

        all_papers.extend(papers)

        # 质量评估（v1.1 新增）
        quality_score, quality_label = _assess_query_quality(len(papers), unique_count)
        dedupe_rate = unique_count / len(papers) if len(papers) > 0 else 0.0

        logs.append(SearchLog(
            query=query_str,
            rationale=rationale,
            returned=len(papers),
            unique=unique_count,
            notes="",
            dedupe_rate=round(dedupe_rate, 3),
            quality_score=round(quality_score, 3),
            quality_label=quality_label,
            provider_used=provider_used or "",
            attempts=[asdict(a) for a in (attempts or [])],
        ))

        # 礼貌延迟
        if i < len(queries):
            # 兼容旧参数：仍保留随机区间，但允许由配置给出更小的“礼貌延迟”
            delay = random.uniform(*polite_delay)
            if rate_limiter is not None and (provider_used or "") == "openalex":
                try:
                    oa_delay = float(getattr(rate_limiter, "openalex_polite_delay", 0.0) or 0.0)
                    if oa_delay > 0:
                        delay = max(oa_delay, min(delay, oa_delay + 0.25))
                except Exception:
                    pass
            print(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)

    # 全局去重
    deduped = _dedupe_papers(all_papers)

    # 全局补摘要（默认启用：上限 + 有限重试）
    topic_for_enrich = (queries[0].get("query") or "") if queries else ""
    abstract_enrichment_summary = _enrich_missing_abstracts_global(
        deduped,
        topic=topic_for_enrich,
        search_cfg=search_cfg,
    )

    rate_limit_summary: Dict[str, Any] = {}
    if rate_limiter is not None:
        try:
            rate_limit_summary = rate_limiter.summary()
        except Exception:
            rate_limit_summary = {}

    return deduped, logs, rate_limit_summary, abstract_enrichment_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="多查询并行检索并合并结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--queries",
        type=Path,
        help="查询 JSON 文件路径，格式: {\"queries\": [{\"query\": \"...\", \"rationale\": \"...\"}, ...]}"
    )
    parser.add_argument(
        "--query-list",
        help="直接传入查询列表（JSON 字符串）",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="输出 papers.jsonl 路径",
    )
    parser.add_argument(
        "--search-log",
        default="search_log_multi_query.json",
        help="检索日志输出路径（默认: search_log_multi_query.json）",
    )
    parser.add_argument(
        "--max-results-per-query",
        type=int,
        default=50,
        help="每个查询最多返回结果数（默认: 50）",
    )
    parser.add_argument(
        "--mailto",
        default=None,
        help="OpenAlex polite pool email（可选）",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=None,
        help="最小年份过滤",
    )
    parser.add_argument(
        "--max-year",
        type=int,
        default=None,
        help="最大年份过滤",
    )
    parser.add_argument(
        "--max-total",
        type=int,
        default=500,
        help="合并后的最大结果数（默认: 500）",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="API 缓存目录路径",
    )
    args = parser.parse_args()

    # 加载查询
    queries = _load_queries(args.queries, args.query_list)
    if not queries:
        print("✗ 错误：未提供有效查询", file=sys.stderr)
        return 1

    print(f"加载了 {len(queries)} 个查询")

    # 执行多查询检索
    papers, logs, rate_limit_summary, abstract_enrichment_summary = multi_search(
        queries=queries,
        max_results_per_query=args.max_results_per_query,
        mailto=args.mailto,
        min_year=args.min_year,
        max_year=args.max_year,
        cache_dir=args.cache_dir,  # 传递缓存目录参数
    )

    # 限制总结果数
    if len(papers) > args.max_total:
        print(f"\n总结果数 {len(papers)} 超过上限 {args.max_total}，截断...")
        papers = papers[:args.max_total]

    # 写入 papers.jsonl
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    # 写入检索日志
    # 生成质量汇总（v1.1 新增）
    quality_summary = _generate_quality_summary(logs)

    log_data = {
        "total_queries": len(queries),
        "total_returned": sum(log.returned for log in logs),
        "total_unique": len(papers),
        "queries": [asdict(log) for log in logs],
        "quality_summary": asdict(quality_summary),  # v1.1 新增
    }
    if rate_limit_summary:
        log_data["rate_limit_summary"] = rate_limit_summary
    if abstract_enrichment_summary:
        log_data["abstract_enrichment_summary"] = abstract_enrichment_summary
    with open(args.search_log, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    # 输出摘要
    print(f"\n" + "=" * 60)
    print("检索完成")
    print(f"  - 查询数: {len(queries)}")
    print(f"  - 总返回: {log_data['total_returned']} 篇")
    print(f"  - 去重后: {log_data['total_unique']} 篇")
    print(f"  - 输出: {args.output}")
    print(f"  - 日志: {args.search_log}")

    # 质量评估汇总（v1.1 新增）
    qs = log_data.get("quality_summary", {})
    print(f"\n质量评估汇总:")
    print(f"  - 优秀: {qs.get('excellent', 0)} 个")
    print(f"  - 良好: {qs.get('good', 0)} 个")
    print(f"  - 一般: {qs.get('fair', 0)} 个")
    print(f"  - 较差: {qs.get('poor', 0)} 个")

    if qs.get("recommendations"):
        print(f"\n改进建议:")
        for rec in qs.get("recommendations", [])[:3]:  # 最多显示 3 条建议
            print(f"  - {rec}")

    print("=" * 60)

    # 详细日志
    print("\n各查询详情:")
    for log in logs:
        quality_tag = f"[{log.quality_label}]" if log.quality_label else ""
        print(f"  - {log.query[:50]}... -> {log.returned} 篇（新增 {log.unique} 篇） {quality_tag}")
        if log.notes:
            print(f"    备注: {log.notes}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
