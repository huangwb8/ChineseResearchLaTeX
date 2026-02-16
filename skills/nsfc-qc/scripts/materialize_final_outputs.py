#!/usr/bin/env python3
"""
Materialize nsfc-qc standard outputs under:
  <project_root>/.nsfc-qc/runs/<run_id>/final/

This script is deterministic and safe:
- It never modifies proposal sources.
- It only writes/overwrites files under the run's final/ directory.

It can be run even if parallel threads were not executed yet.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_parallel_vibe_root(run_dir: Path) -> Optional[Path]:
    pv = run_dir / ".parallel_vibe"
    if pv.exists() and pv.is_dir():
        return pv
    return None


def _collect_thread_results(run_dir: Path) -> List[str]:
    pv = _find_parallel_vibe_root(run_dir)
    if not pv:
        return []
    results: List[str] = []
    for p in pv.rglob("RESULT.md"):
        try:
            results.append(str(p.relative_to(run_dir)))
        except Exception:
            results.append(str(p))
    return sorted(set(results))


def _load_report_template() -> Optional[str]:
    # Resolve template relative to this script.
    skill_root = Path(__file__).resolve().parents[1]
    tpl = skill_root / "templates" / "REPORT_TEMPLATE.md"
    try:
        return tpl.read_text(encoding="utf-8")
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--runs-root", default=".nsfc-qc/runs", help="relative to project-root")
    ap.add_argument("--overwrite", action="store_true", help="overwrite existing final outputs")
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    run_id = str(args.run_id).strip()
    if Path(run_id).name != run_id or ("/" in run_id) or ("\\" in run_id):
        print("error: --run-id must be a simple name (no path separators)", file=sys.stderr)
        return 2

    runs_root = Path(args.runs_root)
    if runs_root.is_absolute() or ".." in runs_root.parts:
        print("error: --runs-root must be a relative path without '..'", file=sys.stderr)
        return 2
    if not runs_root.parts or runs_root.parts[0] != ".nsfc-qc":
        print("error: --runs-root must start with .nsfc-qc/ to keep artifacts isolated", file=sys.stderr)
        return 2

    run_dir = (project_root / runs_root / run_id).resolve()
    try:
        run_dir.relative_to(project_root.resolve())
    except Exception:
        print("error: resolved run directory escapes project_root", file=sys.stderr)
        return 2
    final_dir = run_dir / "final"
    artifacts_dir = run_dir / "artifacts"
    final_dir.mkdir(parents=True, exist_ok=True)

    precheck = _read_json(artifacts_dir / "precheck.json") or {}
    run_meta = _read_json(artifacts_dir / "run_meta.json") or {}

    main_tex = str(run_meta.get("main_tex") or precheck.get("main_tex") or "main.tex")
    execution = str(run_meta.get("execution") or "")

    thread_results = _collect_thread_results(run_dir)
    pv_root = _find_parallel_vibe_root(run_dir)
    pv_main_summary = ""
    if pv_root:
        # parallel-vibe layout: .parallel_vibe/<project_id>/@main/summary.md
        for p in pv_root.rglob("@main/summary.md"):
            try:
                pv_main_summary = str(p.relative_to(run_dir))
            except Exception:
                pv_main_summary = str(p)
            break

    generated_at = datetime.now().isoformat(timespec="seconds")

    metrics = {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at": generated_at,
        "project_root": str(project_root),
        "main_tex": main_tex,
        "threads": run_meta.get("threads"),
        "execution": execution,
        "precheck": {
            "citation_stats": (precheck.get("citation_stats") or {}),
            "compile": (precheck.get("compile") or {}),
            "typography": (precheck.get("typography") or {}),
        },
        "artifacts": {
            "precheck_json": str((artifacts_dir / "precheck.json").relative_to(project_root)) if (artifacts_dir / "precheck.json").exists() else "",
            "citations_index_csv": str((artifacts_dir / "citations_index.csv").relative_to(project_root)) if (artifacts_dir / "citations_index.csv").exists() else "",
            "tex_lengths_csv": str((artifacts_dir / "tex_lengths.csv").relative_to(project_root)) if (artifacts_dir / "tex_lengths.csv").exists() else "",
            "quote_issues_csv": str((artifacts_dir / "quote_issues.csv").relative_to(project_root)) if (artifacts_dir / "quote_issues.csv").exists() else "",
            "reference_evidence_jsonl": str((artifacts_dir / "reference_evidence.jsonl").relative_to(project_root)) if (artifacts_dir / "reference_evidence.jsonl").exists() else "",
            "reference_evidence_summary_json": str((artifacts_dir / "reference_evidence_summary.json").relative_to(project_root)) if (artifacts_dir / "reference_evidence_summary.json").exists() else "",
            "compile_json": str((artifacts_dir / "compile.json").relative_to(project_root)) if (artifacts_dir / "compile.json").exists() else "",
            "compile_log": str((artifacts_dir / "compile.log").relative_to(project_root)) if (artifacts_dir / "compile.log").exists() else "",
            "parallel_vibe_summary": pv_main_summary,
            "thread_results": thread_results,
        },
        "status": {
            "threads_detected": bool(thread_results),
            "note": "This file is a deterministic aggregation of artifacts; findings are produced by QC threads and/or human review.",
        },
    }

    findings = {
        "schema_version": 1,
        "run_id": run_id,
        "project_root": str(project_root),
        "generated_at": generated_at,
        "findings": [],
    }

    report_path = final_dir / "nsfc-qc_report.md"
    metrics_path = final_dir / "nsfc-qc_metrics.json"
    findings_path = final_dir / "nsfc-qc_findings.json"

    for p in (report_path, metrics_path, findings_path):
        if p.exists() and not bool(args.overwrite):
            print(f"error: output already exists (use --overwrite): {p}", file=sys.stderr)
            return 2

    # Report skeleton: fill template placeholders if present, then append an index section.
    tpl = _load_report_template() or ""
    if tpl:
        try:
            report_body = tpl.format(
                run_id=run_id,
                project_root=str(project_root),
                main_tex=main_tex,
                threads=str(run_meta.get("threads") or ""),
                execution=execution,
            )
        except Exception:
            report_body = tpl
    else:
        report_body = (
            "# NSFC 标书 QC 报告（nsfc-qc）\n\n"
            f"- run_id: `{run_id}`\n"
            f"- project_root: `{project_root}`\n"
            f"- main_tex: `{main_tex}`\n\n"
        )

    idx_lines: List[str] = []
    idx_lines.append("\n## 产物索引（自动生成）\n")
    idx_lines.append(f"- 生成时间：{generated_at}")
    if pv_main_summary:
        idx_lines.append(f"- parallel-vibe 汇总：`{pv_main_summary}`")
    if thread_results:
        idx_lines.append("- thread RESULT.md：")
        for r in thread_results[:50]:
            idx_lines.append(f"  - `{r}`")
        if len(thread_results) > 50:
            idx_lines.append(f"  - ...(and {len(thread_results) - 50} more)")
    else:
        idx_lines.append("- thread RESULT.md：未检测到（可能尚未运行 threads）")
    idx_lines.append("\n> 提示：本报告骨架由脚本生成；P0/P1/P2 内容应由 QC threads 汇总或人工复核后补齐。\n")

    report_path.write_text(report_body.rstrip() + "\n" + "\n".join(idx_lines) + "\n", encoding="utf-8")
    _write_json(metrics_path, metrics)
    _write_json(findings_path, findings)

    print(str(final_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
