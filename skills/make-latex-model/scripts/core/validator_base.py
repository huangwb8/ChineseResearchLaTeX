#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证器基类 - 验证插件抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ValidationContext:
    """验证上下文"""
    project_path: Path
    template_config: Dict[str, Any]
    tolerance: Dict[str, Any]
    verbose: bool = False


@dataclass
class ValidationResult:
    """验证结果"""
    passed: List[str]
    warnings: List[str]
    failed: List[str]

    def __post_init__(self):
        if self.passed is None:
            self.passed = []
        if self.warnings is None:
            self.warnings = []
        if self.failed is None:
            self.failed = []

    def is_success(self) -> bool:
        """是否验证成功"""
        return len(self.failed) == 0

    def add_pass(self, message: str):
        """添加通过项"""
        self.passed.append(message)

    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)

    def add_fail(self, message: str):
        """添加失败项"""
        self.failed.append(message)

    def summary(self) -> str:
        """生成摘要"""
        lines = [
            f"✅ Passed: {len(self.passed)}",
            f"⚠️  Warnings: {len(self.warnings)}",
            f"❌ Failed: {len(self.failed)}",
        ]
        return "\n".join(lines)


class ValidatorBase(ABC):
    """验证器基类"""

    @abstractmethod
    def get_name(self) -> str:
        """返回验证器名称"""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """返回优先级（1=最高）"""
        pass

    @abstractmethod
    def validate(self, context: ValidationContext):
        """
        执行验证

        Args:
            context: 验证上下文

        Returns:
            ValidationResult
        """
        pass

    def is_enabled(self, config: Dict[str, Any]) -> bool:
        """
        检查验证器是否启用

        Args:
            config: 模板配置

        Returns:
            是否启用
        """
        enabled_validators = config.get("validation", {}).get("enabled_validators", [])
        return self.get_name() in enabled_validators or len(enabled_validators) == 0


class ValidatorRegistry:
    """验证器注册表"""

    _validators: Dict[str, type] = {}

    @classmethod
    def register(cls, validator_class: type):
        """注册验证器"""
        cls._validators[validator_class.__name__] = validator_class
        return validator_class

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """获取验证器类"""
        return cls._validators.get(name)

    @classmethod
    def load_all(cls, context: ValidationContext):
        """
        加载所有启用的验证器

        Args:
            context: 验证上下文

        Returns:
            验证器实例列表（按优先级排序）
        """
        validators = []
        for validator_class in cls._validators.values():
            instance = validator_class()
            if instance.is_enabled(context.template_config):
                validators.append(instance)

        # 按优先级排序
        validators.sort(key=lambda v: v.get_priority())
        return validators


if __name__ == "__main__":
    # 测试代码
    class ExampleValidator(ValidatorBase):
        def get_name(self) -> str:
            return "example"

        def get_priority(self) -> int:
            return 1

        def validate(self, context: ValidationContext):
            result = ValidationResult(passed=[], warnings=[], failed=[])
            result.add_pass("Example validation passed")
            return result

    # 注册验证器
    ValidatorRegistry.register(ExampleValidator)

    # 测试加载
    from pathlib import Path
    test_context = ValidationContext(
        project_path=Path("."),
        template_config={},
        tolerance={}
    )

    validators = ValidatorRegistry.load_all(test_context)
    print(f"Loaded {len(validators)} validator(s)")
    for v in validators:
        print(f"  - {v.get_name()} (priority: {v.get_priority()})")
