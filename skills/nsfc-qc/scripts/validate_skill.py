#!/usr/bin/env python3
"""
Deterministic validation for the nsfc-qc skill folder.

Checks:
- SKILL.md frontmatter version matches config.yaml skill_info.version
- Key scripts/templates exist

Exit code:
- 0: OK
- 2: validation failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional, Tuple


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_skill_md_version(skill_md: Path) -> Optional[str]:
    s = _read_text(skill_md)
    # Frontmatter is between the first two '---' lines.
    if not s.startswith("---"):
        return None
    parts = s.split("\n---", 2)
    if len(parts) < 2:
        return None
    front = parts[0]
    m = re.search(r"^version:\s*([0-9]+(?:\.[0-9]+){1,3})\s*$", front, flags=re.M)
    return m.group(1) if m else None


def _extract_config_version(cfg: Path) -> Optional[str]:
    s = _read_text(cfg)
    # Minimal, dependency-free parse for:
    # skill_info:
    #   version: x.y.z
    m = re.search(r"^\s*version:\s*([0-9]+(?:\.[0-9]+){1,3})\s*$", s, flags=re.M)
    return m.group(1) if m else None


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    skill_md = skill_root / "SKILL.md"
    cfg = skill_root / "config.yaml"

    missing = []
    for p in (skill_md, cfg):
        if not p.exists():
            missing.append(str(p))
    if missing:
        print("FAIL: missing required files:", file=sys.stderr)
        for p in missing:
            print(f"- {p}", file=sys.stderr)
        return 2

    v_skill = _extract_skill_md_version(skill_md)
    v_cfg = _extract_config_version(cfg)
    if not v_skill or not v_cfg:
        print("FAIL: failed to extract versions", file=sys.stderr)
        print(f"- SKILL.md version: {v_skill!r}", file=sys.stderr)
        print(f"- config.yaml version: {v_cfg!r}", file=sys.stderr)
        return 2
    if v_skill != v_cfg:
        print("FAIL: version mismatch (config.yaml is source of truth)", file=sys.stderr)
        print(f"- SKILL.md: {v_skill}", file=sys.stderr)
        print(f"- config.yaml: {v_cfg}", file=sys.stderr)
        return 2

    required_paths = [
        skill_root / "scripts" / "nsfc_qc_precheck.py",
        skill_root / "scripts" / "run_parallel_qc.py",
        skill_root / "scripts" / "nsfc_qc_compile.py",
        skill_root / "scripts" / "materialize_final_outputs.py",
        skill_root / "templates" / "REPORT_TEMPLATE.md",
        skill_root / "templates" / "FINDINGS_SCHEMA.json",
        skill_root / "references" / "qc_checklist.md",
    ]
    missing2 = [str(p.relative_to(skill_root)) for p in required_paths if not p.exists()]
    if missing2:
        print("FAIL: missing expected paths:", file=sys.stderr)
        for p in missing2:
            print(f"- {p}", file=sys.stderr)
        return 2

    print("OK: nsfc-qc skill structure looks valid.")
    print(f"- version: {v_cfg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
