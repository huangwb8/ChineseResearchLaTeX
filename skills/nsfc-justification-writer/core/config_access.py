#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Sequence


def get_mapping(cfg: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    v = cfg.get(key)
    return v if isinstance(v, Mapping) else {}


def get_mutable_mapping(cfg: Mapping[str, Any], key: str) -> MutableMapping[str, Any]:
    v = cfg.get(key)
    return v if isinstance(v, MutableMapping) else {}


def get_nested_mapping(cfg: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    cur: Mapping[str, Any] = cfg
    for k in keys:
        cur = get_mapping(cur, k)
    return cur


def get_str(cfg: Mapping[str, Any], key: str, default: str = "") -> str:
    v = cfg.get(key, default)
    return str(v) if v is not None else str(default)


def get_bool(cfg: Mapping[str, Any], key: str, default: bool = False) -> bool:
    v = cfg.get(key, default)
    return bool(v)


def get_int(cfg: Mapping[str, Any], key: str, default: int) -> int:
    v = cfg.get(key, default)
    try:
        return int(v)
    except Exception:
        return int(default)


def get_seq_str(cfg: Mapping[str, Any], key: str) -> Sequence[str]:
    v = cfg.get(key)
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return []

