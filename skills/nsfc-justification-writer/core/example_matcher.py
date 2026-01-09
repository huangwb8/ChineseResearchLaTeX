#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class ExampleMatch:
    path: Path
    category: str
    score: float


def _iter_example_files(skill_root: Path) -> Iterable[Tuple[str, Path]]:
    root = (Path(skill_root).resolve() / "examples").resolve()
    if not root.is_dir():
        return []
    out: List[Tuple[str, Path]] = []
    for p in root.glob("**/*.tex"):
        if p.is_file():
            category = p.parent.name
            out.append((category, p.resolve()))
    return out


def _tokens(text: str) -> List[str]:
    t = (text or "").lower()
    toks = re.findall(r"[a-z0-9_]+", t)
    # 加一点常见中文关键词（子串命中时也能参与得分）
    for k in ["临床", "医学", "医疗", "患者", "疾病", "算法", "工程", "系统", "部署", "时延", "吞吐"]:
        if k in (text or ""):
            toks.append(k)
    return toks


def _category_boost(query: str, category: str) -> float:
    q = query or ""
    if category == "medical" and any(x in q for x in ["临床", "医学", "医疗", "患者", "疾病", "诊疗", "医院"]):
        return 2.0
    if category == "engineering" and any(x in q for x in ["算法", "工程", "系统", "部署", "算力", "时延", "吞吐", "鲁棒"]):
        return 2.0
    return 0.0


def recommend_examples(*, skill_root: Path, query: str, top_k: int = 3) -> List[ExampleMatch]:
    q_tokens = _tokens(query)
    q_set = set(q_tokens)
    matches: List[ExampleMatch] = []
    for category, path in _iter_example_files(skill_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        e_tokens = _tokens(text)
        overlap = len([t for t in e_tokens if t in q_set])
        score = float(overlap) + _category_boost(query, category)
        matches.append(ExampleMatch(path=path, category=category, score=score))
    matches.sort(key=lambda m: (m.score, m.path.name), reverse=True)
    return matches[: max(int(top_k), 1)]


def format_example_recommendations(matches: List[ExampleMatch]) -> str:
    if not matches:
        return "（未找到可用示例）\n"
    lines = ["推荐示例："]
    for m in matches:
        lines.append(f"- {m.category}: {m.path}")
    return "\n".join(lines).strip() + "\n"

