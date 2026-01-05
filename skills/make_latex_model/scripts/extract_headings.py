#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标题文字提取工具
从 Word 模板或 LaTeX 文件中提取标题文字结构

使用方法:
    # 从 Word 文档提取
    python scripts/extract_headings.py word --file template.docx

    # 从 LaTeX 文件提取
    python scripts/extract_headings.py latex --file main.tex

    # 输出为 JSON
    python scripts/extract_headings.py latex --file main.tex --format json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


def extract_from_latex(tex_file: Path) -> Dict[str, str]:
    """
    从 LaTeX 文件中提取标题文字

    Args:
        tex_file: LaTeX 文件路径

    Returns:
        标题字典，如 {"section_1": "（一）立项依据与研究内容", "subsection_1_1": "1. 项目的立项依据"}
    """
    headings = {}

    with open(tex_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 \section{} 标题
    section_pattern = r'\\section\{([^}]+)\}'
    sections = re.findall(section_pattern, content)

    for i, section in enumerate(sections, start=1):
        # 清理格式标记
        section_clean = clean_latex_text(section)
        headings[f'section_{i}'] = section_clean

    # 提取 \subsection{} 标题
    subsection_pattern = r'\\subsection\{([^}]+)\}'
    subsections = re.findall(subsection_pattern, content)

    section_num = 1
    subsection_num = 1

    for subsection in subsections:
        subsection_clean = clean_latex_text(subsection)

        # 判断属于哪个 section（根据 LaTeX 文件顺序）
        # 简化处理：假设 subsection 按顺序排列
        if subsection_num > 5:  # 假设每个 section 最多 5 个 subsection
            section_num += 1
            subsection_num = 1

        headings[f'subsection_{section_num}_{subsection_num}'] = subsection_clean
        subsection_num += 1

    return headings


def clean_latex_text(text: str) -> str:
    """
    清理 LaTeX 文本中的格式标记

    Args:
        text: 原始 LaTeX 文本

    Returns:
        清理后的纯文本
    """
    # 移除常见的 LaTeX 格式标记
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
    section_count = 1

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
    parser = argparse.ArgumentParser(description='从 Word 或 LaTeX 文件中提取标题文字')
    parser.add_argument('mode', choices=['word', 'latex'], help='提取模式')
    parser.add_argument('--file', type=Path, required=True, help='文件路径')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
    parser.add_argument('--output', type=Path, help='输出文件路径（可选）')

    args = parser.parse_args()

    # 提取标题
    if args.mode == 'latex':
        headings = extract_from_latex(args.file)
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
