#!/usr/bin/env python3
"""在显式任务工作区创建轻量测试会话，不向 Skill 源码写入。"""
from __future__ import annotations
import argparse
import datetime as dt
import re
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 11):
    raise SystemExit("需要 Python 3.11+")
from revision import SKILL_ROOT, SKILL_NAME, RevisionError, task_path, under


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--kind", choices=("a", "b", "a_round", "a-round", "b_round", "b-round"), default="a")
    parser.add_argument("--id", default="")
    parser.add_argument("--create-plan", action="store_true", help="兼容旧参数；计划仅放入本次会话")
    parser.add_argument("--seed-test-plan-from-plan", action="store_true", help="兼容旧参数；不读取 Skill 内历史计划")
    parser.add_argument("--overwrite", action="store_true", help="显式允许覆盖本次会话已有文档")
    args = parser.parse_args()
    try:
        task = task_path(args.task_root)
        test_id = args.id or dt.datetime.now().strftime("v%Y%m%d%H%M")
        if not re.fullmatch(r"v\d{12}", test_id):
            raise RevisionError("id 须为 vYYYYMMDDHHMM")
        kind = args.kind[0]
        session = under(task, f"{SKILL_NAME}/output/test-{kind}-{test_id}", must_exist=False)
        session.mkdir(parents=True, exist_ok=True)
        paths = [under(session, name, must_exist=False) for name in ("TEST_PLAN.md", "TEST_REPORT.md")]
        if not args.overwrite and any(p.exists() for p in paths):
            raise RevisionError("会话文档已存在；拒绝覆盖")
        for dst in paths:
            text = (SKILL_ROOT / "templates" / dst.name.replace(".md", "_TEMPLATE.md")).read_text(encoding="utf-8")
            for key, value in {"SESSION_NAME": session.name, "TEST_ID": test_id, "ROUND_KIND": kind,
                               "TARGET_SKILL_NAME": SKILL_NAME}.items():
                text = text.replace("{{" + key + "}}", value)
            dst.write_text(text, encoding="utf-8")
        if args.create_plan or args.seed_test_plan_from_plan:
            print("WARN: 旧计划参数仅兼容；正式维护计划请放仓库 docs/plans/。", file=sys.stderr)
        print(session.relative_to(task))
        return 0
    except (RevisionError, OSError, ValueError) as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    raise SystemExit(main())
