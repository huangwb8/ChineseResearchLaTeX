#!/usr/bin/env python3
"""
validate_word_budget.py - 校验 word budget CSV（列/总字数/覆盖率）

检查：
- 必需列：文献ID,大纲,综字数,述字数
- 综+述 总和与目标字数误差 <= tolerance
- 覆盖：word_budget_final 中应包含 selected_papers 中的全部文献，允许空 ID 行（无引用段落）
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Set

import yaml


def read_budget(path: Path) -> tuple[list[dict], float]:
    rows = []
    total = 0.0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
            try:
                z = float(r.get("综字数", 0) or 0)
            except Exception:
                z = 0.0
            try:
                s = float(r.get("述字数", 0) or 0)
            except Exception:
                s = 0.0
            total += z + s
    return rows, total


def load_selected(path: Path) -> Set[str]:
    ids: Set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            pid = (obj.get("id") or obj.get("doi") or "").strip()
            if pid:
                ids.add(pid)
    return ids


def load_cfg(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("word_budget", {})


def main() -> int:
    p = argparse.ArgumentParser(description="Validate word budget CSV")
    p.add_argument("--budget", required=True, type=Path, help="word_budget_final.csv")
    p.add_argument("--selected", required=True, type=Path, help="selected_papers.jsonl")
    p.add_argument("--config", required=True, type=Path, help="config.yaml")
    p.add_argument("--target-words", type=float, help="override target words")
    args = p.parse_args()

    cfg = load_cfg(args.config)
    tol = float(cfg.get("tolerance", 0.05))
    target = args.target_words
    if target is None:
        scoring = (yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}).get("scoring", {})
        word_range = (scoring.get("default_word_range") or {}).get("premium", {})
        lo, hi = float(word_range.get("min", 0)), float(word_range.get("max", 0))
        target = (lo + hi) / 2 if (lo + hi) > 0 else 0.0

    rows, total = read_budget(args.budget)
    if not rows:
        print("✗ 预算表为空")
        return 1

    required_cols = {"文献ID", "大纲", "综字数", "述字数"}
    if set(rows[0].keys()) != required_cols:
        print(f"✗ 列不匹配，期望 {required_cols}")
        return 1

    selected_ids = load_selected(args.selected)
    budget_ids = {r.get("文献ID", "").strip() for r in rows if r.get("文献ID")}
    missing = selected_ids - budget_ids
    if missing:
        print(f"✗ 预算缺少 {len(missing)} 篇文献，如: {list(missing)[:3]}")
        return 1

    if target > 0 and abs(total - target) / target > tol:
        print(f"✗ 总字数 {total:.0f} 偏离目标 {target:.0f} 超过容忍 {tol*100:.1f}%")
        return 1

    print(f"✓ 预算通过，总字数 ~{int(round(total))}, 覆盖文献 {len(selected_ids)} 篇（允许空 ID 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

