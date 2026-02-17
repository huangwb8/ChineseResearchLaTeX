#!/usr/bin/env python3
"""
High-level runner for nsfc-qc with "deliver dir + sidecar workspace" layout.

Default layout (when --deliver-dir not provided):
  <project_root>/QC/<run_id>/               (deliver-dir; for humans)
  <project_root>/QC/<run_id>/.nsfc-qc/      (workspace-dir; for reproducibility)

All QC intermediate products (runs/, snapshot/, .parallel_vibe/, artifacts) go to workspace-dir.
Deliver-dir receives a copy of final outputs for review.

This script is deterministic and does NOT modify proposal sources.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


# Accept both minute-level (vYYYYMMDDHHMM) and second-level (vYYYYMMDDHHMMSS) ids.
RUN_ID_RE = re.compile(r"^v\d{12}(?:\d{2})?(?:r\d+)?$")


def _now_run_id() -> str:
    return datetime.now().strftime("v%Y%m%d%H%M%S")


def _ensure_unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    base = path.name
    parent = path.parent
    for i in range(1, 100):
        # Keep hidden directories hidden (e.g. ".nsfc-qc" -> ".nsfc-qc.r1").
        suffix = f".r{i}" if base.startswith(".") else f"r{i}"
        cand = parent / f"{base}{suffix}"
        if not cand.exists():
            return cand
    raise RuntimeError("failed to pick a unique deliver/workspace directory after 99 attempts")


def _infer_run_id_from_deliver_dir(deliver_dir: Path) -> str:
    name = deliver_dir.name.strip()
    if RUN_ID_RE.match(name):
        return name
    return _now_run_id()


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _run_cmd(cmd: list[str]) -> Tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return int(p.returncode), (p.stdout or "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--main-tex", default="main.tex")
    ap.add_argument("--deliver-dir", default="", help="deliver directory (recommended: .../QC/vYYYYMMDDHHMMSS)")
    ap.add_argument("--workspace-dir", default="", help="workspace directory (recommended: <deliver-dir>/.nsfc-qc)")
    ap.add_argument("--threads", type=int, default=5)
    ap.add_argument("--execution", choices=["serial", "parallel"], default="serial")
    ap.add_argument("--max-parallel", type=int, default=3)
    ap.add_argument("--runner-type", choices=["codex", "claude"], default="codex")
    ap.add_argument("--runner-profile", choices=["fast", "default", "deep"], default="deep")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--no-precheck", dest="precheck", action="store_false", default=True)
    ap.add_argument("--no-resolve-refs", dest="resolve_refs", action="store_false", default=True)
    ap.add_argument("--fetch-pdf", action="store_true")
    ap.add_argument("--unpaywall-email", default=os.environ.get("UNPAYWALL_EMAIL", ""))
    ap.add_argument("--timeout-s", type=int, default=20)
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists():
        print(f"error: project_root not found: {project_root}", file=sys.stderr)
        return 2
    main_tex = project_root / args.main_tex
    if not main_tex.exists():
        print(f"error: main_tex not found: {main_tex}", file=sys.stderr)
        return 2

    skill_root = Path(__file__).resolve().parents[1]
    run_parallel_py = skill_root / "scripts" / "run_parallel_qc.py"
    materialize_py = skill_root / "scripts" / "materialize_final_outputs.py"

    # Derive deliver/workspace directories.
    if str(args.deliver_dir or "").strip():
        deliver_dir = Path(args.deliver_dir).expanduser().resolve()
        run_id = _infer_run_id_from_deliver_dir(deliver_dir)
    else:
        run_id = _now_run_id()
        deliver_dir = (project_root / "QC" / run_id).resolve()

    deliver_dir = _ensure_unique_dir(deliver_dir)
    # If we auto-suffixed deliver dir, keep run_id in sync when the directory name is a run_id-like token.
    if RUN_ID_RE.match(deliver_dir.name):
        run_id = deliver_dir.name

    if str(args.workspace_dir or "").strip():
        workspace_dir = Path(args.workspace_dir).expanduser().resolve()
        workspace_dir = _ensure_unique_dir(workspace_dir)
    else:
        workspace_dir = _ensure_unique_dir(deliver_dir / ".nsfc-qc")

    deliver_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(run_parallel_py),
        "--project-root",
        str(project_root),
        "--main-tex",
        str(Path(args.main_tex)),
        "--workspace-dir",
        str(workspace_dir),
        "--runs-root",
        "runs",
        "--run-id",
        run_id,
        "--threads",
        str(int(args.threads)),
        "--execution",
        str(args.execution),
        "--max-parallel",
        str(int(args.max_parallel)),
        "--runner-type",
        str(args.runner_type),
        "--runner-profile",
        str(args.runner_profile),
        "--timeout-s",
        str(int(args.timeout_s)),
    ]
    if bool(args.plan_only):
        cmd.append("--plan-only")
    if not bool(args.precheck):
        cmd.append("--no-precheck")
    if not bool(args.resolve_refs):
        cmd.append("--no-resolve-refs")
    if bool(args.fetch_pdf):
        cmd.append("--fetch-pdf")
    if str(args.unpaywall_email or "").strip():
        cmd += ["--unpaywall-email", str(args.unpaywall_email).strip()]

    rc, out = _run_cmd(cmd)
    # run_parallel_qc prints run_dir path (last line).
    run_dir_str = (out.strip().splitlines()[-1] if out.strip().splitlines() else "").strip()
    run_dir = Path(run_dir_str).expanduser().resolve() if run_dir_str else None
    if not run_dir or not run_dir.exists():
        # Best-effort: try to materialize using expected run_dir.
        expected = (workspace_dir / "runs" / run_id).resolve()
        expected.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, str(materialize_py), "--run-dir", str(expected), "--project-root", str(project_root), "--deliver-dir", str(deliver_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        run_dir = expected

    # Re-materialize with deliver metadata (safe overwrite of final only if missing).
    subprocess.run(
        [sys.executable, str(materialize_py), "--run-dir", str(run_dir), "--project-root", str(project_root), "--deliver-dir", str(deliver_dir), "--overwrite"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    final_dir = run_dir / "final"

    # Copy deliverables (final outputs).
    _copy_if_exists(final_dir / "nsfc-qc_report.md", deliver_dir / "nsfc-qc_report.md")
    _copy_if_exists(final_dir / "nsfc-qc_metrics.json", deliver_dir / "nsfc-qc_metrics.json")
    _copy_if_exists(final_dir / "nsfc-qc_findings.json", deliver_dir / "nsfc-qc_findings.json")
    _copy_if_exists(final_dir / "validation.json", deliver_dir / "validation.json")

    # Write a small manifest for portability.
    try:
        ws_rel = os.path.relpath(str(workspace_dir), str(deliver_dir))
    except Exception:
        ws_rel = str(workspace_dir)
    manifest = {
        "run_id": run_dir.name,
        "deliver_dir": str(deliver_dir),
        "workspace_dir": str(workspace_dir),
        "workspace_dir_rel_from_deliver": ws_rel,
        "run_dir": str(run_dir),
        "project_root": str(project_root),
        "note": "deliver_dir contains copied final outputs; full reproducibility data (runs/snapshot/artifacts/.parallel_vibe/final) is in workspace_dir.",
    }
    (deliver_dir / "nsfc-qc_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Forward runner output for debugging.
    if out.strip():
        (deliver_dir / "runner.log").write_text(out, encoding="utf-8")

    print(str(deliver_dir))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
