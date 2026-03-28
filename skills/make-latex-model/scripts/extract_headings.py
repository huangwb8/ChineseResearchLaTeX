#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标题文字提取工具（通用化版本）
从 Word 模板或 LaTeX 文件中提取标题文字结构

使用方法:
    # 从 Word 文档提取
    python scripts/extract_headings.py word --file template.docx

    # 从 LaTeX 文件提取
    python scripts/extract_headings.py latex --file main.tex

    # 从 LaTeX 文件提取（指定额外配置）
    python scripts/extract_headings.py latex --file main.tex --config custom_extract.yaml

    # 输出为 JSON
    python scripts/extract_headings.py latex --file main.tex --format json

    # 指定项目路径（自动识别结构默认值）
    python scripts/extract_headings.py latex --file main.tex --project projects/NSFC_Young
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 添加 skill 根目录到路径（以导入 scripts.core）
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SKILL_DIR))

try:
    from scripts.core.config_loader import ConfigLoader
    from scripts.core.latex_format_parser import LatexFormatParser
except ImportError:
    ConfigLoader = None
    LatexFormatParser = None


def _extract_heading_argument(line: str, command: str) -> Optional[str]:
    """从单行中提取位于行首的标题命令参数，支持嵌套花括号。"""
    match = re.match(rf'^\s*\{{?\s*\\{command}\*?\s*', line)
    if not match:
        return None

    brace_index = match.end()
    while brace_index < len(line) and line[brace_index].isspace():
        brace_index += 1

    if brace_index >= len(line) or line[brace_index] != "{":
        return None

    if LatexFormatParser:
        extracted, end_index = LatexFormatParser._extract_braced_arg(line, brace_index)
        if end_index > brace_index:
            return extracted
        return None

    depth = 1
    cursor = brace_index + 1
    start = cursor
    while cursor < len(line) and depth > 0:
        char = line[cursor]
        if char == "\\" and cursor + 1 < len(line):
            cursor += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        cursor += 1

    if depth != 0:
        return None
    return line[start:cursor - 1]


def _unwrap_texorpdfstring(text: str) -> str:
    """将 \\texorpdfstring{A}{B} 还原为正文可见部分 A。"""
    token = r"\texorpdfstring"
    cursor = 0

    while True:
        start = text.find(token, cursor)
        if start == -1:
            return text

        first_open = start + len(token)
        while first_open < len(text) and text[first_open].isspace():
            first_open += 1

        if first_open >= len(text) or text[first_open] != "{":
            cursor = start + len(token)
            continue

        if LatexFormatParser:
            first_arg, first_end = LatexFormatParser._extract_braced_arg(text, first_open)
        else:
            first_arg, first_end = "", first_open
        if first_end <= first_open:
            cursor = start + len(token)
            continue

        second_open = first_end
        while second_open < len(text) and text[second_open].isspace():
            second_open += 1

        if second_open < len(text) and text[second_open] == "{":
            if LatexFormatParser:
                _, second_end = LatexFormatParser._extract_braced_arg(text, second_open)
            else:
                second_end = second_open
        else:
            second_end = second_open

        text = text[:start] + first_arg + text[second_end:]
        cursor = start + len(first_arg)


