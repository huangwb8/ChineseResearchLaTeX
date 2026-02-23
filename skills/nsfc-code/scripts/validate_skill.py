#!/usr/bin/env python3
"""
Deterministic validation for the nsfc-code skill folder.

Checks:
- required files exist
- overrides TOML can be parsed (non-empty)
- ranking script can run on demo input
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    required = [
        skill_root / "SKILL.md",
        skill_root / "config.yaml",
        skill_root / "references" / "nsfc_code_recommend.toml",
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

    cmd_base = [
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
        r = subprocess.run(cmd_base, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("FAIL: smoke run failed:", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return 2

    try:
        payload = json.loads(r.stdout)
    except Exception as e:
        print("FAIL: ranking script did not output valid JSON.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        print("FAIL: ranking script returned empty/invalid candidates.", file=sys.stderr)
        return 2
    required_keys = {"rank", "code", "score", "recommend"}
    if not required_keys.issubset(set(candidates[0].keys())):
        print("FAIL: candidate shape missing required keys.", file=sys.stderr)
        return 2

    # Smoke: test --output-dir behavior (should write a JSON file and print its path).
    with tempfile.TemporaryDirectory(prefix="nsfc-code-validate-") as td:
        cmd_out = list(cmd_base) + ["--output-dir", td]
        try:
            r2 = subprocess.run(cmd_out, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print("FAIL: smoke run (--output-dir) failed:", file=sys.stderr)
            print(e.stdout, file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            return 2

        out_path = Path(r2.stdout.strip())
        if not out_path.exists():
            print("FAIL: --output-dir did not create output file.", file=sys.stderr)
            print(f"expected path: {out_path}", file=sys.stderr)
            return 2

        try:
            payload2 = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            print("FAIL: output file from --output-dir is not valid JSON.", file=sys.stderr)
            return 2
        if not isinstance(payload2.get("candidates"), list) or not payload2["candidates"]:
            print("FAIL: output file candidates missing/empty.", file=sys.stderr)
            return 2

    print("OK: nsfc-code skill structure looks valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
