#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 make-latex-model 生成公共包修改后的回归验证计划。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
PACKAGES_ROOT = REPO_ROOT / "packages"
PROJECTS_ROOT = REPO_ROOT / "projects"
TESTS_BASELINES_ROOT = REPO_ROOT / "tests" / "baselines"


def load_skill_config() -> dict:
    config_path = SKILL_DIR / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def resolve_package_root(raw_target: str) -> Path:
    raw_target = raw_target.strip()
    direct = Path(raw_target)

    if direct.exists():
        candidate = direct.resolve()
    elif not any(sep in raw_target for sep in ("/", "\\")):
        candidate = (PACKAGES_ROOT / raw_target).resolve()
    else:
        candidate = (REPO_ROOT / raw_target).resolve()

    if not candidate.exists():
        raise FileNotFoundError(f"目标不存在: {raw_target}")

    if candidate.is_file():
        candidate = candidate.parent

    for parent in (candidate, *candidate.parents):
        if parent.parent == PACKAGES_ROOT:
            return parent

    raise ValueError(f"目标不在 {PACKAGES_ROOT} 下，无法识别公共包: {candidate}")


def detect_product_line(project_path: Path, config: dict) -> str:
    rules = config.get("product_line_rules") or {}
    haystacks = [project_path.name.lower()]
    try:
        haystacks.append(str(project_path.relative_to(PROJECTS_ROOT)).lower())
    except Exception:
        pass

    for product_line, rule in rules.items():
        for pattern in rule.get("detect_patterns", []):
            pattern_lc = str(pattern).lower()
            if any(pattern_lc in haystack for haystack in haystacks):
                return product_line
    return "unknown"


def get_official_build_command(project_path: Path, config: dict, product_line: str) -> str:
    rules = config.get("product_line_rules") or {}
    commands = config.get("official_build_commands") or {}
    rule = rules.get(product_line) or {}
    command_key = rule.get("official_build_key", product_line)
    command = commands.get(command_key)
    if not command:
        return ""
    return command.replace("<project>", str(project_path.relative_to(REPO_ROOT)))


def get_official_compare_command(project_path: Path, config: dict, product_line: str, baseline_pdf: Path | None) -> str:
    if baseline_pdf is None:
        return ""

    rules = config.get("product_line_rules") or {}
    commands = config.get("official_compare_commands") or {}
    rule = rules.get(product_line) or {}
    command_key = rule.get("official_compare_key", product_line)
    command = commands.get(command_key)
    if not command:
        return ""
    return (
        command
        .replace("<project>", str(project_path.relative_to(REPO_ROOT)))
        .replace("<baseline>", str(baseline_pdf))
    )


def find_baseline_candidates(project_path: Path, config: dict) -> list[Path]:
    candidates: list[Path] = []
    baseline_cfg = config.get("baseline") or {}

    for relative in baseline_cfg.get("preferred_candidates", []):
        candidate = project_path / relative
        if candidate.exists():
            candidates.append(candidate.resolve())

    for candidate in sorted((project_path / "assets" / "source").glob("*.pdf")):
        if candidate.exists():
            candidates.append(candidate.resolve())

    tests_dir = TESTS_BASELINES_ROOT / project_path.name
    if tests_dir.exists():
        for candidate in sorted(tests_dir.glob("*.pdf")):
            candidates.append(candidate.resolve())

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def iter_guard_projects(project_globs: list[str]) -> list[Path]:
    matches: list[Path] = []
    seen: set[str] = set()
    for pattern in project_globs:
        for candidate in sorted(REPO_ROOT.glob(pattern)):
            if not candidate.is_dir():
                continue
            resolved = candidate.resolve()
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            matches.append(resolved)
    return matches


