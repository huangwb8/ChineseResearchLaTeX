#!/usr/bin/env python3
"""
Write NSFC-ABSTRACTS.md in the current working directory.

Input formats supported:
  1) Marker format: [ZH]...[/ZH] and [EN]...[/EN]
  2) Markdown headings: "# 中文摘要" and "# English Abstract" (headings configurable)

This script is intentionally stdlib-only (no PyYAML).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


def _extract_block_by_markers(text: str, begin: str, end: str) -> Optional[str]:
    pattern = re.compile(re.escape(begin) + r"(.*?)" + re.escape(end), re.DOTALL)
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _extract_block_by_headings(text: str, zh_heading: str, en_heading: str) -> Optional[Tuple[str, str]]:
    # Normalize line endings and keep original content lines.
    lines = text.splitlines()

    def _is_heading(line: str, heading: str) -> bool:
        return line.strip() == heading.strip()

    zh_i = None
    en_i = None
    for i, line in enumerate(lines):
        if zh_i is None and _is_heading(line, zh_heading):
            zh_i = i
            continue
        if en_i is None and _is_heading(line, en_heading):
            en_i = i
            continue

    if zh_i is None or en_i is None:
        return None
    if zh_i > en_i:
        # If swapped, treat as invalid format.
        return None

    zh_lines = lines[zh_i + 1 : en_i]
    zh = "\n".join(zh_lines).strip()
    # EN content ends at the next markdown heading (any level) if present,
    # e.g. "## 长度自检" appended by this script itself.
    en_lines = []
    for line in lines[en_i + 1 :]:
        if line.lstrip().startswith("#"):
            break
        en_lines.append(line)
    en = "\n".join(en_lines).strip()
    return zh, en


def _normalize_for_count(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _parse_bool(v: Optional[str], default: bool) -> bool:
    if v is None:
        return default
    s = v.strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return default


@dataclass(frozen=True)
class SkillConfig:
    zh_max: int
    en_max: int
    zh_begin: str
    zh_end: str
    en_begin: str
    en_end: str
    out_name: str
    zh_heading: str
    en_heading: str
    title_required: bool
    title_candidates_default: int
    title_begin: str
    title_end: str
    title_heading: str


def _load_config(skill_root: Path) -> SkillConfig:
    """
    Minimal config reader (no YAML deps). It searches for scalar keys by regex.
    """
    config_path = skill_root / "config.yaml"
    raw = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

    def _strip_inline_comment(value: str) -> str:
        v = value.lstrip()
        if not v:
            return v
        if v[0] in {"\"", "'"}:
            q = v[0]
            out = []
            escaped = False
            for ch in v[1:]:
                if escaped:
                    out.append(ch)
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if ch == q:
                    break
                out.append(ch)
            return "".join(out)
        return v.split("#", 1)[0].rstrip()

    def _get_scalar(key: str) -> Optional[str]:
        m = re.search(rf"^[ \t]*{re.escape(key)}:[ \t]*(.+?)\s*$", raw, re.M)
        if not m:
            return None
        return _strip_inline_comment(m.group(1)).strip()

    def _int(key: str, default: int) -> int:
        v = _get_scalar(key)
        if v is None:
            return default
        return int(v) if v.isdigit() else default

    def _str(key: str, default: str) -> str:
        v = _get_scalar(key)
        return v if v is not None and v != "" else default

    zh_max = _int("zh_max_chars", 400)
    en_max = _int("en_max_chars", 4000)

    zh_begin = _str("zh_begin", "[ZH]")
    zh_end = _str("zh_end", "[/ZH]")
    en_begin = _str("en_begin", "[EN]")
    en_end = _str("en_end", "[/EN]")

    out_name = _str("filename", "NSFC-ABSTRACTS.md")
    zh_heading = _str("zh_heading", "# 中文摘要")
    en_heading = _str("en_heading", "# English Abstract")

    title_required = _parse_bool(_get_scalar("title_required"), False)
    title_candidates_default = _int("title_candidates_default", 5)
    title_begin = _str("title_begin", "[TITLE]")
    title_end = _str("title_end", "[/TITLE]")
    title_heading = _str("title_heading", "# 标题建议")

    return SkillConfig(
        zh_max=zh_max,
        en_max=en_max,
        zh_begin=zh_begin,
        zh_end=zh_end,
        en_begin=en_begin,
        en_end=en_end,
        out_name=out_name,
        zh_heading=zh_heading,
        en_heading=en_heading,
        title_required=title_required,
        title_candidates_default=title_candidates_default,
        title_begin=title_begin,
        title_end=title_end,
        title_heading=title_heading,
    )


def _extract_title_by_headings(text: str, title_heading: str, zh_heading: str) -> Optional[str]:
    lines = text.splitlines()

    def _is_heading(line: str, heading: str) -> bool:
        return line.strip() == heading.strip()

    t_i = None
    zh_i = None
    for i, line in enumerate(lines):
        if t_i is None and _is_heading(line, title_heading):
            t_i = i
            continue
        if zh_i is None and _is_heading(line, zh_heading):
            zh_i = i
            continue

    if t_i is None:
        return None
    end_i = zh_i if (zh_i is not None and zh_i > t_i) else len(lines)
    body = "\n".join(lines[t_i + 1 : end_i]).strip()
    return body or None


def _parse_input(
    text: str,
    *,
    title_begin: str,
    title_end: str,
    title_heading: str,
    title_required: bool,
    title_candidates_default: int,
    zh_begin: str,
    zh_end: str,
    en_begin: str,
    en_end: str,
    zh_heading: str,
    en_heading: str,
) -> Tuple[Optional[str], str, str]:
    title = _extract_block_by_markers(text, title_begin, title_end)
    zh = _extract_block_by_markers(text, zh_begin, zh_end)
    en = _extract_block_by_markers(text, en_begin, en_end)
    if zh is not None and en is not None:
        return title, zh, en

    by_h = _extract_block_by_headings(text, zh_heading, en_heading)
    if by_h is not None:
        zh_h, en_h = by_h
        title_h = _extract_title_by_headings(text, title_heading, zh_heading)
        return title_h, zh_h, en_h

    if title_required:
        raise ValueError(
            "无法解析输入（标题+中英文摘要是必需的）。请使用以下任一格式：\n"
            f"1) 标记格式：{title_begin}...{title_end} 与 {zh_begin}...{zh_end} 与 {en_begin}...{en_end}\n"
            f"2) 标题格式：{title_heading} 与 {zh_heading} 与 {en_heading}\n"
            f"并确保标题候选不少于 {title_candidates_default} 个，且包含“推荐标题：...”一行。"
        )

    raise ValueError(
        "无法解析输入。请使用以下任一格式：\n"
        f"1) 标记格式：{zh_begin}...{zh_end} 与 {en_begin}...{en_end}\n"
        f"2) 标题格式：{zh_heading} 与 {en_heading}"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("input", help="包含摘要内容的输入文件路径（或 - 表示 stdin）")
    ap.add_argument("--out", default=None, help="输出 Markdown 文件名（默认取 config.yaml:output.filename）")
    ap.add_argument("--strict", action="store_true", help="超限则返回非 0")
    ap.add_argument(
        "--auto-compress",
        action="store_true",
        help="超限时自动压缩（占位：当前版本不执行压缩，仅提示并返回 1）",
    )
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告（stdout 仅打印 JSON）")
    args = ap.parse_args(argv)

    skill_root = Path(__file__).resolve().parents[1]
    cfg = _load_config(skill_root)

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        raw = _read_text(Path(args.input))

    title_raw, zh_raw, en_raw = _parse_input(
        raw,
        title_begin=cfg.title_begin,
        title_end=cfg.title_end,
        title_heading=cfg.title_heading,
        title_required=cfg.title_required,
        title_candidates_default=cfg.title_candidates_default,
        zh_begin=cfg.zh_begin,
        zh_end=cfg.zh_end,
        en_begin=cfg.en_begin,
        en_end=cfg.en_end,
        zh_heading=cfg.zh_heading,
        en_heading=cfg.en_heading,
    )

    zh = zh_raw.strip()
    en = en_raw.strip()
    title = (title_raw or "").strip()

    # Reuse validator's counting semantics for consistency.
    try:
        import validate_abstract  # type: ignore

        report = validate_abstract.build_report(zh, en, zh_max=cfg.zh_max, en_max=cfg.en_max)
        title_report = validate_abstract.build_title_report(
            title_raw,
            required=cfg.title_required,
            min_candidates=cfg.title_candidates_default,
        )
    except Exception:
        # Fallback: keep behavior even if import fails for any reason.
        zh_len = len(_normalize_for_count(zh))
        en_len = len(_normalize_for_count(en))
        report = {
            "zh": {"len": zh_len, "max": cfg.zh_max, "exceeded": max(0, zh_len - cfg.zh_max), "ok": zh_len <= cfg.zh_max},
            "en": {"len": en_len, "max": cfg.en_max, "exceeded": max(0, en_len - cfg.en_max), "ok": en_len <= cfg.en_max},
        }
        title_report = {
            "present": bool(title),
            "required": bool(cfg.title_required),
            "has_recommended": bool(re.search(r"(?m)^\s*推荐标题\s*[:：]\s*\S+", title)),
            "candidates": len(re.findall(r"(?m)^\s*(?:[-*]\s*)?\d+[\)\.、]\s+\S+", title)),
            "min_candidates": int(cfg.title_candidates_default),
            "ok": (not cfg.title_required)
            or (
                bool(title)
                and bool(re.search(r"(?m)^\s*推荐标题\s*[:：]\s*\S+", title))
                and len(re.findall(r"(?m)^\s*(?:[-*]\s*)?\d+[\)\.、]\s+\S+", title)) >= int(cfg.title_candidates_default)
            ),
        }

    zh_ok = bool(report["zh"]["ok"])
    en_ok = bool(report["en"]["ok"])
    title_ok = bool(title_report.get("ok"))
    report["title"] = title_report

    out_path = Path.cwd() / (args.out or cfg.out_name)

    if cfg.title_required and not title_ok:
        sys.stderr.write(
            "[ERROR] 缺少或不合格的标题建议分段（不写入）。\n"
            f"- required: {cfg.title_required}\n"
            f"- min candidates: {cfg.title_candidates_default}\n"
            "修复提示：在输入中加入 [TITLE]...[/TITLE] 或 \"# 标题建议\" 分段，并包含“推荐标题：...”与不少于 5 个候选条目。\n"
        )
        if args.json:
            sys.stdout.write(json.dumps(report, ensure_ascii=False))
            sys.stdout.write("\n")
        return 2

    if (args.strict or args.auto_compress) and (not zh_ok or not en_ok):
        # In strict mode, do not write an invalid output file.
        mode = "strict" if args.strict else "auto-compress"
        msg = (
            f"[ERROR] 摘要超限（{mode} 模式不写入）：ZH {report['zh']['len']}/{cfg.zh_max}；EN {report['en']['len']}/{cfg.en_max}\n"
            f"- exceeded: ZH {report['zh']['exceeded']}, EN {report['en']['exceeded']}\n"
        )
        sys.stderr.write(msg)
        if args.auto_compress:
            sys.stderr.write(
                "\n[HINT] --auto-compress 当前为占位参数：不会自动压缩。\n"
                "请按 SKILL.md 的“字数超限处理”策略手工压缩后重试。\n"
            )
        if args.json:
            sys.stdout.write(json.dumps(report, ensure_ascii=False))
            sys.stdout.write("\n")
        return 1

    title_text = ""
    if title:
        title_text = f"{cfg.title_heading}\n\n{title}\n\n"
    out_text = (
        title_text
        + f"{cfg.zh_heading}\n\n{zh}\n\n"
        + f"{cfg.en_heading}\n\n{en}\n\n"
        + "## 长度自检\n"
        + f"- 中文摘要字符数：{report['zh']['len']}/{cfg.zh_max}\n"
        + f"- 英文摘要字符数：{report['en']['len']}/{cfg.en_max}\n"
    )
    out_path.write_text(out_text, encoding="utf-8")

    if args.json:
        # Keep stdout strictly machine-readable.
        sys.stdout.write(json.dumps(report, ensure_ascii=False))
        sys.stdout.write("\n")
        print(f"[OK] Wrote: {out_path}", file=sys.stderr)
    else:
        print(f"[OK] Wrote: {out_path}")
        print(f"- TITLE: {'OK' if title_ok else 'INVALID'}")
        print(f"- ZH: {report['zh']['len']}/{cfg.zh_max} ({'OK' if zh_ok else 'EXCEEDED'})")
        print(f"- EN: {report['en']['len']}/{cfg.en_max} ({'OK' if en_ok else 'EXCEEDED'})")

    if args.strict and (not zh_ok or not en_ok):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
