#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""用于诊断 LaTeX 小节结构的轻量解析器。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


_SUBSUBSECTION_CMD_RE = re.compile(r"\\subsubsection\*?")


@dataclass(frozen=True)
class LatexSection:
    title: str
    header_span: Tuple[int, int]
    body_span: Tuple[int, int]

    def body_text(self, source: str) -> str:
        start, end = self.body_span
        return source[start:end]


def _count_prev_backslashes(line: str, idx_before: int) -> int:
    n = 0
    i = idx_before
    while i >= 0 and line[i] == "\\":
        n += 1
        i -= 1
    return n


def _parse_balanced_inline(line: str, start: int, *, left: str, right: str) -> Optional[int]:
    """
    给定 line[start] == left，返回与之匹配的 right 的位置（含嵌套），找不到则返回 None。
    仅用于单行可选参数解析（如 \\subsubsection[...]{...} 里的 [...]）。
    """
    if start < 0 or start >= len(line) or line[start] != left:
        return None
    depth = 0
    for i in range(start, len(line)):
        ch = line[i]
        if ch == left:
            depth += 1
        elif ch == right:
            depth -= 1
            if depth == 0:
                return i
    return None


def _find_comment_start(line: str) -> Optional[int]:
    """
    在单行内定位注释起点（%），并尽量避免误伤 \\verb / \\lstinline 内的 %。
    规则近似：
    - unescaped %（其前连续 \\ 数量为偶数）视为注释起点
    - 进入 \\verb<delim>...<delim> 与 \\lstinline[... ]<delim>...<delim> 时，跳过其内部
    """
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\":
            if line.startswith("\\verb", i):
                j = i + 5
                if j < len(line) and line[j] == "*":
                    j += 1
                if j >= len(line):
                    return None
                delim = line[j]
                k = line.find(delim, j + 1)
                if k == -1:
                    return None
                i = k + 1
                continue

            if line.startswith("\\lstinline", i):
                j = i + 9
                if j < len(line) and line[j] == "*":
                    j += 1
                if j < len(line) and line[j] == "[":
                    end = _parse_balanced_inline(line, j, left="[", right="]")
                    if end is None:
                        return None
                    j = end + 1
                if j >= len(line):
                    return None
                delim = line[j]
                k = line.find(delim, j + 1)
                if k == -1:
                    return None
                i = k + 1
                continue

        if ch == "%":
            if _count_prev_backslashes(line, i - 1) % 2 == 0:
                return i
        i += 1
    return None


def strip_comments(text: str, *, preserve_length: bool = False) -> str:
    """
    移除 LaTeX 行注释（% ...），并尽量避免误删 \\verb / \\lstinline 内的 %。

    - preserve_length=True 时，用空格替换注释部分以保持字符位置（便于后续 span 对齐）。
    """
    envs = {"verbatim", "lstlisting", "minted"}
    in_verbatim = False

    out_lines: List[str] = []
    for line in (text or "").splitlines():
        code_line = line
        if not in_verbatim:
            start = _find_comment_start(line)
            if start is not None:
                if preserve_length:
                    code_line = line[:start] + (" " * (len(line) - start))
                else:
                    code_line = line[:start]
        out_lines.append(code_line)

        # 仅用“非注释部分”判断环境切换（避免 \\begin{...}%comment 的误触发）
        probe = code_line
        if not in_verbatim:
            for e in envs:
                if f"\\begin{{{e}}}" in probe:
                    in_verbatim = True
                    break
        else:
            for e in envs:
                if f"\\end{{{e}}}" in probe:
                    in_verbatim = False
                    break

    return "\n".join(out_lines)


def _parse_balanced(text: str, start: int, *, left: str, right: str) -> Optional[int]:
    """
    给定 text[start] == left，返回匹配 right 的位置（含嵌套）。
    近似跳过转义括号（\\{、\\} 等）。
    """
    if start < 0 or start >= len(text) or text[start] != left:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == left and _count_prev_backslashes(text, i - 1) % 2 == 0:
            depth += 1
        elif ch == right and _count_prev_backslashes(text, i - 1) % 2 == 0:
            depth -= 1
            if depth == 0:
                return i
    return None


def _parse_subsubsection_header(text: str, start: int) -> Optional[Tuple[int, int, str]]:
    """
    从 start（\\subsubsection 或 \\subsubsection* 的开头）解析 header_end 与 title。
    返回：(header_start, header_end, title)
    """
    m = _SUBSUBSECTION_CMD_RE.match(text, start)
    if not m:
        return None

    i = m.end()
    # 可选空白
    while i < len(text) and text[i].isspace():
        i += 1
    # 可选短标题参数 [...]
    if i < len(text) and text[i] == "[":
        end = _parse_balanced(text, i, left="[", right="]")
        if end is None:
            return None
        i = end + 1
        while i < len(text) and text[i].isspace():
            i += 1
    # 必需长标题 { ... }
    if i >= len(text) or text[i] != "{":
        return None
    end = _parse_balanced(text, i, left="{", right="}")
    if end is None:
        return None
    title = text[i + 1 : end].strip()
    return (start, end + 1, title)


def parse_subsubsections(text: str) -> List[LatexSection]:
    """
    解析所有 \\subsubsection（含 \\subsubsection*、可选短标题 [...]）。

    - 相比正则，支持嵌套花括号（标题中包含 \\textit{...} 等）。
    - 通过 preserve_length 的注释剥离保持 span 对齐，避免把注释里的 \\subsubsection 误当成结构。
    """
    source = text or ""
    scan = strip_comments(source, preserve_length=True)

    headers: List[Tuple[int, int, str]] = []
    for m in _SUBSUBSECTION_CMD_RE.finditer(scan):
        parsed = _parse_subsubsection_header(scan, m.start())
        if not parsed:
            continue
        hs, he, title = parsed
        # title 以原始文本为准（scan 仅用于定位）
        parsed_src = _parse_subsubsection_header(source, hs)
        if parsed_src:
            _, _, title = parsed_src
            he = parsed_src[1]
        headers.append((hs, he, title))

    sections: List[LatexSection] = []
    for idx, (hs, he, title) in enumerate(headers):
        body_start = he
        body_end = headers[idx + 1][0] if (idx + 1) < len(headers) else len(source)
        sections.append(LatexSection(title=title, header_span=(hs, he), body_span=(body_start, body_end)))
    return sections
