#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .ai_integration import AIIntegration
from .config_access import get_bool, get_int, get_mapping, get_str
from .io_utils import read_text_streaming
from .latex_parser import strip_comments
from .limits import ai_max_input_chars


@dataclass(frozen=True)
class TermMatrix:
    headers: List[str]
    rows: List[Tuple[str, List[str], str]]
    issues: List[str]

    def to_markdown(self) -> str:
        header = "| 术语 | " + " | ".join(self.headers) + " | 结论 |"
        sep = "|---" * (len(self.headers) + 2) + "|"
        lines = [header, sep]
        for term, cells, conclusion in self.rows:
            lines.append("| " + " | ".join([term] + cells + [conclusion]) + " |")
        if self.issues:
            lines.append("")
            lines.append("问题摘要：")
            for it in self.issues:
                lines.append(f"- {it}")
        return "\n".join(lines).strip() + "\n"


def _contains_any(text: str, candidates: Sequence[str]) -> Optional[str]:
    for c in candidates:
        if c and (c in text):
            return c
    return None


def _count_alias_hits(text: str, aliases: Sequence[str]) -> Dict[str, int]:
    hits: Dict[str, int] = {}
    for a in aliases:
        a = str(a)
        if not a:
            continue
        try:
            n = len(re.findall(re.escape(a), text))
        except Exception:
            n = 0
        if n > 0:
            hits[a] = n
    return hits


def _format_hits(hits: Dict[str, int]) -> str:
    if not hits:
        return "—"
    parts = [f"{k}({v})" for k, v in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))]
    return ", ".join(parts)


def build_term_matrix(
    *,
    files: Mapping[str, Path],
    alias_groups: Mapping[str, Sequence[str]],
) -> TermMatrix:
    headers = list(files.keys())
    contents: Dict[str, str] = {}
    for label, path in files.items():
        try:
            contents[label] = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            contents[label] = ""

    rows: List[Tuple[str, List[str], str]] = []
    issues: List[str] = []

    for canonical, aliases in alias_groups.items():
        per_file_hits: Dict[str, Dict[str, int]] = {}
        for label in headers:
            text = contents.get(label, "")
            per_file_hits[label] = _count_alias_hits(text, list(aliases))

        any_hit = any(bool(h) for h in per_file_hits.values())
        if not any_hit:
            continue

        variants: List[str] = sorted({k for hits in per_file_hits.values() for k in hits.keys()})
        inconsistent_across_files = len(variants) > 1
        inconsistent_within_file = any(len(hits.keys()) > 1 for hits in per_file_hits.values())
        conclusion = "✅ 一致" if (not inconsistent_across_files and not inconsistent_within_file) else "⚠️ 不一致"
        if inconsistent_across_files:
            issues.append(f"术语“{canonical}”跨章节表述不一致：{', '.join(variants)}")
        if inconsistent_within_file:
            bad = [label for label, hits in per_file_hits.items() if len(hits.keys()) > 1]
            issues.append(f"术语“{canonical}”在同一章节内出现多种表述：{', '.join(bad)}")

        cells = []
        for label in headers:
            cells.append(_format_hits(per_file_hits.get(label, {})))
        rows.append((canonical, cells, conclusion))

    return TermMatrix(headers=headers, rows=rows, issues=issues)


def build_term_matrices(
    *,
    files: Mapping[str, Path],
    dimensions: Mapping[str, Mapping[str, Sequence[str]]],
) -> Dict[str, TermMatrix]:
    out: Dict[str, TermMatrix] = {}
    for dim_name, alias_groups in dimensions.items():
        if not alias_groups:
            continue
        out[str(dim_name)] = build_term_matrix(files=files, alias_groups=alias_groups)
    return out


def format_term_matrices_markdown(mats: Mapping[str, TermMatrix]) -> str:
    if not mats:
        return "（未配置术语一致性规则：terminology.dimensions 或 terminology.alias_groups 为空）\n"
    parts: List[str] = []
    for name, mat in mats.items():
        parts.append(f"## {name}\n")
        parts.append(mat.to_markdown().rstrip() + "\n")
    return "\n".join(parts).strip() + "\n"


class CrossChapterValidator:
    def __init__(self, *, files: Mapping[str, Path], terminology_config: Mapping[str, object]) -> None:
        self.files = dict(files)
        self.terminology_config = dict(terminology_config)

    def build(self) -> Dict[str, TermMatrix]:
        dims = self.terminology_config.get("dimensions")
        if isinstance(dims, dict) and dims:
            # dimensions: {dim_name: {canonical: [aliases...]}}
            safe_dims: Dict[str, Dict[str, Sequence[str]]] = {}
            for dn, groups in dims.items():
                if not isinstance(dn, str) or not isinstance(groups, dict):
                    continue
                safe_groups: Dict[str, Sequence[str]] = {}
                for k, v in groups.items():
                    if isinstance(k, str) and isinstance(v, list):
                        safe_groups[k] = [str(x) for x in v if str(x).strip()]
                if safe_groups:
                    safe_dims[dn] = safe_groups
            return build_term_matrices(files=self.files, dimensions=safe_dims)

        alias_groups = self.terminology_config.get("alias_groups")
        if isinstance(alias_groups, dict) and alias_groups:
            safe_groups: Dict[str, Sequence[str]] = {}
            for k, v in alias_groups.items():
                if isinstance(k, str) and isinstance(v, list):
                    safe_groups[k] = [str(x) for x in v if str(x).strip()]
            return build_term_matrices(files=self.files, dimensions={"术语": safe_groups})

        return {}

    def to_markdown(self) -> str:
        mats = self.build()
        return format_term_matrices_markdown(mats)


