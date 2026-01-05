#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
样式参数验证器 - 检查样式参数与 Word 模板一致性
"""

import re
from pathlib import Path
from typing import Dict, Any, List
from ..validator_base import ValidatorBase, ValidationContext, ValidationResult


class StyleValidator(ValidatorBase):
    """样式参数验证器 - 第二优先级"""

    def get_name(self) -> str:
        return "style"

    def get_priority(self) -> int:
        return 2

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        执行样式参数验证

        检查项:
        1. 行距设置（baselinestretch 或 linespread）
        2. 颜色定义（MsBlue RGB 0,112,192）
        3. 页面边距（左 3.20cm, 右 3.14cm）
        4. 字号系统（三号、四号、小四等）
        5. 标题格式（缩进、间距、编号）
        """
        result = ValidationResult(passed=[], warnings=[], failed=[])

        project_path = context.project_path
        config_file = project_path / "extraTex" / "@config.tex"

        if not config_file.exists():
            result.add_fail(f"样式配置文件不存在: {config_file}")
            return result

        try:
            config_content = config_file.read_text(encoding="utf-8")
        except Exception as e:
            result.add_fail(f"无法读取配置文件: {e}")
            return result

        # 1. 检查行距设置
        self._check_line_spacing(config_content, result, context.tolerance)

        # 2. 检查颜色定义
        self._check_color_definitions(config_content, result, context.tolerance)

        # 3. 检查页面边距
        self._check_page_margins(config_content, result, context.tolerance)

        # 4. 检查字号系统
        self._check_font_sizes(config_content, result, context.tolerance)

        # 5. 检查标题格式
        self._check_title_format(config_content, result, context.tolerance)

        return result

    def _check_line_spacing(self, content: str, result: ValidationResult, tolerance: Dict[str, Any]):
        """检查行距设置"""
        # 查找 baselinestretch 或 linespread
        baseline_match = re.search(r"\\renewcommand{\\baselinestretch}\s*\{([0-9.]+)\}", content)
        linespread_match = re.search(r"\\linespread\s*\{([0-9.]+)\}", content)

        if baseline_match:
            line_spacing = float(baseline_match.group(1))
            expected = tolerance.get("line_height_diff", 1.5)
            diff = abs(line_spacing - expected)

            if diff <= tolerance.get("line_height_diff", 0.1):
                result.add_pass(f"行距设置正确: baselinestretch{{{line_spacing}}}")
            else:
                result.add_warning(f"行距可能不正确: {line_spacing} (期望约 {expected})")

        elif linespread_match:
            line_spacing = float(linespread_match.group(1))
            result.add_pass(f"行距设置: linespread{{{line_spacing}}}")
        else:
            result.add_warning("未找到行距设置 (baselinestretch 或 linespread)")

    def _check_color_definitions(self, content: str, result: ValidationResult, tolerance: Dict[str, Any]):
        """检查颜色定义"""
        # 检查 MsBlue 颜色定义
        msblue_match = re.search(
            r"\\definecolor\{MsBlue\}\s*\{RGB\}\s*\{([0-9]+),\s*([0-9]+),\s*([0-9]+)\}",
            content
        )

        if msblue_match:
            r, g, b = int(msblue_match.group(1)), int(msblue_match.group(2)), int(msblue_match.group(3))
            expected_r, expected_g, expected_b = 0, 112, 192

            color_diff = max(abs(r - expected_r), abs(g - expected_g), abs(b - expected_b))
            max_diff = tolerance.get("color_diff", 2)

            if color_diff <= max_diff:
                result.add_pass(f"MsBlue 颜色正确: RGB {r},{g},{b}")
            else:
                result.add_fail(f"MsBlue 颜色不正确: RGB {r},{g},{b} (期望 {expected_r},{expected_g},{expected_b})")
        else:
            result.add_warning("未找到 MsBlue 颜色定义")

    def _check_page_margins(self, content: str, result: ValidationResult, tolerance: Dict[str, Any]):
        """检查页面边距"""
        # 查找 geometry 设置
        geometry_match = re.search(
            r"\\geometry\s*\{[^}]*left=([0-9.]+)cm[^}]*right=([0-9.]+)cm",
            content
        )

        if geometry_match:
            left_margin = float(geometry_match.group(1))
            right_margin = float(geometry_match.group(2))

            expected_left, expected_right = 3.20, 3.14
            max_diff = tolerance.get("margin_diff", 0.5)

            left_diff = abs(left_margin - expected_left)
            right_diff = abs(right_margin - expected_right)

            if left_diff <= max_diff and right_diff <= max_diff:
                result.add_pass(f"页面边距正确: 左 {left_margin}cm, 右 {right_margin}cm")
            else:
                result.add_warning(
                    f"页面边距可能有偏差: 左 {left_margin}cm (期望 {expected_left}), "
                    f"右 {right_margin}cm (期望 {expected_right})"
                )
        else:
            result.add_warning("未找到明确的页面边距设置 (geometry)")

    def _check_font_sizes(self, content: str, result: ValidationResult, tolerance: Dict[str, Any]):
        """检查字号系统"""
        # 检查常见字号定义
        font_size_patterns = {
            "三号": r"\\newcommand\{\\sanHao\}\s*\{\s*\\fontsize\{([0-9.]+)\)\{([0-9.]+)\}",
            "四号": r"\\newcommand\{\\siHao\}\s*\{\s*\\fontsize\{([0-9.]+)\)\{([0-9.]+)\}",
            "小四": r"\\newcommand\{\\xiaoSi\}\s*\{\s*\\fontsize\{([0-9.]+)\)\{([0-9.]+)\}",
        }

        for name, pattern in font_size_patterns.items():
            match = re.search(pattern, content)
            if match:
                font_size = float(match.group(1))
                result.add_pass(f"字号定义存在: {name} = {font_size}pt")
            else:
                result.add_warning(f"未找到字号定义: {name}")

    def _check_title_format(self, content: str, result: ValidationResult, tolerance: Dict[str, Any]):
        """检查标题格式"""
        # 检查 section 标题缩进
        section_indent_match = re.search(
            r"\\titleformat\{\\section\}\[^}]*\{[^}]*\}\[^}]*\{[^}]*\\hspace\*\{([0-9.]+)em\}",
            content
        )

        if section_indent_match:
            indent = float(section_indent_match.group(1))
            expected_indent = 1.45
            diff = abs(indent - expected_indent)

            if diff <= tolerance.get("spacing_diff", 0.1):
                result.add_pass(f"Section 标题缩进正确: {indent}em")
            else:
                result.add_warning(f"Section 标题缩进可能有偏差: {indent}em (期望 {expected_indent})")
        else:
            result.add_warning("未找到 Section 标题缩进设置")

        # 检查是否有 titleformat 定义
        if re.search(r"\\titleformat", content):
            result.add_pass("标题格式定义存在 (titleformat)")
        else:
            result.add_warning("未找到标题格式定义 (titleformat)")
