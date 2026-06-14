#!/usr/bin/env python3
"""
Make Research Plan - 工具函数

提供常用的辅助功能。
"""

import re
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    清理文件名，移除不安全字符。

    Args:
        filename: 原始文件名
        max_length: 最大长度

    Returns:
        清理后的文件名
    """
    # 移除或替换不安全字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip()

    # 限制长度
    if len(filename) > max_length:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:max_length - len(ext)] + ext

    return filename or "unnamed"


def generate_pdf_filename(paper: dict) -> str:
    """
    根据论文信息生成 PDF 文件名。

    格式: {第一作者}_{年份}_{期刊简写}.pdf

    Args:
        paper: 论文信息字典

    Returns:
        PDF 文件名
    """
    authors = paper.get("authors", [])
    year = paper.get("year", "unknown")
    journal = paper.get("journal", "unknown")

    # 第一作者姓氏
    first_author = authors[0] if authors else "Anonymous"
    last_name = first_author.split()[-1] if " " in first_author else first_author

    # 期刊简写（首字母或前3个字符）
    journal_abbr = journal[:4].upper() if len(journal) > 4 else journal.upper()

    filename = f"{last_name}_{year}_{journal_abbr}.pdf"
    return sanitize_filename(filename)


def validate_doi(doi: str) -> bool:
    """
    验证 DOI 格式。

    Args:
        doi: DOI 字符串

    Returns:
        是否有效
    """
    if not doi:
        return False

    # 基本格式检查
    doi_pattern = r'^10\.\d{4,9}/[^\s]+$'
    return bool(re.match(doi_pattern, doi))


def extract_doi_from_url(url: str) -> Optional[str]:
    """
    从 URL 中提取 DOI。

    Args:
        url: URL 字符串

    Returns:
        DOI 或 None
    """
    # 尝试从常见模式提取
    patterns = [
        r'doi\.org/(10\.\d{4,9}/[^\s]+)',
        r'doi=([^&]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            doi = match.group(1)
            if validate_doi(doi):
                return doi

    return None


def format_authors(authors: list, max_authors: int = 3, et_al: bool = True) -> str:
    """
    格式化作者列表。

    Args:
        authors: 作者列表
        max_authors: 显示的最大作者数
        et_al: 是否添加 "et al"

    Returns:
        格式化的作者字符串
    """
    if not authors:
        return "Unknown"

    if len(authors) <= max_authors:
        return ", ".join(authors)
    else:
        return ", ".join(authors[:max_authors]) + (" et al" if et_al else "")


if __name__ == "__main__":
    # 测试
    import sys

    print("工具函数测试:")
    print(f"  sanitize_filename: {sanitize_filename('test/file:name?.pdf')}")
    print(f"  validate_doi: {validate_doi('10.1234/test')}")

    test_paper = {
        "authors": ["Zhang San", "Li Si", "Wang Wu"],
        "year": 2024,
        "journal": "Nature Methods"
    }
    print(f"  generate_pdf_filename: {generate_pdf_filename(test_paper)}")
