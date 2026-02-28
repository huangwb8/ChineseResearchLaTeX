from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from utils import write_text


@dataclass(frozen=True)
class DrawioNode:
    id: str
    value: str
    x: int
    y: int
    w: int
    h: int
    style: str
    parent: str = "1"


@dataclass(frozen=True)
class DrawioEdge:
    id: str
    source: str
    target: str
    style: str
    value: str = ""
    # Optional absolute waypoints (x, y) in page coordinate system.
    waypoints: Optional[Sequence[Tuple[int, int]]] = None
    parent: str = "1"


def _xml_escape(s: str) -> str:
    # draw.io uses HTML labels when `html=1`. Keep line breaks via `<br>`,
    # but *must* XML-escape it as `&lt;br&gt;` inside the attribute.
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_drawio(path: Path, nodes: List[DrawioNode], edges: List[DrawioEdge]) -> None:
    # Minimal draw.io mxGraphModel that opens in diagrams.net.
    parts: List[str] = []
    parts.append('<mxfile host="app.diagrams.net">')
    parts.append('  <diagram name="roadmap" id="roadmap">')
    parts.append('    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">')
    parts.append("      <root>")
    parts.append('        <mxCell id="0"/>')
    parts.append('        <mxCell id="1" parent="0"/>')
    for n in nodes:
        parts.append(
            f'        <mxCell id="{n.id}" value="{_xml_escape(n.value)}" style="{n.style}" vertex="1" parent="{n.parent}">'
        )
        parts.append(
            f'          <mxGeometry x="{n.x}" y="{n.y}" width="{n.w}" height="{n.h}" as="geometry"/>'
        )
        parts.append("        </mxCell>")
    for e in edges:
        parts.append(
            f'        <mxCell id="{e.id}" value="{_xml_escape(e.value)}" style="{e.style}" edge="1" parent="{e.parent}" source="{e.source}" target="{e.target}">'
        )
        if e.waypoints:
            parts.append('          <mxGeometry relative="1" as="geometry">')
            parts.append('            <Array as="points">')
            for x, y in e.waypoints:
                parts.append(f'              <mxPoint x="{int(x)}" y="{int(y)}"/>')
            parts.append("            </Array>")
            parts.append("          </mxGeometry>")
        else:
            parts.append('          <mxGeometry relative="1" as="geometry"/>')
        parts.append("        </mxCell>")
    parts.append("      </root>")
    parts.append("    </mxGraphModel>")
    parts.append("  </diagram>")
    parts.append("</mxfile>")
    write_text(path, "\n".join(parts) + "\n")


def default_box_style(fill: str, stroke: str, font_size: int, font_color: str = "#1F1F1F") -> str:
    return (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};"
        f"fontSize={font_size};fontColor={font_color};"
    )


def default_bar_style(fill: str, font_size: int, font_color: str = "#FFFFFF") -> str:
    return (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={fill};"
        f"fontSize={font_size};fontColor={font_color};"
    )


def default_edge_style(stroke: str = "#2F5597", width: int = 3) -> str:
    # Keep style explicit so exported PNG/SVG/PDF reliably shows arrows.
    return (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
        "endArrow=block;endFill=1;"
        f"strokeColor={stroke};strokeWidth={int(width)};"
    )
