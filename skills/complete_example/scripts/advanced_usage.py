"""
Complete Example Skill - 高级使用示例
展示如何使用 narrative_hint 参数自定义叙事方向
"""

import sys
from pathlib import Path

# 添加 skill 目录到路径
skill_root = Path(__file__).parent.parent
sys.path.insert(0, str(skill_root))

from scripts.skill_controller import CompleteExampleSkill


def example_medical_imaging():
    """示例 1：医疗影像场景"""
    print("=" * 60)
    print("示例 1：医疗影像 - 深度学习在医疗影像分析中的应用")
    print("=" * 60)

    skill = create_skill()

    result = skill.execute(
        project_name="NSFC_Young",
        options={
            "content_density": "moderate",
            "output_mode": "preview",
            "narrative_hint": (
                "生成一个关于深度学习在医疗影像分析中应用的示例，"
                "重点关注 CNN 架构和数据增强策略。"
                "编造一个肺结节检测的研究场景。"
            )
        }
    )

    print_result(result)


def example_material_science():
    """示例 2：材料科学场景"""
    print("\n" + "=" * 60)
    print("示例 2：材料科学 - 新型纳米材料合成与表征")
    print("=" * 60)

    skill = create_skill()

    result = skill.execute(
        project_name="NSFC_Young",
        options={
            "content_density": "comprehensive",
            "output_mode": "preview",
            "narrative_hint": (
                "创建一个关于新型纳米材料合成与表征的示例，"
                "包括 XRD、SEM、TEM 等表征方法。"
                "编造一种用于催化的新型金属氧化物纳米材料。"
            )
        }
    )

    print_result(result)


def example_clinical_trial():
    """示例 3：临床试验场景"""
    print("\n" + "=" * 60)
    print("示例 3：临床试验 - 多中心随机对照试验")
    print("=" * 60)

    skill = create_skill()

    result = skill.execute(
        project_name="NSFC_Young",
        options={
            "content_density": "moderate",
            "output_mode": "preview",
            "narrative_hint": (
                "模拟一个多中心临床试验的设计与分析流程，"
                "重点描述随机化、盲法实施和统计分析计划。"
                "编造一个关于新药疗效评估的三期临床试验。"
            )
        }
    )

    print_result(result)


def example_traditional_ml():
    """示例 4：传统机器学习场景"""
    print("\n" + "=" * 60)
    print("示例 4：传统机器学习 - 支持向量机分类")
    print("=" * 60)

    skill = create_skill()

    result = skill.execute(
        project_name="NSFC_Young",
        options={
            "content_density": "minimal",
            "output_mode": "preview",
            "narrative_hint": (
                "编写一个使用支持向量机（SVM）进行分类的示例研究。"
                "对比不同核函数的性能，并使用网格搜索优化参数。"
            )
        }
    )

    print_result(result)


def example_apply_mode():
    """示例 5：应用模式（直接修改文件）"""
    print("\n" + "=" * 60)
    print("示例 5：应用模式（直接修改文件，有备份）")
    print("=" * 60)

    skill = create_skill()

    result = skill.execute(
        project_name="NSFC_Young",
        options={
            "content_density": "moderate",
            "output_mode": "apply",  # 注意：这会直接修改文件！
            "target_files": ["extraTex/1.2.内容目标问题.tex"],
            "narrative_hint": "生成一个示例段落"
        }
    )

    print_result(result)
    print("\n注意：文件已被修改，备份保存在 .complete_example/<run_id>/backups/")


def create_skill():
    """创建 skill 实例"""
    import yaml
    config_path = skill_root / "config.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['skill_root'] = str(skill_root)

    return CompleteExampleSkill(config)


def print_result(result):
    """打印结果摘要"""
    print(f"\n执行状态：{result['final_result']}")
    print(f"运行 ID：{result['run_id']}")
    print(f"运行目录：{result['run_dir']}")

    if result['final_result'] == 'success':
        print("\n各阶段摘要：")
        for stage_name, stage_data in result['stages'].items():
            print(f"  - {stage_name}: {stage_data['status']}")

            # 打印特定阶段的详细信息
            if stage_name == 'scan' and 'summary' in stage_data:
                for k, v in stage_data['summary'].items():
                    print(f"      {k}: {v}")

            if stage_name == 'quality' and 'evaluations' in stage_data:
                for file_path, eval_data in stage_data['evaluations'].items():
                    print(f"      {file_path}:")
                    print(f"        总体评分: {eval_data.get('overall_score', 'N/A')}")
    else:
        print(f"\n错误：{result.get('error', '未知错误')}")


def main():
    """运行所有示例"""
    print("Complete Example Skill - 高级使用示例")
    print("展示如何使用 narrative_hint 参数自定义叙事方向\n")

    # 运行示例（可以根据需要注释掉某些示例）
    example_medical_imaging()
    # example_material_science()
    # example_clinical_trial()
    # example_traditional_ml()
    # example_apply_mode()  # 谨慎使用：会直接修改文件！


if __name__ == "__main__":
    main()
