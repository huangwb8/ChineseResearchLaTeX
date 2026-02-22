#!/usr/bin/env python3
"""
Run nsfc-qc multi-thread QC via parallel-vibe.

This script supports two output layouts:
1) Legacy (default): all artifacts under <project_root>/.nsfc-qc/runs/<run_id>/
2) Workspace-driven: all artifacts under <workspace_dir>/<runs_root>/<run_id>/

This script:
- Creates a run directory (see above) with subfolders: artifacts/, final/, snapshot/
- (Default) Runs deterministic precheck and reference evidence collection into artifacts/
- Creates an isolated snapshot of the proposal (read-only) for thread workspaces
- Copies key artifacts into snapshot/.nsfc-qc/input/ for threads to read
- Generates a deterministic parallel-vibe plan.json with N identical QC threads
- Executes parallel-vibe with --out-dir set to the run directory (so .parallel_vibe lives under the run)

Note: This script does NOT modify proposal source files. It only writes into the run directory.
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


def _is_safe_rel_path(p: Path) -> bool:
    return (not p.is_absolute()) and (".." not in p.parts)


def _resolve_unique_run_dir(*, base_dir: Path, runs_root: Path, run_id: str) -> tuple[Path, str]:
    """
    Resolve <base_dir>/<runs_root>/<run_id> while preventing directory traversal.
    If the target directory already exists, auto-suffix with r1/r2/... to avoid overwriting.
    """
    base_dir = base_dir.expanduser().resolve()
    runs_root = Path(str(runs_root))
    if not _is_safe_rel_path(runs_root):
        raise ValueError("runs_root must be a relative path without '..'")

    # Prevent path injection: run_id must be a simple name.
    if Path(run_id).name != run_id or ("/" in run_id) or ("\\" in run_id):
        raise ValueError("run_id must be a simple name (no path separators)")

    def mk(rid: str) -> Path:
        rd = (base_dir / runs_root / rid).resolve()
        rd.relative_to(base_dir)  # will raise if escapes
        return rd

    run_dir = mk(run_id)
    if not run_dir.exists():
        return run_dir, run_id

    for i in range(1, 100):
        rid2 = f"{run_id}r{i}"
        rd2 = mk(rid2)
        if not rd2.exists():
            return rd2, rid2

    raise RuntimeError("failed to pick a unique run directory after 99 attempts")


def _copy_snapshot(project_root: Path, snapshot_dir: Path) -> None:
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)

    # Minimize snapshot size aggressively: only copy sources needed for "read-only QC".
    # We intentionally do NOT copy compiled artifacts, figures, fonts, templates, etc.
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    bad_dirs = {
        ".git",
        ".nsfc-qc",
        ".parallel_vibe",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "target",
        # Common in this repo: previous QC deliveries can be huge; never snapshot them.
        "QC",
    }

    for root, dirs, files in os.walk(project_root):
        # Prune large / irrelevant directories early to avoid expensive traversal.
        dirs[:] = [d for d in dirs if d not in bad_dirs]
        for fn in files:
            ext = Path(fn).suffix.lower()
            if ext not in {".tex", ".bib"}:
                continue
            src = Path(root) / fn
            try:
                rel = src.relative_to(project_root)
            except Exception:
                continue
            dst = snapshot_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
            except Exception:
                continue

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
        "- 注意：snapshot 是“最小化副本”，通常只包含 `*.tex/*.bib` 与 `./.nsfc-qc/input/` 证据包；缺失的图片/模板/字体/编译产物不影响你做文本 QC。\n"
        "- 禁止修改任何已有文件（尤其是 .tex/.bib/.cls/.sty）。把建议写进 RESULT.md。\n"
        "- 禁止访问父目录（..）与任何绝对路径写入。\n"
        "- 不编造引用与论文内容；无法确定时标记为 uncertain，并给出可复核路径。\n\n"
        "证据包（只读，可用于“引用真伪/错引风险”的语义核查）：\n"
        "- `./.nsfc-qc/input/precheck.json`\n"
        "- `./.nsfc-qc/input/citations_index.csv`\n"
        "- `./.nsfc-qc/input/abbreviation_issues_summary.json`（缩写规范预检摘要：建议先读，快速定位高优先级项）\n"
        "- `./.nsfc-qc/input/abbreviation_issues.csv`（缩写规范预检明细：按行定位；注意过滤 LaTeX 标签/数学变量等误报）\n"
        "- `./.nsfc-qc/input/terminology_issues_summary.json`（术语一致性预检摘要：英文术语大小写/连字符变体）\n"
        "- `./.nsfc-qc/input/terminology_issues.csv`（术语一致性预检明细：按 normalized_key 分组，列出所有变体）\n"
        "- `./.nsfc-qc/input/reference_evidence.jsonl`（硬编码抓取到的题目/摘要/可选 PDF 片段 + 标书内引用上下文）\n\n"
        “缩略语规范（必检，独立小节输出）：\n”
        “- 以 `abbreviation_issues_summary.json`/`abbreviation_issues.csv` 为起点，逐条核对。\n”
        “- 对 P1（`bare_first_use`/`missing_english_full`）：确认是否为重要专业术语；首次出现建议采用”中文全称（English Full Name, ABBR）”。\n”
        “- 对 P2（`missing_chinese_full`/`repeated_expansion`）：确认是否确实缺中文全称/是否确实重复展开。\n”
        “- 过滤误报：LaTeX 标签（如 `fig:ABC`）、图表编号、数学变量、bibkey/label 不是缩写。\n”
        “- 你必须在 RESULT.md 的「3) 重要建议（P1）」中写一个二级标题：`### 缩略语规范`，并按 `文件:行号` 给出可执行建议（只写建议，不改文件）。\n\n”
        “术语一致性（必检，独立小节输出）：\n”
        “- 以 `terminology_issues_summary.json`/`terminology_issues.csv` 为起点，逐条核对。\n”
        “- 每条 `term_variant` 问题列出了同一概念的多种英文写法（大小写/连字符差异），请判断：\n”
        “  - 是否为真正的不一致（而非专有名词的合理变体，如 “T cell” vs “T-cell” 在不同语境下均可接受）。\n”
        “  - 建议统一使用哪种形式（通常选出现次数最多的）。\n”
        “- 过滤误报：不同语境下合理的大小写差异（如句首大写）不算不一致。\n”
        “- 你必须在 RESULT.md 的「4) 可选优化（P2）」中写一个二级标题：`### 术语一致性`，并给出可执行建议（只写建议，不改文件）。\n\n”
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
    ap.add_argument("--workspace-dir", default="", help="optional; if set, all outputs go under this directory")
    ap.add_argument(
        "--runs-root",
        default="",
        help="relative root for runs; defaults to '.nsfc-qc/runs' (legacy) or 'runs' (when --workspace-dir is set)",
    )
    ap.add_argument("--plan-only", action="store_true", help="only write plan + snapshot; do not run threads")
    ap.add_argument("--precheck", dest="precheck", action="store_true", default=True, help="run deterministic precheck before threads")
    ap.add_argument("--no-precheck", dest="precheck", action="store_false", help="skip deterministic precheck")
    ap.add_argument("--resolve-refs", dest="resolve_refs", action="store_true", default=True, help="fetch reference evidence (title/abstract/optional pdf) during precheck")
    ap.add_argument("--no-resolve-refs", dest="resolve_refs", action="store_false", help="disable reference evidence fetching")
    ap.add_argument("--fetch-pdf", action="store_true", help="when resolving refs, attempt to download OA PDFs and extract a short text excerpt")
    ap.add_argument("--unpaywall-email", default=os.environ.get("UNPAYWALL_EMAIL", ""), help="optional; required by Unpaywall API (or set env UNPAYWALL_EMAIL)")
    ap.add_argument("--timeout-s", type=int, default=20, help="network timeout seconds for reference resolution")
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

    requested_run_id = args.run_id.strip() or _now_run_id()

    workspace_dir = Path(str(args.workspace_dir or "")).expanduser()
    base_dir: Path
    if str(args.workspace_dir or "").strip():
        base_dir = workspace_dir.resolve()
        if not base_dir.exists():
            base_dir.mkdir(parents=True, exist_ok=True)
        runs_root = Path(args.runs_root.strip() or "runs")
    else:
        base_dir = project_root
        runs_root = Path(args.runs_root.strip() or ".nsfc-qc/runs")
        # Legacy safety: keep artifacts isolated under project_root/.nsfc-qc/ unless workspace-dir is used.
        if not runs_root.parts or runs_root.parts[0] != ".nsfc-qc":
            print("error: --runs-root must start with .nsfc-qc/ unless --workspace-dir is set", file=sys.stderr)
            return 2

    try:
        run_dir, run_id = _resolve_unique_run_dir(base_dir=base_dir, runs_root=runs_root, run_id=requested_run_id)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
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
    qc_in = snapshot_dir / ".nsfc-qc" / "input"
    qc_in.mkdir(parents=True, exist_ok=True)
    for name in (
        "precheck.json",
        "citations_index.csv",
        "tex_lengths.csv",
        "quote_issues.csv",
        "abbreviation_issues.csv",
        "abbreviation_issues_summary.json",
        "terminology_issues.csv",
        "terminology_issues_summary.json",
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
        "requested_run_id": requested_run_id,
        "project_root": str(project_root),
        "main_tex": str(Path(args.main_tex)),
        "threads": int(args.threads),
        "execution": args.execution,
        "runner_type": args.runner_type,
        "runner_profile": args.runner_profile,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "artifacts_dir": str(artifacts),
        "final_dir": str(final_dir),
        "workspace_dir": str(base_dir) if base_dir != project_root else "",
        "runs_root": str(runs_root),
    }
    _write_json(artifacts / "run_meta.json", meta)

    pv = _find_parallel_vibe_script()
    if not pv:
        (final_dir / "parallel_vibe_unavailable.txt").write_text(
            "parallel-vibe script not found. See skills/nsfc-qc/SKILL.md for downgrade strategy.\n",
            encoding="utf-8",
        )
        # Still materialize deterministic final outputs (report/metrics/findings/validation).
        materialize_py = skill_root / "scripts" / "materialize_final_outputs.py"
        subprocess.run(
            [
                sys.executable,
                str(materialize_py),
                "--run-dir",
                str(run_dir),
                "--project-root",
                str(project_root),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        print(str(run_dir))
        return 0

    if args.plan_only:
        # Create deterministic final outputs even in plan-only mode.
        materialize_py = skill_root / "scripts" / "materialize_final_outputs.py"
        subprocess.run(
            [
                sys.executable,
                str(materialize_py),
                "--run-dir",
                str(run_dir),
                "--project-root",
                str(project_root),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
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
        [sys.executable, str(materialize_py), "--run-dir", str(run_dir), "--project-root", str(project_root)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    print(str(run_dir))
    return int(p.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
