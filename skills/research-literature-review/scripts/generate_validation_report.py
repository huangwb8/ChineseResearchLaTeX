#!/usr/bin/env python3
"""
generate_validation_report.py - 生成系统综述验证报告（Markdown 格式）

功能：
- 汇总 validate_counts.py 和 validate_review_tex.py 的验证结果
- 生成易于阅读的 Markdown 报告
- 报告包含：验证摘要、字数验证、引用验证、章节验证、引用一致性验证、总体评估

使用方式：
    python scripts/generate_validation_report.py \
        --counts-json validate_counts_result.json \
        --review-tex-result "✓ LaTeX review validation passed (cites=80, bib_keys=140)" \
        --output validation_report.md \
        --review-level premium
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from path_scope import get_effective_scope_root, resolve_and_check


def load_json_result(path: Path) -> Dict[str, Any]:
    """加载验证脚本的 JSON 输出"""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_review_tex_result(output: str) -> Dict[str, Any]:
    """解析 validate_review_tex.py 的输出"""
    result = {
        "passed": "✓" in output or "passed" in output.lower(),
        "cites": 0,
        "bib_keys": 0,
        "sections": None,
    }
    # 提取 cites= 和 bib_keys= 的数值
    import re
    import json

    cites_match = re.search(r"cites=(\d+)", output)
    bib_match = re.search(r"bib_keys=(\d+)", output)
    if cites_match:
        result["cites"] = int(cites_match.group(1))
    if bib_match:
        result["bib_keys"] = int(bib_match.group(1))

    # 提取 SECTIONS: 后的 JSON 数据
    sections_match = re.search(r"SECTIONS:(\{.*?\})$", output, re.MULTILINE | re.DOTALL)
    if sections_match:
        try:
            result["sections"] = json.loads(sections_match.group(1))
        except json.JSONDecodeError:
            # JSON 解析失败时保持 None
            pass

    return result


def compute_abstract_stats(selected_jsonl: Path, min_abstract_chars: int) -> Dict[str, Any]:
    """统计 selected_papers 的摘要覆盖率（用于选文后摘要补齐的可观测性）。"""
    total = 0
    ok = 0
    examples: list[str] = []
    if not selected_jsonl.exists():
        return {"enabled": False, "reason": f"missing file: {selected_jsonl}"}

    with selected_jsonl.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            total += 1
            abstract = obj.get("abstract") or ""
            if isinstance(abstract, str) and len(abstract.strip()) >= int(min_abstract_chars):
                ok += 1
            elif len(examples) < 10:
                title = str(obj.get("title") or obj.get("id") or "").strip()
                if title:
                    examples.append(title[:120])

    missing = max(0, total - ok)
    coverage = (ok / total) if total else 0.0
    return {
        "enabled": True,
        "min_abstract_chars": int(min_abstract_chars),
        "total_selected": int(total),
        "abstract_ok": int(ok),
        "abstract_missing": int(missing),
        "abstract_coverage": round(coverage, 4),
        "missing_examples": examples,
    }


def format_status(passed: bool, label: str = "") -> str:
    """格式化状态标签"""
    icon = "✅ PASS" if passed else "❌ FAIL"
    return f"{icon} {label}".strip()


def generate_markdown_report(
    counts_result: Dict[str, Any],
    review_tex_result: Dict[str, Any],
    abstract_stats: Dict[str, Any] | None,
    review_level: str,
    timestamp: str,
) -> str:
    """生成 Markdown 格式的验证报告"""

    lines = [
        "# 系统综述验证报告",
        "",
        f"**生成时间**: {timestamp}",
        f"**档位**: {review_level}",
        "",
        "---",
        "",
        "## 验证摘要",
        "",
    ]

    # 判断总体状态
    counts_passed = counts_result.get("passed", False)
    review_tex_passed = review_tex_result.get("passed", False)
    overall_passed = counts_passed and review_tex_passed

    lines.extend([
        f"**验证状态**: {format_status(overall_passed)}",
        "",
        "---",
        "",
    ])

    # 字数验证
    lines.extend([
        "## 字数验证",
        "",
    ])

    if counts_result:
        words_total = counts_result.get("words_total", 0)
        words_cn = counts_result.get("words_chinese", 0)
        words_en = counts_result.get("words_english", 0)
        words_digits = counts_result.get("words_digits", 0)
        words_total_incl_digits = counts_result.get("words_total_including_digits", None)
        thresholds = counts_result.get("thresholds", {})
        min_words = thresholds.get("min_words", 0)
        max_words = thresholds.get("max_words", 0)

        lines.extend([
            f"- **正文字数**: {words_total:,}",
            f"  - 中文: {words_cn:,} 字",
            f"  - 英文: {words_en:,} 词",
            f"  - 数字token: {words_digits:,}",
        ])
        if isinstance(words_total_incl_digits, int):
            lines.append(f"  - 参考：含数字token总计 {words_total_incl_digits:,}")
        lines.extend([
            f"- **目标范围**: {min_words:,} - {max_words:,}",
            f"- **状态**: {format_status(counts_passed)}",
            "",
        ])
    else:
        lines.extend([
            "- 无字数验证数据",
            "",
        ])

    # 引用验证
    lines.extend([
        "## 引用数量验证",
        "",
    ])

    if counts_result:
        cite_keys_count = counts_result.get("cite_keys_count", 0)
        thresholds = counts_result.get("thresholds", {})
        min_cites = thresholds.get("min_unique_citations", 0)
        max_cites = thresholds.get("max_unique_citations", 0)

        lines.extend([
            f"- **正文唯一引用数**: {cite_keys_count}",
            f"- **目标范围**: {min_cites} - {max_cites}",
            f"- **状态**: {format_status(min_cites <= cite_keys_count <= max_cites)}",
            "",
        ])
    else:
        lines.extend([
            "- 无引用数量验证数据",
            "",
        ])

    # 引用一致性验证
    lines.extend([
        "## 引用一致性验证",
        "",
    ])

    if review_tex_result:
        cites = review_tex_result.get("cites", 0)
        bib_keys = review_tex_result.get("bib_keys", 0)
        lines.extend([
            f"- **正文引用 key 数量**: {cites}",
            f"- **BibTeX 条目数量**: {bib_keys}",
            f"- **状态**: {format_status(review_tex_passed, '所有正文引用都在 BibTeX 中')}",
            "",
        ])
    else:
        lines.extend([
            "- 无引用一致性验证数据",
            "",
        ])

    # 摘要覆盖率（selected_papers）
    if abstract_stats and abstract_stats.get("enabled"):
        total_selected = int(abstract_stats.get("total_selected", 0) or 0)
        abs_ok = int(abstract_stats.get("abstract_ok", 0) or 0)
        abs_missing = int(abstract_stats.get("abstract_missing", 0) or 0)
        min_chars = int(abstract_stats.get("min_abstract_chars", 0) or 0)
        coverage = float(abstract_stats.get("abstract_coverage", 0.0) or 0.0)
        lines.extend([
            "## 摘要覆盖率（selected_papers）",
            "",
            f"- **有效摘要判定阈值**: ≥ {min_chars} chars",
            f"- **选中文献数**: {total_selected}",
            f"- **摘要充足**: {abs_ok}（覆盖率 {coverage:.1%}）",
            f"- **摘要缺失/过短**: {abs_missing}",
            "",
        ])
        examples = abstract_stats.get("missing_examples") or []
        if abs_missing > 0 and examples:
            lines.append("- **缺摘要示例（最多10条）**:")
            for t in examples:
                lines.append(f"  - {t}")
            lines.append("")

    # 必需章节验证（从 review_tex_result 获取详细信息）
    lines.extend([
        "## 必需章节验证",
        "",
    ])

    sections = review_tex_result.get("sections")
    if sections:
        # 有详细的章节信息，动态生成报告
        lines.extend([
            f"- **摘要**: {'✅ 存在' if sections.get('abstract') else '❌ 缺失'}",
            f"- **引言**: {'✅ 存在' if sections.get('intro') else '❌ 缺失'}",
        ])

        body_count = sections.get("body_count", 0)
        if body_count > 0:
            lines.append(f"- **子主题段**: ✅ {body_count}个")
            # 列出子主题标题（如果有）
            body_titles = sections.get("body_titles", [])
            if body_titles:
                for title in body_titles:
                    lines.append(f"  - {title}")
            if len(body_titles) < body_count:
                lines.append(f"  - ... 还有 {body_count - len(body_titles)} 个")
        else:
            lines.append("- **子主题段**: ❌ 缺失")

        lines.extend([
            f"- **讨论**: {'✅ 存在' if sections.get('discussion') else '❌ 缺失'}",
            f"- **展望/结论**: {'✅ 存在' if sections.get('outlook') else '❌ 缺失'}",
            "",
        ])
    elif review_tex_passed:
        # 兼容旧版本：没有详细章节信息但验证通过
        lines.extend([
            "- **摘要**: ✅ 存在",
            "- **引言**: ✅ 存在",
            "- **子主题段**: ✅ 至少1个",
            "- **讨论**: ✅ 存在",
            "- **展望/结论**: ✅ 存在",
            "",
        ])
    else:
        # 验证未通过或未执行
        lines.extend([
            "- 章节验证未通过或未执行",
            "",
        ])

    # 总体评估
    lines.extend([
        "---",
        "",
        "## 总体评估",
        "",
    ])

    if overall_passed:
        lines.extend([
            "✅ **所有验证项通过**，系统综述已满足质量标准，可以继续导出 PDF/Word。",
            "",
        ])
    else:
        lines.extend([
            "❌ **部分验证项未通过**，请检查上述详细结果并根据需要调整内容。",
            "",
        ])

    # 验证标准说明
    lines.extend([
        "---",
        "",
        "## 验证标准说明",
        "",
        f"**档位 ({review_level})** 验证阈值：",
        "",
        "| 项目 | 最小值 | 最大值 |",
        "|------|--------|--------|",
    ])

    if counts_result and counts_result.get("thresholds"):
        thresholds = counts_result["thresholds"]
        lines.extend([
            f"| 正文字数 | {thresholds.get('min_words', 0):,} | {thresholds.get('max_words', 0):,} |",
            f"| 引用数量 | {thresholds.get('min_unique_citations', 0)} | {thresholds.get('max_unique_citations', 0)} |",
        ])
    else:
        lines.extend([
            "| 正文字数 | - | - |",
            "| 引用数量 | - | - |",
        ])

    lines.extend([
        "",
        "**必需章节**: 摘要、引言、至少1个子主题段、讨论、展望/结论",
        "",
        "---",
        "",
        f"*报告由 `generate_validation_report.py` 自动生成*",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate validation report for systematic literature review"
    )
    parser.add_argument(
        "--counts-json",
        type=Path,
        help="Path to validate_counts.py JSON output (optional if using manual values)"
    )
    parser.add_argument(
        "--review-tex-output",
        type=str,
        default="",
        help="Output text from validate_review_tex.py (optional)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output validation report (Markdown format)"
    )
    parser.add_argument(
        "--selected-jsonl",
        type=Path,
        default=None,
        help="Path to selected_papers.jsonl (optional; used to compute abstract coverage)",
    )
    parser.add_argument(
        "--min-abstract-chars",
        type=int,
        default=80,
        help="Treat abstract shorter than N chars as missing when computing abstract coverage (default: 80)",
    )
    parser.add_argument(
        "--scope-root",
        type=Path,
        default=None,
        help="工作目录隔离根目录（可选；默认从环境变量 SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT 读取）",
    )
    parser.add_argument(
        "--review-level",
        type=str,
        default="premium",
        choices=["premium", "standard", "basic"],
        help="Review level for validation thresholds"
    )
    parser.add_argument(
        "--timestamp",
        type=str,
        default="",
        help="Timestamp string (default: current time)"
    )

    # 手动指定值（用于测试或当验证脚本未运行时）
    parser.add_argument(
        "--words-total",
        type=int,
        default=0,
        help="Manual override for total word count"
    )
    parser.add_argument(
        "--cite-count",
        type=int,
        default=0,
        help="Manual override for citation count"
    )
    parser.add_argument(
        "--bib-count",
        type=int,
        default=0,
        help="Manual override for BibTeX entry count"
    )
    parser.add_argument(
        "--force-pass",
        action="store_true",
        help="Force all validations to pass (for testing)"
    )

    args = parser.parse_args()

    scope_root = get_effective_scope_root(args.scope_root)
    if scope_root is not None:
        if args.counts_json is not None:
            args.counts_json = resolve_and_check(args.counts_json, scope_root, must_exist=True)
        if args.selected_jsonl is not None:
            args.selected_jsonl = resolve_and_check(args.selected_jsonl, scope_root, must_exist=True)
        args.output = resolve_and_check(args.output, scope_root, must_exist=False)

    # 加载验证结果
    counts_result = {}
    if args.counts_json and args.counts_json.exists():
        counts_result = load_json_result(args.counts_json)

    # 如果有手动覆盖值，使用它们
    if args.words_total > 0:
        counts_result["words_total"] = args.words_total
        if "thresholds" not in counts_result:
            counts_result["thresholds"] = {}
        if args.force_pass:
            counts_result["passed"] = True

    if args.cite_count > 0:
        counts_result["cite_keys_count"] = args.cite_count

    # 解析 review_tex 结果
    review_tex_result = parse_review_tex_result(args.review_tex_output)

    if args.bib_count > 0:
        review_tex_result["bib_keys"] = args.bib_count
    if args.force_pass:
        review_tex_result["passed"] = True

    abstract_stats = None
    if args.selected_jsonl is not None:
        abstract_stats = compute_abstract_stats(args.selected_jsonl, args.min_abstract_chars)

    # 生成时间戳
    timestamp = args.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 生成报告
    report = generate_markdown_report(
        counts_result=counts_result,
        review_tex_result=review_tex_result,
        abstract_stats=abstract_stats,
        review_level=args.review_level,
        timestamp=timestamp,
    )

    # 写入文件
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")

    print(f"✓ 验证报告已生成: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
