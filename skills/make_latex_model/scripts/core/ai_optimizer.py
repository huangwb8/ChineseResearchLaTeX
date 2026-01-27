#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 驱动优化引擎（最小可用版）

按照 plans/v202601271348.md 的“Analyzer → Reasoner → Executor → Memory”闭环落地：
- Analyzer：DiffAnalyzer（基于像素对比特征）
- Reasoner：DecisionReasoner（启发式 / 文件交互）
- Executor：ParameterExecutor（可回滚应用）
- Memory：HistoryMemory（JSONL 记录）

说明：
- 由于“脚本内部直连宿主 AI”缺少通用标准接口，本实现默认启发式；
  如需 AI 全程参与，可使用 DecisionReasoner 的 manual_file 模式。
"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .diff_analyzer import DiffAnalyzer
from .decision_reasoner import DecisionReasoner, ReasonerConfig
from .parameter_executor import ParameterExecutor, ExecutionResult
from .history_memory import HistoryMemory


class AIOptimizer:
    """AI 驱动的优化引擎"""

    def __init__(
        self,
        skill_root: Path,
        project_name: str,
        mode: str = "heuristic",
        evaluate_after_apply: bool = True,
    ):
        self.skill_root = Path(skill_root)
        self.project_name = project_name

        skill_cfg = self._load_skill_config()
        target_ratio = self._infer_target_ratio(skill_cfg)
        default_steps = self._infer_default_steps(skill_cfg)

        self.analyzer = DiffAnalyzer()

        prompt_path = self.skill_root / "prompts" / "analysis_template.txt"
        ws_dir = self.skill_root / "workspace" / project_name

        self.reasoner = DecisionReasoner(
            prompt_template_path=prompt_path if prompt_path.exists() else None,
            workspace_dir=ws_dir,
            config=ReasonerConfig(mode=mode, target_ratio=target_ratio, default_steps=default_steps),
        )

        self.executor = ParameterExecutor(evaluate_after_apply=evaluate_after_apply)
        self.memory = HistoryMemory(ws_dir / "cache" / "ai_memory.jsonl")

    def optimize_iteration(
        self,
        iteration: int,
        current_ratio: float,
        config_path: Path,
        compile_func: Callable[[], bool],
        compare_func: Callable[[], Optional[float]],
    ) -> ExecutionResult:
        features_path = self.skill_root / "workspace" / self.project_name / "iterations" / f"iteration_{iteration:03d}" / "diff_features.json"
        diff_context = self.analyzer.analyze(
            diff_ratio=current_ratio,
            iteration=iteration,
            features_path=features_path,
        )

        history = self.memory.get_recent(n=5)
        decision = self.reasoner.reason(diff_context=diff_context, history=history, current_config=config_path.read_text(encoding="utf-8"))

        result = self.executor.execute(
            decision=decision,
            config_path=config_path,
            compile_func=compile_func,
            compare_func=compare_func,
            current_ratio=current_ratio,
        )

        # 落盘记录（尽量可复盘）
        self.memory.record(
            iteration=iteration,
            context={
                "diff_ratio": diff_context.diff_ratio,
                "root_cause": diff_context.root_cause,
                "affected_regions": diff_context.affected_regions,
                "evidence": diff_context.evidence,
                "parameter_candidates": diff_context.parameter_candidates,
            },
            decision=decision,
            result={
                "status": result.status,
                "new_ratio": result.new_ratio,
                "improvement": result.improvement,
                "rollback": result.rollback,
                "reason": result.reason,
                "applied": result.applied,
            },
        )

        return result

    def _load_skill_config(self) -> Dict[str, Any]:
        cfg_path = self.skill_root / "config.yaml"
        if not cfg_path.exists():
            return {}
        try:
            import yaml
        except Exception:
            return {}
        try:
            return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    def _infer_target_ratio(self, cfg: Dict[str, Any]) -> float:
        # 优先使用“像素差异容忍度”（Single Source of Truth）
        v = (
            cfg.get("validation", {})
            .get("tolerance", {})
            .get("pixel_changed_ratio")
        )
        if isinstance(v, (int, float)) and v > 0:
            return float(v)

        # 其次用迭代收敛阈值
        v = cfg.get("iteration", {}).get("convergence_threshold")
        if isinstance(v, (int, float)) and v > 0:
            return float(v)

        return 0.01

    def _infer_default_steps(self, cfg: Dict[str, Any]) -> Dict[str, float]:
        gran = cfg.get("iteration", {}).get("adjustment_granularity", {}) or {}

        font_pt = float(gran.get("font_size_pt", 0.1) or 0.1)
        line = float(gran.get("line_spacing", 0.05) or 0.05)
        margin = float(gran.get("margin_cm", 0.05) or 0.05)

        # 保守策略：用配置粒度的“更小步长”作为默认
        return {
            "xiaosi_font_size": max(0.01, font_pt / 2.0),
            "baselinestretch": max(0.001, line / 5.0),
            "margin_cm": max(0.01, margin),
            "parskip_em": 0.1,
            "arraystretch": 0.02,
            "title_indent_em": 0.1,
        }
