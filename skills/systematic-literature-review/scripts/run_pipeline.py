#!/usr/bin/env python3
"""
run_pipeline.py - pipeline_runner 的轻量封装

目的：
- 统一 work_dir 生成规则并保持幂等，避免出现 {topic}/{topic} 异常嵌套目录
- 让调用方只需要提供 runs_root + topic
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def _sanitize_topic(raw: str) -> str:
    s = re.sub(r"[\\/\\:*?\"<>|]+", "", raw.strip())
    s = re.sub(r"\s+", "-", s)
    return s[:80] or "topic"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run systematic-literature-review pipeline with idempotent work_dir")
    parser.add_argument("--topic", required=True, help="主题")
    parser.add_argument("--runs-root", type=Path, default=Path("runs"), help="runs 根目录（默认: runs/）")
    parser.add_argument("--work-dir", type=Path, default=None, help="显式 work_dir（优先级最高）")
    parser.add_argument("--domain", default="general", help="领域（可选）")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent.parent / "config.yaml")
    parser.add_argument("--review-level", choices=["premium", "standard", "basic"], help="档位（可选）")
    parser.add_argument("--output-stem", help="文件名前缀（可选）")
    parser.add_argument("--resume-from", type=int, help="从阶段编号开始执行（0-based）")
    args = parser.parse_args()

    safe_topic = _sanitize_topic(args.output_stem or args.topic)
    if args.work_dir is not None:
        work_dir = args.work_dir
    else:
        runs_root = args.runs_root
        # 幂等：如果 runs_root 已经是 runs/{safe_topic}，则不再重复拼接
        work_dir = runs_root if runs_root.name == safe_topic else (runs_root / safe_topic)

    work_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(Path(__file__).parent / "pipeline_runner.py"),
        "--topic",
        args.topic,
        "--domain",
        args.domain,
        "--config",
        str(args.config),
        "--work-dir",
        str(work_dir),
    ]
    if args.review_level:
        cmd += ["--review-level", args.review_level]
    if args.output_stem:
        cmd += ["--output-stem", args.output_stem]
    if args.resume_from is not None:
        cmd += ["--resume-from", str(args.resume_from)]

    print(f"work_dir: {work_dir}")
    proc = subprocess.run(cmd)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

