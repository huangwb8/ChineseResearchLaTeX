#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # type: ignore
except (ModuleNotFoundError, ImportError):  # pragma: no cover - 允许在无 PyYAML 环境降级
    yaml = None

from .ai_integration import AIIntegration


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
    except (OSError, UnicodeError, ValueError, AttributeError, yaml.YAMLError):  # type: ignore[attr-defined]
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


def _example_relpath(skill_root: Path, p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(skill_root).resolve()))
    except ValueError:
        return str(Path(p).resolve())


class ExampleRecommenderAI:
    """
    AI 主导的示例推荐（语义匹配），并提供可解释理由。
    - AI 不可用时回退到关键词/类别启发式（recommend_examples）
    """

    def __init__(self, ai: AIIntegration) -> None:
        self.ai = ai

    async def recommend(
        self,
        *,
        skill_root: Path,
        query: str,
        top_k: int = 3,
        cache_dir: Optional[Path] = None,
        fresh: bool = False,
    ) -> List[Dict[str, Any]]:
        skill_root = Path(skill_root).resolve()
        items: List[Dict[str, Any]] = []
        for category, path, meta in _iter_example_files(skill_root):
            try:
                tex = Path(path).read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeError):
                tex = ""
            keywords = meta.get("keywords", []) if isinstance(meta, dict) else []
            if not isinstance(keywords, list):
                keywords = []
            items.append(
                {
                    "relpath": _example_relpath(skill_root, path),
                    "category": str(meta.get("category") or category),
                    "keywords": [str(x) for x in keywords if str(x).strip()][:20],
                    "description": str(meta.get("description", "") or "").strip(),
                    "excerpt": (tex or "")[:600],
                }
            )

        prompt = (
            "你是示例推荐器。用户会给出一个主题/方向，请从候选示例中选择最相关的若干个。\n"
            "要求：\n"
            "1) 只输出 JSON（不要解释）\n"
            "2) 只从候选 relpath 中选；不要编造不存在的示例\n"
            "3) 给出简短推荐理由（1 句即可）\n\n"
            f"用户查询：{query}\n\n"
            "候选示例（JSON 数组，字段：relpath/category/keywords/description/excerpt）：\n"
            f"{json.dumps(items, ensure_ascii=False, indent=2)[:24000]}\n\n"
            "返回 JSON：\n"
            "{\n"
            '  "recommendations": [\n'
            '    {"rank": 1, "relpath": "...", "title": "...(可选)", "reason": "..."}\n'
            "  ]\n"
            "}\n"
        )

        def _fallback() -> Dict[str, Any]:
            return {"recommendations": []}

        obj = await self.ai.process_request(
            task="recommend_examples",
            prompt=prompt,
            output_format="json",
            fallback=_fallback,
            cache_dir=cache_dir,
            fresh=fresh,
        )
        recs = obj.get("recommendations", []) if isinstance(obj, dict) else []
        if not isinstance(recs, list):
            return []

        allowed = {it["relpath"] for it in items if isinstance(it.get("relpath"), str)}
        out: List[Dict[str, Any]] = []
        for r in recs[: max(int(top_k), 1)]:
            if not isinstance(r, dict):
                continue
            rel = str(r.get("relpath", "") or "").strip()
            if rel and rel in allowed:
                out.append(
                    {
                        "rank": int(r.get("rank", len(out) + 1) or (len(out) + 1)),
                        "relpath": rel,
                        "reason": str(r.get("reason", "") or "").strip(),
                        "title": str(r.get("title", "") or "").strip(),
                    }
                )
        return out

    @staticmethod
    def format_markdown(recs: List[Dict[str, Any]]) -> str:
        if not recs:
            return "（未找到可用示例）\n"
        lines = ["推荐示例："]
        for r in recs:
            rel = str(r.get("relpath", "") or "").strip()
            reason = str(r.get("reason", "") or "").strip()
            title = str(r.get("title", "") or "").strip()
            suffix = f"（{title}）" if title else ""
            if reason:
                lines.append(f"- {rel}{suffix}：{reason}")
            else:
                lines.append(f"- {rel}{suffix}")
        return "\n".join(lines).strip() + "\n"


def recommend_examples_markdown(
    *,
    skill_root: Path,
    query: str,
    top_k: int = 3,
    ai: Optional[AIIntegration] = None,
    cache_dir: Optional[Path] = None,
    fresh: bool = False,
) -> str:
    if ai is not None and ai.is_available():
        recs = asyncio.run(
            ExampleRecommenderAI(ai).recommend(
                skill_root=Path(skill_root),
                query=query,
                top_k=top_k,
                cache_dir=cache_dir,
                fresh=fresh,
            )
        )
        if recs:
            return ExampleRecommenderAI.format_markdown(recs)
    matches = recommend_examples(skill_root=Path(skill_root), query=query, top_k=top_k)
    return format_example_recommendations(matches)
