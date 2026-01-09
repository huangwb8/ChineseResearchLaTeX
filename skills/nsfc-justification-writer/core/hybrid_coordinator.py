#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ai_integration import AIIntegration
from .config_loader import get_runs_dir, load_config
from .diagnostic import DiagnosticReport, format_tier1, run_tier1
from .errors import MissingCitationKeysError, SectionNotFoundError, TargetFileNotFoundError
from .editor import ApplyResult, apply_new_content
from .dimension_coverage import DimensionCoverageAI, format_dimension_coverage_markdown
from .example_matcher import recommend_examples_markdown
from .io_utils import iter_text_chunks_by_subsubsection_mark, read_text_streaming
from .latex_parser import match_title_via_ai, replace_subsubsection_body_hybrid, suggest_titles
from .observability import Observability, ensure_run_dir, make_run_id
from .boastful_expression_checker import BoastfulExpressionAI
from .reference_validator import check_citations
from .security import build_write_policy, resolve_target_path, validate_write_target
from .term_consistency import term_consistency_report
from .wordcount import count_cjk_chars, describe_word_count_mode
from .prompt_templates import get_prompt, TIER2_DIAGNOSTIC_PROMPT
from .review_advice import generate_review_markdown
from .writing_coach import coach_markdown
from .quality_gate import check_new_body_quality
from .word_target import resolve_word_target


@dataclass(frozen=True)
class CoordinatorPaths:
    skill_root: Path
    runs_root: Path


_SUBSUBSECTION_MARK = re.compile(r"\\subsubsection\s*\{")


def _split_tex_by_subsubsection(tex: str, *, max_chars: int) -> List[str]:
    if max_chars <= 0:
        return [tex]
    if len(tex) <= max_chars:
        return [tex]

    starts = [m.start() for m in _SUBSUBSECTION_MARK.finditer(tex)]
    if not starts:
        # 无结构可分，就按长度硬切
        return [tex[i : i + max_chars] for i in range(0, len(tex), max_chars)]

    blocks: List[str] = []
    if starts[0] > 0:
        blocks.append(tex[: starts[0]])
    for i, s in enumerate(starts):
        e = starts[i + 1] if (i + 1) < len(starts) else len(tex)
        blocks.append(tex[s:e])

    chunks: List[str] = []
    cur = ""
    for b in blocks:
        if not b:
            continue
        if (len(cur) + len(b) > max_chars) and cur:
            chunks.append(cur)
            cur = b
        else:
            cur += b
        if len(cur) > max_chars:
            # 单块过大：继续硬切
            chunks.extend([cur[i : i + max_chars] for i in range(0, len(cur), max_chars)])
            cur = ""
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c.strip()] or [tex[:max_chars]]


