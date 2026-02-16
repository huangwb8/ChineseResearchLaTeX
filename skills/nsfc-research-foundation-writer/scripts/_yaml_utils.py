from __future__ import annotations

import re
from typing import Iterable


def extract_yaml_value_under_block(lines: Iterable[str], block_key: str, key: str) -> str | None:
    """
    Minimal YAML extractor for a scalar value under a top-level mapping block.

    This skill intentionally avoids external YAML dependencies; keep this helper
    small and predictable, and only support the patterns we generate in config.yaml.
    """
    in_block = False
    block_indent: int | None = None
    key_re = re.compile(rf"^(\s*){re.escape(key)}:\s*(.*?)\s*$")

    for line in lines:
        if not in_block:
            if re.match(rf"^{re.escape(block_key)}:\s*$", line):
                in_block = True
                block_indent = len(line) - len(line.lstrip(" "))
            continue

        if line.strip() == "":
            continue

        indent = len(line) - len(line.lstrip(" "))
        if block_indent is not None and indent <= block_indent and not line.startswith(" " * (block_indent + 1)):
            break

        m = key_re.match(line)
        if m and indent >= (block_indent or 0) + 2:
            return m.group(2).strip().strip('"').strip("'")

    return None


def extract_yaml_list_under_block(lines: Iterable[str], block_key: str, key: str) -> list[str] | None:
    """Extract a simple YAML list under `block_key: { key: [ - item ] }` style."""
    in_block = False
    block_indent: int | None = None
    key_indent: int | None = None
    items: list[str] = []

    for line in lines:
        if not in_block:
            if re.match(rf"^{re.escape(block_key)}:\s*$", line):
                in_block = True
                block_indent = len(line) - len(line.lstrip(" "))
            continue

        if line.strip() == "":
            continue

        indent = len(line) - len(line.lstrip(" "))
        if block_indent is not None and indent <= block_indent and not line.startswith(" " * (block_indent + 1)):
            break

        if key_indent is None:
            if re.match(rf"^\s*{re.escape(key)}:\s*$", line) and indent >= (block_indent or 0) + 2:
                key_indent = indent
            continue

        if indent <= key_indent:
            break

        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped.removeprefix("- ").strip().strip('"').strip("'"))

    return items if items else None

