#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数执行器（ParameterExecutor）

负责：
- 安全应用参数调整到 @config.tex
- 可选：编译 + 像素对比验证
- 恶化时自动回滚

注意：本模块只对 @config.tex 做最小化、可回滚修改，不接触正文文件。
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ExecutionResult:
    status: str  # success | neutral | failed | error
    new_ratio: Optional[float] = None
    improvement: Optional[float] = None
    rollback: bool = False
    reason: str = ""
    applied: Optional[List[Dict[str, Any]]] = None


class ParameterExecutor:
    """安全的参数执行器"""

    def __init__(
        self,
        worsen_ratio_threshold: float = 0.05,
        improve_ratio_threshold: float = 0.01,
        evaluate_after_apply: bool = True,
    ):
        self.worsen_ratio_threshold = worsen_ratio_threshold
        self.improve_ratio_threshold = improve_ratio_threshold
        self.evaluate_after_apply = evaluate_after_apply

    def execute(
        self,
        decision: Dict[str, Any],
        config_path: Path,
        compile_func: Callable[[], bool],
        compare_func: Callable[[], Optional[float]],
        current_ratio: float,
    ) -> ExecutionResult:
        if not config_path.exists():
            return ExecutionResult(status="error", reason=f"配置文件不存在: {config_path}")

        adjustments = decision.get("adjustments") or []
        if not adjustments:
            return ExecutionResult(status="neutral", reason="没有可执行的调整", applied=[])

        backup = config_path.read_text(encoding="utf-8")

        try:
            new_content, applied = self._apply_adjustments_to_content(backup, adjustments)
            if not applied:
                return ExecutionResult(status="neutral", reason="未命中可修改的参数（无匹配项）", applied=[])

            config_path.write_text(new_content, encoding="utf-8")

            if not self.evaluate_after_apply:
                return ExecutionResult(status="neutral", reason="已应用调整（未执行即时评估）", applied=applied)

            if not compile_func():
                config_path.write_text(backup, encoding="utf-8")
                return ExecutionResult(status="failed", rollback=True, reason="编译失败，已回滚", applied=applied)

            new_ratio = compare_func()
            if new_ratio is None:
                # 无法对比：保守回滚，避免“盲改”
                config_path.write_text(backup, encoding="utf-8")
                return ExecutionResult(status="failed", rollback=True, reason="像素对比失败，已回滚", applied=applied)

            improvement = current_ratio - new_ratio

            # 恶化：相对增幅超过阈值
            if new_ratio > current_ratio * (1.0 + self.worsen_ratio_threshold):
                config_path.write_text(backup, encoding="utf-8")
                return ExecutionResult(
                    status="failed",
                    new_ratio=new_ratio,
                    improvement=improvement,
                    rollback=True,
                    reason=f"差异恶化超过阈值（>{self.worsen_ratio_threshold:.0%}），已回滚",
                    applied=applied,
                )

            # 明显改善
            if new_ratio < current_ratio * (1.0 - self.improve_ratio_threshold):
                return ExecutionResult(
                    status="success",
                    new_ratio=new_ratio,
                    improvement=improvement,
                    rollback=False,
                    reason="差异显著改善",
                    applied=applied,
                )

            return ExecutionResult(
                status="neutral",
                new_ratio=new_ratio,
                improvement=improvement,
                rollback=False,
                reason="差异变化不明显（可能为噪音）",
                applied=applied,
            )

        except Exception as e:
            config_path.write_text(backup, encoding="utf-8")
            return ExecutionResult(status="error", rollback=True, reason=f"执行异常，已回滚: {e}")

    def _apply_adjustments_to_content(
        self, content: str, adjustments: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        applied: List[Dict[str, Any]] = []
        updated = content

        for adj in adjustments:
            param = str(adj.get("parameter", "")).strip()
            delta = adj.get("delta")
            new_value = adj.get("new_value")

            if not param:
                continue

            before = updated

            if param == "xiaosi_font_size":
                updated = self._apply_xiaosi_font_size(updated, delta=delta, new_value=new_value)
            elif param == "baselinestretch":
                updated = self._apply_baselinestretch(updated, delta=delta, new_value=new_value)
            elif param in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
                updated = self._apply_geometry_margin(updated, param, delta=delta, new_value=new_value)
            elif param == "parskip":
                updated = self._apply_parskip(updated, delta=delta, new_value=new_value)
            elif param == "arraystretch":
                updated = self._apply_arraystretch(updated, delta=delta, new_value=new_value)
            elif param == "title_indent":
                updated = self._apply_title_indent(updated, delta=delta, new_value=new_value)
            elif param == "list_leftmargin":
                updated = self._apply_list_leftmargin(updated, delta=delta, new_value=new_value)
            elif param == "caption_skip":
                updated = self._apply_caption_skip(updated, delta=delta, new_value=new_value)

            if updated != before:
                applied.append({"parameter": param, "delta": delta, "new_value": new_value})

        return updated, applied

    def _apply_xiaosi_font_size(self, content: str, delta: Any, new_value: Any) -> str:
        # 匹配：\newcommand{\xiaosi}{\fontsize{12pt}{18pt}\selectfont}
        pattern = r"(\\newcommand\{\\xiaosi\}\s*\{\s*\\fontsize\{)([0-9.]+)(\s*pt?\}\{)([0-9.]+)(\s*pt?\})"
        m = re.search(pattern, content)
        if not m:
            return content

        cur_size = float(m.group(2))
        cur_leading = float(m.group(4))

        if new_value is not None:
            try:
                new_size = float(new_value)
                d = new_size - cur_size
            except Exception:
                return content
        else:
            try:
                d = float(delta) if delta is not None else -0.05
            except Exception:
                d = -0.05
            new_size = cur_size + d

        # 保守：leading 同步增减（保持字面行距差不至于跳变）
        new_leading = max(1.0, cur_leading + d)

        repl = f"{m.group(1)}{new_size:.2f}{m.group(3)}{new_leading:.2f}{m.group(5)}"
        # 使用函数式替换，避免 \\newcommand 中的 \\n 被解释为换行
        return re.sub(pattern, lambda _: repl, content, count=1)

    def _apply_baselinestretch(self, content: str, delta: Any, new_value: Any) -> str:
        pattern = r"(\\renewcommand\{\\baselinestretch\}\s*\{)([0-9.]+)(\})"
        m = re.search(pattern, content)
        if not m:
            return content

        cur = float(m.group(2))
        if new_value is not None:
            try:
                new_val = float(new_value)
            except Exception:
                return content
        else:
            try:
                d = float(delta) if delta is not None else -0.01
            except Exception:
                d = -0.01
            new_val = cur + d

        new_val = max(0.8, min(2.0, new_val))
        repl = f"{m.group(1)}{new_val:.3f}{m.group(3)}"
        # 使用函数式替换，避免 \\renewcommand 中的 \\r 被解释为回车
        return re.sub(pattern, lambda _: repl, content, count=1)

    def _apply_geometry_margin(self, content: str, param: str, delta: Any, new_value: Any) -> str:
        # geometry 一般形如：\geometry{left=2.0cm,right=2.0cm,top=2.5cm,bottom=2.5cm,...}
        key = param.replace("margin_", "")
        pattern = r"(\\geometry\s*\{)([^}]*)\}"
        m = re.search(pattern, content, flags=re.DOTALL)
        if not m:
            return content

        body = m.group(2)
        kv_pattern = rf"({key}\s*=\s*)([0-9.]+)\s*cm"
        kv = re.search(kv_pattern, body)
        if not kv:
            return content

        cur = float(kv.group(2))
        if new_value is not None:
            try:
                new_val = float(new_value)
            except Exception:
                return content
        else:
            try:
                d = float(delta) if delta is not None else -0.05
            except Exception:
                d = -0.05
            new_val = cur + d

        new_val = max(0.5, min(5.0, new_val))
        new_body = re.sub(kv_pattern, rf"\1{new_val:.2f}cm", body, count=1)
        return content[: m.start(2)] + new_body + content[m.end(2) :]

    def _apply_parskip(self, content: str, delta: Any, new_value: Any) -> str:
        pattern = r"(\\setlength\{\\parskip\}\s*\{)([0-9.]+)(\s*)(em|pt)(\})"
        m = re.search(pattern, content)
        if not m:
            return content

        cur = float(m.group(2))
        unit = m.group(4)
        if new_value is not None:
            try:
                new_val = float(new_value)
            except Exception:
                return content
        else:
            try:
                d = float(delta) if delta is not None else (-0.1 if unit == "em" else -1.0)
            except Exception:
                d = -0.1 if unit == "em" else -1.0
            new_val = cur + d

        new_val = max(0.0, new_val)
        repl = f"{m.group(1)}{new_val:.2f}{m.group(3)}{unit}{m.group(5)}"
        return re.sub(pattern, lambda _: repl, content, count=1)

    def _apply_arraystretch(self, content: str, delta: Any, new_value: Any) -> str:
        pattern = r"(\\renewcommand\{\\arraystretch\}\s*\{)([0-9.]+)(\})"
        m = re.search(pattern, content)
        if not m:
            return content

        cur = float(m.group(2))
        if new_value is not None:
            try:
                new_val = float(new_value)
            except Exception:
                return content
        else:
            try:
                d = float(delta) if delta is not None else -0.02
            except Exception:
                d = -0.02
            new_val = cur + d

        new_val = max(0.5, min(3.0, new_val))
        repl = f"{m.group(1)}{new_val:.2f}{m.group(3)}"
        return re.sub(pattern, lambda _: repl, content, count=1)

    def _apply_title_indent(self, content: str, delta: Any, new_value: Any) -> str:
        # 优先：项目内约定的 \NSFCTitleIndent=2em 或类似命令
        pattern = r"(\\NSFCTitleIndent\s*=\s*)([0-9.]+)(\s*em)"
        m = re.search(pattern, content)
        if not m:
            return content

        cur = float(m.group(2))
        if new_value is not None:
            try:
                new_val = float(new_value)
            except Exception:
                return content
        else:
            try:
                d = float(delta) if delta is not None else -0.1
            except Exception:
                d = -0.1
            new_val = cur + d

        new_val = max(0.0, min(10.0, new_val))
        repl = f"{m.group(1)}{new_val:.2f}{m.group(3)}"
        return re.sub(pattern, lambda _: repl, content, count=1)

    def _apply_list_leftmargin(self, content: str, delta: Any, new_value: Any) -> str:
        # 典型：\setlist{leftmargin=2em,...}
        pattern = r"(leftmargin\s*=\s*)([0-9.]+)(\s*em)"
        m = re.search(pattern, content)
        if not m:
            return content

        cur = float(m.group(2))
        if new_value is not None:
            try:
                new_val = float(new_value)
            except Exception:
                return content
        else:
            try:
                d = float(delta) if delta is not None else -0.1
            except Exception:
                d = -0.1
            new_val = cur + d

        new_val = max(0.0, min(10.0, new_val))
        repl = f"{m.group(1)}{new_val:.2f}{m.group(3)}"
        return re.sub(pattern, lambda _: repl, content, count=1)

    def _apply_caption_skip(self, content: str, delta: Any, new_value: Any) -> str:
        # 典型：\setlength{\textfloatsep}{12pt} 或 \setlength{\abovecaptionskip}{6pt}
        # 优先对 textfloatsep 生效（对图表块更敏感）
        for key in ("\\textfloatsep", "\\abovecaptionskip", "\\belowcaptionskip"):
            pattern = rf"(\\setlength\{{{re.escape(key)}\}}\s*\{{)([0-9.]+)(\s*pt\}})"
            m = re.search(pattern, content)
            if not m:
                continue

            cur = float(m.group(2))
            if new_value is not None:
                try:
                    new_val = float(new_value)
                except Exception:
                    return content
            else:
                try:
                    d = float(delta) if delta is not None else -0.5
                except Exception:
                    d = -0.5
                new_val = cur + d

            new_val = max(0.0, min(200.0, new_val))
            repl = f"{m.group(1)}{new_val:.2f}{m.group(3)}"
            return re.sub(pattern, lambda _: repl, content, count=1)

        return content
