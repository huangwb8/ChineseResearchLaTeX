#!/usr/bin/env python3
"""AI 提交正文提案；Python 仅检查文件边界与安全写入。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if sys.version_info < (3, 11):
    raise SystemExit("需要 Python 3.11+")

from revision import (ROLES, RevisionError, apply_entries, bibliography, content_report,
                      load_config, make_diff, prepare, project_path, read_backup,
                      restore, target_path, task_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    revise = sub.add_parser("revise", help="检查提案；preview 只读，apply 写入")
    revise.add_argument("--project-root", required=True)
    revise.add_argument("--task-root", required=True)
    revise.add_argument("--proposal-manifest", required=True, type=Path)
    revise.add_argument("--role", action="append", required=True, choices=ROLES)
    revise.add_argument("--output-mode", choices=("preview", "apply"))
    revise.add_argument("--allow-structure-change", action="store_true",
                        help="仅在作者明确授权改标题/层级/结构时使用")
    check = sub.add_parser("check", help="只读文件、引用和字数检查；不证明科学质量")
    check.add_argument("--project-root", required=True)
    check.add_argument("--role", action="append", choices=ROLES)
    check.add_argument("--no-content-check", action="store_true")
    check.add_argument("--no-risk-scan", action="store_true")
    check.add_argument("--fail-on-risk-phrases", action="store_true")
    for name in ("diff", "restore"):
        command = sub.add_parser(name)
        command.add_argument("--project-root", required=True)
        command.add_argument("--task-root", required=True)
        command.add_argument("--backup-dir", required=True)
    args = parser.parse_args(argv)
    try:
        config, root = load_config(), project_path(args.project_root)
        if args.command == "check":
            known, reports = bibliography(root, config), {}
            for role in args.role or ROLES:
                path = target_path(root, role, config)
                reports[role] = content_report(path.read_text(encoding="utf-8"), known, config,
                    content=not args.no_content_check, risk=not args.no_risk_scan,
                    fail_risk=args.fail_on_risk_phrases)
            if "subgoal_markers_min" in config.get("checks", {}):
                print("WARN: checks.subgoal_markers_min 已停用，不再要求正文 S 编号。", file=sys.stderr)
            print(json.dumps(reports, ensure_ascii=False, indent=2))
            return 2 if any(r["errors"] for r in reports.values()) else 0
        task = task_path(args.task_root)
        if args.command == "revise":
            entries, reports = prepare(root, task, args.proposal_manifest, args.role, config,
                                       allow_structure=args.allow_structure_change)
            for e in entries:
                print(make_diff(e["relative"], e["before"], e["after"]), end="")
            mode = args.output_mode or config["parameters"]["output_mode"]["default"]
            result = apply_entries(root, task, entries) if mode == "apply" else {"status": "preview"}
            print(json.dumps({**result, "checks": reports}, ensure_ascii=False, indent=2))
        elif args.command == "diff":
            _, _, entries = read_backup(root, task, args.backup_dir, config)
            for e in entries:
                print(make_diff(e["relative"], e["before"], e["after"]), end="")
        else:
            print(json.dumps(restore(root, task, args.backup_dir, config), ensure_ascii=False, indent=2))
        return 0
    except (RevisionError, OSError, ValueError, KeyError, TypeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
