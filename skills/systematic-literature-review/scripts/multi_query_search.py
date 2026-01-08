#!/usr/bin/env python3
"""
multi_query_search.py - 多查询并行检索并合并结果

用途：
  - 为 systematic-literature-review 的 Pipeline（阶段 1）提供"多查询检索"能力
  - 接收 AI 生成的查询列表，并行检索 OpenAlex
  - 去重合并结果，生成 papers.jsonl

输入：
  - --queries: JSON 文件，包含 [{"query": "...", "rationale": "..."}, ...]
  - 或 --query-list: 直接传入查询列表（JSON 字符串）

输出：
  - papers.jsonl：合并后的候选文献
  - search_log.json：检索日志（每个查询的结果量）

v1.1 - 2026-01-02 (新增查询质量评估)
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


def multi_search(
    queries: List[Dict[str, str]],
    max_results_per_query: int,
    mailto: Optional[str],
    min_year: Optional[int],
    max_year: Optional[int],
    polite_delay: tuple[float, float] = (0.5, 2.0),
    cache_dir: Optional[Path] = None,  # API 缓存目录
) -> tuple[List[Dict[str, Any]], List[SearchLog]]:
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
            papers = search_openalex(
                query=query_str,
                max_results=max_results_per_query,
                mailto=mailto,
                min_year=min_year,
                max_year=max_year,
                cache_dir=cache_dir,  # 传递缓存目录参数
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
            quality_label=quality_label
        ))

        # 礼貌延迟
        if i < len(queries):
            delay = random.uniform(*polite_delay)
            print(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)

    # 全局去重
    deduped = _dedupe_papers(all_papers)

    return deduped, logs


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
    papers, logs = multi_search(
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
