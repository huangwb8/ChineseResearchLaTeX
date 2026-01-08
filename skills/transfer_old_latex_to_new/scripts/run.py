#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

skill_root_for_import = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(skill_root_for_import))

from core.compiler import compile_project
from core.config_loader import get_runs_dir, load_config
from core.ai_integration import AIIntegration
from core.mapping_engine import compute_structure_diff_async
from core.migration_plan import build_plan_from_diff
from core.migrator import apply_plan, restore_snapshot
from core.project_analyzer import analyze_project
from core.run_manager import create_run, get_run
from core.reports import (
    write_change_summary,
    write_restore_guide,
    write_structure_comparison,
    write_unmapped_old_content,
)
from core.security_manager import SecurityManager
from core.snapshot import snapshot_project_editables


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_analyze(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    runs_root = get_runs_dir(skill_root, config)
    run = create_run(runs_root, run_id=args.run_id)

    old_project = Path(args.old).resolve()
    new_project = Path(args.new).resolve()

    snapshot_project_editables(old_project, run.input_snapshot_dir / "old")
    snapshot_project_editables(new_project, run.input_snapshot_dir / "new")

    old_analysis = analyze_project(old_project)
    new_analysis = analyze_project(new_project)

    _write_json(run.analysis_dir / "sections_map_old.json", old_analysis.to_dict())
    _write_json(run.analysis_dir / "sections_map_new.json", new_analysis.to_dict())

    strategy = args.strategy or (config.get("migration", {}) or {}).get("default_strategy", "smart")
    ai_available = bool(args.ai_enabled) and strategy != "fallback"
    ai_integration = AIIntegration(enable_ai=ai_available, config=config)

    import asyncio
    diff = asyncio.run(
        compute_structure_diff_async(old_analysis, new_analysis, config, ai_integration=ai_integration)
    )
    diff_dict = diff.to_dict()
    _write_json(run.analysis_dir / "structure_diff.json", diff_dict)
    write_structure_comparison(run.deliverables_dir, diff_dict)

    plan = build_plan_from_diff(diff_dict, config, strategy=strategy)
    plan_dict = plan.to_dict()
    _write_json(run.plan_dir / "migration_plan.json", plan_dict)
    write_restore_guide(run.deliverables_dir, run.run_id)

    print(f"run_id={run.run_id}")
    print(f"analysis_dir={run.analysis_dir}")
    print(f"plan_file={run.plan_dir / 'migration_plan.json'}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    runs_root = get_runs_dir(skill_root, config)
    run = get_run(runs_root, args.run_id)

    old_project = Path(args.old).resolve()
    new_project = Path(args.new).resolve()

    plan_path = run.plan_dir / "migration_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    security = SecurityManager.for_new_project(new_project, runs_root)
    import asyncio
    result = asyncio.run(
        apply_plan(
            old_project=old_project,
            new_project=new_project,
            plan=plan,
            config=config,
            security=security,
            backup_root=run.backup_dir,
            allow_low_confidence=bool(args.allow_low),
            enable_optimization=bool(args.optimize),
            enable_word_count_adaptation=bool(args.adapt_word_count),
            ai_enabled=bool(args.ai_enabled),
        )
    )
    apply_dict = result.to_dict()
    _write_json(run.logs_dir / "apply_result.json", apply_dict)
    write_change_summary(run.deliverables_dir, apply_dict)

    diff_path = run.analysis_dir / "structure_diff.json"
    if diff_path.exists():
        diff_all = json.loads(diff_path.read_text(encoding="utf-8"))
        write_unmapped_old_content(run.deliverables_dir, old_project, diff_all)

    print(f"run_id={run.run_id}")
    print(f"apply_result={run.logs_dir / 'apply_result.json'}")
    if result.optimization:
        print(f"✅ 内容优化完成：{len(result.optimization)} 个文件")
    if result.adaptation:
        print(f"✅ 字数适配完成：{len(result.adaptation)} 个文件")
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    runs_root = get_runs_dir(skill_root, config)
    run = get_run(runs_root, args.run_id)

    new_project = Path(args.new).resolve()
    summary = compile_project(new_project, run.logs_dir, config)
    _write_json(run.logs_dir / "compile_summary.json", summary.to_dict())

    print(f"run_id={run.run_id}")
    print(f"compile_summary={run.logs_dir / 'compile_summary.json'}")
    return 0 if summary.success else 2


def cmd_restore(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    runs_root = get_runs_dir(skill_root, config)
    run = get_run(runs_root, args.run_id)

    new_project = Path(args.new).resolve()
    security = SecurityManager.for_new_project(new_project, runs_root)
    restored = restore_snapshot(new_project=new_project, backup_root=run.backup_dir, security=security)
    _write_json(run.logs_dir / "restore_result.json", {"restored": restored})
    print(f"run_id={run.run_id}")
    print(f"restored_count={len(restored)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="transfer-old-latex-to-new",
        description="NSFC LaTeX 标书迁移（可执行 MVP：analyze/apply/compile/restore）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="解析旧新项目结构并生成迁移计划（不写入 new）")
    p_analyze.add_argument("--old", required=True, help="旧项目根目录")
    p_analyze.add_argument("--new", required=True, help="新项目根目录")
    p_analyze.add_argument("--run-id", default=None, help="可选：指定 run_id（用于复现）")
    p_analyze.add_argument(
        "--strategy",
        default=None,
        choices=["smart", "conservative", "aggressive", "fallback"],
        help="smart/conservative/aggressive/fallback",
    )
    p_analyze.add_argument("--no-ai", dest="ai_enabled", action="store_false", default=True, help="禁用 AI 功能")
    p_analyze.set_defaults(func=cmd_analyze)

    p_apply = sub.add_parser("apply", help="按迁移计划写入 new_project/extraTex（默认跳过低置信度）")
    p_apply.add_argument("--run-id", required=True, help="run_id（来自 analyze 输出）")
    p_apply.add_argument("--old", required=True, help="旧项目根目录")
    p_apply.add_argument("--new", required=True, help="新项目根目录")
    p_apply.add_argument("--allow-low", action="store_true", help="允许执行低置信度任务（谨慎）")
    p_apply.add_argument("--optimize", action="store_true", help="启用内容优化（迁移后自动优化）")
    p_apply.add_argument("--adapt-word-count", action="store_true", help="启用字数适配（自动调整到目标字数）")
    p_apply.add_argument("--no-ai", dest="ai_enabled", action="store_false", default=True, help="禁用 AI 功能")
    p_apply.set_defaults(func=cmd_apply)

    p_compile = sub.add_parser("compile", help="对新项目执行 4 步编译并输出日志摘要")
    p_compile.add_argument("--run-id", required=True, help="run_id")
    p_compile.add_argument("--new", required=True, help="新项目根目录")
    p_compile.set_defaults(func=cmd_compile)

    p_restore = sub.add_parser("restore", help="将 new 项目恢复到 apply 前快照")
    p_restore.add_argument("--run-id", required=True, help="run_id")
    p_restore.add_argument("--new", required=True, help="新项目根目录")
    p_restore.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
