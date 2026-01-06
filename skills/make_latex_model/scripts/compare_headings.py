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


def extract_from_latex(tex_file: Path, check_format: bool = False) -> Dict[str, any]:
    """
    从 LaTeX 文件中提取标题文字

    Args:
        tex_file: LaTeX 文件路径
        check_format: 是否检查格式（加粗）

    Returns:
        如果 check_format=False: Dict[str, str] - 标题文本
        如果 check_format=True: Dict[str, Dict] - 包含文本和格式信息
    """
    headings = {}

    with open(tex_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 \section{} 标题（包含原始 LaTeX 代码）
    section_pattern = r'\\section\{([^}]+)\}'
    sections = re.findall(section_pattern, content)

    for i, section in enumerate(sections, start=1):
        key = f'section_{i}'
        if check_format:
            headings[key] = {
                "text": clean_latex_text(section),
                "fragments": extract_formatted_text_from_latex(section)
            }
        else:
            headings[key] = clean_latex_text(section)

    # 提取 \subsection{} 标题
    subsection_pattern = r'\\subsection\{([^}]+)\}'
    subsections = re.findall(subsection_pattern, content)

    section_num = 1
    subsection_num = 1

    for subsection in subsections:
        if subsection_num > 5:
            section_num += 1
            subsection_num = 1

        key = f'subsection_{section_num}_{subsection_num}'
        if check_format:
            headings[key] = {
                "text": clean_latex_text(subsection),
                "fragments": extract_formatted_text_from_latex(subsection)
            }
        else:
            headings[key] = clean_latex_text(subsection)
        subsection_num += 1

    return headings


def clean_latex_text(text: str) -> str:
    """清理 LaTeX 文本中的格式标记"""
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\{|\}', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def clean_latex_commands(text: str) -> str:
    """清理 LaTeX 命令，但保留 \textbf 和 \bfseries"""
    # 删除除 \textbf、\bfseries 外的所有命令
    text = re.sub(r'\\(?!textbf|bfseries)[a-zA-Z]+', '', text)
    text = re.sub(r'\{|\}', '', text)
    text = text.strip()
    return text


def extract_formatted_text_from_word(paragraph) -> List[Dict[str, any]]:
    """
    从 Word 段落中提取带格式信息的文本片段

    Args:
        paragraph: python-docx 的段落对象

    Returns:
        [
            {"text": "立项依据", "bold": True},
            {"text": "与研究内容", "bold": False}
        ]
    """
    fragments = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        fragments.append({
            "text": text,
            "bold": run.bold if run.bold is not None else False
        })
    return fragments


def extract_formatted_text_from_latex(latex_text: str) -> List[Dict[str, any]]:
    """
    从 LaTeX 文本中提取带格式信息的片段

    支持的格式：
    - \textbf{文本}     （推荐）
    - {\bfseries 文本}  （传统方式）

    Args:
        latex_text: LaTeX 标题文本

    Returns:
        [
            {"text": "立项依据", "bold": True},
            {"text": "与研究内容", "bold": False}
        ]
    """
    fragments = []

    # 模式 1: \textbf{...}
    textbf_pattern = r'\\textbf\{([^}]+)\}'

    # 先提取所有 \textbf{} 片段的位置
    bold_segments = []
    for match in re.finditer(textbf_pattern, latex_text):
        start = match.start()
        end = match.end()
        inner_text = match.group(1)
        bold_segments.append({
            "start": start,
            "end": end,
            "text": inner_text,
            "bold": True
        })

    # 按位置排序
    bold_segments.sort(key=lambda x: x["start"])

    # 构建完整片段列表
    last_end = 0
    for seg in bold_segments:
        # 添加加粗前的普通文本
        if seg["start"] > last_end:
            normal_text = latex_text[last_end:seg["start"]]
            normal_text = clean_latex_commands(normal_text)
            if normal_text:
                fragments.append({"text": normal_text, "bold": False})

        # 添加加粗文本
        fragments.append({"text": seg["text"], "bold": True})
        last_end = seg["end"]

    # 添加剩余的普通文本
    if last_end < len(latex_text):
        normal_text = latex_text[last_end:]
        normal_text = clean_latex_commands(normal_text)
        if normal_text:
            fragments.append({"text": normal_text, "bold": False})

    return fragments


def compare_formatted_text(word_fragments: List[Dict],
                          latex_fragments: List[Dict]) -> Dict[str, any]:
    """
    对比 Word 和 LaTeX 的格式化文本

    Args:
        word_fragments: Word 格式片段列表
        latex_fragments: LaTeX 格式片段列表

    Returns:
        {
            "match": true/false,
            "word_text": "立项依据与研究内容",
            "latex_text": "立项依据与研究内容",
            "differences": [
                {
                    "type": "bold_mismatch",
                    "word_fragment": {"text": "立项依据", "bold": True},
                    "latex_fragment": {"text": "立项依据", "bold": False},
                    "position": "0-4"
                }
            ]
        }
    """
    # 提取纯文本进行初步对比
    word_text = "".join(f["text"] for f in word_fragments)
    latex_text = "".join(f["text"] for f in latex_fragments)

    if word_text != latex_text:
        return {
            "match": False,
            "reason": "text_mismatch",
            "word_text": word_text,
            "latex_text": latex_text
        }

    # 对齐片段并对比格式
    differences = []
    word_pos = 0
    word_idx = 0
    latex_idx = 0

    # 创建可修改的片段副本
    word_frags = [f.copy() for f in word_fragments]
    latex_frags = [f.copy() for f in latex_fragments]

    while word_idx < len(word_frags) and latex_idx < len(latex_frags):
        word_frag = word_frags[word_idx]
        latex_frag = latex_frags[latex_idx]

        # 计算当前片段的文本长度
        word_len = len(word_frag["text"])
        latex_len = len(latex_frag["text"])

        # 找到最小长度
        min_len = min(word_len, latex_len)

        # 对比前 min_len 个字符的格式
        for i in range(min_len):
            if word_frag["bold"] != latex_frag["bold"]:
                char_pos = word_pos + i
                differences.append({
                    "type": "bold_mismatch",
                    "position": char_pos,
                    "char": word_frag["text"][i],
                    "word_bold": word_frag["bold"],
                    "latex_bold": latex_frag["bold"]
                })

        # 更新位置
        word_pos += min_len
        word_frag["text"] = word_frag["text"][min_len:]
        latex_frag["text"] = latex_frag["text"][min_len:]
        word_len -= min_len
        latex_len -= min_len

        # 如果 Word 片段用完了，移到下一个
        if word_len == 0:
            word_idx += 1
        # 如果 LaTeX 片段用完了，移到下一个
        if latex_len == 0:
            latex_idx += 1

    return {
        "match": len(differences) == 0,
        "word_text": word_text,
        "latex_text": latex_text,
        "differences": differences
    }


def extract_from_word(doc_file: Path, check_format: bool = False) -> Dict[str, any]:
    """
    从 Word 文档中提取标题文字

    Args:
        doc_file: Word 文档路径
        check_format: 是否检查格式（加粗）

    Returns:
        如果 check_format=False: Dict[str, str] - 标题文本
        如果 check_format=True: Dict[str, Dict] - 包含文本和格式信息
    """
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
                key = f'section_{section_count}'
                if check_format:
                    headings[key] = {
                        "text": paragraph.text.strip(),
                        "fragments": extract_formatted_text_from_word(paragraph)
                    }
                else:
                    headings[key] = paragraph.text.strip()

        elif 'Heading 2' in style_name or '标题 2' in style_name:
            if subsection_num <= 5:
                key = f'subsection_{section_count}_{subsection_num}'
                if check_format:
                    headings[key] = {
                        "text": paragraph.text.strip(),
                        "fragments": extract_formatted_text_from_word(paragraph)
                    }
                else:
                    headings[key] = paragraph.text.strip()
                subsection_num += 1

    return headings


def compare_headings(word_headings: Dict[str, str], latex_headings: Dict[str, str]) -> Tuple[List, List, List]:
    """
    对比两个标题字典（仅文本对比）

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


def compare_headings_with_format(word_headings: Dict[str, Dict],
                                 latex_headings: Dict[str, Dict]) -> Tuple[List, List, List, List]:
    """
    对比两个标题字典（包含格式对比）

    Returns:
        (完全匹配的列表, 文本差异列表, 格式差异列表, 仅在一方存在的列表)
    """
    all_keys = set(word_headings.keys()) | set(latex_headings.keys())

    matched = []
    text_diff = []
    format_diff = []
    only_in_one = []

    for key in sorted(all_keys):
        word_data = word_headings.get(key)
        latex_data = latex_headings.get(key)

        if not word_data and not latex_data:
            continue

        if not word_data:
            only_in_one.append(('latex', key, latex_data["text"]))
        elif not latex_data:
            only_in_one.append(('word', key, word_data["text"]))
        else:
            # 两者都存在，对比文本和格式
            word_text = word_data["text"]
            latex_text = latex_data["text"]

            if word_text != latex_text:
                # 文本不一致
                text_diff.append((key, word_text, latex_text))
            else:
                # 文本一致，对比格式
                format_result = compare_formatted_text(
                    word_data["fragments"],
                    latex_data["fragments"]
                )

                if format_result["match"]:
                    matched.append((key, word_text, format_result))
                else:
                    format_diff.append((key, word_text, format_result))

    return matched, text_diff, format_diff, only_in_one


def generate_text_report_with_format(matched: List, text_diff: List, format_diff: List, only_in_one: List) -> str:
    """生成文本格式报告（包含格式对比）"""
    lines = []
    lines.append('=' * 60)
    lines.append('  标题文字对比报告（包含格式）')
    lines.append('=' * 60)
    lines.append('')

    # 统计
    total = len(matched) + len(text_diff) + len(format_diff)
    match_count = len(matched)
    text_diff_count = len(text_diff)
    format_diff_count = len(format_diff)
    only_count = len(only_in_one)

    lines.append(f'总标题数: {total}')
    lines.append(f'✅ 完全匹配（文本+格式）: {match_count}')
    lines.append(f'⚠️  文本差异: {text_diff_count}')
    lines.append(f'🔶 格式差异: {format_diff_count}')
    lines.append(f'❌ 仅在一方: {only_count}')
    lines.append('')

    # 完全匹配的标题
    if matched:
        lines.append('# 完全匹配的标题')
        lines.append('')
        for key, value, _ in matched:
            lines.append(f'✅ {key}: {value}')
        lines.append('')

    # 文本差异
    if text_diff:
        lines.append('# 文本差异')
        lines.append('')
        for key, word_value, latex_value in text_diff:
            lines.append(f'⚠️  {key}:')
            lines.append(f'   Word:  {word_value}')
            lines.append(f'   LaTeX: {latex_value}')
            lines.append('')

    # 格式差异
    if format_diff:
        lines.append('# 格式差异（加粗）')
        lines.append('')
        for key, text, result in format_diff:
            lines.append(f'🔶 {key}: {text}')
            lines.append('   格式差异:')

            # 显示 Word 格式
            word_display = []
            for frag in result.get("word_fragments", []):
                marker = '**' if frag["bold"] else ''
                word_display.append(f'{marker}{frag["text"]}{marker}')
            lines.append(f'   Word:  {"".join(word_display)}')

            # 显示 LaTeX 格式
            latex_display = []
            for frag in result.get("latex_fragments", []):
                marker = '**' if frag["bold"] else ''
                latex_display.append(f'{marker}{frag["text"]}{marker}')
            lines.append(f'   LaTeX: {"".join(latex_display)}')

            # 显示差异详情
            if result.get("differences"):
                lines.append('   差异位置:')
                for diff in result["differences"]:
                    char = diff.get("char", "")
                    word_bold = "加粗" if diff.get("word_bold") else "正常"
                    latex_bold = "加粗" if diff.get("latex_bold") else "正常"
                    lines.append(f'     位置 {diff.get("position")}: "{char}" - Word:{word_bold}, LaTeX:{latex_bold}')
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
    parser.add_argument('--check-format', action='store_true',
                       help='检查格式（加粗）是否一致（默认仅检查文本）')

    args = parser.parse_args()

    # 提取标题
    print(f'📖 正在提取 Word 标题: {args.word_file}')
    word_headings = extract_from_word(args.word_file, check_format=args.check_format)

    print(f'📖 正在提取 LaTeX 标题: {args.latex_file}')
    latex_headings = extract_from_latex(args.latex_file, check_format=args.check_format)

    # 对比标题
    if args.check_format:
        print('🔍 正在对比标题（包含格式）...')
        matched, text_diff, format_diff, only_in_one = compare_headings_with_format(
            word_headings, latex_headings
        )
    else:
        print('🔍 正在对比标题...')
        matched, differences, only_in_one = compare_headings(word_headings, latex_headings)
        text_diff = []
        format_diff = []
        # 将旧的 differences 转换为 text_diff 格式以保持一致性
        text_diff = differences

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

        if args.check_format:
            # 格式对比模式
            if fmt == 'html':
                # 暂时使用文本报告，HTML 报告的增强在 Phase 2
                report = generate_text_report_with_format(matched, text_diff, format_diff, only_in_one)
                print('⚠️  HTML 报告的格式对比功能将在后续版本增强')
            else:
                report = generate_text_report_with_format(matched, text_diff, format_diff, only_in_one)
        else:
            # 传统模式
            if fmt == 'html':
                report = generate_html_report(matched, differences, only_in_one,
                                            args.word_file, args.latex_file)
            else:
                report = generate_text_report(matched, differences, only_in_one)

        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report)

        if args.check_format:
            total = len(matched) + len(text_diff) + len(format_diff)
            print(f'✅ 报告已生成: {args.report}')
            print(f'   总计: {total} | 匹配: {len(matched)} | 文本差异: {len(text_diff)} | 格式差异: {len(format_diff)} | 仅在一方: {len(only_in_one)}')
        else:
            print(f'✅ 报告已生成: {args.report}')
            print(f'   总计: {len(matched) + len(differences)} | 匹配: {len(matched)} | 差异: {len(differences)} | 仅在一方: {len(only_in_one)}')

    else:
        # 打印到控制台
        if args.check_format:
            report = generate_text_report_with_format(matched, text_diff, format_diff, only_in_one)
        else:
            report = generate_text_report(matched, differences, only_in_one)
        print(report)


if __name__ == '__main__':
    main()
