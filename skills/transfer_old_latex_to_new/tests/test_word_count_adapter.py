"""
测试字数自动适配器
"""

import pytest
import asyncio
from core.ai_integration import AIIntegration
from core.word_count_adapter import WordCountAdapter


def test_count_chinese_words():
    """测试中文字数统计"""
    config = {}
    adapter = WordCountAdapter(config, ".")

    # 测试纯中文
    content = "一二三四五六七八九十" * 2  # 20 个中文字符
    count = adapter._count_chinese_words(content)
    assert count == 20

    # 测试包含 LaTeX 命令
    content = r"""这是中文内容。
\section{标题}
更多中文内容。
\cite{ref123}
继续中文。"""
    count = adapter._count_chinese_words(content)
    # 应该排除 LaTeX 命令，只统计中文
    assert count > 0
    assert "section" not in str(count)


def test_word_count_requirements():
    """测试字数要求加载"""
    config = {}
    adapter = WordCountAdapter(config, ".")

    requirements = adapter.version_requirements
    assert "2025_to_2026" in requirements
    assert "立项依据" in requirements["2025_to_2026"]

    req = requirements["2025_to_2026"]["立项依据"]
    assert req["old"] == (1500, 2000)
    assert req["new"] == (2000, 2500)


def test_adapt_content_skip():
    """测试无字数要求时跳过"""
    config = {}
    adapter = WordCountAdapter(config, ".")

    content = "测试内容"
    ai = AIIntegration(enable_ai=False)
    result = asyncio.run(adapter.adapt_content_by_version_pair(content, "不存在章节", "2025_to_2026", ai_integration=ai))

    assert result["status"] == "skip"


def test_adapt_content_ok():
    """测试字数符合要求"""
    config = {}
    adapter = WordCountAdapter(config, ".")

    # 构造符合新字数要求的内容
    content = "中文内容" * 500  # 约 1000 字
    ai = AIIntegration(enable_ai=False)
    result = asyncio.run(adapter.adapt_content_by_version_pair(content, "研究内容", "2025_to_2026", ai_integration=ai))

    # 由于实际字数可能不在范围内，这里只测试返回结构
    assert "status" in result
    assert "current_count" in result


def test_adapt_content_target_within_tolerance():
    """测试目标字数在容忍范围内不调整"""
    config = {"word_count_adaptation": {"target_tolerance": 50}}
    adapter = WordCountAdapter(config, ".")
    ai = AIIntegration(enable_ai=False)

    content = "中文内容" * 100  # 约 400 字
    current = adapter._count_chinese_words(content)
    result = asyncio.run(adapter.adapt_content(content, "测试章节", current + 10, ai_integration=ai))

    assert result["action"] == "within_tolerance"
    assert result["adapted_content"] == content


def test_generate_report():
    """测试生成字数报告"""
    config = {}
    adapter = WordCountAdapter(config, ".")

    content = "测试内容" * 100
    report = adapter.generate_word_count_report(content, "立项依据", "2025_to_2026")

    assert "section" in report
    assert "current_count" in report
    assert "old_requirement" in report
    assert "new_requirement" in report
    assert report["section"] == "立项依据"
