"""
BibTeX Parser - BibTeX 解析工具
提供 BibTeX 文件解析和条目提取功能
"""

import re
from typing import List, Dict, Optional
from pathlib import Path


def parse_bibtex_file(file_path: Path) -> List[Dict[str, str]]:
    """
    解析 BibTeX 文件

    Args:
        file_path: BibTeX 文件路径

    Returns:
        List[Dict]: 条目列表，每个条目包含所有字段
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return parse_bibtex_content(content)


def parse_bibtex_content(content: str) -> List[Dict[str, str]]:
    """
    解析 BibTeX 内容

    Args:
        content: BibTeX 文件内容

    Returns:
        List[Dict]: 条目列表
    """
    entries = []

    # 匹配条目
    # 支持多行条目，包括嵌套的花括号
    entry_pattern = r'@(\w+)\s*\{([^,]+),\s*((?:[^@]|(?:\{[^{}]*\}))*)\}'

    # 为了正确处理嵌套的花括号，我们需要更复杂的解析
    # 这里使用简化的方法
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 查找条目开始
        if line.startswith('@'):
            # 提取条目类型和键
            match = re.match(r'@(\w+)\s*\{([^,]+),', line)
            if match:
                entry_type = match.group(1)
                citekey = match.group(2)

                # 收集条目内容
                entry_content = line[match.end():]
                i += 1

                # 继续读取直到找到条目结束
                brace_count = entry_content.count('{') - entry_content.count('}')

                while i < len(lines) and brace_count > 0:
                    entry_content += '\n' + lines[i]
                    brace_count += lines[i].count('{') - lines[i].count('}')
                    i += 1

                # 解析字段
                entry = {
                    'key': citekey,
                    'type': entry_type
                }

                # 提取字段
                fields = extract_bibtex_fields(entry_content)
                entry.update(fields)

                entries.append(entry)
        else:
            i += 1

    return entries


def extract_bibtex_fields(content: str) -> Dict[str, str]:
    """
    从 BibTeX 条目内容中提取字段

    Args:
        content: 条目内容（不包含 @type{key, 部分）

    Returns:
        Dict[str, str]: 字段字典
    """
    fields = {}

    # 匹配字段
    # 字段格式：field_name = {value} 或 field_name = "value"
    field_pattern = r'(\w+)\s*=\s*(?:\{([^}]*)\}|"([^"]*)")'

    matches = re.finditer(field_pattern, content)
    for match in matches:
        field_name = match.group(1)
        # 值可能在 group(2) 或 group(3)
        field_value = match.group(2) if match.group(2) is not None else match.group(3)
        fields[field_name] = field_value

    return fields


def extract_bibtex_entries(file_path: Path, entry_type: Optional[str] = None) -> List[Dict[str, str]]:
    """
    提取 BibTeX 条目

    Args:
        file_path: BibTeX 文件路径
        entry_type: 条目类型过滤（可选），如 "article", "book" 等

    Returns:
        List[Dict]: 条目列表
    """
    entries = parse_bibtex_file(file_path)

    if entry_type:
        entries = [e for e in entries if e.get('type') == entry_type]

    return entries


def find_bibtex_entry_by_key(file_path: Path, citekey: str) -> Optional[Dict[str, str]]:
    """
    根据 citekey 查找条目

    Args:
        file_path: BibTeX 文件路径
        citekey: 引用键

    Returns:
        Optional[Dict]: 找到的条目，如果未找到则返回 None
    """
    entries = parse_bibtex_file(file_path)

    for entry in entries:
        if entry.get('key') == citekey:
            return entry

    return None


def format_bibtex_entry(entry: Dict[str, str]) -> str:
    """
    将条目字典格式化为 BibTeX 字符串

    Args:
        entry: 条目字典

    Returns:
        str: BibTeX 格式的字符串
    """
    entry_type = entry.get('type', 'misc')
    citekey = entry.get('key', 'unknown')

    # 排除键和类型字段
    fields = {k: v for k, v in entry.items() if k not in ['key', 'type']}

    # 构建字段字符串
    field_strings = []
    for field_name, field_value in fields.items():
        field_strings.append(f"  {field_name} = {{{field_value}}}")

    fields_str = ',\n'.join(field_strings)

    return f"@{entry_type}{{{citekey},\n{fields_str}\n}}"


def validate_bibtex_syntax(content: str) -> tuple[bool, list[str]]:
    """
    验证 BibTeX 语法

    Args:
        content: BibTeX 内容

    Returns:
        tuple[bool, list[str]]: (是否有效, 错误列表)
    """
    errors = []

    try:
        entries = parse_bibtex_content(content)

        # 检查基本要求
        for entry in entries:
            # 检查必需字段（根据类型）
            entry_type = entry.get('type', '')

            if entry_type == 'article':
                required_fields = ['author', 'title', 'journal', 'year']
            elif entry_type == 'book':
                required_fields = ['author', 'title', 'publisher', 'year']
            elif entry_type == 'inproceedings':
                required_fields = ['author', 'title', 'booktitle', 'year']
            else:
                required_fields = ['title', 'year']

            for field in required_fields:
                if field not in entry or not entry[field]:
                    errors.append(f"条目 '{entry.get('key', 'unknown')}' 缺少必需字段：{field}")

    except Exception as e:
        errors.append(f"解析错误：{str(e)}")

    return len(errors) == 0, errors
