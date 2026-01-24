#!/usr/bin/env python3
"""
run_ai_alignment.py - check-review-alignment 的确定性入口（纯 AI 模式）

脚本职责（确定性）：
- 依赖检查（systematic-literature-review）
- 定位 tex/bib
- 解析段落与引用，抽取 bib 元信息与（可选）PDF 摘要段
- 可选：渲染 PDF/Word（复用依赖 skill 的脚本）

非职责（启发式/AI）：
- 判断“引用是否合理”、生成改写句子与段落
- 写 ai_alignment_report.md 的“问题原因/优化版本”等语义内容

这些由宿主 AI（Claude/Codex）在执行本 skill 时完成。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from bib_utils import extract_pdf_text, find_pdf_for_entry, parse_bib_file
from paragraph_analyzer import parse_latex_document
from runtime_utils import find_tex_and_bib, load_config, python_executable

def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    t = " ".join(str(text).split())
    if len(t) <= limit:
        return t
    return t[:limit].rstrip() + " …(truncated)"

def _safe_int(value: Any, default: int, warnings: List[str], name: str) -> int:
    try:
        return int(value)
    except Exception:
        warnings.append(f"invalid int for {name}: {value!r} (fallback to {default})")
        return default


def build_ai_input(
    work_dir: Path,
    tex_path: Path,
    bib_path: Path,
    config: dict,
) -> Dict[str, Any]:
    """生成供宿主 AI 使用的结构化输入（ai_alignment_input.json）。"""
    warnings: List[str] = []

    ai_cfg = config.get("ai", {}) or {}
    limits = ai_cfg.get("input_limits", {}) or {}
    max_abstract_chars = _safe_int(limits.get("max_abstract_chars", 2000), 2000, warnings, "ai.input_limits.max_abstract_chars")
    max_pdf_excerpt_chars = _safe_int(limits.get("max_pdf_excerpt_chars", 3000), 3000, warnings, "ai.input_limits.max_pdf_excerpt_chars")

    # 将“修改策略”打包进输入，确保宿主 AI 在只读取 ai_alignment_input.json 时也能
    # 严格遵循“只修复致命性错误，不为了改而改”的边界（脚本不做任何语义判断）。
    mod_cfg = ai_cfg.get("modification", {}) or {}
    para_cfg = ai_cfg.get("paragraph_optimization", {}) or {}
    policy: Dict[str, Any] = {
        "modification": {
            "auto_apply": bool(mod_cfg.get("auto_apply", False)),
            "preserve_citations": bool(mod_cfg.get("preserve_citations", True)),
            "max_edits_per_sentence": _safe_int(mod_cfg.get("max_edits_per_sentence", 3), 3, warnings, "ai.modification.max_edits_per_sentence"),
            "error_priority": list(mod_cfg.get("error_priority", []) or []),
            "non_fatal_handling": str(mod_cfg.get("non_fatal_handling", "skip")),
        },
        "paragraph_optimization": {
            "enabled": bool(para_cfg.get("enabled", False)),
            "after_all_citations": bool(para_cfg.get("after_all_citations", False)),
        },
    }

    doc = parse_latex_document(
        tex_path,
        citation_commands=config.get("citation_commands", []),
    )
    bib_entries = parse_bib_file(bib_path)

    raw_skill_info = (config.get("skill_info", {}) or {}) if isinstance(config, dict) else {}
    skill_info: Dict[str, Any] = {}
    for k in ("name", "version", "description", "category"):
        if k in raw_skill_info:
            skill_info[k] = raw_skill_info.get(k)

    cited_keys = sorted({c.bibkey for c in doc.citations})

    pdf_cfg = config.get("pdf", {}) or {}
    pdf_enabled = bool(pdf_cfg.get("enabled", True))
    max_pages = _safe_int(pdf_cfg.get("max_pages", 2), 2, warnings, "pdf.max_pages")

    papers: Dict[str, Dict[str, Any]] = {}
    missing_in_bib_keys: List[str] = []
    for key in cited_keys:
        entry = bib_entries.get(key)
        if not entry:
            papers[key] = {"bibkey": key, "missing_in_bib": True}
            missing_in_bib_keys.append(key)
            continue

        paper: Dict[str, Any] = {
            "bibkey": key,
            "missing_in_bib": False,
            "title": entry.get("title", ""),
            "author": entry.get("author", ""),
            "year": entry.get("year", ""),
            "journal": entry.get("journal", "") or entry.get("booktitle", ""),
            "doi": entry.get("doi", "") or "",
            "url": entry.get("url", "") or "",
            "abstract": _truncate(entry.get("abstract", ""), max_abstract_chars),
        }

        if pdf_enabled:
            pdf_path = find_pdf_for_entry(entry, base_dir=work_dir)
            if pdf_path is not None:
                try:
                    resolved_pdf = pdf_path.resolve()
                    resolved_work = work_dir.resolve()
                    # 如果 PDF 路径不在 work_dir 内，给出 warning（但不强制禁止，避免破坏用户工作流）
                    try:
                        resolved_pdf.relative_to(resolved_work)
                    except Exception:
                        warnings.append(f"PDF 路径不在 work_dir 内（仍会尝试读取）：{resolved_pdf}")
                except Exception:
                    # resolve 失败不影响主流程
                    pass
                excerpt = extract_pdf_text(pdf_path, max_pages=max_pages, warnings=warnings)
                if excerpt:
                    paper["pdf_path"] = str(pdf_path)
                    paper["pdf_excerpt"] = _truncate(excerpt, max_pdf_excerpt_chars)
        papers[key] = paper

    paragraphs: List[Dict[str, Any]] = []
    for p in doc.paragraphs_with_citations:
        paragraphs.append(
            {
                "index": p.index,
                "start_line": p.start_line,
                "end_line": p.end_line,
                "citation_count": p.citation_count,
            }
        )

    citations: List[Dict[str, Any]] = []
    for c in doc.citations:
        citations.append(
            {
                "bibkey": c.bibkey,
                "line_number": c.line_number,
                "paragraph_index": c.paragraph_index,
                "citation_index_in_paragraph": c.citation_index_in_para,
                "citation_index_global": c.citation_index_global,
                "sentence": c.sentence,
                "cite_command": c.cite_command,
            }
        )

    citations.sort(
        key=lambda x: (
            int(x.get("line_number", 0)),
            int(x.get("paragraph_index", 0)),
            int(x.get("citation_index_in_paragraph", 0)),
            str(x.get("bibkey", "")),
        )
    )

    if missing_in_bib_keys:
        warnings.append("以下 bibkey 在 .bib 中缺失（已标记 missing_in_bib=true）: " + ", ".join(missing_in_bib_keys))

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "skill_info": skill_info,
        "work_dir": str(work_dir),
        "tex": tex_path.name,
        "bib": bib_path.name,
        "policy": policy,
        "stats": {
            "total_paragraphs": doc.total_paragraphs,
            "paragraphs_with_citations": len(doc.paragraphs_with_citations),
            "total_citations": doc.total_citations,
            "unique_cited_bibkeys": len(cited_keys),
            "missing_in_bib_bibkeys": len(missing_in_bib_keys),
        },
        "warnings": warnings,
        "paragraphs": paragraphs,
        "citations": citations,
        "papers": papers,
    }


def render_outputs(tex_path: Path, bib_path: Path, config: dict) -> Dict[str, Any]:
    """渲染 PDF/Word（复用依赖 skill 的渲染脚本）。"""
    render_cfg = config.get("render", {}) or {}
    overwrite = bool(render_cfg.get("overwrite", True))

    dep_skill = str(render_cfg.get("use_skill", "systematic-literature-review"))
    # 仅在渲染路径下检查依赖（prepare 不应被渲染依赖阻塞）
    from runtime_utils import require_dependency_skill, resolve_render_scripts

    dep_root = require_dependency_skill(dep_skill, reason="PDF/Word 渲染")
    compile_script, word_script = resolve_render_scripts(dep_root, dep_skill_name=dep_skill)

    pdf_path = tex_path.with_suffix(".pdf")
    docx_path = tex_path.with_suffix(".docx")

    log: List[str] = []
    result: Dict[str, Any] = {"ok": True, "pdf": None, "word": None, "log": log}

    if overwrite or not pdf_path.exists():
        proc_pdf = subprocess.run(
            [python_executable(), str(compile_script), str(tex_path), str(pdf_path)],
            text=True,
            capture_output=True,
            cwd=tex_path.parent,
        )
        if proc_pdf.stdout:
            log.append(proc_pdf.stdout)
        if proc_pdf.returncode != 0:
            if proc_pdf.stderr:
                log.append(proc_pdf.stderr)
            result["ok"] = False
            return result
        result["pdf"] = str(pdf_path)
    else:
        log.append("skip PDF render: overwrite=false and target exists")
        result["pdf"] = str(pdf_path)

    if overwrite or not docx_path.exists():
        proc_docx = subprocess.run(
            [python_executable(), str(word_script), str(tex_path), str(bib_path), str(docx_path)],
            text=True,
            capture_output=True,
            cwd=tex_path.parent,
        )
        if proc_docx.stdout:
            log.append(proc_docx.stdout)
        if proc_docx.returncode != 0:
            if proc_docx.stderr:
                log.append(proc_docx.stderr)
            result["ok"] = False
            return result
        result["word"] = str(docx_path)
    else:
        log.append("skip Word render: overwrite=false and target exists")
        result["word"] = str(docx_path)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="check-review-alignment (AI mode) helper runner")
    parser.add_argument("--work-dir", required=True, type=Path, help="综述工作目录（包含 tex/bib）")
    parser.add_argument("--tex", type=str, default=None, help="可选：指定 tex 文件名")
    parser.add_argument("--prepare", action="store_true", help="生成 ai_alignment_input.json")
    parser.add_argument("--render", action="store_true", help="渲染 PDF/Word（不做任何 AI 判断）")
    args = parser.parse_args()

    work_dir = args.work_dir.resolve()
    skill_root = Path(__file__).resolve().parents[1]
    config, cfg_warnings = load_config(skill_root / "config.yaml")
    for w in cfg_warnings:
        # config 读取警告仅用于告知，不影响执行
        print(f"⚠️  {w}")

    do_prepare = bool(args.prepare)
    do_render = bool(args.render)
    if not do_prepare and not do_render:
        do_prepare = True

    selection_warnings: List[str] = []
    try:
        tex_path, bib_path = find_tex_and_bib(work_dir, args.tex, warnings=selection_warnings)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        if args.tex:
            print("   提示：--tex 只支持传入文件名；并确保该文件存在于 work_dir 根目录。")
        return 2
    for w in selection_warnings:
        # 这里的 warning 主要用于可预期性（例如同目录多 tex 的默认选择）
        print(f"⚠️  {w}")
        if "默认选择第一个" in w:
            print("   提示：可用 --tex <file.tex> 指定目标 tex 文件名。")

    # 创建中间文件目录（隐藏文件夹）
    intermediate_dir = work_dir / ".check-review-alignment"
    intermediate_dir.mkdir(exist_ok=True)

    if do_prepare:
        payload = build_ai_input(work_dir, tex_path, bib_path, config=config)
        out_path = intermediate_dir / "ai_alignment_input.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✅ 已生成: {out_path}")

    if do_render:
        print("🖨️  开始渲染 PDF/Word（复用依赖 skill 脚本）...")
        result = render_outputs(tex_path, bib_path, config=config)
        if not result.get("ok"):
            print("❌ 渲染失败（请检查 log）")
            return 2
        print(f"✅ PDF: {result.get('pdf')}")
        print(f"✅ Word: {result.get('word')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
