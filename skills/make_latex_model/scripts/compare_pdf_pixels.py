#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 像素对比工具
对比两个 PDF 文件的像素差异

使用方法:
    # 对比两个 PDF 文件
    python scripts/compare_pdf_pixels.py baseline.pdf output.pdf

    # 生成 HTML 报告
    python scripts/compare_pdf_pixels.py baseline.pdf output.pdf --report diff_report.html

    # 只对比第一页
    python scripts/compare_pdf_pixels.py baseline.pdf output.pdf --page 1

    # 设置容差
    python scripts/compare_pdf_pixels.py baseline.pdf output.pdf --tolerance 5

    # 生成差异热图
    python scripts/compare_pdf_pixels.py baseline.pdf output.pdf --heatmap diff.png
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from datetime import datetime
import io


def check_dependencies():
    """检查依赖库"""
    missing = []

    try:
        import fitz
    except ImportError:
        missing.append("PyMuPDF (fitz)")

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        missing.append("Pillow")

    return missing


def pdf_to_page_images(pdf_path: Path, dpi: int = 150, page_num: int = None) -> List[np.ndarray]:
    """
    将 PDF 页面转换为图像数组

    Args:
        pdf_path: PDF 文件路径
        dpi: 分辨率
        page_num: 页码（None 表示所有页面）

    Returns:
        图像数组列表
    """
    try:
        import fitz
    except ImportError:
        print("错误: 需要安装 PyMuPDF")
        print("安装命令: pip install PyMuPDF")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    images = []

    # 确定页面范围
    if page_num is not None:
        pages = [page_num - 1] if page_num <= len(doc) else [0]
    else:
        pages = range(len(doc))

    for page_num in pages:
        page = doc[page_num]

        # 渲染为图像
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        # 转换为 numpy 数组
        img_data = pix.tobytes("ppm")
        from PIL import Image
        img = Image.open(io.BytesIO(img_data))
        img_array = np.array(img)

        images.append(img_array)

    doc.close()
    return images


def compare_images(img1: np.ndarray, img2: np.ndarray, tolerance: int = 2) -> Tuple[float, np.ndarray]:
    """
    对比两个图像数组

    Args:
        img1: 第一个图像
        img2: 第二个图像
        tolerance: 容差（RGB 值差异）

    Returns:
        (差异比例, 差异掩码)
    """
    # 确保图像大小相同
    if img1.shape != img2.shape:
        # 调整 img2 到 img1 的大小
        from PIL import Image
        img2_pil = Image.fromarray(img2.astype('uint8'))
        img2_pil = img2_pil.resize((img1.shape[1], img1.shape[0]))
        img2 = np.array(img2_pil)

    # 计算像素差异
    diff = np.abs(img1.astype(int) - img2.astype(int))
    diff_mask = np.any(diff > tolerance, axis=2)

    # 计算差异比例
    total_pixels = diff_mask.size
    diff_pixels = np.sum(diff_mask)
    changed_ratio = diff_pixels / total_pixels

    return changed_ratio, diff_mask


