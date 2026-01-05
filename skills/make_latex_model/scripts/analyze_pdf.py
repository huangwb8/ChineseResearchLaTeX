#!/usr/bin/env python3
"""
PDF 样式分析工具
提取 PDF 中的关键样式信息:字号、颜色、间距等
"""

import sys
import fitz  # PyMuPDF
import json
from pathlib import Path
from collections import defaultdict

def extract_color_info(color):
    """提取颜色信息 (RGB 0-255)"""
    if color is None:
        return None
    # 处理不同格式的颜色数据
    if isinstance(color, (list, tuple)):
        if len(color) >= 3:
            # 如果已经是 0-255 范围
            if color[0] > 1:
                return (int(color[0]), int(color[1]), int(color[2]))
            # 如果是 0-1 范围,转换为 0-255
            else:
                return (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
    return None

def analyze_pdf_fonts(pdf_path):
    """分析 PDF 中的字体使用情况"""
    doc = fitz.open(pdf_path)

    font_stats = defaultdict(lambda: {
        "count": 0,
        "sizes": set(),
        "colors": set(),
        "flags": set()
    })

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    font = span["font"]
                    size = span["size"]
                    color = extract_color_info(span.get("color"))
                    flags = span.get("flags", 0)

                    font_stats[font]["count"] += 1
                    font_stats[font]["sizes"].add(round(size, 2))
                    if color:
                        font_stats[font]["colors"].add(color)
                    font_stats[font]["flags"].add(flags)

    # 转换 sets 为 sorted lists 以便 JSON 序列化
    result = {}
    for font, stats in font_stats.items():
        result[font] = {
            "count": stats["count"],
            "sizes": sorted(list(stats["sizes"])),
            "colors": [list(c) for c in sorted(stats["colors"])],
            "is_bold": bool(2**4 in stats["flags"])  # 16 = bold
        }

    doc.close()
    return result

def analyze_page_layout(pdf_path):
    """分析页面布局信息"""
    doc = fitz.open(pdf_path)
    page = doc[0]  # 分析第一页

    # 获取页面尺寸
    rect = page.rect
    width_pt = rect.width
    height_pt = rect.height

    # 转换为 cm (1 pt = 0.0352778 cm)
    width_cm = round(width_pt * 0.0352778, 2)
    height_cm = round(height_pt * 0.0352778, 2)

    # 分析文本边界来确定边距
    blocks = page.get_text("dict")["blocks"]
    if blocks:
        # 找到文本块的边界
        text_left = min(b["bbox"][0] for b in blocks if "lines" in b)
        text_right = max(b["bbox"][2] for b in blocks if "lines" in b)
        text_top = min(b["bbox"][1] for b in blocks if "lines" in b)
        text_bottom = max(b["bbox"][3] for b in blocks if "lines" in b)

        # 计算边距 (pt 转 cm)
        margin_left = round(text_left * 0.0352778, 2)
        margin_right = round((width_pt - text_right) * 0.0352778, 2)
        margin_top = round(text_top * 0.0352778, 2)
        margin_bottom = round((height_pt - text_bottom) * 0.0352778, 2)
    else:
        margin_left = margin_right = margin_top = margin_bottom = None

    doc.close()

    return {
        "page_size_cm": (width_cm, height_cm),
        "margins_cm": {
            "left": margin_left,
            "right": margin_right,
            "top": margin_top,
            "bottom": margin_bottom
        }
    }

def analyze_line_spacing(pdf_path, page_num=0):
    """分析行距"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    blocks = page.get_text("dict")["blocks"]

    line_heights = []

    for block in blocks:
        if "lines" not in block:
            continue

        prev_y = None
        for line in block["lines"]:
            y0 = line["bbox"][1]
            y1 = line["bbox"][3]
            height = y1 - y0

            if prev_y is not None:
                line_spacing = y0 - prev_y
                line_heights.append(line_spacing)

            prev_y = y0

    # 计算平均行距和字体大小的比率
    if line_heights:
        avg_line_spacing = sum(line_heights) / len(line_heights)
    else:
        avg_line_spacing = 0

    doc.close()
    return round(avg_line_spacing, 2)

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_pdf.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    print(f"\n分析 PDF: {pdf_path}\n")

    # 分析页面布局
    print("=" * 60)
    print("页面布局")
    print("=" * 60)
    layout = analyze_page_layout(pdf_path)
    print(f"页面尺寸: {layout['page_size_cm'][0]} cm x {layout['page_size_cm'][1]} cm")
    print(f"边距:")
    print(f"  左:   {layout['margins_cm']['left']} cm")
    print(f"  右:   {layout['margins_cm']['right']} cm")
    print(f"  上:   {layout['margins_cm']['top']} cm")
    print(f"  下:   {layout['margins_cm']['bottom']} cm")

    # 分析字体
    print("\n" + "=" * 60)
    print("字体使用统计")
    print("=" * 60)
    fonts = analyze_pdf_fonts(pdf_path)

    # 按使用频率排序
    sorted_fonts = sorted(fonts.items(), key=lambda x: x[1]["count"], reverse=True)

    for font, stats in sorted_fonts[:10]:  # 显示前 10 个字体
        print(f"\n字体: {font}")
        print(f"  使用次数: {stats['count']}")
        print(f"  字号: {stats['sizes']}")
        print(f"  颜色 (RGB): {stats['colors']}")
        print(f"  是否加粗: {stats['is_bold']}")

    # 分析行距
    print("\n" + "=" * 60)
    print("行距分析")
    print("=" * 60)
    line_spacing = analyze_line_spacing(pdf_path)
    print(f"平均行距: {line_spacing} pt")

    # 导出为 JSON
    output_path = Path(pdf_path).stem + "_analysis.json"
    output_data = {
        "layout": layout,
        "fonts": fonts,
        "line_spacing_pt": line_spacing
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n详细分析结果已保存到: {output_path}")

if __name__ == "__main__":
    main()
