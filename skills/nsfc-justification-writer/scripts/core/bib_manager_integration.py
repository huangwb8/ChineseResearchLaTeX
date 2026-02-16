#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class BibFixSuggestion:
    missing_bibkeys: List[str]
    missing_doi_keys: List[str]
    invalid_doi_keys: List[str]

    def to_markdown(self, *, project_root: str) -> str:
        lines = [
            "# 引用核验建议（手动补齐 BibTeX）",
            "",
            "说明：本工具不会自动联网补齐引用，但会生成一段“可直接复制”的提示词，帮助你（或任意 BibTeX 工具/助手）完成核验与补齐。",
            "",
        ]
        if self.missing_bibkeys:
            lines += [
                "## 缺失的 bibkey（LaTeX 中引用了，但 .bib 没有）",
                "",
            ] + [f"- {k}" for k in self.missing_bibkeys]
        if self.missing_doi_keys:
            lines += [
                "",
                "## DOI 缺失的条目（.bib 有该 key，但缺 doi 字段，建议补齐以便可核验）",
                "",
            ] + [f"- {k}" for k in self.missing_doi_keys]
        if self.invalid_doi_keys:
            lines += [
                "",
                "## DOI 疑似不合法的条目（.bib 有 doi 字段，但格式看起来不对，建议核验）",
                "",
            ] + [f"- {k}" for k in self.invalid_doi_keys]

        lines += [
            "",
            "## 可直接复制的提示词（用于核验与补齐）",
            "```",
            "请帮我核验并补齐参考文献条目：",
            f"目标项目：{project_root}",
            "任务：核验并补齐参考文献条目，确保不出现幻觉引用。",
        ]
        if self.missing_bibkeys:
            lines += [
                "需要新增/补齐的 bibkey：",
                ", ".join(self.missing_bibkeys),
                "说明：这些 key 在 tex 里被 \\cite{...} 使用，但当前 .bib 未找到。请让我提供 DOI/链接/题录信息后再写入，或提示我补充缺失信息。",
            ]
        if self.missing_doi_keys:
            lines += [
                "需要补 DOI 的 bibkey：",
                ", ".join(self.missing_doi_keys),
                "说明：这些 key 在 .bib 存在，但缺 doi 字段；请在不杜撰的前提下补齐 doi（如无法确定，请明确提示需要我提供 DOI/链接）。",
            ]
        if self.invalid_doi_keys:
            lines += [
                "需要核验/修正 DOI 的 bibkey：",
                ", ".join(self.invalid_doi_keys),
                "说明：这些 key 的 doi 字段疑似不合规（例如写成 URL/带多余字符/缺 10.x 前缀等）；请核验后修正为标准 DOI 格式（如无法确定，请明确提示需要我提供 DOI/链接）。",
            ]
        lines += [
            "输出：更新项目 references/*.bib（或你认为合适的 .bib），并给出每条的题目/作者/年份/期刊/DOI 核验结果；无法核验的条目请标注“待核验”。",
            "```",
        ]
        return "\n".join(lines).strip() + "\n"
