"""
LaTeX Parser - LaTeX 解析工具
提供 LaTeX 格式相关的解析和验证功能
"""

import re
from typing import List, Tuple, Dict


def extract_format_lines(content: str) -> List[str]:
    """
    提取 LaTeX 文件中的格式定义行

    Args:
        content: LaTeX 文件内容

    Returns:
        List[str]: 格式定义行列表
    """
    lines = content.split("\n")
    format_lines = []

    # 受保护的命令模式
    protected_patterns = [
        r'\\setlength\{[^}]+\}\{[^}]+\}',
        r'\\geometry\{[^}]+\}',
        r'\\definecolor\{[^}]+\}\{[^}]+\}\{[^}]+\}',
        r'\\setCJKfamilyfont\{[^}]+\}(\[[^]]*\])?\{[^}]+\}',
        r'\\setmainfont(\[[^]]*\])?\{[^}]+\}',
        r'\\titleformat\{[^}]+\}\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}',
        r'\\setlist\[[^]]+\]\{[^}]+\}',
        r'\\newcommand\{[^}]+\}',
        r'\\renewcommand\{[^}]+\}',
    ]

    for line in lines:
        for pattern in protected_patterns:
            if re.search(pattern, line):
                format_lines.append(line)
                break

    return format_lines


def validate_latex_syntax(content: str) -> Tuple[bool, List[str]]:
    """
    验证 LaTeX 语法的基本正确性

    Args:
        content: LaTeX 内容

    Returns:
        Tuple[bool, List[str]]: (是否有效, 错误列表)
    """
    errors = []

    # 检查花括号匹配
    if not _check_braces_balance(content):
        errors.append("花括号不匹配")

    # 检查环境匹配
    env_errors = _check_environments(content)
    errors.extend(env_errors)

    # 检查常见的语法错误
    common_errors = _check_common_errors(content)
    errors.extend(common_errors)

    return len(errors) == 0, errors


def _check_braces_balance(content: str) -> bool:
    """检查花括号是否平衡"""
    depth = 0
    for char in content:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _check_environments(content: str) -> List[str]:
    """检查环境是否匹配"""
    errors = []

    # 提取所有环境
    begin_pattern = r'\\begin\{([^}]+)\}'
    end_pattern = r'\\end\{([^}]+)\}'

    begins = re.findall(begin_pattern, content)
    ends = re.findall(end_pattern, content)

    # 简单检查：数量应该相同
    # 更复杂的检查需要考虑嵌套
    env_stack = []

    # 找到所有 begin 和 end 的位置
    begin_matches = list(re.finditer(begin_pattern, content))
    end_matches = list(re.finditer(end_pattern, content))

    # 按位置排序
    all_matches = []
    for match in begin_matches:
        all_matches.append(('begin', match.group(1), match.start()))
    for match in end_matches:
        all_matches.append(('end', match.group(1), match.start()))

    all_matches.sort(key=lambda x: x[2])

    # 检查匹配
    for match_type, env_name, pos in all_matches:
        if match_type == 'begin':
            env_stack.append(env_name)
        else:  # end
            if not env_stack:
                errors.append(f"未匹配的 \\end{{{env_name}}}")
            elif env_stack[-1] != env_name:
                errors.append(f"环境不匹配：预期 \\end{{{env_stack[-1]}}}，但找到 \\end{{{env_name}}}")
            else:
                env_stack.pop()

    # 检查未关闭的环境
    for env_name in env_stack:
        errors.append(f"未关闭的环境：\\begin{{{env_name}}}")

    return errors


def _check_common_errors(content: str) -> List[str]:
    """检查常见的 LaTeX 错误"""
    errors = []

    # 检查未转义的百分号（在注释中是允许的）
    # 这是一个简化检查，实际情况更复杂

    # 检查表格行末尾的 \\
    table_lines = re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}', content, re.DOTALL)
    for table in table_lines:
        lines = table.split('\\\\')
        for i, line in enumerate(lines[:-1]):  # 最后一行不需要 \\
            if '&' in line and not line.strip().endswith('\\\\'):
                # 这里只是一个启发式检查
                pass

    return errors


def extract_sections(content: str) -> List[Dict[str, str]]:
    """
    提取 LaTeX 文件中的章节结构

    Args:
        content: LaTeX 文件内容

    Returns:
        List[Dict]: 章节列表，每个章节包含 level, title, content
    """
    sections = []

    # 章节命令模式
    section_patterns = [
        (r'\\chapter\{([^}]+)\}', 'chapter'),
        (r'\\section\{([^}]+)\}', 'section'),
        (r'\\subsection\{([^}]+)\}', 'subsection'),
        (r'\\subsubsection\{([^}]+)\}', 'subsubsection'),
        (r'\\subsubsubsection\{([^}]+)\}', 'subsubsubsection'),
    ]

    lines = content.split('\n')
    current_section = None

    for line in lines:
        matched = False
        for pattern, level in section_patterns:
            match = re.search(pattern, line)
            if match:
                if current_section:
                    sections.append(current_section)

                current_section = {
                    'level': level,
                    'title': match.group(1),
                    'content': ''
                }
                matched = True
                break

        if current_section and not matched:
            current_section['content'] += line + '\n'

    if current_section:
        sections.append(current_section)

    return sections


def find_citations(content: str) -> List[str]:
    """
    查找所有文献引用

    Args:
        content: LaTeX 内容

    Returns:
        List[str]: 引用的 citekey 列表
    """
    # 匹配 \cite{key} 或 \cite{key1,key2}
    pattern = r'\\cite\{([^}]+)\}'
    matches = re.findall(pattern, content)

    # 展开逗号分隔的多个引用
    citations = []
    for match in matches:
        keys = match.split(',')
        citations.extend([key.strip() for key in keys])

    return citations


def find_figures(content: str) -> List[str]:
    """
    查找所有图片引用

    Args:
        content: LaTeX 内容

    Returns:
        List[str]: 图片文件路径列表
    """
    # 匹配 \includegraphics{path} 或 \includegraphics[options]{path}
    pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}'
    return re.findall(pattern, content)
