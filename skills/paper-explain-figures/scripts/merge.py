#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


WORK_DIR_NAME = ".paper-explain-figures"


def _require_within(base_dir: Path, target: Path) -> None:
    base = base_dir.resolve()
    tgt = target.resolve()
    try:
        tgt.relative_to(base)
    except Exception as e:
        raise ValueError(f"path escapes base_dir: base={base} target={tgt}") from e


def _read_text_maybe(path: Path, *, max_chars: int = 240_000) -> str:
    try:
        s = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if len(s) > max_chars:
        return s[:max_chars] + f"\n\n...(truncated, total_chars={len(s)})\n"
    return s


def main() -> int:
    p = argparse.ArgumentParser(description="Merge .paper-explain-figures run outputs into a single Markdown report.")
    p.add_argument("--run-dir", required=True, help="某次 run 目录（例如 .paper-explain-figures/run_... ）")
    p.add_argument("--out", default="paper-explain-figures_report.md", help="输出 Markdown（默认写到当前目录）")
    args = p.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        raise SystemExit(f"[ERROR] run-dir 不存在或不是目录：{run_dir}")

    # Jobs are directories under run_dir, exclude meta files.
    job_dirs = sorted([p for p in run_dir.iterdir() if p.is_dir()])
    parts = ["# Figures", ""]
    for jd in job_dirs:
        md = jd / "analysis.md"
        if not md.exists():
            continue
        parts.append(_read_text_maybe(md).rstrip())
        parts.append("")

    cwd = Path.cwd().resolve()
    out = Path(args.out).expanduser()
    if not out.is_absolute():
        out = (cwd / out).resolve()
    try:
        _require_within(cwd, out)
    except Exception:
        raise SystemExit(f"[ERROR] --out 必须位于当前工作目录内：cwd={cwd} out={out}")
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
