#!/usr/bin/env python3
"""
validate_review_tex.py - 轻量校验：必需章节 + cite/bib 对齐 + 引用数量上下限
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _extract_cite_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    cite_pattern = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}", re.MULTILINE)
    for m in cite_pattern.finditer(tex):
        for part in m.group(1).split(","):
            k = part.strip()
            if k:
                keys.add(k)
    return keys


def _extract_bib_keys(bib: str) -> set[str]:
    keys: set[str] = set()
    # Match BibTeX entries like "@article{key," and capture the key
    for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib):
        keys.add(m.group(1).strip())
    return keys


def _has_keyword(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(k.lower() in lowered for k in keywords)


def _check_citation_distribution(tex: str, verbose: bool = False) -> dict:
    """
    检查引用分布是否符合目标标准
    目标：70% 单篇引用，25% 引用 2-4 篇，<5% 引用 >4 篇

    Returns:
        包含通过状态和详细信息的字典
    """
    import json

    from validate_citation_distribution import extract_citations

    citations = [{"command": command, "count": count, "line": line}
                 for command, count, line, _ in extract_citations(tex)]

    if not citations:
        return {
            "passed": False,
            "error": "No citations found",
            "details": {}
        }

    # 统计分布
    total = len(citations)
    single = sum(1 for c in citations if c["count"] == 1)
    small_group = sum(1 for c in citations if 2 <= c["count"] <= 4)
    large_group = sum(1 for c in citations if c["count"] > 4)

    details = {
        "total_citations": total,
        "single_cite_count": single,
        "single_cite_pct": round(single / total * 100, 1),
        "small_group_count": small_group,
        "small_group_pct": round(small_group / total * 100, 1),
        "large_group_count": large_group,
        "large_group_pct": round(large_group / total * 100, 1),
        "max_keys_in_one_cite": max(c["count"] for c in citations),
    }

    # 检查是否符合目标（允许一定容差）
    single_ok = 65 <= details["single_cite_pct"] <= 75
    small_group_ok = 20 <= details["small_group_pct"] <= 30
    large_group_ok = details["large_group_pct"] <= 10

    passed = single_ok and small_group_ok and large_group_ok

    # 找出违规引用（>5篇）
    violations = [c for c in citations if c["count"] > 5]

    if verbose:
        print("\n" + "=" * 60)
        print("📊 引用分布验证", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"  单篇引用 (1篇):     {single:4d} 次 ({details['single_cite_pct']:5.1f}%)  [目标: 70% ±5%] {'✓' if single_ok else '✗'}", file=sys.stderr)
        print(f"  小组引用 (2-4篇):   {small_group:4d} 次 ({details['small_group_pct']:5.1f}%)  [目标: 25% ±5%] {'✓' if small_group_ok else '✗'}", file=sys.stderr)
        print(f"  大组引用 (>4篇):    {large_group:4d} 次 ({details['large_group_pct']:5.1f}%)  [目标: <5% ±5%] {'✓' if large_group_ok else '✗'}", file=sys.stderr)
        print(f"\n  单次最大引用数: {details['max_keys_in_one_cite']} 篇", file=sys.stderr)

        if violations:
            print(f"\n⚠️  违规引用 (>5篇) 共 {len(violations)} 处:", file=sys.stderr)
            for v in violations[:10]:
                print(f"  行 {v['line']:4d}: {v['command'][:50]}{'...' if len(v['command'])>50 else ''} ({v['count']}篇)", file=sys.stderr)
            if len(violations) > 10:
                print(f"  ... 还有 {len(violations)-10} 处", file=sys.stderr)

        print(f"\n{'🎉 引用分布: ✓ 通过' if passed else '❌ 引用分布: ✗ 失败'}", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

    return {
        "passed": passed,
        "details": details,
        "violations_count": len(violations),
        "worst_violation": max(v["count"] for v in violations) if violations else 0
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate review.tex + references.bib (required sections + citations).")
    parser.add_argument("--tex", required=True, type=Path, help="Path to review.tex")
    parser.add_argument("--bib", required=True, type=Path, help="Path to references.bib")
    parser.add_argument("--min-refs", type=int, default=0, help="Minimum unique citation keys")
    parser.add_argument("--max-refs", type=int, default=0, help="Maximum unique citation keys (0 = no limit)")
    parser.add_argument("--check-citation-dist", action="store_true",
                        # argparse 会对 help 文本做 %-formatting；这里需要对字面量 % 进行转义
                        help="检查引用分布是否符合目标（70%% 单篇，25%% 2-4篇，<5%% >4篇）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细的引用分布报告")
    args = parser.parse_args()

    errors: list[str] = []
    if not args.tex.exists():
        errors.append(f"missing tex: {args.tex}")
    if not args.bib.exists():
        errors.append(f"missing bib: {args.bib}")
    if errors:
        for e in errors:
            print(f"✗ {e}", file=sys.stderr)
        return 1

    tex = re.sub(r"(?<!\\)%[^\n]*", "", _read(args.tex))
    bib = _read(args.bib)

    # 必需章节关键字（轻量检查）
    section_titles_list = re.findall(r"\\section\*?\s*\{([^}]+)\}", tex, flags=re.IGNORECASE)
    section_titles = "\n".join(section_titles_list)
    musts = {
        "abstract": ["\\begin{abstract}", "摘要", "Abstract", "Summary"],
        "intro": ["引言", "Introduction"],
        "body": [],  # 至少一个额外 section
        "discussion": ["讨论", "Discussion"],
        "outlook": ["展望", "Outlook", "Perspectives", "Future work"],
        "conclusion": ["Conclusion", "结论"],
    }
    abstract_present = bool(re.search(r"\\begin\s*\{abstract\}", tex)) or _has_keyword(section_titles, musts["abstract"][1:])
    if not abstract_present:
        errors.append("缺少摘要（abstract 环境或摘要/Abstract 标题）")
    if not _has_keyword(section_titles, musts["intro"]):
        errors.append("缺少引言（引言/Introduction）")

    body_titles = [
        t
        for t in section_titles_list
        if not _has_keyword(t, musts["intro"])
        and not _has_keyword(t, musts["discussion"])
        and not _has_keyword(t, musts["outlook"])
        and not _has_keyword(t, musts["conclusion"])
        and not _has_keyword(t, musts["abstract"])
        and t.lower() not in {"references", "参考文献"}
    ]
    if len(body_titles) < 1:
        errors.append("缺少至少 1 个子主题段落")

    if not _has_keyword(section_titles, musts["discussion"]):
        errors.append("缺少讨论（讨论/Discussion）")
    if not _has_keyword(section_titles, musts["outlook"]):
        errors.append("缺少展望（展望/Outlook/Perspectives）")
    if not _has_keyword(section_titles, musts["conclusion"]):
        errors.append("缺少结论（结论/Conclusion）")

    # cite 与 bib 对齐 + 数量
    cite_keys = _extract_cite_keys(tex)
    bib_keys = _extract_bib_keys(bib)
    if not cite_keys:
        errors.append("正文未包含任何 \\cite 引用")
    else:
        if args.min_refs and len(cite_keys) < args.min_refs:
            errors.append(f"唯一引用数不足: {len(cite_keys)} < {args.min_refs}")
        if args.max_refs and len(cite_keys) > args.max_refs:
            errors.append(f"唯一引用数超出: {len(cite_keys)} > {args.max_refs}")
    missing = sorted([k for k in cite_keys if k not in bib_keys])
    if missing:
        errors.append("Bib 缺少对应 key: " + ", ".join(missing[:20]) + (" ..." if len(missing) > 20 else ""))

    if errors:
        print("LaTeX review validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    # 引用分布检查（可选）
    if args.check_citation_dist:
        dist_result = _check_citation_distribution(tex, verbose=args.verbose)
        if not dist_result["passed"]:
            if dist_result.get("error"):
                print(f"⚠️  引用分布检查错误: {dist_result['error']}", file=sys.stderr)
            else:
                errors.append(f"引用分布不符合目标")
                if args.verbose:
                    print(f"  - 引用分布不符合目标（详见上方报告）", file=sys.stderr)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    # 收集章节验证详情（用于 generate_validation_report.py 解析）
    import json
    sections_info = {
        "abstract": abstract_present,
        "intro": _has_keyword(section_titles, musts["intro"]),
        "body_count": len(body_titles),
        "body_titles": body_titles[:10],  # 最多记录前10个，避免输出过长
        "discussion": _has_keyword(section_titles, musts["discussion"]),
        "outlook": _has_keyword(section_titles, musts["outlook"]),
        "conclusion": _has_keyword(section_titles, musts["conclusion"]),
    }
    sections_json = json.dumps(sections_info, ensure_ascii=False)

    print(f"✓ LaTeX review validation passed (cites={len(cite_keys)}, bib_keys={len(bib_keys)}) SECTIONS:{sections_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
