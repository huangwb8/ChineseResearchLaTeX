#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 分层配置加载与合并

支持三层配置合并（优先级从低到高）:
1. 技能默认配置 (skills/make_latex_model/config.yaml)
2. 模板基础配置 (templates/{template}/{template}.yaml)
3. 项目本地配置 (projects/{project}/.template.yaml)
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import copy


class ConfigLoader:
    """分层配置加载器"""

    def __init__(self, skill_dir: Path, project_path: Optional[Path] = None, template_name: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            skill_dir: 技能目录 (如 skills/make_latex_model)
            project_path: 项目路径 (如 projects/NSFC_Young)
            template_name: 模板名称 (如 nsfc/young)，如未指定则自动检测
        """
        self.skill_dir = Path(skill_dir)
        self.project_path = Path(project_path) if project_path else None
        self.template_name = template_name

        # 配置文件路径
        self.default_config_path = self.skill_dir / "config.yaml"
        self.templates_dir = self.skill_dir / "templates"

    def load(self) -> Dict[str, Any]:
        """
        加载合并后的配置

        Returns:
            合并后的配置字典
        """
        # 加载三层配置
        default_config = self._load_default_config()
        template_config = self._load_template_config()
        local_config = self._load_local_config()

        # 合并配置（优先级：local > template > default）
        merged = self._merge_configs([default_config, template_config, local_config])

        return merged

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """加载 YAML 文件"""
        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load {path}: {e}")
            return {}

    def _load_default_config(self) -> Dict[str, Any]:
        """加载技能默认配置"""
        return self._load_yaml(self.default_config_path)

    def _load_template_config(self) -> Dict[str, Any]:
        """加载模板配置"""
        if not self.template_name:
            # 尝试自动检测模板
            self.template_name = self._detect_template()

        if not self.template_name:
            return {}

        # 支持两种格式: "nsfc/young" 或 "nsfc.young"
        template_path = self.template_name.replace(".", "/")
        config_path = self.templates_dir / f"{template_path}.yaml"

        if not config_path.exists():
            print(f"Warning: Template config not found: {config_path}")
            return {}

        config = self._load_yaml(config_path)

        # 处理配置继承
        if "template" in config and "inherits" in config["template"]:
            parent_template = config["template"]["inherits"]
            parent_config = self._load_inherited_template(parent_template)
            # 子配置覆盖父配置
            return self._merge_configs([parent_config, config])

        return config

    def _load_inherited_template(self, parent_template: str) -> Dict[str, Any]:
        """加载继承的父模板配置"""
        parent_path = parent_template.replace(".", "/")
        config_path = self.templates_dir / f"{parent_path}.yaml"

        if not config_path.exists():
            print(f"Warning: Parent template config not found: {config_path}")
            return {}

        return self._load_yaml(config_path)

    def _load_local_config(self) -> Dict[str, Any]:
        """加载项目本地配置"""
        if not self.project_path:
            return {}

        config_path = self.project_path / ".template.yaml"
        return self._load_yaml(config_path)

    def _merge_configs(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个配置字典（后面的覆盖前面的）

        Args:
            configs: 配置字典列表

        Returns:
            合并后的配置
        """
        result = {}

        for config in configs:
            if not config:
                continue
            result = self._deep_merge(result, config)

        return result

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典

        Args:
            base: 基础字典
            override: 覆盖字典

        Returns:
            合并后的字典
        """
        result = copy.deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = self._deep_merge(result[key], value)
            else:
                # 直接覆盖
                result[key] = copy.deepcopy(value)

        return result

    def _detect_template(self) -> Optional[str]:
        """
        自动检测项目使用的模板类型

        检测方法（按优先级）:
        1. 检查项目目录下的 .template.yaml
        2. 根据 main.tex 的标题结构推断
        3. 根据目录结构推断

        Returns:
            检测到的模板名称（如 "nsfc/young"）
        """
        if not self.project_path:
            return None

        # 方法1: 检查 .template.yaml
        local_config_path = self.project_path / ".template.yaml"
        if local_config_path.exists():
            config = self._load_yaml(local_config_path)
            if "template" in config and "name" in config["template"]:
                return config["template"]["name"]

        # 方法2: 根据项目目录名推断
        project_name = self.project_path.name
        if "NSFC_Young" in project_name or "nsfc_young" in project_name.lower():
            return "nsfc/young"
        elif "NSFC_General" in project_name or "nsfc_general" in project_name.lower():
            return "nsfc/general"
        elif "NSFC_Local" in project_name or "nsfc_local" in project_name.lower():
            return "nsfc/local"

        return None


def load_config(skill_dir: Path, project_path: Optional[Path] = None, template_name: Optional[str] = None) -> Dict[str, Any]:
    """
    便捷函数：加载配置

    Args:
        skill_dir: 技能目录
        project_path: 项目路径
        template_name: 模板名称

    Returns:
        合并后的配置
    """
    loader = ConfigLoader(skill_dir, project_path, template_name)
    return loader.load()


if __name__ == "__main__":
    # 测试代码
    import sys

    # scripts/core/config_loader.py -> parents[2] == skills/make_latex_model
    skill_dir = Path(__file__).resolve().parents[2]

    # 测试1: 仅加载默认配置
    print("=== Test 1: Default Config Only ===")
    config = load_config(skill_dir)
    print(f"Loaded config keys: {list(config.keys())}")

    # 测试2: 加载 NSFC_Young 项目配置
    print("\n=== Test 2: NSFC_Young Project ===")
    project_path = skill_dir.parent.parent / "projects" / "NSFC_Young"
    if project_path.exists():
        config = load_config(skill_dir, project_path)
        print(f"Template detected: {config.get('template', {}).get('name', 'Unknown')}")
        print(f"Style reference keys: {list(config.get('style_reference', {}).keys())}")
    else:
        print(f"Project path not found: {project_path}")
