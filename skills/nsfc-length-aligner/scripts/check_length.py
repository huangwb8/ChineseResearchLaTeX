#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class _ConfigError(RuntimeError):
    pass


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover
        raise _ConfigError(
            "PyYAML is required to run this checker. Install it with: pip install pyyaml"
        ) from e
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise _ConfigError(f"Invalid config.yaml: expected mapping at root: {path}")
    return data


def _strip_tex_comments(text: str) -> str:
    out_lines: list[str] = []
    for line in text.splitlines():
        buf: list[str] = []
        escaped = False
        for ch in line:
            if escaped:
                buf.append(ch)
                escaped = False
                continue
            if ch == "\\":
                buf.append(ch)
                escaped = True
                continue
            if ch == "%":
                break
            buf.append(ch)
        out_lines.append("".join(buf))
    return "\n".join(out_lines)


def _mask_tex_comments(text: str) -> str:
    """Replace TeX comments with spaces, preserving string length.

    Useful when we need stable character offsets (e.g. for section splitting).
    """

    out_lines: list[str] = []
    for line in text.splitlines(keepends=False):
        buf: list[str] = []
        escaped = False
        in_comment = False
        for ch in line:
            if in_comment:
                buf.append(" ")
                continue
            if escaped:
                buf.append(ch)
                escaped = False
                continue
            if ch == "\\":
                buf.append(ch)
                escaped = True
                continue
            if ch == "%":
                buf.append(" ")
                in_comment = True
                continue
            buf.append(ch)
        out_lines.append("".join(buf))
    return "\n".join(out_lines)


_RE_MATH_INLINE = re.compile(r"\$(?:\\.|[^$\\])*\$")
_RE_MATH_PAREN = re.compile(r"\\\((?:.|\n)*?\\\)")
_RE_MATH_BRACK = re.compile(r"\\\[(?:.|\n)*?\\\]")
_RE_COMMAND = re.compile(r"\\[A-Za-z@]+\*?")
_RE_ENV = re.compile(r"\\(begin|end)\s*\{[^}]+\}")


