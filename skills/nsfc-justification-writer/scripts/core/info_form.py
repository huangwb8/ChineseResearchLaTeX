#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class InfoFormAnswers:
    research_object: str
    pain_points: str
    core_hypothesis: str
    key_questions: str
    entry_point: str
    methods_overview: str = ""
    prior_work: str = ""
    related_work: str = ""
    extra: str = ""

    def to_markdown(self, *, version: str) -> str:
        lines = [
            f"# NSFC 写作信息表（{version}）",
            "",
            "## 必填",
            f"1. **研究对象/应用场景**：{self.research_object.strip()}",
            "2. **痛点与现有不足**：",
            self._indent_block(self.pain_points),
            "3. **关键科学问题（疑问句，非研究目标）**：",
            self._indent_block(self.key_questions),
            f"4. **核心科学假设（陈述句，预测性结果，不写验证方式）**：{self.core_hypothesis.strip()}",
            "5. **本项目切入点（差异化切口）**：",
            self._indent_block(self.entry_point),
            "",
            "## 选填",
            "6. **拟解决技术/方法概览**：",
            self._indent_block(self.methods_overview),
            "7. **前期基础（可核验）**：",
            self._indent_block(self.prior_work),
            "8. **主流路线与代表工作（引用先核验）**：",
            self._indent_block(self.related_work),
        ]
        if self.extra.strip():
            lines += ["", "## 可选补充", self._indent_block(self.extra)]
        return "\n".join([x.rstrip() for x in lines]).strip() + "\n"

    @staticmethod
    def _indent_block(text: str) -> str:
        t = (text or "").strip()
        if not t:
            return "   - （留空）"
        if "\n" not in t:
            return f"   - {t}"
        return "\n".join([("   - " + line if i == 0 else "     " + line) for i, line in enumerate(t.splitlines())])


def _ask(prompt: str, *, required: bool, multiline: bool) -> str:
    while True:
        if not multiline:
            ans = input(prompt).strip()
            if ans or (not required):
                return ans
            print("❗该项为必填，请补充。")
            continue

        print(prompt.rstrip())
        print("（可输入多行，空行结束）")
        buf = []
        while True:
            line = input()
            if line == "":
                break
            buf.append(line)
        ans = "\n".join(buf).strip()
        if ans or (not required):
            return ans
        print("❗该项为必填，请补充。")


def interactive_collect_info_form() -> InfoFormAnswers:
    research_object = _ask("1) 研究对象/应用场景（一句话边界）：", required=True, multiline=False)
    pain_points = _ask(
        "2) 痛点与现有不足（建议包含 2–4 条关键瓶颈，并尽量给出“瓶颈→问题约束”的映射）：",
        required=True,
        multiline=True,
    )
    key_questions = _ask(
        "3) 关键科学问题（1–3 条；疑问句；避免“能否构建/开发/实现...”这类研究目标句式）：",
        required=True,
        multiline=True,
    )
    core_hypothesis = _ask(
        "4) 核心科学假设（1 句可证伪陈述；预测性结果；避免“在...验证中/通过...验证”）：",
        required=True,
        multiline=False,
    )
    entry_point = _ask("5) 本项目切入点（差异化切口，怎么破局；并用 1 句承上启下到 2.1 研究内容）：", required=True, multiline=True)
    methods_overview = _ask("6) 拟解决技术/方法概览（选填）：", required=False, multiline=True)
    prior_work = _ask("7) 前期基础（可核验）（选填）：", required=False, multiline=True)
    related_work = _ask("8) 主流路线与代表工作（选填；引用先核验）：", required=False, multiline=True)
    extra = _ask("可选补充（字数限制/术语口径等，选填）：", required=False, multiline=True)
    return InfoFormAnswers(
        research_object=research_object,
        pain_points=pain_points,
        core_hypothesis=core_hypothesis,
        key_questions=key_questions,
        entry_point=entry_point,
        methods_overview=methods_overview,
        prior_work=prior_work,
        related_work=related_work,
        extra=extra,
    )


def write_info_form_file(*, out_path: Path, answers: InfoFormAnswers, version: str) -> None:
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(answers.to_markdown(version=version), encoding="utf-8")


def copy_info_form_template(*, template_path: Path, out_path: Path) -> bool:
    template_path = Path(template_path).resolve()
    out_path = Path(out_path).resolve()
    if not template_path.is_file():
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template_path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return True
