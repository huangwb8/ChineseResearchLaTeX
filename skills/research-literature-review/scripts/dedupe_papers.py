#!/usr/bin/env python3
"""
dedupe_papers.py - 候选文献去重（标题规范化 + year + 模糊匹配）并输出合并映射

目标（与 SKILL.md 对齐）：
  - DOI 优先去重
  - DOI 缺失时：标题规范化 + 年份窗口 + 模糊匹配（SequenceMatcher + token Jaccard）
  - 记录“合并映射 / 选择正式版本”的证据，便于在 {主题}_工作条件.md 中追溯

输入：
  - JSONL：每行一个 paper dict
  - JSON：list[paper]

输出：
  - 去重后的 JSONL
  - 合并映射 JSON（包含每个合并组、选择理由与统计）
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from path_scope import get_effective_scope_root, resolve_and_check


def _normalize_doi(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE).strip()
    return raw.lower()


_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "for",
    "in",
    "on",
    "to",
    "with",
    "from",
    "by",
    "via",
}


def _normalize_title(title: str) -> str:
    title = (title or "").strip().lower()
    title = re.sub(r"[\u3000\s]+", " ", title)
    title = re.sub(r"[\"'“”‘’]", "", title)
    title = re.sub(r"[^\w\s-]", " ", title, flags=re.UNICODE)
    title = re.sub(r"[-_]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    tokens = [t for t in title.split(" ") if t and t not in _STOPWORDS]
    return " ".join(tokens)


def _tokenize(title_norm: str) -> set[str]:
    return {t for t in title_norm.split(" ") if t}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _as_int_year(y: Any) -> Optional[int]:
    if y is None:
        return None
    if isinstance(y, int):
        return y if 1000 <= y <= 3000 else None
    if isinstance(y, str):
        m = re.search(r"\b(19|20)\d{2}\b", y)
        return int(m.group(0)) if m else None
    return None


def _looks_preprint(paper: Dict[str, Any]) -> bool:
    venue = (paper.get("venue") or "").lower()
    url = (paper.get("url") or "").lower()
    return any(
        kw in venue or kw in url
        for kw in [
            "arxiv",
            "biorxiv",
            "medrxiv",
            "preprint",
        ]
    )


def _paper_quality_score(paper: Dict[str, Any]) -> int:
    """
    选择“更正式/更可复用版本”的启发式评分。
    只用于去重选择 canonical，不用于学术质量判断。
    """
    score = 0
    doi = _normalize_doi(paper.get("doi") or "")
    if doi:
        score += 10
    if not _looks_preprint(paper):
        score += 4
    if paper.get("venue"):
        score += 2
    if _as_int_year(paper.get("year")):
        score += 1
    abstract = paper.get("abstract") or ""
    if isinstance(abstract, str):
        score += min(2, len(abstract) // 400)  # 0..2
    url = (paper.get("url") or "").lower()
    if "doi.org/" in url:
        score += 1
    return score


def _merge_fields(canonical: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并字段：尽量补全 canonical 缺失的信息；不覆盖已有的“更正式”字段。
    """
    merged = dict(canonical)
    for k in ["doi", "url", "venue", "year", "abstract", "title", "authors", "source"]:
        if k not in merged or merged.get(k) in (None, "", [], {}):
            if other.get(k) not in (None, "", [], {}):
                merged[k] = other.get(k)
    return merged


@dataclass
class MergeEdge:
    canonical_index: int
    merged_index: int
    reason: str
    similarity: float
    jaccard: float
    year_a: Optional[int]
    year_b: Optional[int]
    doi_a: str
    doi_b: str