def _tex_visible_text(text: str, *, strip_math: bool, strip_commands: bool) -> str:
    text = _strip_tex_comments(text)
    text = _RE_ENV.sub(" ", text)
    if strip_math:
        text = _RE_MATH_BRACK.sub(" ", text)
        text = _RE_MATH_PAREN.sub(" ", text)
        text = _RE_MATH_INLINE.sub(" ", text)
    if strip_commands:
        text = _RE_COMMAND.sub(" ", text)
    text = text.replace("~", " ")
    text = text.replace("\\\\", " ")
    text = re.sub(r"[{}\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _md_visible_text(text: str) -> str:
    # Extremely lightweight markdown text extraction.
    text = re.sub(r"```(?:.|\n)*?```", " ", text)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _count_unit(text: str, unit: str) -> int:
    if not text:
        return 0
    if unit == "cjk_chars":
        return len(re.findall(r"[\u4e00-\u9fff]", text))
    if unit == "chars":
        return len(re.sub(r"\s+", "", text))
    raise _ConfigError(f"Unsupported unit: {unit!r} (supported: cjk_chars, chars)")

def _count_all_units(text: str) -> dict[str, int]:
    return {
        "cjk_chars": _count_unit(text, "cjk_chars"),
        "chars": _count_unit(text, "chars"),
    }


def _read_balanced_braces(text: str, brace_start: int) -> tuple[str, int] | None:
    """Return (inner_text, end_idx_after_closing_brace) for a {...} block.

    This is a minimal TeX-ish brace reader to make section title parsing robust
    against nested braces (e.g. \\texorpdfstring{...}{...}) and line breaks.
    """

    if brace_start < 0 or brace_start >= len(text) or text[brace_start] != "{":
        return None
    depth = 1
    i = brace_start + 1
    buf: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            # Preserve escapes so downstream stripping stays consistent.
            buf.append(ch)
            i += 1
            if i < len(text):
                buf.append(text[i])
                i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(buf), i + 1
        buf.append(ch)
        i += 1
    return None


def _split_tex_sections(
    raw_tex: str,
    *,
    commands: list[str],
    strip_math: bool,
    strip_commands: bool,
) -> list[tuple[str, str]]:
    safe = [c.strip() for c in commands if c and str(c).strip()]
    if not safe:
        safe = ["section", "subsection", "subsubsection"]
    joined = "|".join(re.escape(c) for c in safe)
    marker_re = re.compile(rf"\\({joined})\*?\s*\{{")

    markers: list[tuple[int, int, str]] = []
    # Mask comments (preserve offsets) to avoid treating commented-out headings as real.
    hay = _mask_tex_comments(raw_tex)
    for m in marker_re.finditer(hay):
        brace_start = m.end() - 1  # points to the '{' matched by the pattern
        parsed = _read_balanced_braces(hay, brace_start)
        if not parsed:
            continue
        title_raw, title_end = parsed
        title = _tex_visible_text(title_raw, strip_math=strip_math, strip_commands=strip_commands) or m.group(1)
        markers.append((m.start(), title_end, title))

    if not markers:
        return []

    sections: list[tuple[str, str]] = []
    last_title = "(no section)"
    last_start = 0
    for start_pos, title_end, title in markers:
        sections.append((last_title, raw_tex[last_start:start_pos]))
        last_title = title
        last_start = title_end
    sections.append((last_title, raw_tex[last_start:]))

    # If we have real sections, drop the leading "(no section)" chunk to reduce noise.
    if len(sections) > 1 and sections and sections[0][0] == "(no section)":
        sections = sections[1:]
    return sections


@dataclass(frozen=True)
class _Budget:
    name: str
    match: str
    target: int | None
    min_value: int | None
    max_value: int | None
    notes: str | None

    def bounds(self, *, tolerance_ratio: float) -> tuple[int | None, int | None]:
        if self.min_value is not None or self.max_value is not None:
            return self.min_value, self.max_value
        if self.target is None:
            return None, None
        delta = max(1, int(round(self.target * tolerance_ratio)))
        return self.target - delta, self.target + delta


def _iter_input_files(
    root: Path,
    *,
    include_globs: list[str],
    exclude_globs: list[str],
) -> Iterable[Path]:
    def _matches(path: str, pattern: str) -> bool:
        # Make common glob patterns behave intuitively for root-relative paths:
        # - "**/foo/**" should also match "foo/..."
        # - "./foo/**" should also match "foo/..."
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]):
            return True
        if pattern.startswith("./") and fnmatch.fnmatch(path, pattern[2:]):
            return True
        return False

    if root.is_file():
        rel = root.name
        if any(_matches(rel, g) for g in exclude_globs):
            return []
        if any(_matches(rel, g) for g in include_globs):
            return [root]
        return []

    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root))
        if any(_matches(rel, g) for g in exclude_globs):
            continue
        if any(_matches(p.name, g) for g in include_globs) or any(_matches(rel, g) for g in include_globs):
            out.append(p)
    return out


_RE_DOC_CLASS = re.compile(r"\\documentclass\b")
_RE_BEGIN_DOC = re.compile(r"\\begin\s*\{document\}")
_RE_INPUT = re.compile(r"\\(input|include|subfile)\s*\{([^}]+)\}")


def _looks_like_main_tex(text: str) -> bool:
    # Heuristic: a main TeX file usually has both markers.
    return bool(_RE_DOC_CLASS.search(text) and _RE_BEGIN_DOC.search(text))


def _detect_main_tex(root: Path, *, exclude_globs: list[str]) -> Path | None:
    """Best-effort detection of the proposal's main LaTeX file.

    Preference order:
    1) <root>/main.tex (common in both NSFC_Young and NSFC_General templates)
    2) any .tex under root that contains both \\documentclass and \\begin{document}
    """

    def _glob_match(path: str, pattern: str) -> bool:
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]):
            return True
        if pattern.startswith("./") and fnmatch.fnmatch(path, pattern[2:]):
            return True
        return False

    def _excluded(p: Path) -> bool:
        rel = str(p.relative_to(root))
        return any(_glob_match(rel, g) or _glob_match(p.name, g) for g in exclude_globs)

    if root.is_file():
        if root.suffix.lower() != ".tex":
            return None
        if _looks_like_main_tex(_read_text(root)):
            return root
        return None

    main = root / "main.tex"
    if main.exists() and main.is_file() and not _excluded(main):
        if _looks_like_main_tex(_read_text(main)):
            return main

    # Fallback: scan for a file that looks like a main entry.
    candidates = [p for p in sorted(root.rglob("*.tex")) if p.is_file() and not _excluded(p)]
    for p in candidates:
        try:
            if _looks_like_main_tex(_read_text(p)):
                return p
        except Exception:
            continue
    return None


