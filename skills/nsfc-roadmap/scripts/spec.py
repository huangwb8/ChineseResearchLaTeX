from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple


BoxKind = Literal["primary", "secondary", "decision", "critical", "risk", "auxiliary"]
LayoutTemplate = Literal["auto", "classic", "three-column", "packed-three-column", "layered-pipeline"]
BoxRole = Literal[
    "main",
    "support",
    "output",
    "risk",
    "header",
    # spec v2 semantic roles (optional; renderer may use them for auto-edges/layout hints)
    "input",
    "method",
    "validate",
    "deploy",
    "compare",
]


@dataclass
class BoxSizeHint:
    # All are optional; renderer may treat them as soft constraints.
    min_h: Optional[int] = None
    max_h: Optional[int] = None
    prefer_h: Optional[int] = None
    min_w: Optional[int] = None


@dataclass
class BoxLayoutHint:
    # Soft layout hints; exact semantics depend on layout engine.
    stack: Optional[str] = None  # e.g. "center"
    lane: Optional[str] = None  # e.g. "left|right|center"
    pin: Optional[str] = None  # e.g. "top|bottom"


@dataclass
class Box:
    text: str
    kind: BoxKind = "primary"
    weight: int = 1  # width weight within a row
    # Optional stable id (spec v2). When missing, renderer should deterministically generate one.
    id: Optional[str] = None
    # Optional semantic role for AI-driven specs. When present, the renderer may use it
    # to pick a stable mainline box without heuristics (keeps backward-compatible).
    role: Optional[BoxRole] = None
    size_hint: Optional[BoxSizeHint] = None
    layout_hint: Optional[BoxLayoutHint] = None
    # Optional draw.io style override string (advanced). Prefer palette by default.
    style: Optional[str] = None


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


EdgeRoute = Literal["orthogonal", "elbow", "straight", "auto"]
EdgeKind = Literal["main", "aux", "risk", "custom"]


@dataclass
class Edge:
    # Optional stable id; if missing, renderer should deterministically generate one.
    id: Optional[str]
    from_ref: str
    to_ref: str
    kind: EdgeKind = "main"
    route: EdgeRoute = "auto"
    waypoints: Optional[List[Tuple[int, int]]] = None
    label: Optional[str] = None
    # Optional draw.io edge style override string (advanced).
    style: Optional[str] = None


@dataclass
class Group:
    id: str
    children: List[str]


@dataclass
class Container:
    id: str
    kind: str  # stack|panel|swimlane|custom (renderer-defined)
    children: List[str]
    padding: Optional[int] = None
    layout: Optional[str] = None  # vertical|horizontal|grid (renderer-defined)


@dataclass
class RoadmapSpec:
    title: str
    phases: List[Phase]
    notes: Optional[str] = None
    # Optional style controls (keep backward-compatible; may be omitted in specs).
    layout_template: Optional[LayoutTemplate] = None
    template_ref: Optional[str] = None
    # spec v2 advanced graph controls (optional)
    edges: Optional[List[Edge]] = None
    groups: Optional[List[Group]] = None
    containers: Optional[List[Container]] = None


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


def _opt_str(obj: Dict[str, Any], key: str, where: str) -> Optional[str]:
    v = obj.get(key)
    if v is None:
        return None
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{where}.{key} 必须是非空字符串或省略")
    return v.strip()


