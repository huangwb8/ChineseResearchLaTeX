#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_access import get_mapping
from .hard_rules import QualityRule, StructureRule, load_quality_rule, load_structure_rule
from .latex_parser import parse_subsubsections, strip_comments
from .reference_validator import CitationCheckResult, check_citations
from .wordcount import WordCountResult, count_cjk_chars


@dataclass(frozen=True)
class Tier1Report:
    structure_ok: bool
    subsubsection_count: int
    missing_subsubsections: List[str]
    citation_ok: bool
    missing_citation_keys: List[str]
    missing_doi_keys: List[str]
    invalid_doi_keys: List[str]
    word_count: int
    forbidden_phrases_hits: List[str]
    avoid_commands_hits: List[str]


@dataclass
class DiagnosticReport:
    tier1: Tier1Report
    tier2: Optional[Dict[str, Any]] = None
    dimension_coverage: Optional[Dict[str, Any]] = None
    boastful_expressions: Optional[Dict[str, Any]] = None
    word_target: Optional[Dict[str, Any]] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier1": {
                "structure_ok": self.tier1.structure_ok,
                "subsubsection_count": self.tier1.subsubsection_count,
                "missing_subsubsections": self.tier1.missing_subsubsections,
                "citation_ok": self.tier1.citation_ok,
                "missing_citation_keys": self.tier1.missing_citation_keys,
                "missing_doi_keys": self.tier1.missing_doi_keys,
                "invalid_doi_keys": self.tier1.invalid_doi_keys,
                "word_count": self.tier1.word_count,
                "forbidden_phrases_hits": self.tier1.forbidden_phrases_hits,
                "avoid_commands_hits": self.tier1.avoid_commands_hits,
            },
            "tier2": self.tier2,
            "dimension_coverage": self.dimension_coverage,
            "boastful_expressions": self.boastful_expressions,
            "word_target": self.word_target,
            "notes": self.notes,
        }


def _check_structure(text: str, rule: StructureRule) -> tuple[bool, int, List[str]]:
    secs = parse_subsubsections(text)
    count = len(secs)
    if count < int(rule.min_subsubsection_count):
        missing = list(rule.expected_subsubsections) if rule.expected_subsubsections else []
        return False, count, missing

    if not rule.strict_title_match or not rule.expected_subsubsections:
        return True, count, []

    titles = {s.title for s in secs}
    missing = [t for t in rule.expected_subsubsections if t not in titles]
    return (len(missing) == 0), count, missing


def _check_quality(text: str, rule: QualityRule) -> tuple[List[str], List[str]]:
    t = strip_comments(text)
    forbidden_hits = [p for p in rule.high_risk_examples if p and (p in t)]
    cmd_hits = [c for c in rule.avoid_commands if c and (c in t)]
    return forbidden_hits, cmd_hits


def run_tier1(
    *,
    tex_text: str,
    project_root: Path,
    config: Dict[str, Any],
) -> Tier1Report:
    structure_rule = load_structure_rule(config)
    quality_rule = load_quality_rule(config)

    structure_ok, count, missing_sections = _check_structure(tex_text, structure_rule)

    targets = get_mapping(config, "targets")
    bib_globs = targets.get("bib_globs", ["references/*.bib"])
    cite_result: CitationCheckResult = check_citations(
        tex_text=tex_text, project_root=project_root, bib_globs=bib_globs
    )
    citation_ok = len(cite_result.missing_keys) == 0

    wc_cfg = get_mapping(config, "word_count")
    mode = str(wc_cfg.get("mode", "cjk_only")).strip() or "cjk_only"
    wc: WordCountResult = count_cjk_chars(tex_text, mode=mode)
    forbidden_hits, cmd_hits = _check_quality(tex_text, quality_rule)

    return Tier1Report(
        structure_ok=structure_ok,
        subsubsection_count=count,
        missing_subsubsections=missing_sections,
        citation_ok=citation_ok,
        missing_citation_keys=cite_result.missing_keys,
        missing_doi_keys=cite_result.missing_doi_keys,
        invalid_doi_keys=cite_result.invalid_doi_keys,
        word_count=wc.cjk_count,
        forbidden_phrases_hits=forbidden_hits,
        avoid_commands_hits=cmd_hits,
    )


def format_tier1(report: Tier1Report) -> str:
    lines: List[str] = []
    if report.structure_ok:
        lines.append(f"- ✅ 结构完整：subsubsection={report.subsubsection_count}")
    else:
        missing = "、".join(report.missing_subsubsections) if report.missing_subsubsections else "(未知)"
        lines.append(f"- ❌ 结构缺失：subsubsection={report.subsubsection_count}，缺少：{missing}")

    if report.citation_ok:
        lines.append("- ✅ 引用格式：所有 \\cite{...} 均在 .bib 中存在")
    else:
        lines.append(f"- ❌ 引用缺失：.bib 未找到 keys：{', '.join(report.missing_citation_keys)}")

    if report.missing_doi_keys:
        lines.append(f"- ⚠️ DOI 缺失：建议补齐（可用 DOI/链接线索补齐 .bib）keys：{', '.join(report.missing_doi_keys[:10])}")
    if report.invalid_doi_keys:
        lines.append(f"- ⚠️ DOI 格式疑似不合法：建议核验/修正 keys：{', '.join(report.invalid_doi_keys[:10])}")

    lines.append(f"- ℹ️ 字数统计（中文字符，不含注释）：{report.word_count}")

    if report.forbidden_phrases_hits:
        lines.append(f"- ⚠️ 高风险表述（示例命中）：{', '.join(report.forbidden_phrases_hits)}")
    if report.avoid_commands_hits:
        lines.append(f"- ⚠️ 可能破坏模板的命令：{', '.join(report.avoid_commands_hits)}")

    return "\n".join(lines).strip() + "\n"
