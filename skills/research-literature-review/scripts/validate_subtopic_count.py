#!/usr/bin/env python3
"""
validate_subtopic_count.py - 验证综述正文的子主题数量

目标：除摘要/引言/讨论/展望/结论外，应有 3-7 个子主题 section
参考：Problems_from_breast-test-02.md 中的"主题过多"问题
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# 标准章节名称（不计入子主题）
STANDARD_SECTIONS = {
    "abstract",
    "摘要",
    "introduction",
    "引言",
    "discussion",
    "讨论",
    "conclusion",
    "结论",
    "outlook",
    "展望",
    "future work",
    "perspectives",
    "methods",
    "方法",
    "未来工作",
    "acknowledgement",
    "acknowledgments",
    "致谢",
    "references",
    "参考文献",
}


def count_subsections(tex_file: Path) -> dict:
    """统计子主题 section 数量"""
    content = re.sub(r"(?<!\\)%[^\n]*", "", tex_file.read_text(encoding="utf-8"))

    # 匹配 \section{...} 或 \section*{...}
    section_pattern = r"\\section\*?\{([^}]+)\}"
    matches = re.findall(section_pattern, content)

    # 清理标题（去除空白、编号）
    cleaned_sections = []
    for m in matches:
        # 去除前后空白
        title = m.strip()
        # 去除 TeX 标记（如 \label{}）
        title = re.sub(r"\\label\{[^}]+\}", "", title)
        title = title.strip()

        # 转小写用于标准章节判断
        title_lower = title.lower()

        # 检查是否是标准章节
        is_standard = False
        for std in STANDARD_SECTIONS:
            if std.lower() in title_lower or title_lower in std.lower():
                is_standard = True
                break

        if not is_standard:
            cleaned_sections.append(title)

    return {
        "total_sections": len(matches),
        "standard_sections": len(matches) - len(cleaned_sections),
        "subtopic_sections": len(cleaned_sections),
        "subtopic_list": cleaned_sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="验证综述正文的子主题数量")
    parser.add_argument("--tex", required=True, type=Path, help="LaTeX 综述文件路径")
    parser.add_argument("--min-subtopics", type=int, default=3, help="最小子主题数量（默认3）")
    parser.add_argument("--max-subtopics", type=int, default=7, help="最大子主题数量（默认7）")
    args = parser.parse_args()

    if not args.tex.exists():
        print(f"✗ 文件不存在: {args.tex}", file=sys.stderr)
        return 1

    result = count_subsections(args.tex)

    print(f"\n📊 子主题数量验证报告")
    print(f"   文件: {args.tex.name}")
    print(f"   总 section 数: {result['total_sections']}")
    print(f"   标准章节数: {result['standard_sections']}")
    print(f"   子主题 section 数: {result['subtopic_sections']}")
    print(f"   目标范围: {args.min_subtopics}-{args.max_subtopics}")

    if result['subtopic_list']:
        print(f"\n   子主题列表:")
        for i, topic in enumerate(result['subtopic_list'], 1):
            print(f"     {i}. {topic}")

    # 验证
    passed = args.min_subtopics <= result['subtopic_sections'] <= args.max_subtopics

    if passed:
        print(f"\n✅ 验证通过：子主题数量 {result['subtopic_sections']} 在目标范围内")
    else:
        if result['subtopic_sections'] < args.min_subtopics:
            print(f"\n❌ 验证失败：子主题数量 {result['subtopic_sections']} 少于最小值 {args.min_subtopics}")
            print("   建议：考虑是否需要拆分某些大主题")
        else:
            print(f"\n❌ 验证失败：子主题数量 {result['subtopic_sections']} 超过最大值 {args.max_subtopics}")
            print("   建议：合并相似主题（如 CNN/Transformer → '深度学习模型架构'）")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
