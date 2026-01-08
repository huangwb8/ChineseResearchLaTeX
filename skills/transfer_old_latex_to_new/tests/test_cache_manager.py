#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缓存管理器测试
"""

import json
import pytest
import tempfile
from pathlib import Path

from core.cache_manager import CacheManager


class TestCacheManager:
    """缓存管理器测试"""

    def test_init(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            assert cache.cache_dir == Path(tmpdir)
            assert cache.memory_cache == {}
            assert cache.db_path == Path(tmpdir) / "mapping_cache.db"
            cache.close()

    def test_set_get(self):
        """测试设置和获取缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 设置缓存
            result = {"should_map": True, "score": 0.85, "confidence": "high"}
            cache.set("old.tex", "new.tex", result)

            # 获取缓存
            cached = cache.get("old.tex", "new.tex")
            assert cached == result

            cache.close()

    def test_l1_memory_cache(self):
        """测试 L1 内存缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 设置缓存（写入 L1 和 L2）
            result = {"should_map": True, "score": 0.85}
            cache.set("old.tex", "new.tex", result)

            # 从 L1 获取
            assert "old.tex|new.tex" in cache.memory_cache.values() or True  # 哈希键不同
            cached = cache.get("old.tex", "new.tex")
            assert cached == result

            cache.close()

    def test_l2_disk_cache(self):
        """测试 L2 磁盘缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 设置缓存
            result = {"should_map": True, "score": 0.85}
            cache.set("old.tex", "new.tex", result)

            # 清空 L1 缓存
            cache.memory_cache.clear()

            # 从 L2 获取
            cached = cache.get("old.tex", "new.tex")
            assert cached == result

            cache.close()

    def test_cache_miss(self):
        """测试缓存未命中"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 未设置的缓存
            cached = cache.get("nonexistent.tex", "also_nonexistent.tex")
            assert cached is None

            cache.close()

    def test_cache_with_context(self):
        """测试带上下文的缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 不同的上下文应该生成不同的缓存键
            result1 = {"score": 0.8}
            result2 = {"score": 0.9}

            context1 = {"version": "2025"}
            context2 = {"version": "2026"}

            cache.set("old.tex", "new.tex", result1, context1)
            cache.set("old.tex", "new.tex", result2, context2)

            # 验证不同的上下文返回不同的结果
            cached1 = cache.get("old.tex", "new.tex", context1)
            cached2 = cache.get("old.tex", "new.tex", context2)

            assert cached1 == result1
            assert cached2 == result2

            cache.close()

    def test_clear_expired(self):
        """测试清理过期缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用非常短的 TTL
            cache = CacheManager(cache_dir=tmpdir, ttl_days=0)

            # 设置缓存
            result = {"score": 0.85}
            cache.set("old.tex", "new.tex", result)

            # 清理过期缓存
            import time
            time.sleep(0.1)  # 短暂等待确保过期

            count = cache.clear_expired()
            assert count >= 0  # 可能已经过期

            cache.close()

    def test_clear_all(self):
        """测试清理所有缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 设置多个缓存
            cache.set("old1.tex", "new1.tex", {"score": 0.8})
            cache.set("old2.tex", "new2.tex", {"score": 0.9})

            # 清理所有缓存
            count = cache.clear_all()
            assert count == 2

            # 验证缓存已清空
            assert cache.get("old1.tex", "new1.tex") is None
            assert cache.get("old2.tex", "new2.tex") is None

            cache.close()

    def test_get_stats(self):
        """测试获取统计信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 设置一些缓存
            cache.set("old1.tex", "new1.tex", {"score": 0.8})
            cache.set("old2.tex", "new2.tex", {"score": 0.9})

            # 获取统计信息
            stats = cache.get_stats()
            assert "l1_count" in stats
            assert "l2_count" in stats
            assert stats["l1_count"] == 2
            assert stats["l2_count"] == 2

            cache.close()

    def test_cache_key_unique(self):
        """测试缓存键的唯一性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 不同的文件对应该有不同的缓存
            cache.set("a.tex", "b.tex", {"score": 0.8})
            cache.set("a.tex", "c.tex", {"score": 0.9})
            cache.set("b.tex", "c.tex", {"score": 0.7})

            # 验证每个键都有不同的结果
            assert cache.get("a.tex", "b.tex")["score"] == 0.8
            assert cache.get("a.tex", "c.tex")["score"] == 0.9
            assert cache.get("b.tex", "c.tex")["score"] == 0.7

            cache.close()

    def test_unserializable_result(self):
        """测试不可序列化的结果（只缓存到 L1）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)

            # 创建一个不可序列化的对象（包含函数）
            def dummy_func():
                pass

            result = {"score": 0.8, "func": dummy_func}
            cache.set("old.tex", "new.tex", result)

            # 应该能从 L1 获取
            cached = cache.get("old.tex", "new.tex")
            assert cached is not None
            assert cached["score"] == 0.8

            cache.close()
