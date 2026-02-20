from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from spec_parser import Group, Node, SchematicSpec
from routing import rect_expand, route_edge_points
from utils import is_safe_relative_path, load_yaml, skill_root, write_text


def _xml_escape(s: str) -> str:
    # draw.io stores rich text (e.g. <br>) inside mxCell@value attribute values.
    # The XML must remain well-formed, so any "<" / ">" inside the attribute
    # must be escaped as &lt; / &gt;.
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _load_palette(config: Dict[str, Any]) -> Dict[str, Any]:
    color_cfg = config["color_scheme"]
    scheme_name = color_cfg["name"]

    if "file" in color_cfg and isinstance(color_cfg["file"], str):
        palette_file = color_cfg["file"]
        if not is_safe_relative_path(palette_file):
            raise ValueError(
                "color_scheme.file 必须是 skill 内的安全相对路径（不得包含 `..` 或绝对/盘符路径）："
                f"{palette_file!r}"
            )
        palette_path = skill_root() / palette_file
        payload = load_yaml(palette_path)
        presets = payload.get("color_schemes", {})
    else:
        presets = color_cfg.get("presets", {})

    if scheme_name not in presets:
        raise ValueError(f"未找到配色方案：{scheme_name}")
    return presets[scheme_name]


def _group_style(group_style: str, palette: Dict[str, Any], config: Dict[str, Any]) -> str:
    group_colors = palette.get("group_bg", {"fill": "#FAFAFA", "stroke": "#CCCCCC"})
    fill = group_colors.get("fill", "#FAFAFA")
    stroke = group_colors.get("stroke", "#CCCCCC")
    text = palette.get("text", "#1F1F1F")
    font_size = int(config["layout"]["font"]["group_label_size"])
    stroke_w = int(config["renderer"]["stroke"]["width_px"])
    header_h = int(((config.get("layout", {}) or {}).get("auto", {}) or {}).get("group_header_h", 56))

    # Use swimlane to render a consistent, print-friendly “group header bar”.
    # This looks better than the default container label for long CJK titles (e.g. “数据与特征（输入层）”).
    base = (
        "swimlane;rounded=1;whiteSpace=wrap;html=1;container=1;collapsible=0;"
        "childLayout=none;"
        f"startSize={header_h};"
        f"fillColor={fill};swimlaneFillColor={fill};strokeColor={stroke};"
        f"fontColor={text};fontSize={font_size};fontStyle=1;strokeWidth={stroke_w};"
        "align=center;verticalAlign=middle;"
        "spacingLeft=14;spacingRight=14;spacingTop=8;spacingBottom=8;"
    )
    if group_style == "dashed-border":
        return base + "dashed=1;dashPattern=8 4;"
    if group_style == "background-fill":
        return base + "dashed=0;"
    return base + "dashed=0;"


def _node_shape(kind: str) -> str:
    if kind == "decision":
        return "shape=rhombus;perimeter=rhombusPerimeter;"
    if kind == "risk":
        return "shape=hexagon;perimeter=hexagonPerimeter2;"
    return "rounded=1;"


def _node_style(kind: str, palette: Dict[str, Any], config: Dict[str, Any]) -> str:
    selected = palette.get(kind, palette.get("primary", {"fill": "#D9E8FF", "stroke": "#2F5597"}))
    fill = selected.get("fill", "#D9E8FF")
    stroke = selected.get("stroke", "#2F5597")
    font_size = int(config["layout"]["font"]["node_label_size"])
    stroke_w = int(config["renderer"]["stroke"]["width_px"])
    text = palette.get("text", "#1F1F1F")

    return (
        "whiteSpace=wrap;html=1;"
        + _node_shape(kind)
        + f"fillColor={fill};strokeColor={stroke};"
        + f"fontColor={text};fontSize={font_size};"
        # Extra spacing reduces "贴边/拥挤" and makes exports more publication-ready.
        + f"strokeWidth={stroke_w};align=center;verticalAlign=middle;"
        + "spacing=10;spacingLeft=14;spacingRight=14;spacingTop=10;spacingBottom=10;"
    )


