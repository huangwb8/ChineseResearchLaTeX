#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional

sys.dont_write_bytecode = True

skill_root_for_import = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(skill_root_for_import))

from core.config_loader import load_config, get_runs_dir, validate_config
from core.config_access import get_bool, get_mapping, get_seq_str, get_str
from core.bib_manager_integration import BibFixSuggestion
from core.errors import BackupNotFoundError, MissingCitationKeysError, SectionNotFoundError, SkillError
from core.html_report import render_diagnostic_html
from core.hybrid_coordinator import HybridCoordinator
from core.info_form import copy_info_form_template, interactive_collect_info_form, write_info_form_file
from core.latex_parser import parse_subsubsections
from core.logging_utils import configure_logging
from core.observability import make_run_id
from core.quality_gate import check_new_body_quality
from core.versioning import find_backup_for_run, list_runs, rollback_from_backup, unified_diff

logger = logging.getLogger(__name__)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_body_file(body_file: Optional[str]) -> str:
    if body_file is None or body_file == "-":
        return sys.stdin.read()
    return Path(body_file).read_text(encoding="utf-8", errors="ignore")


def _load_config_for_args(skill_root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    preset = getattr(args, "preset", None)
    override = getattr(args, "override", None)
    no_user_override = bool(getattr(args, "no_user_override", False))
    cfg = load_config(
        skill_root,
        preset=str(preset) if preset else None,
        override_path=str(override) if override else None,
        load_user_override=(not no_user_override),
    )
    meta = get_mapping(cfg, "_config_loader")
    warnings = list(meta.get("warnings", []) or [])
    for w in warnings[:10]:
        logger.warning("⚠️ 配置加载警告：%s", w)
    if len(warnings) > 10:
        logger.warning("⚠️ 配置加载警告：更多 %s 条已省略", str(len(warnings) - 10))
    return cfg


def cmd_diagnose(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)

    if args.tier2 and getattr(args, "verbose", False):
        logger.info("⏳ 正在运行诊断（含 Tier2）...")
    report = coord.diagnose(
        project_root=Path(args.project_root),
        include_tier2=bool(args.tier2),
        tier2_chunk_size=int(args.chunk_size) if args.chunk_size is not None else None,
        tier2_max_chunks=int(args.max_chunks) if args.max_chunks is not None else None,
        tier2_fresh=bool(getattr(args, "fresh", False)),
    )
    text = coord.format_diagnose(report)
    print(text, end="")

    if args.json_out:
        _write_json(Path(args.json_out), report.to_dict())

    if args.html_report:
        if getattr(args, "verbose", False):
            logger.info("⏳ 正在生成 HTML 报告...")
        run_id = args.run_id or make_run_id("diagnose")
        runs_root = get_runs_dir(skill_root, config)
        out_path = Path(args.html_report)
        if str(args.html_report).strip().lower() == "auto":
            out_path = (runs_root / run_id / "reports" / "diagnose.html").resolve()

        targets = get_mapping(config, "targets")
        target_relpath = get_str(targets, "justification_tex", "extraTex/1.1.立项依据.tex")
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
        if bool(getattr(args, "open", False)):
            try:
                webbrowser.open(out_path.resolve().as_uri())
            except (OSError, ValueError, webbrowser.Error) as e:
                if bool(getattr(args, "verbose", False)):
                    logger.warning("⚠️ 打开浏览器失败：%s: %s", type(e).__name__, str(e))
    return 0


def cmd_wordcount(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    status = coord.word_count_status(project_root=Path(args.project_root), mode=getattr(args, "mode", None))
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def cmd_refs(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)

    report = coord.diagnose(project_root=Path(args.project_root), include_tier2=False)
    sug = BibFixSuggestion(
        missing_bibkeys=list(report.tier1.missing_citation_keys or []),
        missing_doi_keys=list(getattr(report.tier1, "missing_doi_keys", []) or []),
        invalid_doi_keys=list(getattr(report.tier1, "invalid_doi_keys", []) or []),
    )
    md = sug.to_markdown(project_root=str(Path(args.project_root)))
    if str(getattr(args, "verify_doi", "none")).strip().lower() == "crossref":
        from core.reference_validator import load_project_bib_doi_map, parse_cite_keys, verify_doi_via_crossref

        target = coord.target_path(project_root=Path(args.project_root))
        tex = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
        cite_keys = parse_cite_keys(tex)
        targets = get_mapping(config, "targets")
        bib_globs = list(get_seq_str(targets, "bib_globs")) or ["references/*.bib"]
        doi_map = load_project_bib_doi_map(Path(args.project_root), bib_globs)
        pairs = [(k, doi_map.get(k, "")) for k in cite_keys if doi_map.get(k)]

        failed = []
        timeout_s = float(getattr(args, "doi_timeout", 5.0))
        for k, doi in pairs[:200]:
            ok = verify_doi_via_crossref(doi=doi, timeout_s=timeout_s)
            if not ok:
                failed.append(f"- {k}: {doi}")
        if failed:
            md = md.rstrip() + "\n\n## Crossref（可选联网）校验失败/超时的 DOI（需人工核验）\n\n" + "\n".join(failed) + "\n"
        else:
            md = md.rstrip() + "\n\n## Crossref（可选联网）校验\n\n- ✅ 未发现明显失败（仍建议抽查关键引用）\n"
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
    return 0


def cmd_terms(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    md = coord.term_consistency_report(project_root=Path(args.project_root))
    targets = get_mapping(config, "targets")
    related = get_mapping(targets, "related_tex")
    if related:
        md = (
            md.rstrip()
            + "\n\n## 建议同步到以下章节\n\n"
            + "\n".join([f"- {k}: `{v}`" for k, v in related.items()])
            + "\n"
        )
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
    return 0


def cmd_validate_config(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    errs = validate_config(skill_root=skill_root, config=config)
    if errs:
        logger.error("❌ 配置校验失败：")
        for e in errs:
            logger.error("- %s", e)
        return 2
    print("✅ 配置有效")
    return 0


def cmd_apply_section(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)

    body = _read_body_file(args.body_file).strip()
    if not body:
        logger.error("❌ body 为空：请通过 --body-file 或 stdin 提供新正文")
        return 2

    run_id = args.run_id or make_run_id("apply")
    # 若用户选择放宽引用约束，建议至少启用“新正文质量闸门”（可选阻断）。
    if bool(getattr(args, "allow_missing_citations", False)) and (not bool(getattr(args, "strict_quality", False))):
        strict_cfg = get_bool(get_mapping(config, "quality"), "strict_on_apply", False)
        if not strict_cfg:
            qr = check_new_body_quality(new_body=body, config=config)
            if not qr.ok:
                if qr.forbidden_phrases_hits:
                    logger.warning(
                        "⚠️ 新正文包含不可核验表述（建议改写或启用 --strict-quality 阻断写入）：%s",
                        "、".join(qr.forbidden_phrases_hits[:10]),
                    )
                if qr.avoid_commands_hits:
                    logger.warning(
                        "⚠️ 新正文包含可能破坏模板的命令（建议移除或启用 --strict-quality 阻断写入）：%s",
                        "、".join(qr.avoid_commands_hits[:10]),
                    )
    try:
        result = coord.apply_section_body(
            project_root=Path(args.project_root),
            title=args.title,
            new_body=body,
            backup=not bool(args.no_backup),
            run_id=run_id,
            allow_missing_citations=bool(args.allow_missing_citations),
            strict_quality=bool(getattr(args, "strict_quality", False)),
        )
    except MissingCitationKeysError as e:
        logger.error("❌ %s", str(e))
        if e.missing_keys:
            logger.error("\n缺失的 bibkey：")
            for k in e.missing_keys[:50]:
                logger.error("- %s", k)
        if getattr(e, "fix_suggestion", ""):
            logger.error("\n💡 修复建议：")
            logger.error("%s", getattr(e, "fix_suggestion", ""))
        return 2
    except SectionNotFoundError as e:
        logger.error("❌ %s", str(e))
        if getattr(e, "fix_suggestion", ""):
            logger.error("\n💡 修复建议：")
            logger.error("%s", getattr(e, "fix_suggestion", ""))
        if bool(getattr(args, "suggest_alias", False)):
            target = coord.target_path(project_root=Path(args.project_root))
            if target.exists():
                tex = target.read_text(encoding="utf-8", errors="ignore")
                titles = [s.title for s in parse_subsubsections(tex)]
                if titles:
                    logger.error("\n可用的小标题（全部）：")
                    for t in titles[:80]:
                        logger.error("- %s", t)
        return 2

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
    config = _load_config_for_args(skill_root, args)
    version = get_str(get_mapping(config, "skill_info"), "version", "")
    runs_root = get_runs_dir(skill_root, config)
    run_id = args.run_id or make_run_id("init")

    out_path = Path(args.out) if args.out else (runs_root / run_id / "inputs" / "info_form.md")
    out_path = out_path.resolve()

    template_path = (skill_root / "references" / "info_form.md").resolve()
    if not args.interactive:
        ok = copy_info_form_template(template_path=template_path, out_path=out_path)
        if not ok:
            logger.error("❌ 未找到 info_form 模板。")
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
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    md = coord.reviewer_advice(
        project_root=Path(args.project_root),
        include_tier2=bool(args.tier2),
        tier2_chunk_size=int(args.chunk_size) if args.chunk_size is not None else None,
        tier2_max_chunks=int(args.max_chunks) if args.max_chunks is not None else None,
        tier2_fresh=bool(getattr(args, "fresh", False)),
    )
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
    return 0


def cmd_coach(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
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
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    print(coord.recommend_examples(query=str(args.query), top_k=int(args.top_k)), end="")
    return 0


def cmd_list_runs(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
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
    config = _load_config_for_args(skill_root, args)
    coord = HybridCoordinator(skill_root=skill_root, config=config)
    runs_root = get_runs_dir(skill_root, config)
    target = coord.target_path(project_root=Path(args.project_root))
    try:
        backup = find_backup_for_run(runs_root=runs_root, run_id=str(args.run_id), filename=target.name)
    except BackupNotFoundError:
        logger.error("❌ 未找到 run_id=%s 的备份文件。", str(args.run_id))
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
        logger.error("❌ 回滚需要显式确认：请加 --yes")
        return 2
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
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
        logger.error("❌ 未找到 run_id=%s 的备份文件。", str(args.run_id))
        return 2
    print(f"✅ 已回滚：{target}")
    print(f"📦 使用备份：{used}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nsfc-justification-writer", add_help=True)
    p.add_argument("--verbose", action="store_true", help="输出更详细的错误信息（包含堆栈）")
    p.add_argument("--preset", help="加载 config/presets/<name>.yaml（可选）")
    p.add_argument("--override", help="额外配置覆盖文件（yaml，可选，优先级最高）")
    p.add_argument("--no-user-override", action="store_true", help="不加载 ~/.config/nsfc-justification-writer/override.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_diag = sub.add_parser("diagnose", help="Tier1/Tier2 诊断（结构/引用/字数/表述）")
    p_diag.add_argument("--project-root", required=True)
    p_diag.add_argument("--tier2", action="store_true", help="启用 AI Tier2（需要 responder 环境）")
    p_diag.add_argument("--chunk-size", type=int, default=12000, help="Tier2 分块大小（字符数），用于大文件；<=0 表示不分块")
    p_diag.add_argument("--max-chunks", type=int, default=20, help="Tier2 最多处理的分块数（防止超长文件过慢）")
    p_diag.add_argument("--fresh", action="store_true", help="忽略 AI 缓存，强制重新计算 Tier2")
    p_diag.add_argument("--json-out", help="可选：输出 JSON 报告到文件")
    p_diag.add_argument("--html-report", help="可选：输出 HTML 报告到文件；用 auto 输出到 runs/...")
    p_diag.add_argument("--open", action="store_true", help="若生成 HTML 报告则尝试自动打开浏览器")
    p_diag.add_argument("--no-terms", action="store_true", help="HTML 报告不附带术语一致性矩阵")
    p_diag.add_argument("--run-id", help="可选：diagnose 的 run_id（用于 html-report=auto）")
    p_diag.set_defaults(func=cmd_diagnose)

    p_wc = sub.add_parser("wordcount", help="统计 1.1 立项依据字数并给出偏差")
    p_wc.add_argument("--project-root", required=True)
    p_wc.add_argument(
        "--mode",
        default=None,
        choices=["cjk_only", "cjk_strip_commands"],
        help="统计口径：cjk_only（默认）或 cjk_strip_commands（更接近正文估计）",
    )
    p_wc.set_defaults(func=cmd_wordcount)

    p_refs = sub.add_parser("refs", help="引用核验摘要 + 生成 nsfc-bib-manager 可复制提示词")
    p_refs.add_argument("--project-root", required=True)
    p_refs.add_argument("--verify-doi", default="none", choices=["none", "crossref"], help="可选：联网用 Crossref 校验 DOI")
    p_refs.add_argument("--doi-timeout", default=5.0, type=float, help="Crossref 校验超时时间（秒）")
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
    p_review.add_argument("--chunk-size", type=int, default=12000, help="Tier2 分块大小（字符数），用于大文件；<=0 表示不分块")
    p_review.add_argument("--max-chunks", type=int, default=20, help="Tier2 最多处理的分块数（防止超长文件过慢）")
    p_review.add_argument("--fresh", action="store_true", help="忽略 AI 缓存，强制重新计算 Tier2")
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
    p_apply.add_argument("--strict-quality", action="store_true", help="启用“新正文质量闸门”：命中绝对化表述/危险命令则拒绝写入")
    p_apply.add_argument("--suggest-alias", action="store_true", help="当标题未命中时，输出可用标题候选（便于改 title）")
    p_apply.set_defaults(func=cmd_apply_section)

    p_cfg = sub.add_parser("validate-config", help="校验当前配置（默认配置 + preset + override）")
    p_cfg.set_defaults(func=cmd_validate_config)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(verbose=bool(getattr(args, "verbose", False)))
    try:
        return int(args.func(args))
    except SystemExit:
        raise
    except SkillError as e:
        logger.error("❌ %s", str(e))
        if getattr(e, "fix_suggestion", ""):
            logger.error("\n💡 修复建议：")
            logger.error("%s", getattr(e, "fix_suggestion", ""))
        return 2
    except Exception as e:
        if bool(getattr(args, "verbose", False)):
            traceback.print_exc()
            raise
        logger.error("❌ %s: %s", type(e).__name__, str(e))
        logger.error("建议：加 --verbose 查看详细堆栈；或先运行 validate-config 检查配置。")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
