#!/usr/bin/env python3
"""
Run nsfc-qc multi-thread QC via parallel-vibe, while keeping all artifacts under .nsfc-qc/.

This script:
- Creates a run directory: <project_root>/.nsfc-qc/runs/<run_id>/
- Creates an isolated snapshot of the proposal (read-only) for thread workspaces
- Generates a deterministic parallel-vibe plan.json with N identical QC threads
- Executes parallel-vibe with --out-dir set to the run directory (so .parallel_vibe lives under .nsfc-qc/)

Note: This script does NOT modify proposal source files. It only writes into .nsfc-qc/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


def _now_run_id() -> str:
    return datetime.now().strftime("v%Y%m%d%H%M%S")


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_parallel_vibe_script() -> Optional[Path]:
    # Prefer the canonical locations suggested by the parallel-vibe skill.
    candidates = [
        Path.home() / ".codex" / "skills" / "parallel-vibe" / "scripts" / "parallel_vibe.py",
        Path.home() / ".claude" / "skills" / "parallel-vibe" / "scripts" / "parallel_vibe.py",
        # Fallback: the explicit path used in this repo's environment (best-effort).
        Path("/Users/bensz/.codex/skills/parallel-vibe/scripts/parallel_vibe.py"),
    ]
    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c
        except Exception:
            continue
    return None


def _copy_snapshot(project_root: Path, snapshot_dir: Path) -> None:
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)

    def ignore(_dir: str, names: List[str]) -> Set[str]:
        bad = {
            ".git",
            ".nsfc-qc",
            ".parallel_vibe",
            "__pycache__",
            ".DS_Store",
            "node_modules",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".cache",
            "dist",
            "build",
            "target",
        }
        return {n for n in names if n in bad}

    shutil.copytree(project_root, snapshot_dir, ignore=ignore, dirs_exist_ok=False)


def _mk_thread_prompt(*, project_root: str, main_tex: str) -> str:
    # Keep this prompt stable and identical across threads.
    return (
        "你将对 NSFC 标书进行“只读质量控制（QC）”。\n"
        "硬约束：\n"
        "- 禁止修改任何已有文件（尤其是 .tex/.bib/.cls/.sty）。把建议写进 RESULT.md。\n"
        "- 不编造引用与论文内容；无法确定时标记为 uncertain，并给出可复核路径。\n\n"
        f"输入：\n- project_root: {project_root}\n- main_tex: {main_tex}\n\n"
        "请在 RESULT.md 中按以下结构输出（标题必须一致）：\n"
        "1) 执行摘要\n"
        "2) 硬性问题（P0）\n"
        "3) 重要建议（P1）\n"
        "4) 可选优化（P2）\n"
        "5) 引用核查清单（含证据链）\n"
        "6) 篇幅与结构分布（给出你观察到的不合理点）\n"
        "7) 建议的最小修改路线图\n"
        "8) 附录：你运行的命令（如有）与复核提示\n"
    )


def _build_plan(
    *,
    prompt: str,
    n_threads: int,
    runner_type: str,
    runner_profile: str,
) -> dict:
    threads: List[dict] = []
    for i in range(1, n_threads + 1):
        tid = str(i).zfill(3)
        threads.append(
            {
                "thread_id": tid,
                "title": "QC",
                "runner": {"type": runner_type, "profile": runner_profile, "model": "", "args": []},
                "prompt": (
                    f"{prompt.strip()}\n\n"
                    "交付要求：\n"
                    "- 必须在当前工作目录写出 `RESULT.md`（Markdown）。\n"
                    "- 严格只读：不要修改任何已有文件。\n"
                ),
            }
        )
    return {
        "plan_version": 1,
        "prompt": prompt,
        "threads": threads,
        "synthesis": {
            "enabled": True,
            "runner": {"type": runner_type, "profile": runner_profile, "model": "", "args": []},
            "prompt": (
                "请综合输入中的多 thread 产物，生成一份最终 QC 结论（面向用户）。\n"
                "要求：\n"
                "- 去重合并同类问题；冲突结论要显式标注，并说明你选择/不确定的依据。\n"
                "- 按 P0/P1/P2 输出，并给出可执行的最小修改路线图。\n"
                "- 引用问题必须提供证据链；不确定则标记 uncertain。\n"
                "- 输出为 Markdown。\n"
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--main-tex", default="main.tex")
    ap.add_argument("--run-id", default="", help="default: auto timestamp like vYYYYMMDDHHMMSS")
    ap.add_argument("--threads", type=int, default=5)
    ap.add_argument("--execution", choices=["serial", "parallel"], default="serial")
    ap.add_argument("--max-parallel", type=int, default=3)
    ap.add_argument("--runner-type", choices=["codex", "claude"], default="codex")
    ap.add_argument("--runner-profile", choices=["fast", "default", "deep"], default="deep")
    ap.add_argument("--runs-root", default=".nsfc-qc/runs", help="relative to project-root")
    ap.add_argument("--plan-only", action="store_true", help="only write plan + snapshot; do not run threads")
    args = ap.parse_args()

    if args.threads < 1 or args.threads > 9:
        print("error: --threads must be in [1, 9]", file=sys.stderr)
        return 2

    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists():
        print(f"error: project_root not found: {project_root}", file=sys.stderr)
        return 2

    main_tex = project_root / args.main_tex
    if not main_tex.exists():
        print(f"error: main_tex not found: {main_tex}", file=sys.stderr)
        return 2

    run_id = args.run_id.strip() or _now_run_id()
    run_dir = project_root / args.runs_root / run_id
    artifacts = run_dir / "artifacts"
    final_dir = run_dir / "final"
    snapshot_dir = run_dir / "snapshot"
    artifacts.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot is the src_dir for parallel-vibe to keep workspaces clean.
    _copy_snapshot(project_root, snapshot_dir)

    base_prompt = _mk_thread_prompt(project_root=str(project_root), main_tex=str(Path(args.main_tex)))
    plan = _build_plan(
        prompt=base_prompt,
        n_threads=int(args.threads),
        runner_type=args.runner_type,
        runner_profile=args.runner_profile,
    )
    plan_path = artifacts / "parallel_vibe_plan.json"
    _write_json(plan_path, plan)

    meta = {
        "run_id": run_id,
        "project_root": str(project_root),
        "main_tex": str(Path(args.main_tex)),
        "threads": int(args.threads),
        "execution": args.execution,
        "runner_type": args.runner_type,
        "runner_profile": args.runner_profile,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "artifacts_dir": str(artifacts),
        "final_dir": str(final_dir),
    }
    _write_json(artifacts / "run_meta.json", meta)

    pv = _find_parallel_vibe_script()
    if not pv:
        (final_dir / "parallel_vibe_unavailable.txt").write_text(
            "parallel-vibe script not found. See skills/nsfc-qc/SKILL.md for downgrade strategy.\n",
            encoding="utf-8",
        )
        print(str(run_dir))
        return 0

    if args.plan_only:
        print(str(run_dir))
        return 0

    cmd = [
        sys.executable,
        str(pv),
        "--plan-file",
        str(plan_path),
        "--src-dir",
        str(snapshot_dir),
        "--out-dir",
        str(run_dir),
    ]
    if args.execution == "parallel":
        cmd += ["--parallel", "--max-parallel", str(int(args.max_parallel))]

    log_path = artifacts / "parallel_vibe_runner.log"
    with log_path.open("w", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd) + "\n\n")
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

    (artifacts / "parallel_vibe_exit_code.txt").write_text(str(int(p.returncode)) + "\n", encoding="utf-8")
    print(str(run_dir))
    return int(p.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

