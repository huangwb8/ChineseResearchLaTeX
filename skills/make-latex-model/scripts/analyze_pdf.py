#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 样式分析工具
提取 PDF 中的关键样式信息:字号、颜色、间距等

用于分析 Word 导出的 PDF 基准，自动提取样式参数
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SKILL_DIR))

# 检查依赖
try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ 错误: 缺少依赖库 PyMuPDF")
    print("请运行: pip install PyMuPDF")
    sys.exit(1)

# 导入 WorkspaceManager
try:
    from scripts.core.workspace_manager import WorkspaceManager
except ImportError:
    print("⚠️  警告: 无法导入 WorkspaceManager，将使用当前目录保存结果")
    WorkspaceManager = None

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
    parser = argparse.ArgumentParser(
        description="PDF 样式分析工具 - 提取 PDF 中的关键样式信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analyze_pdf.py word_baseline.pdf
  python analyze_pdf.py projects/NSFC_General/template/word.pdf --project NSFC_General
  # 输出将保存到：projects/NSFC_General/.make_latex_model/baselines/<stem>_analysis.json
  python analyze_pdf.py word.pdf --output custom_analysis.json
        """
    )
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("--project", help="项目名称（如 NSFC_General），用于保存到 projects/<project>/.make_latex_model/baselines/")
    parser.add_argument("--output", "-o", help="自定义输出 JSON 文件路径")
    parser.add_argument("--no-workspace", action="store_true", help="不使用工作空间，直接保存到当前目录")

    args = parser.parse_args()

    pdf_path = args.pdf_path
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        print(f"❌ 错误: 文件不存在: {pdf_path}")
        sys.exit(1)

    if not pdf_file.suffix.lower() == '.pdf':
        print(f"⚠️  警告: 文件扩展名不是 .pdf: {pdf_path}")
        print("继续分析...\n")

    print(f"\n{'='*60}")
    print(f"PDF 样式分析工具")
    print(f"{'='*60}")
    print(f"分析文件: {pdf_path}")
    print(f"文件大小: {pdf_file.stat().st_size / 1024:.1f} KB")
    print(f"{'='*60}\n")

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
    output_path = None
    workspace_info = ""

    # 优先级 1: 用户指定了自定义输出路径
    if args.output:
        output_path = Path(args.output)
        workspace_info = "(自定义路径)"
    # 优先级 2: 用户指定了项目名称且 WorkspaceManager 可用
    elif args.project and WorkspaceManager and not args.no_workspace:
        ws_manager = WorkspaceManager(SKILL_DIR)
        baseline_dir = ws_manager.get_baseline_path(args.project)
        output_path = baseline_dir / f"{pdf_file.stem}_analysis.json"
        workspace_info = f"(工作空间: {baseline_dir})"
    # 默认: 使用 PDF 所在目录（向后兼容）
    else:
        # NOTE: keep backward-compatible default (next to the PDF), but ensure Path
        output_path = Path(pdf_path).with_name(Path(pdf_path).stem + "_analysis.json")
        if WorkspaceManager and not args.no_workspace:
            workspace_info = "(当前目录，建议使用 --project 参数保存到 projects/<project>/.make_latex_model/baselines/)"

    output_data = {
        "source_file": str(pdf_file),
        "file_size_kb": round(pdf_file.stat().st_size / 1024, 2),
        "layout": layout,
        "fonts": fonts,
        "line_spacing_pt": line_spacing
    }

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"✅ 分析完成")
    print(f"{'='*60}")
    print(f"详细分析结果已保存到: {output_path} {workspace_info}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
