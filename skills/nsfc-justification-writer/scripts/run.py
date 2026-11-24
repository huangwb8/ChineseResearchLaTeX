#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

sys.dont_write_bytecode = True

# core/ 实现统一托管在 scripts/core/ 下：
# - 运行脚本时，scripts/ 目录天然在 sys.path[0]
# - 这里显式插入 scripts/ 目录，避免外部环境把 skill_root 放到更前导致 import core 失效
scripts_root_for_import = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts_root_for_import))

from core.config_loader import load_config, get_runs_dir, validate_config
from core.config_access import get_bool, get_mapping, get_seq_str, get_str
from core.bib_manager_integration import BibFixSuggestion
from core.change_guard import inspect_proposal
from core.errors import BackupNotFoundError, SkillError
from core.coordinator import Coordinator
from core.logging_utils import configure_logging
from core.observability import ensure_run_dir, make_run_id
from core.reference_validator import check_citations
from core.security import validate_target_file
from core.editor import apply_new_content
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
    override = getattr(args, "override", None)
    no_user_override = bool(getattr(args, "no_user_override", False))
    cfg = load_config(
        skill_root,
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
    coord = Coordinator(skill_root=skill_root, config=config)

    if getattr(args, "verbose", False):
        logger.info("⏳ 正在运行机器检查；随后由宿主 AI 做一次语义审查...")
    report = coord.diagnose(project_root=Path(args.project_root))
    text = coord.format_diagnose(report)
    print(text, end="")

    if args.json_out:
        _write_json(Path(args.json_out), report.to_dict())

    return 0


def cmd_wordcount(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = Coordinator(skill_root=skill_root, config=config)
    status = coord.word_count_status(project_root=Path(args.project_root), mode=getattr(args, "mode", None))
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def cmd_refs(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = Coordinator(skill_root=skill_root, config=config)

    report = coord.diagnose(project_root=Path(args.project_root))
    sug = BibFixSuggestion(
        missing_bibkeys=list(report.checks.missing_citation_keys or []),
        missing_doi_keys=list(getattr(report.checks, "missing_doi_keys", []) or []),
        invalid_doi_keys=list(getattr(report.checks, "invalid_doi_keys", []) or []),
    )
    md = sug.to_markdown(project_root=str(Path(args.project_root)))
    if str(getattr(args, "verify_doi", "none")).strip().lower() == "crossref":
        logger.warning("⚠️ 将联网请求 Crossref API 校验 DOI（可用 --doi-timeout 调整超时；失败/超时不会断言不存在）")
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
            md = md.rstrip() + "\n\n## Crossref（可选联网）校验失败/超时的 DOI（记录为待核验）\n\n" + "\n".join(failed) + "\n"
        else:
            md = md.rstrip() + "\n\n## Crossref（可选联网）校验\n\n- ✅ 未发现明显失败（仍建议抽查关键引用）\n"
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已输出：{args.out}")
        return 0
    print(md, end="")
    return 0


def cmd_validate_config(args: argparse.Namespace) -> int:
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    meta = get_mapping(config, "_config_loader")
    if not bool(meta.get("yaml_available", True)):
        print("⚠️ 未安装 PyYAML：无法加载/校验 YAML 配置文件。")
        print("   - 当前仅保证 guardrails 等安全兜底生效。")
        print("   - 建议：安装 PyYAML 后再运行 validate-config（`pip install pyyaml`）。")
        return 0
    errs = validate_config(skill_root=skill_root, config=config)
    if errs:
        logger.error("❌ 配置校验失败：")
        for e in errs:
            logger.error("- %s", e)
        return 2
    print("✅ 配置有效")
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    """生成完整正文提案 diff，并按配置自动写入（--dry-run 时保持只读）。"""
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = Coordinator(skill_root=skill_root, config=config)
    project_root = Path(args.project_root).resolve()
    guard = get_mapping(config, "guardrails")
    auto_apply = (
        (not bool(getattr(args, "dry_run", False)))
        and get_str(guard, "output_mode", "preview").strip().lower() in {"auto_apply", "auto", "write"}
    )
    if args.target_file:
        raw_target = Path(args.target_file).expanduser()
        target = (raw_target if raw_target.is_absolute() else project_root / raw_target).resolve()
        target = validate_target_file(
            project_root=project_root,
            target_path=target,
            require_exists=not (auto_apply and get_bool(guard, "auto_create_target", True)),
        )
    else:
        target = coord.target_path(project_root=project_root)
    if not target.is_file() and not (auto_apply and get_bool(guard, "auto_create_target", True)):
        logger.error("❌ 目标文件不存在：%s", target)
        return 2
    proposal = _read_body_file(args.proposal_file)
    original = target.read_text(encoding="utf-8", errors="ignore") if target.is_file() else ""
    try:
        result = inspect_proposal(original=original, proposed=proposal, target_path=target, project_root=project_root)
    except ValueError as exc:
        logger.error("❌ 目标路径越出 project_root：%s", exc)
        return 2
    print(f"目标文件：{target}")
    print(f"修改行数：{result.changed_lines}")
    targets = get_mapping(config, "targets")
    bib_globs = targets.get("bib_globs", ["references/*.bib"])
    cite_result = check_citations(tex_text=proposal, project_root=project_root, bib_globs=bib_globs)
    if cite_result.missing_keys:
        print("⚠️ 提案包含缺失 bibkey（已记录，自动流程不暂停）：" + "、".join(cite_result.missing_keys[:30]))
    if result.structural_hits:
        print("⚠️ 预览发现结构/配置命令变化（自动流程保留原文件并要求宿主 AI 重试正文-only）：" + "、".join(result.structural_hits))
        print("宿主 AI 应自动移除结构命令后重试；不会请求用户确认。")
    else:
        print("✅ 未发现结构/配置命令变化。")
    print("\n--- unified diff ---")
    print(result.diff, end="")
    if result.structural_hits and not bool(getattr(args, "allow_structural_change", False)):
        return 2
    if not auto_apply:
        print("ℹ️ 只读模式：未写入文件（可移除 --dry-run 并使用 guardrails.output_mode=auto_apply）。")
        return 0
    if cite_result.missing_keys and not get_bool(get_mapping(config, "references"), "allow_missing_citations", False):
        print("⚠️ 自动写入暂缓：宿主 AI 应移除未核验引用或改写对应主张后自动重试；不向用户提问。")
        return 2

    run_id = make_run_id("auto")
    runs_root = get_runs_dir(skill_root, config)
    run_dir = ensure_run_dir(runs_root, run_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        rel = target.relative_to(project_root).as_posix()
    except ValueError:
        rel = target.name
    from core.security import build_write_policy, validate_write_target

    policy = build_write_policy(config)
    # 未配置固定目标时，自动发现的项目正文可加入本次会话白名单；禁写路径仍优先阻断。
    configured_target = get_str(get_mapping(config, "targets"), "justification_tex", "").strip()
    if not configured_target and not args.target_file:
        try:
            if rel not in policy.allowed_relpaths:
                policy.allowed_relpaths.append(rel)
        except AttributeError:
            pass
    validate_write_target(project_root=project_root, target_path=target, policy=policy)
    applied = apply_new_content(
        target_path=target,
        new_text=proposal,
        backup_root=(run_dir / "backup").resolve(),
        run_id=run_id,
        target_relpath=rel,
    )
    log_path = (run_dir / "logs" / "auto_apply.json").resolve()
    _write_json(
        log_path,
        {
            "run_id": run_id,
            "target": str(target),
            "target_relpath": rel,
            "changed": applied.changed,
            "backup": str(applied.backup_path) if applied.backup_path else None,
            "missing_bibkeys": cite_result.missing_keys,
            "structural_hits": result.structural_hits,
        },
    )
    print(f"✅ 已自动写入：{target}")
    if applied.backup_path:
        print(f"📦 自动备份：{applied.backup_path}")
    print(f"🧾 自动写入记录：{log_path}")
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
    coord = Coordinator(skill_root=skill_root, config=config)
    runs_root = get_runs_dir(skill_root, config)
    target = coord.target_path(project_root=Path(args.project_root))
    try:
        target_relpath = target.relative_to(Path(args.project_root).resolve()).as_posix()
    except ValueError:
        target_relpath = target.name
    try:
        backup = find_backup_for_run(
            runs_root=runs_root,
            run_id=str(args.run_id),
            target_relpath=target_relpath,
        )
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
        logger.error("❌ 回滚需要显式安全开关：请加 --yes")
        return 2
    skill_root = Path(__file__).resolve().parent.parent
    config = _load_config_for_args(skill_root, args)
    coord = Coordinator(skill_root=skill_root, config=config)
    runs_root = get_runs_dir(skill_root, config)
    target = coord.target_path(project_root=Path(args.project_root))
    try:
        target_relpath = target.relative_to(Path(args.project_root).resolve()).as_posix()
    except ValueError:
        target_relpath = target.name
    try:
        used = rollback_from_backup(
            runs_root=runs_root,
            run_id=str(args.run_id),
            target_path=target,
            target_relpath=target_relpath,
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
    p.add_argument("--override", help="额外配置覆盖文件（yaml，可选，优先级最高）")
    p.add_argument("--no-user-override", action="store_true", help="不加载 ~/.config/nsfc-justification-writer/override.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_diag = sub.add_parser("diagnose", help="机器诊断（结构/引用/字数）")
    p_diag.add_argument("--project-root", required=True)
    p_diag.add_argument("--json-out", help="可选：输出 JSON 报告到文件")
    p_diag.set_defaults(func=cmd_diagnose)

    p_wc = sub.add_parser("wordcount", help="统计 1.1 立项依据字数（不设目标）")
    p_wc.add_argument("--project-root", required=True)
    p_wc.add_argument(
        "--mode",
        default=None,
        choices=["cjk_only", "cjk_strip_commands"],
        help="统计口径：cjk_only（默认）或 cjk_strip_commands（更接近正文估计）",
    )
    p_wc.set_defaults(func=cmd_wordcount)

    p_refs = sub.add_parser("refs", help="引用核验摘要 + 生成 BibTeX 补齐/核验提示词")
    p_refs.add_argument("--project-root", required=True)
    p_refs.add_argument("--verify-doi", default="none", choices=["none", "crossref"], help="可选：联网用 Crossref 校验 DOI")
    p_refs.add_argument("--doi-timeout", default=5.0, type=float, help="Crossref 校验超时时间（秒）")
    p_refs.add_argument("--out", help="可选：输出到文件（markdown）")
    p_refs.set_defaults(func=cmd_refs)

    p_runs = sub.add_parser("list-runs", help="列出 runs_dir 下的 run_id（用于 diff/rollback）")
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
    p_rb.add_argument("--yes", action="store_true", help="启用回滚安全开关（必须显式指定）")
    p_rb.add_argument("--no-backup", action="store_true", help="不备份当前版本（默认备份到新的 runs_dir/）")
    p_rb.add_argument("--new-run-id", help="可选：回滚备份的 run_id（默认按时间生成）")
    p_rb.set_defaults(func=cmd_rollback)

    p_preview = sub.add_parser("preview", help="生成完整正文 unified diff；默认自动写入，--dry-run 只读")
    p_preview.add_argument("--project-root", required=True)
    p_preview.add_argument("--proposal-file", required=True, help="完整正文提案文件；用 - 表示从 stdin 读")
    p_preview.add_argument("--target-file", help="可选：相对或绝对目标 .tex；未提供时按配置/唯一候选发现")
    p_preview.add_argument("--allow-structural-change", action="store_true", help="允许 diff 中出现结构/配置命令变化（仅在项目白名单允许时使用）")
    p_preview.add_argument("--dry-run", action="store_true", help="只生成 diff，不写入文件")
    p_preview.set_defaults(func=cmd_preview)

    p_cfg = sub.add_parser("validate-config", help="校验当前配置（默认配置 + override）")
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
