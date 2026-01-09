#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from core.config_loader import load_config
from core.security import build_write_policy, validate_write_target


def test_load_config_without_pyyaml_still_enforces_guardrails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    skill_root = Path(__file__).resolve().parents[1]

    orig_import = builtins.__import__

    def _fake_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):  # type: ignore[no-untyped-def]
        if name == "yaml":
            raise ImportError("PyYAML missing (simulated)")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    cfg = load_config(skill_root, load_user_override=False)
    meta = cfg.get("_config_loader", {}) or {}
    assert meta.get("yaml_available") is False
    assert any("未安装 PyYAML" in str(w) for w in (meta.get("warnings", []) or []))

    policy = build_write_policy(cfg)
    assert policy.allowed_relpaths == ["extraTex/1.1.立项依据.tex"]

    (tmp_path / "extraTex").mkdir()
    (tmp_path / "extraTex" / "1.1.立项依据.tex").write_text("ok", encoding="utf-8")
    (tmp_path / "main.tex").write_text("no", encoding="utf-8")

    # 白名单目标允许
    validate_write_target(
        project_root=tmp_path,
        target_path=(tmp_path / "extraTex" / "1.1.立项依据.tex"),
        policy=policy,
    )

    # 非白名单目标拒绝（主模板等）
    with pytest.raises(RuntimeError):
        validate_write_target(project_root=tmp_path, target_path=(tmp_path / "main.tex"), policy=policy)

