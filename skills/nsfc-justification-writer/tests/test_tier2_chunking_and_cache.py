#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from core.ai_integration import AIIntegration
from core.config_loader import load_config
from core.hybrid_coordinator import HybridCoordinator


def _make_project(tmp_path: Path, *, body_repeat: int) -> Path:
    project_root = tmp_path / "proj"
    (project_root / "extraTex").mkdir(parents=True, exist_ok=True)
    (project_root / "references").mkdir(parents=True, exist_ok=True)
    (project_root / "references" / "t.bib").write_text(
        "@article{A,\n  title={x},\n  year={2020},\n  doi={10.5555/12345678}\n}\n",
        encoding="utf-8",
    )
    filler = ("这是一些正文，用于拉长文本。\n" * body_repeat).strip()
    tex = (
        "\\subsubsection{研究背景}\n" + filler + "\n"
        "\\subsubsection{国内外研究现状}\n" + filler + "\n"
        "\\subsubsection{现有研究的局限性}\n" + filler + "\n"
        "\\subsubsection{研究切入点}\n" + filler + "\n"
    )
    (project_root / "extraTex" / "1.1.立项依据.tex").write_text(tex, encoding="utf-8")
    return project_root


def test_tier2_chunking_merges_results(tmp_path: Path) -> None:
    skill_root = Path(__file__).resolve().parents[1]
    project_root = _make_project(tmp_path, body_repeat=200)
    cfg = load_config(skill_root, load_user_override=False)
    cfg.setdefault("ai", {})["cache_dir"] = str(tmp_path / "cache")

    def responder(task: str, prompt: str, output_format: str) -> object:
        return {
            "logic": [],
            "terminology": [],
            "evidence": [],
            "suggestions": [task],
        }

    coord = HybridCoordinator(
        skill_root=skill_root,
        config=cfg,
        ai_integration=AIIntegration(enable_ai=True, responder=responder),
    )

    report = coord.diagnose(
        project_root=project_root,
        include_tier2=True,
        tier2_chunk_size=2000,
        tier2_max_chunks=10,
        tier2_fresh=True,
    )
    assert report.tier2 is not None
    suggestions = (report.tier2 or {}).get("suggestions")  # type: ignore[union-attr]
    assert isinstance(suggestions, list)
    # 至少触发 2 个 chunk
    assert any("diagnose_tier2_chunk_1" in s for s in suggestions)
    assert any("diagnose_tier2_chunk_2" in s for s in suggestions)


def test_ai_integration_json_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    ai = AIIntegration(enable_ai=True, responder=lambda *_: {"x": 1})

    async def _run() -> object:
        return await ai.process_request(
            task="t",
            prompt="p",
            output_format="json",
            cache_dir=cache_dir,
            fresh=True,
            fallback=lambda: {"fallback": True},
        )

    import asyncio

    out = asyncio.run(_run())
    assert out == {"x": 1}
    assert any(p.suffix == ".json" for p in cache_dir.glob("*.json"))

    ai2 = AIIntegration(enable_ai=True, responder=lambda *_: (_ for _ in ()).throw(RuntimeError("should not call")))

    async def _run2() -> object:
        return await ai2.process_request(
            task="t",
            prompt="p",
            output_format="json",
            cache_dir=cache_dir,
            fresh=False,
            fallback=lambda: {"fallback": True},
        )

    out2 = asyncio.run(_run2())
    assert out2 == {"x": 1}

