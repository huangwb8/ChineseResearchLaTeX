#!/usr/bin/env python3
"""
Validate abstract length constraints for nsfc-abstract skill output.

Expected input contains:
  [TITLE] ... [/TITLE]   (optional / configurable)
  [ZH] ... [/ZH]
  [EN] ... [/EN]
  [FIELD] ... [/FIELD]   ("主要研究领域" section; optional / configurable)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_block(text: str, begin: str, end: str) -> str:
    # Non-greedy across newlines
    pattern = re.compile(re.escape(begin) + r"(.*?)" + re.escape(end), re.DOTALL)
    m = pattern.search(text)
    if not m:
        raise ValueError(f"未找到分段标记：{begin}...{end}")
    return m.group(1).strip()

def _extract_blocks_by_headings(text: str, zh_heading: str, en_heading: str) -> Tuple[str, str]:
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

    if zh_i is None or en_i is None or zh_i > en_i:
        raise ValueError(f"未找到标题分段：{zh_heading} 与 {en_heading}")

    zh = "\n".join(lines[zh_i + 1 : en_i]).strip()

    # EN content ends at the next markdown heading (any level) if present,
    # e.g. "## 长度自检" appended by writer script.
    en_lines = []
    for line in lines[en_i + 1 :]:
        if line.lstrip().startswith("#"):
            break
        en_lines.append(line)
    en = "\n".join(en_lines).strip()
    if not zh or not en:
        raise ValueError("标题分段已找到，但内容为空（请在标题下方写入正文）")
    return zh, en


def _normalize_for_count(text: str) -> str:
    # Abstracts are typically submitted as a single paragraph. Users may format
    # outputs with newlines/spaces for readability; count after collapsing
    # whitespace to reduce surprises.
    return re.sub(r"\s+", " ", text).strip()

def _count_ascii_double_quotes(text: str) -> int:
    # In Chinese abstracts, avoid ASCII double quotes ("). Prefer “ ... ” instead.
    return text.count("\"")

def _count_numeric_commas(text: str) -> int:
    # In Chinese abstracts, avoid comma as number separator, e.g. "1,000" / "1，000".
    # Only count commas that appear *between* digits to avoid false positives.
    return len(re.findall(r"(?<=\d)[,，](?=\d)", text))

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
    zh_heading: str
    en_heading: str
    out_name: str
    title_required: bool
    title_candidates_default: int
    title_begin: str
    title_end: str
    title_heading: str
    field_required: bool
    field_begin: str
    field_end: str
    field_heading: str


def _load_limits_from_config(skill_root: Path) -> SkillConfig:
    """
    Avoid external deps (PyYAML). We only need a few scalar fields, so parse by regex.
    """
    config_path = skill_root / "config.yaml"
    if not config_path.exists():
        return SkillConfig(
            zh_max=400,
            en_max=4000,
            zh_begin="[ZH]",
            zh_end="[/ZH]",
            en_begin="[EN]",
            en_end="[/EN]",
            zh_heading="# 中文摘要",
            en_heading="# English Abstract",
            out_name="NSFC-ABSTRACTS.md",
            title_required=False,
            title_candidates_default=5,
            title_begin="[TITLE]",
            title_end="[/TITLE]",
            title_heading="# 标题建议",
            field_required=False,
            field_begin="[FIELD]",
            field_end="[/FIELD]",
            field_heading="# 主要研究领域",
        )

    raw = config_path.read_text(encoding="utf-8")

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
        # NOTE: use real whitespace class `[ \t]` (not `\\t`), otherwise it would also match literal 't'.
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
    zh_heading = _str("zh_heading", "# 中文摘要")
    en_heading = _str("en_heading", "# English Abstract")
    out_name = _str("filename", "NSFC-ABSTRACTS.md")

    title_required = _parse_bool(_get_scalar("title_required"), False)
    title_candidates_default = _int("title_candidates_default", 5)
    title_begin = _str("title_begin", "[TITLE]")
    title_end = _str("title_end", "[/TITLE]")
    title_heading = _str("title_heading", "# 标题建议")

    field_required = _parse_bool(_get_scalar("field_required"), False)
    field_begin = _str("field_begin", "[FIELD]")
    field_end = _str("field_end", "[/FIELD]")
    field_heading = _str("field_heading", "# 主要研究领域")

    return SkillConfig(
        zh_max=zh_max,
        en_max=en_max,
        zh_begin=zh_begin,
        zh_end=zh_end,
        en_begin=en_begin,
        en_end=en_end,
        zh_heading=zh_heading,
        en_heading=en_heading,
        out_name=out_name,
        title_required=title_required,
        title_candidates_default=title_candidates_default,
        title_begin=title_begin,
        title_end=title_end,
        title_heading=title_heading,
        field_required=field_required,
        field_begin=field_begin,
        field_end=field_end,
        field_heading=field_heading,
    )


def _extract_section_by_heading(text: str, heading: str) -> Optional[str]:
    lines = text.splitlines()

    def _is_heading(line: str, h: str) -> bool:
        return line.strip() == h.strip()

    start_i = None
    for i, line in enumerate(lines):
        if _is_heading(line, heading):
            start_i = i
            break
    if start_i is None:
        return None
    body_lines = []
    for line in lines[start_i + 1 :]:
        if line.lstrip().startswith("#"):
            break
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return body or None


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


def build_title_report(title_raw: Optional[str], *, required: bool, min_candidates: int) -> dict:
    title = (title_raw or "").strip()
    present = bool(title)
    recommended_ok = bool(re.search(r"(?m)^\s*推荐标题\s*[:：]\s*\S+", title))
    cand_lines = re.findall(r"(?m)^\s*(?:[-*]\s*)?\d+[\)\.、]\s+\S+", title)
    cand_n = len(cand_lines)
    ok = (not required) or (present and recommended_ok and cand_n >= int(min_candidates))
    return {
        "present": present,
        "required": bool(required),
        "has_recommended": recommended_ok,
        "candidates": cand_n,
        "min_candidates": int(min_candidates),
        "ok": ok,
    }

def build_field_report(field_raw: Optional[str], *, required: bool) -> dict:
    field = (field_raw or "").strip()
    present = bool(field)
    ok = (not required) or present
    return {"present": present, "required": bool(required), "ok": ok}


def _build_report(zh_raw: str, en_raw: str, *, zh_max: int, en_max: int) -> dict:
    """
    Build a machine-readable report.

    Note: length counting collapses consecutive whitespace into a single space.
    """
    zh = _normalize_for_count(zh_raw)
    en = _normalize_for_count(en_raw)

    zh_len = len(zh)
    en_len = len(en)
    zh_exceeded = max(0, zh_len - zh_max)
    en_exceeded = max(0, en_len - en_max)

    zh_ascii_dq = _count_ascii_double_quotes(zh_raw)
    zh_numeric_commas = _count_numeric_commas(zh_raw)
    zh_punct_ok = zh_ascii_dq == 0
    zh_num_ok = zh_numeric_commas == 0
    zh_len_ok = zh_exceeded == 0

    en_len_ok = en_exceeded == 0

    return {
        "zh": {
            "len": zh_len,
            "max": zh_max,
            "exceeded": zh_exceeded,
            "len_ok": zh_len_ok,
            "ascii_double_quotes": zh_ascii_dq,
            "numeric_commas": zh_numeric_commas,
            "punct_ok": zh_punct_ok,
            "num_ok": zh_num_ok,
            "ok": zh_len_ok and zh_punct_ok and zh_num_ok,
        },
        "en": {
            "len": en_len,
            "max": en_max,
            "exceeded": en_exceeded,
            "len_ok": en_len_ok,
            "ok": en_len_ok,
        },
    }


# Public alias for reuse by other scripts (write_abstracts_md.py).
build_report = _build_report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "Validate nsfc-abstract output constraints.\n"
            "It extracts ZH/EN blocks, then counts characters. Title/Field sections may be required by config.\n"
            "Counting collapses consecutive whitespace into a single space by default.\n"
            "In --strict mode, it also enforces: ZH no ASCII double quotes (\") and no digit-comma-digit (1,000)."
        ),
        epilog=(
            "Exit codes:\n"
            "  0  success (and within limits when --strict is used)\n"
            "  1  constraint violations with --strict\n"
            "  2  input format error / missing required sections\n"
        ),
    )
    ap.add_argument("file", help="包含 [ZH]/[EN] 分段标记的文本文件路径（或 - 表示 stdin）")
    ap.add_argument("--strict", action="store_true", help="严格模式：超限/中文标点/数字格式不合规则返回非 0")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果（机器可读；仅打印 JSON）")
    ap.add_argument("--diff", action="store_true", help="输出超出字符数（exceeded= max(0, len-max)）")
    ap.add_argument(
        "--require-title",
        action="store_true",
        help="要求存在标题建议分段（默认取 config.yaml:title.title_required）",
    )
    ap.add_argument(
        "--no-title",
        action="store_true",
        help="忽略标题建议分段（不做检查；向后兼容旧输出）",
    )
    ap.add_argument(
        "--min-title-candidates",
        type=int,
        default=0,
        help="标题候选最少数量（默认取 config.yaml:title.title_candidates_default；0 表示使用默认值）",
    )
    ap.add_argument(
        "--require-field",
        action="store_true",
        help="要求存在“主要研究领域”分段（默认取 config.yaml:field.field_required）",
    )
    ap.add_argument(
        "--no-field",
        action="store_true",
        help="忽略“主要研究领域”分段（不做检查；向后兼容旧输出）",
    )
    args = ap.parse_args(argv)

    skill_root = Path(__file__).resolve().parents[1]
    cfg = _load_limits_from_config(skill_root)

    if args.file == "-":
        text = sys.stdin.read()
    else:
        text = _read_text(Path(args.file))

    zh_raw = None
    en_raw = None
    try:
        zh_raw = _extract_block(text, cfg.zh_begin, cfg.zh_end)
        en_raw = _extract_block(text, cfg.en_begin, cfg.en_end)
    except ValueError:
        # Fall back to heading-based extraction.
        try:
            zh_raw, en_raw = _extract_blocks_by_headings(text, cfg.zh_heading, cfg.en_heading)
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            print("", file=sys.stderr)
            print("修复提示（两种任选其一）：", file=sys.stderr)
            print("A) 标记格式：", file=sys.stderr)
            print(f"{cfg.zh_begin}\n（中文摘要正文）\n{cfg.zh_end}", file=sys.stderr)
            print(f"{cfg.en_begin}\n(English abstract translation)\n{cfg.en_end}", file=sys.stderr)
            print(f"{cfg.field_begin}\n- （主要研究领域要点）\n{cfg.field_end}", file=sys.stderr)
            print("", file=sys.stderr)
            print("B) 标题格式（推荐，便于直接保存为文件）：", file=sys.stderr)
            print(
                f"{cfg.zh_heading}\n（中文摘要正文）\n\n{cfg.en_heading}\n(English abstract translation)\n\n{cfg.field_heading}\n- （主要研究领域要点）",
                file=sys.stderr,
            )
            print("", file=sys.stderr)
            print(f"提示：本 skill 约定输出文件为工作目录下的 `{cfg.out_name}`（可用 write_abstracts_md.py 生成）。", file=sys.stderr)
            return 2

    zh_raw_len = len(zh_raw)
    en_raw_len = len(en_raw)

    report = _build_report(zh_raw, en_raw, zh_max=cfg.zh_max, en_max=cfg.en_max)
    zh_ok = bool(report["zh"]["ok"])
    en_ok = bool(report["en"]["ok"])

    # Title section (optional, but required by config/flags).
    title_required = bool(args.require_title or cfg.title_required) and (not args.no_title)
    min_cands = int(args.min_title_candidates) if int(args.min_title_candidates) > 0 else int(cfg.title_candidates_default)
    title_raw: Optional[str] = None
    if not args.no_title:
        try:
            title_raw = _extract_block(text, cfg.title_begin, cfg.title_end)
        except ValueError:
            title_raw = _extract_title_by_headings(text, cfg.title_heading, cfg.zh_heading)
    title_report = build_title_report(title_raw, required=title_required, min_candidates=min_cands)
    report["title"] = title_report

    # Field section (optional, but may be required by config/flags).
    field_required = bool(args.require_field or cfg.field_required) and (not args.no_field)
    field_raw: Optional[str] = None
    if not args.no_field:
        try:
            field_raw = _extract_block(text, cfg.field_begin, cfg.field_end)
        except ValueError:
            field_raw = _extract_section_by_heading(text, cfg.field_heading)
    field_report = build_field_report(field_raw, required=field_required)
    report["field"] = field_report

    if title_required and not title_report["present"]:
        if args.json:
            # Still emit the report for machine debugging.
            sys.stdout.write(json.dumps(report, ensure_ascii=False))
            sys.stdout.write("\n")
        else:
            print("", file=sys.stderr)
            print("[ERROR] 缺少标题建议分段。修复提示：", file=sys.stderr)
            print(f"{cfg.title_begin}\n推荐标题：...\n1) ... —— 理由：...\n2) ... —— 理由：...\n...\n{cfg.title_end}", file=sys.stderr)
            print("", file=sys.stderr)
            print("或使用 Markdown 标题：", file=sys.stderr)
            print(
                f"{cfg.title_heading}\n推荐标题：...\n1) ... —— 理由：...\n...\n\n{cfg.zh_heading}\n（中文摘要正文）",
                file=sys.stderr,
            )
        return 2

    if field_required and not field_report["present"]:
        if args.json:
            sys.stdout.write(json.dumps(report, ensure_ascii=False))
            sys.stdout.write("\n")
        else:
            print("", file=sys.stderr)
            print("[ERROR] 缺少“主要研究领域”分段。修复提示：", file=sys.stderr)
            print(f"{cfg.field_begin}\n- ...\n{cfg.field_end}", file=sys.stderr)
            print("", file=sys.stderr)
            print("或使用 Markdown 标题：", file=sys.stderr)
            print(f"{cfg.field_heading}\n- ...\n\n{cfg.zh_heading}\n（中文摘要正文）", file=sys.stderr)
        return 2

    if args.json:
        # Keep stdout strictly machine-readable.
        sys.stdout.write(json.dumps(report, ensure_ascii=False))
        sys.stdout.write("\n")
        if args.strict and (not zh_ok or not en_ok or not title_report["ok"] or not field_report["ok"]):
            return 1
        return 0

    print("Length Check (whitespace-collapsed)")
    print(f"- Limits: ZH<= {cfg.zh_max}, EN<= {cfg.en_max}")
    print(
        f"- Markers: ZH {cfg.zh_begin}..{cfg.zh_end}; EN {cfg.en_begin}..{cfg.en_end}; FIELD {cfg.field_begin}..{cfg.field_end}"
    )
    print(f"- Headings: ZH {cfg.zh_heading}; EN {cfg.en_heading}; FIELD {cfg.field_heading}")

    def _status(lang_report: dict) -> str:
        if not lang_report.get("len_ok", True):
            return "EXCEEDED"
        if lang_report.get("punct_ok", True) is False:
            return "INVALID_PUNCT"
        if lang_report.get("num_ok", True) is False:
            return "INVALID_NUM"
        return "OK"

    print(
        f"- ZH: {report['zh']['len']}/{cfg.zh_max} ({_status(report['zh'])}) [raw={zh_raw_len}]"
        + (f" [exceeded={report['zh']['exceeded']}]" if args.diff else "")
    )
    if report["zh"].get("ascii_double_quotes", 0) > 0:
        print(f"- ZH quotes: ASCII (\") = {report['zh']['ascii_double_quotes']} (请改为中文引号“...”)")
    if report["zh"].get("numeric_commas", 0) > 0:
        print(f"- ZH numbers: digit-comma-digit = {report['zh']['numeric_commas']} (请改为 1000 而不是 1,000)")
    print(
        f"- EN: {report['en']['len']}/{cfg.en_max} ({_status(report['en'])}) [raw={en_raw_len}]"
        + (f" [exceeded={report['en']['exceeded']}]" if args.diff else "")
    )
    if not args.no_title:
        print(
            f"- TITLE: {'OK' if title_report['ok'] else 'INVALID'} "
            f"[required={title_required}, candidates={title_report['candidates']}/{min_cands}, "
            f"recommended={title_report['has_recommended']}]"
        )
    if not args.no_field:
        print(f"- FIELD: {'OK' if field_report['ok'] else 'INVALID'} [required={field_required}]")

    if args.strict and (not zh_ok or not en_ok or not title_report["ok"] or not field_report["ok"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
