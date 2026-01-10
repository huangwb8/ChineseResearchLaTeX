#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
systematic-literature-review 集成模块测试
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from core.review_integration import (
    ReviewDirectoryInfo,
    analyze_review_directory,
    detect_slr_directory,
    extract_citation_keys_from_bib,
    extract_citations_from_tex,
    format_review_directory_summary,
    validate_citation_consistency,
    validate_read_access,
)


class TestDetectSlrDirectory:
    """测试 systematic-literature-review 目录检测"""

    def test_detect_non_directory(self, tmp_path: Path):
        """测试非目录路径"""
        assert not detect_slr_directory(tmp_path / "nonexistent")

    def test_detect_regular_directory(self, tmp_path: Path):
        """测试普通目录（无标记文件夹）"""
        assert not detect_slr_directory(tmp_path)

    def test_detect_slr_directory(self, tmp_path: Path):
        """测试 systematic-literature-review 生成的目录"""
        # 创建标记文件夹
        (tmp_path / ".systematic-literature-review").mkdir()

        # 创建典型的 .tex 和 .bib 文件
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        assert detect_slr_directory(tmp_path)

    def test_detect_slr_directory_with_references_bib(self, tmp_path: Path):
        """测试使用 references.bib 命名的情况"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "references.bib").write_text("% bib")

        assert detect_slr_directory(tmp_path)

    def test_detect_slr_directory_missing_marker(self, tmp_path: Path):
        """测试缺少标记文件夹的情况"""
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        assert not detect_slr_directory(tmp_path)

    def test_detect_slr_directory_missing_tex(self, tmp_path: Path):
        """测试缺少 .tex 文件的情况"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        assert not detect_slr_directory(tmp_path)


class TestAnalyzeReviewDirectory:
    """测试文献综述目录分析"""

    def test_analyze_regular_directory(self, tmp_path: Path):
        """测试分析普通目录"""
        (tmp_path / "main.tex").write_text("% main")
        (tmp_path / "refs.bib").write_text("% refs")

        info = analyze_review_directory(tmp_path)

        assert info.path == tmp_path
        assert not info.is_slr_directory
        assert not info.read_only
        assert len(info.tex_files) >= 1
        assert len(info.bib_files) >= 1

    def test_analyze_slr_directory_read_only(self, tmp_path: Path):
        """测试分析 SLR 目录（默认只读）"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        info = analyze_review_directory(tmp_path)

        assert info.is_slr_directory
        assert info.read_only

    def test_analyze_slr_directory_allow_write(self, tmp_path: Path):
        """测试分析 SLR 目录（允许写入）"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        info = analyze_review_directory(tmp_path, allow_write=True)

        assert info.is_slr_directory
        assert not info.read_only

    def test_analyze_filters_hidden_files(self, tmp_path: Path):
        """测试过滤隐藏文件"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / ".hidden.tex").write_text("% hidden")
        (tmp_path / "topic_参考文献.bib").write_text("% bib")
        (tmp_path / ".hidden.bib").write_text("% hidden")

        info = analyze_review_directory(tmp_path)

        # 隐藏文件应被过滤
        assert not any(f.name.startswith(".") for f in info.tex_files)
        assert not any(f.name.startswith(".") for f in info.bib_files)

    def test_analyze_filters_backup_files(self, tmp_path: Path):
        """测试过滤备份文件"""
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "topic_review.tex.bak").write_text("% backup")

        info = analyze_review_directory(tmp_path)

        # 备份文件应被过滤
        assert not any(f.name.endswith(".bak") for f in info.tex_files)


class TestValidateReadAccess:
    """测试可读性验证"""

    def test_valid_directory(self, tmp_path: Path):
        """测试有效目录"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        info = analyze_review_directory(tmp_path)
        issues = validate_read_access(info)

        assert len(issues) == 0

    def test_missing_tex_files(self, tmp_path: Path):
        """测试缺少 .tex 文件"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        info = analyze_review_directory(tmp_path)
        issues = validate_read_access(info)

        assert any("未找到 .tex 文件" in issue for issue in issues)

    def test_missing_bib_files(self, tmp_path: Path):
        """测试缺少 .bib 文件"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_review.tex").write_text("% review")

        info = analyze_review_directory(tmp_path)
        issues = validate_read_access(info)

        assert any("未找到 .bib 文件" in issue for issue in issues)


