#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策推理器（DecisionReasoner）

为避免“脚本内部无法直接调用宿主 AI”的现实约束，本模块提供两种模式：
- heuristic：纯启发式（默认，可离线）
- manual_file：生成 ai_request.json，等待用户/宿主 AI 写回 ai_response.json

输出统一为 dict，便于与 HistoryMemory/ParameterExecutor 对接。
"""

import json
import re
from string import Template
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ReasonerConfig:
    mode: str = "heuristic"  # heuristic | manual_file
    target_ratio: float = 0.01
    default_steps: Optional[Dict[str, float]] = None


class DecisionReasoner:
    """生成下一步参数调整策略"""

    def __init__(
        self,
        prompt_template_path: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
        config: Optional[ReasonerConfig] = None,
    ):
        self.prompt_template_path = Path(prompt_template_path) if prompt_template_path else None
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None
        self.config = config or ReasonerConfig()

        if self.config.default_steps is None:
            self.config.default_steps = {
                "xiaosi_font_size": 0.05,
                "baselinestretch": 0.01,
                "margin_cm": 0.05,
                "parskip_em": 0.1,
                "arraystretch": 0.02,
                "title_indent_em": 0.1,
            }

    def reason(
        self,
        diff_context: Any,
        history: List[Dict[str, Any]],
        current_config: str,
    ) -> Dict[str, Any]:
        mode = (self.config.mode or "heuristic").strip().lower()
        if mode == "manual_file":
            return self._manual_file_reason(diff_context, history, current_config)
        return self._heuristic_reason(diff_context, history, current_config)

    def _heuristic_reason(
        self,
        diff_context: Any,
        history: List[Dict[str, Any]],
        current_config: str,
    ) -> Dict[str, Any]:
        root = getattr(diff_context, "root_cause", "unknown")
        candidates = getattr(diff_context, "parameter_candidates", []) or []

        # 首选参数：按 relevance 取第一个
        primary = candidates[0]["name"] if candidates else "xiaosi_font_size"

        adjustments: List[Dict[str, Any]] = []
        fallback: List[Dict[str, Any]] = []

        if primary == "xiaosi_font_size":
            cur, ok = self._extract_xiaosi_font_size(current_config)
            step = float(self.config.default_steps.get("xiaosi_font_size", 0.05))
            new_val = (cur - step) if ok else None
            adjustments.append(
                {
                    "parameter": "xiaosi_font_size",
                    "current_value": cur if ok else None,
                    "new_value": round(new_val, 2) if new_val is not None else None,
                    "delta": -step,
                    "confidence": 0.75,
                    "reasoning": "优先处理换行/密度差异：先小步调整小四字号。",
                }
            )
            fallback.append({"parameter": "margin_right", "delta": -float(self.config.default_steps["margin_cm"])})
        elif primary == "baselinestretch":
            cur, ok = self._extract_baselinestretch(current_config)
            step = float(self.config.default_steps.get("baselinestretch", 0.01))
            new_val = (cur - step) if ok else None
            adjustments.append(
                {
                    "parameter": "baselinestretch",
                    "current_value": cur if ok else None,
                    "new_value": round(new_val, 3) if new_val is not None else None,
                    "delta": -step,
                    "confidence": 0.70,
                    "reasoning": "垂直偏移/行距累积差：先小步收紧 baselinestretch。",
                }
            )
            fallback.append({"parameter": "parskip", "delta": -float(self.config.default_steps["parskip_em"])})
        elif primary.startswith("margin_"):
            # margin_left / margin_right / margin_top / margin_bottom
            step = float(self.config.default_steps.get("margin_cm", 0.05))
            adjustments.append(
                {
                    "parameter": primary,
                    "current_value": None,
                    "new_value": None,
                    "delta": -step,
                    "confidence": 0.65,
                    "reasoning": "横向条纹/边距不匹配：优先微调 geometry 边距。",
                }
            )
            fallback.append({"parameter": "title_indent", "delta": -float(self.config.default_steps["title_indent_em"])})
        elif primary == "title_indent":
            step = float(self.config.default_steps.get("title_indent_em", 0.1))
            adjustments.append(
                {
                    "parameter": "title_indent",
                    "current_value": None,
                    "new_value": None,
                    "delta": -step,
                    "confidence": 0.60,
                    "reasoning": "标题区差异显著：优先微调标题缩进。",
                }
            )
            fallback.append({"parameter": "xiaosi_font_size", "delta": -float(self.config.default_steps["xiaosi_font_size"])})
        else:
            # 兜底：小四字号
            cur, ok = self._extract_xiaosi_font_size(current_config)
            step = float(self.config.default_steps.get("xiaosi_font_size", 0.05))
            new_val = (cur - step) if ok else None
            adjustments.append(
                {
                    "parameter": "xiaosi_font_size",
                    "current_value": cur if ok else None,
                    "new_value": round(new_val, 2) if new_val is not None else None,
                    "delta": -step,
                    "confidence": 0.55,
                    "reasoning": "缺少可靠根因特征：采用保守默认策略（小四字号微调）。",
                }
            )

        return {
            "analysis": {"root_cause": root, "key_evidence": []},
            "adjustments": adjustments,
            "fallback": fallback,
        }

    def _manual_file_reason(
        self,
        diff_context: Any,
        history: List[Dict[str, Any]],
        current_config: str,
    ) -> Dict[str, Any]:
        if not self.workspace_dir:
            raise ValueError("manual_file 模式需要 workspace_dir")

        iteration = int(getattr(diff_context, "iteration", 0) or 0)
        iter_dir = self.workspace_dir / "iterations" / f"iteration_{iteration:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        prompt = self._render_prompt(diff_context, history, current_config)
        request_path = iter_dir / "ai_request.json"
        response_path = iter_dir / "ai_response.json"

        request_path.write_text(
            json.dumps(
                {
                    "prompt": prompt,
                    "context": {
                        "diff_ratio": getattr(diff_context, "diff_ratio", None),
                        "iteration": getattr(diff_context, "iteration", None),
                        "root_cause": getattr(diff_context, "root_cause", None),
                        "parameter_candidates": getattr(diff_context, "parameter_candidates", None),
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        if not response_path.exists():
            raise RuntimeError(
                f"已生成 AI 请求文件: {request_path}；请写入响应文件: {response_path}（严格 JSON）后重试。"
            )

        try:
            data = json.loads(response_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"ai_response.json 不是合法 JSON: {e}")

        return self._normalize_ai_decision(data, fallback_root=getattr(diff_context, "root_cause", "unknown"))

    def _render_prompt(self, diff_context: Any, history: List[Dict[str, Any]], current_config: str) -> str:
        template_text = None
        if self.prompt_template_path and self.prompt_template_path.exists():
            template_text = self.prompt_template_path.read_text(encoding="utf-8")
        if not template_text:
            template_text = (
                "diff_ratio=$diff_ratio\n"
                "iteration=$iteration\n"
                "target_ratio=$target_ratio\n"
                "diff_analysis=$diff_analysis\n"
                "history=$history\n"
                "current_config=$current_config\n"
            )

        diff_analysis = json.dumps(getattr(diff_context, "evidence", {}), ensure_ascii=False, indent=2)
        hist = json.dumps(history, ensure_ascii=False, indent=2)

        # 用 string.Template 避免花括号与 LaTeX/JSON 冲突
        t = Template(template_text)
        return t.safe_substitute(
            diff_ratio=f"{float(getattr(diff_context, 'diff_ratio', 0.0)):.2%}",
            iteration=str(int(getattr(diff_context, "iteration", 0) or 0)),
            target_ratio=f"{float(self.config.target_ratio):.2%}",
            diff_analysis=diff_analysis,
            history=hist,
            current_config=current_config,
        )

    def _normalize_ai_decision(self, data: Dict[str, Any], fallback_root: str) -> Dict[str, Any]:
        # 允许 AI 返回内容略有差异；这里做最小化归一
        if not isinstance(data, dict):
            raise ValueError("AI decision must be a JSON object")

        analysis = data.get("analysis") or {}
        if "root_cause" not in analysis:
            analysis["root_cause"] = fallback_root

        adjustments = data.get("adjustments") or data.get("strategy", {}).get("adjustments") or []
        if isinstance(adjustments, dict):
            adjustments = [adjustments]

        fallback = data.get("fallback") or []
        if isinstance(fallback, dict):
            fallback = [fallback]

        return {"analysis": analysis, "adjustments": adjustments, "fallback": fallback}

    def _extract_xiaosi_font_size(self, config_content: str) -> Tuple[float, bool]:
        # 兼容 {12pt}{18pt} / {12}{18}
        m = re.search(r"\\newcommand\{\\xiaosi\}\s*\{\s*\\fontsize\{([0-9.]+)\s*pt?\}", config_content)
        if not m:
            return 0.0, False
        try:
            return float(m.group(1)), True
        except Exception:
            return 0.0, False

    def _extract_baselinestretch(self, config_content: str) -> Tuple[float, bool]:
        m = re.search(r"\\renewcommand\{\\baselinestretch\}\s*\{([0-9.]+)\}", config_content)
        if not m:
            return 0.0, False
        try:
            return float(m.group(1)), True
        except Exception:
            return 0.0, False
