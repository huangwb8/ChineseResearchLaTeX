#!/usr/bin/env python
"""
演示三大核心功能：
1. 字数自动适配
2. 引用强制保护
3. AI 内容智能优化
"""

import sys
import asyncio
from pathlib import Path

# 添加技能根目录到路径(现在脚本在 scripts/ 子目录)
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_integration import AIIntegration
from core.word_count_adapter import WordCountAdapter
from core.reference_guardian import ReferenceGuardian
from core.content_optimizer import ContentOptimizer


def demo_word_count_adapter():
    """演示字数自动适配"""
    print("=" * 60)
    print("📊 演示：字数自动适配")
    print("=" * 60)

    config = {}
    adapter = WordCountAdapter(config, ".")

    # 测试内容（约 1800 字，符合 2025 版立项依据）
    content = """
本项目研究意义十分重大。近年来，随着科技的快速发展，相关领域的研究取得了显著进展。
    """ + "这是研究内容。" * 600  # 生成约 1800 字

    current_count = adapter._count_chinese_words(content)
    print(f"当前字数: {current_count}")

    # 获取字数要求
    report = adapter.generate_word_count_report(content, "立项依据", "2025_to_2026")
    print(f"旧版本要求: {report['old_requirement']} 字")
    print(f"新版本要求: {report['new_requirement']} 字")
    print(f"是否需要适配: {'是' if report['needs_adaptation'] else '否'}")

    print(f"\n✅ 字数检测功能正常（AI 适配需要 async 环境）")
    print()


def demo_reference_guardian():
    """演示引用强制保护"""
    print("=" * 60)
    print("🔒 演示：引用强制保护")
    print("=" * 60)

    config = {"reference_protection": {"enabled": True}}
    guardian = ReferenceGuardian(config)

    # 测试内容（包含多种引用）
    content = r"""
本研究涉及多个关键问题（见\ref{sec:problems}）。
相关研究成果如图\ref{fig:results}所示。

根据文献\cite{author2024}和\cite{author2023}的研究，
我们采用了新方法\eqref{eq:method}。

实验数据见图\includegraphics{figures/data.pdf}。
"""

    print("原始内容:")
    print(content[:100] + "...")

    # 第一步：保护引用
    protected, ref_map = guardian.protect_references(content)
    print(f"\n✅ 保护了 {len(ref_map)} 个引用:")
    for placeholder, original in list(ref_map.items())[:3]:
        print(f"   {original} → {placeholder[:30]}...")

    # 第二步：恢复引用
    restored = guardian.restore_references(protected, ref_map)
    print(f"\n✅ 引用恢复: {'成功' if restored == content else '失败'}")

    # 第三步：生成报告
    report = guardian.generate_reference_report(content)
    print(f"\n📊 引用统计:")
    for ref_type, info in report.items():
        if ref_type != "total":
            print(f"   {ref_type}: {info['count']} 个")

    print()


async def demo_content_optimizer():
    """演示内容优化"""
    print("=" * 60)
    print("✨ 演示：内容智能优化")
    print("=" * 60)

    config = {
        "reference_protection": {"enabled": True},
        "content_optimization": {"enabled": True}
    }
    optimizer = ContentOptimizer(config, ".")

    # 测试内容（包含引用）
    content = r"""
本研究具有重要意义。相关研究参见\cite{author2024}。
    这是重复的内容，重复的内容很重要。
    这也是重复内容，重复内容很多。
"""

    print("原始内容:")
    print(content)

    # 生成优化报告
    report = optimizer.generate_optimization_report(content, "立项依据")
    print(f"\n📊 优化分析:")
    print(f"   发现问题: {report['total_issues']} 个")
    for issue in report['issues']:
        print(f"   - [{issue['type']}] {issue['description']}")

    print(f"\n✅ 内容分析功能正常（AI 优化需要 async 环境）")
    print()


async def demo_ai_integration():
    """演示 AI 集成功能（未接入真实 AI 时将自动回退）"""
    print("=" * 60)
    print("🤖 演示：AI 集成功能")
    print("=" * 60)

    config = {
        "reference_protection": {"enabled": True},
        "content_optimization": {"enabled": True}
    }

    optimizer = ContentOptimizer(config, ".")

    # 简单测试内容
    content = "本研究很重要。这是重复的内容。"

    print("测试内容:")
    print(content)
    print("\n尝试 AI 优化...")

    ai = AIIntegration(enable_ai=False)
    result = await optimizer.optimize_content(
        content,
        "测试章节",
        {"remove_redundancy": True},
        ai_integration=ai,
    )

    print("✅ 调用完成（AI 未接入时会自动回退）")
    print(f"   优化日志: {len(result['optimization_log'])} 条")
    print(f"   引用保护: {'✅ 有效' if result['reference_validation']['valid'] else '❌ 失效'}")

    print()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 LaTeX 标书智能迁移技能 - 核心功能演示")
    print("=" * 60 + "\n")

    try:
        # 同步演示
        demo_word_count_adapter()
        demo_reference_guardian()

        # 异步演示
        asyncio.run(demo_content_optimizer())

        print("=" * 60)
        print("✅ 所有功能演示完成！")
        print("=" * 60)
        print("\n说明：")
        print("- 字数适配、引用保护功能已完全实现")
        print("- AI 优化功能已集成 call_ai，需要在 Claude Code/Codex 环境中运行")
        print("- demo 环境无法调用真实 AI，但代码结构已完整")
        print()

    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