def _edge_style(style: str, palette: Dict[str, Any], config: Dict[str, Any], routing_mode: str) -> str:
    arrow = palette.get("arrow", "#2F5597")
    text = palette.get("text", "#000000")
    edge_font = int(config["layout"]["font"].get("edge_label_size", config["layout"]["font"]["node_label_size"]))
    # Prefer print-friendly settings for edge labels.
    bg = str(config.get("renderer", {}).get("background", "#FFFFFF"))
    edge_style = "straightEdgeStyle" if routing_mode == "straight" else "orthogonalEdgeStyle"
    base = (
        f"edgeStyle={edge_style};rounded=1;orthogonalLoop=1;"
        f"strokeColor={arrow};"
        f"fontSize={edge_font};fontColor={text};fontStyle=0;labelBackgroundColor={bg};labelBorderColor=none;labelPadding=4;"
    )
    if style == "dashed":
        return base + "strokeWidth=2;dashed=1;dashPattern=8 4;endArrow=open;endFill=0;"
    if style == "thick":
        return base + "strokeWidth=4;dashed=0;endArrow=block;endFill=1;"
    return base + "strokeWidth=2;dashed=0;endArrow=block;endFill=1;"


def _graph_header(spec: SchematicSpec) -> List[str]:
    page_w = max(850, spec.canvas_width)
    page_h = max(1100, spec.canvas_height)
    return [
        '<mxfile host="app.diagrams.net" modified="auto" agent="nsfc-schematic">',
        '  <diagram name="schematic" id="schematic">',
        (
            "    <mxGraphModel dx=\"1200\" dy=\"800\" grid=\"1\" gridSize=\"10\" guides=\"1\" "
            "tooltips=\"1\" connect=\"1\" arrows=\"1\" fold=\"1\" page=\"1\" pageScale=\"1\" "
            f"pageWidth=\"{page_w}\" pageHeight=\"{page_h}\" math=\"0\" shadow=\"0\">"
        ),
        "      <root>",
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>',
    ]


def _graph_footer() -> List[str]:
    return [
        "      </root>",
        "    </mxGraphModel>",
        "  </diagram>",
        "</mxfile>",
    ]


def _write_group(lines: List[str], group: Group, palette: Dict[str, Any], config: Dict[str, Any]) -> None:
    style = _group_style(group.style, palette, config)
    gid = f"group_{group.id}"
    lines.append(
        f'        <mxCell id="{gid}" value="{_xml_escape(group.label)}" style="{style}" vertex="1" parent="1">'
    )
    lines.append(
        f'          <mxGeometry x="{group.x}" y="{group.y}" width="{group.w}" height="{group.h}" as="geometry"/>'
    )
    lines.append("        </mxCell>")


def _write_node(
    lines: List[str],
    node: Node,
    group: Group,
    palette: Dict[str, Any],
    config: Dict[str, Any],
) -> None:
    style = _node_style(node.kind, palette, config)
    parent = f"group_{node.group_id}"
    lines.append(
        f'        <mxCell id="{node.id}" value="{_xml_escape(node.label)}" style="{style}" vertex="1" parent="{parent}">'
    )
    # draw.io group child coordinates are relative to group.
    group_offset_x = node.x - group.x
    group_offset_y = node.y - group.y
    lines.append(
        f'          <mxGeometry x="{group_offset_x}" y="{group_offset_y}" width="{node.w}" height="{node.h}" as="geometry"/>'
    )
    lines.append("        </mxCell>")


def _write_title(lines: List[str], spec: SchematicSpec, palette: Dict[str, Any], config: Dict[str, Any]) -> None:
    title_cfg = (config.get("layout", {}) or {}).get("title", {})
    enabled = bool((title_cfg or {}).get("enabled", True))
    if not enabled:
        return
    if not spec.title.strip():
        return

    title_size = int(config["layout"]["font"]["title_size"])
    pad_y = int((title_cfg or {}).get("padding_y", 18))
    title_h = max(1, pad_y * 2 + title_size)
    text = palette.get("text", "#1F1F1F")

    style = (
        "text;html=1;whiteSpace=wrap;rounded=0;"
        "align=center;verticalAlign=middle;"
        "strokeColor=none;fillColor=none;"
        f"fontSize={title_size};fontStyle=1;fontColor={text};"
    )
    lines.append(
        f'        <mxCell id="title_cell" value="{_xml_escape(spec.title)}" style="{style}" vertex="1" parent="1">'
    )
    lines.append(f'          <mxGeometry x="0" y="0" width="{spec.canvas_width}" height="{title_h}" as="geometry"/>')
    lines.append("        </mxCell>")


