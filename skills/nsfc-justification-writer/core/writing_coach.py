#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .ai_integration import AIIntegration
from .diagnostic import run_tier1
from .io_utils import read_text_streaming
from .prompt_templates import get_prompt
from .term_consistency import CrossChapterValidator, format_term_matrices_markdown

WritingStage = Literal["auto", "skeleton", "draft", "revise", "polish", "final"]


@dataclass(frozen=True)
class CoachInput:
    stage: WritingStage
    info_form_text: str
    tex_text: str
    tier1: Dict[str, Any]
    term_matrix_md: str


def _infer_stage(*, tex_text: str, tier1: Dict[str, Any], word_target: int, tol: int) -> WritingStage:
    if not tex_text.strip():
        return "skeleton"
    if not bool(tier1.get("structure_ok")):
        return "skeleton"
    wc = int(tier1.get("word_count", 0))
    if wc < max(int(word_target * 0.4), 600):
        return "draft"
    if not bool(tier1.get("citation_ok")) or tier1.get("forbidden_phrases_hits") or tier1.get("avoid_commands_hits"):
        return "revise"
    if abs(wc - word_target) > tol:
        return "polish"
    return "final"


def _suggest_questions(*, stage: WritingStage, tier1: Dict[str, Any]) -> List[str]:
    base = [
        "你的一句话问题定义是什么（评审听得懂的版本）？",
        "现有方案的 2–4 条瓶颈分别是什么（尽量可量化）？",
        "你的核心假说是什么（能被验证/否证的一句话）？",
        "你准备如何验证（数据/指标/对照/消融）？",
        "本项目相对现有工作的差异化切口是什么？",
    ]
    if stage in {"skeleton", "draft"}:
        base.append("四个小标题是否要沿用模板默认（研究背景/现状/局限/切入点）？如要改标题，请明确新标题列表。")
    if not bool(tier1.get("citation_ok", True)):
        base.append("缺失引用的 bibkey 准备怎么补：提供 DOI/链接或走 nsfc-bib-manager 核验？")
    if tier1.get("missing_doi_keys"):
        base.append("已存在的引用 bibkey 是否补齐 DOI 字段（建议补齐以便可核验）？")
    if tier1.get("forbidden_phrases_hits"):
        base.append("是否有可验证指标/对照维度替代“国际领先/国内首次”等表述？")
    return base[:8]


def _copyable_prompt(*, stage: WritingStage) -> str:
    focus = {
        "skeleton": "先生成 4 个 \\subsubsection 骨架（不写引用）。",
        "draft": "只写其中 1 个 \\subsubsection 的正文段落（不新增引用）。",
        "revise": "只重写/压缩其中 1 个 \\subsubsection，修复逻辑跳跃与不可核验表述（不新增引用）。",
        "polish": "在不改变结构与事实点的前提下润色语言，强化“可验证指标/对照维度”（不新增引用）。",
        "final": "按 DoD 做最终自检：结构/字数/引用/术语一致性（不新增引用）。",
        "auto": "按当前阶段输出下一步。",
    }.get(stage, "按当前阶段输出下一步。")

    return (
        "请用 nsfc-justification-writer 的写作规范帮我修改立项依据：\n"
        "约束：\n"
        "- 不修改任何标题层级（仅改正文段落）\n"
        "- 不新增引用；如必须引用，请先提示“需用户提供 DOI/链接或走 nsfc-bib-manager 核验”\n"
        "- 避免不可核验绝对表述（国际领先/国内首次等），改为可验证指标/对照维度\n"
        f"任务：{focus}\n"
        "输入：我会提供（1）信息表（2）当前 tex（如有）。\n"
        "输出：只给出需要替换的正文文本（不要包裹 \\subsubsection）。\n"
    )