def load_papers(path: Path) -> list[Dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        out: list[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
        return out
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    raise ValueError(f"Unsupported JSON structure: expected list[dict], got {type(data)}")


def write_jsonl(path: Path, papers: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for p in papers:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


def dedupe(
    papers: list[Dict[str, Any]],
    *,
    title_similarity_threshold: float,
    token_jaccard_threshold: float,
    year_window: int,
) -> Tuple[list[Dict[str, Any]], list[MergeEdge]]:
    """
    返回：
      - 去重后的 papers（canonical 列表）
      - 合并边（原始 index -> canonical index）
    """
    canonical: list[Dict[str, Any]] = []
    edges: list[MergeEdge] = []

    # DOI 直达索引
    doi_to_canonical: dict[str, int] = {}

    # 对无 DOI 的候选，按 (year_bucket, prefix) 做粗分桶，降低比较次数
    bucket: dict[Tuple[Optional[int], str], list[int]] = {}

    def bucket_key(p: Dict[str, Any]) -> Tuple[Optional[int], str]:
        y = _as_int_year(p.get("year"))
        norm = _normalize_title(p.get("title") or "")
        prefix = (norm[:24] if norm else "") or "untitled"
        return y, prefix

    def candidate_indices(p: Dict[str, Any]) -> list[int]:
        y = _as_int_year(p.get("year"))
        norm = _normalize_title(p.get("title") or "")
        prefix = (norm[:24] if norm else "") or "untitled"

        keys: list[Tuple[Optional[int], str]] = []
        if y is None:
            keys.append((None, prefix))
        else:
            for yy in range(y - year_window, y + year_window + 1):
                keys.append((yy, prefix))
        out: list[int] = []
        for k in keys:
            out.extend(bucket.get(k, []))
        # fallback：不带 prefix 的桶（避免 prefix 微小差异导致完全错过）
        if y is not None:
            out.extend(bucket.get((y, "untitled"), []))
        else:
            out.extend(bucket.get((None, "untitled"), []))
        # 去重
        return list(dict.fromkeys(out))

    for idx, p in enumerate(papers):
        if not isinstance(p, dict):
            continue

        doi = _normalize_doi(p.get("doi") or "")
        title_norm = _normalize_title(p.get("title") or "")

        # 1) DOI 优先：同 DOI 直接合并
        if doi:
            if doi in doi_to_canonical:
                ci = doi_to_canonical[doi]
                canonical[ci] = _merge_fields(canonical[ci], p)
                edges.append(
                    MergeEdge(
                        canonical_index=ci,
                        merged_index=idx,
                        reason="same_doi",
                        similarity=1.0,
                        jaccard=1.0,
                        year_a=_as_int_year(canonical[ci].get("year")),
                        year_b=_as_int_year(p.get("year")),
                        doi_a=_normalize_doi(canonical[ci].get("doi") or ""),
                        doi_b=doi,
                    )
                )
                continue

        # 2) 无 DOI / 可能版本差异：尝试模糊匹配
        best_ci: Optional[int] = None
        best_sim = 0.0
        best_j = 0.0
        best_reason = ""

        if title_norm:
            tokens = _tokenize(title_norm)
            y = _as_int_year(p.get("year"))

            for ci in candidate_indices(p):
                c = canonical[ci]
                c_title_norm = _normalize_title(c.get("title") or "")
                if not c_title_norm:
                    continue

                c_y = _as_int_year(c.get("year"))
                if y is not None and c_y is not None and abs(y - c_y) > year_window:
                    continue

                sim = SequenceMatcher(a=title_norm, b=c_title_norm).ratio()
                j = _jaccard(tokens, _tokenize(c_title_norm))

                c_doi = _normalize_doi(c.get("doi") or "")
                cross_doi_merge = bool(doi and c_doi and doi != c_doi)

                # 默认：允许“至少一方无 DOI”的合并；两方都有 DOI 时需要更高置信度且偏向“预印本->正式版”
                if cross_doi_merge:
                    if not (_looks_preprint(p) or _looks_preprint(c)):
                        continue
                    if sim < 0.97:
                        continue
                    reason = "cross_doi_preprint_to_published"
                else:
                    reason = "fuzzy_title_year"

                if sim >= title_similarity_threshold and j >= token_jaccard_threshold and sim > best_sim:
                    best_ci = ci
                    best_sim = sim
                    best_j = j
                    best_reason = reason

        if best_ci is not None:
            # 2.1) 选择 canonical：用“更正式版本”启发式比较
            ci = best_ci
            chosen = canonical[ci]
            chosen_score = _paper_quality_score(chosen)
            incoming_score = _paper_quality_score(p)

            if incoming_score > chosen_score:
                # incoming 更像“正式版本”，交换
                canonical[ci] = _merge_fields(p, chosen)
                chosen = canonical[ci]
            else:
                canonical[ci] = _merge_fields(chosen, p)

            doi_new = _normalize_doi(chosen.get("doi") or "")
            if doi_new:
                doi_to_canonical[doi_new] = ci

            edges.append(
                MergeEdge(
                    canonical_index=ci,
                    merged_index=idx,
                    reason=best_reason,
                    similarity=best_sim,
                    jaccard=best_j,
                    year_a=_as_int_year(chosen.get("year")),
                    year_b=_as_int_year(p.get("year")),
                    doi_a=_normalize_doi(chosen.get("doi") or ""),
                    doi_b=_normalize_doi(p.get("doi") or ""),
                )
            )
            continue

        # 3) 新 canonical
        ci = len(canonical)
        canonical.append(p)
        if doi:
            doi_to_canonical[doi] = ci
        bucket[bucket_key(p)] = bucket.get(bucket_key(p), []) + [ci]

    return canonical, edges


def main() -> int:
    parser = argparse.ArgumentParser(description="Dedupe candidate papers and write merge map (JSONL + JSON).")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Input papers (.jsonl or .json)")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Output deduped papers (.jsonl)")
    parser.add_argument("--map", required=True, type=Path, help="Output merge map (.json)")
    parser.add_argument(
        "--scope-root",
        type=Path,
        default=None,
        help="工作目录隔离根目录（可选；默认从环境变量 SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT 读取）",
    )
    parser.add_argument("--title-sim", type=float, default=0.92, help="Title similarity threshold (default: 0.92)")
    parser.add_argument("--token-jaccard", type=float, default=0.80, help="Token Jaccard threshold (default: 0.80)")
    parser.add_argument("--year-window", type=int, default=1, help="Year window for matching (default: 1)")
    args = parser.parse_args()

    scope_root = get_effective_scope_root(args.scope_root)
    if scope_root is not None:
        args.input = resolve_and_check(args.input, scope_root, must_exist=True)
        args.output = resolve_and_check(args.output, scope_root, must_exist=False)
        args.map = resolve_and_check(args.map, scope_root, must_exist=False)

    papers = load_papers(args.input)
    deduped, edges = dedupe(
        papers,
        title_similarity_threshold=args.title_sim,
        token_jaccard_threshold=args.token_jaccard,
        year_window=args.year_window,
    )

    write_jsonl(args.output, deduped)

    cross_doi = sum(1 for e in edges if e.reason == "cross_doi_preprint_to_published")

    def summary(p: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": p.get("title") or "",
            "doi": _normalize_doi(p.get("doi") or ""),
            "year": _as_int_year(p.get("year")),
            "venue": p.get("venue") or "",
            "url": p.get("url") or "",
            "preprint": _looks_preprint(p),
            "heuristic_score": _paper_quality_score(p),
        }

    groups: dict[int, Dict[str, Any]] = {}
    for e in edges:
        groups.setdefault(
            e.canonical_index,
            {
                "canonical_index": e.canonical_index,
                "canonical": summary(deduped[e.canonical_index]) if 0 <= e.canonical_index < len(deduped) else {},
                "merged": [],
            },
        )
        merged_paper = papers[e.merged_index] if 0 <= e.merged_index < len(papers) else {}
        groups[e.canonical_index]["merged"].append(
            {
                "merged_index": e.merged_index,
                "merged": summary(merged_paper) if isinstance(merged_paper, dict) else {},
                "reason": e.reason,
                "similarity": e.similarity,
                "jaccard": e.jaccard,
            }
        )
    map_payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input": str(args.input),
        "output": str(args.output),
        "input_count": len(papers),
        "output_count": len(deduped),
        "merged_count": len(edges),
        "cross_doi_merges": cross_doi,
        "params": {
            "title_similarity_threshold": args.title_sim,
            "token_jaccard_threshold": args.token_jaccard,
            "year_window": args.year_window,
        },
        "groups": [groups[i] for i in sorted(groups.keys())],
        "edges": [asdict(e) for e in edges],
    }
    args.map.parent.mkdir(parents=True, exist_ok=True)
    args.map.write_text(json.dumps(map_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "input": str(args.input),
                "output": str(args.output),
                "map": str(args.map),
                "input_count": len(papers),
                "output_count": len(deduped),
                "merged_count": len(edges),
                "cross_doi_merges": cross_doi,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
