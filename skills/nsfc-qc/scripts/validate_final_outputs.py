#!/usr/bin/env python3
"""
Validate final outputs consistency for nsfc-qc.

Checks:
- final/nsfc-qc_report.md contains required headings
- final/nsfc-qc_report.md contains table rows for every finding id in final/nsfc-qc_findings.json

Exit code:
- 0: OK
- 2: FAIL
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple


REQUIRED_HEADINGS = [
    "执行摘要",
    "范围与只读声明",
    "硬性问题（P0）",
    "重要建议（P1）",
    "可选优化（P2）",
    "引用核查清单",
    "篇幅与结构分布",
    "建议的最小修改路线图",
    "附录：复现信息（命令/路径/产物索引）",
]


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _read_json(p: Path) -> dict:
    try:
        return json.loads(_read_text(p))
    except Exception:
        return {}


def _validate(report_text: str, findings_obj: dict) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for h in REQUIRED_HEADINGS:
        if f"## {h}" not in report_text:
            errors.append(f"missing_heading:{h}")
    findings = findings_obj.get("findings") or []
    for f in findings:
        fid = str(f.get("id") or "").strip()
        if not fid:
            errors.append("finding_missing_id")
            continue
        if f"| {fid} |" not in report_text:
            errors.append(f"missing_finding_in_report:{fid}")
    return (len(errors) == 0), errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="run directory (contains final/)")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    report = run_dir / "final" / "nsfc-qc_report.md"
    findings = run_dir / "final" / "nsfc-qc_findings.json"
    if not report.exists() or not findings.exists():
        print("FAIL: missing final outputs", file=sys.stderr)
        print(f"- report: {report} (exists={report.exists()})", file=sys.stderr)
        print(f"- findings: {findings} (exists={findings.exists()})", file=sys.stderr)
        return 2

    ok, errors = _validate(_read_text(report), _read_json(findings))
    if ok:
        print("OK: final outputs are consistent.")
        return 0

    print("FAIL: final outputs validation failed:", file=sys.stderr)
    for e in errors:
        print(f"- {e}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