def _fallback_markdown(inp: CoachInput, stage: WritingStage) -> str:
    qs = _suggest_questions(stage=stage, tier1=inp.tier1)
    tasks = {
        "skeleton": [
            "补齐 4 个 \\subsubsection 标题骨架（先不追求字数）。",
            "每个小标题下先写 3–5 句“要点句”，不要堆引用。",
            "跑一遍 diagnose/terms，确认结构与术语口径。",
        ],
        "draft": [
            "选 1 个小标题先写成 1–2 段（每段 3–5 句）。",
            "每段都包含“可验证维度”（数据/指标/对照）。",
            "再逐小标题扩写到接近目标字数。",
        ],
        "revise": [
            "先修复缺失引用 key（或删掉未核验引用）。",
            "把不可核验表述改成“可对照维度 + 指标 + 预期改善幅度/区间”。",
            "统一术语/缩写口径，并与 2.1/3.1 对齐。",
        ],
        "polish": [
            "按字数目标做压缩/扩写（优先改“现状与不足/局限性”段落）。",
            "增强承上启下：研究切入点最后 1 句自然引到 2.1 研究内容。",
            "删除口号式句子，保留事实点与验证标准。",
        ],
        "final": [
            "最后跑一遍 diagnose（必要时开 tier2）并修复剩余问题。",
            "跑 terms 确认跨章节术语一致。",
            "确认输出只改 1.1 文件，且不含危险命令。",
        ],
    }.get(stage, ["按当前阶段推进。"])

    md = [
        "## 当前阶段判断",
        f"阶段：`{stage}`（可用 `scripts/run.py coach --stage ...` 强制指定）。",
        "",
        "## 本轮只做三件事",
        "1) " + tasks[0],
        "2) " + tasks[1],
        "3) " + tasks[2],
        "",
        "## 需要你补充/确认的问题（不超过 8 个）",
    ] + [f"- {q}" for q in qs] + [
        "",
        "## 下一步可直接复制的写作提示词",
        "```",
        _copyable_prompt(stage=stage).rstrip(),
        "```",
    ]
    return "\n".join(md).strip() + "\n"


async def coach_markdown(
    *,
    skill_root: Path,
    project_root: Path,
    config: Dict[str, Any],
    stage: WritingStage = "auto",
    info_form_text: str = "",
    ai: Optional[AIIntegration] = None,
) -> str:
    skill_root = Path(skill_root).resolve()
    project_root = Path(project_root).resolve()
    targets = config.get("targets", {}) or {}
    rel = str(targets.get("justification_tex", "extraTex/1.1.立项依据.tex"))
    target = (project_root / rel).resolve()
    tex_text = read_text_streaming(target).text if target.exists() else ""

    tier1_obj = run_tier1(tex_text=tex_text, project_root=project_root, config=config)
    tier1 = {
        "structure_ok": tier1_obj.structure_ok,
        "subsubsection_count": tier1_obj.subsubsection_count,
        "missing_subsubsections": tier1_obj.missing_subsubsections,
        "citation_ok": tier1_obj.citation_ok,
        "missing_citation_keys": tier1_obj.missing_citation_keys,
        "missing_doi_keys": tier1_obj.missing_doi_keys,
        "word_count": tier1_obj.word_count,
        "forbidden_phrases_hits": tier1_obj.forbidden_phrases_hits,
        "avoid_commands_hits": tier1_obj.avoid_commands_hits,
    }

    # 术语矩阵（尽量不失败）
    related = targets.get("related_tex", {}) or {}
    files = {"立项依据": target}
    for label, relpath in related.items():
        files[label] = (project_root / str(relpath)).resolve()
    terminology_cfg = config.get("terminology", {}) or {}
    term_matrix_md = format_term_matrices_markdown(CrossChapterValidator(files=files, terminology_config=terminology_cfg).build())

    wc_cfg = config.get("word_count", {}) or {}
    word_target = int(wc_cfg.get("target", 4000))
    tol = int(wc_cfg.get("tolerance", 200))

    auto_stage = _infer_stage(tex_text=tex_text, tier1=tier1, word_target=word_target, tol=tol)
    chosen_stage: WritingStage = auto_stage if stage == "auto" else stage

    inp = CoachInput(stage=chosen_stage, info_form_text=info_form_text, tex_text=tex_text, tier1=tier1, term_matrix_md=term_matrix_md)

    ai_obj = ai
    if ai_obj is None:
        ai_cfg = config.get("ai", {}) or {}
        ai_obj = AIIntegration(enable_ai=bool(ai_cfg.get("enabled", True)), config=config)

    prompt = get_prompt(
        name="writing_coach",
        default="",
        skill_root=skill_root,
        config=config,
        variant=str(config.get("active_preset", "") or "").strip() or None,
    )

    def _fallback() -> str:
        return _fallback_markdown(inp, chosen_stage)

    if not prompt.strip():
        return _fallback()

    payload = {
        "stage": chosen_stage,
        "info_form": (info_form_text or "").strip(),
        "tier1": tier1,
        "term_matrix": (term_matrix_md or "").strip(),
        "tex": (tex_text or "")[:12000],
    }
    filled = prompt.format(
        stage=chosen_stage,
        info_form=payload["info_form"],
        tier1_json=json.dumps(payload["tier1"], ensure_ascii=False, indent=2),
        term_matrix=payload["term_matrix"],
        tex=payload["tex"],
    )

    obj = await ai_obj.process_request(task="writing_coach", prompt=filled, fallback=_fallback, output_format="text")
    return str(obj).strip() + "\n"
