#!/usr/bin/env python3
"""
Run nsfc-qc multi-thread QC via parallel-vibe, while keeping all artifacts under .nsfc-qc/.

This script:
- Creates a run directory: <project_root>/.nsfc-qc/runs/<run_id>/
- (Default) Runs deterministic precheck and reference evidence collection into artifacts/
- Creates an isolated snapshot of the proposal (read-only) for thread workspaces
- Copies key artifacts into snapshot/.nsfc-qc_input/ for threads to read
- Generates a deterministic parallel-vibe plan.json with N identical QC threads
- Executes parallel-vibe with --out-dir set to the run directory (so .parallel_vibe lives under .nsfc-qc/)
- (Optional) Runs isolated 4-step compile as the LAST step and updates metrics

Note: This script does NOT modify proposal source files. It only writes into .nsfc-qc/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set


def _now_run_id() -> str:
    return datetime.now().strftime("v%Y%m%d%H%M%S")


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_parallel_vibe_script() -> Optional[Path]:
    env = os.environ.get("PARALLEL_VIBE_SCRIPT", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.exists() and p.is_file():
            return p.resolve()

    # Prefer the canonical locations suggested by the parallel-vibe skill.
    candidates = [
        Path.home() / ".codex" / "skills" / "parallel-vibe" / "scripts" / "parallel_vibe.py",
        Path.home() / ".claude" / "skills" / "parallel-vibe" / "scripts" / "parallel_vibe.py",
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

    # Enforce read-only at filesystem level (files only; keep directories writable so the run folder remains removable).
    for p in snapshot_dir.rglob("*"):
        try:
            if p.is_file():
                mode = p.stat().st_mode
                os.chmod(p, mode & ~0o222)  # drop write bits, keep exec bits
        except Exception:
            continue


def _mk_thread_prompt(*, main_tex: str) -> str:
    # Keep this prompt stable and identical across threads.
    return (
        "你将对 NSFC 标书进行“只读质量控制（QC）”。\n"
        "硬约束：\n"
        "- 你的当前工作目录（cwd）就是标书项目根目录（来自原项目的 snapshot 拷贝）。\n"
        "- 禁止修改任何已有文件（尤其是 .tex/.bib/.cls/.sty）。把建议写进 RESULT.md。\n"
        "- 禁止访问父目录（..）与任何绝对路径写入。\n"
        "- 不编造引用与论文内容；无法确定时标记为 uncertain，并给出可复核路径。\n\n"
        "证据包（只读，可用于“引用真伪/错引风险”的语义核查）：\n"
        "- `./.nsfc-qc_input/precheck.json`\n"
        "- `./.nsfc-qc_input/citations_index.csv`\n"
        "- `./.nsfc-qc_input/reference_evidence.jsonl`（硬编码抓取到的题目/摘要/可选 PDF 片段 + 标书内引用上下文）\n\n"
        f"输入：\n- project_root: .\n- main_tex: {main_tex}\n\n"
        "请在 RESULT.md 中按以下结构输出（标题必须一致）：\n"
        "1) 执行摘要\n"
        "2) 硬性问题（P0）\n"
        "3) 重要建议（P1）\n"
        "4) 可选优化（P2）\n"
        "5) 引用核查清单（硬编码证据 + 语义判断；含证据链）\n"
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
    ap.add_argument("--precheck", dest="precheck", action="store_true", default=True, help="run deterministic precheck before threads")
    ap.add_argument("--no-precheck", dest="precheck", action="store_false", help="skip deterministic precheck")
    ap.add_argument("--resolve-refs", dest="resolve_refs", action="store_true", default=True, help="fetch reference evidence (title/abstract/optional pdf) during precheck")
    ap.add_argument("--no-resolve-refs", dest="resolve_refs", action="store_false", help="disable reference evidence fetching")
    ap.add_argument("--fetch-pdf", action="store_true", help="when resolving refs, attempt to download OA PDFs and extract a short text excerpt")
    ap.add_argument("--unpaywall-email", default=os.environ.get("UNPAYWALL_EMAIL", ""), help="optional; required by Unpaywall API (or set env UNPAYWALL_EMAIL)")
    ap.add_argument("--timeout-s", type=int, default=20, help="network timeout seconds for reference resolution")
    ap.add_argument("--compile-last", action="store_true", help="run isolated 4-step compile as the last step and update metrics")
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
    # Prevent path injection: run_id must be a simple name.
    if Path(run_id).name != run_id or ("/" in run_id) or ("\\" in run_id):
        print("error: --run-id must be a simple name (no path separators)", file=sys.stderr)
        return 2

    runs_root = Path(args.runs_root)
    # Enforce skill boundary: all artifacts must stay under project_root/.nsfc-qc/
    if runs_root.is_absolute() or ".." in runs_root.parts:
        print("error: --runs-root must be a relative path without '..'", file=sys.stderr)
        return 2
    if not runs_root.parts or runs_root.parts[0] != ".nsfc-qc":
        print("error: --runs-root must start with .nsfc-qc/ to keep artifacts isolated", file=sys.stderr)
        return 2

    run_dir = (project_root / runs_root / run_id).resolve()
    try:
        run_dir.relative_to(project_root.resolve())
    except Exception:
        print("error: resolved run directory escapes project_root", file=sys.stderr)
        return 2
    artifacts = run_dir / "artifacts"
    final_dir = run_dir / "final"
    snapshot_dir = run_dir / "snapshot"
    artifacts.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    # 0) Deterministic precheck (including reference evidence) BEFORE snapshot/threads.
    skill_root = Path(__file__).resolve().parents[1]
    if bool(args.precheck):
        precheck_py = skill_root / "scripts" / "nsfc_qc_precheck.py"
        cmd = [
            sys.executable,
            str(precheck_py),
            "--project-root",
            str(project_root),
            "--main-tex",
            str(Path(args.main_tex)),
            "--out",
            str(artifacts),
            "--timeout-s",
            str(int(args.timeout_s)),
        ]
        if bool(args.resolve_refs):
            cmd.append("--resolve-refs")
            if str(args.unpaywall_email or "").strip():
                cmd += ["--unpaywall-email", str(args.unpaywall_email).strip()]
            if bool(args.fetch_pdf):
                cmd.append("--fetch-pdf")
        log_path = artifacts / "precheck_runner.log"
        with log_path.open("w", encoding="utf-8") as f:
            f.write("$ " + " ".join(cmd) + "\n\n")
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

    # Snapshot is the src_dir for parallel-vibe to keep workspaces clean.
    _copy_snapshot(project_root, snapshot_dir)

    # Make deterministic artifacts readable inside thread workspaces (still read-only).
    qc_in = snapshot_dir / ".nsfc-qc_input"
    qc_in.mkdir(parents=True, exist_ok=True)
    for name in (
        "precheck.json",
        "citations_index.csv",
        "tex_lengths.csv",
        "quote_issues.csv",
        "reference_evidence.jsonl",
        "reference_evidence_summary.json",
    ):
        src = artifacts / name
        if src.exists():
            dst = qc_in / name
            try:
                shutil.copy2(src, dst)
                if dst.is_file():
                    mode = dst.stat().st_mode
                    os.chmod(dst, mode & ~0o222)  # drop write bits
            except Exception:
                continue

    base_prompt = _mk_thread_prompt(main_tex=str(Path(args.main_tex)))
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

    # Materialize standard final outputs skeleton (safe, deterministic).
    materialize_py = skill_root / "scripts" / "materialize_final_outputs.py"
    subprocess.run(
        [
            sys.executable,
            str(materialize_py),
            "--project-root",
            str(project_root),
            "--run-id",
            str(run_id),
            "--runs-root",
            str(args.runs_root),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    # 4) 4-step compile must be the last step (optional).
    if bool(args.compile_last):
        compile_py = skill_root / "scripts" / "nsfc_qc_compile.py"
        cmd2 = [
            sys.executable,
            str(compile_py),
            "--project-root",
            str(project_root),
            "--main-tex",
            str(Path(args.main_tex)),
            "--out",
            str(artifacts),
        ]
        log2 = artifacts / "compile_runner.log"
        with log2.open("w", encoding="utf-8") as f:
            f.write("$ " + " ".join(cmd2) + "\n\n")
            subprocess.run(cmd2, stdout=f, stderr=subprocess.STDOUT, check=False)

    print(str(run_dir))
    return int(p.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