def _resolve_input_path(current_file: Path, arg: str) -> Path | None:
    arg = arg.strip()
    if not arg or "\\" in arg:
        # Likely a macro, or an invalid path for our simple resolver.
        return None
    # TeX allows extensionless inputs.
    candidates = [arg]
    if not Path(arg).suffix:
        candidates.append(arg + ".tex")
    for cand in candidates:
        p = (current_file.parent / cand).resolve()
        if p.exists() and p.is_file():
            return p
    return None


def _collect_included_files(main_tex: Path) -> list[Path]:
    """Collect TeX/MD files reachable from a main TeX via \\input/\\include.

    Notes:
    - Commented-out \\input lines are ignored.
    - This is a best-effort resolver; it intentionally skips macro-driven inputs.
    """

    seen: set[Path] = set()
    order: list[Path] = []
    queue: list[Path] = [main_tex]

    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        order.append(cur)

        try:
            raw = _read_text(cur)
        except Exception:
            continue

        # Strip comments first so optional blocks (commented inputs) won't be counted.
        for _, arg in _RE_INPUT.findall(_strip_tex_comments(raw)):
            resolved = _resolve_input_path(cur, arg)
            if not resolved:
                continue
            if resolved.suffix.lower() in {".tex", ".md", ".markdown"}:
                queue.append(resolved)

    return order


