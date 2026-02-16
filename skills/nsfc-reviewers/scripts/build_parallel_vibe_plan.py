#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _load_yaml(p: Path) -> dict:
    try:
        obj = yaml.safe_load(_read_text(p)) or {}
    except Exception as e:
        raise ValueError(f"failed to read yaml: {p}: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError(f"expected yaml mapping: {p}")
    return obj


def _discover_parallel_vibe_config_path(skill_root: Path) -> Path | None:
    candidates = [
        Path.home() / ".claude" / "skills" / "parallel-vibe" / "config.yaml",
        Path.home() / ".codex" / "skills" / "parallel-vibe" / "config.yaml",
        # In-repo layout: skills/nsfc-reviewers and skills/parallel-vibe are siblings.
        skill_root.parent / "parallel-vibe" / "config.yaml",
    ]
    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return None


def _thread_id_width(skill_root: Path) -> int:
    cfg_path = _discover_parallel_vibe_config_path(skill_root)
    if not cfg_path:
        return 3
    try:
        cfg = _load_yaml(cfg_path)
    except Exception:
        return 3
    defaults = cfg.get("defaults") if isinstance(cfg, dict) else None
    if not isinstance(defaults, dict):
        return 3
    w = defaults.get("thread_id_width", 3)
    try:
        w_i = int(w)
    except Exception:
        return 3
    return w_i if 1 <= w_i <= 6 else 3


def main(argv: list[str] | None = None) -> int:
    skill_root = Path(__file__).resolve().parents[1]
    cfg_path = skill_root / "config.yaml"
    if not cfg_path.exists():
        print(f"error: missing config.yaml at {cfg_path}", file=sys.stderr)
        return 2
    cfg = _load_yaml(cfg_path)
    pr = cfg.get("parallel_review") if isinstance(cfg, dict) else None
    if not isinstance(pr, dict):
        print("error: config.yaml missing parallel_review", file=sys.stderr)
        return 2

    p = argparse.ArgumentParser(prog="build_parallel_vibe_plan.py")
    p.add_argument("--panel-count", type=int, required=True, help="评审组数（= threads 数）")
    p.add_argument("--master-prompt-file", required=True, help="包含 master prompt 的文本文件路径（UTF-8）")
    p.add_argument("--out", required=True, help="输出 plan.json 路径")
    p.add_argument("--runner-type", default="", help="覆盖 config.yaml:parallel_review.runner（claude|codex|shell|local）")
    p.add_argument("--runner-profile", default="", help="覆盖 config.yaml:parallel_review.runner_profile（default|fast|deep）")
    p.add_argument("--runner-model", default="", help="显式指定 runner.model（留空表示使用 CLI 默认或 parallel-vibe config 映射）")
    p.add_argument(
        "--shell-cmd-template",
        default="",
        help="当 runner-type=shell 时必填：一条命令模板（必须包含 {prompt} 占位符）",
    )
    args = p.parse_args(argv)

    panel_count = int(args.panel_count)
    max_panels = int(pr.get("max_panel_count", 1) or 1)
    if panel_count < 1:
        print("error: --panel-count must be >= 1", file=sys.stderr)
        return 2
    if panel_count > max_panels:
        print(f"error: --panel-count must be <= {max_panels} (config.yaml:parallel_review.max_panel_count)", file=sys.stderr)
        return 2

    runner_type = str(args.runner_type or pr.get("runner") or "claude").strip().lower()
    if runner_type not in {"claude", "codex", "shell", "local"}:
        print("error: --runner-type must be one of claude|codex|shell|local", file=sys.stderr)
        return 2

    runner_profile = str(args.runner_profile or pr.get("runner_profile") or "default").strip().lower()
    if runner_profile not in {"default", "fast", "deep"}:
        print("error: --runner-profile must be one of default|fast|deep", file=sys.stderr)
        return 2

    panel_output_filename = str(pr.get("panel_output_filename") or "panel_review.md").strip()
    if not panel_output_filename:
        print("error: config.yaml:parallel_review.panel_output_filename is empty", file=sys.stderr)
        return 2

    prompt_path = Path(str(args.master_prompt_file)).expanduser()
    if not prompt_path.exists():
        print(f"error: master prompt file not found: {prompt_path}", file=sys.stderr)
        return 2
    master_prompt = _read_text(prompt_path).strip() + "\n"
    # Best-effort placeholder fill to keep the template/config consistent.
    master_prompt = master_prompt.replace("{panel_output_filename}", panel_output_filename)

    width = _thread_id_width(skill_root)
    threads: list[dict] = []
    for i in range(1, panel_count + 1):
        tid = str(i).zfill(width)
        runner_obj: dict = {
            "type": runner_type,
            "profile": runner_profile,
            "model": str(args.runner_model or "").strip(),
            "args": [],
        }
        if runner_type == "shell":
            tmpl = str(args.shell_cmd_template or "").strip()
            if not tmpl:
                print("error: --shell-cmd-template is required when --runner-type=shell", file=sys.stderr)
                return 2
            if "{prompt}" not in tmpl:
                print("error: --shell-cmd-template must contain a '{prompt}' placeholder", file=sys.stderr)
                return 2
            runner_obj["cmd_template"] = tmpl
        threads.append(
            {
                "thread_id": tid,
                "title": f"Panel G{tid}",
                "runner": runner_obj,
                "prompt": master_prompt,
            }
        )

    plan = {
        "plan_version": 1,
        "prompt": "nsfc-reviewers parallel panels",
        "threads": threads,
        "synthesis": {"enabled": False},
    }

    out_path = Path(str(args.out)).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
