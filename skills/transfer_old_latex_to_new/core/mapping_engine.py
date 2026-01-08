#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config_loader import get_mapping_thresholds
from .latex_utils import (
    jaccard,
    normalize_filename,
    normalize_title,
    tokenize,
)
from .project_analyzer import ProjectAnalysis


@dataclass(frozen=True)
class MappingCandidate:
    old: str
    new: str
    score: float
    reason: str


@dataclass(frozen=True)
class OneToOne:
    old: str
    new: str
    score: float
    confidence: str
    reason: str


@dataclass(frozen=True)
class StructureDiff:
    one_to_one: List[OneToOne]
    new_added: List[Dict[str, str]]
    removed: List[Dict[str, str]]
    low_confidence: List[Dict[str, str]]

    def to_dict(self) -> Dict:
        return {
            "mapping": {
                "one_to_one": [asdict(x) for x in self.one_to_one],
                "new_added": self.new_added,
                "removed": self.removed,
                "low_confidence": self.low_confidence,
            }
        }


def _best_heading_title(analysis: ProjectAnalysis, rel_path: str) -> str:
    info = analysis.tex_files.get(rel_path)
    if not info:
        return ""
    for h in info.headings:
        title = (h.get("title") or "").strip()
        if title:
            return title
    return ""


def _score_pair(old_analysis: ProjectAnalysis, new_analysis: ProjectAnalysis, old_rel: str, new_rel: str) -> Tuple[float, str]:
    old_stem = normalize_filename(Path(old_rel).stem)
    new_stem = normalize_filename(Path(new_rel).stem)
    stem_j = jaccard(tokenize(old_stem), tokenize(new_stem))
    stem_sub = 1.0 if (old_stem and new_stem and (old_stem in new_stem or new_stem in old_stem)) else 0.0
    stem_score = max(stem_j, stem_sub)

    old_title = normalize_title(_best_heading_title(old_analysis, old_rel))
    new_title = normalize_title(_best_heading_title(new_analysis, new_rel))
    title_score = 0.0 if (not old_title or not new_title) else jaccard(tokenize(old_title), tokenize(new_title))

    old_sum = (old_analysis.tex_files.get(old_rel).summary if old_analysis.tex_files.get(old_rel) else "") or ""
    new_sum = (new_analysis.tex_files.get(new_rel).summary if new_analysis.tex_files.get(new_rel) else "") or ""
    content_score = 0.0 if (not old_sum or not new_sum) else jaccard(tokenize(old_sum), tokenize(new_sum))

    # 解释：在多数 NSFC 模板中，extraTex 文件名往往是最稳定的锚点，因此提高其权重；
    # 标题/摘要用于补充（尤其在文件名不一致时）。
    score = 0.7 * stem_score + 0.2 * title_score + 0.1 * content_score
    reason = f"stem={stem_score:.2f}(j={stem_j:.2f},sub={stem_sub:.0f}), title={title_score:.2f}, content={content_score:.2f}"
    return score, reason


def compute_structure_diff(old_analysis: ProjectAnalysis, new_analysis: ProjectAnalysis, config: Dict) -> StructureDiff:
    thresholds = get_mapping_thresholds(config)

    old_candidates = [p for p in old_analysis.extra_tex_files if p != "extraTex/@config.tex"]
    new_candidates = [p for p in new_analysis.extra_tex_files if p != "extraTex/@config.tex"]

    scored: List[MappingCandidate] = []
    for o in old_candidates:
        for n in new_candidates:
            score, reason = _score_pair(old_analysis, new_analysis, o, n)
            scored.append(MappingCandidate(old=o, new=n, score=score, reason=reason))

    scored.sort(key=lambda x: x.score, reverse=True)

    used_old = set()
    used_new = set()
    one_to_one: List[OneToOne] = []
    low_confidence: List[Dict[str, str]] = []

    for cand in scored:
        if cand.old in used_old or cand.new in used_new:
            continue
        if cand.score < thresholds.low:
            continue

        if cand.score >= thresholds.high:
            confidence = "high"
        elif cand.score >= thresholds.medium:
            confidence = "medium"
        else:
            confidence = "low"

        used_old.add(cand.old)
        used_new.add(cand.new)

        if confidence == "low":
            low_confidence.append(
                {
                    "old": cand.old,
                    "new": cand.new,
                    "score": f"{cand.score:.3f}",
                    "reason": cand.reason,
                    "action": "needs_review",
                }
            )
        else:
            one_to_one.append(
                OneToOne(
                    old=cand.old,
                    new=cand.new,
                    score=round(cand.score, 3),
                    confidence=confidence,
                    reason=cand.reason,
                )
            )

    removed = [{"file": o, "reason": "未找到可靠映射"} for o in old_candidates if o not in used_old]
    new_added = [{"file": n, "reason": "新模板存在但未映射"} for n in new_candidates if n not in used_new]

    return StructureDiff(
        one_to_one=one_to_one,
        new_added=new_added,
        removed=removed,
        low_confidence=low_confidence,
    )