def extract_diff_features(diff_mask: np.ndarray) -> Dict[str, float]:
    """
    从差异掩码提取结构化特征（用于后续的根因推断）
    """
    # 行/列方向差异强度（用于判断“水平条纹/垂直条纹”）
    h, w = diff_mask.shape[:2]
    row_sums = (np.sum(diff_mask, axis=1).astype(float) / max(1, w))
    col_sums = (np.sum(diff_mask, axis=0).astype(float) / max(1, h))

    row_variance = float(np.var(row_sums)) if row_sums.size else 0.0
    col_variance = float(np.var(col_sums)) if col_sums.size else 0.0

    # 上/中/下三区域差异比例
    h = diff_mask.shape[0]
    third = max(1, h // 3)
    top = diff_mask[:third, :]
    mid = diff_mask[third: 2 * third, :]
    bot = diff_mask[2 * third:, :]

    def _ratio(mask: np.ndarray) -> float:
        return float(np.sum(mask)) / float(mask.size) if mask.size else 0.0

    return {
        "row_variance": row_variance,
        "col_variance": col_variance,
        "region_top_ratio": _ratio(top),
        "region_middle_ratio": _ratio(mid),
        "region_bottom_ratio": _ratio(bot),
    }


def generate_diff_heatmap(img1: np.ndarray, img2: np.ndarray, diff_mask: np.ndarray,
                          output_path: Path):
    """
    生成差异热图

    Args:
        img1: 第一个图像
        img2: 第二个图像
        diff_mask: 差异掩码
        output_path: 输出路径
    """
    from PIL import Image, ImageDraw

    # 创建热图（红色表示差异）
    heatmap = img1.copy()
    heatmap[diff_mask] = [255, 0, 0]  # 红色

    # 保存
    img_pil = Image.fromarray(heatmap.astype('uint8'))
    img_pil.save(output_path)


def generate_html_report(baseline_pdf: Path, output_pdf: Path, page_results: List[Dict],
                        report_path: Path):
    """生成 HTML 报告"""

    total_diff = sum(r["changed_ratio"] for r in page_results)
    avg_diff = total_diff / len(page_results) if page_results else 0

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF 像素对比报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}
        .page-result {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .diff-bar {{
            height: 20px;
            background: #e5e7eb;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .diff-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #f59e0b 50%, #ef4444 100%);
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 PDF 像素对比报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="value">{len(page_results)}</div>
            <div>对比页数</div>
        </div>
        <div class="stat-card">
            <div class="value">{avg_diff:.2%}</div>
            <div>平均差异</div>
        </div>
    </div>
"""

    for i, result in enumerate(page_results, 1):
        diff_percent = result["changed_ratio"] * 100
        color = "#10b981" if diff_percent < 1 else "#f59e0b" if diff_percent < 5 else "#ef4444"

        html += f"""
    <div class="page-result">
        <h3>第 {i} 页</h3>
        <div class="diff-bar">
            <div class="diff-fill" style="width: {diff_percent}%; background: {color};"></div>
        </div>
        <p>差异比例: <strong>{diff_percent:.2f}%</strong></p>
        <p>差异像素: {result["diff_pixels"]} / {result["total_pixels"]}</p>
    </div>
"""

    html += """
</body>
</html>
"""

    report_path.write_text(html, encoding="utf-8")


def main():
    # 检查依赖
    missing = check_dependencies()
    if missing:
        print(f"错误: 缺少依赖库: {', '.join(missing)}")
        print("安装命令:")
        for lib in missing:
            print(f"  pip install {lib}")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="PDF 像素对比工具")
    parser.add_argument("baseline_pdf", type=Path, help="基准 PDF 文件")
    parser.add_argument("output_pdf", type=Path, help="输出 PDF 文件")
    parser.add_argument("--report", type=Path, help="生成 HTML 报告")
    parser.add_argument("--page", type=int, help="只对比指定页码")
    parser.add_argument(
        "--mode",
        choices=["page", "paragraph"],
        default="page",
        help="对比模式：page=整页像素对比（默认）；paragraph=逐段像素对比（推荐用于空模板/填充正文场景）",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.85,
        help="逐段模式下的段落文本匹配阈值（0-1，默认 0.85）",
    )
    parser.add_argument("--tolerance", type=int, default=2, help="像素容差（默认 2）")
    parser.add_argument("--dpi", type=int, default=150, help="渲染分辨率（默认 150）")
    parser.add_argument("--heatmap", type=Path, help="生成差异热图")
    parser.add_argument("--json-out", type=Path, help="保存对比结果到 JSON（包含 avg_diff_ratio/pages）")
    parser.add_argument("--features-out", type=Path, help="保存差异特征到 JSON（用于 AI/启发式分析）")

    args = parser.parse_args()

    # 检查文件存在
    if not args.baseline_pdf.exists():
        print(f"错误: 基准 PDF 不存在: {args.baseline_pdf}")
        sys.exit(1)

    if not args.output_pdf.exists():
        print(f"错误: 输出 PDF 不存在: {args.output_pdf}")
        sys.exit(1)

    print(f"📊 正在对比 PDF 文件...")
    print(f"  基准: {args.baseline_pdf}")
    print(f"  输出: {args.output_pdf}")
    print(f"  模式: {args.mode}")
    print(f"  容差: {args.tolerance}")
    print(f"  分辨率: {args.dpi} DPI")

    page_results = []
    page_features = []

    if args.mode == "paragraph":
        print("\n🧩 正在逐段提取与匹配...")
        try:
            from core.paragraph_alignment import (
                compute_internal_variance,
                extract_paragraphs_from_pdf,
                image_diff_ratio,
                match_paragraphs,
            )
        except Exception as e:
            print(f"错误: 无法导入逐段对齐模块 core/paragraph_alignment.py: {e}")
            sys.exit(1)

        baseline_paras = extract_paragraphs_from_pdf(
            args.baseline_pdf, dpi=args.dpi, page_num=args.page, include_images=True
        )
        output_paras = extract_paragraphs_from_pdf(
            args.output_pdf, dpi=args.dpi, page_num=args.page, include_images=True
        )

        matches = match_paragraphs(
            baseline_paras, output_paras, min_similarity=float(args.min_similarity)
        )

        # 建立 id -> Paragraph
        bmap = {(p.page_num, p.paragraph_id): p for p in baseline_paras}
        omap = {(p.page_num, p.paragraph_id): p for p in output_paras}

        # 按页聚合
        matches_by_page = {}
        for m in matches:
            matches_by_page.setdefault(int(m.get("page_num") or 1), []).append(m)

        for page_num in sorted(matches_by_page.keys()):
            ms = sorted(
                matches_by_page[page_num],
                key=lambda m: (float(m["baseline"]["bbox"][1]), int(m["baseline"]["paragraph_id"])),
            )

            total_weight = 0
            weighted_sum = 0.0
            diff_pixels_sum = 0
            total_pixels_sum = 0

            x0_diffs = []
            y0_diffs = []
            gap_diffs = []
            internal_vars = []

            prev_b = None
            prev_o = None

            paragraph_details = []
            for m in ms:
                b_id = int(m["baseline"]["paragraph_id"])
                o_id = int(m["target"]["paragraph_id"])
                b = bmap.get((page_num, b_id))
                o = omap.get((page_num, o_id))
                if b is None or o is None:
                    continue

                ratio, diff_pixels, total_pixels = image_diff_ratio(
                    b.image_rgb, o.image_rgb, tolerance=int(args.tolerance)
                )
                total_weight += total_pixels
                weighted_sum += ratio * float(total_pixels)
                diff_pixels_sum += diff_pixels
                total_pixels_sum += total_pixels

                pos_diff = {
                    "x0": float(o.bbox[0] - b.bbox[0]),
                    "y0": float(o.bbox[1] - b.bbox[1]),
                    "x1": float(o.bbox[2] - b.bbox[2]),
                    "y1": float(o.bbox[3] - b.bbox[3]),
                }
                x0_diffs.append(pos_diff["x0"])
                y0_diffs.append(pos_diff["y0"])

                iv_b = compute_internal_variance(b)
                iv_o = compute_internal_variance(o)
                internal_vars.append(
                    (float(iv_b["line_height_variance"]) + float(iv_o["line_height_variance"])) / 2.0
                )

                if (
                    prev_b is not None
                    and prev_o is not None
                    and b.page_num == prev_b.page_num
                    and o.page_num == prev_o.page_num
                ):
                    b_gap = float(b.bbox[1] - prev_b.bbox[3])
                    o_gap = float(o.bbox[1] - prev_o.bbox[3])
                    gap_diffs.append(o_gap - b_gap)

                prev_b, prev_o = b, o

                paragraph_details.append(
                    {
                        "baseline_paragraph_id": b.paragraph_id,
                        "output_paragraph_id": o.paragraph_id,
                        "text_similarity": float(m.get("text_similarity") or 0.0),
                        "pixel_diff_ratio": float(ratio),
                        "diff_pixels": int(diff_pixels),
                        "total_pixels": int(total_pixels),
                        "position_diff": pos_diff,
                        "internal_variance": {"baseline": iv_b, "output": iv_o},
                    }
                )

            changed_ratio = (weighted_sum / float(total_weight)) if total_weight else 1.0

            page_results.append(
                {
                    "page_num": int(page_num),
                    "changed_ratio": float(changed_ratio),
                    "diff_pixels": int(diff_pixels_sum),
                    "total_pixels": int(total_pixels_sum),
                    "match_count": int(len(paragraph_details)),
                }
            )

            # 简单方差（无需 numpy）
            def _var(vals):
                if len(vals) <= 1:
                    return 0.0
                m = sum(vals) / len(vals)
                return sum((v - m) ** 2 for v in vals) / len(vals)

            page_features.append(
                {
                    "page_num": int(page_num),
                    "changed_ratio": float(changed_ratio),
                    "match_count": int(len(paragraph_details)),
                    "paragraph_position_variance": float(_var(y0_diffs)),
                    "paragraph_spacing_variance": float(_var(gap_diffs)),
                    "indent_variance": float(_var(x0_diffs)),
                    "avg_internal_line_variance": float(sum(internal_vars) / len(internal_vars))
                    if internal_vars
                    else 0.0,
                    "paragraphs": paragraph_details,
                }
            )

        num_pages = len(page_results)
        if num_pages == 0:
            print("错误: 无可对比页面（可能未匹配到段落）")
            sys.exit(1)

        avg_diff = sum(r["changed_ratio"] for r in page_results) / len(page_results)
    else:
        # 转换 PDF 为图像
        print("\n📖 正在渲染 PDF...")
        baseline_images = pdf_to_page_images(args.baseline_pdf, args.dpi, args.page)
        output_images = pdf_to_page_images(args.output_pdf, args.dpi, args.page)

        # 确保页数相同
        num_pages = min(len(baseline_images), len(output_images))
        print(f"  对比页数: {num_pages}")
        if num_pages == 0:
            print("错误: 无可对比页面（PDF 可能为空或渲染失败）")
            sys.exit(1)

        # 对比每一页
        for i in range(num_pages):
            print(f"\n🔍 对比第 {i+1} 页...")

            img1 = baseline_images[i]
            img2 = output_images[i]

            changed_ratio, diff_mask = compare_images(img1, img2, args.tolerance)

            diff_pixels = np.sum(diff_mask)
            total_pixels = diff_mask.size

            print(f"  差异比例: {changed_ratio:.2%}")
            print(f"  差异像素: {diff_pixels} / {total_pixels}")

            page_results.append({
                "page_num": i + 1,
                "changed_ratio": float(changed_ratio),
                "diff_pixels": int(diff_pixels),
                "total_pixels": int(total_pixels),
            })

            feats = extract_diff_features(diff_mask)
            page_features.append(
                {
                    "page_num": i + 1,
                    "changed_ratio": float(changed_ratio),
                    "row_variance": float(feats["row_variance"]),
                    "col_variance": float(feats["col_variance"]),
                    "region_ratios": {
                        "top": float(feats["region_top_ratio"]),
                        "middle": float(feats["region_middle_ratio"]),
                        "bottom": float(feats["region_bottom_ratio"]),
                    },
                }
            )

            # 生成热图
            if args.heatmap:
                heatmap_path = args.heatmap.parent / f"{args.heatmap.stem}_page{i+1}{args.heatmap.suffix}"
                generate_diff_heatmap(img1, img2, diff_mask, heatmap_path)
                print(f"  热图已保存: {heatmap_path}")

        # 计算平均差异
        avg_diff = sum(r["changed_ratio"] for r in page_results) / len(page_results)

    print(f"\n{'='*60}")
    print(f"对比总结")
    print(f"{'='*60}")
    print(f"总页数: {num_pages}")
    print(f"平均差异: {avg_diff:.2%}")

    if avg_diff < 0.01:
        print("✅ 差异很小，样式对齐良好")
    elif avg_diff < 0.05:
        print("⚠️  差异中等，可能需要微调")
    else:
        print("❌ 差异较大，需要仔细检查样式参数")

    # 生成报告
    if args.report:
        print(f"\n📄 正在生成 HTML 报告...")
        generate_html_report(args.baseline_pdf, args.output_pdf, page_results, args.report)
        print(f"✅ 报告已保存: {args.report}")

    # JSON 输出（供脚本解析）
    if args.json_out:
        payload = {
            "baseline_pdf": str(args.baseline_pdf),
            "output_pdf": str(args.output_pdf),
            "mode": str(args.mode),
            "dpi": args.dpi,
            "tolerance": args.tolerance,
            "generated_at": datetime.now().isoformat(),
            "pages": page_results,
            "avg_diff_ratio": avg_diff,
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 特征输出（供 DiffAnalyzer 使用）
    if args.features_out:
        payload = {
            "generated_at": datetime.now().isoformat(),
            "mode": str(args.mode),
            "pages": page_features,
            "avg_diff_ratio": avg_diff,
        }
        args.features_out.parent.mkdir(parents=True, exist_ok=True)
        args.features_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
