#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

skill_root_for_import = Path(__file__).resolve().parent
sys.path.insert(0, str(skill_root_for_import))

from core.config_loader import DEFAULT_CONFIG, _deep_merge, apply_profile


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError("缺少依赖：PyYAML（无法解析 config.yaml）") from exc

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"配置文件不是 YAML dict：{path}")
    return raw


def _as_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


def _check_range(name: str, value: Any, lo: float, hi: float, errors: List[str]) -> None:
    try:
        f = float(value)
    except Exception:
        errors.append(f"{name} 不是数字：{value!r}")
        return
    if f < lo or f > hi:
        errors.append(f"{name} 超出范围 [{lo}, {hi}]：{f}")


def _check_int_ge(name: str, value: Any, min_value: int, errors: List[str]) -> None:
    try:
        i = int(value)
    except Exception:
        errors.append(f"{name} 不是整数：{value!r}")
        return
    if i < min_value:
        errors.append(f"{name} 不能小于 {min_value}：{i}")


def validate_config(config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    migration = _as_dict(config.get("migration"))
    quality = _as_dict(config.get("quality_thresholds"))
    compilation = _as_dict(config.get("compilation"))
    ai = _as_dict(config.get("ai"))
    cache = _as_dict(config.get("cache"))
    workspace = _as_dict(config.get("workspace"))

    # migration
    _check_int_ge("migration.max_rounds", migration.get("max_rounds", 1), 1, errors)
    _check_int_ge("migration.min_rounds", migration.get("min_rounds", 1), 1, errors)
    try:
        if int(migration.get("max_rounds", 1)) < int(migration.get("min_rounds", 1)):
            errors.append("migration.max_rounds 必须 >= migration.min_rounds")
    except Exception:
        pass
    _check_range("migration.convergence_threshold", migration.get("convergence_threshold", 0.05), 0.0, 1.0, errors)
    if migration.get("backup_mode") not in {None, "snapshot", "copy", "none"}:
        errors.append("migration.backup_mode 仅允许 snapshot/copy/none")
    if migration.get("backup_location") not in {None, "runs", "custom"}:
        errors.append("migration.backup_location 仅允许 runs/custom")
    _check_int_ge("migration.keep_backup_days", migration.get("keep_backup_days", 0), 0, errors)
    if migration.get("default_strategy") not in {None, "smart", "conservative", "aggressive", "fallback"}:
        errors.append("migration.default_strategy 仅允许 smart/conservative/aggressive/fallback")
    content_generation = _as_dict(migration.get("content_generation"))
    if content_generation.get("method") not in {None, "smart", "placeholder", "skip"}:
        errors.append("migration.content_generation.method 仅允许 smart/placeholder/skip")
    if migration.get("reference_handling") not in {None, "preserve", "update", "recreate"}:
        errors.append("migration.reference_handling 仅允许 preserve/update/recreate")
    if migration.get("figure_handling") not in {None, "copy", "link", "skip"}:
        errors.append("migration.figure_handling 仅允许 copy/link/skip")

    # quality_thresholds
    _check_range("quality_thresholds.min_similarity", quality.get("min_similarity", 0.7), 0.0, 1.0, errors)
    _check_int_ge("quality_thresholds.min_word_count", quality.get("min_word_count", 0), 0, errors)
    _check_int_ge("quality_thresholds.max_compile_errors", quality.get("max_compile_errors", 0), 0, errors)

    # compilation
    if compilation.get("engine") not in {None, "xelatex", "lualatex", "pdflatex"}:
        errors.append("compilation.engine 仅允许 xelatex/lualatex/pdflatex")
    if compilation.get("interaction_mode") not in {None, "nonstopmode", "batchmode", "errorstopmode"}:
        errors.append("compilation.interaction_mode 仅允许 nonstopmode/batchmode/errorstopmode")
    pass_sequence = _as_list(compilation.get("pass_sequence")) or []
    allowed_steps = {"xelatex", "lualatex", "pdflatex", "bibtex", "biber"}
    bad_steps = [s for s in pass_sequence if not isinstance(s, str) or s not in allowed_steps]
    if bad_steps:
        errors.append(f"compilation.pass_sequence 包含非法步骤：{bad_steps!r}")
    if pass_sequence:
        # 推荐序列：engine → bibtex → engine → engine
        engine = str(compilation.get("engine", "xelatex"))
        recommended = [engine, "bibtex", engine, engine]
        if pass_sequence != recommended:
            warnings.append(f"compilation.pass_sequence 非推荐 4 步法：期望 {recommended}，当前 {pass_sequence}")
    passes = compilation.get("passes")
    if passes is not None and pass_sequence:
        try:
            if int(passes) != len(pass_sequence):
                warnings.append("compilation.passes 与 compilation.pass_sequence 长度不一致")
        except Exception:
            warnings.append("compilation.passes 不是整数")
    _check_int_ge("compilation.timeout_per_pass", compilation.get("timeout_per_pass", 1), 1, errors)
    _check_int_ge("compilation.total_timeout", compilation.get("total_timeout", 1), 1, errors)
    try:
        if int(compilation.get("total_timeout", 0) or 0) > 0 and int(compilation.get("total_timeout", 0) or 0) < int(
            compilation.get("timeout_per_pass", 1)
        ):
            warnings.append("compilation.total_timeout 小于 timeout_per_pass，可能导致首轮就被总超时打断")
    except Exception:
        pass

    # ai/cache/workspace（只做基础类型与非负检查）
    if ai:
        _check_int_ge("ai.max_workers", ai.get("max_workers", 1), 1, errors)
        if "batch_size" in ai:
            _check_int_ge("ai.batch_size", ai.get("batch_size", 1), 1, errors)
    if cache:
        if "ttl_days" in cache:
            _check_int_ge("cache.ttl_days", cache.get("ttl_days", 1), 1, errors)
    if workspace:
        runs_dir = workspace.get("runs_dir")
        if runs_dir is not None and not isinstance(runs_dir, str):
            errors.append("workspace.runs_dir 必须是字符串")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(prog="validate-config", description="校验 transfer_old_latex_to_new 的 config.yaml")
    parser.add_argument(
        "--config",
        default=str(skill_root_for_import / "config.yaml"),
        help="配置文件路径（默认 skills/transfer_old_latex_to_new/config.yaml）",
    )
    parser.add_argument("--profile", default=None, choices=["quick", "balanced", "thorough"], help="可选：应用预设配置")
    parser.add_argument("--print-effective", action="store_true", help="打印合并后的最终配置（调试用）")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    if not config_path.exists():
        print(f"❌ 配置文件不存在：{config_path}", file=sys.stderr)
        return 2

    try:
        raw = _load_yaml(config_path)
        merged = _deep_merge(dict(DEFAULT_CONFIG), raw)
        if args.profile:
            merged = apply_profile(merged, args.profile)
        errors, warnings = validate_config(merged)
    except Exception as exc:
        print(f"❌ 配置解析/校验失败：{exc}", file=sys.stderr)
        return 2

    if warnings:
        print("⚠️  警告：")
        for w in warnings:
            print(f"- {w}")

    if errors:
        print("❌ 错误：", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 2

    print("✅ 配置校验通过")

    if args.print_effective:
        import json

        print(json.dumps(merged, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
