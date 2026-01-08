"""
测试内容优化器
"""

import pytest
import asyncio
from core.ai_integration import AIIntegration
from core.content_optimizer import ContentOptimizer


def test_optimize_content():
    """测试内容优化"""
    config = {
        "reference_protection": {"enabled": True},
        "content_optimization": {"enabled": True}
    }
    optimizer = ContentOptimizer(config, ".")
    ai = AIIntegration(enable_ai=False)

    content = "这是测试内容。"
    result = asyncio.run(optimizer.optimize_content(content, "测试章节", {}, ai_integration=ai))

    assert "original_content" in result
    assert "optimized_content" in result
    assert "optimization_log" in result
    assert "reference_validation" in result
    assert "improvement_score" in result


def test_generate_optimization_report():
    """测试生成优化报告"""
    config = {"reference_protection": {"enabled": True}}
    optimizer = ContentOptimizer(config, ".")

    content = "这是一段测试内容，包含一些重复的测试内容，测试内容很多。"
    report = optimizer.generate_optimization_report(content, "测试章节")

    assert "section" in report
    assert "total_issues" in report
    assert "issues" in report
    assert "improvement_potential" in report
    assert report["section"] == "测试章节"


def test_reference_protection_in_optimization():
    """测试优化时引用保护"""
    config = {"reference_protection": {"enabled": True}}
    optimizer = ContentOptimizer(config, ".")
    ai = AIIntegration(enable_ai=False)

    content = r"""这是内容\ref{fig1}。"""

    result = asyncio.run(optimizer.optimize_content(content, "测试章节", {}, ai_integration=ai))

    # 优化后的内容应该保留引用（即使 AI 调用失败）
    # 在实际 AI 环境中，引用会被保护和恢复
    assert r"\ref{fig1}" in result["optimized_content"]


def test_heuristic_analysis():
    """测试启发式分析"""
    config = {"reference_protection": {"enabled": True}}
    optimizer = ContentOptimizer(config, ".")

    # 测试冗余检测
    content = "测试" * 20
    result = optimizer._heuristic_analysis(content, {"remove_redundancy": True})

    assert "optimization_points" in result
    assert "improvement_potential" in result
    assert len(result["optimization_points"]) > 0
