#!/usr/bin/env python3
"""
Rank NSFC application codes by heuristic similarity between:
- proposal text (from .tex/.md/.txt files)
- overrides TOML recommend descriptions (2026)

Design goals:
- Dependency-free (no third-party packages; Python 3.9+).
- Read-only on inputs; writes only if --out is provided.
- Provide a "candidate shortlist" for the LLM to finalize 5 code pairs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDES = SKILL_ROOT / "references" / "nsfc_2026_recommend_overrides.toml"


_HEADER_RE = re.compile(r"^\[([A-Za-z0-9_.-]+)\]\s*$")
_RECOMMEND_RE = re.compile(r'^\s*recommend\s*=\s*"(.*)"\s*$')


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_overrides(path: Path) -> Dict[str, str]:
    """
    Minimal TOML reader for files shaped like:
      [A.A01.A0101]
      recommend = "..."
    """
    if not path.exists():
        raise FileNotFoundError(str(path))

    codes: Dict[str, str] = {}
    current: Optional[str] = None
    for raw in _read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        m = _HEADER_RE.match(line)
        if m:
            current = m.group(1).strip()
            continue

        if current:
            m2 = _RECOMMEND_RE.match(line)
            if m2:
                # Basic unescape: \" -> "
                val = m2.group(1).replace('\\"', '"')
                codes[current] = val
                continue
    return codes


def is_binary_file(path: Path) -> bool:
    # A cheap heuristic: if NUL in first chunk, treat as binary.
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
        return b"\x00" in chunk
    except Exception:
        return True


def iter_input_files(inputs: Sequence[Path]) -> Iterable[Path]:
    exts = {".tex", ".md", ".txt"}
    skip_md_basenames = {"README.md", "CHANGELOG.md", "SKILL.md"}
    for inp in inputs:
        if inp.is_file():
            if inp.suffix.lower() in exts and not is_binary_file(inp):
                yield inp
            continue
        if inp.is_dir():
            for p in inp.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in exts:
                    continue
                # Avoid feeding tool-generated reports or meta-docs back into ranking.
                if p.suffix.lower() == ".md":
                    if p.name in skip_md_basenames:
                        continue
                    if p.name.startswith("NSFC-"):
                        continue
                if any(part in {".git", ".latex-cache", "build", "dist", "out"} for part in p.parts):
                    continue
                if is_binary_file(p):
                    continue
                yield p


_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
_MATH_INLINE_RE = re.compile(r"\$[^$]*\$")
_MATH_DISPLAY_RE = re.compile(r"\$\$.*?\$\$", flags=re.S)
_TEX_ENV_RE = re.compile(r"\\begin\{[^}]+\}|\\end\{[^}]+\}")
_CITE_RE = re.compile(r"\\(?:cite|citet|citep|ref|eqref|label)\{[^}]*\}")
_CMD_RE = re.compile(r"\\[A-Za-z@]+(\*?)")
_BRACE_RE = re.compile(r"[\{\}\[\]]")


def latex_to_text(s: str) -> str:
    # Strip TeX comments first (line-wise).
    lines = []
    for line in s.splitlines():
        line = _COMMENT_RE.sub("", line)
        lines.append(line)
    s2 = "\n".join(lines)

    # Remove math.
    s2 = _MATH_DISPLAY_RE.sub(" ", s2)
    s2 = _MATH_INLINE_RE.sub(" ", s2)

    # Remove environments and common citation/ref tokens.
    s2 = _TEX_ENV_RE.sub(" ", s2)
    s2 = _CITE_RE.sub(" ", s2)

    # Keep argument text; remove command names and braces.
    s2 = s2.replace("\\linebreak{}", " ")
    s2 = _CMD_RE.sub(" ", s2)
    s2 = _BRACE_RE.sub(" ", s2)

    # Collapse whitespace.
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


_RECOMMEND_BOILERPLATE = [
    "资助",
    "领域基础与应用基础研究",
    "基础与应用基础研究",
    "重点围绕",
    "重点支持",
    "开展理论、方法与应用研究",
    "开展理论、方法与应用研究",
    "开展理论、方法与应用研究，",
    "鼓励交叉创新",
    "聚焦关键科学问题与技术突破",
    "强调原创性与可转化性",
]


def clean_recommend_text(s: str) -> str:
    # Remove boilerplate phrases to make similarity more sensitive to distinctive terms.
    out = s
    for ph in _RECOMMEND_BOILERPLATE:
        out = out.replace(ph, "")
    return out


def normalize_for_ngrams(s: str) -> str:
    # Keep CJK + ascii letters/digits; drop punctuation/spaces.
    s = s.lower()
    s = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", s)
    return s


def ngrams(s: str, n: int) -> set:
    if n <= 0:
        return set()
    if len(s) < n:
        return set()
    return {s[i : i + n] for i in range(0, len(s) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass(frozen=True)
class RankedCode:
    code: str
    score: float
    recommend: str


def rank_codes(
    proposal_text: str,
    overrides: Dict[str, str],
    *,
    w2: float = 0.55,
    w3: float = 0.45,
) -> List[RankedCode]:
    norm_p = normalize_for_ngrams(proposal_text)
    p2 = ngrams(norm_p, 2)
    p3 = ngrams(norm_p, 3)

    ranked: List[RankedCode] = []
    for code, desc in overrides.items():
        norm_d = normalize_for_ngrams(clean_recommend_text(desc))
        d2 = ngrams(norm_d, 2)
        d3 = ngrams(norm_d, 3)
        score = w2 * jaccard(p2, d2) + w3 * jaccard(p3, d3)
        ranked.append(RankedCode(code=code, score=score, recommend=desc))

    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked


def suggest_pairs(ranked: Sequence[RankedCode], k: int = 5) -> List[Tuple[str, str]]:
    """
    Suggest (code1, code2) pairs from ranked list.
    Heuristic:
    - pick diverse code1 by major prefix (first 2 segments, e.g., A.A06)
    - for each code1, pick code2 as the best remaining with same first segment (e.g., A)
      and preferably same major prefix; otherwise next best.
    """
    if k <= 0:
        return []

    def major_prefix(code: str) -> str:
        parts = code.split(".")
        return ".".join(parts[:2]) if len(parts) >= 2 else code

    def first_prefix(code: str) -> str:
        return code.split(".")[0] if code else code

    used_codes = set()
    used_major = set()
    picks: List[str] = []
    for item in ranked:
        if item.code in used_codes:
            continue
        mp = major_prefix(item.code)
        if mp in used_major:
            continue
        picks.append(item.code)
        used_codes.add(item.code)
        used_major.add(mp)
        if len(picks) >= k:
            break

    pairs: List[Tuple[str, str]] = []
    for c1 in picks:
        mp1 = major_prefix(c1)
        fp1 = first_prefix(c1)
        c2: Optional[str] = None
        # Prefer same major prefix.
        for item in ranked:
            if item.code == c1 or item.code in used_codes:
                continue
            if major_prefix(item.code) == mp1:
                c2 = item.code
                break
        # Fallback: same first prefix (discipline letter).
        if c2 is None:
            for item in ranked:
                if item.code == c1 or item.code in used_codes:
                    continue
                if first_prefix(item.code) == fp1:
                    c2 = item.code
                    break
        # Final fallback: next best.
        if c2 is None:
            for item in ranked:
                if item.code == c1 or item.code in used_codes:
                    continue
                c2 = item.code
                break
        if c2 is None:
            continue
        used_codes.add(c2)
        pairs.append((c1, c2))
    return pairs


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True, help="Input file/dir path; repeatable")
    ap.add_argument("--overrides", default=str(DEFAULT_OVERRIDES), help="Path to overrides TOML")
    ap.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="Restrict to code first-segment prefix (e.g., A/F/H); repeatable",
    )
    ap.add_argument("--top-k", type=int, default=50, help="How many candidates to print (default: 50)")
    ap.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    ap.add_argument("--suggest-pairs", action="store_true", help="Also print 5 suggested (code1, code2) pairs")
    ap.add_argument("--out", default="", help="Write output to a file (optional)")
    args = ap.parse_args(list(argv) if argv is not None else None)

    inputs = [Path(x).expanduser().resolve() for x in args.input]
    for p in inputs:
        if not p.exists():
            print(f"FAIL: input path not found: {p}", file=sys.stderr)
            return 2
    overrides_path = Path(args.overrides).expanduser().resolve()

    overrides = load_overrides(overrides_path)
    if not overrides:
        print(f"FAIL: overrides file parsed but empty: {overrides_path}", file=sys.stderr)
        return 2

    prefixes = [x.strip() for x in args.prefix if x and x.strip()]
    if prefixes:
        overrides = {k: v for k, v in overrides.items() if k.split(".")[0] in set(prefixes)}
        if not overrides:
            print(f"FAIL: overrides filtered by --prefix but became empty: {prefixes}", file=sys.stderr)
            return 2

    files = sorted(set(iter_input_files(inputs)))
    if not files:
        print("FAIL: no readable input files found (.tex/.md/.txt).", file=sys.stderr)
        return 2

    chunks: List[str] = []
    for p in files:
        raw = _read_text(p)
        if p.suffix.lower() == ".tex":
            chunks.append(latex_to_text(raw))
        else:
            chunks.append(raw)
    proposal_text = "\n".join(chunks)

    ranked = rank_codes(proposal_text, overrides)
    top = ranked[: max(0, int(args.top_k))]

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overrides": str(overrides_path),
        "filters": {"prefixes": prefixes},
        "inputs": [str(x) for x in inputs],
        "files_used": [str(p) for p in files],
        "top_k": int(args.top_k),
        "candidates": [
            {"rank": i + 1, "code": r.code, "score": round(r.score, 6), "recommend": r.recommend}
            for i, r in enumerate(top)
        ],
    }
    if args.suggest_pairs:
        payload["suggested_pairs"] = [{"code1": a, "code2": b} for a, b in suggest_pairs(top, k=5)]

    if args.format == "json":
        out_text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        lines: List[str] = []
        lines.append(f"generated_at: {payload['generated_at']}")
        lines.append(f"overrides: {payload['overrides']}")
        lines.append(f"files_used: {len(files)}")
        lines.append("")
        lines.append("| rank | code | score | recommend |")
        lines.append("|---:|---|---:|---|")
        for c in payload["candidates"]:
            rec = c["recommend"]
            if len(rec) > 60:
                rec = rec[:60] + "..."
            lines.append(f"| {c['rank']} | {c['code']} | {c['score']:.6f} | {rec} |")
        if args.suggest_pairs:
            lines.append("")
            lines.append("Suggested pairs:")
            for p in payload.get("suggested_pairs", []):
                lines.append(f"- {p['code1']} + {p['code2']}")
        out_text = "\n".join(lines)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_text, encoding="utf-8")
    else:
        print(out_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