def build_regression_plan(package_root: Path, config: dict) -> dict:
    policy = config.get("package_change_policy") or {}
    shared_packages = policy.get("shared_packages") or {}
    package_name = package_root.name
    package_guard = shared_packages.get(package_name)

    report = {
        "package_name": package_name,
        "package_root": str(package_root),
        "policy": {
            "require_regression_plan_before_edit": policy.get("require_regression_plan_before_edit", False),
            "project_layer_bias": policy.get("project_layer_bias", False),
            "escalation_rules": policy.get("escalation_rules", []),
            "preferred_isolation_order": policy.get("preferred_isolation_order", []),
            "verification_rules": policy.get("verification_rules", []),
            "forbidden_actions": policy.get("forbidden_actions", []),
        },
        "guard_found": package_guard is not None,
        "prefer_paths": [],
        "rationale": "",
        "projects": [],
    }

    if not package_guard:
        return report

    report["prefer_paths"] = package_guard.get("prefer_paths", [])
    report["rationale"] = package_guard.get("rationale", "")

    for project_path in iter_guard_projects(package_guard.get("project_globs", [])):
        product_line = detect_product_line(project_path, config)
        baseline_candidates = find_baseline_candidates(project_path, config)
        baseline_pdf = baseline_candidates[0] if baseline_candidates else None

        report["projects"].append(
            {
                "project_path": str(project_path.relative_to(REPO_ROOT)),
                "product_line": product_line,
                "build_command": get_official_build_command(project_path, config, product_line),
                "baseline_pdf": str(baseline_pdf) if baseline_pdf else "",
                "compare_command": get_official_compare_command(project_path, config, product_line, baseline_pdf),
                "all_baseline_candidates": [str(path) for path in baseline_candidates],
            }
        )

    return report


def print_report(report: dict) -> None:
    print(f"\n{'=' * 72}")
    print("公共包回归计划")
    print(f"{'=' * 72}")
    print(f"公共包: {report['package_name']}")
    print(f"目录: {report['package_root']}")
    print(f"需要先生成回归计划: {'是' if report['policy'].get('require_regression_plan_before_edit') else '否'}")
    print(f"默认先尝试项目层: {'是' if report['policy'].get('project_layer_bias') else '否'}")

    if report.get("rationale"):
        print(f"原因: {report['rationale']}")

    if report.get("prefer_paths"):
        print("\n优先收敛到这些位置:")
        for path in report["prefer_paths"]:
            print(f"  - {path}")

    if report["policy"].get("preferred_isolation_order"):
        print("\n推荐隔离顺序:")
        for index, rule in enumerate(report["policy"]["preferred_isolation_order"], start=1):
            print(f"  {index}. {rule}")

    if report["policy"].get("verification_rules"):
        print("\n验证要求:")
        for index, rule in enumerate(report["policy"]["verification_rules"], start=1):
            print(f"  {index}. {rule}")

    if report["policy"].get("forbidden_actions"):
        print("\n禁止事项:")
        for index, rule in enumerate(report["policy"]["forbidden_actions"], start=1):
            print(f"  {index}. {rule}")

    if not report.get("guard_found"):
        print("\n⚠️ 未在 config.yaml 中找到该公共包的回归规则，请手动扩大验证范围后再动包层。")
        print(f"{'=' * 72}\n")
        return

    print("\n受影响项目:")
    if not report["projects"]:
        print("  (未匹配到任何项目，请检查 config.yaml 的 project_globs)")
    for index, item in enumerate(report["projects"], start=1):
        print(f"  {index}. {item['project_path']} [{item['product_line']}]")
        if item["build_command"]:
            print(f"     build   : {item['build_command']}")
        if item["compare_command"]:
            print(f"     compare : {item['compare_command']}")
        elif item["baseline_pdf"]:
            print(f"     baseline: {item['baseline_pdf']} (当前产品线无官方 compare 命令或未配置 compare 入口)")
        else:
            print("     baseline: 未发现可直接复用的 baseline，至少执行官方 build")

    print(f"{'=' * 72}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="为公共包修改生成回归验证计划")
    parser.add_argument("target", help="公共包名、公共包目录，或公共包内任意文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    try:
        package_root = resolve_package_root(args.target)
        config = load_skill_config()
        report = build_regression_plan(package_root, config)
    except Exception as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
