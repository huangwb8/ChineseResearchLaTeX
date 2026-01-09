#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REQUIRED_HEADINGS = [
    "## 写作哲学",
    "## 命名与术语",
    "## 基本原理",
    "## 文献综述与创新性",
    "## 落点清单",
    "## 研究风险",
    "## 附录",
]

BANNED_SNIPPETS: list[str] = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="验证项目指南文件的结构完整性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 项目指南.md
  %(prog)s projects/MyProject/写作指南.md
  %(prog)s docs/guide.md
        """
    )
    parser.add_argument(
        "guide_path",
        type=Path,
        help="项目指南文件的路径（相对于当前目录或绝对路径）",
    )
    return parser.parse_args()


def validate_guide(guide_path: Path) -> int:
    if not guide_path.exists():
        print(f"[FAIL] Missing file: {guide_path}")
        return 2

    try:
        text = guide_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"[FAIL] Not valid UTF-8: {guide_path}")
        return 3

    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    if missing:
        print("[FAIL] Required headings missing:")
        for h in missing:
            print(f"  - {h}")
        return 4

    banned_found = [s for s in BANNED_SNIPPETS if s in text]
    if banned_found:
        print("[FAIL] Banned snippet(s) found (indicates unintended new structure):")
        for s in banned_found:
            print(f"  - {s}")
        return 5

    print("[OK] Guide structure looks intact.")
    return 0


def main() -> int:
    args = parse_args()
    return validate_guide(args.guide_path)


if __name__ == "__main__":
    raise SystemExit(main())
