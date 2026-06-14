#!/usr/bin/env python3
"""
Make Research Plan - 验证脚本

验证 JSON 文件格式和内容。
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict


# JSON Schema 定义
SCHEMAS = {
    "theme": {
        "type": "object",
        "required": ["primary_topic"],
        "properties": {
            "primary_topic": {
                "type": "object",
                "required": ["name", "keywords"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "keywords": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"}
                    }
                }
            },
            "secondary_topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "keywords"],
                    "properties": {
                        "name": {"type": "string"},
                        "keywords": {"type": "array", "minItems": 1}
                    }
                }
            },
            "extracted_at": {"type": "string"}
        }
    },
    "search_history": {
        "type": "object",
        "required": ["searches"],
        "properties": {
            "searches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["topic", "query", "source", "timestamp"],
                    "properties": {
                        "topic": {"type": "string"},
                        "query": {"type": "string"},
                        "source": {"type": "string"},
                        "results_count": {"type": "integer"},
                        "timestamp": {"type": "string"}
                    }
                }
            }
        }
    },
    "papers_scored": {
        "type": "object",
        "required": ["papers"],
        "properties": {
            "papers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title", "relevance_score"],
                    "properties": {
                        "title": {"type": "string"},
                        "authors": {"type": "array", "items": {"type": "string"}},
                        "year": {"type": "integer"},
                        "journal": {"type": "string"},
                        "relevance_score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "subtopic": {"type": "string"},
                        "doi": {"type": "string"},
                        "url": {"type": "string"}
                    }
                }
            }
        }
    }
}


def validate_json(data: Dict[str, Any], schema_name: str) -> tuple:
    """
    验证 JSON 数据是否符合 schema。

    Args:
        data: JSON 数据
        schema_name: Schema 名称

    Returns:
        (is_valid, errors) 元组
    """
    if schema_name not in SCHEMAS:
        return False, [f"未知的 schema: {schema_name}"]

    schema = SCHEMAS[schema_name]
    errors = []

    def validate(value, expected, path=""):
        nonlocal errors

        # 类型检查
        if "type" in expected:
            if expected["type"] == "object":
                if not isinstance(value, dict):
                    errors.append(f"{path or 'root'}: 期望对象，得到 {type(value).__name__}")
                    return
            elif expected["type"] == "array":
                if not isinstance(value, list):
                    errors.append(f"{path or 'root'}: 期望数组，得到 {type(value).__name__}")
                    return
            elif expected["type"] == "string":
                if not isinstance(value, str):
                    errors.append(f"{path}: 期望字符串，得到 {type(value).__name__}")
                    return
            elif expected["type"] == "integer":
                if not isinstance(value, int):
                    errors.append(f"{path}: 期望整数，得到 {type(value).__name__}")
                    return

        # 必需字段检查
        if isinstance(value, dict) and "required" in expected:
            for field in expected["required"]:
                if field not in value:
                    errors.append(f"{path or 'root'}: 缺少必需字段 '{field}'")

        # 属性验证
        if isinstance(value, dict) and "properties" in expected:
            for prop, prop_schema in expected["properties"].items():
                if prop in value:
                    validate(value[prop], prop_schema, f"{path}.{prop}" if path else prop)

        # 数组项验证
        if isinstance(value, list) and "items" in expected:
            for i, item in enumerate(value):
                validate(item, expected["items"], f"{path}[{i}]")

        # 最小项数检查
        if isinstance(value, list) and "minItems" in expected:
            if len(value) < expected["minItems"]:
                errors.append(f"{path}: 数组项数 {len(value)} 少于最小要求 {expected['minItems']}")

        # 数值范围检查
        if isinstance(value, (int, float)) and "minimum" in expected:
            if value < expected["minimum"]:
                errors.append(f"{path}: 值 {value} 小于最小值 {expected['minimum']}")
        if isinstance(value, (int, float)) and "maximum" in expected:
            if value > expected["maximum"]:
                errors.append(f"{path}: 值 {value} 大于最大值 {expected['maximum']}")

    validate(data, schema)

    return len(errors) == 0, errors


def validate_file(file_path: str, schema_name: str) -> tuple:
    """
    验证 JSON 文件。

    Args:
        file_path: 文件路径
        schema_name: Schema 名称

    Returns:
        (is_valid, errors) 元组
    """
    path = Path(file_path)

    if not path.exists():
        return False, [f"文件不存在: {file_path}"]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"JSON 解析错误: {e}"]
    except Exception as e:
        return False, [f"读取错误: {e}"]

    return validate_json(data, schema_name)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: validate.py <文件路径> <schema名称>", file=sys.stderr)
        print(f"可用的 schema: {', '.join(SCHEMAS.keys())}", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    schema_name = sys.argv[2]

    is_valid, errors = validate_file(file_path, schema_name)

    if is_valid:
        print(f"✓ {file_path} 验证通过")
        sys.exit(0)
    else:
        print(f"✗ {file_path} 验证失败:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
