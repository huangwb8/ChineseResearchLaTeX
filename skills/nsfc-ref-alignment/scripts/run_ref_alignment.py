#!/usr/bin/env python3
"""
run_ref_alignment.py - nsfc-ref-alignment 的确定性入口（只读）

脚本职责（确定性）：
- 解析 NSFC 标书 LaTeX 项目（多文件 \input/\include）
- 抽取所有引用（\cite{...} 等）与其句子级上下文
- 发现并解析 .bib（\bibliography / \addbibresource）
- 进行确定性完整性检查：缺失 bibkey / 重复条目 / 字段缺失 / DOI 格式
- 可选：在线核验 DOI（Crossref/OpenAlex，只做存在性与元信息粗比对；失败降级）
- 生成：
  - 中间产物：{project_root}/.nsfc-ref-alignment/run_{timestamp}/...
  - 交付报告（确定性草稿）：{report_dir}/NSFC-REF-ALIGNMENT-v{timestamp}.md

非职责（启发式/AI）：
- 判断“引用-语义是否真的匹配”
- 给出“改正文/改 bib”的具体改动（默认禁止自动修改）
这些由宿主 AI 在执行 nsfc-ref-alignment skill 时完成。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bib_utils import BibEntry, merge_bib_entries, required_field_issues, validate_doi
from latex_scanner import CitationHit, discover_bib_files, discover_tex_dependency_tree, extract_citations
from online_verify import check_doi_online
from report_utils import build_deterministic_report_md, write_citations_csv, write_json
from runtime_utils import load_config, relpath_safe, utc_timestamp_compact


def _safe_get(cfg: Dict[str, Any], path: List[str], default: Any) -> Any:
    cur: Any = cfg
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _entry_digest(e: BibEntry, project_root: Path, limits: Dict[str, int]) -> Dict[str, Any]:
    max_title = int(limits.get("max_title_chars", 400) or 400)
    max_abs = int(limits.get("max_bib_abstract_chars", 1200) or 1200)
    title = e.get("title")
    abstract = e.get("abstract")
    if len(title) > max_title:
        title = title[:max_title].rstrip() + " …"
    if len(abstract) > max_abs:
        abstract = abstract[:max_abs].rstrip() + " …"
    return {
        "bibkey": e.key,
        "entry_type": e.entry_type,
        "source": relpath_safe(Path(e.source), project_root),
        "title": title,
        "author": e.get("author"),
        "year": e.get("year") or e.get("date"),
        "venue": e.get("journal") or e.get("booktitle") or e.get("publisher"),
        "doi": e.get("doi"),
        "url": e.get("url"),
        "abstract": abstract,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True, help="NSFC 标书项目根目录（如 projects/NSFC_General）")
    ap.add_argument("--main-tex", default="main.tex", help="入口 tex（相对 project_root），默认 main.tex")
    ap.add_argument("--report-dir", default="references", help="交付报告输出目录（相对当前工作目录），默认 ./references")
    ap.add_argument("--prepare", action="store_true", help="生成结构化输入与确定性报告（默认执行）")
    ap.add_argument("--verify-online", action="store_true", help="在线核验 DOI（Crossref/OpenAlex）")
    args = ap.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    cfg, cfg_warnings = load_config(skill_root)

    project_root = Path(args.project_root).expanduser().resolve()
    main_tex = (project_root / args.main_tex).resolve()
    report_dir = Path(args.report_dir).expanduser().resolve()

    run_id = utc_timestamp_compact()  # seconds
    runs_root = project_root / ".nsfc-ref-alignment"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_dir = None
    # Use atomic mkdir to avoid collisions (even under concurrent runs).
    for i in range(1, 100):
        suffix = "" if i == 1 else f"-{i}"
        cand = runs_root / f"run_{run_id}{suffix}"
        try:
            cand.mkdir(parents=False, exist_ok=False)
            run_dir = cand
            break
        except FileExistsError:
            continue
    if run_dir is None:
        raise SystemExit(f"failed to allocate unique run_dir under {runs_root} for run_id={run_id}")

    warnings: List[str] = []
    warnings.extend(cfg_warnings)

    if not project_root.exists():
        raise SystemExit(f"project_root not found: {project_root}")
    if not main_tex.exists():
        raise SystemExit(f"main_tex not found: {main_tex}")

    citation_commands = _safe_get(cfg, ["citation_commands"], []) or []
    bibliography_commands = _safe_get(cfg, ["bibliography_commands"], ["bibliography", "addbibresource"]) or []
    limits = _safe_get(cfg, ["ai", "input_limits"], {}) or {}
    max_sentence_chars = int(limits.get("max_sentence_chars", 500) or 500)
    doi_cfg = _safe_get(cfg, ["checks", "doi"], {}) or {}
    doi_regex = str(doi_cfg.get("regex") or r"(?i)\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b")

    tex_files, w1 = discover_tex_dependency_tree(project_root, main_tex)
    warnings.extend(w1)

    bib_files, w2 = discover_bib_files(project_root, tex_files, bibliography_commands=bibliography_commands)
    warnings.extend(w2)

    entries_by_key, duplicates, bib_warnings = merge_bib_entries(bib_files)
    warnings.extend(bib_warnings)

    hits, cite_warnings = extract_citations(project_root, tex_files, citation_commands=citation_commands, max_sentence_chars=max_sentence_chars)
    warnings.extend(cite_warnings)

    def _norm_src(s: str) -> str:
        return relpath_safe(Path(s), project_root)

    duplicates_norm = {k: [_norm_src(x) for x in v] for k, v in (duplicates or {}).items()}

    hits_effective = [h for h in hits if h.bibkey and h.bibkey != "*"]
    cited_keys = [h.bibkey for h in hits_effective]
    cited_key_set = set(cited_keys)
    nocite_star = any(h.bibkey == "*" for h in hits)

    missing_keys = sorted(cited_key_set - set(entries_by_key.keys()))

    # Unused keys is meaningful only if there isn't \nocite{*}
    unused_keys: List[str] = []
    if not nocite_star:
        unused_keys = sorted(set(entries_by_key.keys()) - cited_key_set)

    # Field issues for cited entries only (to avoid noise)
    req_common = list(_safe_get(cfg, ["checks", "bib_required_fields", "common"], ["title", "author"]) or [])
    req_year_like = list(_safe_get(cfg, ["checks", "bib_required_fields", "year_like"], ["year", "date"]) or [])
    field_issues: List[Dict[str, Any]] = []
    doi_issues: List[Dict[str, Any]] = []
    bib_inventory: Dict[str, Any] = {"cited": [], "missing": missing_keys, "duplicates": duplicates_norm}

    for k in sorted(cited_key_set):
        e = entries_by_key.get(k)
        if not e:
            continue
        issues = required_field_issues(e, required_common=req_common, year_like=req_year_like)
        if issues:
            field_issues.append({"bibkey": k, "issues": "; ".join(issues), "source": _norm_src(e.source)})

        doi = e.get("doi")
        if doi and not validate_doi(doi, doi_regex=doi_regex):
            doi_issues.append({"bibkey": k, "doi": doi, "source": _norm_src(e.source)})

        bib_inventory["cited"].append(_entry_digest(e, project_root=project_root, limits=limits))

    # Missing detail: count and examples
    counter = Counter(cited_keys)
    missing_detail: List[Dict[str, Any]] = []
    for k in missing_keys:
        examples = []
        for h in hits:
            if h.bibkey == k:
                examples.append(f"{h.file}:{h.line} {h.sentence}")
                if len(examples) >= 5:
                    break
        missing_detail.append({"bibkey": k, "count": int(counter.get(k, 0)), "examples": examples})

    online_summary: Dict[str, Any] = {"enabled": bool(args.verify_online), "checked": 0, "ok": 0, "failed": 0, "failures": []}
    online_results: Dict[str, Any] = {}
    if args.verify_online:
        # Only check DOIs for cited entries.
        for k in sorted(cited_key_set):
            e = entries_by_key.get(k)
            if not e:
                continue
            doi = e.get("doi").strip()
            if not doi:
                continue
            res = check_doi_online(doi, bib_title=e.get("title"), sleep_s=0.2)
            online_summary["checked"] += 1
            online_results[k] = res.to_dict()

            # mark failures: no provider ok OR title mismatch suspicious (when both titles present)
            title_mismatch = False
            if res.crossref_ok and res.crossref_title and e.get("title"):
                title_mismatch = res.title_similarity_crossref < 0.2
            if res.openalex_ok and res.openalex_title and e.get("title"):
                title_mismatch = title_mismatch or (res.title_similarity_openalex < 0.2)

            if not res.ok or title_mismatch:
                online_summary["failed"] += 1
                online_summary["failures"].append(
                    {
                        "bibkey": k,
                        "doi": doi,
                        "error": res.error or ("title mismatch suspicious" if title_mismatch else ""),
                        "title_similarity_crossref": res.title_similarity_crossref,
                        "title_similarity_openalex": res.title_similarity_openalex,
                    }
                )
            else:
                online_summary["ok"] += 1

    # Build AI input JSON (bounded)
    max_entries = int(limits.get("max_entries", 500) or 500)
    max_citations = int(limits.get("max_citations", 2000) or 2000)

    ai_input: Dict[str, Any] = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "skill_info": (_safe_get(cfg, ["skill_info"], {}) or {}),
        "project_root": str(project_root),
        "main_tex": relpath_safe(main_tex, project_root),
        "run_dir": str(run_dir),
        "policy": {
            "read_only": True,
            "do_not_modify": ["**/*.tex", "**/*.bib", "**/*.cls", "**/*.sty"],
            "intermediate_dir": str(run_dir),
            "deliver_dir_default": str(report_dir),
        },
        "discovery": {
            "tex_files": [relpath_safe(p, project_root) for p in tex_files[:2000]],
            "bib_files": [relpath_safe(p, project_root) for p in bib_files[:2000]],
        },
        "stats": {
            "tex_files": len(tex_files),
            "bib_files": len(bib_files),
            "total_citations": len(hits_effective),
            "unique_cited_bibkeys": len(cited_key_set),
            "missing_bibkeys": len(missing_keys),
            "duplicate_bibkeys": len(duplicates),
            "field_issues": len(field_issues),
            "invalid_doi": len(doi_issues),
            "nocite_star_present": nocite_star,
            "unused_bibkeys": len(unused_keys),
        },
        "warnings": warnings,
        "issues": {
            "missing_bibkeys": missing_keys,
            "missing_bibkeys_detail": missing_detail,
            "duplicate_bibkeys": duplicates_norm,
            "unused_bibkeys": unused_keys[:1000],
            "field_issues": field_issues[:1000],
            "doi_issues": doi_issues[:1000],
        },
        "online_verify": online_summary,
        "online_results_by_bibkey": online_results,
        "citations": [
            {
                "bibkey": h.bibkey,
                "cite_command": h.cite_command,
                "file": h.file,
                "line": h.line,
                "heading": h.heading,
                "sentence": h.sentence,
            }
            for h in hits_effective[:max_citations]
        ],
        "bib_inventory_cited": bib_inventory["cited"][:max_entries],
    }

    # Deterministic report summary input
    report_summary = {
        "generated_at": ai_input["generated_at"],
        "project_root": str(project_root),
        "main_tex": str(ai_input["main_tex"]),
        "run_dir": str(run_dir),
        "warnings": warnings,
        "stats": ai_input["stats"],
        "issues": {
            "missing_bibkeys_detail": missing_detail,
            "duplicate_bibkeys": duplicates_norm,
            "field_issues": field_issues,
            "doi_issues": doi_issues,
        },
        "online_verify": online_summary,
    }

    # Write outputs (all writes are either run_dir or report_dir)
    write_citations_csv(run_dir / "citations.csv", hits_effective)
    write_json(run_dir / "bib_inventory.json", bib_inventory)
    write_json(run_dir / "ai_ref_alignment_input.json", ai_input)
    (run_dir / "ref_integrity_report.md").write_text(build_deterministic_report_md(report_summary), encoding="utf-8")
    write_json(
        run_dir / "run_manifest.json",
        {
            "args": vars(args),
            "project_root": str(project_root),
            "main_tex": str(main_tex),
            "tex_files": [str(p) for p in tex_files],
            "bib_files": [str(p) for p in bib_files],
            "run_dir": str(run_dir),
        },
    )

    # Delivery report (deterministic draft).
    # Tie deliver filename to run_dir so it's unique even when run_id gets a -2/-3 suffix.
    report_dir.mkdir(parents=True, exist_ok=True)
    deliver_id = run_dir.name[len("run_") :] if run_dir.name.startswith("run_") else run_dir.name
    deliver_path = report_dir / f"NSFC-REF-ALIGNMENT-v{deliver_id}.md"
    draft = []
    draft.append("# NSFC 参考文献与引用核查报告（草稿：确定性部分）")
    draft.append("")
    draft.append(f"- project_root: `{project_root}`")
    draft.append(f"- main_tex: `{relpath_safe(main_tex, project_root)}`")
    draft.append(f"- run_dir: `{run_dir}`")
    draft.append("")
    draft.append("本文件由脚本生成，包含“确定性检查”结果；请在执行 nsfc-ref-alignment skill 时由宿主 AI 补充“语义匹配核查”部分。")
    draft.append("")
    draft.append("---")
    draft.append("")
    draft.append(build_deterministic_report_md(report_summary))
    deliver_path.write_text("\n".join(draft) + "\n", encoding="utf-8")

    print(str(deliver_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
