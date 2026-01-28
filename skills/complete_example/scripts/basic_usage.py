"""
Complete Example Skill - 基本使用示例
"""

import sys
from pathlib import Path

# 添加 skill 目录到路径
skill_root = Path(__file__).parent.parent
sys.path.insert(0, str(skill_root))

from scripts.skill_controller import CompleteExampleSkill


def main():
    """基本使用示例"""

    # 1. 加载配置
    import yaml
    config_path = skill_root / "config.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['skill_root'] = str(skill_root)

    # 2. 创建 skill 实例
    skill = CompleteExampleSkill(config)

    # 3. 执行（基本使用，AI 自动推断）
    result = skill.execute(
        project_name="NSFC_Young",
        options={
            "content_density": "moderate",
            "output_mode": "preview",
            "target_files": ["extraTex/2.1.研究内容.tex"]
        }
    )

    # 4. 查看结果
    print(f"执行状态：{result['final_result']}")
    print(f"运行 ID：{result['run_id']}")
    print(f"运行目录：{result['run_dir']}")

    if result['final_result'] == 'success':
        print("\n各阶段状态：")
        for stage_name, stage_data in result['stages'].items():
            print(f"  - {stage_name}: {stage_data['status']}")


if __name__ == "__main__":
    main()
