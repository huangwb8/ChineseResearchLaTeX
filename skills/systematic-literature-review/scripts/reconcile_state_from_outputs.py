#!/usr/bin/env python3
"""
reconcile_state_from_outputs.py - 从目录实际产物反推并修复 pipeline_state.json

适用场景：
- 外部编排器生成了 tex/pdf/docx/验证报告等交付物，但未回写 pipeline_state
- 历史 run 目录需要恢复“产物=状态”的可追溯性

默认 dry-run；使用 --apply 才会写回。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


STAGE_ORDER: list[str] = [
    "0_setup",
    "1_search",
    "2_dedupe",
    "3_score",
    "4_select",
    "4.5_word_budget",
    "5_write",
    "6_validate",
    "7_export",
]


def _find_one(work_dir: Path, pattern: str) -> Optional[Path]:
    hits = sorted(work_dir.glob(pattern))
    return hits[0] if hits else None


def _find_one_in(dir_path: Path, pattern: str) -> Optional[Path]:
    if not dir_path.exists():
        return None
    hits = sorted(dir_path.glob(pattern))
    return hits[0] if hits else None


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ensure_state_shape(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("version", "2.0")
    state.setdefault("completed_stages", [])
    state.setdefault("input_files", {})
    state.setdefault("output_files", {})
    state.setdefault("metrics", {})
    if not isinstance(state.get("completed_stages"), list):
        state["completed_stages"] = []
    if not isinstance(state.get("input_files"), dict):
        state["input_files"] = {}
    if not isinstance(state.get("output_files"), dict):
        state["output_files"] = {}
    if not isinstance(state.get("metrics"), dict):
        state["metrics"] = {}
    return state


def _mark_completed(state: Dict[str, Any], stage: str) -> None:
    done = state.get("completed_stages") or []
    if stage not in done:
        done.append(stage)
    # 按 STAGE_ORDER 排序，保持稳定
    ordered = [s for s in STAGE_ORDER if s in done]
    # 保留未知 stage（若存在）
    for s in done:
        if s not in ordered:
            ordered.append(s)
    state["completed_stages"] = ordered


def _detect(work_dir: Path) -> Tuple[Dict[str, str], Dict[str, str], List[str]]:
    """
    返回 (input_files, output_files, completed_stages)
    """
    hidden = work_dir / ".systematic-literature-review"
    artifacts = hidden / "artifacts"

    output_files: Dict[str, str] = {}
    input_files: Dict[str, str] = {}
    completed: list[str] = []

    # final-ish outputs in work_dir
    wc = _find_one(work_dir, "*_工作条件.md")
    tex = _find_one(work_dir, "*_review.tex")
    bib = _find_one(work_dir, "*_参考文献.bib")
    pdf = _find_one(work_dir, "*_review.pdf")
    docx = _find_one(work_dir, "*_review.docx")
    report = _find_one(work_dir, "*_验证报告.md")

    if wc:
        output_files["working_conditions"] = str(wc)
        completed.append("0_setup")
    if tex:
        output_files["review_tex"] = str(tex)
        completed.append("5_write")
    if bib:
        output_files["references_bib"] = str(bib)
        completed.append("4_select")
    if pdf:
        output_files["review_pdf"] = str(pdf)
    if docx:
        output_files["review_word"] = str(docx)
    if report:
        output_files["validation_report"] = str(report)
        completed.append("6_validate")

    if pdf and docx:
        completed.append("7_export")

    # artifacts
    papers = _find_one_in(artifacts, "papers_*.jsonl")
    deduped = _find_one_in(artifacts, "papers_deduped_*.jsonl")
    scored = _find_one_in(artifacts, "scored_papers_*.jsonl")
    selected = _find_one_in(artifacts, "selected_papers_*.jsonl")
    budget_final = _find_one_in(artifacts, "word_budget_final.csv")
    search_log = _find_one_in(artifacts, "search_log_*.json")

    if papers:
        input_files["papers"] = str(papers)
        completed.append("1_search")
    if deduped:
        input_files["papers_deduped"] = str(deduped)
        completed.append("2_dedupe")
    if scored:
        input_files["scored_papers"] = str(scored)
        completed.append("3_score")
    if selected:
        input_files["selected_papers"] = str(selected)
        completed.append("4_select")
    if budget_final:
        output_files["word_budget_final"] = str(budget_final)
        completed.append("4.5_word_budget")
    if search_log:
        output_files["search_log"] = str(search_log)

    # dedupe map
    dedupe_map = _find_one_in(artifacts, "dedupe_map_*.json")
    if dedupe_map:
        output_files["dedupe_map"] = str(dedupe_map)

    # 去重并按顺序输出
    completed = [s for s in STAGE_ORDER if s in set(completed)]
    return input_files, output_files, completed


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile pipeline_state.json from actual outputs")
    parser.add_argument("--work-dir", required=True, type=Path, help="run directory")
    parser.add_argument("--apply", action="store_true", help="write back pipeline_state.json (default: dry-run)")
    args = parser.parse_args()

    work_dir = args.work_dir.expanduser().resolve()
    if not work_dir.exists() or not work_dir.is_dir():
        raise SystemExit(f"work_dir not found: {work_dir}")

    hidden = work_dir / ".systematic-literature-review"
    state_path = hidden / "pipeline_state.json"

    state = _ensure_state_shape(_load_state(state_path))
    state.setdefault("topic", state.get("topic") or work_dir.name)
    state.setdefault("domain", state.get("domain") or "general")
    state.setdefault("metrics", {})
    if isinstance(state.get("metrics"), dict):
        state["metrics"]["work_dir"] = str(work_dir)

    new_inputs, new_outputs, new_completed = _detect(work_dir)

    # merge
    state["input_files"].update(new_inputs)
    state["output_files"].update(new_outputs)
    for s in new_completed:
        _mark_completed(state, s)

    print(f"work_dir:  {work_dir}")
    print(f"state:     {state_path}")
    print(f"mode:      {'apply' if args.apply else 'dry-run'}")
    print(f"completed: {', '.join(state.get('completed_stages') or []) or '(none)'}")

    if not args.apply:
        return 0

    hidden.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✓ pipeline_state.json updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
