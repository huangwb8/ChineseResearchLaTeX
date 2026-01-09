#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
_SUBSUBSECTION_RE = re.compile(r"\\subsubsection\s*\{([^}]*)\}")


@dataclass(frozen=True)
class LatexSection:
    title: str
    header_span: Tuple[int, int]
    body_span: Tuple[int, int]

    def body_text(self, source: str) -> str:
        start, end = self.body_span
        return source[start:end]


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        lines.append(_COMMENT_RE.sub("", line))
    return "\n".join(lines)


def parse_subsubsections(text: str) -> List[LatexSection]:
    matches = list(_SUBSUBSECTION_RE.finditer(text))
    sections: List[LatexSection] = []
    for idx, m in enumerate(matches):
        header_start, header_end = m.span()
        body_start = header_end
        body_end = matches[idx + 1].start() if (idx + 1) < len(matches) else len(text)
        title = (m.group(1) or "").strip()
        sections.append(
            LatexSection(
                title=title,
                header_span=(header_start, header_end),
                body_span=(body_start, body_end),
            )
        )
    return sections


def find_subsubsection(text: str, title: str) -> Optional[LatexSection]:
    for sec in parse_subsubsections(text):
        if sec.title == title:
            return sec
    return None


def replace_subsubsection_body(text: str, title: str, new_body: str) -> Tuple[str, bool]:
    sec = find_subsubsection(text, title)
    if sec is None:
        return text, False

    start, end = sec.body_span
    new_text = text[:start] + "\n" + new_body.rstrip() + "\n" + text[end:]
    return new_text, True
