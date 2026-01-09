#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass

from .latex_parser import strip_comments


_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")


@dataclass(frozen=True)
class WordCountResult:
    cjk_count: int


def count_cjk_chars(tex_text: str) -> WordCountResult:
    text = strip_comments(tex_text)
    return WordCountResult(cjk_count=len(_CJK_CHAR_RE.findall(text)))
