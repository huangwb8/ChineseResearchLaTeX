#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分层缓存管理器
- L1: 内存缓存（当前会话）
- L2: SQLite 磁盘缓存（跨会话）
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional


class CacheManager:
    """分层缓存管理器"""

    # 缓存键最大长度（SQLite 限制）
    MAX_KEY_LENGTH = 256

    def __init__(self, cache_dir: str = "cache", db_name: str = "mapping_cache.db", ttl_days: int = 30):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录（相对 runs/<run_id>/）
            db_name: 数据库文件名
            ttl_days: 缓存过期天数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / db_name
        self.ttl_seconds = ttl_days * 86400

        # L1: 内存缓存（当前会话）
        self.memory_cache: Dict[str, Any] = {}

        # L2: SQLite 磁盘缓存（跨会话）
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS mapping_cache (
                cache_key TEXT PRIMARY KEY,
                result TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON mapping_cache(timestamp)
        """)
        self.conn.commit()

    def _make_key(self, old_file: str, new_file: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        生成缓存键

        使用 SHA256 哈希确保键的唯一性和固定长度
        """
        # 组合输入
        combined = f"{old_file}|{new_file}"
        if context:
            context_str = json.dumps(context, sort_keys=True)
            combined += f"|{context_str}"

        # SHA256 哈希
        hash_obj = hashlib.sha256(combined.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()

        # 截取前 32 字符（足够唯一且不过长）
        return f"cache_{hash_hex[:32]}"

    def get(self, old_file: str, new_file: str, context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        获取缓存（L1 → L2 → None）

        Args:
            old_file: 旧文件路径
            new_file: 新文件路径
            context: 可选上下文信息

        Returns:
            缓存结果，如果不存在则返回 None
        """
        cache_key = self._make_key(old_file, new_file, context)

        # L1: 内存缓存
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # L2: SQLite 缓存
        cursor = self.conn.execute(
            "SELECT result, timestamp FROM mapping_cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cursor.fetchone()

        if row:
            result_json, timestamp = row

            # 检查是否过期
            if time.time() - timestamp < self.ttl_seconds:
                try:
                    result = json.loads(result_json)
                    # 提升到 L1
                    self.memory_cache[cache_key] = result
                    return result
                except (json.JSONDecodeError, ValueError):
                    # 缓存损坏，删除
                    self.conn.execute("DELETE FROM mapping_cache WHERE cache_key = ?", (cache_key,))
                    self.conn.commit()

        return None

    def set(self, old_file: str, new_file: str, result: Any, context: Optional[Dict[str, Any]] = None) -> None:
        """
        设置缓存（同时写入 L1 和 L2）

        Args:
            old_file: 旧文件路径
            new_file: 新文件路径
            result: 要缓存的结果
            context: 可选上下文信息
        """
        cache_key = self._make_key(old_file, new_file, context)
        current_time = time.time()

        # 写入 L1
        self.memory_cache[cache_key] = result

        # 写入 L2
        try:
            result_json = json.dumps(result, ensure_ascii=False)
            self.conn.execute(
                "INSERT OR REPLACE INTO mapping_cache (cache_key, result, timestamp) VALUES (?, ?, ?)",
                (cache_key, result_json, current_time)
            )
            self.conn.commit()
        except (json.JSONDecodeError, ValueError, TypeError):
            # 结果无法序列化，只缓存到 L1（内存）
            pass

    def clear_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的条目数
        """
        current_time = time.time()
        cursor = self.conn.execute(
            "DELETE FROM mapping_cache WHERE ? - timestamp > ?",
            (current_time, self.ttl_seconds)
        )
        self.conn.commit()
        return cursor.rowcount

    def clear_all(self) -> int:
        """
        清理所有缓存

        Returns:
            清理的条目数
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM mapping_cache")
        count = cursor.fetchone()[0]

        self.conn.execute("DELETE FROM mapping_cache")
        self.conn.commit()

        # 清空 L1
        self.memory_cache.clear()

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        # L1 统计
        l1_count = len(self.memory_cache)

        # L2 统计
        cursor = self.conn.execute("SELECT COUNT(*) FROM mapping_cache")
        l2_count = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM mapping_cache WHERE ? - timestamp > ?",
                                   (time.time(), self.ttl_seconds))
        expired_count = cursor.fetchone()[0]

        return {
            "l1_count": l1_count,
            "l2_count": l2_count,
            "expired_count": expired_count,
            "ttl_days": self.ttl_seconds / 86400,
        }

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def __del__(self) -> None:
        """析构函数，确保连接关闭"""
        try:
            self.close()
        except Exception:
            pass
