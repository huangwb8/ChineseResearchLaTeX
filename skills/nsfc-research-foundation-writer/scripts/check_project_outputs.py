#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _yaml_utils import extract_yaml_value_under_block

RISK_PHRASES = [
    "首次",
    "领先",
    "国际领先",
    "国内领先",
    "唯一",
    "填补空白",
    "世界领先",
    "国内首创",
]


def _err(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def _load_targets(config_yaml: Path) -> tuple[str, str]:
    lines = config_yaml.read_text(encoding="utf-8").splitlines()
    foundation = extract_yaml_value_under_block(lines, "targets", "foundation_tex") or ""
    conditions = extract_yaml_value_under_block(lines, "targets", "conditions_tex") or ""
    if not foundation or not conditions:
        raise ValueError("missing targets.foundation_tex / targets.conditions_tex in config.yaml")
    return foundation, conditions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check nsfc-research-foundation-writer outputs under a LaTeX project root (existence + light heuristics)."
    )
    parser.add_argument("--project-root", required=True, help="LaTeX project root (must contain extraTex/).")
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
    config_yaml = skill_root / "config.yaml"
    if not config_yaml.exists():
        return _err(f"missing config.yaml: {config_yaml}")

    try:
        target_foundation, target_conditions = _load_targets(config_yaml)
    except ValueError as exc:
        return _err(str(exc))

    project_root = Path(args.project_root).expanduser().resolve()
    extra_tex = project_root / "extraTex"
    if not extra_tex.exists() or not extra_tex.is_dir():
        return _err(f"missing extraTex/ under project root: {extra_tex}")

    foundation_path = project_root / target_foundation
    conditions_path = project_root / target_conditions
    for p in [foundation_path, conditions_path]:
        if not p.exists() or not p.is_file():
            return _err(f"missing target file: {p}")

    if args.no_content_check:
        print("OK: target files exist (content checks skipped)", flush=True)
        return 0

    foundation_text = foundation_path.read_text(encoding="utf-8", errors="replace")
    conditions_text = conditions_path.read_text(encoding="utf-8", errors="replace")

    # Foundation must include explicit risk responses; require >=3 risk items.
    if "风险" not in foundation_text:
        return _err(f"{foundation_path} does not contain '风险' (risk section missing?)")
    if not (("应对" in foundation_text) or ("预案" in foundation_text) or ("替代" in foundation_text)):
        _warn(f"{foundation_path} has '风险' but lacks common response keywords (应对/预案/替代); please confirm risk responses are explicit")

    # Try to count "risk items" from common LaTeX heading patterns.
    risk_items: list[str] = []
    risk_items += re.findall(r"\\subsubsubsection\{[^}]*风险[^}]*\}", foundation_text)
    risk_items += re.findall(r"\\subsubsection\{[^}]*风险[^}]*\}", foundation_text)
    risk_items += re.findall(r"(?m)^\\s*#+\\s*.*风险.*$", foundation_text)  # markdown-like headings (rare)
    risk_items += re.findall(r"风险\\s*(?:\\d+|[一二三四五六七八九十])", foundation_text)

    # Deduplicate near-identical hits.
    risk_items = list(dict.fromkeys(risk_items))
    if len(risk_items) < 3:
        return _err(f"{foundation_path} seems to contain < 3 risk items (found {len(risk_items)})")

    # Conditions should reflect "have" and "lack + plan" structure.
    if not (("已具备" in conditions_text) or ("具备" in conditions_text)):
        _warn(f"{conditions_path} does not mention '已具备/具备' explicitly; please confirm it lists existing conditions")
    if not (("尚缺" in conditions_text) or ("缺少" in conditions_text) or ("不足" in conditions_text)):
        _warn(f"{conditions_path} does not mention '尚缺/缺少/不足' explicitly; please confirm it covers missing conditions + plan")

    # Placeholders are allowed in preview / when info is missing; warn for apply-mode outputs.
    if "[请补充：" in foundation_text or "[需补充：" in foundation_text or "[请补充：" in conditions_text or "[需补充：" in conditions_text:
        _warn("found placeholder markers like '[请补充：...]' in outputs; confirm this is intentional and consistent with provided info")

    if not args.no_risk_scan:
        hits: list[tuple[str, str]] = []
        combined = f"{foundation_text}\n{conditions_text}"
        for phrase in RISK_PHRASES:
            if phrase in combined:
                hits.append((phrase, "found"))
        if hits:
            msg = "risk phrases present: " + ", ".join(p for p, _ in hits)
            if args.fail_on_risk_phrases:
                return _err(msg)
            _warn(msg)

    print("OK: output checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
