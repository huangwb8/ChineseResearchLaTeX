#!/usr/bin/env python3
"""
organize_run_dir.py - 整理单次综述运行目录的文件布局（把中间产物收纳到隐藏目录）

目标：
  - 工作目录根部只保留最终交付物：
      {stem}_工作条件.md / {stem}_review.tex / {stem}_参考文献.bib / {stem}_review.pdf / {stem}_review.docx
  - 其余中间产物移动到：
      {work_dir}/.systematic-literature-review/artifacts/
      {work_dir}/.systematic-literature-review/checkpoints/
      {work_dir}/.systematic-literature-review/cache/

安全策略：
  - 默认 dry-run（只打印计划，不移动）
  - 仅移动“已知 runner 产物”命名模式，避免误伤用户自建文件
"""

from __future__ import annotations

import argparse
from pathlib import Path


HIDDEN = ".systematic-literature-review"

FINAL_SUFFIXES = (
    "_工作条件.md",
    "_review.tex",
    "_参考文献.bib",
    "_review.pdf",
    "_review.docx",
    "_验证报告.md",
)


def is_final_output(p: Path) -> bool:
    name = p.name
    return any(name.endswith(suf) for suf in FINAL_SUFFIXES)


def iter_candidates(work_dir: Path) -> list[Path]:
    globs = [
        "pipeline_state.json",
        "checkpoint_*.json",
        "search_plan*.json",
        "search_log_openalex.json",
        "papers*.jsonl",
        "extended_papers*.jsonl",
        "supplemented_papers*.jsonl",
        "expanded_keywords.json",
        "quality_report*.json",
        "evidence_sufficiency*.json",
        "evidence_cards*.jsonl",
        "dedupe_map*.json",
        "supplement_search_history*.json",
        "sentinel_*",
        "selected_*",
        "doi_to_bibkey.json",
        "bibtex_report.json",
        "ccs_append*.bib",
        "data_extraction_table.md",
        "degraded_outline*.md",
        # AI 临时脚本（应移动到 .systematic-literature-review/scripts/）
        "temp_*.py",
        "debug_*.py",
        "analysis_*.py",
    ]
    out: list[Path] = []
    for g in globs:
        out.extend(sorted(work_dir.glob(g)))
    # unique
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize a systematic-literature-review run directory layout.")
    parser.add_argument("--work-dir", required=True, type=Path, help="Run directory (contains final outputs)")
    parser.add_argument("--apply", action="store_true", help="Apply changes (move files). Default is dry-run.")
    args = parser.parse_args()

    work_dir = args.work_dir.expanduser().resolve()
    if not work_dir.exists() or not work_dir.is_dir():
        raise SystemExit(f"work_dir not found or not a directory: {work_dir}")

    hidden = work_dir / HIDDEN
    artifacts = hidden / "artifacts"
    checkpoints = hidden / "checkpoints"
    cache = hidden / "cache"
    scripts = hidden / "scripts"

    moves: list[tuple[Path, Path]] = []
    for p in iter_candidates(work_dir):
        if not p.is_file():
            continue
        if is_final_output(p):
            continue
        if p.name.startswith("checkpoint_"):
            target_dir = checkpoints
        elif p.name == "pipeline_state.json":
            target_dir = hidden
        elif p.suffix == ".py":
            # AI 临时脚本移动到 scripts 目录
            target_dir = scripts
        else:
            target_dir = artifacts
        dst = target_dir / p.name
        if dst.exists():
            # skip conflicts
            continue
        moves.append((p, dst))

    if not moves:
        print("✓ no moves needed")
        return 0

    print(f"work_dir: {work_dir}")
    print(f"hidden:   {hidden}")
    print(f"mode:     {'apply' if args.apply else 'dry-run'}")
    print()
    for src, dst in moves:
        rel_src = src.relative_to(work_dir)
        rel_dst = dst.relative_to(work_dir)
        print(f"- {rel_src} -> {rel_dst}")

    if not args.apply:
        print("\n(dry-run) add --apply to move files")
        return 0

    hidden.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    checkpoints.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    scripts.mkdir(parents=True, exist_ok=True)

    moved = 0
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dst)
        moved += 1

    print(f"\n✓ moved {moved} files into {HIDDEN}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
