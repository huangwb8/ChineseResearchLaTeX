#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式配置向导
引导用户完成 LaTeX 项目的配置

使用方法:
    python scripts/setup_wizard.py

    # 使用预设模板
    python scripts/setup_wizard.py --template nsfc/young

    # 导入历史配置
    python scripts/setup_wizard.py --import old_config.yaml
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SKILL_DIR))

from scripts.core.template_catalog import get_template_catalog


class SetupWizard:
    """交互式配置向导"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.skill_dir = base_dir / "skills" / "make-latex-model"
        self.projects_dir = base_dir / "projects"
        self.answers = {}
        self.template_catalog = get_template_catalog()

    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    def ask(self, question: str, default: Any = None, options: List[str] = None) -> Any:
        """提问"""
        prompt = f"\n{question}"

        if default is not None:
            prompt += f" [默认: {default}]"

        if options:
            prompt += "\n选项:"
            for i, opt in enumerate(options, 1):
                prompt += f"\n  {i}. {opt}"

        prompt += "\n> "

        while True:
            response = input(prompt).strip()

            if not response and default is not None:
                return default

            if options:
                if response.isdigit() and 1 <= int(response) <= len(options):
                    return options[int(response) - 1]
                else:
                    print(f"请输入 1-{len(options)} 之间的数字")
            else:
                return response

    def confirm(self, message: str) -> bool:
        """确认"""
        while True:
            response = input(f"{message} [Y/n] ").strip().lower()
            if response in ["", "y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                print("请输入 Y 或 N")

    def step_project_info(self) -> Dict[str, str]:
        """步骤 1: 项目信息"""
        self.print_header("步骤 1/5: 项目信息")

        print("\n欢迎使用 LaTeX 模板配置向导！")
        print("本向导将帮助您配置一个新的 LaTeX 项目。")

        project_name = self.ask("项目名称", default="MyProject")
        display_name = self.ask("项目显示名称", default=project_name)
        description = self.ask("项目描述", default="")

        return {
            "project_name": project_name,
            "display_name": display_name,
            "description": description
        }

    def step_template_selection(self) -> str:
        """步骤 2: 模板选择"""
        self.print_header("步骤 2/5: 模板选择")

        print("\n请选择要使用的 LaTeX 模板:")

        templates = sorted(self.template_catalog.keys())

        if not templates:
            print("⚠️  未找到可用模板")
            return None

        template_info = {
            template: self.template_catalog.get(template, {}).get("template", {}).get("display_name", template)
            for template in templates
        }
        options = [template_info[t] for t in templates]
        selected_display = self.ask("选择模板", default=options[0], options=options)

        # 返回模板名称
        for template, display in template_info.items():
            if display == selected_display:
                return template

        return templates[0]

    def step_optimization_level(self) -> str:
        """步骤 3: 优化级别"""
        self.print_header("步骤 3/5: 优化级别")

        print("\n请选择优化级别:")
        print("  minimal  - 最小改动：仅修复明显错误")
        print("  moderate - 中等优化：调整不一致的样式（推荐）")
        print("  thorough  - 彻底重构：最大保真度")

        options = ["minimal", "moderate", "thorough"]
        level = self.ask("优化级别", default="moderate", options=options)

        return level

    def step_word_template(self) -> Optional[Path]:
        """步骤 4: Word 模板"""
        self.print_header("步骤 4/5: Word 模板")

        print("\n如果您有 Word 模板，请提供路径。")
        print("这将用于样式对比和标题提取。")

        has_template = self.confirm("是否提供 Word 模板？")

        if not has_template:
            return None

        word_path = self.ask("Word 模板路径（支持拖拽文件）")

        # 处理 macOS 拖拽路径
        if word_path.startswith("'") and word_path.endswith("'"):
            word_path = word_path[1:-1]

        word_file = Path(word_path)

        if not word_file.exists():
            print(f"⚠️  文件不存在: {word_file}")
            return None

        return word_file

    def step_advanced_options(self) -> Dict[str, Any]:
        """步骤 5: 高级选项"""
        self.print_header("步骤 5/5: 高级选项")

        print("\n高级选项（可选）")

        options = {}

        enable_pixel_compare = self.confirm("启用像素对比（需要 Word PDF 基准）？")
        if enable_pixel_compare:
            options["pixel_comparison"] = True

        custom_fonts = self.confirm("使用自定义字体？")
        if custom_fonts:
            font_path = self.ask("字体文件路径")
            options["custom_fonts"] = font_path

        return options

    def generate_config(self, project_info: Dict[str, str], template: str,
                       optimization_level: str, word_template: Optional[Path],
                       advanced_options: Dict[str, Any]) -> Dict[str, Any]:
        """生成配置文件"""
        config = {
            "project": {
                "name": project_info["project_name"],
                "display_name": project_info["display_name"],
                "description": project_info["description"],
                "template": template,
                "optimization_level": optimization_level,
            },
            "validation": {
                "enabled_validators": [],
                "tolerance": {
                    "font_size_diff": 0.5,
                    "color_diff": 2,
                    "spacing_diff": 0.05,
                    "margin_diff": 0.5,
                }
            }
        }

        if word_template:
            config["project"]["word_template"] = str(word_template)

        config.update(advanced_options)

        return config

    def create_project_structure(self, project_name: str, config: Dict[str, Any]) -> Path:
        """创建项目结构"""
        project_path = self.projects_dir / project_name

        if project_path.exists():
            print(f"⚠️  项目目录已存在: {project_path}")
            overwrite = self.confirm("是否继续？")
            if not overwrite:
                return None

        # 创建目录结构
        (project_path / "extraTex").mkdir(parents=True, exist_ok=True)
        (project_path / "template").mkdir(parents=True, exist_ok=True)
        (project_path / ".make_latex_model" / "baselines").mkdir(parents=True, exist_ok=True)

        # 创建 .template.yaml
        import yaml
        with open(project_path / ".template.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        print(f"\n✅ 项目已创建: {project_path}")

        return project_path

    def print_summary(self, project_path: Path, config: Dict[str, Any]):
        """打印配置摘要"""
        self.print_header("配置完成")

        print("\n项目配置:")
        print(f"  名称: {config['project']['name']}")
        print(f"  模板: {config['project']['template']}")
        print(f"  优化级别: {config['project']['optimization_level']}")

        print(f"\n项目路径: {project_path}")
        print("\n下一步:")
        print("  1. 将 baseline PDF 或 Word 模板放入 template/ 目录")
        print("  2. 先运行对应产品线的官方构建脚本确认入口可用")
        print("  3. 再按需使用 make-latex-model 的辅助脚本补充分析")


def main():
    parser = argparse.ArgumentParser(description="LaTeX 项目配置向导")
    parser.add_argument("--template", type=str, help="使用预设模板")
    parser.add_argument("--import", type=Path, dest="import_config", help="导入历史配置")

    args = parser.parse_args()

    # 确定基础目录
    base_dir = Path(__file__).parent.parent.parent.parent

    wizard = SetupWizard(base_dir)

    # 如果导入配置
    if args.import_config:
        print(f"正在导入配置: {args.import_config}")
        # TODO: 实现配置导入
        return

    # 运行向导
    project_info = wizard.step_project_info()
    template = args.template or wizard.step_template_selection()
    optimization_level = wizard.step_optimization_level()
    word_template = wizard.step_word_template()
    advanced_options = wizard.step_advanced_options()

    # 生成配置
    config = wizard.generate_config(
        project_info, template, optimization_level, word_template, advanced_options
    )

    # 创建项目
    project_path = wizard.create_project_structure(project_info["project_name"], config)

    if project_path:
        wizard.print_summary(project_path, config)

        # 保存配置记录
        config_file = project_path / ".template.yaml"
        print(f"\n📝 配置已保存: {config_file}")


if __name__ == "__main__":
    main()
