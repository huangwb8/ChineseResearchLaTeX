#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from latex_scanner import CitationHit


def write_citations_csv(path: Path, hits: List[CitationHit]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bibkey", "cite_command", "file", "line", "heading", "sentence"])
        for h in hits:
            w.writerow([h.bibkey, h.cite_command, h.file, h.line, h.heading, h.sentence])


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_deterministic_report_md(summary: Dict[str, Any]) -> str:
    """
    summary: dict produced by run_ref_alignment.py; deterministic content only.
    """
    s = summary

    def _fmt_list(items: List[str]) -> str:
        if not items:
            return "- （无）"
        return "\n".join([f"- {x}" for x in items])

    lines: List[str] = []
    lines.append("# NSFC Ref Integrity Report（确定性）")
    lines.append("")
    lines.append(f"- generated_at: {s.get('generated_at','')}")
    lines.append(f"- project_root: `{s.get('project_root','')}`")
    lines.append(f"- main_tex: `{s.get('main_tex','')}`")
    lines.append(f"- run_dir: `{s.get('run_dir','')}`")
    lines.append("")

    stats = s.get("stats") or {}
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- tex_files: {stats.get('tex_files', 0)}")
    lines.append(f"- bib_files: {stats.get('bib_files', 0)}")
    lines.append(f"- total_citations: {stats.get('total_citations', 0)}")
    lines.append(f"- unique_cited_bibkeys: {stats.get('unique_cited_bibkeys', 0)}")
    lines.append(f"- missing_bibkeys: {stats.get('missing_bibkeys', 0)}")
    lines.append(f"- duplicate_bibkeys: {stats.get('duplicate_bibkeys', 0)}")
    lines.append(f"- field_issues: {stats.get('field_issues', 0)}")
    lines.append(f"- invalid_doi: {stats.get('invalid_doi', 0)}")
    lines.append("")

    warnings = list(s.get("warnings") or [])
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        lines.append(_fmt_list(warnings))
        lines.append("")

    issues = s.get("issues") or {}

    lines.append("## Missing BibKeys（P0）")
    lines.append("")
    missing = issues.get("missing_bibkeys_detail") or []
    if missing:
        for item in missing:
            bibkey = item.get("bibkey")
            count = item.get("count", 0)
            examples = item.get("examples") or []
            lines.append(f"- `{bibkey}` (count={count})")
            for ex in examples[:3]:
                lines.append(f"  - {ex}")
    else:
        lines.append("- （无）")
    lines.append("")

    lines.append("## Duplicate BibKeys（P0/P1）")
    lines.append("")
    dup = issues.get("duplicate_bibkeys") or {}
    if dup:
        for k, srcs in dup.items():
            lines.append(f"- `{k}`")
            for s0 in srcs:
                lines.append(f"  - {s0}")
    else:
        lines.append("- （无）")
    lines.append("")

    lines.append("## Bib Field Issues（P1）")
    lines.append("")
    field_issues = issues.get("field_issues") or []
    if field_issues:
        for it in field_issues[:200]:
            lines.append(f"- `{it.get('bibkey','')}`: {it.get('issues','')}")
    else:
        lines.append("- （无）")
    lines.append("")

    lines.append("## DOI Format Issues（P1）")
    lines.append("")
    doi_issues = issues.get("doi_issues") or []
    if doi_issues:
        for it in doi_issues[:200]:
            lines.append(f"- `{it.get('bibkey','')}`: `{it.get('doi','')}`")
    else:
        lines.append("- （无）")
    lines.append("")

    online = s.get("online_verify") or {}
    if online.get("enabled"):
        lines.append("## Online Verification（确定性）")
        lines.append("")
        lines.append(f"- enabled: {online.get('enabled')}")
        lines.append(f"- checked_doi: {online.get('checked', 0)}")
        lines.append(f"- ok: {online.get('ok', 0)}")
        lines.append(f"- failed: {online.get('failed', 0)}")
        lines.append("")
        failures = online.get("failures") or []
        if failures:
            lines.append("### Failures（P0/P1）")
            lines.append("")
            for f0 in failures[:200]:
                lines.append(f"- `{f0.get('bibkey','')}` DOI=`{f0.get('doi','')}` error=`{f0.get('error','')}`")
        lines.append("")

    lines.append("## Next Step（AI 语义核查）")
    lines.append("")
    lines.append(
        "本报告仅包含确定性检查结果。请结合 `ai_ref_alignment_input.json` 由宿主 AI 进一步逐条评估“正文表述是否与该文献匹配”，并在 report_dir（默认 `./references/`）输出最终审核报告。"
    )
    lines.append("")
    return "\n".join(lines)
