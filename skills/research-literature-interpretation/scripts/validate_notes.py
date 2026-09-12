#!/usr/bin/env python3
"""Mechanical lint for research-literature-interpretation notes; not a scientific review."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


PLACEHOLDERS = ("页码待补", "完整实验细节需阅读 PDF", "后续工作通常沿三条线发展")
DEFAULT_LEVELS = ("原文事实", "作者主张", "我的解释|我的解读", "待验证")
EVIDENCE_CONTRACT = "research-literature-interpretation-evidence-v1"
EVIDENCE_DEPTHS = {"normative", "fulltext", "abstract", "web", "source"}
EVIDENCE_FIELDS = (
    "source_id", "evidence_depth", "read_scope", "stable_citation", "question",
    "method", "key_results", "limitations", "supports_or_refutes",
)
ANCHOR_RE = re.compile(
    r"(?:第\s*\d+(?:[.–—-]\d+)?\s*(?:页|节)|(?:表|图|式|算法|Table|Figure|Fig\.?|Eq\.?|Algorithm|Theorem|Lemma|Proposition)\s*[A-Za-z]?\d+(?:[.–—-]\d+)?|附录\s*[A-Za-z0-9.]+|§\s*[\dA-Za-z.]+|pp?\.\s*\d+(?:[–—-]\d+)?)",
    re.IGNORECASE,
)


def load_simple_config(skill_root: Path) -> dict[str, int | tuple[str, ...]]:
    config: dict[str, int | tuple[str, ...]] = {
        "paragraph_hard_max_chars": 160,
        "max_sentences_per_paragraph": 4,
        "max_bold_spans_per_section": 3,
        "max_blockquotes_per_section": 1,
        "required_knowledge_levels": DEFAULT_LEVELS,
    }
    path = skill_root / "config.yaml"
    if not path.is_file():
        return config
    section = ""
    levels: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not raw.startswith(" ") and line.endswith(":"):
            section = line[:-1]
            continue
        if section == "style" and ":" in line:
            key, value = [part.strip() for part in line.split(":", 1)]
            if key in config:
                try:
                    parsed = int(value)
                except ValueError as exc:
                    raise ValueError(f"config style.{key} must be an integer: {value}") from exc
                if parsed <= 0:
                    raise ValueError(f"config style.{key} must be positive: {parsed}")
                config[key] = parsed
        elif section == "validation" and line.startswith("- "):
            levels.append(line[2:].strip())
    if levels:
        config["required_knowledge_levels"] = tuple(levels)
    return config


def validate_note(path: Path, *, style: bool = False, config: dict | None = None) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["missing note file"]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read note: {exc}"]
    if not re.search(r"^#\s+\S", text, re.MULTILINE):
        errors.append("missing note title")
    frontmatter = parse_frontmatter(text)
    if frontmatter.get("interpretation_contract") != EVIDENCE_CONTRACT:
        errors.append(f"missing or unsupported interpretation_contract: {EVIDENCE_CONTRACT}")
    else:
        for field in EVIDENCE_FIELDS:
            if not frontmatter.get(field, "").strip():
                errors.append(f"missing evidence field: {field}")
        if frontmatter.get("evidence_depth") not in EVIDENCE_DEPTHS:
            errors.append("evidence_depth must be normative/fulltext/abstract/web/source")
        if frontmatter.get("evidence_depth") == "fulltext" and re.search(r"摘要|abstract only|仅摘要", frontmatter.get("read_scope", ""), re.I):
            errors.append("fulltext evidence_depth conflicts with abstract-only read_scope")
    if not re.search(r"(?:来源|source|阅读范围|reading scope)", text, re.IGNORECASE):
        errors.append("missing source or reading-scope statement")
    if not re.search(r"(?:https?://|doi|arxiv|一手\s*(?:来源|URL)|本地\s*(?:文件|PDF))", text, re.IGNORECASE):
        errors.append("missing identifiable source")
    if not re.search(r"(?:主张|claim|结论|判断|hypothesis|thesis)", text, re.IGNORECASE):
        errors.append("missing claim or conclusion")
    if not re.search(r"(?:局限|限制|反例|缺口|未报告|待验证|不支持|边界)", text):
        errors.append("missing evidence boundary or uncertainty")
    for placeholder in PLACEHOLDERS:
        if placeholder in text:
            errors.append(f"placeholder remains: {placeholder}")
    anchors = set(ANCHOR_RE.findall(text))
    if not anchors:
        errors.append("no traceable evidence anchor")
    active = config or {}
    levels = active.get("required_knowledge_levels", DEFAULT_LEVELS)
    for level in levels:
        if not any(alias in text for alias in str(level).split("|")):
            errors.append(f"missing knowledge level: {level}")
    if not re.search(r"访问日期[： :]\s*20\d{2}-\d{2}-\d{2}", text):
        errors.append("missing source access date")
    if style:
        errors.extend(validate_style(text, active))
    return errors


def parse_frontmatter(text: str) -> dict[str, str]:
    """读取契约所需的简单标量字段；复杂正文仍由 Markdown 人工审查。"""
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match[1].splitlines():
        key, separator, value = line.partition(":")
        if separator and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key.strip()):
            fields[key.strip()] = value.strip().strip("'\"")
    return fields


def content_blocks(text: str) -> list[str]:
    if text.startswith("---\n") and "\n---\n" in text:
        text = text.split("\n---\n", 1)[1]
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"\\\[[\s\S]*?\\\]", "", text)
    blocks = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or all(line.startswith(("#", ">", "|")) for line in lines):
            continue
        if all(line.startswith(("- ", "* ")) for line in lines):
            blocks.extend(line[2:].strip() for line in lines)
        else:
            blocks.append(" ".join(lines))
    return blocks


def validate_style(text: str, config: dict) -> list[str]:
    warnings: list[str] = []
    max_chars = int(config.get("paragraph_hard_max_chars", 160))
    for index, block in enumerate(content_blocks(text), 1):
        visible = re.sub(r"[`*_]", "", block)
        if len(visible) > max_chars:
            warnings.append(f"style: paragraph {index} exceeds {max_chars} chars ({len(visible)})")
        sentence_count = len(re.findall(r"[。！？!?](?:[”’」』])?", visible))
        max_sentences = int(config.get("max_sentences_per_paragraph", 4))
        if sentence_count > max_sentences:
            warnings.append(f"style: paragraph {index} has {sentence_count} sentences (max {max_sentences})")
    body = text.split("\n---\n", 1)[-1] if text.startswith("---\n") else text
    body = re.sub(r"```[\s\S]*?```", "", body)
    sections = re.split(r"(?m)^#{1,6}\s+", body)
    max_bold = int(config.get("max_bold_spans_per_section", 3))
    max_quotes = int(config.get("max_blockquotes_per_section", 1))
    for index, section in enumerate(sections[1:], 1):
        bold_count = len(re.findall(r"\*\*[^*\n]+\*\*", section))
        quote_count = len(re.findall(r"(?m)^>\s+", section))
        if bold_count > max_bold:
            warnings.append(f"style: section {index} has {bold_count} bold spans (max {max_bold})")
        if quote_count > max_quotes:
            warnings.append(f"style: section {index} has {quote_count} blockquotes (max {max_quotes})")
    return warnings


def note_paths(args: argparse.Namespace) -> list[Path]:
    if args.notes:
        return args.notes
    ids = [
        line.removeprefix("- ").strip()
        for line in args.ids_file.read_text(encoding="utf-8").splitlines()
        if line.startswith("- ")
    ]
    return [args.papers / paper_id / f"{paper_id}.md" for paper_id in ids]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical lint only; independent evidence review is still required."
    )
    parser.add_argument("notes", nargs="*", type=Path)
    parser.add_argument("--papers", type=Path, default=Path("docs/papers"))
    parser.add_argument("--ids-file", type=Path)
    parser.add_argument("--style", action="store_true", help="also enforce configurable mobile-reading style limits")
    parser.add_argument("--allow-legacy", action="store_true", help="只读检查旧笔记；不认证新的证据契约")
    args = parser.parse_args()
    if not args.notes and args.ids_file is None:
        parser.error("provide note paths or --ids-file")

    failures = 0
    try:
        config = load_simple_config(Path(__file__).resolve().parent.parent)
    except ValueError as exc:
        parser.error(str(exc))
    paths = note_paths(args)
    for path in paths:
        errors = validate_note(path, style=args.style, config=config)
        if args.allow_legacy:
            errors = [error for error in errors if not (error.startswith("missing or unsupported interpretation_contract") or error.startswith("missing evidence field") or error.startswith("evidence_depth"))]
        if errors:
            failures += 1
            for error in errors:
                print(f"{path}: {error}")
    if failures:
        print(f"note lint failed: {failures}/{len(paths)}")
        return 1
    print(f"note lint ok: {len(paths)} notes (mechanical gate only; style={'on' if args.style else 'off'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
