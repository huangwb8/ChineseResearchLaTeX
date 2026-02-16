#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import html
import re
from dataclasses import asdict
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, List, Optional

from .diagnostic import DiagnosticReport


def _load_template(path: Path) -> Template:
    return Template(path.read_text(encoding="utf-8", errors="ignore"))


def _escape(text: str) -> str:
    return html.escape(text or "", quote=False)


def _badge(text: str, cls: str) -> str:
    return f'<span class="tag {cls}">{_escape(text)}</span>'


def _kv(key: str, val_html: str) -> str:
    return f'<div class="kv"><div class="k">{_escape(key)}</div><div class="v">{val_html}</div></div>'


def _ul(items: Iterable[str]) -> str:
    lis = "".join([f"<li>{_escape(x)}</li>" for x in items if str(x).strip()])
    return f"<ul>{lis}</ul>" if lis else "<div class=\"md\">（无）</div>"


def _render_tier2(tier2: Optional[Dict[str, Any]]) -> str:
    if not tier2:
        return '<div class="md">（未启用或无输出）</div>'
    blocks = []
    for k in ["logic", "terminology", "evidence", "suggestions"]:
        v = tier2.get(k)
        if not v:
            continue
        if isinstance(v, list):
            blocks.append(f'<div class="md"><b>{_escape(k)}</b>{_ul([str(x) for x in v])}</div>')
        else:
            blocks.append(f'<div class="md"><b>{_escape(k)}</b><div>{_escape(str(v))}</div></div>')
    return "\n".join(blocks) if blocks else '<div class="md">（无）</div>'


def _highlight_line(
    *,
    src: str,
    forbidden_phrases: List[str],
    avoid_commands: List[str],
    missing_cite_keys: List[str],
) -> str:
    t = _escape(src)

    def _wrap(pattern: str, cls: str) -> None:
        nonlocal t
        if not pattern:
            return
        try:
            t = re.sub(re.escape(pattern), lambda m: f'<span class="{cls}">{m.group(0)}</span>', t)
        except re.error:
            return

    for p in forbidden_phrases:
        _wrap(p, "hlbad")
    for c in avoid_commands:
        _wrap(c, "hlbad")

    if missing_cite_keys:
        def _cite_repl(m: re.Match[str]) -> str:
            raw = m.group(0)
            keys = m.group(1) or ""
            bad = [k.strip() for k in keys.split(",") if k.strip() in set(missing_cite_keys)]
            cls = "hlbad" if bad else "hl"
            return f'<span class="{cls}">{raw}</span>'

        try:
            t = re.sub(r"(\\cite[a-zA-Z\\*]*\s*(?:\[[^\\]]*\\]\s*)*\{([^}]*)\})", _cite_repl, t)
        except re.error:
            pass

    return t


def _markdown_table_to_html(md: str) -> str:
    lines = [ln.strip() for ln in (md or "").splitlines() if ln.strip()]
    rows = [ln for ln in lines if ln.startswith("|") and ln.endswith("|")]
    if len(rows) < 2:
        if md.strip():
            return f'<div class="md"><pre class="mono">{_escape(md)}</pre></div>'
        return '<div class="md">（无）</div>'

    header = [c.strip() for c in rows[0].strip("|").split("|")]
    body_rows = []
    for r in rows[2:]:
        cols = [c.strip() for c in r.strip("|").split("|")]
        if len(cols) != len(header):
            continue
        body_rows.append(cols)

    thead = "<tr>" + "".join([f"<th>{_escape(h)}</th>" for h in header]) + "</tr>"
    tbody = "".join(
        [
            "<tr>"
            + "".join([f"<td>{_escape(c)}</td>" for c in cols])
            + "</tr>"
            for cols in body_rows
        ]
    )
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


