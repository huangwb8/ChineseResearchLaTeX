#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .config_access import get_mapping, get_str
from .config_loader import get_runs_dir, load_config
from .diagnostic import DiagnosticReport, format_tier1, run_tier1
from .io_utils import read_text_streaming
from .observability import Observability
from .security import choose_target_relpath, discover_target_candidates, resolve_target_path, validate_target_file
from .wordcount import count_cjk_chars, describe_word_count_mode
from .word_target import resolve_word_target


@dataclass(frozen=True)
class CoordinatorPaths:
    skill_root: Path
    runs_root: Path


class HybridCoordinator:
    def __init__(
        self,
        *,
        skill_root: Path,
        config: Optional[Dict[str, Any]] = None,
        observability: Optional[Observability] = None,
    ) -> None:
        self.skill_root = Path(skill_root).resolve()
        self.config = config or load_config(self.skill_root)
        self.obs = observability or Observability()
        self.paths = CoordinatorPaths(skill_root=self.skill_root, runs_root=get_runs_dir(self.skill_root, self.config))

    def _target_relpath(self, project_root: Optional[Path] = None) -> str:
        targets = get_mapping(self.config, "targets")
        configured = get_str(targets, "justification_tex", "").strip()
        if configured:
            return configured
        if project_root is not None:
            candidates = discover_target_candidates(project_root)
            return choose_target_relpath(project_root, candidates)
        return "extraTex/1.1.立项依据.tex"

    def _resolve_target(self, project_root: Path) -> Path:
        return validate_target_file(
            project_root=project_root,
            target_path=resolve_target_path(project_root, self._target_relpath(project_root)),
            require_exists=False,
        )

    def target_path(self, *, project_root: Path) -> Path:
        return self._resolve_target(Path(project_root).resolve())

    def diagnose(
        self,
        *,
        project_root: Path,
        include_tier2: bool = True,
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
                except (OSError, UnicodeError):
                    continue
        word_spec = resolve_word_target(config=self.config, user_intent_text="", info_form_text=info_form_text)
        tier1 = run_tier1(tex_text=tex, project_root=project_root, config=self.config)
        report = DiagnosticReport(
            tier1=tier1,
            tier2=None,
            word_target={"target": word_spec.target, "tolerance": word_spec.tolerance, "source": word_spec.source, "evidence": word_spec.evidence},
            notes=[],
        )
        self.obs.add("diagnose.tier1", **report.to_dict()["tier1"])

        report.notes.append(
            "机器检查已完成；写入前由当前宿主 AI 按 references/quality_control.md 做一次语义审查。"
        )
        return report

    def format_diagnose(self, report: DiagnosticReport) -> str:
        out = ["诊断结果：", format_tier1(report.tier1).rstrip()]
        if report.word_target:
            tgt = report.word_target
            src = tgt.get("source", "")
            ev = tgt.get("evidence", "")
            out.append(f"- 🎯 目标字数：{tgt.get('target')}（容差 ±{tgt.get('tolerance')}，来源：{src}{'，线索：'+ev if ev else ''}）")
        if report.tier2:
            out.append("")
            out.append("语义审查（宿主 AI）：")
            for k in ["logic", "terminology", "evidence", "readability", "suggestions"]:
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

    def word_count_status(self, *, project_root: Path, mode: Optional[str] = None) -> Dict[str, Any]:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        tex = read_text_streaming(target).text if target.exists() else ""
        wc_cfg = get_mapping(self.config, "word_count")
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
                except (OSError, UnicodeError):
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
