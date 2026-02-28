from __future__ import annotations

import math
import os
import platform
from pathlib import Path
from shutil import which
from subprocess import CompletedProcess, run
from typing import Any, Dict, List, Optional, Tuple

from spec_parser import SchematicSpec
from routing import rect_expand, route_edge_points
from utils import FontChoice, hex_to_rgb, pick_font, warn, write_text


def _require_pillow() -> tuple[Any, Any, Any]:
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "缺少依赖 Pillow，无法使用内部渲染兜底。\n"
            "解决方案：\n"
            "- 方案1：安装 Pillow：python3 -m pip install pillow\n"
            "- 方案2：安装 draw.io CLI 并关闭内部兜底：config.yaml:renderer.allow_internal_fallback=false\n"
            f"原始错误：{exc}"
        ) from exc
    return Image, ImageDraw, ImageFont


def _drawio_cli_candidates() -> List[str]:
    # Common candidates across OSes:
    # - "drawio"/"draw.io": if user added it to PATH
    # - macOS Desktop app bundle binary
    # - Linux packages sometimes expose "drawio" or "draw.io"
    return [
        "drawio",
        "draw.io",
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        "/Applications/draw.io.app/Contents/MacOS/drawio",
    ]


def detect_drawio_cli() -> Optional[str]:
    # For testing/debugging: force internal renderer even if draw.io CLI exists.
    if os.environ.get("NSFC_SCHEMATIC_FORCE_INTERNAL_RENDER", "").strip() in {"1", "true", "TRUE", "yes", "YES"}:
        return None
    for cmd in _drawio_cli_candidates():
        if which(cmd) or Path(cmd).exists():
            return cmd
    return None


_DRAWIO_CLI_CACHE: Optional[str] = None
_DRAWIO_CLI_CHECKED: bool = False
_WARNED_NO_DRAWIO: bool = False


def ensure_drawio_cli(config: Dict[str, Any]) -> Optional[str]:
    """
    Try to find draw.io CLI. Optionally auto-install on macOS if enabled in config.
    This function is cached per-process to avoid repeated installation attempts.
    """
    global _DRAWIO_CLI_CACHE, _DRAWIO_CLI_CHECKED
    if _DRAWIO_CLI_CHECKED:
        return _DRAWIO_CLI_CACHE

    cmd = detect_drawio_cli()
    if cmd:
        _DRAWIO_CLI_CACHE = cmd
        _DRAWIO_CLI_CHECKED = True
        return cmd

    drawio_cfg = (config.get("renderer", {}) or {}).get("drawio", {})
    auto_install = bool(drawio_cfg.get("auto_install_macos", False))
    method = str(drawio_cfg.get("install_method_macos", "brew"))

    if auto_install and platform.system() == "Darwin":
        if method != "brew":
            warn("draw.io CLI 缺失：已启用 auto_install_macos，但 install_method_macos != brew，跳过自动安装。")
        elif which("brew") is None:
            warn("draw.io CLI 缺失：已启用 auto_install_macos，但未检测到 Homebrew（brew），跳过自动安装。")
        else:
            warn("未找到 draw.io CLI，尝试使用 Homebrew 安装 draw.io（brew install --cask drawio）...")
            result = _run_cli(["brew", "install", "--cask", "drawio"])
            if result.returncode != 0:
                warn(
                    "draw.io 自动安装失败，将回退到内部渲染兜底。\n"
                    f"stdout: {result.stdout.strip()}\n"
                    f"stderr: {result.stderr.strip()}"
                )
            cmd = detect_drawio_cli()

    _DRAWIO_CLI_CACHE = cmd
    _DRAWIO_CLI_CHECKED = True
    return cmd


def drawio_install_hints() -> List[str]:
    # Plain text lines for reports/logs (no markdown assumptions here).
    lines: List[str] = []
    sysname = platform.system()
    if sysname == "Darwin":
        lines.extend(
            [
                "macOS:",
                "  推荐：brew install --cask drawio",
                "  或手动安装 draw.io Desktop 到 /Applications，然后使用：/Applications/draw.io.app/Contents/MacOS/draw.io",
            ]
        )
    elif sysname == "Windows":
        lines.extend(
            [
                "Windows:",
                "  安装 draw.io Desktop（diagrams.net），并将其 CLI 加入 PATH（或在配置中写入完整路径）",
            ]
        )
    else:
        lines.extend(
            [
                "Linux:",
                "  安装 draw.io（diagrams.net）桌面版或包管理器版本，并确保 drawio/draw.io 可执行文件在 PATH 中",
            ]
        )
    return lines


