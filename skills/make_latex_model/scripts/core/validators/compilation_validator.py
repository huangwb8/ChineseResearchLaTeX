#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编译验证器 - 检查 LaTeX 编译状态
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..validator_base import ValidatorBase, ValidationContext, ValidationResult


class CompilationValidator(ValidatorBase):
    """编译验证器 - 第一优先级"""

    def get_name(self) -> str:
        return "compilation"

    def get_priority(self) -> int:
        return 1

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        执行编译验证

        检查项:
        1. PDF 文件是否存在
        2. 编译日志中是否有错误
        3. 编译日志中是否有警告
        4. 跨平台编译测试（可选）
        """
        result = ValidationResult(passed=[], warnings=[], failed=[])

        project_path = context.project_path
        pdf_file = project_path / "main.pdf"
        log_file = project_path / "main.log"

        # 1. 检查 PDF 文件是否存在
        if pdf_file.exists():
            result.add_pass(f"PDF 文件存在: {pdf_file}")

            # 获取文件大小
            pdf_size = pdf_file.stat().st_size
            if pdf_size > 1000:  # 至少 1KB
                result.add_pass(f"PDF 文件大小正常: {pdf_size / 1024:.1f} KB")
            else:
                result.add_fail(f"PDF 文件过小: {pdf_size} bytes，可能编译失败")
        else:
            result.add_fail(f"PDF 文件不存在: {pdf_file}")
            return result

        # 2. 检查编译日志
        if log_file.exists():
            errors, warnings = self._parse_log_file(log_file)

            if errors:
                result.add_fail(f"发现 {len(errors)} 个编译错误")
                for error in errors[:3]:  # 只显示前 3 个
                    result.add_fail(f"  {error}")
            else:
                result.add_pass("编译无错误")

            if warnings:
                result.add_warning(f"发现 {len(warnings)} 个编译警告")
                # 显示前 5 个警告
                for warning in warnings[:5]:
                    result.add_warning(f"  {warning}")
            else:
                result.add_pass("编译无警告")
        else:
            result.add_warning("编译日志不存在，跳过日志检查")

        # 3. 检查参考文献（可选）
        bbl_file = project_path / "main.bbl"
        if bbl_file.exists():
            result.add_pass("参考文献编译成功")
        else:
            result.add_warning("参考文献文件不存在，可能未运行 bibtex")

        return result

    def _parse_log_file(self, log_file: Path) -> tuple[List[str], List[str]]:
        """
        解析 LaTeX 编译日志

        Returns:
            (错误列表, 警告列表)
        """
        errors = []
        warnings = []

        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()

            # 常见错误模式
            error_patterns = [
                r"^! (.*)",  # LaTeX 错误
                r"^l\.\d+ (.*)",  # 错误位置
                r"Emergency stop",  # 紧急停止
                r"Missing character: .*",  # 缺少字符
            ]

            # 常见警告模式
            warning_patterns = [
                r"^LaTeX Warning: (.*)",
                r"^Package .* Warning: (.*)",
                r"Overfull \\hbox.*",  # 行溢出
                r"Underfull \\hbox.*",  # 行未满
                r"Float too large for page",  # 浮动体过大
            ]

            # 提取错误
            for pattern in error_patterns:
                matches = re.finditer(pattern, log_content, re.MULTILINE)
                for match in matches:
                    error_msg = match.group(1).strip()
                    if error_msg and error_msg not in errors:
                        errors.append(error_msg)

            # 提取警告
            for pattern in warning_patterns:
                matches = re.finditer(pattern, log_content, re.MULTILINE)
                for match in matches:
                    warning_msg = match.group(1).strip()
                    # 过滤常见无害警告
                    if self._is_harmless_warning(warning_msg):
                        continue
                    if warning_msg and warning_msg not in warnings:
                        warnings.append(warning_msg)

        except Exception as e:
            warnings.append(f"无法解析日志文件: {e}")

        return errors, warnings

    def _is_harmless_warning(self, warning: str) -> bool:
        """判断是否为无害警告"""
        harmless_patterns = [
            "There were undefined references",
            "Label(s) may have changed",
            "Rerun to get cross-references right",
        ]
        return any(pattern in warning for pattern in harmless_patterns)

    def compile_latex(self, project_path: Path) -> bool:
        """
        执行 LaTeX 编译（可选功能）

        Args:
            project_path: 项目路径

        Returns:
            是否编译成功
        """
        main_tex = project_path / "main.tex"
        if not main_tex.exists():
            return False

        try:
            # 执行 xelatex 编译
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "main.tex"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
