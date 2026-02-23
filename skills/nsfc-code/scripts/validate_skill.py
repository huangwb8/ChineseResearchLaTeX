#!/usr/bin/env python3
"""
Deterministic validation for the nsfc-code skill folder.

Checks:
- required files exist
- overrides TOML can be parsed (non-empty)
- ranking script can run on demo input
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    required = [
        skill_root / "SKILL.md",
        skill_root / "config.yaml",
        skill_root / "references" / "nsfc_2026_recommend_overrides.toml",
        skill_root / "scripts" / "nsfc_code_rank.py",
        skill_root / "scripts" / "nsfc_code_new_report.py",
    ]
    missing = [str(p.relative_to(skill_root)) for p in required if not p.exists()]
    if missing:
        print("FAIL: missing required files:", file=sys.stderr)
        for p in missing:
            print(f"- {p}", file=sys.stderr)
        return 2

    # Smoke: ranking script should work on demo.
    demo_dir = skill_root / "references" / "demo"
    demo_tex = demo_dir / "proposal_excerpt.tex"
    if not demo_tex.exists():
        print("WARN: demo input missing, skip smoke run.", file=sys.stderr)
        return 0

    cmd = [
        sys.executable,
        str(skill_root / "scripts" / "nsfc_code_rank.py"),
        "--input",
        str(demo_dir),
        "--top-k",
        "5",
        "--prefix",
        "A",
        "--format",
        "json",
    ]
    try:
        r = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("FAIL: smoke run failed:", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return 2

    if '"candidates"' not in r.stdout:
        print("FAIL: unexpected output from ranking script", file=sys.stderr)
        return 2

    print("OK: nsfc-code skill structure looks valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
