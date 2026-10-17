#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .config_access import get_mapping, get_str
from .config_loader import load_config
from .diagnostic import DiagnosticReport, format_diagnostic, run_checks
from .io_utils import read_text_streaming
from .observability import Observability
from .security import (
    choose_target_relpath,
    discover_target_candidates,
    resolve_target_path,
    validate_target_file,
)
from .wordcount import count_cjk_chars, describe_word_count_mode


class Coordinator:
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

    def diagnose(self, *, project_root: Path) -> DiagnosticReport:
        project_root = Path(project_root).resolve()
        target = self._resolve_target(project_root)
        tex = read_text_streaming(target).text if target.exists() else ""
        checks = run_checks(tex_text=tex, project_root=project_root, config=self.config)
        report = DiagnosticReport(
            checks=checks,
            notes=[],
        )
        self.obs.add("diagnose", **report.to_dict()["checks"])

        report.notes.append(
            "机器检查已完成；写入前由当前宿主 AI 按 references/quality_control.md 做一次语义审查。"
        )
        return report

    def format_diagnose(self, report: DiagnosticReport) -> str:
        out = ["诊断结果：", format_diagnostic(report.checks).rstrip()]
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

        status = "unconstrained"
        self.obs.add("wordcount", current=current, status=status)
        return {
            "current": current,
            "mode": used_mode,
            "mode_definition": describe_word_count_mode(used_mode),
            "status": status,
        }
