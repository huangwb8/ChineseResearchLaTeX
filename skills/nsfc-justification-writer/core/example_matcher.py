#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - 允许在无 PyYAML 环境降级
    yaml = None


@dataclass(frozen=True)
class ExampleMatch:
    path: Path
    category: str
    score: float
    description: str = ""


def _read_example_metadata(tex_path: Path) -> Dict[str, Any]:
    if yaml is None:
        return {}
    candidates = [
        tex_path.with_suffix(".metadata.yaml"),
        tex_path.with_suffix(".metadata.yml"),
        tex_path.parent / "metadata.yaml",
        tex_path.parent / "metadata.yml",
    ]
    meta_path = next((p for p in candidates if p.exists() and p.is_file()), None)
    if meta_path is None:
        return {}
    try:
        raw = yaml.safe_load(meta_path.read_text(encoding="utf-8", errors="ignore")) or {}
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _iter_example_files(skill_root: Path) -> Iterable[Tuple[str, Path, Dict[str, Any]]]:
    root = (Path(skill_root).resolve() / "examples").resolve()
    if not root.is_dir():
        return []
    out: List[Tuple[str, Path, Dict[str, Any]]] = []
    for p in root.glob("**/*.tex"):
        if p.is_file():
            category = p.parent.name
            meta = _read_example_metadata(p)
            out.append((category, p.resolve(), meta))
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
    cues = {
        "medical": ["临床", "医学", "医疗", "患者", "疾病", "诊疗", "医院", "影像", "队列", "预测"],
        "engineering": ["算法", "工程", "系统", "部署", "算力", "时延", "吞吐", "鲁棒", "容错", "在线"],
        "cs": ["计算机", "软件", "系统", "网络", "安全", "隐私", "联邦学习", "大模型", "LLM", "推理", "编译"],
        "materials": ["材料", "合金", "电池", "催化", "表界面", "缺陷", "晶体", "相变", "性能", "制备"],
        "chemistry": ["化学", "催化", "反应", "电化学", "分子", "配体", "溶剂", "动力学", "选择性", "机理"],
        "biology": ["生物", "基因", "蛋白", "组学", "单细胞", "转录", "代谢", "通路", "表型", "进化"],
        "math": ["数学", "优化", "证明", "定理", "随机", "凸", "非凸", "数值", "偏微分", "PDE"],
        "social": ["社会", "经济", "政策", "治理", "教育", "问卷", "访谈", "机制", "行为"],
        "informatics": ["信息学", "数据", "知识图谱", "文本挖掘", "检索", "本体", "标注"],
    }
    if any(x in q for x in cues.get(category, [])):
        return 2.0
    return 0.0


def _keyword_hits(*, query: str, keywords: List[str]) -> int:
    q = (query or "").strip()
    q_lower = q.lower()
    hits = 0
    for kw in keywords or []:
        k = str(kw or "").strip()
        if not k:
            continue
        if k in q:
            hits += 1
            continue
        if k.lower() in q_lower:
            hits += 1
    return hits


def recommend_examples(*, skill_root: Path, query: str, top_k: int = 3) -> List[ExampleMatch]:
    q_tokens = _tokens(query)
    q_set = set(q_tokens)
    matches: List[ExampleMatch] = []
    for category, path, meta in _iter_example_files(skill_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        e_tokens = _tokens(text)
        overlap = len([t for t in e_tokens if t in q_set])
        keywords = meta.get("keywords", []) if isinstance(meta, dict) else []
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(x) for x in keywords if str(x).strip()]
        meta_text = " ".join(keywords) + " " + str(meta.get("description", "") or "")
        meta_tokens = _tokens(meta_text)
        meta_overlap = len([t for t in meta_tokens if t in q_set])
        hit_n = _keyword_hits(query=query, keywords=keywords)
        score = float(overlap) + float(meta_overlap) + float(hit_n) * 2.0 + _category_boost(query, category)
        matches.append(
            ExampleMatch(
                path=path,
                category=str(meta.get("category") or category),
                score=score,
                description=str(meta.get("description", "") or "").strip(),
            )
        )
    matches.sort(key=lambda m: (m.score, m.path.name), reverse=True)
    return matches[: max(int(top_k), 1)]


def format_example_recommendations(matches: List[ExampleMatch]) -> str:
    if not matches:
        return "（未找到可用示例）\n"
    lines = ["推荐示例："]
    for m in matches:
        suffix = f"（{m.description}）" if m.description else ""
        lines.append(f"- {m.category}: {m.path}{suffix}")
    return "\n".join(lines).strip() + "\n"
