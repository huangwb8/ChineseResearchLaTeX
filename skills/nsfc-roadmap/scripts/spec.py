from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional


BoxKind = Literal["primary", "secondary", "decision", "critical", "risk", "auxiliary"]
LayoutTemplate = Literal["auto", "classic", "three-column", "layered-pipeline"]
BoxRole = Literal["main", "support", "output", "risk", "header"]


@dataclass
class Box:
    text: str
    kind: BoxKind = "primary"
    weight: int = 1  # width weight within a row
    # Optional semantic role for AI-driven specs. When present, the renderer may use it
    # to pick a stable mainline box without heuristics (keeps backward-compatible).
    role: Optional[BoxRole] = None


@dataclass
class Row:
    boxes: List[Box]


@dataclass
class Phase:
    label: str
    rows: List[Row]
    # Optional: used by some layouts to render a dedicated phase header bar/title strip,
    # instead of injecting a short "title" box into the layout (keeps mainline box selection stable).
    phase_header_override: Optional[str] = None


@dataclass
class RoadmapSpec:
    title: str
    phases: List[Phase]
    notes: Optional[str] = None
    # Optional style controls (keep backward-compatible; may be omitted in specs).
    layout_template: Optional[LayoutTemplate] = None
    template_ref: Optional[str] = None


def _require_str(obj: Dict[str, Any], key: str) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"spec.{key} 必须是非空字符串")
    return v.strip()


def _require_list(obj: Dict[str, Any], key: str) -> List[Any]:
    v = obj.get(key)
    if not isinstance(v, list) or not v:
        raise ValueError(f"spec.{key} 必须是非空列表")
    return v


def load_spec(data: Dict[str, Any]) -> RoadmapSpec:
    title = _require_str(data, "title")
    phases_raw = _require_list(data, "phases")
    phases: List[Phase] = []
    for i, p in enumerate(phases_raw, start=1):
        if not isinstance(p, dict):
            raise ValueError(f"spec.phases[{i}] 必须是 mapping")
        label = _require_str(p, "label")
        rows_raw = _require_list(p, "rows")
        rows: List[Row] = []
        for j, r in enumerate(rows_raw, start=1):
            if not isinstance(r, list) or not r:
                raise ValueError(f"spec.phases[{i}].rows[{j}] 必须是非空列表（row boxes）")
            boxes: List[Box] = []
            for k, b in enumerate(r, start=1):
                if isinstance(b, str):
                    boxes.append(Box(text=b))
                    continue
                if not isinstance(b, dict):
                    raise ValueError(
                        f"spec.phases[{i}].rows[{j}][{k}] 必须是字符串或 mapping"
                    )
                text = _require_str(b, "text")
                kind = b.get("kind", "primary")
                if kind not in (
                    "primary",
                    "secondary",
                    "decision",
                    "critical",
                    "risk",
                    "auxiliary",
                ):
                    raise ValueError(
                        f"spec.phases[{i}].rows[{j}][{k}].kind 不合法：{kind}"
                    )
                weight = b.get("weight", 1)
                if not isinstance(weight, int) or weight <= 0:
                    raise ValueError(
                        f"spec.phases[{i}].rows[{j}][{k}].weight 必须是正整数"
                    )
                role = b.get("role")
                if role is not None:
                    if not isinstance(role, str) or not role.strip():
                        raise ValueError(f"spec.phases[{i}].rows[{j}][{k}].role 必须是字符串或省略")
                    rr = role.strip()
                    if rr not in ("main", "support", "output", "risk", "header"):
                        raise ValueError(
                            f"spec.phases[{i}].rows[{j}][{k}].role 不合法：{rr!r}（允许：main|support|output|risk|header）"
                        )
                    role = rr  # type: ignore[assignment]
                boxes.append(Box(text=text, kind=kind, weight=weight, role=role))  # type: ignore[arg-type]
            rows.append(Row(boxes=boxes))
        phase_header_override = p.get("phase_header_override")
        if phase_header_override is not None:
            if not isinstance(phase_header_override, str) or not phase_header_override.strip():
                raise ValueError(f"spec.phases[{i}].phase_header_override 必须是非空字符串或省略")
            phase_header_override = phase_header_override.strip()

        phases.append(
            Phase(
                label=label,
                rows=rows,
                phase_header_override=phase_header_override,  # type: ignore[arg-type]
            )
        )
    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ValueError("spec.notes 必须是字符串或省略")

    layout_template = data.get("layout_template")
    if layout_template is not None:
        if not isinstance(layout_template, str) or not layout_template.strip():
            raise ValueError("spec.layout_template 必须是字符串或省略")
        lt = layout_template.strip()
        if lt not in ("auto", "classic", "three-column", "layered-pipeline"):
            raise ValueError(
                "spec.layout_template 不合法："
                f"{lt!r}（允许：auto|classic|three-column|layered-pipeline）"
            )
        layout_template = lt  # type: ignore[assignment]

    template_ref = data.get("template_ref")
    if template_ref is not None:
        if not isinstance(template_ref, str) or not template_ref.strip():
            raise ValueError("spec.template_ref 必须是字符串或省略")
        template_ref = template_ref.strip()

    return RoadmapSpec(
        title=title,
        phases=phases,
        notes=notes,
        layout_template=layout_template,  # type: ignore[arg-type]
        template_ref=template_ref,
    )


