#!/usr/bin/env python3
"""
update_working_conditions_data_extraction.py - 写入数据抽取表（Score/Subtopic + Extraction 版）

输入：
  - papers.jsonl：推荐使用已评分文献（fields: doi/title/year/venue/score/subtopic/extraction）
  - extraction 字段包含：{design, key_findings, limitations}

写入：
  - 如目标文件包含 marker，则替换 `<!-- AUTO:DATA_EXTRACTION_TABLE:BEGIN --> ... <!-- AUTO:DATA_EXTRACTION_TABLE:END -->`
  - 如无 marker，则写入一个含 marker 的完整表格块
  - 表格包含9列：Score | Subtopic | DOI | Year | Title | Venue | Design | Key findings | Limitations

v3.2 更新：
  - 新增从 AI 评分结果的 extraction 字段读取 Design/Key findings/Limitations
  - 确保 AI 评分时同步提取的数据能正确填充到数据抽取表
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

BEGIN = "<!-- AUTO:DATA_EXTRACTION_TABLE:BEGIN -->"
END = "<!-- AUTO:DATA_EXTRACTION_TABLE:END -->"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _normalize_doi(doi: str) -> str:
    doi = (doi or "").strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = re.sub(r"^doi:\\s*", "", doi, flags=re.IGNORECASE).strip()
    return doi.lower()


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


@dataclass(frozen=True)
class Row:
    score: Optional[float]
    subtopic: str
    doi: str
    year: Optional[int]
    title: str
    venue: str
    design: str
    key_findings: str
    limitations: str


def _load_papers_jsonl(path: Path) -> Dict[str, Dict[str, Any]]:
    by_doi: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            doi = _normalize_doi(_safe_str(obj.get("doi"))) or _safe_str(obj.get("id"))
            if not doi:
                continue
            by_doi[doi] = obj
    return by_doi


def _iter_rows(papers_by_doi: Dict[str, Dict[str, Any]]) -> Iterable[Row]:
    for doi, paper in papers_by_doi.items():
        title = _safe_str(paper.get("title")) or doi
        venue = _safe_str(paper.get("venue"))
        year_raw = paper.get("year")
        try:
            year = int(year_raw) if year_raw not in (None, "", 0) else None
        except Exception:
            year = None
        score_raw = paper.get("score")
        try:
            score: Optional[float] = float(score_raw) if score_raw not in (None, "") else None
        except Exception:
            score = None
        subtopic = _safe_str(paper.get("subtopic")) or "—"

        # 从 extraction 字段提取数据抽取表字段
        extraction = paper.get("extraction") or {}
        if isinstance(extraction, dict):
            design = _safe_str(extraction.get("design"))
            key_findings = _safe_str(extraction.get("key_findings"))
            limitations = _safe_str(extraction.get("limitations"))
        else:
            design = key_findings = limitations = ""

        yield Row(
            score=score,
            subtopic=subtopic,
            doi=doi,
            year=year,
            title=title,
            venue=venue,
            design=design,
            key_findings=key_findings,
            limitations=limitations
        )


def _render_table(rows: list[Row]) -> str:
    lines = [
        "| Score | Subtopic | DOI | Year | Title | Venue | Design | Key findings | Limitations |",
        "|---:|---|---|---:|---|---|---|---|---|",
    ]
    for r in rows:
        score = f"{r.score:.1f}" if r.score is not None else ""
        year = str(r.year) if r.year is not None else ""
        title = r.title.replace("|", " ").replace("\n", " ").strip()
        venue = r.venue.replace("|", " ").replace("\n", " ").strip()
        subtopic = r.subtopic.replace("|", " ").replace("\n", " ").strip()
        design = r.design.replace("|", " ").replace("\n", " ").strip() if r.design else ""
        key_findings = r.key_findings.replace("|", " ").replace("\n", " ").strip() if r.key_findings else ""
        limitations = r.limitations.replace("|", " ").replace("\n", " ").strip() if r.limitations else ""
        lines.append(f"| {score} | {subtopic} | {r.doi} | {year} | {title} | {venue} | {design} | {key_findings} | {limitations} |")
    return "\n".join(lines) + "\n"


def _replace_marker_block(text: str, new_block: str) -> str:
    if BEGIN in text and END in text:
        pattern = re.compile(rf"{re.escape(BEGIN)}.*?{re.escape(END)}", flags=re.S)
        replacement = f"{BEGIN}\n{new_block}{END}"
        return pattern.sub(replacement, text, count=1)
    return f"{BEGIN}\n{new_block}{END}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Data Extraction table with score/subtopic columns.")
    parser.add_argument("--md", required=True, type=Path, help="Path to markdown table output")
    parser.add_argument("--papers", required=True, type=Path, help="Path to papers jsonl (selected/scored)")
    parser.add_argument("--max-rows", type=int, default=200, help="Max rows to render (default: 200)")
    args = parser.parse_args()

    md = args.md.resolve()
    papers = args.papers.resolve()

    if not papers.exists():
        print(f"✗ missing papers: {papers}", file=sys.stderr)
        return 1

    try:
        papers_by_doi = _load_papers_jsonl(papers)
    except Exception as e:
        print(f"✗ failed to load papers: {e}", file=sys.stderr)
        return 1

    rows = list(_iter_rows(papers_by_doi))
    rows.sort(key=lambda r: (-(r.score or 0), r.subtopic.lower(), -(r.year or 0)))
    if args.max_rows > 0:
        rows = rows[: args.max_rows]
    table = _render_table(rows)

    existing = _read_text(md)
    new_text = _replace_marker_block(existing, table)
    _write_text(md, new_text)
    print(f"✓ 写入数据抽取表: {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
