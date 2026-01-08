#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置工具测试
"""

import pytest

from core.config_utils import (
    ConfigAccessor,
    ConfigDefaults,
    ThresholdDefaults,
    apply_profile,
    get_config_accessor,
)


class TestConfigAccessor:
    """配置访问器测试"""

    def test_init(self):
        """测试初始化"""
        accessor = ConfigAccessor()
        assert accessor.raw == {}

        accessor = ConfigAccessor({"key": "value"})
        assert accessor.raw == {"key": "value"}

    def test_get_simple(self):
        """测试获取简单值"""
        config = {"key": "value", "number": 42}
        accessor = ConfigAccessor(config)

        assert accessor.get("key") == "value"
        assert accessor.get("number") == 42
        assert accessor.get("missing", "default") == "default"

    def test_get_nested(self):
        """测试获取嵌套值"""
        config = {"level1": {"level2": {"level3": "deep"}}}
        accessor = ConfigAccessor(config)

        assert accessor.get("level1.level2.level3") == "deep"
        assert accessor.get("level1.level2.missing", "default") == "default"

    def test_get_typed(self):
        """测试类型化获取"""
        config = {"bool": True, "int": 42, "float": 3.14, "str": "hello"}
        accessor = ConfigAccessor(config)

        assert accessor.get_bool("bool") is True
        assert accessor.get_int("int") == 42
        assert accessor.get_float("float") == 3.14
        assert accessor.get_str("str") == "hello"

    def test_get_list(self):
        """测试获取列表"""
        config = {"list": [1, 2, 3], "tuple": (4, 5, 6)}
        accessor = ConfigAccessor(config)

        assert accessor.get_list("list") == [1, 2, 3]
        assert accessor.get_list("tuple") == [4, 5, 6]
        assert accessor.get_list("missing") == []

    def test_get_dict(self):
        """测试获取字典"""
        config = {"dict": {"nested": "value"}}
        accessor = ConfigAccessor(config)

        assert accessor.get_dict("dict") == {"nested": "value"}
        assert accessor.get_dict("missing") == {}

    def test_sub(self):
        """测试子配置"""
        config = {"level1": {"level2": {"value": "deep"}}}
        accessor = ConfigAccessor(config)

        sub = accessor.sub("level1")
        assert isinstance(sub, ConfigAccessor)
        assert sub.get("level2.value") == "deep"

    def test_has(self):
        """测试检查键是否存在"""
        config = {"existing": "value", "nested": {"key": "value"}}
        accessor = ConfigAccessor(config)

        assert accessor.has("existing") is True
        assert accessor.has("missing") is False
        assert accessor.has("nested.key") is True
        assert accessor.has("nested.missing") is False

    def test_type_conversion(self):
        """测试类型转换"""
        config = {"number_str": "42", "bool_str": "true"}
        accessor = ConfigAccessor(config)

        # 应该自动转换类型
        assert accessor.get_int("number_str") == 42
        assert accessor.get("number_str", 0, int) == 42


class TestApplyProfile:
    """应用预设测试"""

    def test_apply_profile_quick(self):
        """测试应用 quick 预设"""
        config = {
            "ai": {"batch_mode": True, "max_workers": 8},
            "profiles": {
                "quick": {
                    "ai": {"batch_mode": False, "max_workers": 2},
                }
            },
        }

        result = apply_profile(config, "quick")

        assert result["ai"]["batch_mode"] is False
        assert result["ai"]["max_workers"] == 2

    def test_apply_profile_missing(self):
        """测试应用不存在的预设"""
        config = {"ai": {"batch_mode": True}}
        result = apply_profile(config, "nonexistent")

        # 应该返回原配置
        assert result == config

    def test_apply_profile_none(self):
        """测试不应用预设"""
        config = {"ai": {"batch_mode": True}}
        result = apply_profile(config, None)

        assert result == config

    def test_deep_merge(self):
        """测试深度合并"""
        config = {
            "ai": {
                "batch_mode": True,
                "max_workers": 8,
                "temperature": 0.5,
            },
            "profiles": {
                "test": {
                    "ai": {"max_workers": 2},
                }
            },
        }

        result = apply_profile(config, "test")

        # 应该保留其他设置
        assert result["ai"]["batch_mode"] is True
        assert result["ai"]["temperature"] == 0.5
        # 只覆盖预设中的值
        assert result["ai"]["max_workers"] == 2


class TestGetConfigAccessor:
    """获取配置访问器测试"""

    def test_get_config_accessor_no_profile(self):
        """测试不使用预设"""
        config = {"key": "value"}
        accessor = get_config_accessor(config)

        assert accessor.get("key") == "value"

    def test_get_config_accessor_with_profile(self):
        """测试使用预设"""
        config = {
            "ai": {"max_workers": 8},
            "profiles": {
                "test": {"ai": {"max_workers": 2}},
            },
        }

        accessor = get_config_accessor(config, profile="test")

        assert accessor.get_int("ai.max_workers") == 2


class TestConfigDefaults:
    """配置默认值测试"""

    def test_ai_defaults(self):
        """测试 AI 默认值"""
        assert ConfigDefaults.AI_BATCH_SIZE == 10
        assert ConfigDefaults.AI_MAX_WORKERS == 4
        assert ConfigDefaults.AI_TEMPERATURE == 0.3

    def test_cache_defaults(self):
        """测试缓存默认值"""
        assert ConfigDefaults.CACHE_TTL_DAYS == 30
        assert ConfigDefaults.CACHE_MEMORY_MAX_SIZE == 1000

    def test_reference_defaults(self):
        """测试引用验证默认值"""
        assert ConfigDefaults.REFERENCE_INTACT_RATE_MIN == 0.95

    def test_word_count_defaults(self):
        """测试字数默认值"""
        assert ConfigDefaults.WORD_COUNT_TOLERANCE == 50
        assert ConfigDefaults.WORD_COUNT_DEFAULT_TARGET == 3000


class TestThresholdDefaults:
    """阈值默认值测试"""

    def test_mapping_thresholds(self):
        """测试映射阈值"""
        assert ThresholdDefaults.MAPPING_HIGH == 0.85
        assert ThresholdDefaults.MAPPING_MEDIUM == 0.7
        assert ThresholdDefaults.MAPPING_LOW == 0.5

    def test_quality_thresholds(self):
        """测试质量阈值"""
        assert ThresholdDefaults.MIN_SIMILARITY == 0.7
        assert ThresholdDefaults.MIN_WORD_COUNT == 50
        assert ThresholdDefaults.CONTENT_INTEGRITY == 0.95

    def test_compile_thresholds(self):
        """测试编译阈值"""
        assert ThresholdDefaults.MAX_COMPILE_WARNINGS == 10
        assert ThresholdDefaults.MAX_COMPILE_ERRORS == 0
        assert ThresholdDefaults.MAX_REF_ERRORS == 5