def extract_from_latex(tex_file: Path, config: Optional[Dict] = None) -> Dict[str, str]:
    """
    从 LaTeX 文件中提取标题文字

    Args:
        tex_file: LaTeX 文件路径
        config: 模板配置（可选，用于自定义标题提取规则）

    Returns:
        标题字典，如 {"section_1": "（一）立项依据与研究内容", "subsection_1_1": "1. 项目的立项依据"}
    """
    headings: Dict[str, str] = {}

    with open(tex_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    section_num = 0
    subsection_num = 0

    for line in lines:
        section_text = _extract_heading_argument(line, "section")
        if section_text is not None:
            section_num += 1
            subsection_num = 0
            section_clean = clean_latex_text(section_text)
            headings[f'section_{section_num}'] = section_clean
            continue

        subsection_text = _extract_heading_argument(line, "subsection")
        if subsection_text is not None:
            if section_num == 0:
                section_num = 1
            subsection_num += 1
            subsection_clean = clean_latex_text(subsection_text)
            headings[f'subsection_{section_num}_{subsection_num}'] = subsection_clean

    return headings


def clean_latex_text(text: str) -> str:
    """
    清理 LaTeX 文本中的格式标记

    Args:
        text: 原始 LaTeX 文本

    Returns:
        清理后的纯文本
    """
    text = _unwrap_texorpdfstring(text)
    text = re.sub(r'\\punctstyle\{[^}]*\}', '', text)

    # 移除常见的 LaTeX 格式标记
    if LatexFormatParser:
        text = LatexFormatParser.clean_latex_text(text)
    else:
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # 移除命令
        text = re.sub(r'\{|\}', '', text)  # 移除花括号

    text = re.sub(r'\s+', ' ', text)  # 合并空白字符
    text = text.strip()

    return text


def extract_from_word(doc_file: Path) -> Dict[str, str]:
    """
    从 Word 文档中提取标题文字

    Args:
        doc_file: Word 文档路径（.doc 或 .docx）

    Returns:
        标题字典
    """
    try:
        from docx import Document
    except ImportError:
        print("错误: 需要安装 python-docx 库")
        print("安装命令: pip install python-docx")
        sys.exit(1)

    if not doc_file.suffix == '.docx':
        # 如果是 .doc 格式，提示用户转换
        print(f"警告: {doc_file} 是 .doc 格式")
        print("建议使用 LibreOffice 转换为 .docx:")
        print(f"  soffice --headless --convert-to docx {doc_file}")
        sys.exit(1)

    doc = Document(doc_file)
    headings = {}

    section_num = 1
    subsection_num = 1
    section_count = 0

    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name

        # Word 中的标题样式
        if 'Heading 1' in style_name or '标题 1' in style_name:
            section_count += 1
            subsection_num = 1
            if section_count <= 3:  # NSFC 模板有 3 个主要 section
                headings[f'section_{section_count}'] = paragraph.text.strip()

        elif 'Heading 2' in style_name or '标题 2' in style_name:
            if subsection_num <= 5:  # 每个 section 最多 5 个 subsection
                headings[f'subsection_{section_count}_{subsection_num}'] = paragraph.text.strip()
                subsection_num += 1

    return headings


def main():
    parser = argparse.ArgumentParser(
        description='从 Word 或 LaTeX 文件中提取标题文字',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 Word 文档提取
  %(prog)s word --file template.docx

  # 从 LaTeX 文件提取
  %(prog)s latex --file main.tex

  # 指定额外配置
  %(prog)s latex --file main.tex --config custom_extract.yaml

  # 指定项目（自动识别结构默认值）
  %(prog)s latex --file main.tex --project projects/NSFC_Young
        """
    )

    parser.add_argument('mode', choices=['word', 'latex'], help='提取模式')
    parser.add_argument('--file', type=Path, required=True, help='文件路径')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
    parser.add_argument('--output', type=Path, help='输出文件路径（可选）')

    # 新增参数
    parser.add_argument('--config', type=Path, help='额外 YAML 配置文件路径（可用于自定义提取正则）')
    parser.add_argument('--project', type=Path, help='项目路径（用于自动识别模板类型）')

    args = parser.parse_args()

    # 加载配置
    config = None
    if args.mode == 'latex':
        if ConfigLoader:
            if args.project:
                # 从项目路径加载配置
                skill_dir = SCRIPT_DIR.parent
                loader = ConfigLoader(skill_dir, args.project)
                config = loader.load()
            elif args.config:
                # 直接加载配置文件
                import yaml
                with open(args.config, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

    # 提取标题
    if args.mode == 'latex':
        headings = extract_from_latex(args.file, config)
    else:
        headings = extract_from_word(args.file)

    # 输出结果
    if args.format == 'json':
        output = json.dumps(headings, ensure_ascii=False, indent=2)
    else:
        # 文本格式输出
        lines = []
        lines.append('# 标题文字提取结果')
        lines.append(f'# 源文件: {args.file}')

        if config:
            template_name = config.get('template', {}).get('name', 'Unknown')
            lines.append(f'# 模板: {template_name}')

        lines.append('')

        # 按 section 分组输出
        for key in sorted(headings.keys()):
            value = headings[key]
            lines.append(f'{key}: {value}')

        output = '\n'.join(lines)

    # 打印或保存
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f'✅ 标题已提取到: {args.output}')
    else:
        print(output)


if __name__ == '__main__':
    main()
