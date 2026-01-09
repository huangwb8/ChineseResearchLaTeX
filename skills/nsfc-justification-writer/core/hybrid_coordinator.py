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
from .errors import MissingCitationKeysError
from .editor import ApplyResult, apply_new_content
from .example_matcher import format_example_recommendations, recommend_examples
from .latex_parser import replace_subsubsection_body
from .observability import Observability, ensure_run_dir, make_run_id
from .reference_validator import check_citations
from .security import build_write_policy, resolve_target_path, validate_write_target
from .term_consistency import CrossChapterValidator, format_term_matrices_markdown
from .wordcount import count_cjk_chars
from .prompt_templates import get_prompt, TIER2_DIAGNOSTIC_PROMPT
from .review_advice import generate_review_markdown
from .writing_coach import coach_markdown


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
        tex = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
        tier1 = run_tier1(tex_text=tex, project_root=project_root, config=self.config)
        report = DiagnosticReport(tier1=tier1, tier2=None, notes=[])
        self.obs.add("diagnose.tier1", **report.to_dict()["tier1"])

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
            )
            ai_cfg = self.config.get("ai", {}) or {}
            max_chars = int(tier2_chunk_size or ai_cfg.get("tier2_chunk_size", 12000))
            max_chunks = int(tier2_max_chunks or ai_cfg.get("tier2_max_chunks", 20))
            cache_dir = (self.skill_root / str(ai_cfg.get("cache_dir", ".cache/ai"))).resolve()

            chunks = _split_tex_by_subsubsection(tex, max_chars=max_chars)
            if max_chunks > 0 and len(chunks) > max_chunks:
                report.notes.append(f"Tier2 分块过多：仅处理前 {max_chunks}/{len(chunks)} 块（可调 --chunk-size/--max-chunks）")
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

        terminology_cfg = self.config.get("terminology", {}) or {}
        validator = CrossChapterValidator(files=files, terminology_config=terminology_cfg)
        mats = validator.build()
        issues = sum(len(m.issues) for m in mats.values())
        rows = sum(len(m.rows) for m in mats.values())
        self.obs.add("terms.matrix", dims=len(mats), issues=issues, rows=rows)
        return format_term_matrices_markdown(mats)

    def apply_section_body(
        self,
        *,
        project_root: Path,
        title: str,
        new_body: str,
        backup: bool = True,
        run_id: Optional[str] = None,
        allow_missing_citations: bool = False,
    ) -> ApplyResult:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        policy = build_write_policy(self.config)
        validate_write_target(project_root=project_root, target_path=target, policy=policy)

        src = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
        new_text, changed = replace_subsubsection_body(src, title, new_body)
        if not changed:
            return ApplyResult(changed=False, target_path=target, backup_path=None)

        ref_cfg = (self.config.get("references", {}) or {})
        allow_missing = bool(ref_cfg.get("allow_missing_citations", False)) or bool(allow_missing_citations)
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
        self.obs.add("apply.section", title=title, changed=result.changed)
        if result.backup_path:
            self.obs.add("apply.backup", path=str(result.backup_path))
        return result

    def word_count_status(self, *, project_root: Path) -> Dict[str, Any]:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        tex = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
        current = count_cjk_chars(tex).cjk_count
        wc_cfg = self.config.get("word_count", {}) or {}
        target_n = int(wc_cfg.get("target", 4000))
        tol = int(wc_cfg.get("tolerance", 200))
        status = "within_tolerance" if abs(current - target_n) <= tol else ("need_expand" if current < target_n else "need_compress")
        self.obs.add("wordcount", current=current, target=target_n, tolerance=tol, status=status)
        return {
            "current": current,
            "target": target_n,
            "tolerance": tol,
            "status": status,
            "delta": current - target_n,
        }

    def recommend_examples(self, *, query: str, top_k: int = 3) -> str:
        matches = recommend_examples(skill_root=self.skill_root, query=query, top_k=top_k)
        return format_example_recommendations(matches)

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
        tex = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
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
