#!/usr/bin/env python3
"""
validate_no_process_leakage.py - 检测综述正文中的 AI 流程泄露

用于检测综述 LaTeX 文件中是否出现了"AI工作流程"相关描述，
这些描述应该放在 {主题}_工作条件.md 中，而非综述正文。

检测目标：
1. 检索流程统计（"基于 X 条文献"、"去重后 Y 条"等）
2. 评分选文流程（"相关性评分系统"、"高分优先选文"等）
3. 完整工作管线（"检索→去重→评分→选文→写作"等）
4. 元操作描述（"字数预算系统"、"多查询策略"等）
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple


# ============================================================================
# 检测模式定义
# ============================================================================

# 检测模式列表：(名称, 正则表达式, 严重性, 描述)
DETECTION_PATTERNS = [
    (
        "文献统计泄露",
        r"本综述(?:基于|共|纳入|涵盖|分析了)\s*\d+\s*条?(?:初检|候选|文献|研究|论文)",
        "high",
        "摘要或正文出现文献数量统计",
    ),
    (
        "去重统计泄露",
        r"去重(?:后|有|(?:保留|剩余)了?)\s*\d+\s*条?(?:文献|研究|论文)",
        "high",
        "出现去重后的文献数量",
    ),
    (
        "选文统计泄露",
        r"(?:最终|筛选出|保留|纳入)\s*(?:\d+\s*篇?|前\s*\d+\s*篇)(?:代表)?(?:研究|文献|论文)",
        "high",
        "出现最终选中的文献数量",
    ),
    (
        "评分流程泄露",
        r"(?:采用|使用|基于)\s*(?:相关性)?评分\s*(?:系统|机制|方法|模型)",
        "high",
        "出现评分系统描述",
    ),
    (
        "评分选文泄露",
        r"高分(?:优先)?(?:比例)?(?:筛选|选文|选择)",
        "medium",
        "出现高分优先选文描述",
    ),
    (
        "工作管线泄露",
        r"(?:方法学(?:上|中)?，?(?:本综述)?)?按照[\s\S]*?(?:检索|搜索|查询)[\s\S]*?(?:去重)[\s\S]*?(?:相关性)?评分[\s\S]*?(?:高分)?(?:选文|筛选)",
        "high",
        "出现完整工作管线描述",
    ),
    (
        "检索策略泄露",
        r"(?:文献)?(?:检索|搜索|查询)(?:采用|使用|基于)?\s*(?:多查询|多策略|并行|变体)",
        "medium",
        "出现检索策略描述",
    ),
    (
        "数据库泄露",
        r"OpenAlex|PubMed|Web of Science|IEEE Xplore\s*(?:数据库|API|数据源)",
        "medium",
        "出现数据库名称（应在工作条件中）",
    ),
    (
        "字数预算泄露",
        r"(?:字数|词数)(?:预算|分配|规划)(?:系统|机制|方法)",
        "medium",
        "出现字数预算系统描述",
    ),
    (
        "流程关键词",
        r"\b(?:检索|去重|相关性评分|选文|字数预算)(?:流程|管线|步骤|阶段)\b",
        "medium",
        "出现流程关键词组合",
    ),
]


# ============================================================================
# 核心检测逻辑
# ============================================================================


def load_file_content(tex_path: Path) -> str:
    """读取 LaTeX 文件内容，移除注释和纯代码块"""
    if not tex_path.exists():
        raise FileNotFoundError(f"文件不存在: {tex_path}")

    content = tex_path.read_text(encoding="utf-8", errors="replace")

    # 移除 LaTeX 注释
    content = re.sub(r"%.*$", "", content, flags=re.MULTILINE)

    # 移除常见的纯代码环境（这些不包含正文内容）
    # 保留 \section, \subsection, \paragraph 等结构命令后的内容
    pure_code_envs = [
        r"\\bibliography\{[^}]*\}",
        r"\\bibliographystyle\{[^}]*\}",
        r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
        r"\\documentclass(?:\[.*?\])?\{.*?\}",
        r"\\usepackage(?:\[.*?\])?\{.*?\}",
    ]

    for env_pattern in pure_code_envs:
        content = re.sub(env_pattern, "", content, flags=re.DOTALL)

    return content


def detect_leakage(content: str, patterns: List[Tuple[str, str, str, str]]) -> defaultdict:
    """执行检测并返回结果"""
    results = defaultdict(lambda: {"matches": [], "severity": "unknown", "description": ""})

    for name, pattern, severity, description in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            # 提取匹配行的上下文
            lines_before = content[:match.start()].split("\n")
            line_num = len(lines_before)
            line_text = lines_before[-1].strip() if lines_before else ""

            results[name]["matches"].append({
                "line": line_num,
                "text": line_text[:100],  # 限制长度
                "match": match.group(0),
            })
            results[name]["severity"] = severity
            results[name]["description"] = description

    return results


def format_results(results: defaultdict, total_issues: int) -> str:
    """格式化检测结果"""
    if total_issues == 0:
        return "✅ 未检测到 AI 流程泄露问题\n"

    output = ["\n🔍 检测到 AI 流程泄露问题\n", "=" * 70]

    # 按严重性分组
    high_issues = []
    medium_issues = []

    for name, data in results.items():
        if not data["matches"]:
            continue
        issue_info = (name, data)
        if data["severity"] == "high":
            high_issues.append(issue_info)
        else:
            medium_issues.append(issue_info)

    if high_issues:
        output.append("\n🔴 严重问题（必须修复）:")
        output.append("-" * 70)
        for name, data in high_issues:
            output.append(f"\n⚠️  {name}: {data['description']}")
            for match in data["matches"][:3]:  # 限制显示数量
                output.append(f"   第 {match['line']} 行: {match['text']}")
            if len(data["matches"]) > 3:
                output.append(f"   ... 还有 {len(data['matches']) - 3} 处匹配")

    if medium_issues:
        output.append("\n🟡 中等问题（建议修复）:")
        output.append("-" * 70)
        for name, data in medium_issues:
            output.append(f"\n⚠️  {name}: {data['description']}")
            for match in data["matches"][:3]:
                output.append(f"   第 {match['line']} 行: {match['text']}")
            if len(data["matches"]) > 3:
                output.append(f"   ... 还有 {len(data['matches']) - 3} 处匹配")

    output.append("\n" + "=" * 70)
    output.append("\n💡 修复建议:")
    output.append("1. 删除综述正文中的上述内容")
    output.append("2. 将方法学信息移至 {主题}_工作条件.md 的相应章节")
    output.append("3. 确保综述正文完全聚焦领域知识")
    output.append(f"\n详细说明见: references/expert-review-writing.md 的'内容分离原则'章节\n")

    return "\n".join(output)


# ============================================================================
# CLI 接口
# ============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="检测综述正文中的 AI 流程泄露",
        epilog="示例: python validate_no_process_leakage.py review.tex"
    )
    parser.add_argument(
        "tex_file",
        type=Path,
        help="要检测的 LaTeX 文件路径",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细匹配信息",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        content = load_file_content(args.tex_file)
    except FileNotFoundError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ 读取文件失败: {e}", file=sys.stderr)
        return 1

    results = detect_leakage(content, DETECTION_PATTERNS)
    total_issues = sum(len(data["matches"]) for data in results.values())

    if args.json:
        # JSON 输出（用于脚本集成）
        import json
        json_data = {
            "total_issues": total_issues,
            "passed": total_issues == 0,
            "issues": {
                name: {
                    "severity": data["severity"],
                    "description": data["description"],
                    "count": len(data["matches"]),
                    "matches": data["matches"] if args.verbose else [],
                }
                for name, data in results.items()
                if data["matches"]
            }
        }
        print(json.dumps(json_data, ensure_ascii=False, indent=2))
        # JSON 模式也要返回正确的退出码
        if total_issues > 0:
            return 1
        return 0
    else:
        # 人性化输出
        print(f"\n📄 检测文件: {args.tex_file.name}")
        print(format_results(results, total_issues))

        if total_issues > 0:
            print(f"总计: {total_issues} 处问题")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
