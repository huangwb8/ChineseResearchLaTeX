#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import builtins
import os
import platform
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = Path(__file__).resolve().parent
WORK_DIR = (TEST_ROOT / "work").resolve()

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write_report(*, overall_ok: bool, rows: List[Tuple[str, str, bool, str]], log_lines: List[str]) -> None:
    report_path = TEST_ROOT / "TEST_REPORT.md"
    python_info = f"{sys.version.split()[0]} ({sys.executable})"
    conclusion = "PASS" if overall_ok else "FAIL"

    def _row_line(case_id: str, goal: str, ok: bool, note: str) -> str:
        return f"| {case_id} | {goal} | {'PASS' if ok else 'FAIL'} | {note} |"

    table_lines = [
        "| 用例 | 目标 | 结果 | 说明 |",
        "|---|---|---|---|",
    ] + [_row_line(cid, goal, ok, note) for (cid, goal, ok, note) in rows]

    body = "\n".join(
        [
            "# 轻量测试报告：nsfc-justification-writer（P0–P2 安全修复验证）",
            "",
            f"**执行日期**：{_now()}  ",
            f"**执行命令**：`python3 tests/v202601100912/run_light_tests.py`  ",
            f"**结论**：{conclusion}  ",
            "",
            "---",
            "",
            "## 环境信息",
            "",
            f"- Python：{python_info}",
            f"- Platform：{platform.platform()}",
            f"- 工作目录：`{WORK_DIR}`",
            "",
            "---",
            "",
            "## 用例结果",
            "",
            "\n".join(table_lines),
            "",
            "---",
            "",
            "## 详细日志",
            "",
            "```",
            "\n".join(log_lines).rstrip(),
            "```",
            "",
            "---",
            "",
            "本文件不记录变更历史；变更历史统一记录在 `CHANGELOG.md`。",
            "",
        ]
    )
    report_path.write_text(body, encoding="utf-8")


@dataclass(frozen=True)
class Case:
    case_id: str
    goal: str
    fn: Callable[[], None]


def _ensure_clean_workdir() -> None:
    # 仅在测试目录树内操作，避免污染仓库其它位置
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    # 尽量保持可复现：清空 work/ 下旧内容（只删本目录树）
    for p in sorted(WORK_DIR.glob("**/*"), reverse=True):
        try:
            if p.is_file() or p.is_symlink():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
        except OSError:
            continue


def _import_skill_modules() -> None:
    skill_root = (REPO_ROOT / "skills" / "nsfc-justification-writer").resolve()
    sys.path.insert(0, str(skill_root))


def _case_t1_no_pyyaml_load_config_guardrails_ok() -> None:
    _import_skill_modules()
    from core.config_loader import load_config
    from core.security import build_write_policy

    orig_import = builtins.__import__

    def _fake_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):  # type: ignore[no-untyped-def]
        if name == "yaml":
            raise ImportError("PyYAML missing (simulated)")
        return orig_import(name, globals, locals, fromlist, level)

    try:
        builtins.__import__ = _fake_import  # type: ignore[assignment]
        cfg = load_config((REPO_ROOT / "skills" / "nsfc-justification-writer").resolve(), load_user_override=False)
    finally:
        builtins.__import__ = orig_import  # type: ignore[assignment]

    meta = cfg.get("_config_loader", {})
    assert isinstance(meta, dict)
    assert meta.get("yaml_available") is False

    policy = build_write_policy(cfg)
    assert isinstance(policy.allowed_relpaths, list) and len(policy.allowed_relpaths) > 0
    assert "extraTex/1.1.立项依据.tex" in set(policy.allowed_relpaths)