def render_diagnostic_html(
    *,
    skill_root: Path,
    project_root: Path,
    target_relpath: str,
    tex_text: str,
    report: DiagnosticReport,
    term_matrix_md: str = "",
    next_steps: Optional[List[str]] = None,
) -> str:
    # 新规范：assets/templates/...
    # 兼容旧路径：templates/...
    skill_root = Path(skill_root).resolve()
    tpl_candidates = [
        (skill_root / "assets" / "templates" / "html" / "report_template.html").resolve(),
        (skill_root / "templates" / "html" / "report_template.html").resolve(),
    ]
    tpl_path = next((p for p in tpl_candidates if p.exists()), tpl_candidates[0])
    template = _load_template(tpl_path)

    t1 = report.tier1
    tier1_items = [
        _kv("结构", ("✅ 完整" if t1.structure_ok else "❌ 缺失") + _badge(f"subsubsection={t1.subsubsection_count}", "warn")),
        _kv("引用", ("✅ 正常" if t1.citation_ok else "❌ 缺失") + _badge(f"missing={len(t1.missing_citation_keys)}", "bad" if (not t1.citation_ok) else "ok")),
        _kv("字数", _escape(str(t1.word_count))),
    ]
    if getattr(t1, "missing_doi_keys", None):
        tier1_items.append(_kv("DOI", _badge(f"缺失={len(t1.missing_doi_keys)}", "warn")))
    if t1.forbidden_phrases_hits:
        tier1_items.append(_kv("不可核验表述", _badge(", ".join(t1.forbidden_phrases_hits[:6]), "bad")))
    if t1.avoid_commands_hits:
        tier1_items.append(_kv("危险命令", _badge(", ".join(t1.avoid_commands_hits[:6]), "bad")))

    tier1_summary_html = '<div class="kvs">' + "".join(tier1_items) + "</div>"

    default_next = []
    if not t1.structure_ok:
        default_next.append("先补齐 4 个 \\subsubsection 标题骨架，再进入段落写作。")
    if not t1.citation_ok:
        default_next.append("修复缺失的 \\cite{...}：先补 bib 或用 nsfc-bib-manager 核验后再写入。")
    if t1.forbidden_phrases_hits:
        default_next.append("删除不可核验绝对表述（国际领先/国内首次等），改为可验证指标与对照维度。")
    if t1.avoid_commands_hits:
        default_next.append("移除可能破坏模板的命令（\\section/\\input 等），仅改正文段落。")
    next_steps = next_steps if next_steps is not None else default_next
    next_steps_html = '<div class="md">' + _ul(next_steps) + "</div>"

    code_lines = []
    forbidden = list(t1.forbidden_phrases_hits or [])
    avoid_cmds = list(t1.avoid_commands_hits or [])
    missing_keys = list(t1.missing_citation_keys or [])
    for i, line in enumerate((tex_text or "").splitlines(), start=1):
        line_html = _highlight_line(
            src=line,
            forbidden_phrases=forbidden,
            avoid_commands=avoid_cmds,
            missing_cite_keys=missing_keys,
        )
        code_lines.append(
            '<li class="line"><a class="ln mono" id="L{n}" href="#L{n}">{n}</a><div class="src mono">{src}</div></li>'.format(
                n=i, src=line_html
            )
        )

    meta = f"project_root={project_root} · bytes={len(tex_text.encode('utf-8', errors='ignore'))}"
    if report.notes:
        meta += " · notes=" + str(len(report.notes))

    return template.safe_substitute(
        title="nsfc-justification-writer 诊断报告",
        headline="nsfc-justification-writer 诊断报告",
        meta=_escape(meta),
        target_relpath=_escape(target_relpath),
        tier1_summary_html=tier1_summary_html,
        next_steps_html=next_steps_html,
        tier2_html=_render_tier2(report.tier2),
        terms_html=_markdown_table_to_html(term_matrix_md),
        code_lines_html="".join(code_lines) if code_lines else '<li class="line"><div class="ln mono">—</div><div class="src mono">（文件为空）</div></li>',
    )
