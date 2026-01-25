#!/usr/bin/env python3
"""
multi_source_abstract.py - 多源摘要补充模块

功能：
  1. 从多个备用 API 获取摘要（Semantic Scholar、Crossref、PubMed）
  2. 自动识别主题类型（生物医学/通用）以调整 API 优先级
  3. 实现超时控制和降级策略
  4. 提供批量处理能力（支持并发）

Usage:
    fetcher = AbstractFetcher(timeout=5)
    abstract = fetcher.fetch_by_doi("10.1126/science.1231143", topic="CRISPR gene editing")

Author: systematic-literature-review skill
Version: 1.0.0
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# ============================================================================
# 常量定义
# ============================================================================

# 生物医学关键词（用于判断主题类型）
BIOMED_KEYWORDS = {
    # 英文关键词
    "cancer", "tumor", "ultrasound", "mri", "ct", "x-ray", "clinical", "diagnosis",
    "therapy", "pathology", "disease", "patient", "medical", "biomedical", "health",
    "imaging", "radiology", "oncology", "surgery", "treatment", "drug", "pharmaceutical",
    "gene", "protein", "cell", "molecular", "genetic", "virus", "bacteria", "infection",
    # 中文关键词
    "病理", "肿瘤", "癌症", "超声", "临床", "诊断", "治疗", "医学", "生物",
    "影像", "影像学", "放射", "肿瘤学", "外科", "药物", "基因", "蛋白质",
    "细胞", "分子", "遗传", "病毒", "细菌", "感染", "健康", "患者"
}

# API 端点配置
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
CROSSREF_API = "https://api.crossref.org/works"
OPENALEX_API = "https://api.openalex.org/works"


# ============================================================================
# 工具函数
# ============================================================================

def _normalize_doi(raw: str) -> str:
    """标准化 DOI 格式"""
    if not raw:
        return ""
    raw = raw.strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE).strip()
    return raw.lower()


def _is_biomedical_topic(topic: str) -> bool:
    """
    判断是否为生物医学主题

    Args:
        topic: 研究主题描述

    Returns:
        True 如果主题包含生物医学关键词
    """
    if not topic:
        return False
    topic_lower = topic.lower()
    return any(keyword in topic_lower for keyword in BIOMED_KEYWORDS)


def _clean_abstract(text: str) -> str:
    """
    清理摘要文本：去除多余空白、HTML 标签等

    Args:
        text: 原始摘要文本

    Returns:
        清理后的摘要
    """
    if not text:
        return ""
    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", " ", text)
    # 去除多余空白
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _make_request(url: str, timeout: int, headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
    """
    发起 HTTP GET 请求并解析 JSON 响应

    Args:
        url: 请求 URL
        timeout: 超时时间（秒）
        headers: 请求头

    Returns:
        解析后的 JSON 对象，失败返回 None
    """
    default_headers = {
        "User-Agent": "pipelines/skills systematic-literature-review multi-source-abstract",
        "Accept": "application/json",
    }
    if headers:
        default_headers.update(headers)

    try:
        req = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            data = resp.read()
            return json.loads(data.decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None


# ============================================================================
# 单个 API 获取函数
# ============================================================================

def _fetch_from_semantic_scholar(doi: str, timeout: int) -> Optional[str]:
    """
    从 Semantic Scholar API 获取摘要

    Args:
        doi: 论文 DOI
        timeout: 超时时间（秒）

    Returns:
        摘要文本，失败返回 None
    """
    if not doi:
        return None

    # Semantic Scholar 支持两种 DOI 格式：DOI:10.xxx 或直接 https://doi.org/10.xxx
    normalized_doi = _normalize_doi(doi)
    url = f"{SEMANTIC_SCHOLAR_API}/DOI:{normalized_doi}"
    params = {"fields": "abstract"}

    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    data = _make_request(full_url, timeout)

    if data and "abstract" in data:
        abstract = data["abstract"]
        if abstract:
            return _clean_abstract(abstract)

    return None


def _fetch_from_pubmed(doi: str, timeout: int) -> Optional[str]:
    """
    从 PubMed API 获取摘要

    Args:
        doi: 论文 DOI
        timeout: 超时时间（秒）

    Returns:
        摘要文本，失败返回 None
    """
    if not doi:
        return None

    # 步骤 1：使用 esearch 查找 PubMed ID
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": f"{doi}[doi]",
        "retmax": "1",
        "retmode": "json",
        "tool": "systematic-literature-review",
    }

    search_response = _make_request(
        f"{search_url}?{urllib.parse.urlencode(search_params)}", timeout
    )

    if not search_response:
        return None

    idlist = search_response.get("esearchresult", {}).get("idlist", [])
    if not idlist:
        return None

    pmid = idlist[0]

    # 步骤 2：使用 esummary 获取摘要（如果有的话）
    # 注意：esummary 不直接提供摘要，需要用 efetch
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "id": pmid,
        "rettype": "abstract",
        "retmode": "xml",
        "tool": "systematic-literature-review",
    }

    try:
        req = urllib.request.Request(
            f"{fetch_url}?{urllib.parse.urlencode(fetch_params)}",
            headers={"User-Agent": "pipelines/skills systematic-literature-review multi-source-abstract"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            xml_data = resp.read().decode("utf-8", errors="replace")

            # 简单解析 XML 提取 AbstractText
            abstract_match = re.search(r"<AbstractText>([^<]+)</AbstractText>", xml_data, re.DOTALL)
            if abstract_match:
                return _clean_abstract(abstract_match.group(1))
    except Exception:
        return None

    return None


def _fetch_from_crossref(doi: str, timeout: int) -> Optional[str]:
    """
    从 Crossref API 获取摘要

    Args:
        doi: 论文 DOI
        timeout: 超时时间（秒）

    Returns:
        摘要文本，失败返回 None
    """
    if not doi:
        return None

    normalized_doi = _normalize_doi(doi)
    url = f"{CROSSREF_API}/{urllib.parse.quote(normalized_doi)}"

    data = _make_request(url, timeout)

    if data and "message" in data:
        message = data["message"]
        # Crossref 可能在不同字段中包含摘要
        for key in ["abstract", "description", "subtitle"]:
            if key in message and message[key]:
                value = message[key]
                if isinstance(value, list):
                    value = value[0] if value else ""
                if isinstance(value, str):
                    return _clean_abstract(value)

    return None


def _fetch_from_openalex_by_doi(doi: str, timeout: int) -> Optional[str]:
    """
    从 OpenAlex API 直接获取摘要（作为备用）

    注意：这通常不会比原始 openalex_search 效果更好，
    但在某些情况下 OpenAlex 可能重新索引了摘要

    Args:
        doi: 论文 DOI
        timeout: 超时时间（秒）

    Returns:
        摘要文本，失败返回 None
    """
    if not doi:
        return None

    normalized_doi = _normalize_doi(doi)
    url = f"{OPENALEX_API}/https://doi.org/{urllib.parse.quote(normalized_doi)}"

    data = _make_request(url, timeout)

    if data and "abstract_inverted_index" in data:
        # 重建摘要
        positions: Dict[int, str] = {}
        for token, idxs in data["abstract_inverted_index"].items():
            for idx in idxs:
                if idx not in positions:
                    positions[idx] = token
        if positions:
            return _clean_abstract(" ".join(positions[i] for i in sorted(positions)))

    return None


# ============================================================================
# 统计数据类
# ============================================================================

@dataclass
class FetchStatistics:
    """摘要获取统计"""
    total_papers: int = 0
    openalex_has_abstract: int = 0
    semantic_scholar_success: int = 0
    pubmed_success: int = 0
    crossref_success: int = 0
    openalex_fallback_success: int = 0
    total_success: int = 0
    total_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_papers": self.total_papers,
            "openalex_coverage": f"{(self.openalex_has_abstract / max(1, self.total_papers) * 100):.1f}%",
            "semantic_scholar_enriched": self.semantic_scholar_success,
            "pubmed_enriched": self.pubmed_success,
            "crossref_enriched": self.crossref_success,
            "openalex_fallback_enriched": self.openalex_fallback_success,
            "total_enriched": self.semantic_scholar_success + self.pubmed_success + self.crossref_success + self.openalex_fallback_success,
            "final_coverage": f"{(self.total_success / max(1, self.total_papers) * 100):.1f}%",
            "total_failed": self.total_failed,
        }

    def __str__(self) -> str:
        d = self.to_dict()
        return (
            f"Abstract Fetch Statistics:\n"
            f"  Total papers: {d['total_papers']}\n"
            f"  OpenAlex coverage: {d['openalex_coverage']}\n"
            f"  Enriched from Semantic Scholar: {d['semantic_scholar_enriched']}\n"
            f"  Enriched from PubMed: {d['pubmed_enriched']}\n"
            f"  Enriched from Crossref: {d['crossref_enriched']}\n"
            f"  Enriched from OpenAlex fallback: {d['openalex_fallback_enriched']}\n"
            f"  Total enriched: {d['total_enriched']}\n"
            f"  Final coverage: {d['final_coverage']}\n"
            f"  Total failed: {d['total_failed']}"
        )


# ============================================================================
# 主获取器类
# ============================================================================

@dataclass
class AbstractFetcher:
    """
    多源摘要获取器

    Attributes:
        timeout: 单个 API 请求的超时时间（秒）
        max_retries: 最多尝试的备用 API 数量
        enable_semantic_scholar: 是否启用 Semantic Scholar
        enable_pubmed: 是否启用 PubMed
        enable_crossref: 是否启用 Crossref

    Note:
        OpenAlex 的条目并非都包含摘要，因此在“需要高摘要覆盖率”的场景（写作、对齐检查）
        可以启用该模块对缺失摘要的条目做多源补齐。
    """

    timeout: int = 3
    # 这里的 max_retries 表示“最多尝试的来源数量（不含 OpenAlex fallback）”，历史命名保留以避免破坏兼容性。
    # 实际顺序由 _get_api_priority 决定，且始终会在末尾追加 OpenAlex-by-DOI 作为兜底。
    max_retries: int = 3
    enable_semantic_scholar: bool = True
    enable_pubmed: bool = True
    enable_crossref: bool = True

    # 统计信息（内部使用）
    _stats: FetchStatistics = field(default_factory=FetchStatistics, init=False, repr=False)

    def _get_api_priority(self, topic: str) -> List[Callable[[str, int], Optional[str]]]:
        """
        根据主题类型返回 API 优先级列表

        优先级策略（基于测试结果）：
        1. Crossref - 在测试中表现最稳定
        2. Semantic Scholar - 数据质量高但部分受限
        3. PubMed - 仅生物医学主题
        4. OpenAlex fallback - 最后尝试

        Args:
            topic: 研究主题

        Returns:
            API 函数列表（按优先级排序）
        """
        is_biomed = _is_biomedical_topic(topic)

        # 主来源（最多取 N 个），OpenAlex fallback 始终追加在末尾
        primary: list[Callable[[str, int], Optional[str]]] = []
        if self.enable_crossref:
            primary.append(_fetch_from_crossref)
        if self.enable_semantic_scholar:
            primary.append(_fetch_from_semantic_scholar)
        if self.enable_pubmed:
            # 生物医学主题优先，其余主题放在更靠后的位置
            if is_biomed:
                primary.append(_fetch_from_pubmed)
            else:
                primary.append(_fetch_from_pubmed)

        max_sources = max(0, int(self.max_retries))
        primary = primary[:max_sources] if max_sources else primary

        return primary + [_fetch_from_openalex_by_doi]

    def fetch_by_doi(self, doi: str, topic: str = "") -> Optional[str]:
        """
        按 DOI 获取摘要（自动选择 API 优先级）

        Args:
            doi: 论文 DOI
            topic: 研究主题（用于判断主题类型）

        Returns:
            摘要文本，所有 API 失败返回 None
        """
        if not doi:
            return None

        self._stats.total_papers += 1

        # 按 API 优先级依次尝试
        for fetch_func in self._get_api_priority(topic):
            abstract = fetch_func(doi, self.timeout)
            if abstract:
                # 记录成功的 API
                func_name = fetch_func.__name__
                if "semantic_scholar" in func_name:
                    self._stats.semantic_scholar_success += 1
                elif "pubmed" in func_name:
                    self._stats.pubmed_success += 1
                elif "crossref" in func_name:
                    self._stats.crossref_success += 1
                elif "openalex_by_doi" in func_name:
                    self._stats.openalex_fallback_success += 1
                self._stats.total_success += 1
                return abstract

        self._stats.total_failed += 1
        return None

    def fetch_by_title(self, title: str, topic: str = "") -> Optional[str]:
        """
        按标题获取摘要（当 DOI 不可用时）

        注意：Semantic Scholar 支持标题查询，但精度较低

        Args:
            title: 论文标题
            topic: 研究主题

        Returns:
            摘要文本，失败返回 None
        """
        if not title:
            return None

        # 仅 Semantic Scholar 支持标题查询
        if not self.enable_semantic_scholar:
            return None

        url = f"{SEMANTIC_SCHOLAR_API}/search"
        params = {
            "query": title,
            "fields": "abstract,title",
            "limit": "1",
        }

        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        data = _make_request(full_url, self.timeout)

        if data and "data" in data and data["data"]:
            paper = data["data"][0]
            # 标题匹配度检查（简单的大小写不敏感比较）
            if title.lower().strip() == paper.get("title", "").lower().strip():
                if "abstract" in paper and paper["abstract"]:
                    self._stats.semantic_scholar_success += 1
                    self._stats.total_success += 1
                    return _clean_abstract(paper["abstract"])

        return None

    def fetch_batch(self, papers: List[Dict[str, Any]], topic: str = "", max_workers: int = 5) -> List[Dict[str, Any]]:
        """
        批量获取摘要（并发处理）

        Args:
            papers: 论文列表，每项至少包含 `doi` 和 `abstract` 字段
            topic: 研究主题
            max_workers: 最大并发数

        Returns:
            更新后的论文列表（abstract 字段可能被填充）
        """
        self._stats = FetchStatistics()  # 重置统计

        def enrich_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
            """为单篇论文补充摘要"""
            if paper.get("abstract"):
                # 已有摘要，记录统计
                self._stats.total_papers += 1
                self._stats.openalex_has_abstract += 1
                self._stats.total_success += 1
                return paper

            self._stats.total_papers += 1

            # 尝试按 DOI 获取
            doi = paper.get("doi") or paper.get("DOI") or ""
            if doi:
                abstract = self.fetch_by_doi(doi, topic)
                if abstract:
                    paper["abstract"] = abstract
                    return paper

            # 尝试按标题获取
            title = paper.get("title") or ""
            if title:
                abstract = self.fetch_by_title(title, topic)
                if abstract:
                    paper["abstract"] = abstract
                    return paper

            self._stats.total_failed += 1
            return paper

        # 并发处理
        result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(enrich_paper, paper.copy()): paper for paper in papers}
            for future in concurrent.futures.as_completed(futures):
                try:
                    result.append(future.result())
                except Exception:
                    # 失败时保留原论文
                    result.append(futures[future])

        return result

    def get_statistics(self) -> FetchStatistics:
        """
        获取获取统计

        Returns:
            FetchStatistics 对象
        """
        return self._stats

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._stats = FetchStatistics()


# ============================================================================
# 命令行接口
# ============================================================================

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-source abstract fetcher for academic papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # 按 DOI 获取摘要
    python multi_source_abstract.py --doi 10.1126/science.1231143

    # 按标题获取摘要
    python multi_source_abstract.py --title "CRISPR-Cas9 genome editing"

    # 批量处理 JSONL 文件
    python multi_source_abstract.py --input papers.jsonl --output papers_enriched.jsonl --topic "cancer research"

    # 仅使用特定 API
    python multi_source_abstract.py --doi 10.1126/science.1231143 --no-crossref --no-pubmed
        """
    )
    parser.add_argument("--doi", help="DOI to fetch abstract for")
    parser.add_argument("--title", help="Paper title to search")
    parser.add_argument("--topic", default="", help="Research topic (for API priority selection)")
    parser.add_argument("--input", type=Path, help="Input JSONL file path")
    parser.add_argument("--output", type=Path, help="Output JSONL file path")
    parser.add_argument("--timeout", type=int, default=5, help="API timeout in seconds (default: 5)")
    parser.add_argument("--max-workers", type=int, default=5, help="Max concurrent workers for batch mode (default: 5)")
    parser.add_argument("--no-semantic-scholar", action="store_true", help="Disable Semantic Scholar API")
    parser.add_argument("--no-pubmed", action="store_true", help="Disable PubMed API")
    parser.add_argument("--no-crossref", action="store_true", help="Disable Crossref API")

    args = parser.parse_args()

    # 初始化获取器
    fetcher = AbstractFetcher(
        timeout=args.timeout,
        enable_semantic_scholar=not args.no_semantic_scholar,
        enable_pubmed=not args.no_pubmed,
        enable_crossref=not args.no_crossref,
    )

    # 单 DOI 模式
    if args.doi:
        abstract = fetcher.fetch_by_doi(args.doi, args.topic)
        if abstract:
            print(f"✓ Abstract found for DOI: {args.doi}")
            print(f"\n{abstract}")
            print(f"\n{fetcher.get_statistics()}")
            return 0
        else:
            print(f"✗ No abstract found for DOI: {args.doi}")
            return 1

    # 标题模式
    if args.title:
        abstract = fetcher.fetch_by_title(args.title, args.topic)
        if abstract:
            print(f"✓ Abstract found for title: {args.title}")
            print(f"\n{abstract}")
            print(f"\n{fetcher.get_statistics()}")
            return 0
        else:
            print(f"✗ No abstract found for title: {args.title}")
            return 1

    # 批量处理模式
    if args.input:
        if not args.input.exists():
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            return 1

        # 读取输入文件
        papers = []
        with open(args.input, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        papers.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        print(f"Loaded {len(papers)} papers from {args.input}")

        # 批量处理
        enriched = fetcher.fetch_batch(papers, topic=args.topic, max_workers=args.max_workers)

        # 写入输出文件
        output_path = args.output or args.input.parent / f"{args.input.stem}_enriched.jsonl"
        with open(output_path, "w", encoding="utf-8") as f:
            for paper in enriched:
                f.write(json.dumps(paper, ensure_ascii=False) + "\n")

        print(f"\n✓ Enriched papers written to: {output_path}")
        print(f"\n{fetcher.get_statistics()}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