def default_spec_for_nsfc_young_2026() -> Dict[str, Any]:
    # 初版示例：保持通用风格，但默认内容更贴近常见 NSFC 结构（可被 AI/用户改写）。
    return {
        "title": "技术路线图（示例）",
        "phases": [
            {
                "label": "数据准备",
                "rows": [
                    [
                        {"text": "公开组学数据\nTCGA / ICGC / GEO", "kind": "primary"},
                        {"text": "公开 ICI 队列\nTIDE / ICBatlas", "kind": "primary"},
                        {"text": "自有 ICI 队列\n多中心临床试验数据", "kind": "secondary"},
                    ],
                    [
                        {
                            "text": "组学数据预处理\n标准化 / 批次校正 / 质控 / 特征映射",
                            "kind": "auxiliary",
                            "weight": 3,
                        }
                    ],
                ],
            },
            {
                "label": "模型构建",
                "rows": [
                    [
                        {
                            "text": "统一表征框架\n训练-部署脱钩（G_train / S_deploy）",
                            "kind": "critical",
                            "weight": 3,
                        }
                    ],
                    [
                        {"text": "基因集优化", "kind": "decision"},
                        {"text": "自监督预训练\n（MGM）", "kind": "primary"},
                        {"text": "超参/消融\n与稳健性", "kind": "auxiliary"},
                    ],
                    [
                        {"text": "分型体系\nCCS / ITS", "kind": "primary"},
                        {"text": "预测模型\nICI 疗效分层", "kind": "secondary"},
                    ],
                    [
                        {
                            "text": "风险与替代方案\n最小可用门槛 / 备选策略",
                            "kind": "risk",
                            "weight": 2,
                        }
                    ],
                ],
            },
            {
                "label": "机制研究",
                "rows": [
                    [
                        {"text": "可解释性\n组织/队列/特征", "kind": "auxiliary"},
                        {"text": "分子特征\n通路 / LOF-GOF", "kind": "primary"},
                        {"text": "免疫特征\n浸润 / 抑制", "kind": "secondary"},
                    ],
                    [
                        {
                            "text": "单细胞实验\nscRNA-seq + scATAC-seq（可选验证）",
                            "kind": "auxiliary",
                            "weight": 3,
                        }
                    ],
                ],
            },
            {
                "label": "临床验证",
                "rows": [
                    [
                        {"text": "区分度\nAUC / C-index", "kind": "primary"},
                        {"text": "校准\nBrier / 校准曲线", "kind": "auxiliary"},
                        {"text": "临床净获益\nDCA", "kind": "secondary"},
                    ],
                    [
                        {"text": "扩展应用\n跨癌种迁移", "kind": "auxiliary"},
                        {"text": "平台建设\n开源模型 / Web 应用", "kind": "auxiliary"},
                    ],
                ],
            },
        ],
    }
