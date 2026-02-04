#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _yaml_utils import extract_yaml_list_under_block, extract_yaml_value_under_block

DEFAULT_RISK_PHRASES = ["首次", "领先", "填补空白", "突破性", "国际领先", "世界领先"]
DEFAULT_SUBGOAL_MARKERS_MIN = 3


def _err(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _read_targets_from_config(config_yaml: Path) -> dict[str, str]:
    lines = config_yaml.read_text(encoding="utf-8").splitlines()
    research = extract_yaml_value_under_block(lines, "targets", "research_content_tex")
    innovation = extract_yaml_value_under_block(lines, "targets", "innovation_tex")
    yearly = extract_yaml_value_under_block(lines, "targets", "yearly_plan_tex")
    if not research or not innovation or not yearly:
        raise ValueError("config.yaml missing targets.*_tex")
    return {
        "research_content_tex": research,
        "innovation_tex": innovation,
        "yearly_plan_tex": yearly,
    }


def _read_checks_from_config(config_yaml: Path) -> tuple[list[str], int]:
    lines = config_yaml.read_text(encoding="utf-8").splitlines()

    risk_phrases = extract_yaml_list_under_block(lines, "checks", "risk_phrases") or DEFAULT_RISK_PHRASES
    raw_min = extract_yaml_value_under_block(lines, "checks", "subgoal_markers_min")
    try:
        subgoal_markers_min = int(raw_min) if raw_min is not None else DEFAULT_SUBGOAL_MARKERS_MIN
    except ValueError:
        subgoal_markers_min = DEFAULT_SUBGOAL_MARKERS_MIN

    subgoal_markers_min = max(1, subgoal_markers_min)
    return risk_phrases, subgoal_markers_min


def _check_file_exists(project_root: Path, relpath: str) -> str | None:
    path = project_root / relpath
    if not path.exists():
        return f"missing file: {path}"
    if not path.is_file():
        return f"not a file: {path}"
    return None


def _check_minimal_content(path: Path, *, kind: str, subgoal_markers_min: int) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []

    if kind == "research":
        markers = {int(m.group(1)) for m in re.finditer(r"\bS(\d+)\b", text)}
        if len(markers) < subgoal_markers_min:
            problems.append(
                f"{path}: not enough subgoal markers like S1/S2/... (found={len(markers)} min={subgoal_markers_min})"
            )
    elif kind == "innovation":
        if not re.search(r"对应\s*S\d+", text):
            problems.append(f"{path}: missing backreference marker like '对应 S1'")
    elif kind == "yearly":
        year_patterns = {
            "第1年/第一年": [r"第\s*1\s*年", r"第一年"],
            "第2年/第二年": [r"第\s*2\s*年", r"第二年"],
            "第3年/第三年": [r"第\s*3\s*年", r"第三年"],
        }
        for label, patterns in year_patterns.items():
            if not any(re.search(p, text) for p in patterns):
                problems.append(f"{path}: missing yearly header ({label})")
        if not re.search(r"对应\s*S\d+", text) and not re.search(r"\bS\d+\b", text):
            problems.append(f"{path}: missing subgoal backreference like '对应 S1'")
    else:
        problems.append(f"{path}: unknown kind {kind}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lightweight checker for nsfc-research-content-writer outputs under a given project_root.",
    )
    parser.add_argument(
        "--project-root",
        required=True,
        help="NSFC LaTeX project root (must contain extraTex/).",
    )
    parser.add_argument(
        "--no-content-check",
        action="store_true",
        help="Only check that target files exist (skip content heuristics).",
    )
    parser.add_argument(
        "--no-risk-scan",
        action="store_true",
        help="Skip scanning for risk phrases like '首次/领先' (default: scan and warn).",
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

    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        return _err(f"project_root does not exist or is not a directory: {project_root}")
    if not (project_root / "extraTex").exists():
        return _err(f"project_root missing extraTex/: {project_root}")

    try:
        targets = _read_targets_from_config(config_yaml)
    except ValueError as exc:
        return _err(str(exc))

    risk_phrases, subgoal_markers_min = _read_checks_from_config(config_yaml)

    errors: list[str] = []
    errors.extend(
        e
        for e in [
            _check_file_exists(project_root, targets["research_content_tex"]),
            _check_file_exists(project_root, targets["innovation_tex"]),
            _check_file_exists(project_root, targets["yearly_plan_tex"]),
        ]
        if e
    )
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not args.no_content_check:
        checks = [
            (targets["research_content_tex"], "research"),
            (targets["innovation_tex"], "innovation"),
            (targets["yearly_plan_tex"], "yearly"),
        ]
        for relpath, kind in checks:
            errors.extend(
                _check_minimal_content(project_root / relpath, kind=kind, subgoal_markers_min=subgoal_markers_min)
            )

    warnings: list[str] = []
    if not args.no_risk_scan:
        for relpath in [
            targets["research_content_tex"],
            targets["innovation_tex"],
            targets["yearly_plan_tex"],
        ]:
            path = project_root / relpath
            text = path.read_text(encoding="utf-8", errors="replace")
            for phrase in risk_phrases:
                if phrase in text:
                    msg = f"{path}: contains risk phrase '{phrase}'"
                    if args.fail_on_risk_phrases:
                        errors.append(msg)
                    else:
                        warnings.append(msg)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    print("OK: project outputs check passed")
    print(f"- project_root: {project_root}")
    print("- targets:")
    print(f"  - {targets['research_content_tex']}")
    print(f"  - {targets['innovation_tex']}")
    print(f"  - {targets['yearly_plan_tex']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
