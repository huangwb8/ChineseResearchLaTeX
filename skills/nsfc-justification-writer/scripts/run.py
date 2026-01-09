#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.dont_write_bytecode = True

skill_root_for_import = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(skill_root_for_import))

from core.config_loader import load_config, get_runs_dir
from core.hybrid_coordinator import HybridCoordinator
from core.observability import make_run_id


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_body_file(body_file: Optional[str]) -> str:
    if body_file is None or body_file == "-":
        return sys.stdin.read()
    return Path(body_file).read_text(encoding="utf-8", errors="ignore")


def cmd_diagnose(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)

    report = coord.diagnose(project_root=Path(args.project_root), include_tier2=bool(args.tier2))
    text = coord.format_diagnose(report)
    print(text, end="")

    if args.json_out:
        _write_json(Path(args.json_out), report.to_dict())
    return 0


def cmd_wordcount(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    status = coord.word_count_status(project_root=Path(args.project_root))
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def cmd_terms(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    md = coord.term_consistency_report(project_root=Path(args.project_root))
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
    return 0


def cmd_apply_section(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)

    body = _read_body_file(args.body_file).strip()
    if not body:
        print("❌ body 为空：请通过 --body-file 或 stdin 提供新正文", file=sys.stderr)
        return 2

    run_id = args.run_id or make_run_id("apply")
    result = coord.apply_section_body(
        project_root=Path(args.project_root),
        title=args.title,
        new_body=body,
        backup=not bool(args.no_backup),
        run_id=run_id,
    )

    if not result.changed:
        print("未修改：未找到对应小标题，或新内容与原内容一致。")
        return 1

    print(f"✅ 已写入：{result.target_path}")
    if result.backup_path:
        print(f"📦 备份：{result.backup_path}")

    if args.log_json:
        runs_root = get_runs_dir(skill_root, config)
        log_path = (runs_root / run_id / "logs" / "apply_result.json").resolve()
        _write_json(
            log_path,
            {
                "run_id": run_id,
                "target": str(result.target_path),
                "backup": str(result.backup_path) if result.backup_path else None,
            },
        )
        print(f"🧾 记录：{log_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nsfc-justification-writer", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_diag = sub.add_parser("diagnose", help="Tier1/Tier2 诊断（结构/引用/字数/表述）")
    p_diag.add_argument("--project-root", required=True)
    p_diag.add_argument("--tier2", action="store_true", help="启用 AI Tier2（需要 responder 环境）")
    p_diag.add_argument("--json-out", help="可选：输出 JSON 报告到文件")
    p_diag.set_defaults(func=cmd_diagnose)

    p_wc = sub.add_parser("wordcount", help="统计 1.1 立项依据字数并给出偏差")
    p_wc.add_argument("--project-root", required=True)
    p_wc.set_defaults(func=cmd_wordcount)

    p_terms = sub.add_parser("terms", help="术语一致性（硬编码 alias_groups）")
    p_terms.add_argument("--project-root", required=True)
    p_terms.add_argument("--out", help="可选：输出到文件（markdown）")
    p_terms.set_defaults(func=cmd_terms)

    p_apply = sub.add_parser("apply-section", help="替换指定 \\subsubsection 的正文（安全写入+备份）")
    p_apply.add_argument("--project-root", required=True)
    p_apply.add_argument("--title", required=True, help="精确匹配 \\subsubsection{title}")
    p_apply.add_argument("--body-file", help="新正文来源文件；用 - 表示从 stdin 读")
    p_apply.add_argument("--no-backup", action="store_true", help="不做备份（默认备份）")
    p_apply.add_argument("--run-id", help="可选：指定 run_id（默认按时间生成）")
    p_apply.add_argument("--log-json", action="store_true", help="写入 runs/.../logs/apply_result.json")
    p_apply.set_defaults(func=cmd_apply_section)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

