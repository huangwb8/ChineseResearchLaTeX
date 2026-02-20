from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional, Tuple


Direction = Literal["top-to-bottom", "left-to-right", "bottom-to-top"]
NodeKind = Literal["primary", "secondary", "decision", "critical", "risk", "auxiliary"]
GroupStyle = Literal["dashed-border", "solid-border", "background-fill"]
EdgeStyle = Literal["solid", "dashed", "thick"]

_CJK_RANGES: tuple[tuple[int, int], ...] = (
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
)


@dataclass
class Node:
    id: str
    label: str
    kind: NodeKind
    x: int
    y: int
    w: int
    h: int
    group_id: str


@dataclass
class Group:
    id: str
    label: str
    x: int
    y: int
    w: int
    h: int
    style: GroupStyle
    children: List[Node]


@dataclass
class Edge:
    source: str
    target: str
    style: EdgeStyle
    label: str


@dataclass
class SchematicSpec:
    title: str
    canvas_width: int
    canvas_height: int
    direction: Direction
    groups: List[Group]
    edges: List[Edge]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schematic": {
                "title": self.title,
                "canvas": {"width": self.canvas_width, "height": self.canvas_height},
                "direction": self.direction,
                "groups": [
                    {
                        "id": g.id,
                        "label": g.label,
                        "position": {"x": g.x, "y": g.y},
                        "size": {"w": g.w, "h": g.h},
                        "style": g.style,
                        "children": [
                            {
                                "id": n.id,
                                "label": n.label,
                                "kind": n.kind,
                                "position": {"x": n.x, "y": n.y},
                                "size": {"w": n.w, "h": n.h},
                            }
                            for n in g.children
                        ],
                    }
                    for g in self.groups
                ],
                "edges": [
                    {"from": e.source, "to": e.target, "style": e.style, "label": e.label}
                    for e in self.edges
                ],
            }
        }


def default_schematic_spec() -> Dict[str, Any]:
    return {
        "schematic": {
            "title": "NSFC 原理图（示例）",
            "direction": "top-to-bottom",
            "groups": [
                {
                    "id": "input_group",
                    "label": "输入层",
                    "style": "dashed-border",
                    "children": [
                        {"id": "raw_expr", "label": "Raw RNA Expression", "kind": "primary"},
                        {"id": "phenotype", "label": "Phenotype", "kind": "decision"},
                    ],
                },
                {
                    "id": "processing_group",
                    "label": "处理层",
                    "style": "solid-border",
                    "children": [
                        {"id": "tissue_dr", "label": "Tissue-level DR (nD)", "kind": "secondary"},
                        {"id": "cluster_dr", "label": "Cluster-level DR (2D)", "kind": "secondary"},
                        {
                            "id": "meta_ccs",
                            "label": "Meta CCS Calling Predictor",
                            "kind": "critical",
                        },
                    ],
                },
                {
                    "id": "output_group",
                    "label": "输出层",
                    "style": "background-fill",
                    "children": [
                        {"id": "norm_ccs", "label": "Normalized CCS", "kind": "primary"},
                        {"id": "pred_ccs", "label": "Predicted Meta CCS", "kind": "critical"},
                    ],
                },
            ],
            "edges": [
                {"from": "raw_expr", "to": "tissue_dr", "style": "solid"},
                {"from": "tissue_dr", "to": "cluster_dr", "style": "solid"},
                {"from": "cluster_dr", "to": "meta_ccs", "style": "solid"},
                {
                    "from": "phenotype",
                    "to": "meta_ccs",
                    "style": "dashed",
                    "label": "辅助输入",
                },
                {"from": "meta_ccs", "to": "norm_ccs", "style": "solid"},
                {"from": "meta_ccs", "to": "pred_ccs", "style": "thick"},
            ],
        }
    }


def _require_mapping(v: Any, path: str) -> Dict[str, Any]:
    if not isinstance(v, dict):
        raise ValueError(f"{path} 必须是 mapping")
    return v


