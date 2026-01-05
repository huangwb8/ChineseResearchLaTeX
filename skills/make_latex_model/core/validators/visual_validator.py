#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉相似度验证器 - 检查 PDF 视觉相似度
"""

import re
from pathlib import Path
from typing import Dict, Any, List
from ..validator_base import ValidatorBase, ValidationContext, ValidationResult


class VisualValidator(ValidatorBase):
    """视觉相似度验证器 - 第三优先级"""

    def get_name(self) -> str:
        return "visual"

    def get_priority(self) -> int:
        return 3

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        执行视觉相似度验证

        检查项:
        1. PDF 页面尺寸
        2. 每行字数统计（需人工对比）
        3. 提供视觉对比指导
        """
        result = ValidationResult(passed=[], warnings=[], failed=[])

        project_path = context.project_path
        pdf_file = project_path / "main.pdf"

        if not pdf_file.exists():
            result.add_fail(f"PDF 文件不存在: {pdf_file}")
            return result

        # 1. 检查 PDF 页面尺寸
        self._check_pdf_page_size(pdf_file, result)

        # 2. 尝试统计每行字数（需要 PyMuPDF）
        self._count_chars_per_line(pdf_file, result)

        # 3. 提供视觉对比指导
        if result.is_success():
            result.add_pass("视觉相似度验证器运行完成")
            result.add_warning("视觉相似度需要人工对比 PDF 与 Word 模板")
            result.add_warning("请检查：每行字数、换行位置、整体布局")

        return result

    def _check_pdf_page_size(self, pdf_file: Path, result: ValidationResult):
        """检查 PDF 页面尺寸"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            result.add_warning("未安装 PyMuPDF，无法检查 PDF 页面尺寸")
            result.add_warning("安装命令: pip install PyMuPDF")
            return

        try:
            doc = fitz.open(pdf_file)
            if len(doc) == 0:
                result.add_fail("PDF 文件为空")
                return

            # 获取第一页尺寸
            page = doc[0]
            width_pt = page.rect.width
            height_pt = page.rect.height

            # 转换为 cm (1 pt = 0.0352778 cm)
            width_cm = width_pt * 0.0352778
            height_cm = height_pt * 0.0352778

            # A4 纸尺寸: 21.0 cm x 29.7 cm
            a4_width, a4_height = 21.0, 29.7

            width_diff = abs(width_cm - a4_width)
            height_diff = abs(height_cm - a4_height)

            if width_diff < 0.5 and height_diff < 0.5:
                result.add_pass(f"PDF 页面尺寸正确: {width_cm:.1f} cm x {height_cm:.1f} cm (A4)")
            else:
                result.add_warning(
                    f"PDF 页面尺寸可能有偏差: {width_cm:.1f} cm x {height_cm:.1f} cm "
                    f"(A4 标准: {a4_width} cm x {a4_height} cm)"
                )

            doc.close()

        except Exception as e:
            result.add_warning(f"无法读取 PDF 页面尺寸: {e}")

    def _count_chars_per_line(self, pdf_file: Path, result: ValidationResult):
        """统计每行字数（需要 PyMuPDF）"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return

        try:
            doc = fitz.open(pdf_file)
            if len(doc) == 0:
                return

            # 统计第一页的文本
            page = doc[0]
            text = page.get_text("text")

            # 按行分割
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            if lines:
                # 统计每行字数
                char_counts = [len(line) for line in lines]
                avg_chars = sum(char_counts) / len(char_counts)
                max_chars = max(char_counts)
                min_chars = min(char_counts)

                result.add_pass(f"第一页文本统计:")
                result.add_pass(f"  总行数: {len(lines)}")
                result.add_pass(f"  平均字数: {avg_chars:.1f} 字/行")
                result.add_pass(f"  字数范围: {min_chars} - {max_chars} 字/行")

                # 检查是否合理（A4 纸正常行约 35-40 字）
                if avg_chars < 20:
                    result.add_warning("平均每行字数偏少，可能存在排版问题")
                elif avg_chars > 50:
                    result.add_warning("平均每行字数偏多，可能存在排版问题")

                # 提供视觉对比建议
                result.add_warning("⚠️ 需要人工对比 Word 模板:")
                result.add_warning("  1. 在 Microsoft Word 中打开 2026 年模板")
                result.add_warning("  2. 导出为 PDF (不能使用 QuickLook)")
                result.add_warning("  3. 对比 LaTeX 生成的 PDF 与 Word PDF")
                result.add_warning("  4. 检查每行字数、换行位置是否一致")

            doc.close()

        except Exception as e:
            result.add_warning(f"无法统计 PDF 文本: {e}")
