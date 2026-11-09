#!/usr/bin/env python3
"""
validate_citation_distribution.py - 验证 LaTeX 文件中的引用分布

目标：检查引用分布是否符合人类学术写作习惯
- 单篇引用（1篇）：约 70%
- 小组引用（2-4篇）：约 25%
- 大组引用（>4篇）：<5%
- 引用多样性：段落间引用均匀、文献利用率高

使用示例：
    python scripts/validate_citation_distribution.py review.tex
    python scripts/validate_citation_distribution.py review.tex --output report.json
    python scripts/validate_citation_distribution.py review.tex --check-diversity
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import stdev
from typing import Dict, List, Tuple, Optional


_CITE_PATTERN = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}")


def _strip_comments(text: str) -> str:
    """保留换行位置，忽略未转义百分号后的内容。"""
    lines = []
    for line in text.split('\n'):
        for index, char in enumerate(line):
            if char == '%':
                prefix = line[:index]
                slashes = len(prefix) - len(prefix.rstrip('\\'))
                if slashes % 2 == 0:
                    line = prefix
                    break
        lines.append(line)
    return '\n'.join(lines)


def extract_citations(tex_content: str) -> List[Tuple[str, int, int, List[str]]]:
    """
    提取所有 \\cite{} 命令及其位置

    Args:
        tex_content: LaTeX 文件内容

    Returns:
        List of (cite_command, number_of_keys, line_number, [keys])
    """
    content = _strip_comments(tex_content)
    citations = []
    # 整段匹配，支持命令与花括号分行，同时保留源文件行号。
    line_num = 1
    previous = 0
    for match in _CITE_PATTERN.finditer(content):
        line_num += content.count('\n', previous, match.start())
        previous = match.start()
        keys = [k.strip() for k in match.group(1).split(',') if k.strip()]
        citations.append((match.group(0), len(keys), line_num, keys))

    return citations


def analyze_distribution(citations: List[Tuple[str, int, int, List[str]]]) -> Dict:
    """
    分析引用分布并与目标对比

    Args:
        citations: 引用列表

    Returns:
        包含分布统计和通过状态的字典
    """
    total = len(citations)
    if total == 0:
        return {
            "error": "No citations found",
            "total_citations": 0
        }

    # 统计各类型引用
    single = sum(1 for _, n, _, _ in citations if n == 1)
    small_group = sum(1 for _, n, _, _ in citations if 2 <= n <= 4)
    large_group = sum(1 for _, n, _, _ in citations if n > 4)

    # 计算百分比
    distribution = {
        "total_citations": total,
        "single_cite_count": single,
        "single_cite_pct": round(single / total * 100, 1),
        "small_group_count": small_group,
        "small_group_pct": round(small_group / total * 100, 1),
        "large_group_count": large_group,
        "large_group_pct": round(large_group / total * 100, 1),
        "max_keys_in_one_cite": max(n for _, n, _, _ in citations),
    }

    # 目标范围（允许一定容差）
    target = {
        "single_target": 70.0,
        "single_tolerance": 5.0,  # 65%-75%
        "small_group_target": 25.0,
        "small_group_tolerance": 5.0,  # 20%-30%
        "large_group_max": 5.0,
        "large_group_tolerance": 5.0,  # 允许到 10%
    }

    # 检查是否符合目标
    single_ok = abs(distribution["single_cite_pct"] - target["single_target"]) <= target["single_tolerance"]
    small_group_ok = abs(distribution["small_group_pct"] - target["small_group_target"]) <= target["small_group_tolerance"]
    large_group_ok = distribution["large_group_pct"] <= (target["large_group_max"] + target["large_group_tolerance"])

    status = {
        "single_ok": single_ok,
        "small_group_ok": small_group_ok,
        "large_group_ok": large_group_ok,
        "overall_pass": single_ok and small_group_ok and large_group_ok
    }

    return {
        "distribution": distribution,
        "target": target,
        "status": status
    }


def find_violations(citations: List[Tuple[str, int, int, List[str]]], threshold: int = 5) -> List[Dict]:
    """
    找出违规的引用（引用数量超过阈值）

    Args:
        citations: 引用列表
        threshold: 引用数量阈值，默认 5

    Returns:
        违规引用列表
    """
    violations = []
    for cite_cmd, n_keys, line_num, _ in citations:
        if n_keys > threshold:
            violations.append({
                "line": line_num,
                "citation": cite_cmd,
                "count": n_keys
            })
    return violations


def generate_recommendations(result: Dict, violations: List[Dict]) -> List[str]:
    """
    根据分析结果生成改进建议

    Args:
        result: 分析结果
        violations: 违规列表

    Returns:
        建议列表
    """
    recommendations = []

    dist = result.get("distribution", {})
    status = result.get("status", {})

    # 检查单篇引用比例
    if not status.get("single_ok", True):
        single_pct = dist.get("single_cite_pct", 0)
        if single_pct < 65:
            recommendations.append(
                "单篇引用比例过低（当前 {:.1f}%）。建议将多篇引用拆分为多个独立的引用陈述。".format(single_pct)
            )
        elif single_pct > 75:
            recommendations.append(
                "单篇引用比例过高（当前 {:.1f}%）。建议适当增加对比文献的引用。".format(single_pct)
            )

    # 检查大组引用
    if not status.get("large_group_ok", True):
        large_pct = dist.get("large_group_pct", 0)
        recommendations.append(
            "大组引用（>4篇）比例过高（当前 {:.1f}%）。建议将文献按观点拆分，采用'引用+阐述+再引用'的模式。".format(large_pct)
        )

    # 检查严重违规
    if violations:
        max_count = max(v["count"] for v in violations)
        if max_count > 10:
            recommendations.append(
                "存在单次引用 {} 篇文献的严重违规情况。这是'引用堆砌'的典型特征，必须立即修正。".format(max_count)
            )

    if not recommendations:
        recommendations.append("引用分布符合目标，继续保持。")

    return recommendations


# ===================================================================
# 引用多样性检测（Citation Diversity）功能
# ===================================================================

def parse_paragraphs(tex_content: str) -> List[Dict]:
    """
    解析 LaTeX 内容为段落列表，统计每段的引用数

    Args:
        tex_content: LaTeX 文件内容

    Returns:
        段落列表，每个段落包含 text, cite_count, line_start, line_end
    """
    paragraphs = []
    lines = _strip_comments(tex_content).split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 跳过注释行、空行、LaTeX 命令行
        if not line or line.startswith('%') or (
            line.startswith('\\') and not re.match(r'\\cite[a-zA-Z*]*(?:\s|\[|\{|$)', line)
        ):
            i += 1
            continue

        # 收集段落内容（直到空行或新命令）
        paragraph_lines = []
        start_line = i + 1
        while i < len(lines):
            current = lines[i].strip()
            if not current or current.startswith('\\') and current.startswith('%'):
                break
            paragraph_lines.append(lines[i])
            i += 1

        if paragraph_lines:
            paragraph_text = '\n'.join(paragraph_lines)
            cite_count = len(extract_citations(paragraph_text))
            paragraphs.append({
                'text': paragraph_text[:100] + '...' if len(paragraph_text) > 100 else paragraph_text,
                'cite_count': cite_count,
                'line_start': start_line,
                'line_end': i
            })

        i += 1

    return paragraphs


def extract_bib_keys(bib_content: str) -> set:
    """
    从 BibTeX 文件内容中提取所有条目的 key

    Args:
        bib_content: BibTeX 文件内容

    Returns:
        所有文献 key 的集合
    """
    pattern = r'@+\w+\s*\{([^,]+),'
    keys = re.findall(pattern, bib_content)
    return set(keys)


def check_citation_diversity(
    tex_content: str,
    citations: List[Tuple[str, int, int, List[str]]],
    bib_keys: Optional[set] = None,
    *,
    min_ref_util: Optional[float] = None,
) -> Dict:
    """
    检查引用多样性，包含 4 个维度：
    1. 零引用段落率
    2. 段落引用密度方差
    3. 文献利用率
    4. 高频文献占比

    Args:
        tex_content: LaTeX 文件内容
        citations: 引用列表
        bib_keys: BibTeX 文献 key 集合（可选，如果不提供则跳过文献利用率检测）

    Returns:
        包含 4 个指标及通过状态的字典
    """
    # 解析段落
    paragraphs = parse_paragraphs(tex_content)
    total_paragraphs = len(paragraphs)

    if total_paragraphs == 0:
        return {
            "error": "No content paragraphs found",
            "diversity_metrics": {}
        }

    # 指标 1：零引用段落率
    zero_cite_paragraphs = [p for p in paragraphs if p['cite_count'] == 0]
    zero_cite_rate = round(len(zero_cite_paragraphs) / total_paragraphs * 100, 1)

    # 指标 2：段落引用密度方差
    cite_counts = [p['cite_count'] for p in paragraphs]
    cite_variance = round(stdev(cite_counts), 2) if len(cite_counts) > 1 else 0.0

    # 指标 3：文献利用率（需要提供 bib_keys）
    reference_utilization = None
    if bib_keys:
        used_keys = set()
        for _, _, _, keys in citations:
            used_keys.update(keys)
        reference_utilization = round(len(used_keys) / len(bib_keys) * 100, 1)

    # 指标 4：高频文献占比（被引用 >=5 次）
    key_freq = defaultdict(int)
    for _, _, _, keys in citations:
        for key in keys:
            key_freq[key] += 1

    if key_freq:
        high_freq_count = sum(1 for f in key_freq.values() if f >= 5)
        high_freq_rate = round(high_freq_count / len(key_freq) * 100, 1)
    else:
        high_freq_rate = 0.0

    # 汇总结果
    diversity_metrics = {
        "zero_cite_rate": zero_cite_rate,
        "zero_cite_count": len(zero_cite_paragraphs),
        "total_paragraphs": total_paragraphs,
        "cite_variance": cite_variance,
        "avg_cites_per_paragraph": round(sum(cite_counts) / total_paragraphs, 1),
        "reference_utilization": reference_utilization,
        "high_freq_rate": high_freq_rate,
        "high_freq_count": high_freq_count if key_freq else 0,
        "total_unique_references": len(key_freq) if key_freq else 0,
    }

    # 目标阈值
    # 注意：文献利用率默认仅提示，不作为硬性门槛；需要时可用 --min-ref-util 启用硬门槛。
    target = {
        "zero_cite_max": 10.0,  # 零引用段落率 <10%
        "cite_variance_max": 3.0,  # 方差 <3
        "ref_util_min": float(min_ref_util) if min_ref_util is not None else None,
        "high_freq_max": 15.0,  # 高频占比 <15%
    }

    # 检查通过状态
    ref_util_ok = True
    if target["ref_util_min"] is not None and reference_utilization is not None:
        ref_util_ok = reference_utilization >= float(target["ref_util_min"])

    status = {
        "zero_cite_ok": zero_cite_rate < target["zero_cite_max"],
        "cite_variance_ok": cite_variance < target["cite_variance_max"],
        "ref_util_ok": ref_util_ok,
        "high_freq_ok": high_freq_rate < target["high_freq_max"],
        "overall_pass": (
            zero_cite_rate < target["zero_cite_max"] and
            cite_variance < target["cite_variance_max"] and
            ref_util_ok and
            high_freq_rate < target["high_freq_max"]
        )
    }

    return {
        "diversity_metrics": diversity_metrics,
        "target": target,
        "status": status,
        "zero_cite_paragraphs": zero_cite_paragraphs[:10],  # 最多返回前10个
        "cite_distribution": cite_counts
    }


def find_zero_cite_paragraphs(tex_content: str) -> List[Dict]:
    """
    找出所有零引用段落

    Args:
        tex_content: LaTeX 文件内容

    Returns:
        零引用段落列表
    """
    paragraphs = parse_paragraphs(tex_content)
    return [p for p in paragraphs if p['cite_count'] == 0]


def generate_diversity_recommendations(diversity_result: Dict) -> List[str]:
    """
    根据引用多样性检测结果生成改进建议

    Args:
        diversity_result: check_citation_diversity() 返回的结果

    Returns:
        建议列表
    """
    recommendations = []
    metrics = diversity_result.get("diversity_metrics", {})
    status = diversity_result.get("status", {})
    target = diversity_result.get("target", {})

    # 检查零引用段落
    if not status.get("zero_cite_ok", True):
        zero_rate = metrics.get("zero_cite_rate", 0)
        zero_count = metrics.get("zero_cite_count", 0)
        recommendations.append(
            f"零引用段落比例过高（当前 {zero_rate}%，共 {zero_count} 段）。"
            f"建议：每个段落至少引用 1-2 篇文献以提供证据支撑。"
        )

    # 检查引用密度方差
    if not status.get("cite_variance_ok", True):
        variance = metrics.get("cite_variance", 0)
        recommendations.append(
            f"段落引用密度分布不均（方差 {variance}，目标 <3）。"
            f"建议：平衡各段落的引用数量，避免某段过度引用而其他段落引用不足。"
        )

    # 检查文献利用率
    if target.get("ref_util_min") is not None and not status.get("ref_util_ok", True):
        util = metrics.get("reference_utilization", 0)
        total_refs = metrics.get("total_unique_references", 0)
        recommendations.append(
            f"文献利用率偏低（当前 {util}%，仅 {total_refs} 篇被引用）。"
            f"建议：不要为“用完文献”而强行加引用；优先回到选文阶段减少噪声，或把重要文献对应的观点写出来再自然引用。"
        )

    # 检查高频文献
    if not status.get("high_freq_ok", True):
        high_freq_rate = metrics.get("high_freq_rate", 0)
        recommendations.append(
            f"高频文献占比过高（当前 {high_freq_rate}%）。"
            f"建议：避免过度依赖少数几篇文献，应增加引用的多样性以体现全面调研。"
        )

    if not recommendations:
        recommendations.append("引用多样性符合目标，继续保持。")

    return recommendations


def main():
    parser = argparse.ArgumentParser(
        description='验证 LaTeX 文件中的引用分布是否符合人类学术写作习惯',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
目标分布（基于人类学术写作习惯）：
  - 单篇引用（1篇）：约 70%%
  - 小组引用（2-4篇）：约 25%%
  - 大组引用（>4篇）：<5%%

引用多样性指标：
  - 零引用段落率：<10%%
  - 段落引用密度方差：<3
  - 文献利用率：默认仅提示展示（可用 --min-ref-util 启用硬门槛）
  - 高频文献占比：<15%%

示例：
  %(prog)s review.tex
  %(prog)s review.tex --output report.json
  %(prog)s review.tex --threshold 4
  %(prog)s review.tex --check-diversity --bib references.bib
        """
    )

    parser.add_argument('tex_file', help='LaTeX 文件路径')
    parser.add_argument('--output', '-o', help='输出 JSON 结果到文件')
    parser.add_argument('--threshold', '-t', type=int, default=5,
                        help='违规阈值（单次引用超过此数量将被标记，默认：5）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='显示详细输出')
    parser.add_argument('--check-diversity', '-d', action='store_true',
                        help='启用引用多样性检测（需要 --bib 参数）')
    parser.add_argument('--bib', '-b', help='BibTeX 文件路径（用于文献利用率检测）')
    parser.add_argument('--min-ref-util', type=float, default=None,
                        help='可选：启用文献利用率硬门槛（例如 60/70/85）；默认仅展示指标，不做硬性门槛')

    args = parser.parse_args()

    tex_path = Path(args.tex_file)
    if not tex_path.exists():
        print(f"❌ 错误：文件不存在 {tex_path}")
        return 1

    # 读取 LaTeX 文件
    try:
        tex_content = tex_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"❌ 错误：无法读取文件 {e}")
        return 1

    # 提取引用
    citations = extract_citations(tex_content)

    if not citations:
        print(f"⚠️  警告：未找到任何 \\cite{{}} 命令")
        return 0

    # 分析引用分布
    result = analyze_distribution(citations)

    # 找出违规
    violations = find_violations(citations, args.threshold)

    # 生成建议
    recommendations = generate_recommendations(result, violations)

    # 引用多样性检测（可选）
    diversity_result = None
    diversity_recommendations = []
    if args.check_diversity:
        bib_keys = None
        if args.bib:
            bib_path = Path(args.bib)
            if bib_path.exists():
                try:
                    bib_content = bib_path.read_text(encoding='utf-8')
                    bib_keys = extract_bib_keys(bib_content)
                except Exception as e:
                    print(f"⚠️  警告：无法读取 BibTeX 文件 {e}")
            else:
                print(f"⚠️  警告：BibTeX 文件不存在 {args.bib}")
        else:
            print("ℹ️  提示：未提供 --bib 参数，文献利用率检测将被跳过")

        diversity_result = check_citation_diversity(
            tex_content,
            citations,
            bib_keys,
            min_ref_util=args.min_ref_util,
        )
        diversity_recommendations = generate_diversity_recommendations(diversity_result)

    # 输出报告
    print("=" * 70)
    print("📊 引用分布验证报告")
    print("=" * 70)
    print(f"文件: {tex_path}")
    print(f"总引用次数: {result['distribution']['total_citations']}")
    print()

    print("📈 分布统计:")
    print(f"  单篇引用 (1篇):     {result['distribution']['single_cite_count']:4d} 次 ({result['distribution']['single_cite_pct']:5.1f}%)  [目标: 70% ±5%]")
    print(f"  小组引用 (2-4篇):   {result['distribution']['small_group_count']:4d} 次 ({result['distribution']['small_group_pct']:5.1f}%)  [目标: 25% ±5%]")
    print(f"  大组引用 (>4篇):    {result['distribution']['large_group_count']:4d} 次 ({result['distribution']['large_group_pct']:5.1f}%)  [目标: <5% ±5%]")
    print()
    print(f"📊 单次最大引用数: {result['distribution']['max_keys_in_one_cite']} 篇")
    print()

    print("✅ 状态检查:")
    print(f"  单篇引用:   {'✓ 通过' if result['status']['single_ok'] else '✗ 失败'}")
    print(f"  小组引用:   {'✓ 通过' if result['status']['small_group_ok'] else '✗ 失败'}")
    print(f"  大组引用:   {'✓ 通过' if result['status']['large_group_ok'] else '✗ 失败'}")
    print()
    print(f"{'🎉 分布总体结果: ✓ 通过' if result['status']['overall_pass'] else '❌ 分布总体结果: ✗ 失败'}")
    print()

    # 显示违规
    if violations:
        print(f"⚠️  违规引用 (>{args.threshold}篇) 共 {len(violations)} 处:")
        for v in violations[:20]:
            print(f"  行 {v['line']:4d}: {v['citation'][:60]}{'...' if len(v['citation'])>60 else ''} ({v['count']}篇)")
        if len(violations) > 20:
            print(f"  ... 还有 {len(violations)-20} 处未显示")
        print()

    # 显示引用多样性报告
    if diversity_result:
        print("🌐 引用多样性检测:")
        print("-" * 70)

        if "error" in diversity_result:
            print(f"⚠️  {diversity_result['error']}")
        else:
            metrics = diversity_result['diversity_metrics']
            status = diversity_result['status']
            target = diversity_result.get('target', {})

            print(f"  零引用段落率:     {metrics['zero_cite_rate']:5.1f}% ({metrics['zero_cite_count']}/{metrics['total_paragraphs']})  [目标: <10%]  {'✓' if status['zero_cite_ok'] else '✗'}")
            print(f"  段落引用密度方差: {metrics['cite_variance']:5.2f}  [目标: <3]  {'✓' if status['cite_variance_ok'] else '✗'}")
            print(f"  平均每段引用数:   {metrics['avg_cites_per_paragraph']:5.1f}")

            if metrics['reference_utilization'] is not None:
                if target.get("ref_util_min") is None:
                    print(f"  文献利用率:       {metrics['reference_utilization']:5.1f}% ({metrics['total_unique_references']} 篇被引用)  [提示项：不做硬性门槛]")
                else:
                    print(f"  文献利用率:       {metrics['reference_utilization']:5.1f}% ({metrics['total_unique_references']} 篇被引用)  [目标: >{target['ref_util_min']:.0f}%]  {'✓' if status['ref_util_ok'] else '✗'}")
            else:
                print(f"  文献利用率:       (未提供 BibTeX 文件)")

            print(f"  高频文献占比:     {metrics['high_freq_rate']:5.1f}% ({metrics['high_freq_count']} 篇被引用≥5次)  [目标: <15%]  {'✓' if status['high_freq_ok'] else '✗'}")
            print()
            print(f"{'🎉 多样性总体结果: ✓ 通过' if status['overall_pass'] else '❌ 多样性总体结果: ✗ 失败'}")
            print()

            # 显示零引用段落
            if diversity_result.get('zero_cite_paragraphs'):
                print(f"📌 零引用段落 (共 {metrics['zero_cite_count']} 段):")
                for p in diversity_result['zero_cite_paragraphs'][:5]:
                    print(f"  行 {p['line_start']:4d}: {p['text'][:60]}...")
                if metrics['zero_cite_count'] > 5:
                    print(f"  ... 还有 {metrics['zero_cite_count']-5} 段未显示")
                print()
        print()

    # 显示建议
    all_recommendations = recommendations + diversity_recommendations
    if args.verbose or not result['status']['overall_pass'] or (diversity_result and not diversity_result['status']['overall_pass']):
        print("💡 改进建议:")
        for i, rec in enumerate(all_recommendations, 1):
            print(f"  {i}. {rec}")
        print()

    # 输出 JSON
    if args.output:
        output_data = {
            "file": str(tex_path),
            "result": result,
            "violations": violations,
            "recommendations": recommendations,
            "diversity_result": diversity_result,
            "diversity_recommendations": diversity_recommendations
        }
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"📁 结果已保存至: {args.output}")
        except Exception as e:
            print(f"⚠️  无法保存输出文件: {e}")

    # 返回状态：任一检测失败则返回 1
    pass_dist = result['status']['overall_pass']
    pass_div = diversity_result['status']['overall_pass'] if diversity_result else True
    return 0 if (pass_dist and pass_div) else 1


if __name__ == '__main__':
    exit(main())
