#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ai_integration import AIIntegration
from .config_access import get_bool, get_mapping, get_str
from .diagnostic import DiagnosticReport
from .prompt_templates import get_prompt


def _load_dod_checklist(skill_root: Path) -> str:
    p = (Path(skill_root).resolve() / "references" / "dod_checklist.md").resolve()
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore").strip()


def _fallback_review_markdown(*, report: DiagnosticReport, dod_checklist: str) -> str:
    t1 = report.tier1
    qs: List[str] = [
        "你的一句话问题定义是否让“非本细分领域评审”也能理解？",
        "现有方案的瓶颈是否是 2–4 条“可量化/可验证”的不足，而不是口号？",
        "核心假说是否可证伪，且对应的关键科学问题是否一一映射？",
        "项目切入点是否明确“差异化切口 + 验证指标 + 对照维度”？",
        "是否自然承上启下到 2.1 研究内容（而不是戛然而止）？",
        "是否存在不可核验绝对表述（国际领先/国内首次等）？如有，如何改成可验证指标？",
        "引用是否都可追溯（bibkey 存在且来源可核验）？",
        "术语/缩写/指标口径是否与 2.1/3.1 一致？",
    ]
    if not t1.structure_ok:
        qs.insert(0, "四个 \\subsubsection 是否齐全，标题是否与模板一致？")
    if not t1.citation_ok:
        qs.insert(0, f"缺失引用 keys：{', '.join(t1.missing_citation_keys[:10])}（是否需要补 bib 或删除未核验引用）？")

    adv: List[str] = []
    if not t1.structure_ok:
        adv.append("先补齐 4 个小标题骨架（研究背景/现状/局限/切入点），再写正文。")
    if not t1.citation_ok:
        adv.append("修复所有缺失 bibkey：提供 DOI/链接或用 nsfc-bib-manager 核验后写入 \\cite{...}。")
    if t1.forbidden_phrases_hits:
        adv.append("删除“国际领先/国内首次/填补空白”等表述，改为“对照维度 + 指标 + 改善幅度/区间”。")
    if t1.avoid_commands_hits:
        adv.append("移除 \\section/\\subsection/\\input/\\include 等命令，避免破坏模板。")
    adv.append("每段都补一个“可验证锚点”：数据来源/指标定义/对照组/消融实验/统计检验。")
    adv.append("在“研究切入点”末尾加 1 句过渡：引出 2.1 的研究内容与技术路线。")

    md = [
        "# 评审人视角质疑与建议（自动生成）",
        "",
        "## DoD 复核要点",
        dod_checklist.strip() if dod_checklist.strip() else "（未找到 dod_checklist.md）",
        "",
        "## 评审人可能会问的问题",
        "",
    ] + [f"- {q}" for q in qs[:12]] + [
        "",
        "## 对应的可执行修改建议",
        "",
    ] + [f"- {a}" for a in adv[:12]]
    return "\n".join(md).strip() + "\n"


async def generate_review_markdown(
    *,
    skill_root: Path,
    config: Dict[str, Any],
    report: DiagnosticReport,
    tex_text: str,
    ai: Optional[AIIntegration] = None,
) -> str:
    skill_root = Path(skill_root).resolve()
    dod_checklist = _load_dod_checklist(skill_root)

    ai_obj = ai
    if ai_obj is None:
        ai_cfg = get_mapping(config, "ai")
        ai_obj = AIIntegration(enable_ai=get_bool(ai_cfg, "enabled", True), config=config)

    prompt = get_prompt(
        name="review_suggestions",
        default="",
        skill_root=skill_root,
        config=config,
        variant=get_str(config, "active_preset", "").strip() or None,
    )

    def _fallback() -> str:
        return _fallback_review_markdown(report=report, dod_checklist=dod_checklist)

    if not prompt.strip():
        return _fallback()

    t1_json = json.dumps(report.to_dict().get("tier1", {}), ensure_ascii=False, indent=2)
    filled = prompt.format(
        dod_checklist=dod_checklist,
        tier1_json=t1_json,
        tex=(tex_text or "")[:12000],
    )
    obj = await ai_obj.process_request(task="review_suggestions", prompt=filled, fallback=_fallback, output_format="text")
    return str(obj).strip() + "\n"
