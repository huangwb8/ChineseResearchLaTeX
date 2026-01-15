#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> int:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run nsfc-research-content-writer minimal checks (validate skill + optional project output checks).",
    )
    parser.add_argument(
        "--project-root",
        default="",
        help="Optional LaTeX project root to check outputs (must contain extraTex/).",
    )
    parser.add_argument(
        "--no-content-check",
        action="store_true",
        help="Only check that target files exist (skip content heuristics).",
    )
    parser.add_argument(
        "--no-risk-scan",
        action="store_true",
        help="Skip scanning for risk phrases like '首次/领先'.",
    )
    parser.add_argument(
        "--fail-on-risk-phrases",
        action="store_true",
        help="Treat risk phrases as errors (default: warnings).",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    validate = skill_root / "scripts" / "validate_skill.py"
    check_outputs = skill_root / "scripts" / "check_project_outputs.py"

    rc = _run([sys.executable, str(validate)])
    if rc != 0:
        return rc

    if args.project_root:
        cmd = [
            sys.executable,
            str(check_outputs),
            "--project-root",
            args.project_root,
        ]
        if args.no_content_check:
            cmd.append("--no-content-check")
        if args.no_risk_scan:
            cmd.append("--no-risk-scan")
        if args.fail_on_risk_phrases:
            cmd.append("--fail-on-risk-phrases")

        rc = _run(cmd)
        if rc != 0:
            return rc

    print("OK: all checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