def _load_budgets(
    cfg: dict[str, Any],
) -> tuple[str, float, dict[str, Any], dict[str, Any], list[_Budget]]:
    std = cfg.get("length_standard") or {}
    if not isinstance(std, dict):
        raise _ConfigError("config.yaml:length_standard must be a mapping")
    unit = str(std.get("unit") or "cjk_chars")
    tolerance_ratio = float(std.get("tolerance_ratio") or 0.08)
    overall = std.get("overall") or {}
    if not isinstance(overall, dict):
        overall = {}
    pages = std.get("pages") or {}
    if not isinstance(pages, dict):
        pages = {}
    file_rules_raw = std.get("files") or []
    if not isinstance(file_rules_raw, list):
        raise _ConfigError("config.yaml:length_standard.files must be a list")
    budgets: list[_Budget] = []
    for item in file_rules_raw:
        if not isinstance(item, dict):
            continue
        budgets.append(
            _Budget(
                name=str(item.get("name") or item.get("match") or "unknown"),
                match=str(item.get("match") or ""),
                target=int(item["target"]) if "target" in item and item["target"] is not None else None,
                min_value=int(item["min"]) if "min" in item and item["min"] is not None else None,
                max_value=int(item["max"]) if "max" in item and item["max"] is not None else None,
                notes=str(item.get("notes")) if item.get("notes") else None,
            )
        )
    return unit, tolerance_ratio, overall, pages, budgets


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _count_pdf_pages(pdf_path: Path) -> int | None:
    # Best-effort page counting:
    # - Prefer pure-Python libraries if installed.
    # - Fall back to `pdfinfo` if available.
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        pass

    try:
        import PyPDF2  # type: ignore

        reader = PyPDF2.PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        pass

    try:
        cp = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if cp.returncode == 0 and cp.stdout:
            for line in cp.stdout.splitlines():
                if line.lower().startswith("pages:"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return _to_int(parts[1].strip())
    except Exception:
        pass
    return None


def _pick_budget(rel_path: str, budgets: list[_Budget]) -> _Budget | None:
    for b in budgets:
        if not b.match:
            continue
        if fnmatch.fnmatch(rel_path, b.match) or fnmatch.fnmatch(Path(rel_path).name, b.match):
            return b
    return None


def _render_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out: list[str] = []
    for idx, row in enumerate(rows):
        out.append("| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |")
        if idx == 0:
            out.append("| " + " | ".join("-" * widths[i] for i in range(len(widths))) + " |")
    return "\n".join(out)


def _load_template(skill_root: Path) -> str:
    template = skill_root / "templates" / "LENGTH_REPORT_TEMPLATE.md"
    if not template.exists():
        return "# 篇幅对齐报告\n\n（未找到模板）\n"
    return _read_text(template)


def _render_template(text: str, values: dict[str, str]) -> str:
    rendered = text
    for k, v in values.items():
        rendered = rendered.replace(f"{{{{{k}}}}}", v)
    return rendered


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="NSFC proposal length checker (file/section budgets)")
    parser.add_argument("--input", required=True, help="Path to proposal dir or a single file")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--pdf",
        default="",
        help="Optional PDF to count pages for (page limit is a hard constraint in 2026+ templates)",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory for reports (default: <input>/_artifacts/nsfc-length-aligner)",
    )
    parser.add_argument(
        "--fail-if-exists",
        action="store_true",
        help="Fail if report files already exist (prevents accidental overwrite)",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2

    config_path = Path(args.config).expanduser().resolve()
    if not config_path.exists():
        print(f"error: config not found: {config_path}", file=sys.stderr)
        return 2

    cfg = _load_yaml(config_path)
    unit, tolerance_ratio, overall, pages_cfg, budgets = _load_budgets(cfg)

    checker = cfg.get("checker") or {}
    if not isinstance(checker, dict):
        checker = {}
    include_globs = [str(x) for x in (checker.get("include_globs") or ["*.tex", "*.md"])]
    exclude_globs = [str(x) for x in (checker.get("exclude_globs") or [])]
    latex_cfg = checker.get("latex") or {}
    if not isinstance(latex_cfg, dict):
        latex_cfg = {}
    follow_inputs_raw = latex_cfg.get("follow_inputs", "auto")
    follow_inputs: str | bool
    if isinstance(follow_inputs_raw, bool):
        follow_inputs = follow_inputs_raw
    else:
        follow_inputs = str(follow_inputs_raw).strip().lower() if follow_inputs_raw is not None else "auto"
    section_commands = latex_cfg.get("section_commands") or ["section", "subsection", "subsubsection"]
    if not isinstance(section_commands, list):
        section_commands = ["section", "subsection", "subsubsection"]
    section_commands = [str(x) for x in section_commands]

    discovery: dict[str, Any] = {"mode": "filesystem"}
    base_dir = input_path if input_path.is_dir() else input_path.parent

    files: list[Path] = []
    main_tex: Path | None = None
    if (follow_inputs is True) or (follow_inputs == "auto"):
        main_tex = _detect_main_tex(input_path, exclude_globs=exclude_globs)
        if main_tex is not None:
            included = _collect_included_files(main_tex)

            def _glob_match(path: str, pattern: str) -> bool:
                if fnmatch.fnmatch(path, pattern):
                    return True
                if pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]):
                    return True
                if pattern.startswith("./") and fnmatch.fnmatch(path, pattern[2:]):
                    return True
                return False

            def _matches_any(path: str, patterns: list[str]) -> bool:
                name = Path(path).name
                return any(_glob_match(path, g) or _glob_match(name, g) for g in patterns)

            filtered: list[Path] = []
            for p in included:
                try:
                    rel = str(p.relative_to(base_dir))
                except Exception:
                    rel = p.name
                if _matches_any(rel, exclude_globs):
                    continue
                if _matches_any(rel, include_globs):
                    filtered.append(p)
            files = filtered
            discovery = {
                "mode": "latex_inputs",
                "main_tex": str(main_tex),
                "included_count": len(included),
                "counted_count": len(files),
            }

    if not files:
        files = list(_iter_input_files(input_path, include_globs=include_globs, exclude_globs=exclude_globs))
        discovery = {"mode": "filesystem", "counted_count": len(files)}
    file_results: list[dict[str, Any]] = []
    section_results: list[dict[str, Any]] = []
    unmatched_budget_files: list[str] = []

    total_value = 0
    totals_all = {"cjk_chars": 0, "chars": 0}
    for f in files:
        rel = str(f.relative_to(base_dir))
        raw = _read_text(f)

        visible = ""
        sections: list[tuple[str, str]] = []
        if f.suffix.lower() == ".tex":
            visible = _tex_visible_text(
                raw,
                strip_math=bool(latex_cfg.get("strip_math", True)),
                strip_commands=bool(latex_cfg.get("strip_commands", True)),
            )
            if bool(latex_cfg.get("split_sections", True)):
                sections = _split_tex_sections(
                    raw,
                    commands=section_commands,
                    strip_math=bool(latex_cfg.get("strip_math", True)),
                    strip_commands=bool(latex_cfg.get("strip_commands", True)),
                )
        elif f.suffix.lower() in {".md", ".markdown"}:
            visible = _md_visible_text(raw)
        else:
            continue

        all_counts = _count_all_units(visible)
        value = all_counts[unit]
        total_value += value
        totals_all["cjk_chars"] += all_counts["cjk_chars"]
        totals_all["chars"] += all_counts["chars"]
        budget = _pick_budget(rel, budgets)
        min_v, max_v = (None, None)
        budget_name = None
        budget_notes = None
        if budget:
            min_v, max_v = budget.bounds(tolerance_ratio=tolerance_ratio)
            budget_name = budget.name
            budget_notes = budget.notes
        else:
            unmatched_budget_files.append(rel)

        file_results.append(
            {
                "path": rel,
                "value": value,
                "unit": unit,
                "values": all_counts,
                "budget": {
                    "name": budget_name,
                    "min": min_v,
                    "max": max_v,
                    "target": budget.target if budget else None,
                    "notes": budget_notes,
                    "match": budget.match if budget else None,
                }
                if budget
                else None,
            }
        )

        if sections:
            for title, seg_raw in sections:
                seg_visible = _tex_visible_text(
                    seg_raw,
                    strip_math=bool(latex_cfg.get("strip_math", True)),
                    strip_commands=bool(latex_cfg.get("strip_commands", True)),
                )
                if not seg_visible:
                    continue
                section_results.append(
                    {
                        "file": rel,
                        "section": title,
                        "value": _count_unit(seg_visible, unit),
                        "unit": unit,
                    }
                )

    # Overall (text) budget can be expressed as:
    # - min/max (explicit), or
    # - target (+/- tolerance_ratio)
    overall_target = _to_int(overall.get("target"))
    overall_min_cfg = _to_int(overall.get("min"))
    overall_max_cfg = _to_int(overall.get("max"))
    overall_bounds = None
    overall_delta = None
    overall_budget_notes = overall.get("notes")
    overall_min = overall_min_cfg
    overall_max = overall_max_cfg
    if overall_min is None and overall_max is None and overall_target is not None:
        overall_min = overall_target - max(1, int(round(overall_target * tolerance_ratio)))
        overall_max = overall_target + max(1, int(round(overall_target * tolerance_ratio)))
    if overall_min is not None or overall_max is not None or overall_target is not None:
        overall_bounds = {"min": overall_min, "max": overall_max, "target": overall_target, "notes": overall_budget_notes}
        if overall_min is not None and total_value < overall_min:
            overall_delta = f"-{overall_min - total_value}"
        elif overall_max is not None and total_value > overall_max:
            overall_delta = f"+{total_value - overall_max}"
        else:
            overall_delta = "OK"

    # Optional page budget (PDF-based).
    pdf_path = Path(args.pdf).expanduser().resolve() if args.pdf else None
    page_count = None
    pdf_error = None
    if pdf_path:
        if not pdf_path.exists():
            pdf_error = f"pdf not found: {pdf_path}"
        elif pdf_path.suffix.lower() != ".pdf":
            pdf_error = f"not a pdf: {pdf_path}"
        else:
            page_count = _count_pdf_pages(pdf_path)
            if page_count is None:
                pdf_error = "failed to count pages (install `pypdf` or `PyPDF2`, or ensure `pdfinfo` is available)"

    pages_max = _to_int(pages_cfg.get("max"))
    pages_min = _to_int(pages_cfg.get("min"))
    pages_target = _to_int(pages_cfg.get("target"))
    pages_hard_max = _to_int(pages_cfg.get("hard_max"))
    pages_notes = pages_cfg.get("notes")

    # If only target is given, interpret it as "recommended max" by default.
    if pages_max is None and pages_target is not None:
        pages_max = pages_target

    page_delta = None
    if page_count is not None:
        if pages_hard_max is not None and page_count > pages_hard_max:
            page_delta = f"FAIL:+{page_count - pages_hard_max} (over hard_max)"
        elif pages_max is not None and page_count > pages_max:
            page_delta = f"WARN:+{page_count - pages_max} (over max)"
        elif pages_min is not None and page_count < pages_min:
            page_delta = f"-{pages_min - page_count}"
        else:
            page_delta = "OK"

    report = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "unit": unit,
        "tolerance_ratio": tolerance_ratio,
        "input": str(input_path),
        "discovery": discovery,
        "pdf": {
            "path": str(pdf_path) if pdf_path else None,
            "page_count": page_count,
            "error": pdf_error,
        },
        "file_count": len(file_results),
        "total_value": total_value,
        "total_values": dict(totals_all),
        "overall_budget": {"min": overall_min_cfg, "max": overall_max_cfg, "target": overall_target, "notes": overall_budget_notes},
        "overall_bounds": overall_bounds,
        "overall_delta": overall_delta,
        "page_budget": {"min": pages_min, "max": pages_max, "target": pages_target, "hard_max": pages_hard_max, "notes": pages_notes},
        "page_delta": page_delta,
        "unmatched_budget_files": unmatched_budget_files,
        "files": file_results,
        "sections": section_results,
    }

    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser()
    else:
        base = input_path if input_path.is_dir() else input_path.parent
        out_dir = base / "_artifacts" / "nsfc-length-aligner"
    try:
        _ensure_dir(out_dir)
    except OSError as e:
        print(f"error: cannot create out dir: {out_dir} ({e})", file=sys.stderr)
        print("hint: your --input may be read-only; use --out-dir to write reports elsewhere", file=sys.stderr)
        return 2
    json_path = out_dir / "length_report.json"
    md_path = out_dir / "length_report.md"

    if args.fail_if_exists and (json_path.exists() or md_path.exists()):
        print(f"error: report already exists (use a different --out-dir): {out_dir}", file=sys.stderr)
        return 2

    try:
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"error: cannot write json report: {json_path} ({e})", file=sys.stderr)
        print("hint: use --out-dir to write reports to a writable directory", file=sys.stderr)
        return 2

    table_rows: list[list[str]] = [["文件", unit, "预算(min~max)", "偏差"]]
    for r in file_results:
        b = r.get("budget")
        bounds = "-"
        delta = "-"
        if b and b.get("min") is not None and b.get("max") is not None:
            bounds = f"{b['min']}~{b['max']}"
            if r["value"] < b["min"]:
                delta = f"-{b['min'] - r['value']}"
            elif r["value"] > b["max"]:
                delta = f"+{r['value'] - b['max']}"
            else:
                delta = "OK"
        table_rows.append([str(r["path"]), str(r["value"]), bounds, delta])

    file_table = _render_table(table_rows)

    section_table = ""
    if section_results:
        s_rows: list[list[str]] = [["文件", "章节", unit]]
        for s in section_results:
            s_rows.append([s["file"], s["section"], str(s["value"])])
        section_table = _render_table(s_rows)

    template_text = _load_template(Path(__file__).resolve().parents[1])
    overall_bounds_text = "-"
    if overall_bounds and overall_bounds.get("min") is not None and overall_bounds.get("max") is not None:
        overall_bounds_text = f"{overall_bounds['min']}~{overall_bounds['max']}"
    unmatched_text = "（无）"
    if unmatched_budget_files:
        unmatched_text = ", ".join(unmatched_budget_files[:20])
        if len(unmatched_budget_files) > 20:
            unmatched_text += f" ... (+{len(unmatched_budget_files) - 20})"
    md = _render_template(
        template_text,
        {
            "generated_at": report["generated_at"],
            "unit": unit,
            "file_count": str(len(file_results)),
            "discovery_mode": str((report.get("discovery") or {}).get("mode") or "-"),
            "main_tex": str((report.get("discovery") or {}).get("main_tex") or "-"),
            "total_value": str(total_value),
            "total_cjk_chars": str(totals_all["cjk_chars"]),
            "total_chars": str(totals_all["chars"]),
            "overall_budget": str(overall_target) if overall_target is not None else "-",
            "overall_bounds": overall_bounds_text,
            "overall_delta": str(overall_delta) if overall_delta is not None else "-",
            "pdf_path": str(pdf_path) if pdf_path else "-",
            "page_count": str(page_count) if page_count is not None else "-",
            "page_budget_max": str(pages_max) if pages_max is not None else "-",
            "page_budget_hard_max": str(pages_hard_max) if pages_hard_max is not None else "-",
            "page_delta": str(page_delta) if page_delta is not None else "-",
            "page_notes": str(pages_notes) if pages_notes else "-",
            "unmatched_files": unmatched_text,
            "file_table": file_table or "（无）",
            "section_table": section_table or "（未启用或无可解析章节）",
        },
    )
    try:
        md_path.write_text(md, encoding="utf-8")
    except OSError as e:
        print(f"error: cannot write md report: {md_path} ({e})", file=sys.stderr)
        print("hint: use --out-dir to write reports to a writable directory", file=sys.stderr)
        return 2

    print(f"OK: total {unit}={total_value} files={len(file_results)}")
    if page_count is not None:
        print(f"- pdf pages: {page_count} (delta={page_delta or '-'})")
    elif pdf_path and pdf_error:
        print(f"- pdf pages: - ({pdf_error})")
    print(f"- json: {json_path}")
    print(f"- md:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
