#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass

from .latex_parser import strip_comments


_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
_MATH_ENV_RE = re.compile(
    r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?|math|displaymath)\}.*?\\end\{\1\}",
    re.DOTALL,
)


@dataclass(frozen=True)
class WordCountResult:
    cjk_count: int


def describe_word_count_mode(mode: str) -> str:
    m = str(mode or "").strip().lower()
    if m == "cjk_strip_commands":
        return "cjk_strip_commands：先粗剔除注释/类代码环境/数学环境/控制序列，再统计 CJK 字符数（更接近“正文字符数”的估计）"
    return "cjk_only：仅剔除注释后统计 CJK 字符数（保守、可复现，但会把命令参数/数学环境中的中文也计入）"


def _strip_code_like_envs(text: str) -> str:
    envs = {"verbatim", "lstlisting", "minted"}
    in_env = False
    active = ""
    out_lines = []
    for line in (text or "").splitlines():
        if not in_env:
            out_lines.append(line)
            for e in envs:
                if f"\\begin{{{e}}}" in line:
                    in_env = True
                    active = e
                    break
            continue

        if f"\\end{{{active}}}" in line:
            in_env = False
            active = ""
            out_lines.append(line)
        else:
            out_lines.append("")
    return "\n".join(out_lines)


def _strip_commands_and_math(text: str) -> str:
    t = _strip_code_like_envs(text)
    t = _MATH_ENV_RE.sub("", t)
    t = re.sub(r"\\\[(.|\n)*?\\\]", "", t)
    t = re.sub(r"\\\((.|\n)*?\\\)", "", t)
    t = re.sub(r"\$(?:\\\$|[^\$])*\$", "", t)
    t = re.sub(r"\\[a-zA-Z@]+\\*?", "", t)
    t = re.sub(r"\\.", "", t)
    return t


def count_cjk_chars(tex_text: str, *, mode: str = "cjk_only") -> WordCountResult:
    text = strip_comments(tex_text)
    m = str(mode or "").strip().lower()
    if m == "cjk_strip_commands":
        text = _strip_commands_and_math(text)
    return WordCountResult(cjk_count=len(_CJK_CHAR_RE.findall(text)))
