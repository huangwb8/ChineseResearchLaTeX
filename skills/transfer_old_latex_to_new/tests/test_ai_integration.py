"""
测试 AIIntegration（优雅降级）
"""

import asyncio

from core.ai_integration import AIIntegration


def test_ai_fallback_when_disabled():
    ai = AIIntegration(enable_ai=False)
    result = asyncio.run(
        ai.process_request(
            task="test",
            prompt="test",
            fallback=lambda: {"result": "fallback"},
            output_format="json",
        )
    )
    assert result == {"result": "fallback"}


def test_ai_stats():
    ai = AIIntegration(enable_ai=False)
    asyncio.run(
        ai.process_request(
            task="test",
            prompt="test",
            fallback=lambda: {"result": "fallback"},
            output_format="json",
        )
    )
    stats = ai.get_stats()
    assert stats["request_count"] == 1
    assert stats["fallback_mode"] is True