def _run_cli(cmd: List[str]) -> CompletedProcess[str]:
    return run(cmd, capture_output=True, text=True, check=False)


def _export_with_drawio_cli(
    drawio_cmd: str,
    drawio_path: Path,
    output_path: Path,
    fmt: str,
    width: int,
    height: int,
    border: int,
) -> None:
    cmd = [drawio_cmd, "-x", "-f", fmt, "--border", str(border)]
    if fmt == "png":
        cmd.extend(["--width", str(width), "--height", str(height)])
    cmd.extend(["-o", str(output_path), str(drawio_path)])

    result = _run_cli(cmd)
    if result.returncode != 0 and fmt == "png":
        # Backward-compat fallback: some draw.io CLI builds may not support --height.
        cmd2 = [drawio_cmd, "-x", "-f", fmt, "--border", str(border), "--width", str(width)]
        cmd2.extend(["-o", str(output_path), str(drawio_path)])
        result2 = _run_cli(cmd2)
        if result2.returncode == 0:
            return
        raise RuntimeError(
            "draw.io CLI 渲染失败\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}\n"
            "\n"
            "已尝试回退（不使用 --height）仍失败\n"
            f"cmd2: {' '.join(cmd2)}\n"
            f"stdout2: {result2.stdout.strip()}\n"
            f"stderr2: {result2.stderr.strip()}"
        )
    if result.returncode != 0:
        raise RuntimeError(
            "draw.io CLI 渲染失败\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )


def _ensure_png_canvas_size(
    png_path: Path,
    target_w: int,
    target_h: int,
    bg_rgb: Tuple[int, int, int],
) -> None:
    """
    Ensure exported PNG matches spec canvas size.

    draw.io CLI may occasionally export with an unexpected height when only width is constrained.
    We pad/crop (centered) to keep downstream evaluation stable and publish-ready.
    """
    from PIL import Image  # type: ignore

    img = Image.open(png_path)
    try:
        w, h = img.size
        if (w, h) == (target_w, target_h):
            return

        # Crop if needed (center-crop), then pad to target (centered).
        x0 = 0 if w <= target_w else max(0, (w - target_w) // 2)
        y0 = 0 if h <= target_h else max(0, (h - target_h) // 2)
        x1 = min(w, x0 + target_w)
        y1 = min(h, y0 + target_h)
        cropped = img.crop((x0, y0, x1, y1))

        out = Image.new("RGB", (target_w, target_h), bg_rgb)
        cx, cy = cropped.size
        px = max(0, (target_w - cx) // 2)
        py = max(0, (target_h - cy) // 2)
        out.paste(cropped, (px, py))
        out.save(png_path)
    finally:
        try:
            img.close()
        except Exception:
            pass


def _load_font(font_choice: FontChoice) -> Any:
    _, _, ImageFont = _require_pillow()
    if font_choice.path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(str(font_choice.path), font_choice.size)
    except Exception:
        return ImageFont.load_default()


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _wrap_text(
    draw: Any,
    text: str,
    font: Any,
    max_width: int,
) -> List[str]:
    rows = []
    for part in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not part.strip():
            rows.append("")
            continue
        current = ""
        for ch in part.strip():
            cand = ch if not current else current + ch
            box = draw.textbbox((0, 0), cand, font=font)
            if box[2] <= max_width:
                current = cand
            else:
                if current:
                    rows.append(current)
                    current = ch
                else:
                    rows.append(ch)
                    current = ""
        if current:
            rows.append(current)
    return rows


def _draw_dashed_line(
    draw: Any,
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    color: Tuple[int, int, int],
    width: int,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    length = max(1, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5))
    step = 14
    for i in range(0, length, step * 2):
        t0 = i / length
        t1 = min(1.0, (i + step) / length)
        sx = int(x1 + (x2 - x1) * t0)
        sy = int(y1 + (y2 - y1) * t0)
        ex = int(x1 + (x2 - x1) * t1)
        ey = int(y1 + (y2 - y1) * t1)
        draw.line([(sx, sy), (ex, ey)], fill=color, width=width)


def _draw_arrow_head(
    draw: Any,
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    color: Tuple[int, int, int],
    size: int,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    vx = x2 - x1
    vy = y2 - y1
    norm = max(1.0, (vx * vx + vy * vy) ** 0.5)
    ux = vx / norm
    uy = vy / norm
    px = -uy
    py = ux

    tip = (x2, y2)
    left = (int(x2 - ux * size + px * (size * 0.6)), int(y2 - uy * size + py * (size * 0.6)))
    right = (int(x2 - ux * size - px * (size * 0.6)), int(y2 - uy * size - py * (size * 0.6)))
    draw.polygon([tip, left, right], fill=color)


def _shape_colors(kind: str, palette: Dict[str, Any]) -> Tuple[str, str]:
    selected = palette.get(kind, palette.get("primary", {"fill": "#D9E8FF", "stroke": "#2F5597"}))
    return selected.get("fill", "#D9E8FF"), selected.get("stroke", "#2F5597")


def _svg_marker_def(fill_rgb: Tuple[int, int, int]) -> str:
    fill = f"rgb({fill_rgb[0]},{fill_rgb[1]},{fill_rgb[2]})"
    return (
        "  <defs>\n"
        '    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        f'      <path d="M 0 0 L 10 5 L 0 10 z" fill="{fill}"/>\n'
        "    </marker>\n"
        "  </defs>\n"
    )


def _svg_polyline(points: List[Tuple[int, int]]) -> str:
    return " ".join(f"{x},{y}" for x, y in points)


def _svg_text_lines(
    x: int,
    y: int,
    lines: List[str],
    font_size: int,
    fill: str,
    anchor: str = "middle",
) -> str:
    if not lines:
        return ""
    # Use <tspan> for line breaks; dy is relative to previous line.
    out: List[str] = [f'  <text x="{x}" y="{y}" font-size="{font_size}" fill="{fill}" text-anchor="{anchor}">']
    for i, line in enumerate(lines):
        safe = _xml_escape(line)
        if i == 0:
            out.append(f"    <tspan>{safe}</tspan>")
        else:
            out.append(f'    <tspan x="{x}" dy="{font_size + 4}">{safe}</tspan>')
    out.append("  </text>\n")
    return "\n".join(out)


def _resolve_edge_route_mode(edge: Any, default_mode: str) -> str:
    route = str(getattr(edge, "route", "auto") or "auto").strip().lower()
    if route == "straight":
        return "straight"
    if route == "orthogonal":
        return "orthogonal"
    return default_mode


def _render_internal_png_svg(
    spec: SchematicSpec,
    config: Dict[str, Any],
    out_png: Path,
    out_svg: Path,
) -> None:
    Image, ImageDraw, _ = _require_pillow()

    color_cfg = config["color_scheme"]
    palette_file = color_cfg.get("file")
    if not isinstance(palette_file, str):
        raise ValueError("config.color_scheme.file 缺失")

    from utils import is_safe_relative_path, load_yaml, skill_root

    if not is_safe_relative_path(palette_file):
        raise ValueError(
            "config.color_scheme.file 必须是 skill 内的安全相对路径（不得包含 `..` 或绝对/盘符路径）："
            f"{palette_file!r}"
        )

    palette_db = load_yaml(skill_root() / palette_file)
    presets = palette_db.get("color_schemes")
    if not isinstance(presets, dict):
        raise ValueError("配色库格式错误：缺少 color_schemes")
    scheme_name = color_cfg.get("name")
    if not isinstance(scheme_name, str) or not scheme_name.strip():
        raise ValueError("config.color_scheme.name 缺失")
    if scheme_name not in presets:
        raise ValueError(f"未找到配色方案：{scheme_name}")
    palette = presets[scheme_name]

    width = spec.canvas_width
    height = spec.canvas_height

    bg = hex_to_rgb(config["renderer"].get("background", "#FFFFFF"))
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    font_cfg = config["renderer"]["fonts"]
    node_size = int(config["layout"]["font"]["node_label_size"])
    group_size = int(config["layout"]["font"]["group_label_size"])
    title_size = int(config["layout"]["font"]["title_size"])
    edge_size = int(config["layout"]["font"].get("edge_label_size", group_size))

    node_font = _load_font(pick_font(font_cfg["candidates"], node_size))
    group_font = _load_font(pick_font(font_cfg["candidates"], group_size))
    title_font = _load_font(pick_font(font_cfg["candidates"], title_size))
    edge_font = _load_font(pick_font(font_cfg["candidates"], edge_size))

    text_color = hex_to_rgb(palette.get("text", "#1F1F1F"))
    arrow_color = hex_to_rgb(palette.get("arrow", "#2F5597"))

    # Title (align with layout margins when enabled).
    title_cfg = config.get("layout", {}).get("title", {})
    title_enabled = bool((title_cfg or {}).get("enabled", True))
    title_pad_y = int((title_cfg or {}).get("padding_y", 18))
    margin_x = int(config.get("layout", {}).get("auto", {}).get("margin_x", 60))
    if title_enabled and spec.title.strip():
        draw.text((margin_x, title_pad_y), spec.title, font=title_font, fill=text_color)

    # Groups
    node_lookup: Dict[str, Tuple[int, int, int, int]] = {}
    node_label_lines: Dict[str, List[str]] = {}
    group_label_pos: Dict[str, Tuple[int, int]] = {}

    for g in spec.groups:
        group_fill = hex_to_rgb(palette.get("group_bg", {}).get("fill", "#FAFAFA"))
        group_stroke = hex_to_rgb(palette.get("group_bg", {}).get("stroke", "#CCCCCC"))
        draw.rounded_rectangle(
            [g.x, g.y, g.x + g.w, g.y + g.h],
            radius=22,
            fill=group_fill,
            outline=group_stroke,
            width=2,
        )
        draw.text((g.x + 14, g.y + 10), g.label, font=group_font, fill=text_color)
        group_label_pos[g.id] = (g.x + 14, g.y + 10)

        for n in g.children:
            x0, y0, x1, y1 = n.x, n.y, n.x + n.w, n.y + n.h
            node_lookup[n.id] = (x0, y0, x1, y1)
            node_label_lines[n.id] = _wrap_text(draw, n.label, node_font, max(40, n.w - 20))

    # Edges
    routing = str(config.get("renderer", {}).get("internal_routing", "orthogonal"))
    default_mode = "straight" if routing == "straight" else "orthogonal"
    obstacles: List[Tuple[int, int, int, int]] = []
    for nid, rect in node_lookup.items():
        obstacles.append(rect_expand(rect, pad=10))

    for e in spec.edges:
        src = node_lookup.get(e.source)
        tgt = node_lookup.get(e.target)
        if not src or not tgt:
            continue
        # Exclude endpoints from obstacles.
        obs = [
            rect_expand(v, 10)
            for nid, v in node_lookup.items()
            if nid not in {e.source, e.target}
        ]

        mode = _resolve_edge_route_mode(e, default_mode)
        pts = route_edge_points(
            spec.direction,  # type: ignore[arg-type]
            mode,  # type: ignore[arg-type]
            src,
            tgt,
            obs,
            canvas_w=spec.canvas_width,
            canvas_h=spec.canvas_height,
        )

        stroke_w = 4 if e.style == "thick" else 2
        # Draw segments
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            if e.style == "dashed":
                _draw_dashed_line(draw, p1, p2, arrow_color, stroke_w)
            else:
                draw.line([p1, p2], fill=arrow_color, width=stroke_w)
        if len(pts) >= 2:
            _draw_arrow_head(draw, pts[-2], pts[-1], arrow_color, size=14)

        if e.label:
            lx = (pts[0][0] + pts[-1][0]) // 2
            ly = (pts[0][1] + pts[-1][1]) // 2 - 8
            # Provide a small white background for better print readability.
            bbox = draw.textbbox((lx, ly), e.label, font=edge_font)
            if bbox is not None:
                pad = 2
                draw.rectangle(
                    [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
                    fill=bg,
                    outline=None,
                )
            draw.text((lx, ly), e.label, font=edge_font, fill=text_color)

    # Nodes (draw last to avoid edges covering text)
    for g in spec.groups:
        for n in g.children:
            fill_hex, stroke_hex = _shape_colors(n.kind, palette)
            fill = hex_to_rgb(fill_hex)
            stroke = hex_to_rgb(stroke_hex)
            x0, y0, x1, y1 = n.x, n.y, n.x + n.w, n.y + n.h
            if n.kind == "decision":
                cx = (x0 + x1) // 2
                cy = (y0 + y1) // 2
                draw.polygon([(cx, y0), (x1, cy), (cx, y1), (x0, cy)], fill=fill, outline=stroke)
            else:
                draw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=fill, outline=stroke, width=2)

            lines = node_label_lines.get(n.id, [n.label])
            line_heights: List[int] = []
            for line in lines:
                bb = draw.textbbox((0, 0), line, font=node_font)
                line_heights.append(bb[3] - bb[1])
            total_h = sum(line_heights) + max(0, len(lines) - 1) * 4
            ty = y0 + max(8, (n.h - total_h) // 2)
            for idx, line in enumerate(lines):
                bb = draw.textbbox((0, 0), line, font=node_font)
                tw = bb[2] - bb[0]
                tx = x0 + max(8, (n.w - tw) // 2)
                draw.text((tx, ty), line, font=node_font, fill=text_color)
                ty += line_heights[idx] + 4

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)

    # True vector SVG fallback (no PNG embedding).
    svg_lines: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        _svg_marker_def(arrow_color).rstrip("\n"),
        f'  <rect x="0" y="0" width="{width}" height="{height}" fill="rgb({bg[0]},{bg[1]},{bg[2]})"/>',
    ]
    if title_enabled and spec.title.strip():
        svg_lines.append(
            _svg_text_lines(
                margin_x,
                title_pad_y + title_size,
                [spec.title],
                title_size,
                f"rgb({text_color[0]},{text_color[1]},{text_color[2]})",
                anchor="start",
            ).rstrip("\n")
        )

    # Groups
    for g in spec.groups:
        group_fill = hex_to_rgb(palette.get("group_bg", {}).get("fill", "#FAFAFA"))
        group_stroke = hex_to_rgb(palette.get("group_bg", {}).get("stroke", "#CCCCCC"))
        svg_lines.append(
            f'  <rect x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" rx="22" ry="22" '
            f'fill="rgb({group_fill[0]},{group_fill[1]},{group_fill[2]})" '
            f'stroke="rgb({group_stroke[0]},{group_stroke[1]},{group_stroke[2]})" stroke-width="2"/>'
        )
        # Group label
        gx, gy = group_label_pos.get(g.id, (g.x + 14, g.y + 10))
        svg_lines.append(
            _svg_text_lines(
                gx,
                gy + group_size,
                [g.label],
                group_size,
                f"rgb({text_color[0]},{text_color[1]},{text_color[2]})",
                anchor="start",
            ).rstrip("\n")
        )

    # Edges (behind nodes/text)
    for e in spec.edges:
        src = node_lookup.get(e.source)
        tgt = node_lookup.get(e.target)
        if not src or not tgt:
            continue
        obs = [
            rect_expand(v, 10)
            for nid, v in node_lookup.items()
            if nid not in {e.source, e.target}
        ]

        mode = _resolve_edge_route_mode(e, default_mode)
        pts = route_edge_points(
            spec.direction,  # type: ignore[arg-type]
            mode,  # type: ignore[arg-type]
            src,
            tgt,
            obs,
            canvas_w=spec.canvas_width,
            canvas_h=spec.canvas_height,
        )

        stroke_w = 4 if e.style == "thick" else 2
        dash = ' stroke-dasharray="8 4"' if e.style == "dashed" else ""
        svg_lines.append(
            f'  <polyline points="{_svg_polyline(pts)}" fill="none" '
            f'stroke="rgb({arrow_color[0]},{arrow_color[1]},{arrow_color[2]})" stroke-width="{stroke_w}" '
            f'marker-end="url(#arrow)"{dash}/>'
        )
        if e.label:
            lx = (pts[0][0] + pts[-1][0]) // 2
            ly = (pts[0][1] + pts[-1][1]) // 2 - 6
            svg_lines.append(
                _svg_text_lines(
                    lx,
                    ly,
                    [e.label],
                    edge_size,
                    f"rgb({text_color[0]},{text_color[1]},{text_color[2]})",
                    anchor="middle",
                ).rstrip("\n")
            )

    # Nodes
    for g in spec.groups:
        for n in g.children:
            fill_hex, stroke_hex = _shape_colors(n.kind, palette)
            fill = hex_to_rgb(fill_hex)
            stroke = hex_to_rgb(stroke_hex)
            x0, y0, w0, h0 = n.x, n.y, n.w, n.h
            if n.kind == "decision":
                cx = x0 + w0 // 2
                cy = y0 + h0 // 2
                pts = f"{cx},{y0} {x0 + w0},{cy} {cx},{y0 + h0} {x0},{cy}"
                svg_lines.append(
                    f'  <polygon points="{pts}" fill="rgb({fill[0]},{fill[1]},{fill[2]})" '
                    f'stroke="rgb({stroke[0]},{stroke[1]},{stroke[2]})" stroke-width="2"/>'
                )
            else:
                svg_lines.append(
                    f'  <rect x="{x0}" y="{y0}" width="{w0}" height="{h0}" rx="18" ry="18" '
                    f'fill="rgb({fill[0]},{fill[1]},{fill[2]})" '
                    f'stroke="rgb({stroke[0]},{stroke[1]},{stroke[2]})" stroke-width="2"/>'
                )

            lines = node_label_lines.get(n.id, [n.label])
            # Centered multi-line text.
            line_h = node_size + 4
            total_h = len(lines) * line_h - 4
            ty = y0 + max(8, (h0 - total_h) // 2) + node_size
            svg_lines.append(
                _svg_text_lines(
                    x0 + w0 // 2,
                    ty,
                    lines,
                    node_size,
                    f"rgb({text_color[0]},{text_color[1]},{text_color[2]})",
                    anchor="middle",
                ).rstrip("\n")
            )

    svg_lines.append("</svg>\n")
    write_text(out_svg, "\n".join(svg_lines))


def render_artifacts(
    spec: SchematicSpec,
    config: Dict[str, Any],
    drawio_path: Path,
    output_dir: Path,
) -> Dict[str, Optional[Path]]:
    artifacts = config["output"]["artifacts"]
    png_path = output_dir / artifacts["png"]
    svg_path = output_dir / artifacts["svg"]
    pdf_path = output_dir / artifacts["pdf"]

    render_cfg = config["renderer"]
    border = int(render_cfg.get("drawio_border_px", 20))
    # Prefer spec canvas as the single source of truth for exported resolution.
    width = int(spec.canvas_width)
    height = int(spec.canvas_height)
    bg = hex_to_rgb(render_cfg.get("background", "#FFFFFF"))

    drawio_cmd = ensure_drawio_cli(config)
    if drawio_cmd:
        _export_with_drawio_cli(drawio_cmd, drawio_path, png_path, "png", width, height, border)
        _ensure_png_canvas_size(png_path, width, height, bg)
        _export_with_drawio_cli(drawio_cmd, drawio_path, svg_path, "svg", width, height, border)
        if bool(render_cfg.get("pdf", {}).get("enabled", False)):
            _export_with_drawio_cli(drawio_cmd, drawio_path, pdf_path, "pdf", width, height, border)
            return {"png": png_path, "svg": svg_path, "pdf": pdf_path}
        return {"png": png_path, "svg": svg_path, "pdf": None}

    fallback = bool(render_cfg.get("allow_internal_fallback", True))
    if not fallback:
        raise RuntimeError("未找到 draw.io CLI。请安装 draw.io 或启用内部渲染兜底。")

    global _WARNED_NO_DRAWIO
    if not _WARNED_NO_DRAWIO:
        warn(
            "未找到 draw.io CLI，将使用内部渲染兜底（SVG 为简化矢量，仍建议安装 draw.io CLI 获取最佳交付质量）。"
        )
        _WARNED_NO_DRAWIO = True
    _render_internal_png_svg(spec, config, png_path, svg_path)
    return {"png": png_path, "svg": svg_path, "pdf": None}


def main() -> None:
    import argparse

    from spec_parser import load_schematic_spec
    from utils import fatal, load_yaml

    p = argparse.ArgumentParser(description="Render draw.io schematic to PNG/SVG/PDF.")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--drawio", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()

    try:
        cfg = load_yaml(args.config)
        spec_data = load_yaml(args.spec)
        spec = load_schematic_spec(spec_data, cfg)
        render_artifacts(spec, cfg, args.drawio, args.out_dir)
    except Exception as exc:
        fatal(str(exc))


if __name__ == "__main__":
    main()
