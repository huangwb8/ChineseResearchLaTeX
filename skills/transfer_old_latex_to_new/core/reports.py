#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .latex_utils import safe_read_text


def write_restore_guide(deliverables_dir: Path, run_id: str) -> Path:
    deliverables_dir.mkdir(parents=True, exist_ok=True)
    path = deliverables_dir / "restore_guide.md"
    path.write_text(
        "\n".join(
            [
                "# 恢复指南",
                "",
                f"- run_id: `{run_id}`",
                "- 说明：本技能在 apply 前会为新项目的目标文件创建快照（仅限白名单路径）。",
                "",
                "## 一键恢复命令",
                "",
                "```bash",
                f"python skills/transfer_old_latex_to_new/scripts/run.py restore --run-id {run_id} --new /path/to/new_project",
                "```",
                "",
                "## 备注",
                "- 本恢复只覆盖本次 apply 涉及的目标文件。",
                "- 如新项目在 apply 后又被手动修改，恢复会以快照为准覆盖对应文件。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_structure_comparison(deliverables_dir: Path, diff: Dict[str, Any]) -> Path:
    deliverables_dir.mkdir(parents=True, exist_ok=True)
    path = deliverables_dir / "structure_comparison.md"

    mapping = (diff or {}).get("mapping") or {}
    one_to_one = mapping.get("one_to_one") or []
    new_added = mapping.get("new_added") or []
    removed = mapping.get("removed") or []
    low_conf = mapping.get("low_confidence") or []

    lines: List[str] = []
    lines += ["# 结构对比摘要", ""]
    lines += [f"- one_to_one: {len(one_to_one)}", f"- new_added: {len(new_added)}", f"- removed: {len(removed)}", f"- low_confidence: {len(low_conf)}", ""]

    if one_to_one:
        lines += ["## One-to-One", ""]
        for x in one_to_one:
            lines.append(f"- `{x.get('old')}` → `{x.get('new')}`（{x.get('confidence')}, score={x.get('score')}）")
        lines.append("")

    if low_conf:
        lines += ["## 低置信度（需人工确认）", ""]
        for x in low_conf:
            lines.append(f"- `{x.get('old')}` → `{x.get('new')}`（score={x.get('score')}）")
        lines.append("")

    if new_added:
        lines += ["## 新增章节（未映射）", ""]
        for x in new_added:
            lines.append(f"- `{x.get('file')}`")
        lines.append("")

    if removed:
        lines += ["## 旧章节未映射（需人工处理）", ""]
        for x in removed:
            lines.append(f"- `{x.get('file')}`")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_change_summary(deliverables_dir: Path, apply_result: Dict[str, Any]) -> Path:
    deliverables_dir.mkdir(parents=True, exist_ok=True)
    path = deliverables_dir / "change_summary.md"

    applied = (apply_result or {}).get("applied") or []
    skipped = (apply_result or {}).get("skipped") or []
    warnings = (apply_result or {}).get("warnings") or []

    lines: List[str] = ["# 变更摘要", ""]
    for w in warnings:
        lines.append(f"- ⚠️ {w}")
    if warnings:
        lines.append("")

    lines += [f"- 已执行任务: {len(applied)}", f"- 跳过任务: {len(skipped)}", ""]

    if applied:
        lines += ["## 已执行", ""]
        for t in applied:
            lines.append(f"- `{t.get('type')}`: `{t.get('source','')}` → `{t.get('target','')}`（{t.get('status','')}）")
        lines.append("")

    if skipped:
        lines += ["## 已跳过", ""]
        for t in skipped:
            lines.append(f"- `{t.get('type')}`: `{t.get('source','')}` → `{t.get('target','')}`（{t.get('skip_reason','')}）")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_unmapped_old_content(
    deliverables_dir: Path,
    old_project: Path,
    diff: Dict[str, Any],
    max_chars_per_file: int = 20000,
) -> Optional[Path]:
    mapping = (diff or {}).get("mapping") or {}
    removed = mapping.get("removed") or []
    if not removed:
        return None

    deliverables_dir.mkdir(parents=True, exist_ok=True)
    path = deliverables_dir / "unmapped_old_content.md"

    lines: List[str] = [
        "# 旧章节未映射内容（待人工迁移）",
        "",
        "说明：以下内容来自旧项目中未能自动映射的 `extraTex/*.tex`，用于确保科学内容不丢失。",
        "",
    ]

    for item in removed:
        rel = item.get("file")
        if not rel:
            continue
        abs_path = (old_project / rel).resolve()
        content = safe_read_text(abs_path) if abs_path.exists() else ""
        if max_chars_per_file and len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n\n% ... truncated ...\n"
        lines += [f"## `{rel}`", "", "```tex", content, "```", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path

