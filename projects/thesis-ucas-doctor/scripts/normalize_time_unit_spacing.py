#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = "extraTex/*.tex"
DEFAULT_BACKUP_DIR = Path(".latex-cache") / "time-unit-spacing" / "backups"

MATH_PATTERNS = [
    re.compile(r"\$(?:[^$\\]|\\.)*?\$"),
    re.compile(r"\\\((?:[^\\]|\\.)*?\\\)"),
    re.compile(r"\\\[(?:[^\\]|\\.)*?\\\]", re.DOTALL),
]
UNIT_SPACING_TARGETS = ("mg/kg", "rpm", "d", "g")
UNIT_SPACING_UNITS_RE = "|".join(re.escape(unit) for unit in UNIT_SPACING_TARGETS)
UNIT_SPACING_PATTERN = re.compile(
    rf"(?P<num>\d+(?:\.\d+)?)[ \t]+(?P<unit>{UNIT_SPACING_UNITS_RE})(?=$|[^A-Za-z/])"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 TeX 中 `60 d`、`8000 rpm`、`5.28 g`、`0.28 mg/kg` 规范为不换行空格连接（默认 dry-run）。"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=DEFAULT_PROJECT_DIR,
        help="项目根目录（默认脚本上级目录）",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help="扫描文件模式（相对 project-dir）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际写回文件；默认仅检查预览",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help="写回时备份目录（相对 project-dir）",
    )
    parser.add_argument(
        "--max-preview",
        type=int,
        default=5,
        help="每个文件最多预览命中行数",
    )
    return parser.parse_args()


def _find_unescaped_percent(line: str) -> int:
    for idx, char in enumerate(line):
        if char != "%":
            continue
        slash_count = 0
        probe = idx - 1
        while probe >= 0 and line[probe] == "\\":
            slash_count += 1
            probe -= 1
        if slash_count % 2 == 0:
            return idx
    return -1


def _protect_math(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        key = f"__BENSZ_TIME_MATH_{counter}__"
        placeholders[key] = match.group(0)
        counter += 1
        return key

    protected = text
    for pattern in MATH_PATTERNS:
        protected = pattern.sub(repl, protected)
    return protected, placeholders


def _restore_math(text: str, placeholders: dict[str, str]) -> str:
    restored = text
    for key in sorted(placeholders.keys(), key=len, reverse=True):
        restored = restored.replace(key, placeholders[key])
    return restored


def _safe_print(message: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(message)
    except UnicodeEncodeError:
        sanitized = message.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(sanitized)


def _normalize_text(text: str) -> tuple[str, int, list[tuple[int, str, str]]]:
    protected, placeholders = _protect_math(text)
    lines = protected.splitlines(keepends=True)
    changed = 0
    previews: list[tuple[int, str, str]] = []
    out_lines: list[str] = []

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")
        eol = "\n" if raw_line.endswith("\n") else ""
        comment_start = _find_unescaped_percent(line)
        if comment_start >= 0:
            code, comment = line[:comment_start], line[comment_start:]
        else:
            code, comment = line, ""

        normalized_code, count = UNIT_SPACING_PATTERN.subn(r"\g<num>~\g<unit>", code)
        if count > 0:
            changed += count
            before_preview = _restore_math(line, placeholders)
            after_preview = _restore_math(normalized_code + comment, placeholders)
            previews.append((lineno, before_preview, after_preview))

        out_lines.append(normalized_code + comment + eol)

    restored = _restore_math("".join(out_lines), placeholders)
    return restored, changed, previews


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()
    files = sorted(project_dir.glob(args.glob))
    if not files:
        print(f"[ERROR] 未匹配到文件: glob={args.glob}")
        return 1

    touched_files = 0
    total_hits = 0
    backup_root: Path | None = None
    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_root = (project_dir / args.backup_dir / stamp).resolve()
        backup_root.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] apply=1 backup_root={backup_root}")
    else:
        print("[INFO] apply=0 (dry-run)")

    for file_path in files:
        original = file_path.read_text(encoding="utf-8")
        normalized, hits, previews = _normalize_text(original)
        if hits == 0:
            continue

        touched_files += 1
        total_hits += hits
        rel_path = file_path.relative_to(project_dir)
        _safe_print(f"[HIT] {rel_path} replacements={hits}")
        for lineno, before, after in previews[: args.max_preview]:
            _safe_print(f"  - L{lineno}: {before}")
            _safe_print(f"    -> {after}")

        if args.apply:
            assert backup_root is not None
            backup_path = backup_root / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            file_path.write_text(normalized, encoding="utf-8", newline="\n")

    print(
        f"[SUMMARY] files_scanned={len(files)} files_changed={touched_files} replacements={total_hits}"
    )
    if args.apply and backup_root is not None:
        print(f"[SUMMARY] backups={backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
