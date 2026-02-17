#!/usr/bin/env python3
"""
Materialize nsfc-qc standard outputs under:
  <run_dir>/final/

This script is deterministic and safe:
- It never modifies proposal sources.
- It only writes/overwrites files under the run's final/ directory.

It can be run even if parallel threads were not executed yet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_parallel_vibe_root(run_dir: Path) -> Optional[Path]:
    pv = run_dir / ".parallel_vibe"
    if pv.exists() and pv.is_dir():
        return pv
    return None


def _collect_thread_results(run_dir: Path) -> List[str]:
    pv = _find_parallel_vibe_root(run_dir)
    if not pv:
        return []
    results: List[str] = []
    for p in pv.rglob("RESULT.md"):
        try:
            results.append(str(p.relative_to(run_dir)))
        except Exception:
            results.append(str(p))
    return sorted(set(results))


def _load_report_template() -> Optional[str]:
    # Resolve template relative to this script.
    skill_root = Path(__file__).resolve().parents[1]
    tpl = skill_root / "templates" / "REPORT_TEMPLATE.md"
    try:
        return tpl.read_text(encoding="utf-8")
    except Exception:
        return None


def _load_page_limit_soft_default() -> int:
    """
    Best-effort parse for config.yaml:
      parameters:
        page_limit_soft:
          default: 30
    Keep this dependency-free (no PyYAML).
    """
    skill_root = Path(__file__).resolve().parents[1]
    cfg = skill_root / "config.yaml"
    try:
        lines = cfg.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return 30

    in_block = False
    block_indent = 0
    for ln in lines:
        # Enter block
        if re.match(r"^\s*page_limit_soft:\s*$", ln):
            in_block = True
            block_indent = len(ln) - len(ln.lstrip(" "))
            continue
        if not in_block:
            continue
        # Exit block if indentation decreases to the same or less than the block key.
        cur_indent = len(ln) - len(ln.lstrip(" "))
        if ln.strip() and cur_indent <= block_indent:
            break
        m = re.match(r"^\s*default:\s*(\d+)\s*$", ln)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return 30
    return 30


REQUIRED_HEADINGS = [
    "执行摘要",
    "范围与只读声明",
    "硬性问题（P0）",
    "重要建议（P1）",
    "可选优化（P2）",
    "引用核查清单",
    "篇幅与结构分布",
    "建议的最小修改路线图",
    "附录：复现信息（命令/路径/产物索引）",
]


def _safe_rel_from(base: Path, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except Exception:
        return str(p)


def _mk_finding(
    *,
    fid: str,
    severity: str,
    category: str,
    path: str,
    anchor: str,
    problem: str,
    evidence: List[dict],
    recommendation: str,
    status: str,
) -> dict:
    return {
        "id": fid,
        "severity": severity,
        "category": category,
        "location": {"path": path, "anchor": anchor},
        "problem": problem,
        "evidence": evidence,
        "recommendation": recommendation,
        "status": status,
    }


def _deterministic_findings(*, precheck: dict, compile_info: dict, artifacts: dict, page_limit_soft: int) -> List[dict]:
    """
    Convert deterministic precheck/compile signals into a baseline findings list.
    This provides a "won't be wrong" floor even if AI threads are unavailable.
    """
    out: List[dict] = []

    citation_stats = precheck.get("citation_stats") or {}
    missing_n = int(citation_stats.get("missing_bibkeys") or 0)
    missing_list = citation_stats.get("missing_bibkeys_list") or []
    incomplete_n = int(citation_stats.get("incomplete_bib_entries") or 0)
    incomplete_list = citation_stats.get("incomplete_bibkeys_list") or []

    # P0: missing bibkeys
    if missing_n > 0:
        keys_preview = ", ".join([str(x) for x in missing_list[:20]])
        detail = f"missing_bibkeys={missing_n}; preview={keys_preview}"
        out.append(
            _mk_finding(
                fid="P0-001",
                severity="P0",
                category="citation",
                path="",
                anchor="precheck.citation_stats",
                problem=f"存在缺失的 bibkey（引用 key 在 .bib 中找不到）：{missing_n} 个。",
                evidence=[
                    {"type": "metric", "detail": detail},
                    {"type": "note", "detail": f"see `{artifacts.get('citations_index_csv','')}` for occurrences preview"},
                ],
                recommendation="补齐缺失 bib 条目或修正 \\cite{...} 中的 bibkey；缺失 bibkey 视为阻塞性问题（P0）。",
                status="open",
            )
        )

    # P1: incomplete bib entries (best-effort)
    if incomplete_n > 0:
        keys_preview = ", ".join([str(x) for x in incomplete_list[:20]])
        out.append(
            _mk_finding(
                fid="P1-001",
                severity="P1",
                category="citation",
                path="",
                anchor="precheck.citation_stats",
                problem=f"存在明显不完整的 BibTeX 条目（缺 title/author/year 等）：{incomplete_n} 个。",
                evidence=[{"type": "metric", "detail": f"incomplete_bib_entries={incomplete_n}; preview={keys_preview}"}],
                recommendation="优先补齐被引用频次高的条目字段（title/author/year/doi/journal）；避免占位符/缺失字段导致评审印象扣分。",
                status="needs_human_review",
            )
        )

    # P1: straight quotes with CJK (typography)
    typography = precheck.get("typography") or {}
    q = (typography.get("straight_double_quotes_with_cjk") or {}) if isinstance(typography, dict) else {}
    qn = int(q.get("count") or 0)
    if qn > 0:
        out.append(
            _mk_finding(
                fid="P1-002",
                severity="P1",
                category="style",
                path="",
                anchor="precheck.typography",
                problem=f"检测到中文内容中使用直引号 \"...\"：{qn} 处（可能影响中文排版与一致性）。",
                evidence=[{"type": "note", "detail": f"see `{artifacts.get('quote_issues_csv','')}` for preview"}],
                recommendation="将中文语境的直引号替换为 TeX 引号：``...''（或按模板规范统一）。",
                status="open",
            )
        )

    # P1/P2: abbreviation conventions (best-effort)
    abbr = precheck.get("abbreviation_conventions") or {}
    abbr_sum = (abbr.get("summary") or {}) if isinstance(abbr, dict) else {}
    by_sev = (abbr_sum.get("issues_by_severity") or {}) if isinstance(abbr_sum, dict) else {}
    abbr_p1 = int(by_sev.get("P1") or 0)
    abbr_p2 = int(by_sev.get("P2") or 0)
    if abbr_p1 > 0:
        out.append(
            _mk_finding(
                fid="P1-003",
                severity="P1",
                category="style",
                path="",
                anchor="precheck.abbreviation_conventions",
                problem=f"检测到“全称+缩写”首次引入可能不规范的情况：P1 级 {abbr_p1} 项（启发式，需人工复核）。",
                evidence=[{"type": "note", "detail": f"see `{artifacts.get('abbreviation_issues_csv','')}` for preview"}],
                recommendation="一般建议：重要概念首次出现写为“中文全称（English Full Name, ABBR）”，后文尽量仅用 ABBR；按 CSV 逐条核对并做最小修改。",
                status="needs_human_review",
            )
        )
    if abbr_p2 > 0:
        out.append(
            _mk_finding(
                fid="P2-003",
                severity="P2",
                category="style",
                path="",
                anchor="precheck.abbreviation_conventions",
                problem=f"检测到缩写规范的可选优化项（如缺中文全称/重复展开）：P2 级 {abbr_p2} 项（启发式）。",
                evidence=[{"type": "note", "detail": f"see `{artifacts.get('abbreviation_issues_csv','')}` for preview"}],
                recommendation="按重要性逐条处理：首次定义尽量完整；后文避免重复“Full Name (ABBR)”展开，保持一致性与节省篇幅。",
                status="open",
            )
        )

    # Compile-based findings (compile can be under precheck.compile or compile.json)
    ci = compile_info or {}
    if bool(ci.get("enabled")):
        if ci.get("missing_tools"):
            out.append(
                _mk_finding(
                    fid="P2-001",
                    severity="P2",
                    category="format",
                    path="",
                    anchor="compile.missing_tools",
                    problem="本机缺少 TeX 工具链，无法完成隔离编译（不一定代表标书无法编译）。",
                    evidence=[{"type": "note", "detail": f"missing_tools={ci.get('missing_tools')} (see `{artifacts.get('compile_log','')}`)"}],
                    recommendation="在具备 TeX 环境（或 Overleaf/CI）中复现编译；若仍失败，再按 compile.log 定位缺文件/宏包等问题。",
                    status="uncertain",
                )
            )
        elif not bool(ci.get("ok")):
            # Keep ID stable: if P0-001 already used, use P0-002.
            fid = "P0-002" if any(x.get("severity") == "P0" for x in out) else "P0-001"
            out.append(
                _mk_finding(
                    fid=fid,
                    severity="P0",
                    category="format",
                    path="",
                    anchor="compile.log",
                    problem="隔离编译失败（需优先定位阻塞错误，如缺图/缺文件/宏包冲突）。",
                    evidence=[{"type": "note", "detail": f"see `{artifacts.get('compile_log','')}` and `{artifacts.get('compile_json','')}`"}],
                    recommendation="优先在 compile.log 中定位第一个 fatal error（常见：缺图文件、路径大小写、未提交 .sty/.cls、bibtex 报错）。",
                    status="open",
                )
            )
        else:
            # Soft page limit hint (optional)
            pages = ci.get("pages")
            if isinstance(pages, int) and pages > 0 and pages > int(page_limit_soft):
                out.append(
                    _mk_finding(
                        fid="P2-002",
                        severity="P2",
                        category="length",
                        path="",
                        anchor="compile.pages",
                        problem=f"PDF 页数偏多（pages={pages}；软约束：原则上不超过 {int(page_limit_soft)} 页）。",
                        evidence=[{"type": "metric", "detail": f"pages={pages}"}],
                        recommendation="优先压缩重复叙述与背景综述；保留核心科学问题/创新点/可行性证据链。",
                        status="needs_human_review",
                    )
                )

    return out


def _render_md_table_rows(findings: List[dict], *, severity: str) -> List[str]:
    rows: List[str] = []
    items = [f for f in findings if str(f.get("severity")) == severity]
    if severity in ("P0", "P1"):
        for f in items:
            loc = f.get("location") or {}
            loc_s = (loc.get("path") or "").strip()
            anchor = (loc.get("anchor") or "").strip()
            if loc_s and anchor:
                loc_s = f"{loc_s}#{anchor}"
            elif anchor and not loc_s:
                loc_s = anchor
            evidence = f.get("evidence") or []
            ev_lines: List[str] = []
            for e in evidence[:2]:
                ev_lines.append(str(e.get("detail") or "").strip())
            ev = "<br>".join([x for x in ev_lines if x]) or ""
            rows.append(
                "| {id} | {loc} | {prob} | {ev} | {rec} |".format(
                    id=str(f.get("id") or ""),
                    loc=loc_s,
                    prob=str(f.get("problem") or ""),
                    ev=ev,
                    rec=str(f.get("recommendation") or ""),
                )
            )
    else:
        for f in items:
            loc = f.get("location") or {}
            loc_s = (loc.get("path") or "").strip()
            anchor = (loc.get("anchor") or "").strip()
            if loc_s and anchor:
                loc_s = f"{loc_s}#{anchor}"
            elif anchor and not loc_s:
                loc_s = anchor
            rows.append(
                "| {id} | {loc} | {prob} | {rec} |".format(
                    id=str(f.get("id") or ""),
                    loc=loc_s,
                    prob=str(f.get("problem") or ""),
                    rec=str(f.get("recommendation") or ""),
                )
            )
    if not rows:
        if severity in ("P0", "P1"):
            rows = ["| - |  |  |  |  |"]
        else:
            rows = ["| - |  |  |  |"]
    return rows


def _inject_table_rows(report_md: str, *, section_title: str, rows: List[str]) -> str:
    lines = report_md.splitlines()
    heading = f"## {section_title}".strip()
    try:
        hi = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return report_md

    # Find table header after heading.
    th = None
    for i in range(hi + 1, min(hi + 80, len(lines))):
        if lines[i].lstrip().startswith("| ID |"):
            th = i
            break
    if th is None or th + 1 >= len(lines):
        return report_md

    sep = th + 1
    if not lines[sep].lstrip().startswith("|---"):
        return report_md

    body_start = sep + 1
    body_end = body_start
    for j in range(body_start, len(lines)):
        if lines[j].strip() == "":
            body_end = j
            break
        if lines[j].startswith("## "):
            body_end = j
            break
    else:
        body_end = len(lines)

    new_lines = lines[:body_start] + rows + lines[body_end:]
    return "\n".join(new_lines) + "\n"


def _validate_report_and_findings(report_text: str, findings_obj: dict) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for h in REQUIRED_HEADINGS:
        if f"## {h}" not in report_text:
            errors.append(f"missing_heading:{h}")

    findings = findings_obj.get("findings") or []
    for f in findings:
        fid = str(f.get("id") or "").strip()
        if not fid:
            errors.append("finding_missing_id")
            continue
        if f"| {fid} |" not in report_text:
            errors.append(f"missing_finding_in_report:{fid}")

    return (len(errors) == 0), errors


def _patch_report_warning(report_path: Path, *, errors: List[str]) -> None:
    try:
        s = report_path.read_text(encoding="utf-8")
    except Exception:
        return
    if "⚠️ 结构校验失败" in s:
        return
    lines = s.splitlines()
    ins = "> ⚠️ 结构校验失败：请先修复报告结构/表格与 findings JSON 的一致性，再作为最终交付。\n"
    ins += "> errors: " + ", ".join(errors[:12]) + ("\n" if len(errors) > 12 else "\n")
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            lines = lines[: i + 1] + ["", ins.rstrip()] + lines[i + 1 :]
            break
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="", help="preferred: the run directory (contains artifacts/final/snapshot)")
    ap.add_argument("--project-root", default="", help="optional; used for metadata only")
    ap.add_argument("--run-id", default="", help="legacy mode: resolve run_dir from project_root + runs_root + run_id")
    ap.add_argument("--runs-root", default=".nsfc-qc/runs", help="legacy mode: relative to project-root")
    ap.add_argument("--deliver-dir", default="", help="optional; for report metadata only")
    ap.add_argument("--overwrite", action="store_true", help="overwrite existing final outputs")
    args = ap.parse_args()

    project_root_resolved = Path(args.project_root).expanduser().resolve() if str(args.project_root or "").strip() else None

    if str(args.run_dir or "").strip():
        run_dir = Path(args.run_dir).expanduser().resolve()
        run_id = run_dir.name
    else:
        # Legacy mode
        if not project_root_resolved:
            print("error: either --run-dir or --project-root must be provided", file=sys.stderr)
            return 2
        run_id = str(args.run_id).strip()
        if Path(run_id).name != run_id or ("/" in run_id) or ("\\" in run_id):
            print("error: --run-id must be a simple name (no path separators)", file=sys.stderr)
            return 2
        runs_root = Path(args.runs_root)
        if runs_root.is_absolute() or ".." in runs_root.parts:
            print("error: --runs-root must be a relative path without '..'", file=sys.stderr)
            return 2
        if not runs_root.parts or runs_root.parts[0] != ".nsfc-qc":
            print("error: --runs-root must start with .nsfc-qc/ to keep artifacts isolated", file=sys.stderr)
            return 2
        run_dir = (project_root_resolved / runs_root / run_id).resolve()

    final_dir = run_dir / "final"
    artifacts_dir = run_dir / "artifacts"
    final_dir.mkdir(parents=True, exist_ok=True)

    precheck = _read_json(artifacts_dir / "precheck.json") or {}
    run_meta = _read_json(artifacts_dir / "run_meta.json") or {}
    compile_json = _read_json(artifacts_dir / "compile.json") or {}

    main_tex = str(run_meta.get("main_tex") or precheck.get("main_tex") or "main.tex")
    execution = str(run_meta.get("execution") or "")

    thread_results = _collect_thread_results(run_dir)
    pv_root = _find_parallel_vibe_root(run_dir)
    pv_main_summary = ""
    if pv_root:
        for p in pv_root.rglob("@main/summary.md"):
            try:
                pv_main_summary = str(p.relative_to(run_dir))
            except Exception:
                pv_main_summary = str(p)
            break

    generated_at = datetime.now().isoformat(timespec="seconds")

    artifacts_rel = {
        "precheck_json": _safe_rel_from(run_dir, artifacts_dir / "precheck.json") if (artifacts_dir / "precheck.json").exists() else "",
        "citations_index_csv": _safe_rel_from(run_dir, artifacts_dir / "citations_index.csv") if (artifacts_dir / "citations_index.csv").exists() else "",
        "tex_lengths_csv": _safe_rel_from(run_dir, artifacts_dir / "tex_lengths.csv") if (artifacts_dir / "tex_lengths.csv").exists() else "",
        "quote_issues_csv": _safe_rel_from(run_dir, artifacts_dir / "quote_issues.csv") if (artifacts_dir / "quote_issues.csv").exists() else "",
        "abbreviation_issues_csv": _safe_rel_from(run_dir, artifacts_dir / "abbreviation_issues.csv") if (artifacts_dir / "abbreviation_issues.csv").exists() else "",
        "reference_evidence_jsonl": _safe_rel_from(run_dir, artifacts_dir / "reference_evidence.jsonl") if (artifacts_dir / "reference_evidence.jsonl").exists() else "",
        "reference_evidence_summary_json": _safe_rel_from(run_dir, artifacts_dir / "reference_evidence_summary.json") if (artifacts_dir / "reference_evidence_summary.json").exists() else "",
        "compile_json": _safe_rel_from(run_dir, artifacts_dir / "compile.json") if (artifacts_dir / "compile.json").exists() else "",
        "compile_log": _safe_rel_from(run_dir, artifacts_dir / "compile.log") if (artifacts_dir / "compile.log").exists() else "",
        "parallel_vibe_summary": pv_main_summary,
        "thread_results": thread_results,
    }

    metrics = {
        "schema_version": 2,
        "run_id": run_id,
        "generated_at": generated_at,
        "project_root": str(project_root_resolved) if project_root_resolved else str(run_meta.get("project_root") or precheck.get("project_root") or ""),
        "deliver_dir": str(Path(args.deliver_dir).expanduser().resolve()) if str(args.deliver_dir or "").strip() else "",
        "main_tex": main_tex,
        "threads": run_meta.get("threads"),
        "execution": execution,
        "paths_base": {
            "run_dir": ".",
            "artifacts_dir": "artifacts",
            "final_dir": "final",
            "snapshot_dir": "snapshot",
        },
        "precheck": {
            "citation_stats": (precheck.get("citation_stats") or {}),
            "compile": (compile_json or precheck.get("compile") or {}),
            "typography": (precheck.get("typography") or {}),
            "abbreviation_conventions": (precheck.get("abbreviation_conventions") or {}),
        },
        "artifacts": artifacts_rel,
        "status": {
            "threads_detected": bool(thread_results),
            "note": "This file is a deterministic aggregation of artifacts; findings are produced by QC threads and/or human review.",
        },
    }

    compile_info_for_findings = compile_json or (precheck.get("compile") or {})
    page_limit_soft = _load_page_limit_soft_default()
    det_findings = _deterministic_findings(
        precheck=precheck,
        compile_info=compile_info_for_findings,
        artifacts=artifacts_rel,
        page_limit_soft=page_limit_soft,
    )

    findings = {
        "schema_version": 1,
        "run_id": run_id,
        "project_root": metrics.get("project_root") or "",
        "generated_at": generated_at,
        "findings": det_findings,
    }

    report_path = final_dir / "nsfc-qc_report.md"
    metrics_path = final_dir / "nsfc-qc_metrics.json"
    findings_path = final_dir / "nsfc-qc_findings.json"
    validation_path = final_dir / "validation.json"

    for p in (report_path, metrics_path, findings_path, validation_path):
        if p.exists() and not bool(args.overwrite):
            print(f"error: output already exists (use --overwrite): {p}", file=sys.stderr)
            return 2

    tpl = _load_report_template() or ""
    if tpl:
        class _SafeDict(dict):
            def __missing__(self, key: str) -> str:  # type: ignore[override]
                return "{" + key + "}"

        report_body = tpl.format_map(
            _SafeDict(
                run_id=run_id,
                project_root=str(metrics.get("project_root") or ""),
                main_tex=main_tex,
                threads=str(run_meta.get("threads") or ""),
                execution=execution,
            )
        )
    else:
        report_body = (
            "# NSFC 标书 QC 报告（nsfc-qc）\n\n"
            f"- run_id: `{run_id}`\n"
            f"- project_root: `{metrics.get('project_root','')}`\n"
            f"- main_tex: `{main_tex}`\n\n"
        )

    # Fill some stats/paths (best-effort).
    deliver_dir_s = str(Path(args.deliver_dir).expanduser().resolve()) if str(args.deliver_dir or "").strip() else ""
    report_body = re.sub(r"^- 产物目录：\s*$", f"- 产物目录：`{run_dir}`", report_body, flags=re.M)
    if deliver_dir_s:
        report_body = re.sub(r"^- 本次 QC 范围：\s*$", f"- 本次 QC 范围：项目只读检查；交付目录：`{deliver_dir_s}`", report_body, flags=re.M)

    cs = precheck.get("citation_stats") or {}
    if cs:
        report_body = re.sub(r"^- 引用总数（去重 bibkey）：\s*$", f"- 引用总数（去重 bibkey）：{cs.get('unique_citations','')}", report_body, flags=re.M)
        report_body = re.sub(r"^- 缺失 bibkey：\s*$", f"- 缺失 bibkey：{cs.get('missing_bibkeys','')}", report_body, flags=re.M)

    pages = compile_info_for_findings.get("pages") if isinstance(compile_info_for_findings, dict) else None
    if isinstance(pages, int) and pages > 0:
        report_body = re.sub(r"^- PDF 页数（如可得）：\s*$", f"- PDF 页数（如可得）：{pages}", report_body, flags=re.M)

    # Inject deterministic findings into P0/P1/P2 tables.
    report_body = _inject_table_rows(report_body, section_title="硬性问题（P0）", rows=_render_md_table_rows(det_findings, severity="P0"))
    report_body = _inject_table_rows(report_body, section_title="重要建议（P1）", rows=_render_md_table_rows(det_findings, severity="P1"))
    report_body = _inject_table_rows(report_body, section_title="可选优化（P2）", rows=_render_md_table_rows(det_findings, severity="P2"))

    idx_lines: List[str] = []
    idx_lines.append("\n## 产物索引（自动生成）\n")
    idx_lines.append(f"- 生成时间：{generated_at}")
    if pv_main_summary:
        idx_lines.append(f"- parallel-vibe 汇总：`{pv_main_summary}`")
    if thread_results:
        idx_lines.append("- thread RESULT.md：")
        for r in thread_results[:50]:
            idx_lines.append(f"  - `{r}`")
        if len(thread_results) > 50:
            idx_lines.append(f"  - ...(and {len(thread_results) - 50} more)")
    else:
        idx_lines.append("- thread RESULT.md：未检测到（可能尚未运行 threads）")
    idx_lines.append("\n> 提示：本报告包含“确定性预检→findings”的底线结论；更深入的问题应结合 threads 汇总与人工复核补齐。\n")

    report_path.write_text(report_body.rstrip() + "\n" + "\n".join(idx_lines) + "\n", encoding="utf-8")
    _write_json(metrics_path, metrics)
    _write_json(findings_path, findings)

    ok, errors = _validate_report_and_findings(report_path.read_text(encoding="utf-8"), findings)
    _write_json(validation_path, {"ok": ok, "errors": errors, "generated_at": generated_at})
    if not ok:
        _patch_report_warning(report_path, errors=errors)

    print(str(final_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