def _case_t2_guardrails_null_or_empty_never_weakens_whitelist() -> None:
    _import_skill_modules()
    from core.security import build_write_policy, validate_write_target

    proj = (WORK_DIR / "t2_project").resolve()
    (proj / "extraTex").mkdir(parents=True, exist_ok=True)
    (proj / "extraTex" / "1.1.立项依据.tex").write_text("ok", encoding="utf-8")
    (proj / "main.tex").write_text("no", encoding="utf-8")

    for cfg in [
        {"guardrails": None},
        {"guardrails": {}},
        {"guardrails": {"allowed_write_files": []}},
        {"guardrails": {"allowed_write_files": ["  "]}},
    ]:
        policy = build_write_policy(cfg)
        # 白名单不应为空
        assert policy.allowed_relpaths and "extraTex/1.1.立项依据.tex" in set(policy.allowed_relpaths)

        # 白名单目标允许
        validate_write_target(project_root=proj, target_path=(proj / "extraTex" / "1.1.立项依据.tex"), policy=policy)

        # 非白名单目标拒绝（主模板等）
        failed = False
        try:
            validate_write_target(project_root=proj, target_path=(proj / "main.tex"), policy=policy)
        except RuntimeError:
            failed = True
        assert failed is True


def _case_t3_prompt_external_path_warns() -> None:
    _import_skill_modules()
    from core.config_loader import _collect_config_warnings

    skill_root = (REPO_ROOT / "skills" / "nsfc-justification-writer").resolve()
    cfg = {
        "prompts": {
            "tier2_diagnostic": "/etc/passwd",
            "writing_coach": "../outside.txt",
        }
    }
    warns = _collect_config_warnings(skill_root=skill_root, config=cfg)  # type: ignore[arg-type]
    assert any("prompts.tier2_diagnostic" in w for w in warns)
    assert any("skill_root 之外" in w for w in warns)


def _case_t4_backup_find_by_relpath_and_legacy_fallback() -> None:
    _import_skill_modules()
    from core.versioning import find_backup_for_run_v2

    runs_root = (WORK_DIR / "t4_runs").resolve()
    run_new = "apply_new"
    run_old = "apply_old"

    # new style: backup/<run_id>/<relpath>
    p_new = (runs_root / run_new / "backup" / run_new / "extraTex" / "1.1.立项依据.tex").resolve()
    p_new.parent.mkdir(parents=True, exist_ok=True)
    p_new.write_text("new-backup", encoding="utf-8")

    got_new = find_backup_for_run_v2(
        runs_root=runs_root,
        run_id=run_new,
        target_relpath="extraTex/1.1.立项依据.tex",
        filename_fallback="1.1.立项依据.tex",
    )
    assert got_new.resolve() == p_new

    # legacy style: backup/<run_id>/<filename>
    p_old = (runs_root / run_old / "backup" / run_old / "1.1.立项依据.tex").resolve()
    p_old.parent.mkdir(parents=True, exist_ok=True)
    p_old.write_text("old-backup", encoding="utf-8")

    got_old = find_backup_for_run_v2(
        runs_root=runs_root,
        run_id=run_old,
        target_relpath="extraTex/1.1.立项依据.tex",
        filename_fallback="1.1.立项依据.tex",
    )
    assert got_old.resolve() == p_old


def main() -> int:
    _ensure_clean_workdir()
    log_lines: List[str] = [f"[{_now()}] start"]
    rows: List[Tuple[str, str, bool, str]] = []

    cases = [
        Case("T1", "无 PyYAML 降级仍可运行且 guardrails 生效", _case_t1_no_pyyaml_load_config_guardrails_ok),
        Case("T2", "guardrails 置空/清空不导致白名单失效", _case_t2_guardrails_null_or_empty_never_weakens_whitelist),
        Case("T3", "prompt 外部路径风险提示（warning）", _case_t3_prompt_external_path_warns),
        Case("T4", "备份/回滚按 relpath 定位 + 旧版回退", _case_t4_backup_find_by_relpath_and_legacy_fallback),
    ]

    overall_ok = True
    for c in cases:
        try:
            log_lines.append(f"[{_now()}] {c.case_id} begin: {c.goal}")
            c.fn()
            rows.append((c.case_id, c.goal, True, ""))
            log_lines.append(f"[{_now()}] {c.case_id} PASS")
        except Exception as e:
            overall_ok = False
            note = f"{type(e).__name__}: {e}"
            rows.append((c.case_id, c.goal, False, note))
            log_lines.append(f"[{_now()}] {c.case_id} FAIL: {note}")
            log_lines.append(traceback.format_exc().rstrip())

    log_lines.append(f"[{_now()}] end overall={'PASS' if overall_ok else 'FAIL'}")
    _write_report(overall_ok=overall_ok, rows=rows, log_lines=log_lines)
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
