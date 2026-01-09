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
from core.bib_manager_integration import BibFixSuggestion
from core.errors import MissingCitationKeysError, BackupNotFoundError
from core.html_report import render_diagnostic_html
from core.hybrid_coordinator import HybridCoordinator
from core.info_form import copy_info_form_template, interactive_collect_info_form, write_info_form_file
from core.observability import make_run_id
from core.versioning import find_backup_for_run, list_runs, rollback_from_backup, unified_diff


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

    if args.html_report:
        run_id = args.run_id or make_run_id("diagnose")
        runs_root = get_runs_dir(skill_root, config)
        out_path = Path(args.html_report)
        if str(args.html_report).strip().lower() == "auto":
            out_path = (runs_root / run_id / "reports" / "diagnose.html").resolve()

        target_relpath = str((config.get("targets", {}) or {}).get("justification_tex", "extraTex/1.1.立项依据.tex"))
        target = coord.target_path(project_root=Path(args.project_root))
        tex = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
        include_terms = not bool(getattr(args, "no_terms", False))
        term_md = coord.term_consistency_report(project_root=Path(args.project_root)) if include_terms else ""
        html_text = render_diagnostic_html(
            skill_root=skill_root,
            project_root=Path(args.project_root),
            target_relpath=target_relpath,
            tex_text=tex,
            report=report,
            term_matrix_md=term_md,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_text, encoding="utf-8")
        print(f"🧩 HTML 报告：{out_path}")
    return 0


