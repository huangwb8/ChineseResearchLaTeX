#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标题文字对比工具
对比 Word 模板和 LaTeX 文件的标题文字差异

使用方法:
    # 对比两个文件
    python scripts/compare_headings.py word.docx main.tex

    # 输出为 HTML 报告
    python scripts/compare_headings.py word.docx main.tex --report output.html

    # 输出为 Markdown 报告
    python scripts/compare_headings.py word.docx main.tex --report output.md
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


def extract_from_latex(tex_file: Path) -> Dict[str, str]:
    """从 LaTeX 文件中提取标题文字"""
    headings = {}

    with open(tex_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 \section{} 标题
    section_pattern = r'\\section\{([^}]+)\}'
    sections = re.findall(section_pattern, content)

    for i, section in enumerate(sections, start=1):
        section_clean = clean_latex_text(section)
        headings[f'section_{i}'] = section_clean

    # 提取 \subsection{} 标题
    subsection_pattern = r'\\subsection\{([^}]+)\}'
    subsections = re.findall(subsection_pattern, content)

    section_num = 1
    subsection_num = 1

    for subsection in subsections:
        subsection_clean = clean_latex_text(subsection)

        if subsection_num > 5:
            section_num += 1
            subsection_num = 1

        headings[f'subsection_{section_num}_{subsection_num}'] = subsection_clean
        subsection_num += 1

    return headings


def clean_latex_text(text: str) -> str:
    """清理 LaTeX 文本中的格式标记"""
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\{|\}', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def extract_from_word(doc_file: Path) -> Dict[str, str]:
    """从 Word 文档中提取标题文字"""
    try:
        from docx import Document
    except ImportError:
        print("错误: 需要安装 python-docx 库")
        print("安装命令: pip install python-docx")
        sys.exit(1)

    if not doc_file.suffix == '.docx':
        print(f"警告: {doc_file} 是 .doc 格式，建议转换为 .docx")
        sys.exit(1)

    doc = Document(doc_file)
    headings = {}

    section_num = 1
    subsection_num = 1
    section_count = 1

    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name

        if 'Heading 1' in style_name or '标题 1' in style_name:
            section_count += 1
            subsection_num = 1
            if section_count <= 3:
                headings[f'section_{section_count}'] = paragraph.text.strip()

        elif 'Heading 2' in style_name or '标题 2' in style_name:
            if subsection_num <= 5:
                headings[f'subsection_{section_count}_{subsection_num}'] = paragraph.text.strip()
                subsection_num += 1

    return headings


def compare_headings(word_headings: Dict[str, str], latex_headings: Dict[str, str]) -> Tuple[List, List, List]:
    """
    对比两个标题字典

    Returns:
        (完全匹配的列表, 有差异的列表, 仅在一方存在的列表)
    """
    all_keys = set(word_headings.keys()) | set(latex_headings.keys())

    matched = []
    differences = []
    only_in_one = []

    for key in sorted(all_keys):
        word_value = word_headings.get(key, '')
        latex_value = latex_headings.get(key, '')

        if word_value == latex_value:
            if word_value:  # 两者都有且相同
                matched.append((key, word_value))
        else:
            if word_value and latex_value:  # 两者都有但不同
                differences.append((key, word_value, latex_value))
            elif word_value:  # 仅在 Word 中
                only_in_one.append(('word', key, word_value))
            elif latex_value:  # 仅在 LaTeX 中
                only_in_one.append(('latex', key, latex_value))

    return matched, differences, only_in_one


def generate_text_report(matched: List, differences: List, only_in_one: List) -> str:
    """生成文本格式报告"""
    lines = []
    lines.append('=' * 60)
    lines.append('  标题文字对比报告')
    lines.append('=' * 60)
    lines.append('')

    # 统计
    total = len(matched) + len(differences)
    match_count = len(matched)
    diff_count = len(differences)
    only_count = len(only_in_one)

    lines.append(f'总标题数: {total}')
    lines.append(f'✅ 完全匹配: {match_count}')
    lines.append(f'⚠️  有差异: {diff_count}')
    lines.append(f'❌ 仅在一方: {only_count}')
    lines.append('')

    # 完全匹配的标题
    if matched:
        lines.append('# 完全匹配的标题')
        lines.append('')
        for key, value in matched:
            lines.append(f'✅ {key}: {value}')
        lines.append('')

    # 有差异的标题
    if differences:
        lines.append('# 有差异的标题')
        lines.append('')
        for key, word_value, latex_value in differences:
            lines.append(f'⚠️  {key}:')
            lines.append(f'   Word:  {word_value}')
            lines.append(f'   LaTeX: {latex_value}')
            lines.append('')

    # 仅在一方的标题
    if only_in_one:
        lines.append('# 仅在一方的标题')
        lines.append('')
        for source, key, value in only_in_one:
            source_label = 'Word' if source == 'word' else 'LaTeX'
            lines.append(f'❌ 仅在 {source_label}: {key}')
            lines.append(f'   {value}')
            lines.append('')

    return '\n'.join(lines)


def generate_html_report(matched: List, differences: List, only_in_one: List,
                        word_file: Path, latex_file: Path) -> str:
    """生成 HTML 格式报告"""
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>标题文字对比报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
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
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #666;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .matched .value {{ color: #10b981; }}
        .differences .value {{ color: #f59e0b; }}
        .only .value {{ color: #ef4444; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-top: 0;
            padding-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .item {{
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #ddd;
            background: #f9fafb;
            border-radius: 4px;
        }}
        .item.matched {{
            border-left-color: #10b981;
            background: #f0fdf4;
        }}
        .item.difference {{
            border-left-color: #f59e0b;
            background: #fffbeb;
        }}
        .item.only {{
            border-left-color: #ef4444;
            background: #fef2f2;
        }}
        .key {{
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 5px;
        }}
        .value {{
            color: #4b5563;
        }}
        .diff-pair {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 10px;
        }}
        .diff-box {{
            padding: 10px;
            background: white;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
        }}
        .diff-box.word {{
            border-left: 3px solid #3b82f6;
        }}
        .diff-box.latex {{
            border-left: 3px solid #8b5cf6;
        }}
        .label {{
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 5px;
        }}
        .meta {{
            color: #9ca3af;
            font-size: 14px;
            margin-top: 30px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 标题文字对比报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="stats">
        <div class="stat-card matched">
            <h3>✅ 完全匹配</h3>
            <div class="value">{len(matched)}</div>
        </div>
        <div class="stat-card differences">
            <h3>⚠️ 有差异</h3>
            <div class="value">{len(differences)}</div>
        </div>
        <div class="stat-card only">
            <h3>❌ 仅在一方</h3>
            <div class="value">{len(only_in_one)}</div>
        </div>
    </div>
'''

    # 完全匹配的标题
    if matched:
        html += '<div class="section"><h2>✅ 完全匹配的标题</h2>'
        for key, value in matched:
            html += f'''
    <div class="item matched">
        <div class="key">{key}</div>
        <div class="value">{value}</div>
    </div>'''
        html += '</div>'

    # 有差异的标题
    if differences:
        html += '<div class="section"><h2>⚠️ 有差异的标题</h2>'
        for key, word_value, latex_value in differences:
            html += f'''
    <div class="item difference">
        <div class="key">{key}</div>
        <div class="diff-pair">
            <div class="diff-box word">
                <div class="label">Word 模板</div>
                <div class="value">{word_value}</div>
            </div>
            <div class="diff-box latex">
                <div class="label">LaTeX 文件</div>
                <div class="value">{latex_value}</div>
            </div>
        </div>
    </div>'''
        html += '</div>'

    # 仅在一方的标题
    if only_in_one:
        html += '<div class="section"><h2>❌ 仅在一方的标题</h2>'
        for source, key, value in only_in_one:
            source_label = 'Word 模板' if source == 'word' else 'LaTeX 文件'
            html += f'''
    <div class="item only">
        <div class="key">仅在 {source_label}: {key}</div>
        <div class="value">{value}</div>
    </div>'''
        html += '</div>'

    html += f'''
    <div class="meta">
        <p>Word 文件: {word_file.name}</p>
        <p>LaTeX 文件: {latex_file.name}</p>
    </div>
</body>
</html>'''

    return html


def main():
    parser = argparse.ArgumentParser(description='对比 Word 和 LaTeX 的标题文字')
    parser.add_argument('word_file', type=Path, help='Word 文档路径')
    parser.add_argument('latex_file', type=Path, help='LaTeX 文件路径')
    parser.add_argument('--report', type=Path, help='输出报告文件路径')
    parser.add_argument('--format', choices=['auto', 'text', 'html'], default='auto',
                       help='报告格式（auto 根据扩展名自动判断）')

    args = parser.parse_args()

    # 提取标题
    print(f'📖 正在提取 Word 标题: {args.word_file}')
    word_headings = extract_from_word(args.word_file)

    print(f'📖 正在提取 LaTeX 标题: {args.latex_file}')
    latex_headings = extract_from_latex(args.latex_file)

    # 对比标题
    print('🔍 正在对比标题...')
    matched, differences, only_in_one = compare_headings(word_headings, latex_headings)

    # 生成报告
    if args.report:
        # 判断格式
        if args.format == 'auto':
            if args.report.suffix == '.html':
                fmt = 'html'
            elif args.report.suffix == '.md':
                fmt = 'markdown'
            else:
                fmt = 'text'
        else:
            fmt = args.format

        if fmt == 'html':
            report = generate_html_report(matched, differences, only_in_one,
                                        args.word_file, args.latex_file)
        else:
            report = generate_text_report(matched, differences, only_in_one)

        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f'✅ 报告已生成: {args.report}')
        print(f'   总计: {len(matched) + len(differences)} | 匹配: {len(matched)} | 差异: {len(differences)} | 仅在一方: {len(only_in_one)}')

    else:
        # 打印到控制台
        report = generate_text_report(matched, differences, only_in_one)
        print(report)


if __name__ == '__main__':
    main()