def _require_str(v: Any, path: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{path} 必须是非空字符串")
    return v.strip()


_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")


def _require_id(v: Any, path: str) -> str:
    s = _require_str(v, path)
    if not _ID_RE.fullmatch(s):
        raise ValueError(
            f"{path} 不合法：{s!r}。要求：仅允许 ASCII 字母/数字/下划线/连字符，"
            "且必须以字母或下划线开头，长度 <= 64。"
        )
    return s


def _require_list(v: Any, path: str) -> List[Any]:
    if not isinstance(v, list) or not v:
        raise ValueError(f"{path} 必须是非空列表")
    return v


def _int_or_none(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None


def _parse_position(obj: Dict[str, Any], path: str) -> Tuple[Optional[int], Optional[int]]:
    pos = obj.get("position")
    if pos is None:
        return (None, None)
    p = _require_mapping(pos, f"{path}.position")
    x = _int_or_none(p.get("x"))
    y = _int_or_none(p.get("y"))
    if x is None or y is None:
        raise ValueError(f"{path}.position.x/y 必须为整数")
    return (x, y)


def _parse_size(obj: Dict[str, Any], path: str) -> Tuple[Optional[int], Optional[int]]:
    size = obj.get("size")
    if size is None:
        return (None, None)
    s = _require_mapping(size, f"{path}.size")
    w = _int_or_none(s.get("w"))
    h = _int_or_none(s.get("h"))
    if w is None or h is None or w <= 0 or h <= 0:
        raise ValueError(f"{path}.size.w/h 必须为正整数")
    return (w, h)


def _edge_style(v: Any, path: str) -> EdgeStyle:
    style = v if isinstance(v, str) else "solid"
    if style not in ("solid", "dashed", "thick"):
        raise ValueError(f"{path}.style 不合法：{style}")
    return style


def _group_style(v: Any, path: str) -> GroupStyle:
    style = v if isinstance(v, str) else "solid-border"
    if style not in ("dashed-border", "solid-border", "background-fill"):
        raise ValueError(f"{path}.style 不合法：{style}")
    return style


def _node_kind(v: Any, path: str) -> NodeKind:
    kind = v if isinstance(v, str) else "primary"
    if kind not in ("primary", "secondary", "decision", "critical", "risk", "auxiliary"):
        raise ValueError(f"{path}.kind 不合法：{kind}")
    return kind  # type: ignore[return-value]


def _auto_group_size(child_count: int, cfg: Dict[str, Any]) -> Tuple[int, int]:
    auto = cfg["layout"]["auto"]
    cols = max(1, min(int(auto["max_cols"]), child_count))
    rows = max(1, ceil(child_count / cols))
    node_w = int(cfg["layout"]["node_default_size"]["w"])
    node_h = int(cfg["layout"]["node_default_size"]["h"])
    gap_x = int(auto["node_gap_x"])
    gap_y = int(auto["node_gap_y"])
    pad_x = int(auto["group_padding_x"])
    pad_y = int(auto["group_padding_y"])
    header_h = int(auto["group_header_h"])

    w = pad_x * 2 + cols * node_w + max(0, cols - 1) * gap_x
    h = header_h + pad_y * 2 + rows * node_h + max(0, rows - 1) * gap_y
    return (max(int(auto["group_min_w"]), w), max(int(auto["group_min_h"]), h))


def _contains_cjk(s: str) -> bool:
    for ch in s:
        code = ord(ch)
        for lo, hi in _CJK_RANGES:
            if lo <= code <= hi:
                return True
    return False


def _estimate_char_width_px(font_px: int, text: str) -> float:
    # A coarse proxy: CJK glyphs are roughly square; Latin letters are narrower.
    # This is only used for deterministic autosizing (no font file dependency).
    if _contains_cjk(text):
        return max(1.0, font_px * 0.98)
    return max(1.0, font_px * 0.62)


def _wrap_line_count(text: str, chars_per_line: int) -> int:
    # Deterministic wrap on characters (works reasonably for CJK; OK-ish for Latin).
    if chars_per_line <= 0:
        return 10**9
    total = 0
    for part in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        s = part.strip()
        if not s:
            total += 1
            continue
        total += int(ceil(len(s) / chars_per_line))
    return total


def _autosize_node_for_text(node: Node, cfg: Dict[str, Any]) -> None:
    """
    Expand node.w/node.h to reduce "text overflow/遮挡" risk.
    We never shrink nodes, only expand.
    """
    layout = cfg.get("layout", {}) if isinstance(cfg.get("layout"), dict) else {}
    font_cfg = layout.get("font", {}) if isinstance(layout.get("font"), dict) else {}
    fit_cfg = layout.get("text_fit", {}) if isinstance(layout.get("text_fit"), dict) else {}

    if fit_cfg.get("enabled", True) is False:
        return

    font_px = int(font_cfg.get("node_label_size", 22))
    padding_x = int(fit_cfg.get("padding_x", 18))
    padding_y = int(fit_cfg.get("padding_y", 14))
    line_spacing = int(fit_cfg.get("line_spacing_px", 4))
    max_lines = int(fit_cfg.get("max_lines", 3))
    max_w = int(fit_cfg.get("max_node_w", 520))
    # A safety cap: very tall nodes usually look worse than slightly wider nodes.
    max_h_soft = int(fit_cfg.get("max_node_h_soft", 260))
    widen_step = int(fit_cfg.get("widen_step_px", 20))

    label = node.label.strip()
    if not label:
        return

    char_w = _estimate_char_width_px(font_px, label)

    def lines_for_width(w: int) -> int:
        usable = max(1, int(w) - padding_x * 2)
        chars_per_line = max(1, int(usable / max(1.0, char_w)))
        return _wrap_line_count(label, chars_per_line)

    # Prefer widening to keep nodes short and tidy.
    w = int(node.w)
    if w < 60:
        w = 60
    current_lines = lines_for_width(w)
    if current_lines > max_lines:
        for cand in range(w, max_w + 1, max(10, widen_step)):
            if lines_for_width(cand) <= max_lines:
                w = cand
                break
        else:
            w = max_w
    node.w = max(int(node.w), w)

    usable = max(1, int(node.w) - padding_x * 2)
    chars_per_line = max(1, int(usable / max(1.0, char_w)))
    lines = _wrap_line_count(label, chars_per_line)

    required_h = padding_y * 2 + lines * (font_px + line_spacing) + 2
    # Soft cap: if the label is extremely long, height may still exceed.
    # We still honor correctness (no overflow) over aesthetics.
    if required_h > max_h_soft:
        node.h = max(int(node.h), required_h)
    else:
        node.h = max(int(node.h), required_h)


def _auto_group_size_for_nodes(children: List[Node], cfg: Dict[str, Any]) -> Tuple[int, int]:
    auto = cfg["layout"]["auto"]
    child_count = max(1, len(children))
    cols = max(1, min(int(auto["max_cols"]), child_count))
    rows = max(1, ceil(child_count / cols))

    gap_x = int(auto["node_gap_x"])
    gap_y = int(auto["node_gap_y"])
    pad_x = int(auto["group_padding_x"])
    pad_y = int(auto["group_padding_y"])
    header_h = int(auto["group_header_h"])

    max_node_w = max(int(cfg["layout"]["node_default_size"]["w"]), max((n.w for n in children), default=0))
    max_node_h = max(int(cfg["layout"]["node_default_size"]["h"]), max((n.h for n in children), default=0))

    w = pad_x * 2 + cols * max_node_w + max(0, cols - 1) * gap_x
    h = header_h + pad_y * 2 + rows * max_node_h + max(0, rows - 1) * gap_y
    return (max(int(auto["group_min_w"]), w), max(int(auto["group_min_h"]), h))


def _auto_place_children(
    group: Group,
    missing_children: List[Node],
    cfg: Dict[str, Any],
) -> None:
    if not missing_children:
        return

    auto = cfg["layout"]["auto"]
    pad_x = int(auto["group_padding_x"])
    pad_y = int(auto["group_padding_y"])
    header_h = int(auto["group_header_h"])
    gap_x = int(auto["node_gap_x"])
    gap_y = int(auto["node_gap_y"])

    cols = max(1, min(int(auto["max_cols"]), len(group.children)))
    rows = max(1, ceil(len(group.children) / cols))

    # Keep a tidy grid: use the largest node size in the group as the cell size.
    node_w = max(int(cfg["layout"]["node_default_size"]["w"]), max((n.w for n in group.children), default=0))
    node_h = max(int(cfg["layout"]["node_default_size"]["h"]), max((n.h for n in group.children), default=0))

    avail_w = max(1, group.w - pad_x * 2 - max(0, cols - 1) * gap_x)
    avail_h = max(1, group.h - header_h - pad_y * 2 - max(0, rows - 1) * gap_y)

    cell_w = max(node_w, avail_w // cols)
    cell_h = max(node_h, avail_h // rows)

    for idx, node in enumerate(group.children):
        if node.x >= 0 and node.y >= 0:
            continue
        row = idx // cols
        col = idx % cols
        node.x = group.x + pad_x + col * (cell_w + gap_x)
        node.y = group.y + header_h + pad_y + row * (cell_h + gap_y)
        # Never shrink (text fitting), but ensure we don't exceed the group's inner box.
        node.w = max(node.w, min(cell_w, max(1, group.w - pad_x * 2)))
        node.h = max(node.h, min(cell_h, max(1, group.h - header_h - pad_y * 2)))


def _title_reserved_height(title: str, cfg: Dict[str, Any]) -> int:
    title_cfg = (cfg.get("layout", {}) or {}).get("title", {})
    enabled = bool((title_cfg or {}).get("enabled", True))
    if not enabled:
        return 0
    if not title.strip():
        return 0
    pad_y = int((title_cfg or {}).get("padding_y", 18))
    size = int(cfg.get("layout", {}).get("font", {}).get("title_size", 34))
    return max(0, pad_y * 2 + size)


def _auto_place_groups(
    groups: List[Group],
    cfg: Dict[str, Any],
    canvas_w: int,
    canvas_h: int,
    direction: Direction,
    title: str,
) -> None:
    auto = cfg["layout"]["auto"]
    margin_x = int(auto["margin_x"])
    margin_y = int(auto["margin_y"]) + _title_reserved_height(title, cfg)
    group_gap_x = int(auto["group_gap_x"])
    group_gap_y = int(auto["group_gap_y"])

    x = margin_x
    y = margin_y
    for g in groups:
        if g.w <= 0 or g.h <= 0:
            g.w, g.h = _auto_group_size(max(1, len(g.children)), cfg)

        if g.x < 0 or g.y < 0:
            g.x, g.y = x, y

        if direction == "top-to-bottom":
            y = g.y + g.h + group_gap_y
        elif direction == "left-to-right":
            x = g.x + g.w + group_gap_x
        else:  # bottom-to-top
            y = g.y - g.h - group_gap_y

        # Clamp origin so the group stays inside canvas. (Avoid "右侧贴边但整体越界"这类 P0。)
        g.x = max(0, min(g.x, max(0, canvas_w - g.w)))
        g.y = max(0, min(g.y, max(0, canvas_h - g.h)))


def _auto_edges(groups: List[Group]) -> List[Edge]:
    edges: List[Edge] = []
    prev_last: Optional[Node] = None
    for g in groups:
        if not g.children:
            continue
        if prev_last is not None:
            edges.append(Edge(source=prev_last.id, target=g.children[0].id, style="solid", label=""))
        prev_last = g.children[-1]
    return edges


def load_schematic_spec(data: Dict[str, Any], config: Dict[str, Any]) -> SchematicSpec:
    root = data.get("schematic") if isinstance(data.get("schematic"), dict) else data
    root = _require_mapping(root, "schematic")

    title = _require_str(root.get("title"), "schematic.title")

    direction_raw = root.get("direction", config["layout"].get("direction", "top-to-bottom"))
    if direction_raw not in ("top-to-bottom", "left-to-right", "bottom-to-top"):
        raise ValueError(f"schematic.direction 不合法：{direction_raw}")
    direction: Direction = direction_raw  # type: ignore[assignment]

    canvas_explicit = isinstance(root.get("canvas"), dict)
    canvas = root.get("canvas") if canvas_explicit else {}
    canvas = _require_mapping(canvas, "schematic.canvas")
    canvas_w = int(canvas.get("width", config["renderer"]["canvas"]["width_px"]))
    canvas_h = int(canvas.get("height", config["renderer"]["canvas"]["height_px"]))
    if canvas_w <= 0 or canvas_h <= 0:
        raise ValueError("schematic.canvas.width/height 必须为正整数")

    groups_raw = _require_list(root.get("groups"), "schematic.groups")
    groups: List[Group] = []

    node_ids: set[str] = set()
    group_ids: set[str] = set()

    default_node_w = int(config["layout"]["node_default_size"]["w"])
    default_node_h = int(config["layout"]["node_default_size"]["h"])

    for i, g_raw in enumerate(groups_raw, start=1):
        g = _require_mapping(g_raw, f"schematic.groups[{i}]")
        gid = _require_id(g.get("id"), f"schematic.groups[{i}].id")
        if gid in group_ids:
            raise ValueError(f"重复 group id：{gid}")
        group_ids.add(gid)

        label = _require_str(g.get("label"), f"schematic.groups[{i}].label")
        gstyle = _group_style(g.get("style"), f"schematic.groups[{i}]")
        gx, gy = _parse_position(g, f"schematic.groups[{i}]")
        gw, gh = _parse_size(g, f"schematic.groups[{i}]")

        children_raw = _require_list(g.get("children"), f"schematic.groups[{i}].children")
        children: List[Node] = []
        missing_children: List[Node] = []
        for j, c_raw in enumerate(children_raw, start=1):
            c = _require_mapping(c_raw, f"schematic.groups[{i}].children[{j}]")
            nid = _require_id(c.get("id"), f"schematic.groups[{i}].children[{j}].id")
            if nid in node_ids:
                raise ValueError(f"重复 node id：{nid}")
            node_ids.add(nid)

            nlabel = _require_str(c.get("label"), f"schematic.groups[{i}].children[{j}].label")
            nkind = _node_kind(c.get("kind"), f"schematic.groups[{i}].children[{j}]")

            nx, ny = _parse_position(c, f"schematic.groups[{i}].children[{j}]")
            nw, nh = _parse_size(c, f"schematic.groups[{i}].children[{j}]")

            node = Node(
                id=nid,
                label=nlabel,
                kind=nkind,
                x=nx if nx is not None else -1,
                y=ny if ny is not None else -1,
                w=nw if nw is not None else default_node_w,
                h=nh if nh is not None else default_node_h,
                group_id=gid,
            )
            _autosize_node_for_text(node, config)
            if nx is None or ny is None:
                missing_children.append(node)
            children.append(node)

        # If group size is missing or too small, expand it to fit the (possibly autosized) nodes.
        need_w, need_h = _auto_group_size_for_nodes(children, config)
        if gw is None:
            gw = need_w
        else:
            gw = max(gw, need_w)
        if gh is None:
            gh = need_h
        else:
            gh = max(gh, need_h)

        group = Group(
            id=gid,
            label=label,
            x=gx if gx is not None else -1,
            y=gy if gy is not None else -1,
            w=gw if gw is not None else -1,
            h=gh if gh is not None else -1,
            style=gstyle,
            children=children,
        )
        groups.append(group)

    _auto_place_groups(groups, config, canvas_w, canvas_h, direction, title)

    for group in groups:
        _auto_place_children(group, [n for n in group.children if n.x < 0 or n.y < 0], config)

    # Auto-expand canvas to avoid overflow after autosizing nodes/groups.
    # This is a deterministic safety net; users can still override by shrinking in their spec if desired.
    expand_canvas = bool((config.get("layout", {}) or {}).get("auto_expand_canvas", True))
    if expand_canvas and groups:
        auto = config.get("layout", {}).get("auto", {})
        margin_x = int(auto.get("margin_x", 80))
        margin_y = int(auto.get("margin_y", 80))
        right = max(g.x + g.w for g in groups)
        bottom = max(g.y + g.h for g in groups)
        canvas_w = max(canvas_w, int(right + margin_x))
        canvas_h = max(canvas_h, int(bottom + margin_y))

    # Optional "shrink to content" to avoid extreme aspect ratios when user-specified
    # canvas is much larger than the actual content bounds.
    fit_cfg = (config.get("layout", {}) or {}).get("canvas_fit", {})
    if isinstance(fit_cfg, dict) and bool(fit_cfg.get("enabled", True)) and groups:
        shrink = bool(fit_cfg.get("shrink_to_content", True))
        try:
            trigger = float(fit_cfg.get("shrink_trigger_ratio", 1.15))
        except Exception:
            trigger = 1.15
        trigger = max(1.0, trigger)

        auto = config.get("layout", {}).get("auto", {}) or {}
        margin_x = int(auto.get("margin_x", 80))
        margin_y = int(auto.get("margin_y", 80))
        right = max(g.x + g.w for g in groups)
        bottom = max(g.y + g.h for g in groups)

        need_w = int(right + margin_x)
        need_h = int(bottom + margin_y)

        # Only enforce renderer defaults as minimum when canvas is not explicitly specified in spec.
        if not canvas_explicit:
            need_w = max(need_w, int(config.get("renderer", {}).get("canvas", {}).get("width_px", need_w)))
            need_h = max(need_h, int(config.get("renderer", {}).get("canvas", {}).get("height_px", need_h)))

        if shrink and need_w > 0 and canvas_w > need_w and (canvas_w / max(1, need_w)) >= trigger:
            canvas_w = need_w
        else:
            canvas_w = max(canvas_w, need_w)

        if shrink and need_h > 0 and canvas_h > need_h and (canvas_h / max(1, need_h)) >= trigger:
            canvas_h = need_h
        else:
            canvas_h = max(canvas_h, need_h)

    node_index = {n.id: n for g in groups for n in g.children}

    edges_raw = root.get("edges")
    edges: List[Edge] = []
    if isinstance(edges_raw, list) and edges_raw:
        for i, e_raw in enumerate(edges_raw, start=1):
            e = _require_mapping(e_raw, f"schematic.edges[{i}]")
            source = _require_id(e.get("from"), f"schematic.edges[{i}].from")
            target = _require_id(e.get("to"), f"schematic.edges[{i}].to")
            style = _edge_style(e.get("style"), f"schematic.edges[{i}]")
            label = e.get("label", "")
            if not isinstance(label, str):
                raise ValueError(f"schematic.edges[{i}].label 必须是字符串")
            if source not in node_index:
                raise ValueError(f"schematic.edges[{i}] source 节点不存在：{source}")
            if target not in node_index:
                raise ValueError(f"schematic.edges[{i}] target 节点不存在：{target}")
            edges.append(Edge(source=source, target=target, style=style, label=label.strip()))
    else:
        edges = _auto_edges(groups)

    # Warning-only: conservative “术语一致性”提示（不影响解析结果）。
    # 目的：帮助用户在规划阶段避免同一概念出现多种写法（会降低评审阅读一致性）。
    try:
        from utils import warn  # local import to keep spec_parser usable as a standalone module

        def term_key(s: str) -> str:
            x = (s or "").strip().lower()
            x = re.sub(r"[\s\-_:/,，。;；（）()【】\[\]{}<>“”\"'`]+", "", x)
            x = re.sub(r"(数据|信息|特征|方法|算法|模型|模块|系统|平台|流程)$", "", x)
            return x

        labels: List[str] = []
        for g in groups:
            if g.label.strip():
                labels.append(g.label.strip())
            for n in g.children:
                if n.label.strip():
                    labels.append(n.label.strip())

        buckets: Dict[str, List[str]] = {}
        for lab in labels:
            k = term_key(lab)
            if not k:
                continue
            buckets.setdefault(k, [])
            if lab not in buckets[k]:
                buckets[k].append(lab)

        for _k, vals in buckets.items():
            if len(vals) <= 1:
                continue
            warn("术语可能不一致（疑似同一概念多种写法）： " + " / ".join(vals[:4]))
    except Exception:
        # Never block parsing due to warning logic.
        pass

    return SchematicSpec(
        title=title,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        direction=direction,
        groups=groups,
        edges=edges,
    )


def main() -> None:
    import argparse

    from utils import dump_yaml, fatal, load_yaml

    p = argparse.ArgumentParser(description="Parse/normalize schematic spec YAML.")
    p.add_argument("--spec", required=True, type=str)
    p.add_argument("--config", required=True, type=str)
    p.add_argument("--out", required=False, type=str, default=None)
    args = p.parse_args()

    try:
        cfg = load_yaml(Path(args.config))
        raw = load_yaml(Path(args.spec))
        normalized = load_schematic_spec(raw, cfg).to_dict()
    except Exception as exc:
        fatal(str(exc))
    text = dump_yaml(normalized)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
