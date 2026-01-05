#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板基类 - LaTeX 模板抽象基类
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class StyleRules:
    """样式规则"""
    fonts: Dict[str, Any]
    colors: Dict[str, Any]
    page: Dict[str, Any]
    headings: Dict[str, Any]
    lists: Dict[str, Any]
    font_sizes: Dict[str, Any]


@dataclass
class HeadingInfo:
    """标题信息"""
    id: str
    level: int
    latex_command: str
    text: str
    line_number: int
    max_children: int = 0


@dataclass
class ValidationResult:
    """验证结果"""
    passed: List[str]
    warnings: List[str]
    failed: List[str]

    def __post_init__(self):
        if self.passed is None:
            self.passed = []
        if self.warnings is None:
            self.warnings = []
        if self.failed is None:
            self.failed = []

    def is_success(self) -> bool:
        """是否验证成功"""
        return len(self.failed) == 0

    def add_pass(self, message: str):
        """添加通过项"""
        self.passed.append(message)

    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)

    def add_fail(self, message: str):
        """添加失败项"""
        self.failed.append(message)

    def summary(self) -> str:
        """生成摘要"""
        lines = [
            f"✅ Passed: {len(self.passed)}",
            f"⚠️  Warnings: {len(self.warnings)}",
            f"❌ Failed: {len(self.failed)}",
        ]
        return "\n".join(lines)


class TemplateBase(ABC):
    """LaTeX 模板基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化模板

        Args:
            config: 模板配置字典
        """
        self.config = config
        self.template_info = config.get("template", {})
        self.style_reference = config.get("style_reference", {})
        self.structure = config.get("structure", {})
        self.heading_structure = config.get("heading_structure", {})
        self.validation = config.get("validation", {})

    def get_name(self) -> str:
        """获取模板名称"""
        return self.template_info.get("name", "Unknown")

    def get_display_name(self) -> str:
        """获取模板显示名称"""
        return self.template_info.get("display_name", self.get_name())

    def get_version(self) -> str:
        """获取模板版本"""
        return self.template_info.get("version", "1.0")

    def get_style_rules(self) -> StyleRules:
        """获取样式规则"""
        return StyleRules(
            fonts=self.style_reference.get("fonts", {}),
            colors=self.style_reference.get("colors", {}),
            page=self.style_reference.get("page", {}),
            headings=self.style_reference.get("headings", {}),
            lists=self.style_reference.get("lists", {}),
            font_sizes=self.style_reference.get("font_sizes", {})
        )

    def get_content_dir(self) -> str:
        """获取内容文件目录"""
        return self.structure.get("content_dir", "extraTex")

    def get_config_file(self) -> str:
        """获取样式配置文件"""
        return self.structure.get("config_file", "@config.tex")

    def get_main_file(self) -> str:
        """获取主文件"""
        return self.structure.get("main_file", "main.tex")

    @abstractmethod
    def extract_headings(self, source_file: Path) -> Dict[str, List[HeadingInfo]]:
        """
        提取标题结构

        Args:
            source_file: LaTeX 源文件路径

        Returns:
            标题信息字典 {level: [HeadingInfo]}
        """
        raise NotImplementedError

    def validate_structure(self, project_path: Path) -> ValidationResult:
        """
        验证项目结构是否符合模板要求

        Args:
            project_path: 项目路径

        Returns:
            验证结果
        """
        result = ValidationResult(passed=[], warnings=[], failed=[])

        # 检查主文件
        main_file = project_path / self.get_main_file()
        if main_file.exists():
            result.add_pass(f"Main file exists: {main_file}")
        else:
            result.add_fail(f"Main file missing: {main_file}")

        # 检查内容目录
        content_dir = project_path / self.get_content_dir()
        if content_dir.exists() and content_dir.is_dir():
            result.add_pass(f"Content directory exists: {content_dir}")
        else:
            result.add_warning(f"Content directory missing: {content_dir}")

        # 检查样式配置文件
        config_file = content_dir / self.get_config_file()
        if config_file.exists():
            result.add_pass(f"Style config exists: {config_file}")
        else:
            result.add_fail(f"Style config missing: {config_file}")

        return result

    def extract_headings_from_latex(self, source_file: Path) -> Dict[str, List[HeadingInfo]]:
        """
        从 LaTeX 文件中提取标题（默认实现）

        Args:
            source_file: LaTeX 源文件路径

        Returns:
            标题信息字典
        """
        if not source_file.exists():
            return {}

        headings = {"section": [], "subsection": [], "subsubsection": [], "paragraph": []}

        with open(source_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 支持的标题命令
        heading_patterns = {
            "section": r"\\section\*?\{([^}]+)\}",
            "subsection": r"\\subsection\*?\{([^}]+)\}",
            "subsubsection": r"\\subsubsection\*?\{([^}]+)\}",
            "paragraph": r"\\paragraph\*?\{([^}]+)\}",
        }

        for line_num, line in enumerate(lines, 1):
            for level, pattern in heading_patterns.items():
                match = re.search(pattern, line)
                if match:
                    text = match.group(1).strip()
                    headings[level].append(HeadingInfo(
                        id=f"{level}_{len(headings[level]) + 1}",
                        level=list(heading_patterns.keys()).index(level) + 1,
                        latex_command=level,
                        text=text,
                        line_number=line_num
                    ))

        return headings


class NSFCTemplate(TemplateBase):
    """NSFC 模板类"""

    def extract_headings(self, source_file: Path) -> Dict[str, List[HeadingInfo]]:
        """
        提取 NSFC 标题结构

        Args:
            source_file: LaTeX 源文件路径

        Returns:
            标题信息字典
        """
        return self.extract_headings_from_latex(source_file)

    def validate_heading_texts(self, source_file: Path) -> ValidationResult:
        """
        验证标题文字是否与模板一致

        Args:
            source_file: LaTeX 源文件路径

        Returns:
            验证结果
        """
        result = ValidationResult(passed=[], warnings=[], failed=[])

        heading_texts = self.style_reference.get("heading_texts", {})
        if not heading_texts:
            result.add_warning("No heading texts defined in template config")
            return result

        headings = self.extract_headings(source_file)

        # 验证一级标题
        section_headings = headings.get("section", [])
        expected_sections = [
            heading_texts.get("section_1", ""),
            heading_texts.get("section_2", ""),
            heading_texts.get("section_3", ""),
        ]

        for i, (actual, expected) in enumerate(zip(section_headings, expected_sections)):
            if expected and actual.text == expected:
                result.add_pass(f"Section {i+1} text matches: {actual.text}")
            elif expected:
                result.add_fail(f"Section {i+1} text mismatch: expected '{expected}', got '{actual.text}'")

        return result


if __name__ == "__main__":
    # 测试代码
    import sys

    # 测试 TemplateBase
    config = {
        "template": {
            "name": "NSFC_Young",
            "display_name": "国家自然科学基金-青年科学基金项目",
            "version": "2026"
        },
        "structure": {
            "content_dir": "extraTex",
            "config_file": "@config.tex",
            "main_file": "main.tex"
        }
    }

    template = NSFCTemplate(config)
    print(f"Template: {template.get_display_name()} v{template.get_version()}")
    print(f"Content dir: {template.get_content_dir()}")
