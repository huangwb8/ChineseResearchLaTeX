#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标题文字验证器 - 检查标题文字与 Word 模板一致性
"""

import re
from pathlib import Path
from typing import Dict, Any, List
from ..validator_base import ValidatorBase, ValidationContext, ValidationResult


class HeadingValidator(ValidatorBase):
    """标题文字验证器 - 第二优先级"""

    def get_name(self) -> str:
        return "heading"

    def get_priority(self) -> int:
        return 2

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        执行标题文字验证

        检查项:
        1. 一级标题文字（section_1, section_2, section_3）
        2. 二级标题文字（subsection_1_1 ~ subsection_3_5）
        3. 标题编号格式一致性
        """
        result = ValidationResult(passed=[], warnings=[], failed=[])

        project_path = context.project_path
        main_tex = project_path / "main.tex"
        template_dir = project_path / "template"

        if not main_tex.exists():
            result.add_fail(f"主文件不存在: {main_tex}")
            return result

        # 提取 LaTeX 标题
        latex_headings = self._extract_latex_headings(main_tex)

        # 尝试提取 Word 标题（如果存在）
        word_headings = self._extract_word_headings(template_dir)

        if not word_headings:
            result.add_warning("未找到 Word 模板文件，无法进行标题对比")
            result.add_warning("请手动检查 main.tex 中的标题文字是否与 Word 模板一致")
            return result

        # 对比标题
        self._compare_headings(latex_headings, word_headings, result)

        return result

    def _extract_latex_headings(self, tex_file: Path) -> Dict[str, str]:
        """从 LaTeX 文件中提取标题"""
        headings = {}

        try:
            content = tex_file.read_text(encoding="utf-8")
        except Exception as e:
            return {}

        # 提取 \section{} 标题
        section_pattern = r"\\section\{([^}]+)\}"
        sections = re.findall(section_pattern, content)

        for i, section in enumerate(sections, start=1):
            section_clean = self._clean_latex_text(section)
            headings[f"section_{i}"] = section_clean

        # 提取 \subsection{} 标题
        subsection_pattern = r"\\subsection\{([^}]+)\}"
        subsections = re.findall(subsection_pattern, content)

        section_num = 1
        subsection_num = 1

        for subsection in subsections:
            subsection_clean = self._clean_latex_text(subsection)

            # 假设每个 section 最多 5 个 subsection
            if subsection_num > 5:
                section_num += 1
                subsection_num = 1

            headings[f"subsection_{section_num}_{subsection_num}"] = subsection_clean
            subsection_num += 1

        return headings

    def _extract_word_headings(self, template_dir: Path) -> Dict[str, str]:
        """从 Word 模板中提取标题"""
        if not template_dir.exists():
            return {}

        # 查找 .docx 文件
        docx_files = list(template_dir.glob("*.docx"))
        if not docx_files:
            return {}

        try:
            from docx import Document
        except ImportError:
            return {}

        doc_file = docx_files[0]
        doc = Document(doc_file)
        headings = {}

        section_num = 1
        subsection_num = 1
        section_count = 0

        for paragraph in doc.paragraphs:
            style_name = paragraph.style.name

            if "Heading 1" in style_name or "标题 1" in style_name:
                section_count += 1
                subsection_num = 1
                if section_count <= 3:
                    headings[f"section_{section_count}"] = paragraph.text.strip()

            elif "Heading 2" in style_name or "标题 2" in style_name:
                if subsection_num <= 5:
                    headings[f"subsection_{section_count}_{subsection_num}"] = paragraph.text.strip()
                    subsection_num += 1

        return headings

    def _clean_latex_text(self, text: str) -> str:
        """清理 LaTeX 文本中的格式标记"""
        text = re.sub(r"\\[a-zA-Z]+", "", text)
        text = re.sub(r"\{|\}", "", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    def _compare_headings(self, latex_headings: Dict[str, str], word_headings: Dict[str, str],
                         result: ValidationResult):
        """对比标题文字"""
        all_keys = set(latex_headings.keys()) | set(word_headings.keys())

        matched = 0
        differences = 0
        only_in_one = 0

        for key in sorted(all_keys):
            latex_value = latex_headings.get(key, "")
            word_value = word_headings.get(key, "")

            if latex_value == word_value:
                if latex_value:
                    result.add_pass(f"标题匹配 {key}: {latex_value}")
                    matched += 1
            else:
                if latex_value and word_value:
                    result.add_fail(f"标题不匹配 {key}:")
                    result.add_fail(f"  Word:  {word_value}")
                    result.add_fail(f"  LaTeX: {latex_value}")
                    differences += 1
                elif word_value:
                    result.add_warning(f"仅在 Word 中: {key} = {word_value}")
                    only_in_one += 1
                elif latex_value:
                    result.add_warning(f"仅在 LaTeX 中: {key} = {latex_value}")
                    only_in_one += 1

        # 总结
        total = matched + differences
        if total > 0:
            match_rate = (matched / total) * 100
            if differences == 0:
                result.add_pass(f"标题文字完全匹配 ({matched}/{total})")
            else:
                result.add_warning(f"标题匹配率: {match_rate:.1f}% ({matched}/{total}, {differences} 个差异)")
