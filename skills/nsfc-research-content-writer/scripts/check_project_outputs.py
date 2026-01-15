#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


RISK_PHRASES = [
    "首次",
    "领先",
    "填补空白",
    "突破性",
    "国际领先",
    "世界领先",
]


def _err(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _extract_yaml_value_under_block(lines: list[str], block_key: str, key: str) -> str | None:
    in_block = False
    block_indent = None
    key_re = re.compile(rf"^(\s*){re.escape(key)}:\s*(.*?)\s*$")

    for line in lines:
        if not in_block:
            if re.match(rf"^{re.escape(block_key)}:\s*$", line):
                in_block = True
                block_indent = len(line) - len(line.lstrip(" "))
            continue

        if line.strip() == "":
            continue

        indent = len(line) - len(line.lstrip(" "))
        if block_indent is not None and indent <= block_indent and not line.startswith(" " * (block_indent + 1)):
            break

        m = key_re.match(line)
        if m and indent >= (block_indent or 0) + 2:
            return m.group(2).strip().strip('"').strip("'")
    return None


def _read_targets_from_config(config_yaml: Path) -> dict[str, str]:
    lines = config_yaml.read_text(encoding="utf-8").splitlines()
    research = _extract_yaml_value_under_block(lines, "targets", "research_content_tex")
    innovation = _extract_yaml_value_under_block(lines, "targets", "innovation_tex")
    yearly = _extract_yaml_value_under_block(lines, "targets", "yearly_plan_tex")
    if not research or not innovation or not yearly:
        raise ValueError("config.yaml missing targets.*_tex")
    return {
        "research_content_tex": research,
        "innovation_tex": innovation,
        "yearly_plan_tex": yearly,
    }


def _check_file_exists(project_root: Path, relpath: str) -> str | None:
    path = project_root / relpath
    if not path.exists():
        return f"missing file: {path}"
    if not path.is_file():
        return f"not a file: {path}"
    return None


def _check_minimal_content(path: Path, *, kind: str) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []

    if kind == "research":
        for token in ["S1", "S2", "S3"]:
            if token not in text:
                problems.append(f"{path}: missing subgoal marker {token}")
    elif kind == "innovation":
        if not re.search(r"对应\s*S\d", text):
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
        if not re.search(r"对应\s*S\d", text) and not re.search(r"\bS\d\b", text):
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
            errors.extend(_check_minimal_content(project_root / relpath, kind=kind))

    warnings: list[str] = []
    if not args.no_risk_scan:
        for relpath in [
            targets["research_content_tex"],
            targets["innovation_tex"],
            targets["yearly_plan_tex"],
        ]:
            path = project_root / relpath
            text = path.read_text(encoding="utf-8", errors="replace")
            for phrase in RISK_PHRASES:
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
