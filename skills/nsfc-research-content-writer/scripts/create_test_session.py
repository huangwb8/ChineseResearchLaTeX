#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
import typing
from pathlib import Path


def _generate_test_id(now: dt.datetime) -> str:
    return f"v{now:%Y%m%d%H%M}"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_write(path: Path, content: str, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def _render_template(template: str, *, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _copy_or_template(
    *,
    dst_path: Path,
    src_path: Path | None,
    template_path: Path | None,
    template_values: dict[str, str] | None,
    overwrite: bool,
) -> None:
    if dst_path.exists() and not overwrite:
        return

    if src_path is not None and src_path.exists():
        if dst_path.exists():
            dst_path.unlink()
        shutil.copyfile(src_path, dst_path)
        return

    if template_path is not None and template_path.exists():
        template_text = template_path.read_text(encoding="utf-8")
        if template_values:
            template_text = _render_template(template_text, values=template_values)
        _safe_write(dst_path, template_text, overwrite=overwrite)
        return

    _safe_write(
        dst_path,
        "# TEST_PLAN\n\n（未找到可复制的计划文档或模板，请手动补全）\n",
        overwrite=overwrite,
    )


def _normalize_kind(kind: str) -> str:
    kind = kind.strip().lower()
    if kind in {"a", "a_round", "a-round"}:
        return "a"
    if kind in {"b", "b_round", "b-round"}:
        return "b"
    raise ValueError("kind must be 'a' or 'b'")


def _fail(parser: argparse.ArgumentParser, message: str) -> typing.NoReturn:
    parser.print_usage(sys.stderr)
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a nsfc-research-content-writer test session skeleton (A round or B round).",
    )
    parser.add_argument("--kind", default="a", help="Session kind: a (default) or b.")
    parser.add_argument("--id", default="", help="Explicit test id like vYYYYMMDDHHMM (optional).")
    parser.add_argument(
        "--create-plan",
        action="store_true",
        help="Create missing plan doc skeleton under plans/ (optional).",
    )
    parser.add_argument(
        "--seed-test-plan-from-plan",
        action="store_true",
        help="If plan doc exists, seed TEST_PLAN.md from it (optional).",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing session files.")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    if not (skill_root / "SKILL.md").exists():
        _fail(parser, f"missing SKILL.md at expected skill root: {skill_root}")

    try:
        kind = _normalize_kind(args.kind)
    except ValueError as exc:
        _fail(parser, str(exc))
    test_id = args.id.strip() or _generate_test_id(dt.datetime.now())
    if not test_id.startswith("v"):
        _fail(parser, "test id must start with 'v', e.g. vYYYYMMDDHHMM")

    plans_dir = skill_root / "plans"
    tests_dir = skill_root / "tests"
    templates_dir = skill_root / "templates"

    required_templates = [
        templates_dir / "OPTIMIZATION_PLAN_TEMPLATE.md",
        templates_dir / "B_ROUND_CHECK_TEMPLATE.md",
        templates_dir / "TEST_PLAN_TEMPLATE.md",
        templates_dir / "TEST_REPORT_TEMPLATE.md",
    ]
    missing_templates = [p for p in required_templates if not p.exists()]
    if missing_templates:
        missing_list = "\n".join(f"- {p.relative_to(skill_root)}" for p in missing_templates)
        _fail(
            parser,
            "missing required templates (run validate_skill.py for details):\n" + missing_list,
        )

    _ensure_dir(plans_dir)
    _ensure_dir(tests_dir)

    template_values = {
        "TEST_ID": test_id,
        "TARGET_SKILL_NAME": skill_root.name,
        "TARGET_SKILL_ROOT": str(skill_root),
        "PLAN_TIME": dt.datetime.now().isoformat(timespec="minutes"),
        "CHECK_TIME": dt.datetime.now().isoformat(timespec="minutes"),
        "PLAN_DATE": dt.datetime.now().date().isoformat(),
        "KIND_ARG": kind,
    }

    if kind == "a":
        session_name = test_id
        test_plan_template = templates_dir / "TEST_PLAN_TEMPLATE.md"
        plan_doc_path = plans_dir / f"{test_id}.md"
        plan_template = templates_dir / "OPTIMIZATION_PLAN_TEMPLATE.md"
        round_kind = "A轮"
    else:
        session_name = f"B轮-{test_id}"
        test_plan_template = templates_dir / "TEST_PLAN_TEMPLATE.md"
        plan_doc_path = plans_dir / f"B轮-{test_id}.md"
        plan_template = templates_dir / "B_ROUND_CHECK_TEMPLATE.md"
        round_kind = "B轮"

    template_values["ROUND_KIND"] = round_kind
    template_values["SESSION_NAME"] = session_name
    template_values["PLAN_DOC_PATH"] = str(plan_doc_path.relative_to(skill_root))

    if args.create_plan and (not plan_doc_path.exists() or args.overwrite):
        if plan_template.exists():
            _safe_write(
                plan_doc_path,
                _render_template(plan_template.read_text(encoding="utf-8"), values=template_values),
                overwrite=args.overwrite,
            )
        else:
            _safe_write(
                plan_doc_path,
                f"# 计划文档（{session_name}）\n\n（未找到模板，请手动补全）\n",
                overwrite=args.overwrite,
            )

    session_dir = tests_dir / session_name
    _ensure_dir(session_dir)
    _ensure_dir(session_dir / "_artifacts")
    _ensure_dir(session_dir / "_scripts")

    _copy_or_template(
        dst_path=session_dir / "TEST_PLAN.md",
        src_path=plan_doc_path if (args.seed_test_plan_from_plan and plan_doc_path.exists()) else None,
        template_path=test_plan_template if test_plan_template.exists() else None,
        template_values=template_values,
        overwrite=args.overwrite,
    )

    report_path = session_dir / "TEST_REPORT.md"
    test_report_template = templates_dir / "TEST_REPORT_TEMPLATE.md"
    if not report_path.exists() or args.overwrite:
        if test_report_template.exists():
            _safe_write(
                report_path,
                _render_template(test_report_template.read_text(encoding="utf-8"), values=template_values),
                overwrite=args.overwrite,
            )
        else:
            _safe_write(
                report_path,
                "# 测试报告（TEST_REPORT）\n\n"
                f"**测试会话**: {session_name}\n\n"
                "## 结果\n\n"
                "- 状态：✅ 通过 / ❌ 失败 / ⚠️ 部分通过\n\n"
                "## 证据\n\n"
                "- （填入命令输出、文件路径、对比结果等）\n",
                overwrite=args.overwrite,
            )

    print(str(session_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
