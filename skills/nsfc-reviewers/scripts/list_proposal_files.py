#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import yaml


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _load_yaml(p: Path) -> dict:
    try:
        obj = yaml.safe_load(_read_text(p)) or {}
    except Exception as e:
        raise ValueError(f"failed to read yaml: {p}: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError(f"expected yaml mapping: {p}")
    return obj


def _is_safe_relpath(p: Path) -> bool:
    if p.is_absolute():
        return False
    # Reject any ".." segment to keep path derivations predictable.
    return ".." not in p.parts


def _load_discovery_config(cfg: dict) -> tuple[list[str], list[str], str, str]:
    pf = cfg.get("proposal_files") if isinstance(cfg, dict) else None
    pf = pf if isinstance(pf, dict) else {}
    patterns = pf.get("patterns") or []
    exclude = pf.get("exclude") or []

    if not isinstance(patterns, list) or not all(isinstance(x, str) for x in patterns):
        raise ValueError("config.yaml: proposal_files.patterns must be a list of strings")
    if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
        raise ValueError("config.yaml: proposal_files.exclude must be a list of strings")

    os_cfg = cfg.get("output_settings") if isinstance(cfg, dict) else None
    os_cfg = os_cfg if isinstance(os_cfg, dict) else {}
    panel_dir = str(os_cfg.get("panel_dir") or "panels").strip()
    intermediate_dir = str(os_cfg.get("intermediate_dir") or ".nsfc-reviewers").strip()
    if not panel_dir or not intermediate_dir:
        raise ValueError("config.yaml: output_settings.panel_dir/intermediate_dir must be non-empty")

    return patterns, exclude, panel_dir, intermediate_dir


def _should_skip_path(
    *,
    rel: Path,
    panel_dir: str,
    intermediate_dir: str,
) -> bool:
    # Skip any file that is under intermediate outputs / final panels / legacy parallel-vibe roots.
    skip_dir_names = {
        panel_dir,
        intermediate_dir,
        ".parallel_vibe",
        ".parallel_vibe".lstrip("."),  # defensive; unlikely
        ".parallel_vibe".strip("/"),
    }
    for part in rel.parts[:-1]:
        if part in skip_dir_names:
            return True
    return False


def _matches_exclude(rel: Path, excludes: list[str]) -> bool:
    rel_posix = rel.as_posix()
    name = rel.name
    for pat in excludes:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_posix, pat):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    skill_root = Path(__file__).resolve().parents[1]
    cfg_path = skill_root / "config.yaml"
    if not cfg_path.exists():
        print(f"error: missing config.yaml at {cfg_path}", file=sys.stderr)
        return 2
    cfg = _load_yaml(cfg_path)
    try:
        patterns, excludes, panel_dir, intermediate_dir = _load_discovery_config(cfg)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    p = argparse.ArgumentParser(prog="list_proposal_files.py")
    p.add_argument("--proposal-path", required=True, help="标书目录或单个 .tex 文件路径")
    p.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="最多允许输出的文件数（0 表示不限制）；超限则退出码=3 并提示 count",
    )
    p.add_argument("--json", action="store_true", help="以 JSON 数组输出（默认逐行输出）")
    args = p.parse_args(argv)

    proposal_path = Path(str(args.proposal_path)).expanduser().resolve()
    if not proposal_path.exists():
        print(f"error: path not found: {proposal_path}", file=sys.stderr)
        return 2

    files: set[Path] = set()
    if proposal_path.is_file():
        if proposal_path.suffix.lower() != ".tex":
            print(f"error: proposal file must be a .tex file, got: {proposal_path.name}", file=sys.stderr)
            return 2
        files.add(proposal_path)
    else:
        # Recursive discovery (rglob) is more robust than only scanning the root.
        for pat in patterns:
            for f in proposal_path.rglob(pat):
                if not f.is_file():
                    continue
                if f.suffix.lower() != ".tex":
                    continue
                try:
                    rel = f.resolve().relative_to(proposal_path)
                except Exception:
                    continue
                if _should_skip_path(rel=rel, panel_dir=panel_dir, intermediate_dir=intermediate_dir):
                    continue
                if _matches_exclude(rel, excludes):
                    continue
                files.add(f.resolve())

    out = sorted(files)
    if args.max_files and len(out) > int(args.max_files):
        print(f"error: too many tex files: {len(out)} (max={args.max_files})", file=sys.stderr)
        return 3

    if args.json:
        import json

        print(json.dumps([str(p) for p in out], ensure_ascii=False, indent=2))
    else:
        for f in out:
            print(str(f))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

