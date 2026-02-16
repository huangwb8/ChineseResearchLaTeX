#!/usr/bin/env python3
"""
Deterministic, read-only precheck for NSFC LaTeX proposals.

- Extracts citations and checks bibkey existence.
- Produces rough length metrics (per tex file and overall).
- Optionally compiles in an isolated copy to get PDF page count.

All outputs must be written under a user-provided --out directory (recommended inside .nsfc-qc/).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


TEX_INPUT_RE = re.compile(r"\\(input|include)\s*\{([^}]+)\}")
TEX_BIB_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
TEX_CITE_RE = re.compile(
    r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}"
)
TEX_COMMENT_RE = re.compile(r"(^|[^\\])%.*?$", flags=re.M)

LATEX_CMD_RE = re.compile(r"\\[a-zA-Z@]+(\*?)\s*(\[[^\]]*\])?\s*(\{[^}]*\})?")

BIB_ENTRY_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _strip_comments(s: str) -> str:
    # Keep escaped percent (\\%) intact.
    return TEX_COMMENT_RE.sub(r"\1", s)


def _norm_tex_path(raw: str) -> str:
    raw = raw.strip()
    # Allow \input{a/b} without .tex suffix
    return raw if raw.lower().endswith(".tex") else raw + ".tex"


def _resolve_tex_path(base_dir: Path, raw: str) -> Optional[Path]:
    rel = Path(_norm_tex_path(raw))
    # LaTeX allows paths without extension and without leading ./.
    candidates = [
        base_dir / rel,
        base_dir / raw,  # if raw already contains extension
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def _find_included_tex_files(main_tex: Path) -> List[Path]:
    seen: Set[Path] = set()
    order: List[Path] = []

    def walk(p: Path) -> None:
        rp = p.resolve()
        if rp in seen:
            return
        seen.add(rp)
        order.append(p)
        try:
            s = _strip_comments(_read_text(p))
        except Exception:
            return
        for m in TEX_INPUT_RE.finditer(s):
            inc = m.group(2).strip()
            # Prefer resolving relative to the including file directory.
            inc_path = _resolve_tex_path(p.parent, inc) or _resolve_tex_path(main_tex.parent, inc)
            if inc_path:
                walk(inc_path)

    walk(main_tex)
    return order


def _find_bib_files(tex_files: Iterable[Path], project_root: Path) -> List[Path]:
    # Prefer explicit \bibliography{...} declarations.
    bib_names: List[str] = []
    for p in tex_files:
        try:
            s = _strip_comments(_read_text(p))
        except Exception:
            continue
        for m in TEX_BIB_RE.finditer(s):
            bib_names.extend([x.strip() for x in m.group(1).split(",") if x.strip()])

    bib_paths: List[Path] = []
    if bib_names:
        for name in bib_names:
            name = name.strip()
            if not name:
                continue
            # BibTeX allows \bibliography{references/foo,bar}
            rel = Path(name)
            if rel.suffix.lower() != ".bib":
                rel = rel.with_suffix(".bib")
            # Search common locations.
            candidates = [
                project_root / rel,
                project_root / "references" / rel.name,
                project_root / rel.name,
            ]
            for c in candidates:
                if c.exists() and c.is_file():
                    bib_paths.append(c)
                    break

    # Fallback: any .bib under project_root/references
    if not bib_paths:
        refs = project_root / "references"
        if refs.exists():
            bib_paths.extend(sorted(refs.glob("*.bib")))
    return bib_paths


def _extract_citations(tex_files: Iterable[Path], *, project_root: Path) -> Dict[str, List[str]]:
    # bibkey -> list of "path:line" occurrences (first N kept per file scan)
    occ: Dict[str, List[str]] = {}
    for p in tex_files:
        try:
            raw = _strip_comments(_read_text(p))
        except Exception:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            for m in TEX_CITE_RE.finditer(line):
                keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
                for k in keys:
                    occ.setdefault(k, [])
                    if len(occ[k]) < 50:
                        try:
                            rel = p.relative_to(project_root)
                            occ[k].append(f"{rel}:{i}")
                        except Exception:
                            occ[k].append(f"{p}:{i}")
    return occ


def _parse_bib_keys(bib_files: Iterable[Path]) -> Dict[str, Dict[str, str]]:
    # key -> simple field map (best-effort). No external dependencies.
    out: Dict[str, Dict[str, str]] = {}
    field_re = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9_-]*)\s*=\s*[\{\"](.+?)[\}\"]\s*,?\s*$")
    for bf in bib_files:
        try:
            s = _read_text(bf)
        except Exception:
            continue
        current_key: Optional[str] = None
        current_fields: Dict[str, str] = {}
        for line in s.splitlines():
            m_key = BIB_ENTRY_KEY_RE.search(line)
            if m_key:
                # flush previous
                if current_key:
                    out[current_key] = current_fields
                current_key = m_key.group(1).strip()
                current_fields = {"__file__": str(bf)}
                continue
            if current_key:
                m_f = field_re.match(line)
                if m_f:
                    k = m_f.group(1).lower()
                    v = m_f.group(2).strip()
                    if k not in current_fields:
                        current_fields[k] = v
            if current_key and line.strip().endswith("}"):
                # naive entry end
                pass
        if current_key:
            out[current_key] = current_fields
    return out


def _rough_text_metrics(tex_files: Iterable[Path]) -> Dict[str, Dict[str, int]]:
    metrics: Dict[str, Dict[str, int]] = {}
    for p in tex_files:
        try:
            s = _strip_comments(_read_text(p))
        except Exception:
            continue
        # Remove common LaTeX commands to approximate natural language length.
        s2 = LATEX_CMD_RE.sub(" ", s)
        # Drop braces and TeX special chars
        s2 = re.sub(r"[{}\\\\$&#_^~]", " ", s2)
        # Count CJK characters and ASCII words separately.
        cjk = len(re.findall(r"[\u4e00-\u9fff]", s2))
        words = len(re.findall(r"[A-Za-z0-9]+", s2))
        chars = len(re.sub(r"\s+", "", s2))
        metrics[str(p)] = {"cjk_chars": cjk, "ascii_words": words, "non_space_chars": chars}
    return metrics


def _run(cmd: List[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(cmd) + "\n")
        p = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
        return int(p.returncode)


def _get_pdf_pages(pdf_path: Path) -> Optional[int]:
    # Try pdfinfo (poppler) first, then qpdf.
    for tool in (["pdfinfo"], ["qpdf", "--show-npages"]):
        try:
            if tool[0] == "pdfinfo":
                p = subprocess.run(
                    tool + [str(pdf_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if p.returncode == 0:
                    for line in p.stdout.splitlines():
                        if line.lower().startswith("pages:"):
                            return int(line.split(":", 1)[1].strip())
            else:
                p = subprocess.run(
                    tool + [str(pdf_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if p.returncode == 0:
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
        # Keep this conservative; only avoid obvious junk.
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
        }
        return {n for n in names if n in bad}

    shutil.copytree(project_root, src, ignore=ignore, dirs_exist_ok=False)
    build.mkdir(parents=True, exist_ok=True)

    main_tex = src / main_tex_rel
    if not main_tex.exists():
        return {"enabled": True, "ok": False, "error": f"main_tex not found in isolated src: {main_tex_rel}"}

    base = main_tex.stem
    log = out_dir / "compile.log"
    r1 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log)
    # bibtex must run in build dir on the generated .aux
    r2 = _run(["bibtex", base], cwd=build, log_path=log) if r1 == 0 else 1
    r3 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log) if r2 == 0 else 1
    r4 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log) if r3 == 0 else 1

    pdf_path = build / f"{base}.pdf"
    pages = _get_pdf_pages(pdf_path) if pdf_path.exists() else None
    return {
        "enabled": True,
        "ok": (r4 == 0 and pdf_path.exists()),
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "pages": pages if pages is not None else None,
        "steps_rc": {"xelatex1": r1, "bibtex": r2, "xelatex2": r3, "xelatex3": r4},
        "log": str(log),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--main-tex", default="main.tex", help="relative to project-root")
    ap.add_argument("--out", required=True, help="output directory (recommended: .nsfc-qc/.../artifacts)")
    ap.add_argument("--compile", action="store_true", help="compile in an isolated copy to estimate PDF page count")
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    main_tex = (project_root / args.main_tex).resolve()
    if not main_tex.exists():
        print(f"error: main tex not found: {project_root / args.main_tex}", file=sys.stderr)
        return 2

    tex_files = _find_included_tex_files(main_tex)
    bib_files = _find_bib_files(tex_files, project_root)
    citations = _extract_citations(tex_files, project_root=project_root)
    bib_entries = _parse_bib_keys(bib_files)
    lengths = _rough_text_metrics(tex_files)

    cited_keys = sorted(citations.keys())
    missing = [k for k in cited_keys if k not in bib_entries]

    # Detect obviously incomplete bib entries (best-effort).
    incomplete: List[str] = []
    for k, f in bib_entries.items():
        # Minimal fields in BibTeX vary by entry type, but these are common.
        if not f.get("title") or not (f.get("author") or f.get("editor")) or not f.get("year"):
            incomplete.append(k)

    compile_info = {"enabled": False}
    if bool(args.compile):
        compile_info = _compile_isolated(project_root, args.main_tex, out_dir)

    precheck = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "main_tex": str(Path(args.main_tex)),
        "tex_files": [
            str(p.relative_to(project_root)) if _is_within(project_root, p) else str(p)
            for p in tex_files
        ],
        "bib_files": [
            str(p.relative_to(project_root)) if _is_within(project_root, p) else str(p)
            for p in bib_files
        ],
        "citation_stats": {
            "unique_citations": len(cited_keys),
            "missing_bibkeys": len(missing),
            "missing_bibkeys_list": missing[:200],
            "incomplete_bib_entries": len(incomplete),
            "incomplete_bibkeys_list": incomplete[:200],
        },
        "lengths": {
            "per_tex_file": {
                str(Path(k).relative_to(project_root)) if str(k).startswith(str(project_root)) else str(k): v
                for k, v in lengths.items()
            }
        },
        "compile": compile_info,
    }

    (out_dir / "precheck.json").write_text(json.dumps(precheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # citations index CSV
    with (out_dir / "citations_index.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bibkey", "status", "occurrences_n", "occurrences_preview"])
        for k in cited_keys:
            occ_list = citations.get(k, [])
            status = "ok" if k in bib_entries else "missing"
            w.writerow([k, status, len(occ_list), " | ".join(occ_list[:5])])

    # section/file lengths CSV (file-level)
    with (out_dir / "tex_lengths.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "cjk_chars", "ascii_words", "non_space_chars"])
        for p in sorted(lengths.keys()):
            rel = str(Path(p).relative_to(project_root)) if str(p).startswith(str(project_root)) else str(p)
            m = lengths[p]
            w.writerow([rel, m["cjk_chars"], m["ascii_words"], m["non_space_chars"]])

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