def _legacy_report(*, files: Mapping[str, Path], terminology_config: Mapping[str, object]) -> str:
    validator = CrossChapterValidator(files=files, terminology_config=terminology_config)
    return validator.to_markdown()


class TermConsistencyAI:
    """
    AI 主导的跨章节术语一致性检查。

    说明：
    - 仅在 ai.is_available() 时尝试调用 AI；否则使用 legacy 规则矩阵作为 fallback
    - 主要目的：减少“手写别名组”的维护成本，并捕捉隐含同义词/缩写混用
    """

    def __init__(self, ai: AIIntegration) -> None:
        self.ai = ai

    async def check(
        self,
        *,
        files: Mapping[str, Path],
        max_chars: int,
        cache_dir: Optional[Path] = None,
        fresh: bool = False,
    ) -> Dict[str, Any]:
        max_chars = max(int(max_chars), 1000)
        file_contents: Dict[str, str] = {}
        for label, path in files.items():
            try:
                res = read_text_streaming(Path(path), max_bytes=None)
                # 只给 AI 看“去注释后”的文本，降低噪音
                file_contents[str(label)] = strip_comments(res.text)[:max_chars]
            except Exception:
                file_contents[str(label)] = ""

        prompt = (
            "请分析以下 LaTeX 文档内容的术语/缩写/指标口径一致性。\n"
            "要求：\n"
            "1) 只输出 JSON（不要解释）\n"
            "2) 不要杜撰文献引用与 DOI\n"
            "3) 输出尽量具体：指出冲突的两种/多种表述分别出现在哪里\n\n"
            "输入（JSON，key 为章节名，value 为去注释后的 LaTeX 文本，可能截断）：\n"
            f"{json.dumps(file_contents, ensure_ascii=False, indent=2)[:max_chars]}\n\n"
            "返回 JSON 结构：\n"
            "{\n"
            '  "issues": [\n'
            '    {"category": "research_objects|metrics|terminology|abbrev", "detail": "...", "examples": ["..."]}\n'
            "  ],\n"
            '  "suggestions": ["..."]\n'
            "}\n"
        )

        def _fallback() -> Dict[str, Any]:
            return {"issues": [], "suggestions": []}

        obj = await self.ai.process_request(
            task="term_consistency",
            prompt=prompt,
            output_format="json",
            fallback=_fallback,
            cache_dir=cache_dir,
            fresh=fresh,
        )
        return obj if isinstance(obj, dict) else _fallback()

    @staticmethod
    def format_markdown(obj: Dict[str, Any]) -> str:
        issues = obj.get("issues", []) if isinstance(obj.get("issues"), list) else []
        suggestions = obj.get("suggestions", []) if isinstance(obj.get("suggestions"), list) else []

        lines = ["## 术语一致性检查（AI 语义分析）", ""]
        if not issues:
            lines.append("- ✅ 未发现明显术语不一致（AI 视角）")
        else:
            for it in issues[:30]:
                if not isinstance(it, dict):
                    continue
                cat = str(it.get("category", "") or "").strip() or "terminology"
                detail = str(it.get("detail", "") or "").strip()
                ex = it.get("examples", [])
                ex_list = [str(x) for x in ex] if isinstance(ex, list) else []
                if detail:
                    lines.append(f"- ⚠️ [{cat}] {detail}")
                    for e in ex_list[:5]:
                        if e.strip():
                            lines.append(f"  - {e.strip()}")

        if suggestions:
            lines.append("")
            lines.append("### 修改建议")
            for s in suggestions[:20]:
                if str(s).strip():
                    lines.append(f"- {str(s).strip()}")

        return "\n".join(lines).strip() + "\n"


def term_consistency_report(
    *,
    files: Mapping[str, Path],
    config: Mapping[str, Any],
    ai: Optional[AIIntegration] = None,
    cache_dir: Optional[Path] = None,
    fresh: bool = False,
) -> str:
    terminology_cfg = get_mapping(config, "terminology")
    mode = get_str(terminology_cfg, "mode", "auto").strip().lower()
    alt_mode = get_str(terminology_cfg, "ai_mode", "").strip().lower()
    if alt_mode in {"auto", "ai", "legacy", "legacy_only", "semantic_only"}:
        mode = alt_mode
    if mode == "legacy_only":
        mode = "legacy"
    enable_ai_semantic = get_bool(terminology_cfg, "enable_ai_semantic_check", True)
    ai_cfg = get_mapping(terminology_cfg, "ai")
    ai_enabled = get_bool(ai_cfg, "enabled", True)
    legacy_md = _legacy_report(files=files, terminology_config=terminology_cfg)

    if (not enable_ai_semantic) or mode == "legacy":
        return legacy_md

    ai_obj = ai
    if ai_obj is None:
        return legacy_md
    if not ai_enabled or not ai_obj.is_available():
        return legacy_md

    max_chars = get_int(ai_cfg, "max_chars", ai_max_input_chars(config))
    obj = asyncio.run(TermConsistencyAI(ai_obj).check(files=files, max_chars=max_chars, cache_dir=cache_dir, fresh=fresh))
    ai_md = TermConsistencyAI.format_markdown(obj)
    if mode == "semantic_only":
        return ai_md
    return ai_md.rstrip() + "\n\n" + legacy_md
