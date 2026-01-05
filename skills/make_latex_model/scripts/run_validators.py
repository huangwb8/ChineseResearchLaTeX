#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证器运行器 - 执行所有验证器并生成报告
"""

import argparse
import sys
from pathlib import Path

# 添加 core 目录到路径
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CORE_DIR = SKILL_DIR / "core"
sys.path.insert(0, str(CORE_DIR))

from config_loader import ConfigLoader
from validator_base import ValidatorRegistry, ValidationContext
from validators import CompilationValidator, StyleValidator, HeadingValidator, VisualValidator

# 注册验证器
ValidatorRegistry.register(CompilationValidator)
ValidatorRegistry.register(StyleValidator)
ValidatorRegistry.register(HeadingValidator)
ValidatorRegistry.register(VisualValidator)


def run_validators(project_path: Path, template: str = None, verbose: bool = False):
    """运行所有验证器"""

    # 加载配置
    loader = ConfigLoader()
    config = loader.load_config(project_path, template)

    if not config:
        print(f"错误: 无法加载项目配置")
        return False

    # 创建验证上下文
    tolerance = config.get("validation", {}).get("tolerance", {})
    context = ValidationContext(
        project_path=project_path,
        template_config=config,
        tolerance=tolerance,
        verbose=verbose
    )

    # 加载所有启用的验证器
    validators = ValidatorRegistry.load_all(context)

    if not validators:
        print("警告: 没有启用的验证器")
        return True

    print(f"\n{'='*60}")
    print(f"  make_latex_model 验证报告（Python 版本）")
    print(f"{'='*60}\n")
    print(f"项目路径: {project_path}")
    print(f"模板: {template or '<自动检测>'}")
    print(f"启用的验证器: {len(validators)}")
    print()

    # 执行验证
    all_passed = []
    all_warnings = []
    all_failed = []

    for validator in validators:
        print(f"\n{'-'*60}")
        print(f"运行验证器: {validator.get_name()} (优先级: {validator.get_priority()})")
        print(f"{'-'*60}")

        result = validator.validate(context)

        all_passed.extend(result.passed)
        all_warnings.extend(result.warnings)
        all_failed.extend(result.failed)

        # 打印结果
        for msg in result.passed:
            print(f"✅ {msg}")
        for msg in result.warnings:
            print(f"⚠️  {msg}")
        for msg in result.failed:
            print(f"❌ {msg}")

    # 打印总结
    print(f"\n{'='*60}")
    print(f"验证总结")
    print(f"{'='*60}\n")

    print(f"总检查项: {len(all_passed) + len(all_warnings) + len(all_failed)}")
    print(f"  ✅ 通过: {len(all_passed)}")
    print(f"  ⚠️  警告: {len(all_warnings)}")
    print(f"  ❌ 失败: {len(all_failed)}")
    print()

    if len(all_failed) == 0:
        print("✅ 所有核心检查通过！")
        if len(all_warnings) > 0:
            print(f"⚠️  但有 {len(all_warnings)} 个警告需要注意")
        return True
    else:
        print(f"❌ 有 {len(all_failed)} 个检查失败，需要修复")
        return False


def main():
    parser = argparse.ArgumentParser(description="make_latex_model 验证器运行器")
    parser.add_argument("--project", type=Path, required=True, help="项目路径或名称")
    parser.add_argument("--template", type=str, default=None, help="模板名称")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    success = run_validators(args.project, args.template, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
