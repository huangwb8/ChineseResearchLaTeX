#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置工具模块
- 统一类型检查
- 简化配置访问
- 支持默认值
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")


class ConfigAccessor:
    """
    配置访问器

    提供类型安全的配置访问方法，避免重复的 isinstance 检查
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化配置访问器

        Args:
            config: 配置字典（None 则返回默认值）
        """
        self._config = config if isinstance(config, dict) else {}

    def get(self, key: str, default: T = None, expected_type: Optional[type] = None) -> Union[T, Any]:
        """
        获取配置值

        Args:
            key: 配置键（支持点号分隔的嵌套键，如 "ai.batch_mode"）
            default: 默认值
            expected_type: 期望的类型（None 表示不检查）

        Returns:
            配置值或默认值
        """
        # 支持嵌套键（如 "ai.batch_mode"）
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        # 检查类型
        if value is None:
            return default
        if expected_type is not None and not isinstance(value, expected_type):
            try:
                # 尝试类型转换
                return expected_type(value)
            except (ValueError, TypeError):
                return default

        return value

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔值"""
        return bool(self.get(key, default, bool))

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数值"""
        return int(self.get(key, default, int))

    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数值"""
        return float(self.get(key, default, (int, float)))

    def get_str(self, key: str, default: str = "") -> str:
        """获取字符串值"""
        return str(self.get(key, default, str))

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """获取列表值"""
        if default is None:
            default = []
        value = self.get(key, default)
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return default

    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取字典值"""
        if default is None:
            default = {}
        value = self.get(key, default)
        if isinstance(value, dict):
            return value
        return default

    def sub(self, key: str) -> "ConfigAccessor":
        """
        获取子配置的访问器

        Args:
            key: 子配置键

        Returns:
            新的 ConfigAccessor 实例
        """
        return ConfigAccessor(self.get_dict(key))

    def has(self, key: str) -> bool:
        """
        检查配置键是否存在

        Args:
            key: 配置键

        Returns:
            是否存在
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                if k not in value:
                    return False
                value = value[k]
            else:
                return False

        return True

    @property
    def raw(self) -> Dict[str, Any]:
        """获取原始配置字典"""
        return self._config.copy()


def apply_profile(config: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
    """
    应用配置预设（profile）

    Args:
        config: 原始配置
        profile_name: 预设名称（quick/balanced/thorough）

    Returns:
        应用预设后的配置
    """
    profiles = config.get("profiles", {})
    profile = profiles.get(profile_name, {})

    if not profile:
        return config

    # 深度合并配置
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    return deep_merge(config, profile)


def get_config_accessor(config: Optional[Dict[str, Any]] = None, profile: Optional[str] = None) -> ConfigAccessor:
    """
    获取配置访问器

    Args:
        config: 配置字典
        profile: 可选的预设名称

    Returns:
        ConfigAccessor 实例
    """
    if profile and config:
        config = apply_profile(config, profile)

    return ConfigAccessor(config)


# 常量定义（消除魔法数字）
class ConfigDefaults:
    """配置默认值常量"""

    # AI 调用
    AI_BATCH_SIZE = 10
    AI_MAX_WORKERS = 4
    AI_TEMPERATURE = 0.3

    # 缓存
    CACHE_TTL_DAYS = 30
    CACHE_MEMORY_MAX_SIZE = 1000

    # 引用验证
    REFERENCE_INTACT_RATE_MIN = 0.95

    # 内容优化
    CONTENT_MIN_IMPROVEMENT = 0.1
    CONTENT_MIN_WORD_COUNT = 500

    # 编译
    COMPILE_TIMEOUT_PER_PASS = 120
    COMPILE_TOTAL_TIMEOUT = 600

    # 字数适配
    WORD_COUNT_TOLERANCE = 50
    WORD_COUNT_DEFAULT_TARGET = 3000

    # LaTeX 命令检测（内容长度限制）
    LATEX_CONTENT_PREVIEW_LENGTH = 500
    LATEX_AI_PROMPT_LENGTH = 1500
    LATEX_AI_MAX_LENGTH = 2000


class ThresholdDefaults:
    """阈值默认值"""

    # 映射置信度阈值
    MAPPING_HIGH = 0.85
    MAPPING_MEDIUM = 0.7
    MAPPING_LOW = 0.5

    # 质量阈值
    MIN_SIMILARITY = 0.7
    MIN_WORD_COUNT = 50
    CONTENT_INTEGRITY = 0.95
    LOGICAL_COHERENCE = 0.8

    # 编译阈值
    MAX_COMPILE_WARNINGS = 10
    MAX_COMPILE_ERRORS = 0
    MAX_REF_ERRORS = 5
    MAX_UNDEFINED_REFS = 3
