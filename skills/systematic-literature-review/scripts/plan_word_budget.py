#!/usr/bin/env python3
"""
plan_word_budget.py - 为 systematic-literature-review 生成 per-paper/per-section 综/述字数预算

特点：
- 70% 引用段落 + 30% 无引用段落（摘要/结论/展望等），支持无引用节点写入空文献 ID 行。
- 按大纲节点权重分配，再按文献 score softmax+扰动分配；综/述按基准比例拆分并可随 score 轻微倾斜。
- 独立运行 3 次（不同种子），输出 run1/2/3 CSV 并对齐取均值生成 final CSV；检查总字数误差 ≤ tolerance，否则按比例缩放。

输入：
  - --selected: 选中文献 jsonl（需含 id/doi、score、subtopic）
  - --outline: 大纲 yaml（可选）。缺省时按 subtopic 汇总并附带默认无引用段落（摘要/结论/展望/讨论）。
  - --target-words: 目标总字数（默认取 config 中该档位 min/max 中点）

输出：
  - artifacts/word_budget_run{1,2,3}.csv
  - artifacts/word_budget_final.csv（三次均值）
  - artifacts/non_cited_budget.csv（方便检查无引用段落占用）

CSV 列：文献ID、大纲、综字数、述字数。无引用行的文献ID为空串。
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class Paper:
    pid: str
    subtopic: str
    score: float


@dataclass
class Section:
    sid: str
    title: str
    cited: bool
    weight: Optional[float]
    subtopic: Optional[str]


# ---------------------------------------------------------------------------
# 读写与校验
# ---------------------------------------------------------------------------


def load_papers(path: Path) -> List[Paper]:
    papers: List[Paper] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            pid = (obj.get("id") or obj.get("doi") or "").strip()
            if not pid:
                continue
            try:
                score = float(obj.get("score", 0.0))
            except Exception:
                score = 0.0
            subtopic = str(obj.get("subtopic") or "").strip() or "general"
            papers.append(Paper(pid=pid, subtopic=subtopic, score=score))
    return papers


def load_outline(path: Optional[Path], subtopics: List[str]) -> List[Section]:
    if path is None:
        # 默认大纲：引言/讨论/展望/结论（无引用），其余按子主题生成引用段
        sections: List[Section] = [
            Section("intro", "引言", False, 1.0, None),
        ]
        for idx, st in enumerate(subtopics, 1):
            sections.append(Section(f"subtopic-{idx}", st, True, None, st))
        sections.extend(
            [
                Section("discussion", "讨论", False, 1.0, None),
                Section("outlook", "展望", False, 1.0, None),
                Section("conclusion", "结论", False, 1.0, None),
            ]
        )
        return sections

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sections_cfg = data.get("sections") or []
    sections: List[Section] = []
    for i, item in enumerate(sections_cfg, 1):
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or f"s{i}")
        title = str(item.get("title") or sid)
        cited = bool(item.get("cited", True))
        weight = item.get("weight")
        subtopic = item.get("subtopic")
        if subtopic is not None:
            subtopic = str(subtopic)
        sections.append(Section(sid=sid, title=title, cited=cited, weight=weight, subtopic=subtopic))
    return sections


def ensure_dirs(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: List[Tuple[str, str, float, float]]) -> None:
    ensure_dirs(path)
    lines = ["文献ID,大纲,综字数,述字数"]
    for pid, sec, zong, shu in rows:
        lines.append(f"{pid},{sec},{int(round(zong))},{int(round(shu))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 分配算法
# ---------------------------------------------------------------------------


def softmax(xs: List[float]) -> List[float]:
    if not xs:
        return []
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    total = sum(exps)
    return [v / total for v in exps] if total else [1.0 / len(xs)] * len(xs)


def allocate_to_sections(
    sections: List[Section],
    papers: List[Paper],
    cited_pool: float,
    non_cited_pool: float,
) -> Dict[str, float]:
    # 权重：引用段按 weight 或 avg(score)*count；无引用段按 weight（缺省=1）
    cited_weights: Dict[str, float] = {}
    non_cited_weights: Dict[str, float] = {}
    by_subtopic: Dict[str, List[Paper]] = defaultdict(list)
    for p in papers:
        by_subtopic[p.subtopic].append(p)

    for sec in sections:
        if sec.cited:
            if sec.subtopic:
                ps = by_subtopic.get(sec.subtopic, [])
            else:
                ps = papers
            if ps:
                avg_score = sum(p.score for p in ps) / len(ps)
                weight = sec.weight if sec.weight is not None else max(avg_score, 0.1) * len(ps)
            else:
                weight = sec.weight if sec.weight is not None else 0.1
            cited_weights[sec.sid] = weight
        else:
            weight = sec.weight if sec.weight is not None else 1.0
            non_cited_weights[sec.sid] = weight

    def _norm(weights: Dict[str, float]) -> Dict[str, float]:
        total = sum(max(w, 0.0) for w in weights.values())
        if total <= 0:
            n = len(weights) or 1
            return {k: 1.0 / n for k in weights}
        return {k: max(w, 0.0) / total for k, w in weights.items()}

    cited_norm = _norm(cited_weights)
    non_cited_norm = _norm(non_cited_weights)

    section_alloc: Dict[str, float] = {}
    for sid, frac in cited_norm.items():
        section_alloc[sid] = cited_pool * frac
    for sid, frac in non_cited_norm.items():
        section_alloc[sid] = non_cited_pool * frac
    return section_alloc


def allocate_within_section(
    section: Section,
    papers: List[Paper],
    alloc: float,
    summary_ratio: float,
    commentary_ratio: float,
    noise_strength: float,
) -> List[Tuple[str, str, float, float]]:
    if not section.cited:
        # 无引用段落：空 ID 行
        return [("", section.title, alloc * summary_ratio, alloc * commentary_ratio)]

    # 过滤该 section 的文献
    if section.subtopic:
        ps = [p for p in papers if p.subtopic == section.subtopic]
    else:
        ps = papers
    if not ps:
        # 无文献但标记为 cited，仍给空行避免丢配额
        return [("", section.title, alloc * summary_ratio, alloc * commentary_ratio)]

    scores = []
    for p in ps:
        noise = random.uniform(-noise_strength, noise_strength)
        scores.append(p.score + noise)
    probs = softmax(scores)
    rows: List[Tuple[str, str, float, float]] = []
    for p, prob in zip(ps, probs):
        total = alloc * prob
        # 高分轻微偏向“综”
        tilt = (p.score - 5.0) / 10.0  # 大致 [-0.5, 0.5]
        zong_ratio = max(0.1, min(0.9, summary_ratio + 0.1 * tilt))
        zong = total * zong_ratio
        shu = total - zong
        rows.append((p.pid, section.title, zong, shu))
    return rows


def run_once(
    sections: List[Section],
    papers: List[Paper],
    target_words: float,
    cfg: Dict[str, Any],
    seed: int,
) -> List[Tuple[str, str, float, float]]:
    random.seed(seed)
    ratio = cfg.get("ratio", {})
    cited_ratio = float(ratio.get("cited", 0.7))
    non_cited_ratio = float(ratio.get("non_cited", 0.3))
    summary_ratio = float(cfg.get("summary_ratio", 0.55))
    commentary_ratio = float(cfg.get("commentary_ratio", 0.45))
    noise_strength = float(cfg.get("noise_strength", 0.1))

    cited_pool = target_words * cited_ratio
    non_cited_pool = target_words * non_cited_ratio
    section_alloc = allocate_to_sections(sections, papers, cited_pool, non_cited_pool)

    rows: List[Tuple[str, str, float, float]] = []
    for sec in sections:
        alloc = section_alloc.get(sec.sid, 0.0)
        rows.extend(allocate_within_section(sec, papers, alloc, summary_ratio, commentary_ratio, noise_strength))
    return rows


def align_and_average(runs: List[List[Tuple[str, str, float, float]]]) -> List[Tuple[str, str, float, float]]:
    acc: Dict[Tuple[str, str], Tuple[float, float, int]] = {}
    for rows in runs:
        for pid, sec, zong, shu in rows:
            key = (pid, sec)
            a_z, a_s, n = acc.get(key, (0.0, 0.0, 0))
            acc[key] = (a_z + zong, a_s + shu, n + 1)
    averaged: List[Tuple[str, str, float, float]] = []
    for (pid, sec), (a_z, a_s, n) in acc.items():
        averaged.append((pid, sec, a_z / n, a_s / n))
    return averaged


def total_words(rows: List[Tuple[str, str, float, float]]) -> float:
    return sum(z + s for _, _, z, s in rows)


def scale_to_target(rows: List[Tuple[str, str, float, float]], target: float) -> List[Tuple[str, str, float, float]]:
    current = total_words(rows)
    if current <= 0:
        return rows
    factor = target / current
    return [(pid, sec, z * factor, s * factor) for pid, sec, z, s in rows]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate word budget CSVs for SLR")
    p.add_argument("--selected", required=True, type=Path, help="selected_papers.jsonl")
    p.add_argument("--outline", type=Path, help="outline_plan.yaml (optional)")
    p.add_argument("--config", type=Path, required=True, help="config.yaml")
    p.add_argument("--output-dir", type=Path, required=True, help="artifacts dir for CSVs")
    p.add_argument("--target-words", type=float, help="override target words")
    p.add_argument("--review-level", default="premium", choices=["premium", "standard", "basic"], help="review level for inferring target words")
    return p.parse_args()


def load_cfg(config_path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data.get("word_budget", {})


def infer_target_words(config_path: Path, review_level: str = "premium") -> float:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    scoring = data.get("scoring", {}) if isinstance(data, dict) else {}
    word_range = (scoring.get("default_word_range") or {}).get(review_level, {})
    try:
        lo = float(word_range.get("min", 0))
        hi = float(word_range.get("max", 0))
    except Exception:
        return 0.0
    return (lo + hi) / 2 if (lo + hi) > 0 else 0.0


def main() -> int:
    args = parse_args()
    cfg = load_cfg(args.config)
    papers = load_papers(args.selected)
    if not papers:
        print("✗ 无法加载选中文献")
        return 1
    subtopics = sorted({p.subtopic for p in papers})
    sections = load_outline(args.outline, subtopics)

    target_words = args.target_words or infer_target_words(args.config, args.review_level)
    if target_words <= 0:
        target_words = 15000.0

    seeds = cfg.get("seeds", [17, 23, 43])
    runs: List[List[Tuple[str, str, float, float]]] = []
    out_dir = args.output_dir

    for i, seed in enumerate(seeds, 1):
        rows = run_once(sections, papers, target_words, cfg, seed)
        run_path = out_dir / cfg.get("outputs", {}).get("run_pattern", "word_budget_run{n}.csv").format(n=i)
        write_csv(run_path, rows)
        runs.append(rows)
        print(f"✓ 生成 {run_path}")

    final_rows = align_and_average(runs)
    total = total_words(final_rows)
    tol = float(cfg.get("tolerance", 0.05))
    if target_words > 0 and abs(total - target_words) / target_words > tol:
        final_rows = scale_to_target(final_rows, target_words)
        total = total_words(final_rows)

    final_path = out_dir / cfg.get("outputs", {}).get("final", "word_budget_final.csv")
    write_csv(final_path, final_rows)
    print(f"✓ 生成 {final_path} (总字数约 {int(round(total))})")

    # 额外输出无引用汇总
    non_cited_rows = [(pid, sec, z, s) for pid, sec, z, s in final_rows if pid == ""]
    if non_cited_rows:
        nc_path = out_dir / cfg.get("outputs", {}).get("non_cited", "non_cited_budget.csv")
        write_csv(nc_path, non_cited_rows)
        print(f"✓ 生成 {nc_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

