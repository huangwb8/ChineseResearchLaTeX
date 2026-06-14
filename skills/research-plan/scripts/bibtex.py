#!/usr/bin/env python3
"""
Make Research Plan - BibTeX 生成脚本

从论文信息生成 BibTeX 文件。
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def sanitize_bibtex(text: str) -> str:
    """
    清理文本用于 BibTeX。

    Args:
        text: 输入文本

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    # 替换特殊字符
    replacements = {
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\^{}",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def create_bibtex_id(authors: List[str], year: int, title: str) -> str:
    """
    生成 BibTeX ID。

    Args:
        authors: 作者列表
        year: 年份
        title: 标题

    Returns:
        BibTeX ID
    """
    # 第一作者姓氏
    first_author = authors[0] if authors else "Anonymous"
    last_name = first_author.split()[-1] if " " in first_author else first_author

    # 标题首词（去除冠词）
    title_words = title.lower().split()
    articles = {"a", "an", "the"}
    for word in title_words:
        if word not in articles and len(word) > 2:
            first_word = word
            break
    else:
        first_word = "unknown"

    return f"{last_name}{year}{first_word}"


def paper_to_bibtex(paper: Dict[str, Any]) -> str:
    """
    将论文信息转换为 BibTeX 条目。

    Args:
        paper: 论文信息字典

    Returns:
        BibTeX 条目字符串
    """
    # 确定条目类型
    entry_type = "article"
    if "conference" in paper.get("journal", "").lower() or "proceedings" in paper.get("journal", "").lower():
        entry_type = "inproceedings"

    # 生成 ID
    authors = paper.get("authors", [])
    year = paper.get("year", datetime.now().year)
    title = paper.get("title", "Untitled")
    bib_id = create_bibtex_id(authors, year, title)

    # 构建字段
    fields = []

    # 标题
    fields.append(f"  title = {{{sanitize_bibtex(title)}}}")

    # 作者
    if authors:
        # 格式化作者：Surname, Name and Surname, Name
        formatted_authors = " and ".join(authors)
        fields.append(f"  author = {{{formatted_authors}}}")

    # 年份
    if year:
        fields.append(f"  year = {{{year}}}")

    # 期刊/会议
    journal = paper.get("journal", "")
    if journal:
        if entry_type == "inproceedings":
            fields.append(f"  booktitle = {{{sanitize_bibtex(journal)}}}")
        else:
            fields.append(f"  journal = {{{sanitize_bibtex(journal)}}}")

    # 卷号
    if "volume" in paper:
        fields.append(f"  volume = {{{paper['volume']}}}")

    # 期号
    if "number" in paper or "issue" in paper:
        number = paper.get("number", paper.get("issue"))
        fields.append(f"  number = {{{number}}}")

    # 页码
    if "pages" in paper:
        fields.append(f"  pages = {{{paper['pages']}}}")

    # DOI
    if "doi" in paper and paper["doi"]:
        fields.append(f"  doi = {{{paper['doi']}}}")

    # URL
    if "url" in paper and paper["url"]:
        fields.append(f"  url = {{{paper['url']}}}")

    # 构建条目
    bibtex = f"@{entry_type}{{{bib_id},\n" + ",\n".join(fields) + "\n}"

    return bibtex


def generate_bibtex(papers: List[Dict[str, Any]], output_path: str) -> int:
    """
    生成 BibTeX 文件。

    Args:
        papers: 论文列表
        output_path: 输出文件路径

    Returns:
        生成的条目数
    """
    output = Path(output_path)

    # 确保目录存在
    output.parent.mkdir(parents=True, exist_ok=True)

    # 添加文件头
    header = [
        "% BibTeX 文件由 research-plan 自动生成",
        f"% 生成时间: {datetime.now().isoformat()}",
        f"% 论文数量: {len(papers)}",
        "",
    ]

    # 生成条目
    entries = [paper_to_bibtex(paper) for paper in papers]

    # 写入文件
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(entries))
        f.write("\n")

    return len(entries)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: bibtex.py <papers_json> <output_bib>", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        papers = data.get("papers", [])
        count = generate_bibtex(papers, output_path)

        print(f"✓ 已生成 {count} 条 BibTeX 条目到 {output_path}")

    except Exception as e:
        print(f"✗ 错误: {e}", file=sys.stderr)
        sys.exit(1)
