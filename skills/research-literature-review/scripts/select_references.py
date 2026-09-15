#!/usr/bin/env python3
"""
select_references.py - 按相关性、证据角色与软预算选文并生成 BibTeX

输入：评分后的 papers jsonl（包含 score/subtopic/doi/title/year/venue 等）
输出：
  - selected jsonl
  - references.bib
  - selection rationale yaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml

from path_scope import get_effective_scope_root, resolve_and_check

try:
    from config_loader import load_config
except ImportError:
    load_config = None  # type: ignore[assignment]

# 与 config.yaml: search.abstract_enrichment.min_abstract_chars 保持一致；作为兜底值
DEFAULT_MIN_ABSTRACT_CHARS = 80


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                items.append(obj)
    return items


def _normalize_key(paper: Dict[str, Any]) -> str:
    doi = str(paper.get("doi") or "").strip().lower()
    if doi:
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    title = str(paper.get("title") or "").strip().lower()
    year = str(paper.get("year") or "").strip()
    return doi or f"{title}::{year}"


def _bib_key_from_title(title: str, year: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", title)
    base = "".join(tokens[:3]).lower() or "ref"
    yr = re.sub(r"[^0-9]", "", year) if year else ""
    return (base + yr)[:40] or "ref"


def _make_unique_key(base: str, used_lower: set[str]) -> str:
    candidate = base or "ref"
    if candidate.lower() not in used_lower:
        used_lower.add(candidate.lower())
        return candidate
    suffix = 1
    while f"{candidate}{suffix}".lower() in used_lower:
        suffix += 1
    final = f"{candidate}{suffix}"
    used_lower.add(final.lower())
    return final


_LATEX_SPECIALS: dict[str, str] = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    # ^ / ~ 在正文中可能触发 LaTeX 语法错误或语义偏差（尤其是 URL）；用 \string 保守输出字面字符
    "^": r"\string^",
    "~": r"\string~",
}


def _escape_bib_value(value: str) -> tuple[str, dict[str, int]]:
    """Escape common LaTeX specials in BibTeX values (best-effort).

    We keep this conservative to avoid breaking intentional LaTeX macros.
    """
    escaped = value
    counts: dict[str, int] = {}
    for ch, repl in _LATEX_SPECIALS.items():
        escaped, n = re.subn(rf"(?<!\\\\){re.escape(ch)}", lambda m, r=repl: r, escaped)
        if n:
            counts[ch] = n
    return escaped, counts


def _format_escape_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{k}×{v}" for k, v in sorted(counts.items()))


def _normalize_authors(authors: Any) -> str:
    if isinstance(authors, list):
        names: list[str] = []
        for a in authors:
            if isinstance(a, dict) and a.get("name"):
                names.append(str(a["name"]))
            elif isinstance(a, str):
                names.append(a)
        if names:
            return " and ".join(names)
    if isinstance(authors, str) and authors.strip():
        return authors.strip()
    return "Unknown"


def _render_bib_entry(key: str, paper: Dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    title_raw = paper.get("title") or "Untitled"
    venue_raw = paper.get("venue") or paper.get("journal") or ""
    year_raw = str(paper.get("year") or "").strip()
    url_raw = paper.get("url") or ""
    doi_raw = paper.get("doi") or ""
    authors_raw = paper.get("authors") or paper.get("author") or ""
    abstract_raw = paper.get("abstract") or ""

    title, title_counts = _escape_bib_value(str(title_raw))
    venue, venue_counts = _escape_bib_value(str(venue_raw))
    author_str, author_counts = _escape_bib_value(_normalize_authors(authors_raw))
    doi = str(doi_raw).replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    year = year_raw if year_raw else "n.d."

    missing_fields = []
    if author_str.lower() == "unknown":
        missing_fields.append("author")
    if venue.strip() == "":
        missing_fields.append("journal")
    if doi == "":
        missing_fields.append("doi")
    if missing_fields:
        warnings.append(f"{key} 缺失字段: {', '.join(missing_fields)}（已填默认值，建议补全）")

    for counts, label in [(title_counts, "title"), (venue_counts, "journal"), (author_counts, "author")]:
        if counts:
            warnings.append(f"{key} 自动转义 {label} 中的 LaTeX 特殊字符（{_format_escape_counts(counts)}）")

    fields = [
        f"title = {{{title}}}",
        f"author = {{{author_str or 'Unknown'}}}",
        f"year = {{{year}}}",
        f"journal = {{{venue or 'Unknown'}}}",
    ]
    if doi:
        fields.append(f"doi = {{{doi}}}")
    if url_raw:
        url, url_counts = _escape_bib_value(str(url_raw))
        fields.append(f"url = {{{url}}}")
        if url_counts:
            warnings.append(f"{key} 自动转义 url 中的 LaTeX 特殊字符（{_format_escape_counts(url_counts)}）")
    if abstract_raw:
        abstract, abstract_counts = _escape_bib_value(str(abstract_raw))
        fields.append(f"abstract = {{{abstract}}}")
        if abstract_counts:
            warnings.append(f"{key} 自动转义 abstract 中的 LaTeX 特殊字符（{_format_escape_counts(abstract_counts)}）")
    return "@article{{{key},\n  {fields}\n}}\n".format(key=key, fields=",\n  ".join(fields)), warnings


def _select_papers(
    papers: List[Dict[str, Any]],
    min_refs: int,
    max_refs: int,
    target_refs: int,
    high_score_min: float,
    high_score_max: float,
    *,
    min_abstract_chars: int,
    min_score: float = 5.0,
    purpose: str = "standard-review",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    unique: Dict[str, Dict[str, Any]] = {}
    for p in papers:
        k = _normalize_key(p)
        if not k:
            continue
        unique[k] = p
    items = list(unique.values())

    def _has_abstract(p: Dict[str, Any]) -> bool:
        a = p.get("abstract") or ""
        return isinstance(a, str) and len(a.strip()) >= int(min_abstract_chars)

    total = len(items)
    if total == 0:
        return [], {"total_candidates": 0}

    role_priority = {
        "direct-neighbor": 0,
        "contradictory": 1,
        "boundary": 2,
        "methodological": 3,
        "supporting": 4,
    }

    def _role(p: Dict[str, Any]) -> str:
        value = str(p.get("evidence_role") or p.get("role") or "supporting").strip().lower()
        return value if value in role_priority else "supporting"

    for paper in items:
        paper["evidence_role"] = _role(paper)
        paper["evidence_depth"] = "abstract" if _has_abstract(paper) else "title"

    qualified = [paper for paper in items if float(paper.get("score") or 0) >= float(min_score)]
    if purpose == "standard-review":
        qualified = [paper for paper in qualified if _has_abstract(paper)]
    elif purpose != "novelty-check":
        raise ValueError(f"unsupported purpose: {purpose}")
    qualified.sort(
        key=lambda paper: (
            role_priority[_role(paper)],
            -float(paper.get("score") or 0),
            str(paper.get("subtopic") or ""),
        )
    )

    # target_refs 是预算目标，max_refs 是硬上限；min_refs 只保留为旧配置的软目标提示。
    desired = int(target_refs)
    if desired <= 0:
        desired = int(round((min_refs + max_refs) / 2.0))
    desired = max(1, min(int(max_refs), desired))
    selected = qualified[:desired]

    # novelty-check 保留只有标题的强近邻供升级核验，但明确禁止把它当成可引用结论证据。
    for p in selected:
        if not _has_abstract(p):
            p["do_not_cite"] = True
            p["quality_warnings"] = list(p.get("quality_warnings") or [])
            if "missing_abstract" not in p["quality_warnings"]:
                p["quality_warnings"].append("missing_abstract")

    # 统计选中文献的实际分数分布
    selected_scores = [float(p.get("score") or 0) for p in selected]
    score_distribution = {
        "high_score_count": sum(1 for s in selected_scores if s >= 7),
        "mid_score_count": sum(1 for s in selected_scores if 4 <= s < 7),
        "low_score_count": sum(1 for s in selected_scores if s < 4),
        "max_score": max(selected_scores) if selected_scores else 0,
        "min_score": min(selected_scores) if selected_scores else 0,
        "avg_score": round(sum(selected_scores) / len(selected_scores), 2) if selected_scores else 0,
    }

    role_counts = {role: sum(1 for p in selected if _role(p) == role) for role in role_priority}
    missing_target = max(0, desired - len(selected))
    gaps: list[str] = []
    if missing_target:
        gaps.append(f"qualified_references_below_soft_target:{missing_target}")
    if purpose == "novelty-check" and not any(_role(p) == "direct-neighbor" for p in selected):
        gaps.append("direct_neighbor_missing")
    if any(not _has_abstract(p) for p in selected):
        gaps.append("title_only_records_require_enrichment")
    rationale = {
        "total_candidates": total,
        "qualified_candidates": len(qualified),
        "selected": len(selected),
        "purpose": purpose,
        "minimum_score": float(min_score),
        "minimum_refs_legacy_soft_target": min_refs,
        "migration_warning": "min_refs is no longer a hard floor; relevance and evidence eligibility decide the final count",
        "max_refs": max_refs,
        "target_refs_soft": desired,
        "target_shortfall": missing_target,
        "stop_reason": "soft_target_reached" if not missing_target else "eligible_evidence_exhausted",
        "evidence_role_counts": role_counts,
        "evidence_gaps": gaps,
        "min_abstract_chars": int(min_abstract_chars),
        "score_distribution": score_distribution,
        "missing_abstract_candidates": sum(1 for p in items if not _has_abstract(p)),
        "missing_abstract_selected": sum(1 for p in selected if not _has_abstract(p)),
    }
    return selected, rationale


def main() -> int:
    parser = argparse.ArgumentParser(description="Select references by score and generate bib.")
    parser.add_argument("--input", required=True, type=Path, help="Scored papers jsonl")
    parser.add_argument("--output", required=True, type=Path, help="Selected papers jsonl output")
    parser.add_argument("--bib", required=True, type=Path, help="BibTeX output path")
    parser.add_argument("--selection", required=True, type=Path, help="Selection rationale yaml")
    parser.add_argument(
        "--scope-root",
        type=Path,
        default=None,
        help="工作目录隔离根目录（可选；默认从环境变量 SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT 读取）",
    )
    parser.add_argument("--min-refs", type=int, required=True, help="Minimum references to keep")
    parser.add_argument("--max-refs", type=int, required=True, help="Maximum references to keep")
    parser.add_argument(
        "--target-refs",
        type=int,
        default=None,
        help="Target references to keep (default: from config.yaml selection.target_refs or midpoint(min,max))",
    )
    parser.add_argument("--high-score-min", type=float, default=0.6, help="Lower bound of high-score fraction")
    parser.add_argument("--high-score-max", type=float, default=0.8, help="Upper bound of high-score fraction")
    parser.add_argument("--min-score", type=float, default=None, help="Minimum relevance score (default: config selection.minimum_score)")
    parser.add_argument(
        "--purpose",
        choices=("standard-review", "novelty-check"),
        default=None,
        help="standard review or focused novelty check",
    )
    parser.add_argument(
        "--min-abstract-chars",
        type=int,
        default=None,
        help="Treat abstract shorter than N chars as missing (default: from config.yaml search.abstract_enrichment.min_abstract_chars, fallback: 80)",
    )
    args = parser.parse_args()

    scope_root = get_effective_scope_root(args.scope_root)
    if scope_root is not None:
        args.input = resolve_and_check(args.input, scope_root, must_exist=True)
        args.output = resolve_and_check(args.output, scope_root, must_exist=False)
        args.bib = resolve_and_check(args.bib, scope_root, must_exist=False)
        args.selection = resolve_and_check(args.selection, scope_root, must_exist=False)

    papers = _read_jsonl(args.input)

    # 默认跟随 config.yaml 的“有效摘要最小长度”，保持写作/对齐检查的一致性
    min_abs_chars = DEFAULT_MIN_ABSTRACT_CHARS
    # 默认目标参考数：优先从 config.yaml 读取；否则采用 midpoint(min,max)
    target_refs = 0
    if args.min_abstract_chars is not None:
        min_abs_chars = int(args.min_abstract_chars)
    elif load_config is not None:
        try:
            cfg = load_config()
            search_cfg = cfg.get("search", {}) if isinstance(cfg, dict) else {}
            ae = (search_cfg.get("abstract_enrichment") or {}) if isinstance(search_cfg.get("abstract_enrichment"), dict) else {}
            min_abs_chars = int(ae.get("min_abstract_chars", min_abs_chars))
        except Exception:
            min_abs_chars = DEFAULT_MIN_ABSTRACT_CHARS

    cfg: dict[str, Any] = {}
    if load_config is not None:
        try:
            loaded = load_config()
            cfg = loaded if isinstance(loaded, dict) else {}
        except Exception:
            cfg = {}

    if args.target_refs is not None:
        target_refs = int(args.target_refs)
    elif load_config is not None:
        try:
            sel_cfg = cfg.get("selection", {}) if isinstance(cfg, dict) else {}
            tr = sel_cfg.get("target_refs", {}) if isinstance(sel_cfg.get("target_refs"), dict) else {}
            v = tr.get("value", None)
            if v is not None:
                target_refs = int(v)
            else:
                strategy = str(tr.get("strategy", "midpoint")).strip().lower()
                if strategy == "midpoint":
                    target_refs = int(round((args.min_refs + args.max_refs) / 2.0))
                else:
                    # 未识别策略时回退 midpoint（保持简单与可预期）
                    target_refs = int(round((args.min_refs + args.max_refs) / 2.0))
        except Exception:
            target_refs = int(round((args.min_refs + args.max_refs) / 2.0))
    else:
        target_refs = int(round((args.min_refs + args.max_refs) / 2.0))

    selected, rationale = _select_papers(
        papers,
        min_refs=args.min_refs,
        max_refs=args.max_refs,
        target_refs=target_refs,
        high_score_min=args.high_score_min,
        high_score_max=args.high_score_max,
        min_abstract_chars=min_abs_chars,
        min_score=float(args.min_score if args.min_score is not None else (cfg.get("selection", {}) or {}).get("minimum_score", 5.0)),
        purpose=str(args.purpose or (cfg.get("selection", {}) or {}).get("default_purpose", "standard-review")),
    )

    if not selected:
        print("✗ 无可选文献", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fo:
        for p in selected:
            fo.write(json.dumps(p, ensure_ascii=False) + "\n")

    # 生成简易 BibTeX
    args.bib.parent.mkdir(parents=True, exist_ok=True)
    bib_entries = []
    used_keys_lower: set[str] = set()
    warnings: list[str] = []
    for p in selected:
        title = str(p.get("title") or "")
        year = str(p.get("year") or "")
        key = _make_unique_key(_bib_key_from_title(title, year), used_keys_lower)
        entry, entry_warnings = _render_bib_entry(key, p)
        bib_entries.append(entry)
        warnings.extend(entry_warnings)

    # 提示：若仍包含“摘要缺失”条目，建议写作时不要引用它们（或优先替换为有摘要的同等相关文献）
    missing_abs_selected = int((rationale or {}).get("missing_abstract_selected", 0) or 0)
    if missing_abs_selected > 0:
        print(
            f"⚠️ 选中文献中仍有 {missing_abs_selected} 篇摘要缺失/过短：建议写作时不引用或尽量替换为有摘要的文献",
            file=sys.stderr,
        )
    if int((rationale or {}).get("target_shortfall", 0) or 0) > 0:
        print(
            "⚠️ 合格证据少于软目标；未使用低相关或无摘要条目补足，详见 selection rationale",
            file=sys.stderr,
        )
    args.bib.write_text("\n".join(bib_entries), encoding="utf-8")
    if warnings:
        print("⚠️ BibTeX 清洗提示:", file=sys.stderr)
        for w in warnings[:20]:
            print(f"  - {w}", file=sys.stderr)

    args.selection.parent.mkdir(parents=True, exist_ok=True)
    yaml.safe_dump(rationale, args.selection.open("w", encoding="utf-8"), allow_unicode=True, sort_keys=False)

    print(json.dumps({"selected": len(selected), "bib": str(args.bib), "selection": str(args.selection)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
