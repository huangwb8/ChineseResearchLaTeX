#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio

from core.ai_integration import AIIntegration


def test_ai_integration_falls_back_when_disabled() -> None:
    ai = AIIntegration(enable_ai=False, responder=lambda *_: {"ok": True})
    called = {"n": 0}

    async def _run() -> object:
        return await ai.process_request(
            task="t",
            prompt="p",
            output_format="json",
            fallback=lambda: (called.__setitem__("n", called["n"] + 1) or {"fallback": True}),
        )

    out = asyncio.run(_run())
    assert out == {"fallback": True}
    assert called["n"] == 1
    assert ai.get_stats()["fallback_mode"] is True


def test_ai_integration_falls_back_when_no_responder() -> None:
    ai = AIIntegration(enable_ai=True, responder=None)

    async def _run() -> object:
        return await ai.process_request(
            task="t",
            prompt="p",
            output_format="json",
            fallback=lambda: {"fallback": True},
        )

    out = asyncio.run(_run())
    assert out == {"fallback": True}
    assert ai.get_stats()["fallback_mode"] is True


def test_ai_integration_accepts_dict_json_response() -> None:
    ai = AIIntegration(enable_ai=True, responder=lambda *_: {"a": 1})

    async def _run() -> object:
        return await ai.process_request(task="t", prompt="p", output_format="json", fallback=lambda: {"fallback": True})

    out = asyncio.run(_run())
    assert out == {"a": 1}
    assert ai.get_stats()["success_count"] == 1


def test_ai_integration_parses_fenced_json_block() -> None:
    text = "some preface\n```json\n{\"x\": 1}\n```\nmore"
    ai = AIIntegration(enable_ai=True, responder=lambda *_: text)

    async def _run() -> object:
        return await ai.process_request(task="t", prompt="p", output_format="json", fallback=lambda: {"fallback": True})

    out = asyncio.run(_run())
    assert out == {"x": 1}


def test_ai_integration_falls_back_on_invalid_json() -> None:
    ai = AIIntegration(enable_ai=True, responder=lambda *_: "not json at all")

    async def _run() -> object:
        return await ai.process_request(task="t", prompt="p", output_format="json", fallback=lambda: {"fallback": True})

    out = asyncio.run(_run())
    assert out == {"fallback": True}
    assert ai.get_stats()["fallback_mode"] is True


def test_ai_integration_supports_async_responder() -> None:
    async def responder(task: str, prompt: str, output_format: str) -> object:
        await asyncio.sleep(0)
        return {"task": task, "fmt": output_format, "ok": True}

    ai = AIIntegration(enable_ai=True, responder=responder)  # type: ignore[arg-type]

    async def _run() -> object:
        return await ai.process_request(
            task="hello", prompt="p", output_format="json", fallback=lambda: {"fallback": True}
        )

    out = asyncio.run(_run())
    assert out == {"task": "hello", "fmt": "json", "ok": True}

