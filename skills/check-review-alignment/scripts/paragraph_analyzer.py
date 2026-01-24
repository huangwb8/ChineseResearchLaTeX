#!/usr/bin/env python3
"""
paragraph_analyzer.py - LaTeX 段落分析器

核心功能：
1. 解析 LaTeX 文档，提取段落结构
2. 定位每个引用所在的句子
3. 建立引用 → 句子 → 段落的映射关系
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class CitationInContext:
    """引用及其上下文信息"""
    bibkey: str
    cite_command: str          # 完整的 \cite{...} 命令
    sentence: str              # 包含该引用的完整句子
    sentence_start: int        # 句子在段落中的字符位置
    sentence_end: int
    line_number: int
    paragraph_index: int       # 所属段落索引
    citation_index_in_para: int  # 在段落中的第几个引用
    citation_index_global: int  # 全局第几个引用


@dataclass
class Paragraph:
    """LaTeX 段落"""
    index: int
    raw_text: str
    start_line: int  # 1-based, inclusive
    end_line: int    # 1-based, inclusive
    sentences: List[str] = field(default_factory=list)
    citations: List[CitationInContext] = field(default_factory=list)

    @property
    def has_citations(self) -> bool:
        return len(self.citations) > 0

    @property
    def citation_count(self) -> int:
        return len(self.citations)


@dataclass
class DocumentStructure:
    """LaTeX 文档结构"""
    paragraphs: List[Paragraph] = field(default_factory=list)
    citations: List[CitationInContext] = field(default_factory=list)
    bibkey_to_citations: Dict[str, List[CitationInContext]] = field(default_factory=dict)

    @property
    def total_citations(self) -> int:
        return len(self.citations)

    @property
    def total_paragraphs(self) -> int:
        return len(self.paragraphs)

    @property
    def paragraphs_with_citations(self) -> List[Paragraph]:
        return [p for p in self.paragraphs if p.has_citations]


def parse_latex_document(
    tex_path: Path,
    citation_commands: Optional[List[str]] = None
) -> DocumentStructure:
    """
    解析 LaTeX 文档，提取段落和引用结构

    Args:
        tex_path: LaTeX 文件路径
        citation_commands: 要识别的引用命令列表

    Returns:
        DocumentStructure: 文档结构对象
    """
    if citation_commands is None:
        citation_commands = ["cite", "citep", "citet", "citealp",
                            "citeauthor", "Cite", "Citet"]

    text = tex_path.read_text(encoding="utf-8", errors="ignore")
    lines = _sanitize_lines_for_analysis(text.splitlines())

    # 提取文档主体（跳过导言区）
    body_start = _find_document_body(lines)  # 0-based line index where body starts
    body_lines = lines[body_start:] if body_start > 0 else lines

    # 提取段落（body_lines 已经切片过：用 1-based 行号偏移恢复到原文件行号）
    paragraphs = _extract_paragraphs(body_lines, body_start + 1)

    # 构建引用正则
    cite_pattern = _build_citation_pattern(citation_commands)

    # 分析每个段落的引用
    all_citations: List[CitationInContext] = []
    bibkey_map: Dict[str, List[CitationInContext]] = {}

    global_cite_idx = 0
    for para in paragraphs:
        # 在段落中查找所有引用
        para_citations = _extract_citations_from_paragraph(para, cite_pattern, global_cite_idx)
        para.citations = para_citations
        all_citations.extend(para_citations)
        global_cite_idx += len(para_citations)

        # 更新 bibkey 映射
        for citation in para_citations:
            bibkey_map.setdefault(citation.bibkey, []).append(citation)

    return DocumentStructure(
        paragraphs=paragraphs,
        citations=all_citations,
        bibkey_to_citations=bibkey_map
    )


def _find_document_body(lines: List[str]) -> int:
    """查找 \\begin{document} 的位置"""
    for i, line in enumerate(lines):
        if r"\begin{document}" in line:
            return i + 1
    return 0


def _sanitize_lines_for_analysis(lines: List[str]) -> List[str]:
    """
    为引用抽取做预处理：
    - 剔除未转义的 % 注释（避免把注释里的 \\cite{} 当作真实引用）
    - 将 verbatim-like 环境内容置空（避免从代码块里误抽取引用）

    注意：这里保持行数不变，以确保行号映射仍然可靠。
    """
    out: List[str] = []
    in_verbatim = False

    for line in lines:
        stripped = line.strip()

        # 粗粒度识别 verbatim-like 环境（覆盖常见代码块环境）
        if not in_verbatim and (
            r"\begin{verbatim}" in stripped
            or r"\begin{lstlisting}" in stripped
            or r"\begin{minted}" in stripped
        ):
            in_verbatim = True
            out.append("")
            continue

        if in_verbatim and (
            r"\end{verbatim}" in stripped
            or r"\end{lstlisting}" in stripped
            or r"\end{minted}" in stripped
        ):
            in_verbatim = False
            out.append("")
            continue

        if in_verbatim:
            out.append("")
            continue

        out.append(_strip_latex_comment(line))

    return out


def _strip_latex_comment(line: str) -> str:
    """
    剔除 LaTeX 行内注释：未被转义的 '%' 之后的内容都视为注释。

    规则：
    - '\\%' 表示字面百分号，不开启注释
    - '...\\\\%' 里 '%' 仍然是注释（连续反斜杠数为偶数时不算转义）
    """
    for i, ch in enumerate(line):
        if ch != "%":
            continue

        # 统计 '%' 前连续反斜杠数量，奇数表示该 '%' 被转义。
        bs = 0
        j = i - 1
        while j >= 0 and line[j] == "\\":
            bs += 1
            j -= 1
        if bs % 2 == 1:
            continue
        return line[:i].rstrip()
    return line


def _extract_paragraphs(lines: List[str], offset_line_1based: int) -> List[Paragraph]:
    """
    从 LaTeX 行列表中提取段落
    注意：传入的 lines 应该已经是 \\begin{document} 之后的内容

    规则：
    - 空行分隔段落
    - 跳过注释行（以 % 开头）
    - 跳过纯命令行（如 \\section{...}）
    - 合并连续的非空行为段落
    """
    paragraphs: List[Paragraph] = []
    current_para_lines: List[str] = []
    para_start_line = offset_line_1based
    para_idx = 0

    for i, line in enumerate(lines):
        # 遇到 \end{document} 停止
        if r"\end{document}" in line:
            if current_para_lines:
                para_text = "\n".join(current_para_lines)
                if para_text.strip():
                    paragraphs.append(Paragraph(
                        index=para_idx,
                        raw_text=para_text,
                        start_line=para_start_line,
                        end_line=offset_line_1based + (i - 1),
                        sentences=_split_sentences(para_text)
                    ))
                    para_idx += 1
            current_para_lines = []
            break

        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith("%"):
            if current_para_lines:
                para_text = "\n".join(current_para_lines)
                if para_text.strip():
                    paragraphs.append(Paragraph(
                        index=para_idx,
                        raw_text=para_text,
                        start_line=para_start_line,
                        end_line=offset_line_1based + (i - 1),
                        sentences=_split_sentences(para_text)
                    ))
                    para_idx += 1
                current_para_lines = []
            continue

        # 跳过纯命令
        if re.match(r"\\(section|subsection|subsubsection|chapter|part|maketitle|setcounter)\s*\{?", stripped):
            if current_para_lines:
                para_text = "\n".join(current_para_lines)
                if para_text.strip():
                    paragraphs.append(Paragraph(
                        index=para_idx,
                        raw_text=para_text,
                        start_line=para_start_line,
                        end_line=offset_line_1based + (i - 1),
                        sentences=_split_sentences(para_text)
                    ))
                    para_idx += 1
                current_para_lines = []
            continue

        # 保留内容
        if not current_para_lines:
            para_start_line = offset_line_1based + i
        current_para_lines.append(line)

    # 最后一个段落
    if current_para_lines:
        para_text = "\n".join(current_para_lines)
        if para_text.strip():
            paragraphs.append(Paragraph(
                index=para_idx,
                raw_text=para_text,
                start_line=para_start_line,
                end_line=offset_line_1based + (len(lines) - 1),
                sentences=_split_sentences(para_text)
            ))

    return paragraphs


def _split_sentences(text: str) -> List[str]:
    """
    将文本分割为句子

    简单规则：
    - 按句号、问号、感叹号分割
    - 保留 LaTeX 命令完整性
    - 过滤空句子
    """
    # 保护常见缩写（避免被断句切开），例如 "i.e.", "e.g.", "etc."
    #
    # 注意：这里必须使用“可还原的 token”，避免把正则转义字符写回正文导致污染。
    abbrev_rules = [
        (r"\betc\.", "etc."),
        (r"\bi\.e\.", "i.e."),
        (r"\be\.g\.", "e.g."),
        (r"\bFig\.", "Fig."),
        (r"\bFigs\.", "Figs."),
        (r"\bvs\.", "vs."),
        (r"\bapprox\.", "approx."),
        (r"\bNo\.", "No."),
    ]
    token_map: Dict[str, str] = {}
    for idx, (pat, literal) in enumerate(abbrev_rules):
        token = f"__ABBR{idx}__"
        token_map[token] = literal
        text = re.sub(pat, token, text, flags=re.IGNORECASE)

    # 按标点分割
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z]|\\[\w]|[\u4e00-\u9fff])', text)

    # 恢复缩写
    for i, sent in enumerate(sentences):
        for token, literal in token_map.items():
            sent = sent.replace(token, literal)
        sentences[i] = sent

    # 过滤并清理
    result = [s.strip() for s in sentences if s.strip()]
    return result


def _build_citation_pattern(commands: List[str]) -> re.Pattern:
    """
    构建识别引用命令的正则表达式

    支持：
    - \cite{key}
    - \cite{key1,key2}
    - \cite[p.1]{key}
    - \cite*{key}
    - 多行引用
    """
    cmd_pattern = "|".join(re.escape(cmd) for cmd in commands)
    # 修正：避免重复的量词
    # 允许多个可选参数：\cite[see][p.3]{key}
    pattern = rf"\\(?:{cmd_pattern})\*?\s*(?:\[[^\]]*\]\s*)*\{{[^}}]*?\}}"
    return re.compile(pattern, re.MULTILINE | re.DOTALL)


def _extract_citations_from_paragraph(
    paragraph: Paragraph,
    cite_pattern: re.Pattern,
    global_start_idx: int
) -> List[CitationInContext]:
    """从段落中提取所有引用及其上下文"""
    citations: List[CitationInContext] = []

    for match in cite_pattern.finditer(paragraph.raw_text):
        cite_cmd = match.group(0)

        # 计算引用所在行号（1-based）
        # paragraph.start_line 已是文件内的 1-based 行号。
        rel_line_offset = paragraph.raw_text[:match.start()].count("\n")
        line_no = paragraph.start_line + rel_line_offset

        # 提取 bibkey（可能有多个）
        keys_match = re.search(r'\{([^}]*)\}', cite_cmd)
        if not keys_match:
            continue

        keys_str = keys_match.group(1)
        keys = [k.strip() for k in keys_str.split(",") if k.strip()]

        # 提取引用所在句子（及其边界）
        sentence, sent_start, sent_end = _extract_sentence_containing_citation(
            paragraph.raw_text, match.start(), match.end()
        )

        for key in keys:
            citation = CitationInContext(
                bibkey=key,
                cite_command=cite_cmd,
                sentence=sentence,
                sentence_start=sent_start,
                sentence_end=sent_end,
                line_number=line_no,
                paragraph_index=paragraph.index,
                citation_index_in_para=len(citations),
                citation_index_global=global_start_idx + len(citations),
            )
            citations.append(citation)

    return citations


def _extract_sentence_containing_citation(
    text: str,
    cite_start: int,
    cite_end: int
) -> Tuple[str, int, int]:
    """
    提取包含引用的完整句子

    策略：
    - 向前查找句子开始（句号、问号、感叹号或段落开头）
    - 向后查找句子结束（句号、问号、感叹号或段落结尾）
    - 保护 LaTeX 命令完整性
    """
    # 为了避免把 "i.e." / "e.g." / "etc." 里的 '.' 当作断句标点，
    # 在边界扫描时先对常见缩写做等长掩码（不改变字符串长度，保证索引可复用）。
    scan_text = text
    scan_text = re.sub(r"\betc\.", "etc_", scan_text, flags=re.IGNORECASE)
    scan_text = re.sub(r"\bi\.e\.", "i_e_", scan_text, flags=re.IGNORECASE)
    scan_text = re.sub(r"\be\.g\.", "e_g_", scan_text, flags=re.IGNORECASE)
    scan_text = re.sub(r"\bFig\.", "Fig_", scan_text, flags=re.IGNORECASE)
    scan_text = re.sub(r"\bFigs\.", "Figs_", scan_text, flags=re.IGNORECASE)
    scan_text = re.sub(r"\bvs\.", "vs_", scan_text, flags=re.IGNORECASE)
    scan_text = re.sub(r"\bapprox\.", "approx_", scan_text, flags=re.IGNORECASE)
    scan_text = re.sub(r"\bNo\.", "No_", scan_text, flags=re.IGNORECASE)

    # 向前查找
    sentence_start = 0
    for i in range(cite_start - 1, -1, -1):
        if scan_text[i] in ".!?。？！":
            sentence_start = i + 1
            break

    # 向后查找
    sentence_end = len(text)
    for i in range(cite_end, len(text)):
        if scan_text[i] in ".!?。？！":
            sentence_end = i + 1
            break

    sentence = text[sentence_start:sentence_end].strip()
    # 合并多余空格
    sentence = " ".join(sentence.split())

    return sentence, sentence_start, sentence_end


def get_paragraph_by_index(
    structure: DocumentStructure,
    index: int
) -> Optional[Paragraph]:
    """按索引获取段落"""
    if 0 <= index < len(structure.paragraphs):
        return structure.paragraphs[index]
    return None


def get_citations_by_bibkey(
    structure: DocumentStructure,
    bibkey: str
) -> List[CitationInContext]:
    """按 bibkey 获取所有引用"""
    return structure.bibkey_to_citations.get(bibkey, [])


def format_paragraph_summary(paragraph: Paragraph) -> str:
    """格式化段落摘要（用于调试）"""
    lines = [
        f"=== 段落 #{paragraph.index} ===",
        f"行范围: {paragraph.start_line}-{paragraph.end_line}",
        f"引用数: {paragraph.citation_count}",
    ]
    if paragraph.citations:
        lines.append("引用列表:")
        for cite in paragraph.citations:
            lines.append(f"  - [{cite.bibkey}] L{cite.line_number}: {cite.sentence[:80]}...")
    else:
        lines.append("（无引用）")

    return "\n".join(lines)


# 导出
__all__ = [
    "parse_latex_document",
    "DocumentStructure",
    "Paragraph",
    "CitationInContext",
    "get_paragraph_by_index",
    "get_citations_by_bibkey",
    "format_paragraph_summary",
]
