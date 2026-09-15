#!/usr/bin/env python3
"""
run_pipeline.py - pipeline_runner 的轻量封装

目的：
- 统一 work_dir 生成规则并保持幂等，避免出现 {topic}/{topic} 异常嵌套目录
- 让调用方只需要提供 runs_root + topic
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from query_contract import normalize_output_stem


def _sanitize_topic(raw: str) -> str:
    """兼容旧调用方；实际规则由 query_contract 统一维护。"""
    return normalize_output_stem(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run research-literature-review pipeline with idempotent work_dir")
    parser.add_argument("--topic", required=True, help="主题")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=None,
        help="兼容旧入口：显式指定 runs 根目录；未指定时使用 .bensz-api 任务工作区",
    )
    parser.add_argument("--work-dir", type=Path, default=None, help="显式 work_dir（优先级最高）")
    parser.add_argument("--domain", default="general", help="领域（可选）")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent.parent / "config.yaml")
    parser.add_argument("--review-level", choices=["premium", "standard", "basic"], help="档位（可选）")
    parser.add_argument(
        "--purpose",
        choices=["standard-review", "novelty-check"],
        default="standard-review",
        help="标准综述或轻量查新",
    )
    parser.add_argument("--output-stem", help="文件名前缀（可选）")
    parser.add_argument("--query-file", "--queries", dest="query_file", type=Path, help="多查询 JSON 文件")
    parser.add_argument("--allow-single-query-fallback", action="store_true", help="显式授权单查询后备")
    parser.add_argument("--fallback-reason", help="单查询后备原因（用于审计）")
    parser.add_argument("--search-skill-root", type=Path, help="research-literature-search Skill 根目录")
    parser.add_argument("--prepare-only", action="store_true", help="只生成查询输入模板，不启动检索")
    parser.add_argument("--resume-from", type=int, help="从阶段编号开始执行（0-based）")
    parser.add_argument("--publish-dir", type=Path, help="正式交付目录（与内部 work_dir 分离）")
    parser.add_argument("--include-supporting", action="store_true", help="同时发布 tex/bib/工作条件/验证报告")
    parser.add_argument("--force-publish", action="store_true", help="允许覆盖发布目录中的同名文件")
    args = parser.parse_args()

    safe_topic = _sanitize_topic(args.output_stem or args.topic)
    if args.work_dir is not None:
        work_dir = args.work_dir
    elif args.runs_root is not None:
        runs_root = args.runs_root
        # 幂等：如果 runs_root 已经是 runs/{safe_topic}，则不再重复拼接
        work_dir = runs_root if runs_root.name == safe_topic else (runs_root / safe_topic)
    else:
        work_dir = None

    cmd = [
        sys.executable,
        str(Path(__file__).parent / "pipeline_runner.py"),
        "--topic",
        args.topic,
        "--domain",
        args.domain,
        "--config",
        str(args.config),
        "--purpose",
        args.purpose,
    ]
    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
        cmd += ["--work-dir", str(work_dir)]
    if args.review_level:
        cmd += ["--review-level", args.review_level]
    if args.output_stem:
        cmd += ["--output-stem", args.output_stem]
    if args.query_file is not None:
        cmd += ["--query-file", str(args.query_file.expanduser().resolve())]
    if args.allow_single_query_fallback:
        cmd += ["--allow-single-query-fallback"]
    if args.fallback_reason:
        cmd += ["--fallback-reason", args.fallback_reason]
    if args.search_skill_root is not None:
        cmd += ["--search-skill-root", str(args.search_skill_root.expanduser().resolve())]
    if args.prepare_only:
        cmd += ["--prepare-only"]
    if args.resume_from is not None:
        cmd += ["--resume-from", str(args.resume_from)]
    if args.publish_dir is not None:
        cmd += ["--publish-dir", str(args.publish_dir)]
    if args.include_supporting:
        cmd += ["--include-supporting"]
    if args.force_publish:
        cmd += ["--force-publish"]

    print(f"work_dir: {work_dir or '(由 pipeline_runner 分配 .bensz-api 任务工作区)'}")
    proc = subprocess.run(cmd)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
