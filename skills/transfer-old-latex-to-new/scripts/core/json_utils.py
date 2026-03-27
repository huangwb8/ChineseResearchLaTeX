#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一的 JSON 解析工具
- 支持多种响应格式
- 提取 JSON 块
- 解析批量结果
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union


class JsonParser:
    """
    统一的 JSON 解析器

    支持从 AI 响应中提取 JSON，无论格式如何
    """

    @staticmethod
    def parse_json_response(response_text: str) -> Optional[Dict[str, Any]]:
        """
        从 AI 响应中解析 JSON 对象

        支持格式：
        1. fenced code block: ```json ... ```
        2. 无语言标记的代码块: ``` ... ```
        3. 直接的 JSON 对象: { ... }

        Args:
            response_text: AI 响应文本

        Returns:
            解析后的字典，失败返回 None
        """
        if not response_text or not isinstance(response_text, str):
            return None

        response_text = response_text.strip()

        # 1) 提取 fenced code block 中的 JSON
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                json_str = response_text[start:end].strip()
                try:
                    obj = json.loads(json_str)
                    return obj if isinstance(obj, dict) else None
                except (json.JSONDecodeError, ValueError):
                    pass

        # 2) 提取无语言标记的代码块
        if "```" in response_text:
            start = response_text.find("```") + 3
            # 找到换行符（跳过语言标识）
            newline = response_text.find("\n", start)
            if newline != -1:
                start = newline + 1
                end = response_text.find("```", start)
                if end != -1:
                    json_str = response_text[start:end].strip()
                    try:
                        obj = json.loads(json_str)
                        return obj if isinstance(obj, dict) else None
                    except (json.JSONDecodeError, ValueError):
                        pass

        # 3) 直接解析整个响应
        try:
            obj = json.loads(response_text)
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, ValueError):
            pass

        # 4) 尝试找到第一个完整的 JSON 对象
        start = response_text.find("{")
        if start == -1:
            return None

        depth = 0
        for i in range(start, len(response_text)):
            ch = response_text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    json_str = response_text[start:i + 1]
                    try:
                        obj = json.loads(json_str)
                        return obj if isinstance(obj, dict) else None
                    except (json.JSONDecodeError, ValueError):
                        pass

        return None

    @staticmethod
    def parse_json_array(response_text: str) -> Optional[List[Any]]:
        """
        从 AI 响应中解析 JSON 数组

        Args:
            response_text: AI 响应文本

        Returns:
            解析后的列表，失败返回 None
        """
        if not response_text or not isinstance(response_text, str):
            return None

        response_text = response_text.strip()

        # 1) 提取 fenced code block 中的 JSON
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                json_str = response_text[start:end].strip()
                try:
                    obj = json.loads(json_str)
                    return obj if isinstance(obj, list) else None
                except (json.JSONDecodeError, ValueError):
                    pass

        # 2) 提取无语言标记的代码块
        if "```" in response_text:
            start = response_text.find("```") + 3
            newline = response_text.find("\n", start)
            if newline != -1:
                start = newline + 1
                end = response_text.find("```", start)
                if end != -1:
                    json_str = response_text[start:end].strip()
                    try:
                        obj = json.loads(json_str)
                        return obj if isinstance(obj, list) else None
                    except (json.JSONDecodeError, ValueError):
                        pass

        # 3) 直接解析整个响应
        try:
            obj = json.loads(response_text)
            return obj if isinstance(obj, list) else None
        except (json.JSONDecodeError, ValueError):
            pass

        # 4) 尝试找到第一个完整的 JSON 数组
        start = response_text.find("[")
        if start == -1:
            return None

        depth = 0
        for i in range(start, len(response_text)):
            ch = response_text[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    json_str = response_text[start:i + 1]
                    try:
                        obj = json.loads(json_str)
                        return obj if isinstance(obj, list) else None
                    except (json.JSONDecodeError, ValueError):
                        pass

        return None

    @staticmethod
    def parse_batch_json_response(response_text: str) -> List[Any]:
        """
        解析批量 JSON 响应

        尝试多种方式从响应中提取多个 JSON 对象

        Args:
            response_text: AI 响应文本

        Returns:
            解析后的对象列表
        """
        if not response_text or not isinstance(response_text, str):
            return []

        # 首先尝试解析为 JSON 数组
        array_result = JsonParser.parse_json_array(response_text)
        if array_result is not None:
            return array_result

        # 尝试解析为多个 JSON 对象（按行分割）
        results = []
        lines = response_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # 尝试解析为 JSON 对象
            obj = JsonParser.parse_json_response(line)
            if obj is not None:
                results.append(obj)
                continue

            # 尝试按 { 分割
            for match in line.split("{"):
                if not match.strip():
                    continue
                try:
                    obj_str = "{" + match.split("}")[0] + "}"
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict):
                        results.append(obj)
                except (json.JSONDecodeError, ValueError, IndexError):
                    continue

        return results if len(results) > 1 else []

    @staticmethod
    def extract_field_from_text(text: str, field: str) -> Optional[Any]:
        """
        从非结构化文本中提取字段值

        例如：从 "score: 0.85" 中提取 0.85

        Args:
            text: 文本内容
            field: 字段名

        Returns:
            字段值，未找到返回 None
        """
        if not text or not field:
            return None

        # 尝试多种模式
        patterns = [
            f'{field}\\s*[:：]\\s*([^\\s,;\\n]+)',  # field: value 或 field：value
            f'{field}\\s*=\\s*([^\\s,;\\n]+)',      # field=value
            f'["\']?{field}["\']?\\s*[:=]\\s*["\']?([^"\';\\n]+)["\']?',  # JSON风格
        ]

        import re
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip(' "\'')
                # 尝试转换为合适的类型
                try:
                    # 尝试转换为数字
                    if "." in value:
                        return float(value)
                    return int(value)
                except ValueError:
                    pass

                # 尝试转换为布尔值
                if value.lower() in ("true", "yes", "是"):
                    return True
                if value.lower() in ("false", "no", "否"):
                    return False

                return value

        return None

    @staticmethod
    def safe_loads(json_str: str, default: Any = None) -> Any:
        """
        安全的 JSON 加载

        Args:
            json_str: JSON 字符串
            default: 解析失败时的默认值

        Returns:
            解析后的对象或默认值
        """
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError, TypeError):
            return default


# 便捷函数
def parse_json(response_text: str) -> Optional[Dict[str, Any]]:
    """解析 JSON 对象（便捷函数）"""
    return JsonParser.parse_json_response(response_text)


def parse_json_array(response_text: str) -> Optional[List[Any]]:
    """解析 JSON 数组（便捷函数）"""
    return JsonParser.parse_json_array(response_text)


def parse_batch_json(response_text: str) -> List[Any]:
    """解析批量 JSON 响应（便捷函数）"""
    return JsonParser.parse_batch_json_response(response_text)
