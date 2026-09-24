#!/usr/bin/env python3
"""Validate the repository's SKILL.md public document contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n(?P<content>.*)\Z", re.S)
KEY_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*):\s*(?P<value>.+)$")


def validate(path: Path, max_lines: int) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return ["missing YAML frontmatter"]

    keys = []
    for line in match.group("body").splitlines():
        item = KEY_RE.match(line)
        if item:
            keys.append(item.group("key"))
    if keys not in (["name", "description"], ["name", "description", "metadata"]):
        errors.append(f"frontmatter keys must be name, description, optional metadata; got {keys}")
    if "metadata" in keys and not re.search(
        r"^metadata:\s*\n  author:\s*Bensz Conan\s*$", match.group("body"), re.M
    ):
        errors.append("metadata.author must be Bensz Conan")
    if not re.search(r"^name:\s*[^\s#]+\s*$", match.group("body"), re.M):
        errors.append("name must be a non-empty identifier")
    if not re.search(r"^description:\s*.+$", match.group("body"), re.M):
        errors.append("description must be a non-empty single line")

    content = match.group("content")
    lines = content.splitlines()
    first_content = next((line for line in lines if line.strip()), "")
    if not first_content.startswith("# "):
        errors.append("content must start with one H1 title")
    headings = [
        (len(match.group("marks")), match.group("text"))
        for line in lines
        if (match := re.match(r"^(?P<marks>#{1,6})\s+(?P<text>.+?)\s*$", line))
    ]
    if (
        len(headings) >= 3
        and headings[0][0] == 1
        and headings[1][0] == 2
        and headings[2][0] == 1
    ):
        errors.append("opening headings contain a duplicate H1 separated by an H2")
    if len(text.splitlines()) > max_lines:
        errors.append(f"document exceeds {max_lines} lines")
    if re.search(r"^#{1,6}\s+\d+[.)]\s", content, re.M):
        errors.append("headings must not use numeric prefixes")
    if re.search(r"^#{1,6}\s+[^\n]*(?:⚠️|版本号|v\d+\.\d+\.\d+)", content, re.I | re.M):
        errors.append("version/status markers do not belong in SKILL.md headings")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=Path("skills"))
    parser.add_argument("--max-lines", type=int, default=500)
    args = parser.parse_args()

    files = sorted(args.skills_dir.glob("*/SKILL.md"))
    if not files:
        print(f"No SKILL.md files found under {args.skills_dir}", file=sys.stderr)
        return 2
    failures = 0
    for path in files:
        errors = validate(path, args.max_lines)
        if errors:
            failures += 1
            for error in errors:
                print(f"{path}: {error}")
    if failures:
        print(f"FAILED: {failures}/{len(files)} Skill documents")
        return 1
    print(f"OK: {len(files)} Skill documents satisfy the SKILL.md contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
