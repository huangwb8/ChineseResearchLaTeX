from __future__ import annotations

import os
import platform
from pathlib import Path
from shutil import which
from subprocess import CompletedProcess, run
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

from drawio_writer import (
    DrawioEdge,
    DrawioNode,
    default_bar_style,
    default_box_style,
    default_edge_style,
    write_drawio,
)
from template_library import resolve_layout_template
from utils import FontChoice, hex_to_rgb, load_yaml, pick_font, warn, write_text
from spec import RoadmapSpec, load_spec


def _drawio_cli_candidates() -> List[str]:
    return [
        "drawio",
        "draw.io",
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        "/Applications/draw.io.app/Contents/MacOS/drawio",
    ]


def detect_drawio_cli() -> Union[str, None]:
    # For testing/debugging: force internal renderer even if draw.io CLI exists.
    if os.environ.get("NSFC_ROADMAP_FORCE_INTERNAL_RENDER", "").strip() in {"1", "true", "TRUE", "yes", "YES"}:
        return None
    for cmd in _drawio_cli_candidates():
        if which(cmd) or Path(cmd).exists():
            return cmd
    return None


_DRAWIO_CLI_CACHE: Union[str, None] = None
_DRAWIO_CLI_CHECKED: bool = False


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
            "draw.io CLI 导出失败\n"
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
            "draw.io CLI 导出失败\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )


