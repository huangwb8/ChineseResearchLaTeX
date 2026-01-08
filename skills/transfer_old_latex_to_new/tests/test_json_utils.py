#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSON 解析工具测试
"""

import pytest

from core.json_utils import JsonParser, parse_json, parse_json_array, parse_batch_json


class TestParseJsonResponse:
    """解析 JSON 对象测试"""

    def test_parse_simple_json(self):
        """测试解析简单 JSON"""
        text = '{"key": "value", "number": 42}'
        result = JsonParser.parse_json_response(text)

        assert result is not None
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_parse_fenced_json(self):
        """测试解析 fenced code block 中的 JSON"""
        text = '''```json
{
    "should_map": true,
    "score": 0.85
}
```'''
        result = JsonParser.parse_json_response(text)

        assert result is not None
        assert result["should_map"] is True
        assert result["score"] == 0.85

    def test_parse_fenced_without_language(self):
        """测试解析无语言标记的 code block"""
        text = '''```
{
    "key": "value"
}
```'''
        result = JsonParser.parse_json_response(text)

        assert result is not None
        assert result["key"] == "value"

    def test_parse_json_with_extra_text(self):
        """测试解析包含额外文本的 JSON"""
        text = '''这是一些说明文本

```json
{"key": "value"}
```

更多文本'''
        result = JsonParser.parse_json_response(text)

        assert result is not None
        assert result["key"] == "value"

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        text = '{"key": invalid}'
        result = JsonParser.parse_json_response(text)

        assert result is None

    def test_parse_empty_input(self):
        """测试解析空输入"""
        assert JsonParser.parse_json_response("") is None
        assert JsonParser.parse_json_response(None) is None


class TestParseJsonArray:
    """解析 JSON 数组测试"""

    def test_parse_simple_array(self):
        """测试解析简单数组"""
        text = '[1, 2, 3, 4, 5]'
        result = JsonParser.parse_json_array(text)

        assert result is not None
        assert result == [1, 2, 3, 4, 5]

    def test_parse_object_array(self):
        """测试解析对象数组"""
        text = '''[
    {"key": "value1"},
    {"key": "value2"}
]'''
        result = JsonParser.parse_json_array(text)

        assert result is not None
        assert len(result) == 2
        assert result[0]["key"] == "value1"
        assert result[1]["key"] == "value2"

    def test_parse_fenced_array(self):
        """测试解析 fenced code block 中的数组"""
        text = '''```json
[
    {"should_map": true, "score": 0.8},
    {"should_map": false, "score": 0.3}
]
```'''
        result = JsonParser.parse_json_array(text)

        assert result is not None
        assert len(result) == 2
        assert result[0]["should_map"] is True

    def test_parse_object_instead_of_array(self):
        """测试解析对象而不是数组"""
        text = '{"key": "value"}'
        result = JsonParser.parse_json_array(text)

        # 应该返回 None（不是数组）
        assert result is None


class TestParseBatchJsonResponse:
    """解析批量 JSON 响应测试"""

    def test_parse_batch_array(self):
        """测试解析批量数组"""
        text = '''[
    {"task": "task1", "result": 0.8},
    {"task": "task2", "result": 0.9}
]'''
        results = JsonParser.parse_batch_json_response(text)

        assert len(results) == 2
        assert results[0]["task"] == "task1"
        assert results[1]["task"] == "task2"

    def test_parse_batch_multiple_objects(self):
        """测试解析多个独立的 JSON 对象"""
        text = '''{"task": "task1", "result": 0.8}
{"task": "task2", "result": 0.9}'''
        results = JsonParser.parse_batch_json_response(text)

        assert len(results) == 2

    def test_parse_batch_empty(self):
        """测试解析空批量响应"""
        results = JsonParser.parse_batch_json_response("")
        assert results == []

    def test_parse_batch_invalid(self):
        """测试解析无效批量响应"""
        results = JsonParser.parse_batch_json_response("not json at all")
        assert results == []


class TestExtractFieldFromText:
    """从文本中提取字段测试"""

    def test_extract_field_colon(self):
        """测试提取字段（冒号分隔）"""
        text = "score: 0.85"
        result = JsonParser.extract_field_from_text(text, "score")

        assert result == 0.85

    def test_extract_field_chinese_colon(self):
        """测试提取字段（中文冒号）"""
        text = "得分：0.85"
        result = JsonParser.extract_field_from_text(text, "得分")

        assert result == 0.85

    def test_extract_field_equals(self):
        """测试提取字段（等号）"""
        text = "score=0.85"
        result = JsonParser.extract_field_from_text(text, "score")

        assert result == 0.85

    def test_extract_field_boolean(self):
        """测试提取布尔字段"""
        text = "should_map: yes"
        result = JsonParser.extract_field_from_text(text, "should_map")

        assert result is True

    def test_extract_field_missing(self):
        """测试提取缺失字段"""
        text = "some other text"
        result = JsonParser.extract_field_from_text(text, "missing")

        assert result is None


class TestSafeLoads:
    """安全加载测试"""

    def test_safe_loads_valid(self):
        """测试安全加载有效 JSON"""
        result = JsonParser.safe_loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_safe_loads_invalid(self):
        """测试安全加载无效 JSON"""
        result = JsonParser.safe_loads('invalid json', default={"default": True})
        assert result == {"default": True}

    def test_safe_loads_none(self):
        """测试安全加载 None"""
        result = JsonParser.safe_loads(None, default=[])
        assert result == []


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_parse_json_function(self):
        """测试 parse_json 便捷函数"""
        result = parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_array_function(self):
        """测试 parse_json_array 便捷函数"""
        result = parse_json_array('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_parse_batch_json_function(self):
        """测试 parse_batch_json 便捷函数"""
        result = parse_batch_json('[{"a": 1}, {"b": 2}]')
        assert len(result) == 2