def cmd_wordcount(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    status = coord.word_count_status(project_root=Path(args.project_root))
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def cmd_refs(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)

    report = coord.diagnose(project_root=Path(args.project_root), include_tier2=False)
    sug = BibFixSuggestion(
        missing_bibkeys=list(report.tier1.missing_citation_keys or []),
        missing_doi_keys=list(getattr(report.tier1, "missing_doi_keys", []) or []),
    )
    md = sug.to_markdown(project_root=str(Path(args.project_root)))
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
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
    try:
        result = coord.apply_section_body(
            project_root=Path(args.project_root),
            title=args.title,
            new_body=body,
            backup=not bool(args.no_backup),
            run_id=run_id,
            allow_missing_citations=bool(args.allow_missing_citations),
        )
    except MissingCitationKeysError as e:
        print("❌ 检测到缺失引用 bibkey（为避免幻觉引用，已拒绝写入）：", file=sys.stderr)
        for k in e.missing_keys[:20]:
            print(f"- {k}", file=sys.stderr)
        print("建议：先补齐 .bib（或使用 nsfc-bib-manager 核验 DOI/条目）后再写入。", file=sys.stderr)
        print("如你确实要忽略该检查，可加 --allow-missing-citations。", file=sys.stderr)
        return 2

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


def cmd_init(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    version = str((config.get("skill_info", {}) or {}).get("version", ""))
    runs_root = get_runs_dir(skill_root, config)
    run_id = args.run_id or make_run_id("init")

    out_path = Path(args.out) if args.out else (runs_root / run_id / "inputs" / "info_form.md")
    out_path = out_path.resolve()

    template_path = (skill_root / "references" / "info_form.md").resolve()
    if not args.interactive:
        ok = copy_info_form_template(template_path=template_path, out_path=out_path)
        if not ok:
            print("❌ 未找到 info_form 模板。", file=sys.stderr)
            return 2
        print(f"✅ 已生成信息表模板：{out_path}")
        return 0

    print("进入交互式信息表收集（仅本地生成，不会修改标书项目目录）。")
    answers = interactive_collect_info_form()
    write_info_form_file(out_path=out_path, answers=answers, version=version or "v0.0.0")
    print(f"✅ 已生成信息表：{out_path}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    md = coord.reviewer_advice(project_root=Path(args.project_root), include_tier2=bool(args.tier2))
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
    return 0


def cmd_coach(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    info_form_text = ""
    if args.info_form:
        info_form_text = Path(args.info_form).read_text(encoding="utf-8", errors="ignore")
    md = coord.coach(project_root=Path(args.project_root), stage=str(args.stage), info_form_text=info_form_text)
    if args.topic:
        md = coord.recommend_examples(query=str(args.topic), top_k=int(args.top_k)) + "\n" + md
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
    return 0


def cmd_examples(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    print(coord.recommend_examples(query=str(args.query), top_k=int(args.top_k)), end="")
    return 0


def cmd_list_runs(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    runs_root = get_runs_dir(skill_root, config)
    runs = list_runs(runs_root=runs_root)
    if not runs:
        print("（暂无 runs 记录）")
        return 0
    for r in runs[: int(args.limit)]:
        print(r.run_id)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    runs_root = get_runs_dir(skill_root, config)
    target = coord.target_path(project_root=Path(args.project_root))
    try:
        backup = find_backup_for_run(runs_root=runs_root, run_id=str(args.run_id), filename=target.name)
    except BackupNotFoundError:
        print(f"❌ 未找到 run_id={args.run_id} 的备份文件。", file=sys.stderr)
        return 2
    old = backup.read_text(encoding="utf-8", errors="ignore")
    new = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
    diff_text = unified_diff(
        old_text=old,
        new_text=new,
        fromfile=str(backup),
        tofile=str(target),
        context_lines=int(args.context),
    )
    print(diff_text, end="")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    if not args.yes:
        print("❌ 回滚需要显式确认：请加 --yes", file=sys.stderr)
        return 2
    skill_root = Path(__file__).resolve().parent.parent
    config = load_config(skill_root)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    runs_root = get_runs_dir(skill_root, config)
    target = coord.target_path(project_root=Path(args.project_root))
    try:
        used = rollback_from_backup(
            runs_root=runs_root,
            run_id=str(args.run_id),
            target_path=target,
            backup_current=not bool(args.no_backup),
            rollback_run_id=args.new_run_id,
        )
    except BackupNotFoundError:
        print(f"❌ 未找到 run_id={args.run_id} 的备份文件。", file=sys.stderr)
        return 2
    print(f"✅ 已回滚：{target}")
    print(f"📦 使用备份：{used}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nsfc-justification-writer", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_diag = sub.add_parser("diagnose", help="Tier1/Tier2 诊断（结构/引用/字数/表述）")
    p_diag.add_argument("--project-root", required=True)
    p_diag.add_argument("--tier2", action="store_true", help="启用 AI Tier2（需要 responder 环境）")
    p_diag.add_argument("--json-out", help="可选：输出 JSON 报告到文件")
    p_diag.add_argument("--html-report", help="可选：输出 HTML 报告到文件；用 auto 输出到 runs/...")
    p_diag.add_argument("--no-terms", action="store_true", help="HTML 报告不附带术语一致性矩阵")
    p_diag.add_argument("--run-id", help="可选：diagnose 的 run_id（用于 html-report=auto）")
    p_diag.set_defaults(func=cmd_diagnose)

    p_wc = sub.add_parser("wordcount", help="统计 1.1 立项依据字数并给出偏差")
    p_wc.add_argument("--project-root", required=True)
    p_wc.set_defaults(func=cmd_wordcount)

    p_refs = sub.add_parser("refs", help="引用核验摘要 + 生成 nsfc-bib-manager 可复制提示词")
    p_refs.add_argument("--project-root", required=True)
    p_refs.add_argument("--out", help="可选：输出到文件（markdown）")
    p_refs.set_defaults(func=cmd_refs)

    p_terms = sub.add_parser("terms", help="术语一致性（硬编码 alias_groups）")
    p_terms.add_argument("--project-root", required=True)
    p_terms.add_argument("--out", help="可选：输出到文件（markdown）")
    p_terms.set_defaults(func=cmd_terms)

    p_init = sub.add_parser("init", help="生成（或交互式填写）信息表 info_form.md")
    p_init.add_argument("--interactive", action="store_true", help="问答式收集并生成已填写的信息表")
    p_init.add_argument("--out", help="输出路径（默认写到 runs/<run_id>/inputs/info_form.md）")
    p_init.add_argument("--run-id", help="可选：指定 run_id（默认按时间生成）")
    p_init.set_defaults(func=cmd_init)

    p_review = sub.add_parser("review", help="评审人视角质疑与建议（可选 Tier2）")
    p_review.add_argument("--project-root", required=True)
    p_review.add_argument("--tier2", action="store_true", help="启用 AI Tier2（需要 responder 环境）")
    p_review.add_argument("--out", help="可选：输出到文件（markdown）")
    p_review.set_defaults(func=cmd_review)

    p_coach = sub.add_parser("coach", help="渐进式写作引导（骨架→段落→修订→润色→验收）")
    p_coach.add_argument("--project-root", required=True)
    p_coach.add_argument("--stage", default="auto", choices=["auto", "skeleton", "draft", "revise", "polish", "final"])
    p_coach.add_argument("--info-form", help="可选：已填写的信息表文件（markdown）")
    p_coach.add_argument("--topic", help="可选：一句话主题，用于推荐 examples/ 示例")
    p_coach.add_argument("--top-k", default=3, type=int)
    p_coach.add_argument("--out", help="可选：输出到文件（markdown）")
    p_coach.set_defaults(func=cmd_coach)

    p_ex = sub.add_parser("examples", help="根据主题推荐 examples/ 中的参考骨架")
    p_ex.add_argument("--query", required=True, help="主题/方向/关键词")
    p_ex.add_argument("--top-k", default=3, type=int)
    p_ex.set_defaults(func=cmd_examples)

    p_runs = sub.add_parser("list-runs", help="列出 runs/ 下的 run_id（用于 diff/rollback）")
    p_runs.add_argument("--limit", default=20, type=int)
    p_runs.set_defaults(func=cmd_list_runs)

    p_diff = sub.add_parser("diff", help="查看某次 run 的备份与当前文件的 diff")
    p_diff.add_argument("--project-root", required=True)
    p_diff.add_argument("--run-id", required=True)
    p_diff.add_argument("--context", default=3, type=int)
    p_diff.set_defaults(func=cmd_diff)

    p_rb = sub.add_parser("rollback", help="从某次 run 的备份回滚当前文件（默认会备份当前版本）")
    p_rb.add_argument("--project-root", required=True)
    p_rb.add_argument("--run-id", required=True)
    p_rb.add_argument("--yes", action="store_true", help="确认回滚（必须显式指定）")
    p_rb.add_argument("--no-backup", action="store_true", help="不备份当前版本（默认备份到新的 runs/）")
    p_rb.add_argument("--new-run-id", help="可选：回滚备份的 run_id（默认按时间生成）")
    p_rb.set_defaults(func=cmd_rollback)

    p_apply = sub.add_parser("apply-section", help="替换指定 \\subsubsection 的正文（安全写入+备份）")
    p_apply.add_argument("--project-root", required=True)
    p_apply.add_argument("--title", required=True, help="精确匹配 \\subsubsection{title}")
    p_apply.add_argument("--body-file", help="新正文来源文件；用 - 表示从 stdin 读")
    p_apply.add_argument("--no-backup", action="store_true", help="不做备份（默认备份）")
    p_apply.add_argument("--run-id", help="可选：指定 run_id（默认按时间生成）")
    p_apply.add_argument("--log-json", action="store_true", help="写入 runs/.../logs/apply_result.json")
    p_apply.add_argument("--allow-missing-citations", action="store_true", help="允许存在缺失 bibkey 的 \\cite{...}（不推荐）")
    p_apply.set_defaults(func=cmd_apply_section)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