class HybridCoordinator:
    def __init__(
        self,
        *,
        skill_root: Path,
        config: Optional[Dict[str, Any]] = None,
        ai_integration: Optional[AIIntegration] = None,
        observability: Optional[Observability] = None,
    ) -> None:
        self.skill_root = Path(skill_root).resolve()
        self.config = config or load_config(self.skill_root)
        ai_cfg = self.config.get("ai", {}) or {}
        self.ai = ai_integration or AIIntegration(enable_ai=bool(ai_cfg.get("enabled", True)), config=self.config)
        self.obs = observability or Observability()
        self.paths = CoordinatorPaths(skill_root=self.skill_root, runs_root=get_runs_dir(self.skill_root, self.config))

    def _target_relpath(self) -> str:
        targets = self.config.get("targets", {}) or {}
        return str(targets.get("justification_tex", "extraTex/1.1.立项依据.tex"))

    def _resolve_target(self, project_root: Path) -> Path:
        return resolve_target_path(project_root, self._target_relpath())

    def target_path(self, *, project_root: Path) -> Path:
        return self._resolve_target(Path(project_root).resolve())

    def diagnose(
        self,
        *,
        project_root: Path,
        include_tier2: bool = False,
        tier2_chunk_size: Optional[int] = None,
        tier2_max_chunks: Optional[int] = None,
        tier2_fresh: bool = False,
    ) -> DiagnosticReport:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        tex = read_text_streaming(target).text if target.exists() else ""
        info_form_text = ""
        for candidate in [
            project_root / "info_form.md",
            project_root / "references" / "info_form.md",
        ]:
            if candidate.exists():
                try:
                    info_form_text = candidate.read_text(encoding="utf-8", errors="ignore")
                    break
                except Exception:
                    continue
        word_spec = resolve_word_target(config=self.config, user_intent_text="", info_form_text=info_form_text)
        tier1 = run_tier1(tex_text=tex, project_root=project_root, config=self.config)
        report = DiagnosticReport(
            tier1=tier1,
            tier2=None,
            dimension_coverage=None,
            boastful_expressions=None,
            word_target={"target": word_spec.target, "tolerance": word_spec.tolerance, "source": word_spec.source, "evidence": word_spec.evidence},
            notes=[],
        )
        self.obs.add("diagnose.tier1", **report.to_dict()["tier1"])

        ai_cfg = self.config.get("ai", {}) or {}
        cache_dir = (self.skill_root / str(ai_cfg.get("cache_dir", ".cache/ai"))).resolve()

        # 内容维度覆盖检查（AI 不可用时自动回退启发式）
        if (self.config.get("structure", {}) or {}).get("enable_dimension_coverage_check", False):
            try:
                report.dimension_coverage = asyncio.run(DimensionCoverageAI(self.ai).check(tex_text=tex, cache_dir=cache_dir, fresh=bool(tier2_fresh)))
            except Exception:
                report.dimension_coverage = None

        # 吹牛式表述检查（AI 语义判断）
        quality_cfg = self.config.get("quality", {}) or {}
        if quality_cfg.get("enable_ai_judgment", True):
            try:
                report.boastful_expressions = asyncio.run(
                    BoastfulExpressionAI(self.ai).check(tex_text=tex, cache_dir=cache_dir, fresh=bool(tier2_fresh))
                )
            except Exception:
                report.boastful_expressions = None

        if not include_tier2:
            return report

        if not tier1.structure_ok:
            report.notes.append("结构缺失：已跳过 Tier2（避免浪费 AI 资源）")
            return report

        async def _run() -> Optional[Dict[str, Any]]:
            tpl = get_prompt(
                name="tier2_diagnostic",
                default=TIER2_DIAGNOSTIC_PROMPT,
                skill_root=self.skill_root,
                config=self.config,
                variant=str(self.config.get("active_preset", "") or "").strip() or None,
            )
            max_chars = int(tier2_chunk_size or ai_cfg.get("tier2_chunk_size", 12000))
            max_chunks = int(tier2_max_chunks or ai_cfg.get("tier2_max_chunks", 20))
            chunks: List[str]
            # 超大文件：优先流式分块，避免一次性加载后再切块造成峰值内存
            if target.exists() and int(target.stat().st_size) > 5 * 1024 * 1024:
                chunks = list(
                    iter_text_chunks_by_subsubsection_mark(
                        target,
                        max_chars=max_chars,
                        max_chunks=max_chunks if max_chunks > 0 else 10**9,
                    )
                )
            else:
                chunks = _split_tex_by_subsubsection(tex, max_chars=max_chars)
                if max_chunks > 0 and len(chunks) > max_chunks:
                    report.notes.append(
                        f"Tier2 分块过多：仅处理前 {max_chunks}/{len(chunks)} 块（可调 --chunk-size/--max-chunks）"
                    )
                    chunks = chunks[:max_chunks]

            def _fallback() -> Dict[str, Any]:
                return {
                    "logic": [],
                    "terminology": [],
                    "evidence": [],
                    "suggestions": ["AI 不可用：仅完成 Tier1 硬编码诊断。"],
                }

            merged: Dict[str, Any] = {"logic": [], "terminology": [], "evidence": [], "suggestions": []}
            for i, ch in enumerate(chunks):
                prompt = tpl.format(tex=ch)
                obj = await self.ai.process_request(
                    task=f"diagnose_tier2_chunk_{i+1}",
                    prompt=prompt,
                    fallback=_fallback,
                    output_format="json",
                    cache_dir=cache_dir,
                    fresh=bool(tier2_fresh),
                )
                if not isinstance(obj, dict):
                    continue
                for k in ["logic", "terminology", "evidence", "suggestions"]:
                    v = obj.get(k)
                    if not v:
                        continue
                    if isinstance(v, list):
                        merged[k].extend([str(x) for x in v if str(x).strip()])
                    else:
                        merged[k].append(str(v).strip())

            # 去重但保序
            for k in ["logic", "terminology", "evidence", "suggestions"]:
                seen = set()
                uniq: List[str] = []
                for it in merged[k]:
                    if it in seen:
                        continue
                    seen.add(it)
                    uniq.append(it)
                merged[k] = uniq

            return merged

        report.tier2 = asyncio.run(_run())
        self.obs.add("diagnose.tier2", enabled=self.ai.is_available())
        return report

    def format_diagnose(self, report: DiagnosticReport) -> str:
        out = ["诊断结果：", format_tier1(report.tier1).rstrip()]
        if report.word_target:
            tgt = report.word_target
            src = tgt.get("source", "")
            ev = tgt.get("evidence", "")
            out.append(f"- 🎯 目标字数：{tgt.get('target')}（容差 ±{tgt.get('tolerance')}，来源：{src}{'，线索：'+ev if ev else ''}）")
        if report.dimension_coverage:
            out.append("")
            out.append("内容维度覆盖（价值/现状/科学问题/切入点）：")
            out.append(format_dimension_coverage_markdown(report.dimension_coverage).rstrip())
        if report.boastful_expressions:
            issues = report.boastful_expressions.get("issues", []) if isinstance(report.boastful_expressions, dict) else []
            if issues:
                out.append("")
                out.append("可能引起评审不适的表述（AI 语义判断）：")
                for it in issues[:6]:
                    if not isinstance(it, dict):
                        continue
                    cat = str(it.get("category", "") or "")
                    txt = str(it.get("text", "") or "")
                    reason = str(it.get("reason", "") or "")
                    out.append(f"- [{cat}] {txt}")
                    if reason:
                        out.append(f"  - 原因：{reason}")
        if report.tier2:
            out.append("")
            out.append("Tier2（AI 语义分析）：")
            for k in ["logic", "terminology", "evidence", "suggestions"]:
                v = report.tier2.get(k) if isinstance(report.tier2, dict) else None
                if not v:
                    continue
                out.append(f"- {k}:")
                if isinstance(v, list):
                    for item in v[:10]:
                        out.append(f"  - {item}")
                else:
                    out.append(f"  - {v}")
        if report.notes:
            out.append("")
            out.append("备注：")
            for n in report.notes:
                out.append(f"- {n}")
        return "\n".join(out).strip() + "\n"

    def term_consistency_report(self, *, project_root: Path) -> str:
        project_root = Path(project_root).resolve()
        targets = self.config.get("targets", {}) or {}
        related = targets.get("related_tex", {}) or {}

        files = {
            "立项依据": resolve_target_path(project_root, self._target_relpath()),
        }
        for label, relpath in related.items():
            files[label] = resolve_target_path(project_root, str(relpath))

        ai_cfg = self.config.get("ai", {}) or {}
        cache_dir = (self.skill_root / str(ai_cfg.get("cache_dir", ".cache/ai"))).resolve()
        md = term_consistency_report(files=files, config=self.config, ai=self.ai, cache_dir=cache_dir)
        self.obs.add("terms.report", ai=self.ai.is_available())
        return md

    def apply_section_body(
        self,
        *,
        project_root: Path,
        title: str,
        new_body: str,
        backup: bool = True,
        run_id: Optional[str] = None,
        allow_missing_citations: bool = False,
        strict_quality: bool = False,
    ) -> ApplyResult:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        policy = build_write_policy(self.config)
        validate_write_target(project_root=project_root, target_path=target, policy=policy)
        if not target.exists():
            raise TargetFileNotFoundError(target_relpath=self._target_relpath(), project_root=str(project_root))

        src = read_text_streaming(target).text
        structure_cfg = self.config.get("structure", {}) or {}
        strict = bool(structure_cfg.get("strict_title_match", True))
        min_sim = float(structure_cfg.get("min_title_similarity", 0.6))

        # strict=False 时：先做“候选标题提示”，并在 AI 可用时尝试语义匹配
        chosen = title
        if not strict:
            cands = suggest_titles(src, query=title, limit=30)
            if self.ai.is_available() and cands:
                ai_cfg = self.config.get("ai", {}) or {}
                cache_dir = (self.skill_root / str(ai_cfg.get("cache_dir", ".cache/ai"))).resolve()
                matched = asyncio.run(match_title_via_ai(query=title, candidates=cands, ai=self.ai, cache_dir=cache_dir))
                if matched:
                    chosen = matched

        new_text, changed, matched_title = replace_subsubsection_body_hybrid(
            src,
            title=chosen,
            new_body=new_body,
            strict=strict,
            min_similarity=min_sim,
        )
        if not changed:
            raise SectionNotFoundError(title=title, suggestions=suggest_titles(src, query=title, limit=12))

        ref_cfg = (self.config.get("references", {}) or {})
        allow_missing = bool(ref_cfg.get("allow_missing_citations", False)) or bool(allow_missing_citations)

        quality_cfg = self.config.get("quality", {}) or {}
        strict_on_apply = bool(quality_cfg.get("strict_on_apply", False)) or bool(strict_quality)
        if strict_on_apply:
            ai_cfg = self.config.get("ai", {}) or {}
            cache_dir = (self.skill_root / str(ai_cfg.get("cache_dir", ".cache/ai"))).resolve()
            qr = check_new_body_quality(new_body=new_body, config=self.config, ai=self.ai, cache_dir=cache_dir)
            if not qr.ok:
                from .errors import QualityGateError

                raise QualityGateError(
                    forbidden_phrases=qr.forbidden_phrases_hits,
                    avoid_commands=qr.avoid_commands_hits,
                )

        if not allow_missing:
            targets = self.config.get("targets", {}) or {}
            bib_globs = targets.get("bib_globs", ["references/*.bib"])
            cite_result = check_citations(tex_text=new_text, project_root=project_root, bib_globs=bib_globs)
            if cite_result.missing_keys:
                raise MissingCitationKeysError(cite_result.missing_keys)

        run_id = run_id or make_run_id("apply")
        run_dir = ensure_run_dir(self.paths.runs_root, run_id)
        backup_root = (run_dir / "backup").resolve() if backup else None
        result = apply_new_content(target_path=target, new_text=new_text, backup_root=backup_root, run_id=run_id)
        self.obs.add("apply.section", title=str(matched_title or title), changed=result.changed)
        if result.backup_path:
            self.obs.add("apply.backup", path=str(result.backup_path))
        return result

    def word_count_status(self, *, project_root: Path, mode: Optional[str] = None) -> Dict[str, Any]:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        tex = read_text_streaming(target).text if target.exists() else ""
        wc_cfg = self.config.get("word_count", {}) or {}
        used_mode = str(mode or wc_cfg.get("mode", "cjk_only")).strip() or "cjk_only"
        current = count_cjk_chars(tex, mode=used_mode).cjk_count

        info_form_text = ""
        for candidate in [
            project_root / "info_form.md",
            project_root / "references" / "info_form.md",
        ]:
            if candidate.exists():
                try:
                    info_form_text = candidate.read_text(encoding="utf-8", errors="ignore")
                    break
                except Exception:
                    continue

        word_spec = resolve_word_target(
            config=self.config,
            user_intent_text="",
            info_form_text=info_form_text,
        )
        target_n = int(word_spec.target)
        tol = int(word_spec.tolerance)
        status = "within_tolerance" if abs(current - target_n) <= tol else ("need_expand" if current < target_n else "need_compress")
        self.obs.add("wordcount", current=current, target=target_n, tolerance=tol, status=status)
        return {
            "current": current,
            "mode": used_mode,
            "mode_definition": describe_word_count_mode(used_mode),
            "target": target_n,
            "tolerance": tol,
            "source": word_spec.source,
            "evidence": word_spec.evidence,
            "status": status,
            "delta": current - target_n,
        }

    def recommend_examples(self, *, query: str, top_k: int = 3) -> str:
        ai_cfg = self.config.get("ai", {}) or {}
        cache_dir = (self.skill_root / str(ai_cfg.get("cache_dir", ".cache/ai"))).resolve()
        return recommend_examples_markdown(skill_root=self.skill_root, query=query, top_k=top_k, ai=self.ai, cache_dir=cache_dir)

    def coach(self, *, project_root: Path, stage: str = "auto", info_form_text: str = "") -> str:
        return asyncio.run(
            coach_markdown(
                skill_root=self.skill_root,
                project_root=Path(project_root),
                config=self.config,
                stage=stage,  # type: ignore[arg-type]
                info_form_text=info_form_text,
                ai=self.ai,
            )
        )

    def reviewer_advice(
        self,
        *,
        project_root: Path,
        include_tier2: bool = False,
        tier2_chunk_size: Optional[int] = None,
        tier2_max_chunks: Optional[int] = None,
        tier2_fresh: bool = False,
    ) -> str:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        tex = read_text_streaming(target).text if target.exists() else ""
        report = self.diagnose(
            project_root=project_root,
            include_tier2=include_tier2,
            tier2_chunk_size=tier2_chunk_size,
            tier2_max_chunks=tier2_max_chunks,
            tier2_fresh=tier2_fresh,
        )
        return asyncio.run(
            generate_review_markdown(
                skill_root=self.skill_root,
                config=self.config,
                report=report,
                tex_text=tex,
                ai=self.ai,
            )
        )