class TestExtractCitationKeysFromBib:
    """测试从 .bib 文件提取 citation key"""

    def test_extract_simple_entries(self, tmp_path: Path):
        """测试提取简单条目"""
        bib_content = dedent("""
            @article{zhang2020,
                title = {Test Article}
            }
            @book{li2021,
                title = {Test Book}
            }
        """)
        bib_file = tmp_path / "refs.bib"
        bib_file.write_text(bib_content)

        keys = extract_citation_keys_from_bib(bib_file)

        assert "zhang2020" in keys
        assert "li2021" in keys

    def test_extract_with_whitespace(self, tmp_path: Path):
        """测试处理空白字符"""
        bib_content = "@article{ zhang2020 ,\n title = {Test}\n}"
        bib_file = tmp_path / "refs.bib"
        bib_file.write_text(bib_content)

        keys = extract_citation_keys_from_bib(bib_file)

        assert "zhang2020" in keys

    def test_extract_empty_file(self, tmp_path: Path):
        """测试空文件"""
        bib_file = tmp_path / "refs.bib"
        bib_file.write_text("")

        keys = extract_citation_keys_from_bib(bib_file)

        assert len(keys) == 0


class TestExtractCitationsFromTex:
    """测试从 .tex 文件提取引用"""

    def test_extract_simple_cites(self, tmp_path: Path):
        """测试提取简单引用"""
        tex_content = dedent("""
            Some text \\cite{zhang2020} and more.
            Another \\cite{li2021} here.
        """)
        tex_file = tmp_path / "main.tex"
        tex_file.write_text(tex_content)

        keys = extract_citations_from_tex(tex_file)

        assert "zhang2020" in keys
        assert "li2021" in keys

    def test_extract_multiple_cites(self, tmp_path: Path):
        """测试提取多个引用（逗号分隔）"""
        tex_content = r"Some text \cite{zhang2020,li2021,wang2022} here."
        tex_file = tmp_path / "main.tex"
        tex_file.write_text(tex_content)

        keys = extract_citations_from_tex(tex_file)

        assert "zhang2020" in keys
        assert "li2021" in keys
        assert "wang2022" in keys

    def test_extract_with_whitespace(self, tmp_path: Path):
        """测试处理空白字符"""
        tex_content = r"Some text \cite{ zhang2020 , li2021 } here."
        tex_file = tmp_path / "main.tex"
        tex_file.write_text(tex_content)

        keys = extract_citations_from_tex(tex_file)

        assert "zhang2020" in keys
        assert "li2021" in keys


class TestValidateCitationConsistency:
    """测试引用一致性验证"""

    def test_consistent_citations(self, tmp_path: Path):
        """测试一致的引用"""
        tex_content = r"Some text \cite{zhang2020} and \cite{li2021}."
        bib_content = dedent("""
            @article{zhang2020, title = {Test}}
            @article{li2021, title = {Test}}
        """)

        tex_file = tmp_path / "main.tex"
        bib_file = tmp_path / "refs.bib"
        tex_file.write_text(tex_content)
        bib_file.write_text(bib_content)

        result = validate_citation_consistency(tex_file, bib_file)

        assert len(result["missing_in_bib"]) == 0
        assert len(result["unused_in_bib"]) == 0

    def test_missing_in_bib(self, tmp_path: Path):
        """测试缺少 .bib 定义的引用"""
        tex_content = r"Some text \cite{zhang2020} and \cite{missing}."
        bib_content = dedent("""
            @article{zhang2020, title = {Test}}
        """)

        tex_file = tmp_path / "main.tex"
        bib_file = tmp_path / "refs.bib"
        tex_file.write_text(tex_content)
        bib_file.write_text(bib_content)

        result = validate_citation_consistency(tex_file, bib_file)

        assert "missing" in result["missing_in_bib"]
        assert "zhang2020" not in result["missing_in_bib"]

    def test_unused_in_bib(self, tmp_path: Path):
        """测试未使用的 .bib 条目"""
        tex_content = r"Some text \cite{zhang2020}."
        bib_content = dedent("""
            @article{zhang2020, title = {Test}}
            @article{unused, title = {Test}}
        """)

        tex_file = tmp_path / "main.tex"
        bib_file = tmp_path / "refs.bib"
        tex_file.write_text(tex_content)
        bib_file.write_text(bib_content)

        result = validate_citation_consistency(tex_file, bib_file)

        assert "unused" in result["unused_in_bib"]
        assert "zhang2020" not in result["unused_in_bib"]


class TestFormatReviewDirectorySummary:
    """测试格式化输出"""

    def test_format_slr_directory(self, tmp_path: Path):
        """测试格式化 SLR 目录摘要"""
        (tmp_path / ".systematic-literature-review").mkdir()
        (tmp_path / "topic_review.tex").write_text("% review")
        (tmp_path / "topic_参考文献.bib").write_text("% bib")

        info = analyze_review_directory(tmp_path)
        summary = format_review_directory_summary(info)

        assert "systematic-literature-review 生成的目录" in summary
        assert "只读" in summary
        assert "topic_review.tex" in summary
        assert "topic_参考文献.bib" in summary

    def test_format_regular_directory(self, tmp_path: Path):
        """测试格式化普通目录摘要"""
        (tmp_path / "main.tex").write_text("% main")
        (tmp_path / "refs.bib").write_text("% refs")

        info = analyze_review_directory(tmp_path)
        summary = format_review_directory_summary(info)

        assert "普通目录" in summary
        assert "可读写" in summary
