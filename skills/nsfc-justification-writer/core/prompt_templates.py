#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


INTENT_PARSE_PROMPT = """\
你是 NSFC 标书写作助手的“意图解析器”。

任务：把用户指令解析为 JSON，字段：
- action: expand|compress|rewrite|restructure|diagnose
- target: 目标段落/小标题（优先匹配 \\subsubsection 标题）
- focus: 关注点（可为空）
- constraints: 约束（可为空，例如 年份范围、字数、必须保留信息点）

要求：
- 只输出 JSON（不要解释）
- 若无法判断 action/target，请用 null，并说明 reason 字段

用户指令：
{instruction}
"""


TIER2_DIAGNOSTIC_PROMPT = """\
你是 NSFC 立项依据“语义诊断器”。请基于以下 LaTeX 文本，输出诊断要点（JSON）：

字段：
- logic: 逻辑连贯性问题（列表）
- terminology: 术语/缩写不一致问题（列表）
- evidence: 证据不足/不可量化陈述（列表）
- suggestions: 3-6 条可执行修改建议（列表）

要求：
- 只输出 JSON
- 不生成新的引用；若需要引用，请提示“需用户提供 DOI/链接或走 nsfc-bib-manager 核验”

LaTeX 文本：
{tex}
"""

