#!/usr/bin/env python3
"""
Isolated 4-step compile for nsfc-qc.

Goal:
- Compile the proposal in an isolated copy (never touching proposal sources).
- Run the standard 4-step sequence:
    xelatex -> bibtex -> xelatex -> xelatex
- Write all outputs under a user-provided --out directory (recommended: .../.nsfc-qc/runs/<run_id>/artifacts).

Note:
- `nsfc-qc` is positioned as "content quality QC"; compile success is an environment/engineering concern.
- This script is kept as an optional, manual debugging helper and is NOT used by the nsfc-qc runners.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set


def _rel_to_out(out_dir: Path, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(out_dir.resolve()))
    except Exception:
        return str(p)


def _run(cmd: List[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(cmd) + "\n")
        try:
            p = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
            return int(p.returncode)
        except FileNotFoundError:
            f.write(f"[nsfc-qc] command not found: {cmd[0]}\n")
            return 127


def _get_pdf_pages(pdf_path: Path) -> Optional[int]:
    for tool in (["pdfinfo"], ["qpdf", "--show-npages"]):
        try:
            p = subprocess.run(
                tool + [str(pdf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if p.returncode != 0:
                continue
            if tool[0] == "pdfinfo":
                for line in p.stdout.splitlines():
                    if line.lower().startswith("pages:"):
                        return int(line.split(":", 1)[1].strip())
            else:
                return int(p.stdout.strip())
        except Exception:
            continue
    return None


def _compile_isolated(project_root: Path, main_tex_rel: str, out_dir: Path) -> dict:
    compile_dir = out_dir / "compile"
    src = compile_dir / "src"
    build = compile_dir / "build"
    if compile_dir.exists():
        shutil.rmtree(compile_dir)
    compile_dir.mkdir(parents=True, exist_ok=True)

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
            "build",
            "dist",
            "target",
            # In this repo, QC deliveries can be huge and are never needed for isolated compile.
            "QC",
        }
        return {n for n in names if n in bad}

    shutil.copytree(project_root, src, ignore=ignore, dirs_exist_ok=False)
    build.mkdir(parents=True, exist_ok=True)

    main_tex = src / main_tex_rel
    if not main_tex.exists():
        return {
            "enabled": True,
            "ok": False,
            "error": f"main_tex not found in isolated src: {main_tex_rel}",
            "compile_dir": _rel_to_out(out_dir, compile_dir),
            "compile_dir_abs": str(compile_dir),
        }

    base = main_tex.stem
    log = out_dir / "compile.log"
    log_rel = _rel_to_out(out_dir, log)

    missing_tools = [t for t in ("xelatex", "bibtex") if shutil.which(t) is None]
    if missing_tools:
        try:
            log.write_text(
                "[nsfc-qc] TeX toolchain not available; skip compile step.\n"
                f"missing_tools={missing_tools}\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        return {
            "enabled": True,
            "ok": False,
            "missing_tools": missing_tools,
            "error": "TeX toolchain not available; skip compile step",
            "log": log_rel,
            "log_abs": str(log),
            "compile_dir": _rel_to_out(out_dir, compile_dir),
            "compile_dir_abs": str(compile_dir),
        }

    r1 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log)
    r2 = _run(["bibtex", base], cwd=build, log_path=log) if r1 == 0 else 1
    r3 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log) if r2 == 0 else 1
    r4 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log) if r3 == 0 else 1

    pdf_path = build / f"{base}.pdf"
    pages = _get_pdf_pages(pdf_path) if pdf_path.exists() else None
    return {
        "enabled": True,
        "ok": (r4 == 0 and pdf_path.exists()),
        "pdf": _rel_to_out(out_dir, pdf_path) if pdf_path.exists() else "",
        "pdf_abs": str(pdf_path) if pdf_path.exists() else "",
        "pages": pages if pages is not None else None,
        "steps_rc": {"xelatex1": r1, "bibtex": r2, "xelatex2": r3, "xelatex3": r4},
        "log": log_rel,
        "log_abs": str(log),
        "compile_dir": _rel_to_out(out_dir, compile_dir),
        "compile_dir_abs": str(compile_dir),
    }


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--main-tex", default="main.tex", help="relative to project-root")
    ap.add_argument("--out", required=True, help="output directory (recommended: .../.nsfc-qc/runs/<run_id>/artifacts)")
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    info = _compile_isolated(project_root, str(Path(args.main_tex)), out_dir)
    info["generated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json(out_dir / "compile.json", info)

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