def write_schematic_drawio(spec: SchematicSpec, config: Dict[str, Any], out_drawio: Path) -> Path:
    palette = _load_palette(config)

    lines: List[str] = []
    lines.extend(_graph_header(spec))
    _write_title(lines, spec, palette, config)

    for group in spec.groups:
        _write_group(lines, group, palette, config)

    # Z-order: groups (background) -> edges -> nodes (foreground, avoid lines covering text).
    routing_raw = str(config.get("renderer", {}).get("internal_routing", "orthogonal"))
    mode = "straight" if routing_raw == "straight" else "orthogonal"
    routing_cfg = ((config.get("layout", {}) or {}).get("routing", {}) or {}) if isinstance((config.get("layout", {}) or {}).get("routing", {}), dict) else {}
    obstacle_pad = int(routing_cfg.get("obstacle_padding_px", 10))
    avoid_headers = bool(routing_cfg.get("avoid_group_headers", True))
    header_h = int(((config.get("layout", {}) or {}).get("auto", {}) or {}).get("group_header_h", 56))

    node_lookup: Dict[str, Tuple[int, int, int, int]] = {}
    for g in spec.groups:
        for n in g.children:
            node_lookup[n.id] = (n.x, n.y, n.x + n.w, n.y + n.h)

    header_obstacles: List[Tuple[int, int, int, int]] = []
    if avoid_headers:
        pad = max(0, obstacle_pad // 2)
        for g in spec.groups:
            header_obstacles.append(rect_expand((g.x, g.y, g.x + g.w, g.y + header_h), pad))

    edge_idx = 1
    for edge in spec.edges:
        edge_style = _edge_style(edge.style, palette, config, mode)
        eid = f"edge_{edge_idx}"
        edge_idx += 1
        label = _xml_escape(edge.label) if edge.label else ""
        lines.append(
            f'        <mxCell id="{eid}" value="{label}" style="{edge_style}" edge="1" parent="1" source="{edge.source}" target="{edge.target}">'
        )
        src = node_lookup.get(edge.source)
        tgt = node_lookup.get(edge.target)
        if mode == "orthogonal" and src and tgt:
            obs = [rect_expand(r, obstacle_pad) for nid, r in node_lookup.items() if nid not in {edge.source, edge.target}]
            obs.extend(header_obstacles)
            pts = route_edge_points(
                spec.direction,  # type: ignore[arg-type]
                mode,  # type: ignore[arg-type]
                src,
                tgt,
                obs,
                canvas_w=spec.canvas_width,
                canvas_h=spec.canvas_height,
            )
            mid = pts[1:-1]
            if mid:
                lines.append('          <mxGeometry relative="1" as="geometry">')
                lines.append('            <Array as="points">')
                for x, y in mid:
                    lines.append(f'              <mxPoint x="{int(x)}" y="{int(y)}"/>')
                lines.append("            </Array>")
                lines.append("          </mxGeometry>")
            else:
                lines.append('          <mxGeometry relative="1" as="geometry"/>')
        else:
            lines.append('          <mxGeometry relative="1" as="geometry"/>')
        lines.append("        </mxCell>")

    for group in spec.groups:
        for node in group.children:
            _write_node(lines, node, group, palette, config)

    lines.extend(_graph_footer())
    write_text(out_drawio, "\n".join(lines) + "\n")
    return out_drawio


def main() -> None:
    import argparse

    from spec_parser import load_schematic_spec
    from utils import fatal, load_yaml

    p = argparse.ArgumentParser(description="Convert schematic spec YAML to draw.io XML.")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    try:
        cfg = load_yaml(args.config)
        spec_data = load_yaml(args.spec)
        spec = load_schematic_spec(spec_data, cfg)
        write_schematic_drawio(spec, cfg, args.out)
    except Exception as exc:
        fatal(str(exc))


if __name__ == "__main__":
    main()
