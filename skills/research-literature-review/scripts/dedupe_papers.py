#!/usr/bin/env python3
"""Deprecated dedupe wrapper delegating to research-literature-search."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SEARCH_ROOT = Path(__file__).resolve().parents[2] / "research-literature-search" / "scripts"
sys.path.insert(0, str(SEARCH_ROOT))
from candidate_schema import normalize_record  # noqa: E402
from dedupe_papers import dedupe_records  # noqa: E402


def load_papers(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    raise ValueError("expected list[dict]")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deprecated dedupe compatibility wrapper")
    parser.add_argument("--input", "-i", required=True, type=Path)
    parser.add_argument("--output", "-o", required=True, type=Path)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--title-sim", type=float, default=.92)
    parser.add_argument("--token-jaccard", type=float, default=.80)
    parser.add_argument("--year-window", type=int, default=1)
    args = parser.parse_args()
    raw = load_papers(args.input)
    canonical = [normalize_record(item, provider=str(item.get("source") or "legacy"), fallback_index=index) for index, item in enumerate(raw)]
    result, edges = dedupe_records(canonical, title_similarity=args.title_sim, token_threshold=args.token_jaccard, year_window=args.year_window)
    write_jsonl(args.output, result)
    args.map.parent.mkdir(parents=True, exist_ok=True)
    args.map.write_text(json.dumps({"input_count": len(raw), "output_count": len(result), "merged_count": len(edges), "edges": edges}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