def _ensure_png_canvas_size(png_path: Path, target_w: int, target_h: int, bg_rgb: Tuple[int, int, int]) -> None:
    """
    Ensure exported PNG matches expected canvas size.

    draw.io CLI may export with unexpected padding/cropping depending on builds.
    We pad/crop (centered) to keep downstream evaluation stable.
    """
    img = Image.open(png_path)
    try:
        w, h = img.size
        if (w, h) == (target_w, target_h):
            return

        x0 = 0 if w <= target_w else max(0, (w - target_w) // 2)
        y0 = 0 if h <= target_h else max(0, (h - target_h) // 2)
        x1 = min(w, x0 + target_w)
        y1 = min(h, y0 + target_h)
        cropped = img.crop((x0, y0, x1, y1))

        out = Image.new("RGB", (target_w, target_h), bg_rgb)
        cw, ch = cropped.size
        px = max(0, (target_w - cw) // 2)
        py = max(0, (target_h - ch) // 2)
        out.paste(cropped, (px, py))
        out.save(png_path)
    finally:
        try:
            img.close()
        except Exception:
            pass


def ensure_drawio_cli(config: Dict[str, Any]) -> Union[str, None]:
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
                    "draw.io 自动安装失败，将继续使用内部渲染链路。\n"
                    f"stdout: {result.stdout.strip()}\n"
                    f"stderr: {result.stderr.strip()}"
                )
            cmd = detect_drawio_cli()

    _DRAWIO_CLI_CACHE = cmd
    _DRAWIO_CLI_CHECKED = True
    return cmd


def drawio_install_hints() -> List[str]:
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


def _load_font(
    font_choice: FontChoice,
) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    if font_choice.path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(str(font_choice.path), font_choice.size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int
) -> List[str]:
    words = []
    for part in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if part.strip() == "":
            words.append("")
        else:
            words.append(part.strip())

    lines: List[str] = []
    for w in words:
        if w == "":
            lines.append("")
            continue
        # Greedy wrap by characters (works for CJK and mixed text).
        current = ""
        for ch in w:
            candidate = ch if current == "" else (current + ch)
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                    current = ch
                else:
                    # single char too wide: force it
                    lines.append(ch)
                    current = ""
        if current:
            lines.append(current)
    return lines


def _text_compact_len(s: str) -> int:
    # Count characters excluding whitespace/newlines; good enough for CJK/mixed.
    return len("".join(ch for ch in (s or "") if not ch.isspace()))


def _pick_main_box_idx(phase: Any) -> int:
    """
    Heuristic main box selection.

    Goal:
    - Prefer "content-heavy" boxes (more text / higher weight) as mainline,
      instead of a short injected "title-like critical" that would cause huge blanks.
    """
    items: List[tuple[int, int, int, Any]] = []  # (flat_idx, row_idx, row_len, box)
    flat_idx = 0
    for row_idx, row in enumerate(getattr(phase, "rows", []) or []):
        boxes = getattr(row, "boxes", []) or []
        row_len = len(boxes)
        for b in boxes:
            items.append((flat_idx, row_idx, row_len, b))
            flat_idx += 1
    if not items:
        return 0

    # AI-driven explicit semantics: if any box declares role=main, prefer it.
    main_role = [it for it in items if str(getattr(it[3], "role", "") or "").strip() == "main"]
    if main_role:
        # If multiple "main" boxes exist, pick the most content-heavy one deterministically.
        best_idx = main_role[0][0]
        best_score = -10**9
        for flat_i, row_i, row_len, b in main_role:
            text = str(getattr(b, "text", "") or "")
            weight = int(getattr(b, "weight", 1) or 1)
            score = min(200, _text_compact_len(text)) + min(6, weight) * 10 - row_i * 2
            if score > best_score:
                best_score = score
                best_idx = flat_i
        return best_idx

    def is_header_like(row_idx: int, row_len: int, b: Any) -> bool:
        if row_idx != 0 or row_len != 1:
            return False
        t = str(getattr(b, "text", "") or "").strip()
        # "short title" heuristic: avoid selecting it as the mainline box.
        return _text_compact_len(t) <= 16

    kind_bonus = {
        "primary": 30,
        "critical": 28,
        "decision": 20,
        "secondary": 12,
        "auxiliary": 10,
        "risk": 8,
    }

    candidates = [it for it in items if not is_header_like(it[1], it[2], it[3])]
    if not candidates:
        candidates = items

    best_idx = candidates[0][0]
    best_score = -10**9
    for flat_i, row_i, row_len, b in candidates:
        text = str(getattr(b, "text", "") or "")
        kind = str(getattr(b, "kind", "primary") or "primary")
        weight = int(getattr(b, "weight", 1) or 1)
        tlen = _text_compact_len(text)
        score = 0
        score += kind_bonus.get(kind, 0)
        score += min(120, tlen)
        score += min(6, weight) * 10
        if "\n" in text:
            score += 6
        # Slightly prefer earlier rows for readability.
        score -= row_i * 2
        if score > best_score:
            best_score = score
            best_idx = flat_i
    return best_idx


def _draw_vertical_arrow_png(
    draw: ImageDraw.ImageDraw,
    x: int,
    y0: int,
    y1: int,
    color: Tuple[int, int, int],
    width: int,
) -> None:
    if y1 <= y0:
        return
    draw.line([(x, y0), (x, y1)], fill=color, width=max(1, int(width)))
    # Simple triangle arrowhead
    head = max(8, int(width) * 3)
    tip = (x, y1)
    left = (x - head // 2, y1 - head)
    right = (x + head // 2, y1 - head)
    draw.polygon([tip, left, right], fill=color)


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    width: int,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _render_png_classic(
    spec: RoadmapSpec,
    config: Dict[str, Any],
    out_png: Path,
    out_svg: Path,
    out_drawio: Path,
) -> None:
    renderer = config["renderer"]
    layout = config["layout"]
    color_presets = config["color_scheme"]["presets"][config["color_scheme"]["name"]]

    width = int(renderer["canvas"]["width_px"])
    height = int(renderer["canvas"]["height_px"])
    margin = int(renderer["canvas"]["margin_px"])
    spacing = int(layout["spacing_px"])
    phase_bar_w = int(layout["phase_bar"]["width_px"])

    background = hex_to_rgb(renderer["background"])
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)

    main_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["default_size"]))
    title_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["title_size"]))
    if main_choice.path is None or title_choice.path is None:
        warn("未找到可用中文字体候选；输出可能出现中文乱码/方框。")
    font_main = _load_font(main_choice)
    font_title = _load_font(title_choice)

    text_color = hex_to_rgb(color_presets["text"])

    title_cfg = layout.get("title", {}) if isinstance(layout.get("title", {}), dict) else {}
    notes_cfg = layout.get("notes", {}) if isinstance(layout.get("notes", {}), dict) else {}
    title_enabled = bool(title_cfg.get("enabled", True))
    notes_enabled = bool(notes_cfg.get("enabled", True))

    title_h = 0
    title_y = margin
    if title_enabled:
        title_bbox = draw.textbbox((0, 0), spec.title, font=font_title)
        title_h = title_bbox[3] - title_bbox[1]
        draw.text((margin + phase_bar_w + spacing, title_y), spec.title, font=font_title, fill=text_color)

    note = (spec.notes or "").strip()
    note_h = 0
    if notes_enabled and note:
        note_bbox = draw.textbbox((0, 0), note, font=font_main)
        note_h = note_bbox[3] - note_bbox[1]

    content_top = margin + (title_h + spacing if title_enabled else 0)
    content_left = margin
    content_right = width - margin
    content_bottom = height - margin - (note_h + spacing if (notes_enabled and note) else 0)

    phases = spec.phases
    if not phases:
        raise ValueError("spec.phases 不能为空")

    phase_gap = spacing
    available_h = content_bottom - content_top - phase_gap * (len(phases) - 1)
    available_h = max(1, available_h)

    # Allocate phase heights proportional to row counts to avoid overflow.
    phase_weights = [max(1, len(p.rows)) for p in phases]
    total_weight = sum(phase_weights)
    phase_heights: List[int] = []
    used = 0
    for i, w in enumerate(phase_weights):
        if i == len(phase_weights) - 1:
            h = max(1, available_h - used)
        else:
            h = max(1, int(round(available_h * (w / total_weight))))
        phase_heights.append(h)
        used += h
    # Fix rounding drift
    drift = available_h - sum(phase_heights)
    if drift != 0:
        phase_heights[-1] = max(1, phase_heights[-1] + drift)

    box_radius = int(layout["box"]["radius_px"])
    box_padding = int(layout["box"]["padding_px"])
    min_box_h = int(layout["box"]["min_height_px"])
    stroke_w = int(renderer["stroke"]["width_px"])

    phase_bar_fill = hex_to_rgb(layout["phase_bar"]["fill"])
    phase_bar_text = hex_to_rgb(layout["phase_bar"]["text_color"])

    svg_elements: List[str] = []
    svg_elements.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    # Arrow marker for mainline connectors (internal SVG fallback).
    stroke_hex = str((renderer.get("stroke", {}) or {}).get("color", "#2F5597"))
    svg_elements.append(
        f'<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">'
        f'<path d="M0,0 L0,6 L6,3 z" fill="{stroke_hex}"/></marker></defs>'
    )
    svg_elements.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{renderer["background"]}"/>')

    def svg_escape(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    if title_enabled:
        svg_elements.append(
            f'<text x="{margin + phase_bar_w + spacing}" y="{title_y + title_h}" '
            f'font-size="{renderer["fonts"]["title_size"]}" fill="{color_presets["text"]}" '
            f'font-family="sans-serif">{svg_escape(spec.title)}</text>'
        )

    def box_colors(kind: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], str, str]:
        palette = color_presets.get(kind, color_presets["primary"])
        fill_hex = palette["fill"]
        stroke_hex = palette["stroke"]
        return (hex_to_rgb(fill_hex), hex_to_rgb(stroke_hex), fill_hex, stroke_hex)

    # Render phases
    phase_bounds: List[Tuple[int, int]] = []  # (phase_y0, phase_y1) for mainline arrows
    for idx, phase in enumerate(phases):
        phase_y0 = content_top + sum(phase_heights[:idx]) + idx * phase_gap
        phase_h = phase_heights[idx]
        phase_y1 = phase_y0 + phase_h
        phase_bounds.append((phase_y0, phase_y1))

        # Phase bar
        bar_x0 = content_left
        bar_x1 = bar_x0 + phase_bar_w
        _draw_rounded_rect(
            draw,
            (bar_x0, phase_y0, bar_x1, phase_y1),
            radius=box_radius,
            fill=phase_bar_fill,
            outline=phase_bar_fill,
            width=stroke_w,
        )

        # Rotated label (Pillow doesn't support rotate text directly; draw on temp image)
        label_font = font_main
        label_text = phase.label
        lbbox = draw.textbbox((0, 0), label_text, font=label_font)
        lw, lh = lbbox[2] - lbbox[0], lbbox[3] - lbbox[1]
        label_img = Image.new("RGBA", (lw + 4, lh + 4), (0, 0, 0, 0))
        label_draw = ImageDraw.Draw(label_img)
        label_draw.text((2, 2), label_text, font=label_font, fill=phase_bar_text)
        label_rot = label_img.rotate(90, expand=True)
        lx = bar_x0 + (phase_bar_w - label_rot.width) // 2
        ly = phase_y0 + (phase_h - label_rot.height) // 2
        img.paste(label_rot, (lx, ly), label_rot)

        svg_elements.append(
            f'<rect x="{bar_x0}" y="{phase_y0}" width="{phase_bar_w}" height="{phase_h}" rx="{box_radius}" ry="{box_radius}" fill="{layout["phase_bar"]["fill"]}" stroke="{layout["phase_bar"]["fill"]}" stroke-width="{stroke_w}"/>'
        )
        # SVG rotated text
        svg_elements.append(
            f'<text x="{bar_x0 + phase_bar_w/2:.1f}" y="{phase_y0 + phase_h/2:.1f}" font-size="{renderer["fonts"]["default_size"]}" fill="{layout["phase_bar"]["text_color"]}" font-family="sans-serif" text-anchor="middle" dominant-baseline="middle" transform="rotate(90 {bar_x0 + phase_bar_w/2:.1f} {phase_y0 + phase_h/2:.1f})">{svg_escape(label_text)}</text>'
        )

        # Boxes area
        area_x0 = bar_x1 + spacing
        area_x1 = content_right
        area_y0 = phase_y0
        area_y1 = phase_y1

        # Invisible anchor for mainline edges (keeps classic layout compatible with mainline arrows).
        anchor_x = area_x0 + max(0, (area_x1 - area_x0) // 2) - 5
        anchor_y = area_y0 + max(0, (area_y1 - area_y0) // 2) - 5
        drawio_nodes.append(
            DrawioNode(
                id=f"p{idx+1}_main",
                value="",
                x=anchor_x,
                y=anchor_y,
                w=10,
                h=10,
                style="ellipse;html=1;fillColor=none;strokeColor=none;opacity=0;",
            )
        )

        rows = phase.rows
        if not rows:
            continue

        row_gap = spacing
        available_row_h = (area_y1 - area_y0) - row_gap * (len(rows) - 1)
        row_h = max(1, available_row_h // len(rows))

        for r_idx, row in enumerate(rows):
            row_y0 = area_y0 + r_idx * (row_h + row_gap)
            row_y1 = area_y1 if r_idx == len(rows) - 1 else min(area_y1, row_y0 + row_h)
            weights = [b.weight for b in row.boxes]
            total_w = sum(weights)
            box_gap = spacing
            available_w = (area_x1 - area_x0) - box_gap * (len(row.boxes) - 1)
            x = area_x0
            for b_idx, box in enumerate(row.boxes):
                w = int(round(available_w * (weights[b_idx] / total_w)))
                # ensure last box hits the end
                if b_idx == len(row.boxes) - 1:
                    w = area_x1 - x
                bx0, bx1 = x, x + w
                by0, by1 = row_y0, row_y1
                if by1 < by0:
                    by0, by1 = by1, by0
                fill_rgb, stroke_rgb, fill_hex, stroke_hex = box_colors(box.kind)
                _draw_rounded_rect(
                    draw,
                    (bx0, by0, bx1, by1),
                    radius=box_radius,
                    fill=fill_rgb,
                    outline=stroke_rgb,
                    width=stroke_w,
                )
                svg_elements.append(
                    f'<rect x="{bx0}" y="{by0}" width="{bx1-bx0}" height="{by1-by0}" rx="{box_radius}" ry="{box_radius}" fill="{fill_hex}" stroke="{stroke_hex}" stroke-width="{stroke_w}"/>'
                )

                # Text
                max_text_w = (bx1 - bx0) - 2 * box_padding
                max_text_h = (by1 - by0) - 2 * box_padding
                lines = _wrap_text(draw, box.text, font_main, max_text_w)
                # vertical centering
                line_heights = []
                for line in lines:
                    bb = draw.textbbox((0, 0), line, font=font_main)
                    line_heights.append(bb[3] - bb[1])
                total_text_h = sum(line_heights) + max(0, (len(lines) - 1)) * 6
                ty = by0 + box_padding + max(0, (max_text_h - total_text_h) // 2)
                for li, line in enumerate(lines):
                    bb = draw.textbbox((0, 0), line, font=font_main)
                    tw = bb[2] - bb[0]
                    tx = bx0 + box_padding + max(0, (max_text_w - tw) // 2)
                    draw.text((tx, ty), line, font=font_main, fill=text_color)
                    svg_elements.append(
                        f'<text x="{bx0 + (bx1-bx0)/2:.1f}" y="{ty + (line_heights[li])}" font-size="{renderer["fonts"]["default_size"]}" fill="{color_presets["text"]}" font-family="sans-serif" text-anchor="middle">{svg_escape(line)}</text>'
                    )
                    ty += line_heights[li] + 6

                x = bx1 + box_gap

    # Mainline arrows between phases (internal fallback only; draw.io export uses real edges).
    stroke_hex = str((renderer.get("stroke", {}) or {}).get("color", "#2F5597"))
    stroke_rgb = hex_to_rgb(stroke_hex)
    arrow_w = max(2, int((renderer.get("stroke", {}) or {}).get("width_px", 3)))
    # Place arrow in the middle of the content area (excluding the phase bar).
    main_x = int((content_left + phase_bar_w + spacing) + (content_right - (content_left + phase_bar_w + spacing)) // 2)
    for i in range(len(phase_bounds) - 1):
        y0 = phase_bounds[i][1] - max(2, arrow_w)
        y1 = phase_bounds[i + 1][0] + max(2, arrow_w)
        _draw_vertical_arrow_png(draw, main_x, y0, y1, stroke_rgb, arrow_w)
        svg_elements.append(
            f'<line x1="{main_x}" y1="{y0}" x2="{main_x}" y2="{y1}" '
            f'stroke="{stroke_hex}" stroke-width="{arrow_w}" marker-end="url(#arrow)"/>'
        )

    if notes_enabled and note:
        # Notes at bottom (reserved space is already removed from content_bottom).
        ny = height - margin - note_h
        draw.text((margin, ny), note, font=font_main, fill=text_color)
        svg_elements.append(
            f'<text x="{margin}" y="{height - margin}" font-size="{renderer["fonts"]["default_size"]}" '
            f'fill="{color_presets["text"]}" font-family="sans-serif">{svg_escape(note)}</text>'
        )

    svg_elements.append("</svg>")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    if bool((renderer.get("svg", {}) or {}).get("enabled", True)):
        write_text(out_svg, "\n".join(svg_elements) + "\n")

    # Write draw.io (nodes only; arrows/edges are optional and can be edited manually)
    drawio_nodes: List[DrawioNode] = []
    font_size = int(renderer["fonts"]["default_size"])

    if title_enabled:
        drawio_nodes.append(
            DrawioNode(
                id="title",
                value=spec.title,
                x=margin + phase_bar_w + spacing,
                y=title_y,
                w=max(300, min(1200, content_right - (margin + phase_bar_w + spacing))),
                h=title_h + 12,
                style=default_box_style(
                    fill="#FFFFFF",
                    stroke="#FFFFFF",
                    font_size=int(renderer["fonts"]["title_size"]),
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=left;verticalAlign=top;",
            )
        )

    def kind_fill_stroke(kind: str) -> Tuple[str, str]:
        pal = color_presets.get(kind, color_presets["primary"])
        return (pal["fill"], pal["stroke"])

    for idx, phase in enumerate(phases):
        phase_y0 = content_top + sum(phase_heights[:idx]) + idx * phase_gap
        phase_h = phase_heights[idx]
        phase_y1 = phase_y0 + phase_h

        bar_x0 = content_left
        bar_x1 = bar_x0 + phase_bar_w
        drawio_nodes.append(
            DrawioNode(
                id=f"phase_{idx+1}_bar",
                value=phase.label,
                x=bar_x0,
                y=phase_y0,
                w=phase_bar_w,
                h=phase_h,
                style=default_bar_style(
                    fill=layout["phase_bar"]["fill"],
                    font_size=font_size,
                    font_color=str(layout.get("phase_bar", {}).get("text_color", "#FFFFFF")),
                )
                + "align=center;verticalAlign=middle;rotation=90;",
            )
        )

        area_x0 = bar_x1 + spacing
        area_x1 = content_right
        area_y0 = phase_y0
        area_y1 = phase_y1

        rows = phase.rows
        if not rows:
            continue

        row_gap = spacing
        available_row_h = (area_y1 - area_y0) - row_gap * (len(rows) - 1)
        row_h = max(1, available_row_h // len(rows))

        for r_idx, row in enumerate(rows):
            row_y0 = area_y0 + r_idx * (row_h + row_gap)
            row_y1 = area_y1 if r_idx == len(rows) - 1 else min(area_y1, row_y0 + row_h)
            weights = [b.weight for b in row.boxes]
            total_w = sum(weights)
            box_gap = spacing
            available_w = (area_x1 - area_x0) - box_gap * (len(row.boxes) - 1)
            x = area_x0
            for b_idx, box in enumerate(row.boxes):
                w = int(round(available_w * (weights[b_idx] / total_w)))
                if b_idx == len(row.boxes) - 1:
                    w = area_x1 - x
                bx0, bx1 = x, x + w
                by0, by1 = row_y0, row_y1
                fill_hex, stroke_hex = kind_fill_stroke(box.kind)
                drawio_nodes.append(
                    DrawioNode(
                        id=f"p{idx+1}_r{r_idx+1}_b{b_idx+1}",
                        value=box.text,
                        x=bx0,
                        y=by0,
                        w=(bx1 - bx0),
                        h=(by1 - by0),
                        style=default_box_style(
                            fill=fill_hex,
                            stroke=stroke_hex,
                            font_size=font_size,
                            font_color=str(color_presets.get("text", "#1F1F1F")),
                        )
                        + "align=center;verticalAlign=middle;",
                    )
                )
                x = bx1 + box_gap

    if notes_enabled and note:
        drawio_nodes.append(
            DrawioNode(
                id="notes",
                value=note,
                x=margin,
                y=height - margin - note_h - 12,
                w=max(300, content_right - margin),
                h=note_h + 12,
                style=default_box_style(
                    fill="#FFFFFF",
                    stroke="#FFFFFF",
                    font_size=font_size,
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=left;verticalAlign=top;",
            )
        )

    edge_style = default_edge_style(
        stroke=str((renderer.get("stroke", {}) or {}).get("color", "#2F5597")),
        width=max(2, int((renderer.get("stroke", {}) or {}).get("width_px", 3))),
    )
    edges: List[DrawioEdge] = []
    for i in range(1, len(phases)):
        edges.append(
            DrawioEdge(
                id=f"e_main_{i}",
                source=f"p{i}_main",
                target=f"p{i+1}_main",
                style=edge_style,
            )
        )
    write_drawio(out_drawio, nodes=drawio_nodes, edges=edges)


def _render_png_three_column(
    spec: RoadmapSpec,
    config: Dict[str, Any],
    out_png: Path,
    out_svg: Path,
    out_drawio: Path,
) -> None:
    renderer = config["renderer"]
    layout = config["layout"]
    color_presets = config["color_scheme"]["presets"][config["color_scheme"]["name"]]

    width = int(renderer["canvas"]["width_px"])
    height = int(renderer["canvas"]["height_px"])
    margin = int(renderer["canvas"]["margin_px"])
    spacing = int(layout["spacing_px"])

    background = hex_to_rgb(renderer["background"])
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)

    main_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["default_size"]))
    title_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["title_size"]))
    if main_choice.path is None or title_choice.path is None:
        warn("未找到可用中文字体候选；输出可能出现中文乱码/方框。")
    font_main = _load_font(main_choice)
    font_title = _load_font(title_choice)

    text_color = hex_to_rgb(color_presets["text"])

    title_cfg = layout.get("title", {}) if isinstance(layout.get("title", {}), dict) else {}
    notes_cfg = layout.get("notes", {}) if isinstance(layout.get("notes", {}), dict) else {}
    title_enabled = bool(title_cfg.get("enabled", True))
    notes_enabled = bool(notes_cfg.get("enabled", True))

    title_h = 0
    title_y = margin
    if title_enabled:
        title_bbox = draw.textbbox((0, 0), spec.title, font=font_title)
        title_h = title_bbox[3] - title_bbox[1]
        draw.text((margin, title_y), spec.title, font=font_title, fill=text_color)

    note = (spec.notes or "").strip()
    note_h = 0
    if notes_enabled and note:
        note_bbox = draw.textbbox((0, 0), note, font=font_main)
        note_h = note_bbox[3] - note_bbox[1]

    content_top = margin + (title_h + spacing if title_enabled else 0)
    content_left = margin
    content_right = width - margin
    content_bottom = height - margin - (note_h + spacing if (notes_enabled and note) else 0)

    phases = spec.phases
    if not phases:
        raise ValueError("spec.phases 不能为空")

    # Phase bands (keep similar allocation logic to classic).
    phase_gap = spacing
    available_h = content_bottom - content_top - phase_gap * (len(phases) - 1)
    available_h = max(1, available_h)
    phase_weights = [max(1, sum(len(r.boxes) for r in p.rows) or len(p.rows) or 1) for p in phases]
    total_weight = sum(phase_weights)
    phase_heights: List[int] = []
    used = 0
    for i, w in enumerate(phase_weights):
        if i == len(phase_weights) - 1:
            h = max(1, available_h - used)
        else:
            h = max(1, int(round(available_h * (w / total_weight))))
        phase_heights.append(h)
        used += h
    drift = available_h - sum(phase_heights)
    if drift != 0:
        phase_heights[-1] = max(1, phase_heights[-1] + drift)

    box_radius = int(layout["box"]["radius_px"])
    box_padding = int(layout["box"]["padding_px"])
    min_box_h = int(layout["box"]["min_height_px"])
    stroke_w = int(renderer["stroke"]["width_px"])

    header_fill = hex_to_rgb(layout["phase_bar"]["fill"])
    header_text = hex_to_rgb(layout["phase_bar"]["text_color"])

    svg_elements: List[str] = []
    svg_elements.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    # Arrow marker for mainline connectors (internal SVG fallback).
    stroke_hex = str((renderer.get("stroke", {}) or {}).get("color", "#2F5597"))
    svg_elements.append(
        f'<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">'
        f'<path d="M0,0 L0,6 L6,3 z" fill="{stroke_hex}"/></marker></defs>'
    )
    svg_elements.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{renderer["background"]}"/>')

    def svg_escape(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    if title_enabled:
        svg_elements.append(
            f'<text x="{margin}" y="{title_y + title_h}" font-size="{renderer["fonts"]["title_size"]}" '
            f'fill="{color_presets["text"]}" font-family="sans-serif">{svg_escape(spec.title)}</text>'
        )

    def kind_fill_stroke(kind: str) -> Tuple[str, str]:
        pal = color_presets.get(kind, color_presets["primary"])
        return (pal["fill"], pal["stroke"])

    def box_colors(kind: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], str, str]:
        palette = color_presets.get(kind, color_presets["primary"])
        fill_hex = palette["fill"]
        stroke_hex = palette["stroke"]
        return (hex_to_rgb(fill_hex), hex_to_rgb(stroke_hex), fill_hex, stroke_hex)

    content_w = content_right - content_left
    col_gap = spacing
    col_w = max(1, int((content_w - 2 * col_gap) // 3))
    col_x = [
        content_left,
        content_left + col_w + col_gap,
        content_left + 2 * (col_w + col_gap),
    ]

    # Render phases
    phase_bounds: List[Tuple[int, int]] = []  # (phase_y0, phase_y1) for mainline arrows
    for idx, phase in enumerate(phases):
        phase_y0 = content_top + sum(phase_heights[:idx]) + idx * phase_gap
        phase_h = phase_heights[idx]
        phase_y1 = phase_y0 + phase_h
        phase_bounds.append((phase_y0, phase_y1))

        # Section header bar
        header_h = min(max(int(renderer["fonts"]["default_size"]) + box_padding, 44), max(32, phase_h // 4))
        _draw_rounded_rect(
            draw,
            (content_left, phase_y0, content_right, phase_y0 + header_h),
            radius=box_radius,
            fill=header_fill,
            outline=header_fill,
            width=stroke_w,
        )
        header_value = phase.label
        if getattr(phase, "phase_header_override", None):
            header_value = f"{phase.label}：{str(getattr(phase, 'phase_header_override') or '').strip()}"
        draw.text(
            (content_left + box_padding, phase_y0 + (header_h - int(renderer["fonts"]["default_size"])) // 2),
            header_value,
            font=font_main,
            fill=header_text,
        )

        svg_elements.append(
            f'<rect x="{content_left}" y="{phase_y0}" width="{content_right - content_left}" height="{header_h}" '
            f'rx="{box_radius}" ry="{box_radius}" fill="{layout["phase_bar"]["fill"]}" stroke="{layout["phase_bar"]["fill"]}" stroke-width="{stroke_w}"/>'
        )
        svg_elements.append(
            f'<text x="{content_left + box_padding}" y="{phase_y0 + header_h - box_padding}" '
            f'font-size="{renderer["fonts"]["default_size"]}" fill="{layout["phase_bar"]["text_color"]}" '
            f'font-family="sans-serif">{svg_escape(header_value)}</text>'
        )

        # Boxes area
        area_y0 = phase_y0 + header_h + spacing
        area_y1 = phase_y1
        area_h = max(1, area_y1 - area_y0)

        flat_boxes = [b for r in phase.rows for b in r.boxes]
        if not flat_boxes:
            continue

        # Pick a "mainline" box for center column.
        main_idx = min(max(_pick_main_box_idx(phase), 0), len(flat_boxes) - 1)
        main_box = flat_boxes[main_idx]
        side_boxes = [b for i, b in enumerate(flat_boxes) if i != main_idx]

        left_boxes: List[Any] = []
        right_boxes: List[Any] = []
        for b in side_boxes:
            if b.kind in ("secondary", "auxiliary"):
                left_boxes.append(b)
            else:
                right_boxes.append(b)

        # Center box (do NOT stretch to full phase height; keep to content height to avoid huge blanks).
        cx0, cx1 = col_x[1], col_x[1] + col_w
        fill_rgb, stroke_rgb, fill_hex, stroke_hex = box_colors(main_box.kind)
        wrapped = _wrap_text(draw, main_box.text, font_main, (cx1 - cx0) - 2 * box_padding)
        lb = draw.textbbox((0, 0), "测", font=font_main)
        line_h = lb[3] - lb[1]
        text_h = len(wrapped) * line_h + max(0, (len(wrapped) - 1) * 2)
        main_h = max(min_box_h, min(area_h, text_h + 2 * box_padding + 4))
        _draw_rounded_rect(
            draw,
            (cx0, area_y0, cx1, area_y0 + main_h),
            radius=box_radius,
            fill=fill_rgb,
            outline=stroke_rgb,
            width=stroke_w,
        )
        # Vertically center within the main box itself
        ty = area_y0 + max(0, (main_h - text_h) // 2)
        for ln in wrapped:
            draw.text((cx0 + box_padding, ty), ln, font=font_main, fill=text_color)
            ty += line_h + 2

        svg_elements.append(
            f'<rect x="{cx0}" y="{area_y0}" width="{cx1 - cx0}" height="{main_h}" '
            f'rx="{box_radius}" ry="{box_radius}" fill="{fill_hex}" stroke="{stroke_hex}" stroke-width="{stroke_w}"/>'
        )
        # (SVG text wrapping is intentionally simplified: keep as a single <text> with <tspan> lines)
        if wrapped:
            base_y = area_y0 + max(
                int(renderer["fonts"]["default_size"]),
                max(0, (main_h - text_h) // 2) + int(renderer["fonts"]["default_size"]),
            )
            svg_elements.append(
                f'<text x="{cx0 + box_padding}" y="{base_y}" font-size="{renderer["fonts"]["default_size"]}" '
                f'fill="{color_presets["text"]}" font-family="sans-serif">'
            )
            y = base_y
            for i, ln in enumerate(wrapped):
                if i == 0:
                    svg_elements.append(f'{svg_escape(ln)}')
                else:
                    y += int(renderer["fonts"]["default_size"]) + 2
                    svg_elements.append(f'<tspan x="{cx0 + box_padding}" y="{y}">{svg_escape(ln)}</tspan>')
            svg_elements.append("</text>")

        def render_side(col: int, boxes: List[Any]) -> None:
            if not boxes:
                return
            x0 = col_x[col]
            x1 = x0 + col_w
            n = len(boxes)
            gap = spacing
            h_each = max(1, int((area_h - gap * (n - 1)) // n))
            y = area_y0
            for b in boxes:
                bh = max(1, min(area_y1 - y, max(min_box_h, h_each)))
                if y + bh > area_y1:
                    bh = max(1, area_y1 - y)
                frgb, srgb, fhex, shex = box_colors(b.kind)
                _draw_rounded_rect(
                    draw,
                    (x0, y, x1, y + bh),
                    radius=box_radius,
                    fill=frgb,
                    outline=srgb,
                    width=stroke_w,
                )
                wrapped2 = _wrap_text(draw, b.text, font_main, (x1 - x0) - 2 * box_padding)
                ty2 = y + box_padding
                for ln in wrapped2:
                    if ty2 + int(renderer["fonts"]["default_size"]) > y + bh - box_padding:
                        break
                    draw.text((x0 + box_padding, ty2), ln, font=font_main, fill=text_color)
                    ty2 += int(renderer["fonts"]["default_size"]) + 2

                svg_elements.append(
                    f'<rect x="{x0}" y="{y}" width="{x1 - x0}" height="{bh}" rx="{box_radius}" ry="{box_radius}" '
                    f'fill="{fhex}" stroke="{shex}" stroke-width="{stroke_w}"/>'
                )
                y = y + bh + gap
                if y >= area_y1:
                    break

        render_side(0, left_boxes)
        render_side(2, right_boxes)

    # Mainline arrows between phases (internal fallback only; draw.io export uses real edges).
    stroke_hex = str((renderer.get("stroke", {}) or {}).get("color", "#2F5597"))
    stroke_rgb = hex_to_rgb(stroke_hex)
    arrow_w = max(2, int((renderer.get("stroke", {}) or {}).get("width_px", 3)))
    main_x = int(col_x[1] + col_w // 2)
    for i in range(len(phase_bounds) - 1):
        y0 = phase_bounds[i][1] - max(2, arrow_w)
        y1 = phase_bounds[i + 1][0] + max(2, arrow_w)
        _draw_vertical_arrow_png(draw, main_x, y0, y1, stroke_rgb, arrow_w)
        svg_elements.append(
            f'<line x1="{main_x}" y1="{y0}" x2="{main_x}" y2="{y1}" '
            f'stroke="{stroke_hex}" stroke-width="{arrow_w}" marker-end="url(#arrow)"/>'
        )

    if notes_enabled and note:
        ny = height - margin - note_h
        draw.text((margin, ny), note, font=font_main, fill=text_color)
        svg_elements.append(
            f'<text x="{margin}" y="{height - margin}" font-size="{renderer["fonts"]["default_size"]}" '
            f'fill="{color_presets["text"]}" font-family="sans-serif">{svg_escape(note)}</text>'
        )

    svg_elements.append("</svg>")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    if bool((renderer.get("svg", {}) or {}).get("enabled", True)):
        write_text(out_svg, "\n".join(svg_elements) + "\n")

    # draw.io nodes
    drawio_nodes: List[DrawioNode] = []
    font_size = int(renderer["fonts"]["default_size"])

    if title_enabled:
        drawio_nodes.append(
            DrawioNode(
                id="title",
                value=spec.title,
                x=margin,
                y=title_y,
                w=max(300, min(1400, content_right - margin)),
                h=title_h + 12,
                style=default_box_style(
                    fill="#FFFFFF",
                    stroke="#FFFFFF",
                    font_size=int(renderer["fonts"]["title_size"]),
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=left;verticalAlign=top;",
            )
        )

    # Build nodes by re-running layout in a deterministic way (keep it simple).
    # Recompute per-phase band geometry (mirrors above) to avoid sharing mutable state.
    for idx, phase in enumerate(phases):
        phase_y0 = content_top + sum(phase_heights[:idx]) + idx * phase_gap
        phase_h = phase_heights[idx]
        phase_y1 = phase_y0 + phase_h
        header_h = min(max(int(renderer["fonts"]["default_size"]) + box_padding, 44), max(32, phase_h // 4))
        header_value = phase.label
        if getattr(phase, "phase_header_override", None):
            header_value = f"{phase.label}：{str(getattr(phase, 'phase_header_override') or '').strip()}"
        drawio_nodes.append(
            DrawioNode(
                id=f"phase_{idx+1}_header",
                value=header_value,
                x=content_left,
                y=phase_y0,
                w=(content_right - content_left),
                h=header_h,
                style=default_bar_style(
                    fill=layout["phase_bar"]["fill"],
                    font_size=font_size,
                    font_color=str(layout.get("phase_bar", {}).get("text_color", "#FFFFFF")),
                )
                + "align=left;verticalAlign=middle;",
            )
        )
        area_y0 = phase_y0 + header_h + spacing
        area_y1 = phase_y1
        flat_boxes = [b for r in phase.rows for b in r.boxes]
        if not flat_boxes:
            # Keep mainline edges stable even for empty phases.
            cx0, cx1 = col_x[1], col_x[1] + col_w
            drawio_nodes.append(
                DrawioNode(
                    id=f"p{idx+1}_main",
                    value="",
                    x=cx0 + (cx1 - cx0) // 2 - 5,
                    y=area_y0 + max(0, (area_y1 - area_y0) // 2) - 5,
                    w=10,
                    h=10,
                    style="ellipse;html=1;fillColor=none;strokeColor=none;opacity=0;",
                )
            )
            continue
        main_idx = min(max(_pick_main_box_idx(phase), 0), len(flat_boxes) - 1)
        main_box = flat_boxes[main_idx]
        side_boxes = [b for i, b in enumerate(flat_boxes) if i != main_idx]
        left_boxes = [b for b in side_boxes if b.kind in ("secondary", "auxiliary")]
        right_boxes = [b for b in side_boxes if b.kind not in ("secondary", "auxiliary")]

        cx0, cx1 = col_x[1], col_x[1] + col_w
        fill_hex, stroke_hex = kind_fill_stroke(main_box.kind)
        wrapped = _wrap_text(draw, main_box.text, font_main, (cx1 - cx0) - 2 * box_padding)
        lb = draw.textbbox((0, 0), "测", font=font_main)
        line_h = lb[3] - lb[1]
        text_h = len(wrapped) * line_h + max(0, (len(wrapped) - 1) * 2)
        area_h = max(1, area_y1 - area_y0)
        main_h = max(min_box_h, min(area_h, text_h + 2 * box_padding + 4))
        drawio_nodes.append(
            DrawioNode(
                id=f"p{idx+1}_main",
                value=main_box.text,
                x=cx0,
                y=area_y0,
                w=(cx1 - cx0),
                h=main_h,
                style=default_box_style(
                    fill=fill_hex,
                    stroke=stroke_hex,
                    font_size=font_size,
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=center;verticalAlign=middle;",
            )
        )

        def add_side(col: int, boxes: List[Any], prefix: str) -> None:
            if not boxes:
                return
            x0 = col_x[col]
            x1 = x0 + col_w
            n = len(boxes)
            gap = spacing
            area_h = max(1, area_y1 - area_y0)
            h_each = max(1, int((area_h - gap * (n - 1)) // n))
            y = area_y0
            for i, b in enumerate(boxes, start=1):
                bh = max(1, min(area_y1 - y, max(min_box_h, h_each)))
                if y + bh > area_y1:
                    bh = max(1, area_y1 - y)
                fhex, shex = kind_fill_stroke(b.kind)
                drawio_nodes.append(
                    DrawioNode(
                        id=f"p{idx+1}_{prefix}{i}",
                        value=b.text,
                        x=x0,
                        y=y,
                        w=(x1 - x0),
                        h=bh,
                        style=default_box_style(
                            fill=fhex,
                            stroke=shex,
                            font_size=font_size,
                            font_color=str(color_presets.get("text", "#1F1F1F")),
                        )
                        + "align=center;verticalAlign=middle;",
                    )
                )
                y = y + bh + gap
                if y >= area_y1:
                    break

        add_side(0, left_boxes, "l")
        add_side(2, right_boxes, "r")

    if notes_enabled and note:
        drawio_nodes.append(
            DrawioNode(
                id="notes",
                value=note,
                x=margin,
                y=height - margin - note_h - 12,
                w=max(300, content_right - margin),
                h=note_h + 12,
                style=default_box_style(
                    fill="#FFFFFF",
                    stroke="#FFFFFF",
                    font_size=font_size,
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=left;verticalAlign=top;",
            )
        )

    edge_style = default_edge_style(
        stroke=str((renderer.get("stroke", {}) or {}).get("color", "#2F5597")),
        width=max(2, int((renderer.get("stroke", {}) or {}).get("width_px", 3))),
    )
    edges: List[DrawioEdge] = []
    for i in range(1, len(phases)):
        edges.append(
            DrawioEdge(
                id=f"e_main_{i}",
                source=f"p{i}_main",
                target=f"p{i+1}_main",
                style=edge_style,
            )
        )
    write_drawio(out_drawio, nodes=drawio_nodes, edges=edges)


def _render_png_layered_pipeline(
    spec: RoadmapSpec,
    config: Dict[str, Any],
    out_png: Path,
    out_svg: Path,
    out_drawio: Path,
) -> None:
    # Implementation note: layered-pipeline shares most geometry with three-column,
    # but uses a wider center column to emphasize the mainline.
    renderer = config["renderer"]
    layout = config["layout"]
    color_presets = config["color_scheme"]["presets"][config["color_scheme"]["name"]]

    width = int(renderer["canvas"]["width_px"])
    height = int(renderer["canvas"]["height_px"])
    margin = int(renderer["canvas"]["margin_px"])
    spacing = int(layout["spacing_px"])

    background = hex_to_rgb(renderer["background"])
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)

    main_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["default_size"]))
    title_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["title_size"]))
    if main_choice.path is None or title_choice.path is None:
        warn("未找到可用中文字体候选；输出可能出现中文乱码/方框。")
    font_main = _load_font(main_choice)
    font_title = _load_font(title_choice)

    text_color = hex_to_rgb(color_presets["text"])

    title_cfg = layout.get("title", {}) if isinstance(layout.get("title", {}), dict) else {}
    notes_cfg = layout.get("notes", {}) if isinstance(layout.get("notes", {}), dict) else {}
    title_enabled = bool(title_cfg.get("enabled", True))
    notes_enabled = bool(notes_cfg.get("enabled", True))

    title_h = 0
    title_y = margin
    if title_enabled:
        title_bbox = draw.textbbox((0, 0), spec.title, font=font_title)
        title_h = title_bbox[3] - title_bbox[1]
        draw.text((margin, title_y), spec.title, font=font_title, fill=text_color)

    note = (spec.notes or "").strip()
    note_h = 0
    if notes_enabled and note:
        note_bbox = draw.textbbox((0, 0), note, font=font_main)
        note_h = note_bbox[3] - note_bbox[1]

    content_top = margin + (title_h + spacing if title_enabled else 0)
    content_left = margin
    content_right = width - margin
    content_bottom = height - margin - (note_h + spacing if (notes_enabled and note) else 0)

    phases = spec.phases
    if not phases:
        raise ValueError("spec.phases 不能为空")

    phase_gap = spacing
    available_h = content_bottom - content_top - phase_gap * (len(phases) - 1)
    available_h = max(1, available_h)
    phase_weights = [max(1, sum(len(r.boxes) for r in p.rows) or len(p.rows) or 1) for p in phases]
    total_weight = sum(phase_weights)
    phase_heights: List[int] = []
    used = 0
    for i, w in enumerate(phase_weights):
        if i == len(phases) - 1:
            h = max(1, available_h - used)
        else:
            h = max(1, int(round(available_h * (w / total_weight))))
        phase_heights.append(h)
        used += h
    drift = available_h - sum(phase_heights)
    if drift != 0:
        phase_heights[-1] = max(1, phase_heights[-1] + drift)

    box_radius = int(layout["box"]["radius_px"])
    box_padding = int(layout["box"]["padding_px"])
    min_box_h = int(layout["box"]["min_height_px"])
    stroke_w = int(renderer["stroke"]["width_px"])

    svg_elements: List[str] = []
    svg_elements.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    svg_elements.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{renderer["background"]}"/>')

    def svg_escape(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    if title_enabled:
        svg_elements.append(
            f'<text x="{margin}" y="{title_y + title_h}" font-size="{renderer["fonts"]["title_size"]}" '
            f'fill="{color_presets["text"]}" font-family="sans-serif">{svg_escape(spec.title)}</text>'
        )

    def kind_fill_stroke(kind: str) -> Tuple[str, str]:
        pal = color_presets.get(kind, color_presets["primary"])
        return (pal["fill"], pal["stroke"])

    def box_colors(kind: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], str, str]:
        palette = color_presets.get(kind, color_presets["primary"])
        fill_hex = palette["fill"]
        stroke_hex = palette["stroke"]
        return (hex_to_rgb(fill_hex), hex_to_rgb(stroke_hex), fill_hex, stroke_hex)

    # Column widths: emphasize center mainline.
    content_w = content_right - content_left
    col_gap = spacing
    center_w = int(content_w * 0.46)
    side_w = max(1, int((content_w - center_w - 2 * col_gap) // 2))
    center_w = max(1, content_w - 2 * side_w - 2 * col_gap)
    left_x0 = content_left
    center_x0 = left_x0 + side_w + col_gap
    right_x0 = center_x0 + center_w + col_gap

    # Arrow marker for mainline connectors (internal SVG fallback).
    stroke_hex = str((renderer.get("stroke", {}) or {}).get("color", "#2F5597"))
    svg_elements.append(
        f'<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">'
        f'<path d="M0,0 L0,6 L6,3 z" fill="{stroke_hex}"/></marker></defs>'
    )

    phase_bounds: List[Tuple[int, int]] = []
    for idx, phase in enumerate(phases):
        phase_y0 = content_top + sum(phase_heights[:idx]) + idx * phase_gap
        phase_h = phase_heights[idx]
        phase_y1 = phase_y0 + phase_h
        phase_bounds.append((phase_y0, phase_y1))

        # Phase container + title bar (improves "成品感" and makes stages explicit).
        header_value = phase.label
        if getattr(phase, "phase_header_override", None):
            header_value = f"{phase.label}：{str(getattr(phase, 'phase_header_override') or '').strip()}"

        header_h = min(max(int(renderer["fonts"]["default_size"]) + box_padding, 44), max(36, phase_h // 5))
        container_x0 = content_left
        container_x1 = content_right
        _draw_rounded_rect(
            draw,
            (container_x0, phase_y0, container_x1, phase_y1),
            radius=box_radius,
            fill=background,
            outline=hex_to_rgb(str(layout.get("phase_bar", {}).get("fill", "#2F75B5"))),
            width=max(2, stroke_w),
        )
        _draw_rounded_rect(
            draw,
            (container_x0, phase_y0, container_x1, phase_y0 + header_h),
            radius=box_radius,
            fill=hex_to_rgb(str(layout.get("phase_bar", {}).get("fill", "#2F75B5"))),
            outline=hex_to_rgb(str(layout.get("phase_bar", {}).get("fill", "#2F75B5"))),
            width=max(2, stroke_w),
        )
        draw.text(
            (container_x0 + box_padding, phase_y0 + (header_h - int(renderer["fonts"]["default_size"])) // 2),
            header_value,
            font=font_main,
            fill=hex_to_rgb(str(layout.get("phase_bar", {}).get("text_color", "#FFFFFF"))),
        )

        svg_elements.append(
            f'<rect x="{container_x0}" y="{phase_y0}" width="{container_x1 - container_x0}" height="{phase_y1 - phase_y0}" '
            f'rx="{box_radius}" ry="{box_radius}" fill="{renderer["background"]}" '
            f'stroke="{layout.get("phase_bar", {}).get("fill", "#2F75B5")}" stroke-width="{max(2, stroke_w)}"/>'
        )
        svg_elements.append(
            f'<rect x="{container_x0}" y="{phase_y0}" width="{container_x1 - container_x0}" height="{header_h}" '
            f'rx="{box_radius}" ry="{box_radius}" fill="{layout.get("phase_bar", {}).get("fill", "#2F75B5")}" '
            f'stroke="{layout.get("phase_bar", {}).get("fill", "#2F75B5")}" stroke-width="{max(2, stroke_w)}"/>'
        )
        svg_elements.append(
            f'<text x="{container_x0 + box_padding}" y="{phase_y0 + header_h - box_padding}" '
            f'font-size="{renderer["fonts"]["default_size"]}" fill="{layout.get("phase_bar", {}).get("text_color", "#FFFFFF")}" '
            f'font-family="sans-serif">{svg_escape(header_value)}</text>'
        )

        area_y0 = phase_y0 + header_h + spacing
        area_y1 = phase_y1
        area_h = max(1, area_y1 - area_y0)

        flat_boxes = [b for r in phase.rows for b in r.boxes]
        if not flat_boxes:
            continue
        main_idx = min(max(_pick_main_box_idx(phase), 0), len(flat_boxes) - 1)
        main_box = flat_boxes[main_idx]
        side_boxes = [b for i, b in enumerate(flat_boxes) if i != main_idx]
        left_boxes = [b for b in side_boxes if b.kind in ("secondary", "auxiliary")]
        right_boxes = [b for b in side_boxes if b.kind not in ("secondary", "auxiliary")]

        # Center mainline box (do NOT stretch to full phase height; keep to content height).
        cx0, cx1 = center_x0, center_x0 + center_w
        frgb, srgb, fhex, shex = box_colors(main_box.kind)
        wrapped = _wrap_text(draw, main_box.text, font_main, (cx1 - cx0) - 2 * box_padding)
        lb = draw.textbbox((0, 0), "测", font=font_main)
        line_h = lb[3] - lb[1]
        text_h = len(wrapped) * line_h + max(0, (len(wrapped) - 1) * 2)
        main_h = max(min_box_h, min(area_h, text_h + 2 * box_padding + 4))
        _draw_rounded_rect(
            draw,
            (cx0, area_y0, cx1, area_y0 + main_h),
            radius=box_radius,
            fill=frgb,
            outline=srgb,
            width=stroke_w,
        )
        ty = area_y0 + max(0, (main_h - text_h) // 2)
        for ln in wrapped:
            if ty + int(renderer["fonts"]["default_size"]) > (area_y0 + main_h) - box_padding:
                break
            draw.text((cx0 + box_padding, ty), ln, font=font_main, fill=text_color)
            ty += int(renderer["fonts"]["default_size"]) + 2

        svg_elements.append(
            f'<rect x="{cx0}" y="{area_y0}" width="{cx1 - cx0}" height="{main_h}" '
            f'rx="{box_radius}" ry="{box_radius}" fill="{fhex}" stroke="{shex}" stroke-width="{stroke_w}"/>'
        )

        def render_side(x0: int, w: int, boxes: List[Any]) -> None:
            if not boxes:
                return
            x1 = x0 + w
            n = len(boxes)
            gap = spacing
            h_each = max(1, int((area_h - gap * (n - 1)) // n))
            y = area_y0
            for b in boxes:
                bh = max(1, min(area_y1 - y, max(min_box_h, h_each)))
                if y + bh > area_y1:
                    bh = max(1, area_y1 - y)
                frgb2, srgb2, fhex2, shex2 = box_colors(b.kind)
                _draw_rounded_rect(
                    draw,
                    (x0, y, x1, y + bh),
                    radius=box_radius,
                    fill=frgb2,
                    outline=srgb2,
                    width=stroke_w,
                )
                wrapped2 = _wrap_text(draw, b.text, font_main, (x1 - x0) - 2 * box_padding)
                ty2 = y + box_padding
                for ln in wrapped2:
                    if ty2 + int(renderer["fonts"]["default_size"]) > y + bh - box_padding:
                        break
                    draw.text((x0 + box_padding, ty2), ln, font=font_main, fill=text_color)
                    ty2 += int(renderer["fonts"]["default_size"]) + 2

                svg_elements.append(
                    f'<rect x="{x0}" y="{y}" width="{x1 - x0}" height="{bh}" rx="{box_radius}" ry="{box_radius}" '
                    f'fill="{fhex2}" stroke="{shex2}" stroke-width="{stroke_w}"/>'
                )
                y = y + bh + gap
                if y >= area_y1:
                    break

        render_side(left_x0, side_w, left_boxes)
        render_side(right_x0, side_w, right_boxes)

    # Mainline arrows between phases (internal fallback only; draw.io export uses real edges).
    stroke_hex = str((renderer.get("stroke", {}) or {}).get("color", "#2F5597"))
    stroke_rgb = hex_to_rgb(stroke_hex)
    arrow_w = max(2, int((renderer.get("stroke", {}) or {}).get("width_px", 3)))
    main_x = int(center_x0 + center_w // 2)
    for i in range(len(phase_bounds) - 1):
        y0 = phase_bounds[i][1] - max(2, arrow_w)
        y1 = phase_bounds[i + 1][0] + max(2, arrow_w)
        _draw_vertical_arrow_png(draw, main_x, y0, y1, stroke_rgb, arrow_w)
        svg_elements.append(
            f'<line x1="{main_x}" y1="{y0}" x2="{main_x}" y2="{y1}" '
            f'stroke="{stroke_hex}" stroke-width="{arrow_w}" marker-end="url(#arrow)"/>'
        )

    if notes_enabled and note:
        ny = height - margin - note_h
        draw.text((margin, ny), note, font=font_main, fill=text_color)
        svg_elements.append(
            f'<text x="{margin}" y="{height - margin}" font-size="{renderer["fonts"]["default_size"]}" '
            f'fill="{color_presets["text"]}" font-family="sans-serif">{svg_escape(note)}</text>'
        )

    svg_elements.append("</svg>")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    if bool((renderer.get("svg", {}) or {}).get("enabled", True)):
        write_text(out_svg, "\n".join(svg_elements) + "\n")

    drawio_nodes: List[DrawioNode] = []
    font_size = int(renderer["fonts"]["default_size"])

    if title_enabled:
        drawio_nodes.append(
            DrawioNode(
                id="title",
                value=spec.title,
                x=margin,
                y=title_y,
                w=max(300, min(1400, content_right - margin)),
                h=title_h + 12,
                style=default_box_style(
                    fill="#FFFFFF",
                    stroke="#FFFFFF",
                    font_size=int(renderer["fonts"]["title_size"]),
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=left;verticalAlign=top;",
            )
        )

    for idx, phase in enumerate(phases):
        phase_y0 = content_top + sum(phase_heights[:idx]) + idx * phase_gap
        phase_h = phase_heights[idx]
        phase_y1 = phase_y0 + phase_h

        header_value = phase.label
        if getattr(phase, "phase_header_override", None):
            header_value = f"{phase.label}：{str(getattr(phase, 'phase_header_override') or '').strip()}"

        header_h = min(max(int(renderer["fonts"]["default_size"]) + box_padding, 44), max(36, phase_h // 5))
        # Container (behind everything in draw.io)
        drawio_nodes.append(
            DrawioNode(
                id=f"phase_{idx+1}_container",
                value="",
                x=content_left,
                y=phase_y0,
                w=(content_right - content_left),
                h=(phase_y1 - phase_y0),
                style=default_box_style(
                    fill=renderer.get("background", "#FFFFFF"),
                    stroke=str(layout.get("phase_bar", {}).get("fill", "#2F75B5")),
                    font_size=font_size,
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=left;verticalAlign=top;",
            )
        )
        drawio_nodes.append(
            DrawioNode(
                id=f"phase_{idx+1}_header",
                value=header_value,
                x=content_left,
                y=phase_y0,
                w=(content_right - content_left),
                h=header_h,
                style=default_bar_style(
                    fill=str(layout.get("phase_bar", {}).get("fill", "#2F75B5")),
                    font_size=font_size,
                    font_color=str(layout.get("phase_bar", {}).get("text_color", "#FFFFFF")),
                )
                + "align=left;verticalAlign=middle;",
            )
        )

        area_y0 = phase_y0 + header_h + spacing
        area_y1 = phase_y1
        flat_boxes = [b for r in phase.rows for b in r.boxes]
        if not flat_boxes:
            drawio_nodes.append(
                DrawioNode(
                    id=f"p{idx+1}_main",
                    value="",
                    x=center_x0 + center_w // 2 - 5,
                    y=area_y0 + max(0, (area_y1 - area_y0) // 2) - 5,
                    w=10,
                    h=10,
                    style="ellipse;html=1;fillColor=none;strokeColor=none;opacity=0;",
                )
            )
            continue
        main_idx = min(max(_pick_main_box_idx(phase), 0), len(flat_boxes) - 1)
        main_box = flat_boxes[main_idx]
        side_boxes = [b for i, b in enumerate(flat_boxes) if i != main_idx]
        left_boxes = [b for b in side_boxes if b.kind in ("secondary", "auxiliary")]
        right_boxes = [b for b in side_boxes if b.kind not in ("secondary", "auxiliary")]

        # Center
        fill_hex, stroke_hex = kind_fill_stroke(main_box.kind)
        wrapped = _wrap_text(draw, main_box.text, font_main, center_w - 2 * box_padding)
        lb = draw.textbbox((0, 0), "测", font=font_main)
        line_h = lb[3] - lb[1]
        text_h = len(wrapped) * line_h + max(0, (len(wrapped) - 1) * 2)
        area_h = max(1, area_y1 - area_y0)
        main_h = max(min_box_h, min(area_h, text_h + 2 * box_padding + 4))
        drawio_nodes.append(
            DrawioNode(
                id=f"p{idx+1}_main",
                value=main_box.text,
                x=center_x0,
                y=area_y0,
                w=center_w,
                h=main_h,
                style=default_box_style(
                    fill=fill_hex,
                    stroke=stroke_hex,
                    font_size=font_size,
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=center;verticalAlign=middle;",
            )
        )

        def add_side(x0: int, w: int, boxes: List[Any], prefix: str) -> None:
            if not boxes:
                return
            n = len(boxes)
            gap = spacing
            area_h = max(1, area_y1 - area_y0)
            h_each = max(1, int((area_h - gap * (n - 1)) // n))
            y = area_y0
            for i, b in enumerate(boxes, start=1):
                bh = max(1, min(area_y1 - y, max(min_box_h, h_each)))
                if y + bh > area_y1:
                    bh = max(1, area_y1 - y)
                fhex, shex = kind_fill_stroke(b.kind)
                drawio_nodes.append(
                    DrawioNode(
                        id=f"p{idx+1}_{prefix}{i}",
                        value=b.text,
                        x=x0,
                        y=y,
                        w=w,
                        h=bh,
                        style=default_box_style(
                            fill=fhex,
                            stroke=shex,
                            font_size=font_size,
                            font_color=str(color_presets.get("text", "#1F1F1F")),
                        )
                        + "align=center;verticalAlign=middle;",
                    )
                )
                y = y + bh + gap
                if y >= area_y1:
                    break

        add_side(left_x0, side_w, left_boxes, "l")
        add_side(right_x0, side_w, right_boxes, "r")

    if notes_enabled and note:
        drawio_nodes.append(
            DrawioNode(
                id="notes",
                value=note,
                x=margin,
                y=height - margin - note_h - 12,
                w=max(300, content_right - margin),
                h=note_h + 12,
                style=default_box_style(
                    fill="#FFFFFF",
                    stroke="#FFFFFF",
                    font_size=font_size,
                    font_color=str(color_presets.get("text", "#1F1F1F")),
                )
                + "align=left;verticalAlign=top;",
            )
        )

    edge_style = default_edge_style(
        stroke=str((renderer.get("stroke", {}) or {}).get("color", "#2F5597")),
        width=max(2, int((renderer.get("stroke", {}) or {}).get("width_px", 3))),
    )
    edges: List[DrawioEdge] = []
    for i in range(1, len(phases)):
        edges.append(
            DrawioEdge(
                id=f"e_main_{i}",
                source=f"p{i}_main",
                target=f"p{i+1}_main",
                style=edge_style,
            )
        )
    write_drawio(out_drawio, nodes=drawio_nodes, edges=edges)


def _render_png(
    spec: RoadmapSpec,
    config: Dict[str, Any],
    out_png: Path,
    out_svg: Path,
    out_drawio: Path,
) -> None:
    layout_cfg = config.get("layout", {}) if isinstance(config.get("layout", {}), dict) else {}
    cfg_lt = layout_cfg.get("template")
    cfg_ref = layout_cfg.get("template_ref")

    spec_lt = spec.layout_template
    spec_ref = spec.template_ref

    lt = spec_lt if spec_lt is not None else (str(cfg_lt).strip() if isinstance(cfg_lt, str) else None)
    ref = spec_ref if spec_ref is not None else (str(cfg_ref).strip() if isinstance(cfg_ref, str) else None)

    effective, _ = resolve_layout_template(layout_template=lt, template_ref=ref)
    if effective == "three-column":
        return _render_png_three_column(spec, config, out_png, out_svg, out_drawio)
    if effective == "layered-pipeline":
        return _render_png_layered_pipeline(spec, config, out_png, out_svg, out_drawio)
    # Unknown / classic fallback
    return _render_png_classic(spec, config, out_png, out_svg, out_drawio)


def render(spec_yaml: Path, config_yaml: Path, out_dir: Path) -> Tuple[Path, Path, Path]:
    config = load_yaml(config_yaml)
    spec_data = load_yaml(spec_yaml)
    spec = load_spec(spec_data)

    artifacts = config["output"]["artifacts"]
    out_png = out_dir / artifacts["png"]
    out_svg = out_dir / artifacts["svg"]
    out_drawio = out_dir / artifacts["drawio"]
    out_pdf = out_dir / str(artifacts.get("pdf", "roadmap.pdf"))

    # Always build internal outputs first (deterministic + also produces .drawio for CLI export).
    _render_png(spec, config, out_png, out_svg, out_drawio)

    renderer = config.get("renderer", {}) if isinstance(config.get("renderer", {}), dict) else {}
    canvas = renderer.get("canvas", {}) if isinstance(renderer.get("canvas", {}), dict) else {}
    width = int(canvas.get("width_px", 2400))
    height = int(canvas.get("height_px", 1800))
    border_px = int(((renderer.get("drawio", {}) or {}).get("border_px", 20)))
    bg_rgb = hex_to_rgb(str(renderer.get("background", "#FFFFFF")))

    drawio_cmd = ensure_drawio_cli(config)
    if drawio_cmd:
        try:
            _export_with_drawio_cli(drawio_cmd, out_drawio, out_png, "png", width, height, border_px)
            _ensure_png_canvas_size(out_png, width, height, bg_rgb)
            if bool((renderer.get("svg", {}) or {}).get("enabled", True)):
                _export_with_drawio_cli(drawio_cmd, out_drawio, out_svg, "svg", width, height, border_px)
            pdf_cfg = renderer.get("pdf", {}) if isinstance(renderer.get("pdf", {}), dict) else {}
            if bool(pdf_cfg.get("enabled", False)):
                _export_with_drawio_cli(drawio_cmd, out_drawio, out_pdf, "pdf", width, height, border_px)
        except Exception as exc:
            warn(f"draw.io CLI 导出失败，将使用内部渲染产物作为兜底：{exc}")
    else:
        pdf_cfg = renderer.get("pdf", {}) if isinstance(renderer.get("pdf", {}), dict) else {}
        if bool(pdf_cfg.get("enabled", False)):
            if bool(pdf_cfg.get("require_drawio_cli", False)):
                raise RuntimeError(
                    "已启用 PDF 导出，但未检测到 draw.io CLI（且 require_drawio_cli=true）。\n"
                    "可执行安装指引：\n- " + "\n- ".join(drawio_install_hints())
                )
            warn("未检测到 draw.io CLI：PDF 将降级为 PNG→PDF 栅格输出（如需矢量 PDF，请安装 draw.io CLI）。")
            img = Image.open(out_png).convert("RGB")
            try:
                out_pdf.parent.mkdir(parents=True, exist_ok=True)
                img.save(out_pdf, "PDF")
            finally:
                try:
                    img.close()
                except Exception:
                    pass
    return (out_png, out_svg, out_drawio)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Render nsfc-roadmap spec to PNG/SVG/(optional PDF).")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()

    render(args.spec, args.config, args.out_dir)


if __name__ == "__main__":
    main()