def _opt_int(obj: Dict[str, Any], key: str, where: str) -> Optional[int]:
    v = obj.get(key)
    if v is None:
        return None
    if not isinstance(v, int):
        raise ValueError(f"{where}.{key} 必须是整数或省略")
    return int(v)


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
                bid = _opt_str(b, "id", f"spec.phases[{i}].rows[{j}][{k}]")
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
                    if rr not in (
                        "main",
                        "support",
                        "output",
                        "risk",
                        "header",
                        "input",
                        "method",
                        "validate",
                        "deploy",
                        "compare",
                    ):
                        raise ValueError(
                            f"spec.phases[{i}].rows[{j}][{k}].role 不合法：{rr!r}（允许：main|support|output|risk|header|input|method|validate|deploy|compare）"
                        )
                    role = rr  # type: ignore[assignment]

                # Optional v2 hints
                size_hint = None
                sh = b.get("size_hint")
                if sh is not None:
                    if not isinstance(sh, dict):
                        raise ValueError(f"spec.phases[{i}].rows[{j}][{k}].size_hint 必须是 mapping 或省略")
                    size_hint = BoxSizeHint(
                        min_h=_opt_int(sh, "min_h", f"spec.phases[{i}].rows[{j}][{k}].size_hint"),
                        max_h=_opt_int(sh, "max_h", f"spec.phases[{i}].rows[{j}][{k}].size_hint"),
                        prefer_h=_opt_int(sh, "prefer_h", f"spec.phases[{i}].rows[{j}][{k}].size_hint"),
                        min_w=_opt_int(sh, "min_w", f"spec.phases[{i}].rows[{j}][{k}].size_hint"),
                    )
                layout_hint = None
                lh = b.get("layout_hint")
                if lh is not None:
                    if not isinstance(lh, dict):
                        raise ValueError(f"spec.phases[{i}].rows[{j}][{k}].layout_hint 必须是 mapping 或省略")
                    layout_hint = BoxLayoutHint(
                        stack=_opt_str(lh, "stack", f"spec.phases[{i}].rows[{j}][{k}].layout_hint"),
                        lane=_opt_str(lh, "lane", f"spec.phases[{i}].rows[{j}][{k}].layout_hint"),
                        pin=_opt_str(lh, "pin", f"spec.phases[{i}].rows[{j}][{k}].layout_hint"),
                    )
                style = _opt_str(b, "style", f"spec.phases[{i}].rows[{j}][{k}]")

                boxes.append(
                    Box(
                        text=text,
                        kind=kind,
                        weight=weight,
                        id=bid,
                        role=role,  # type: ignore[arg-type]
                        size_hint=size_hint,
                        layout_hint=layout_hint,
                        style=style,
                    )
                )
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
        if lt not in ("auto", "classic", "three-column", "packed-three-column", "layered-pipeline"):
            raise ValueError(
                "spec.layout_template 不合法："
                f"{lt!r}（允许：auto|classic|three-column|packed-three-column|layered-pipeline）"
            )
        layout_template = lt  # type: ignore[assignment]

    template_ref = data.get("template_ref")
    if template_ref is not None:
        if not isinstance(template_ref, str) or not template_ref.strip():
            raise ValueError("spec.template_ref 必须是字符串或省略")
        template_ref = template_ref.strip()

    # Optional v2: explicit edges
    edges: Optional[List[Edge]] = None
    edges_raw = data.get("edges")
    if edges_raw is not None:
        if not isinstance(edges_raw, list):
            raise ValueError("spec.edges 必须是 list 或省略")
        edges = []
        for ei, e in enumerate(edges_raw, start=1):
            if not isinstance(e, dict):
                raise ValueError(f"spec.edges[{ei}] 必须是 mapping")
            eid = _opt_str(e, "id", f"spec.edges[{ei}]")
            fr = e.get("from")
            tr = e.get("to")
            if not isinstance(fr, str) or not fr.strip():
                raise ValueError(f"spec.edges[{ei}].from 必须是非空字符串")
            if not isinstance(tr, str) or not tr.strip():
                raise ValueError(f"spec.edges[{ei}].to 必须是非空字符串")
            fr = fr.strip()
            tr = tr.strip()
            kind = str(e.get("kind", "main") or "main").strip()
            if kind not in ("main", "aux", "risk", "custom"):
                raise ValueError(f"spec.edges[{ei}].kind 不合法：{kind!r}（允许：main|aux|risk|custom）")
            route = str(e.get("route", "auto") or "auto").strip()
            if route not in ("orthogonal", "elbow", "straight", "auto"):
                raise ValueError(
                    f"spec.edges[{ei}].route 不合法：{route!r}（允许：orthogonal|elbow|straight|auto）"
                )
            waypoints = None
            wps = e.get("waypoints")
            if wps is not None:
                if not isinstance(wps, list):
                    raise ValueError(f"spec.edges[{ei}].waypoints 必须是点列表或省略")
                waypoints = []
                for wi, pt in enumerate(wps, start=1):
                    if (
                        not isinstance(pt, (list, tuple))
                        or len(pt) != 2
                        or not isinstance(pt[0], (int, float))
                        or not isinstance(pt[1], (int, float))
                    ):
                        raise ValueError(f"spec.edges[{ei}].waypoints[{wi}] 必须是 [x, y]")
                    waypoints.append((int(round(float(pt[0]))), int(round(float(pt[1])))))
            label = None
            if "label" in e:
                lv = e.get("label")
                if lv is not None:
                    if not isinstance(lv, str):
                        raise ValueError(f"spec.edges[{ei}].label 必须是字符串或省略")
                    label = lv.strip() or None
            style = None
            if "style" in e:
                sv = e.get("style")
                if sv is not None:
                    if not isinstance(sv, str):
                        raise ValueError(f"spec.edges[{ei}].style 必须是字符串或省略")
                    style = sv.strip() or None
            edges.append(
                Edge(
                    id=eid,
                    from_ref=fr,
                    to_ref=tr,
                    kind=kind,  # type: ignore[arg-type]
                    route=route,  # type: ignore[arg-type]
                    waypoints=waypoints,
                    label=label,
                    style=style,
                )
            )

    # Optional v2: groups/containers (currently validated & stored; renderer may ignore).
    groups: Optional[List[Group]] = None
    groups_raw = data.get("groups")
    if groups_raw is not None:
        if not isinstance(groups_raw, list):
            raise ValueError("spec.groups 必须是 list 或省略")
        groups = []
        for gi, g in enumerate(groups_raw, start=1):
            if not isinstance(g, dict):
                raise ValueError(f"spec.groups[{gi}] 必须是 mapping")
            gid = g.get("id")
            if not isinstance(gid, str) or not gid.strip():
                raise ValueError(f"spec.groups[{gi}].id 必须是非空字符串")
            gid = gid.strip()
            children_raw = g.get("children")
            if not isinstance(children_raw, list) or not children_raw:
                raise ValueError(f"spec.groups[{gi}].children 必须是非空列表")
            children = []
            for ci, c in enumerate(children_raw, start=1):
                if not isinstance(c, str) or not c.strip():
                    raise ValueError(f"spec.groups[{gi}].children[{ci}] 必须是非空字符串")
                children.append(c.strip())
            groups.append(Group(id=gid, children=children))

    containers: Optional[List[Container]] = None
    containers_raw = data.get("containers")
    if containers_raw is not None:
        if not isinstance(containers_raw, list):
            raise ValueError("spec.containers 必须是 list 或省略")
        containers = []
        for ci, c in enumerate(containers_raw, start=1):
            if not isinstance(c, dict):
                raise ValueError(f"spec.containers[{ci}] 必须是 mapping")
            cid = c.get("id")
            if not isinstance(cid, str) or not cid.strip():
                raise ValueError(f"spec.containers[{ci}].id 必须是非空字符串")
            cid = cid.strip()
            kind = c.get("kind")
            if not isinstance(kind, str) or not kind.strip():
                raise ValueError(f"spec.containers[{ci}].kind 必须是非空字符串")
            kind = kind.strip()
            children_raw = c.get("children")
            if not isinstance(children_raw, list) or not children_raw:
                raise ValueError(f"spec.containers[{ci}].children 必须是非空列表")
            children: List[str] = []
            for ji, child in enumerate(children_raw, start=1):
                if not isinstance(child, str) or not child.strip():
                    raise ValueError(f"spec.containers[{ci}].children[{ji}] 必须是非空字符串")
                children.append(child.strip())
            padding = _opt_int(c, "padding", f"spec.containers[{ci}]")
            layout = _opt_str(c, "layout", f"spec.containers[{ci}]")
            containers.append(Container(id=cid, kind=kind, children=children, padding=padding, layout=layout))

    return RoadmapSpec(
        title=title,
        phases=phases,
        notes=notes,
        layout_template=layout_template,  # type: ignore[arg-type]
        template_ref=template_ref,
        edges=edges,
        groups=groups,
        containers=containers,
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
