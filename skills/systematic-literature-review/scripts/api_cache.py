#!/usr/bin/env python3
"""
api_cache.py - API 调用缓存机制

P0-4: API 调用缓存 - 减少重复请求，提高效率，避免速率限制

功能：
  - 自动缓存 API 请求结果（基于 URL + 参数的哈希）
  - 支持缓存过期时间（TTL）
  - 磁盘持久化缓存
  - 缓存命中率统计

使用示例：
    from scripts.api_cache import cached_api, CacheStats

    # 方式1：使用装饰器
    @cached_api(ttl=86400)  # 缓存24小时
    def call_semantic_scholar(url, params=None):
        return requests.get(url, params=params).json()

    # 方式2：使用上下文管理器
    with APICache(ttl=3600) as cache:
        result1 = cache.get_or_call(url1, params1)
        result2 = cache.get_or_call(url2, params2)

    # 查看缓存统计
    print(CacheStats.get_summary())
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 缓存配置
# ============================================================================

def _get_default_cache_dir() -> Optional[Path]:
    """
    获取默认缓存目录。

    优先使用环境变量 SYSTEMATIC_LITERATURE_REVIEW_CACHE_DIR。
    如果未设置，返回 None 并在运行时禁用缓存（避免使用相对路径导致跨 run 污染）。
    """
    env_cache_dir = os.environ.get("SYSTEMATIC_LITERATURE_REVIEW_CACHE_DIR")
    if env_cache_dir:
        return Path(env_cache_dir)
    # 如果环境变量未设置，返回 None（禁用缓存）
    return None


DEFAULT_CACHE_DIR = _get_default_cache_dir()
DEFAULT_TTL = 86400  # 24小时（秒）
CACHE_VERSION = 'v1'  # 缓存格式版本


# ============================================================================
# 缓存统计
# ============================================================================

class CacheStats:
    """缓存命中率统计"""

    _hits = 0
    _misses = 0
    _errors = 0

    @classmethod
    def record_hit(cls):
        """记录缓存命中"""
        cls._hits += 1

    @classmethod
    def record_miss(cls):
        """记录缓存未命中"""
        cls._misses += 1

    @classmethod
    def record_error(cls):
        """记录缓存错误"""
        cls._errors += 1

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """获取统计摘要"""
        total = cls._hits + cls._misses
        hit_rate = cls._hits / total * 100 if total > 0 else 0

        return {
            'hits': cls._hits,
            'misses': cls._misses,
            'errors': cls._errors,
            'total_requests': total,
            'hit_rate': f'{hit_rate:.1f}%'
        }

    @classmethod
    def reset(cls):
        """重置统计"""
        cls._hits = 0
        cls._misses = 0
        cls._errors = 0

    @classmethod
    def log_summary(cls):
        """记录统计摘要到日志"""
        summary = cls.get_summary()
        logger.info(
            f"缓存统计: 命中={summary['hits']}, "
            f"未命中={summary['misses']}, "
            f"错误={summary['errors']}, "
            f"命中率={summary['hit_rate']}"
        )


# ============================================================================
# 缓存存储
# ============================================================================

class CacheStorage:
    """缓存存储管理器"""

    def __init__(self, cache_dir: Optional[Path] = None, ttl: int = DEFAULT_TTL):
        """
        初始化缓存存储

        Args:
            cache_dir: 缓存目录路径，None 时尝试使用环境变量或禁用缓存
            ttl: 缓存过期时间（秒）
        """
        # 优先使用传入的 cache_dir，其次使用环境变量，最后禁用缓存
        if cache_dir is None:
            cache_dir = DEFAULT_CACHE_DIR
        if cache_dir is None:
            logger.warning(
                "SYSTEMATIC_LITERATURE_REVIEW_CACHE_DIR 未设置，缓存已禁用。"
                "设置该环境变量以启用 API 缓存（避免使用相对路径导致跨 run 污染）。"
            )
            self.enabled = False
            self.cache_dir = None
            self.ttl = ttl
            return

        self.enabled = True
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 创建元数据文件
        self.meta_file = self.cache_dir / 'cache_meta.json'
        self.meta = self._load_meta()

    def _load_meta(self) -> Dict[str, Any]:
        """加载缓存元数据"""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载缓存元数据失败: {e}")
        return {'version': CACHE_VERSION, 'entries': {}}

    def _save_meta(self):
        """保存缓存元数据"""
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)

    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_data = f"{url}{json.dumps(params, sort_keys=True) if params else ''}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cache_file(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """
        从缓存获取数据

        Args:
            url: 请求URL
            params: 请求参数

        Returns:
            缓存的数据，如果不存在或已过期则返回 None
        """
        if not self.enabled:
            CacheStats.record_miss()
            return None

        cache_key = self._get_cache_key(url, params)
        cache_file = self._get_cache_file(cache_key)

        if not cache_file.exists():
            CacheStats.record_miss()
            return None

        # 检查是否过期
        if cache_key in self.meta['entries']:
            cached_time = self.meta['entries'][cache_key].get('timestamp')
            if cached_time:
                cached_datetime = datetime.fromisoformat(cached_time)
                if datetime.now() - cached_datetime > timedelta(seconds=self.ttl):
                    logger.debug(f"缓存已过期: {cache_key[:8]}")
                    self.delete(cache_key)
                    CacheStats.record_miss()
                    return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            CacheStats.record_hit()
            logger.debug(f"✓ 缓存命中: {cache_key[:8]}")
            return data
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            CacheStats.record_error()
            return None

    def set(self, url: str, params: Optional[Dict], data: Any):
        """
        保存数据到缓存

        Args:
            url: 请求URL
            params: 请求参数
            data: 要缓存的数据
        """
        if not self.enabled:
            return

        cache_key = self._get_cache_key(url, params)
        cache_file = self._get_cache_file(cache_key)

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 更新元数据
            self.meta['entries'][cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'url': url[:100],  # 只保留前100个字符
                'params': bool(params)
            }
            self._save_meta()

            logger.debug(f"✓ 缓存已保存: {cache_key[:8]}")
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
            CacheStats.record_error()

    def delete(self, cache_key: str):
        """删除缓存条目"""
        cache_file = self._get_cache_file(cache_key)
        if cache_file.exists():
            cache_file.unlink()

        if cache_key in self.meta['entries']:
            del self.meta['entries'][cache_key]
            self._save_meta()

    def clear(self):
        """清空所有缓存"""
        for cache_file in self.cache_dir.glob('*.json'):
            if cache_file != self.meta_file:
                cache_file.unlink()

        self.meta['entries'] = {}
        self._save_meta()
        logger.info("✓ 缓存已清空")

    def cleanup_expired(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = []

        for cache_key, entry in self.meta['entries'].items():
            cached_time = entry.get('timestamp')
            if cached_time:
                cached_datetime = datetime.fromisoformat(cached_time)
                if now - cached_datetime > timedelta(seconds=self.ttl):
                    expired_keys.append(cache_key)

        for key in expired_keys:
            self.delete(key)

        if expired_keys:
            logger.info(f"✓ 清理了 {len(expired_keys)} 个过期缓存")


# ============================================================================
# 装饰器和上下文管理器
# ============================================================================

def cached_api(ttl: int = DEFAULT_TTL, cache_dir: Path = DEFAULT_CACHE_DIR):
    """
    API 缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        cache_dir: 缓存目录路径

    使用示例:
        @cached_api(ttl=3600)
        def fetch_data(url, params=None):
            return requests.get(url, params=params).json()
    """
    storage = CacheStorage(cache_dir=cache_dir, ttl=ttl)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从函数参数中提取 URL 和 params
            url = args[0] if args else kwargs.get('url', '')
            params = kwargs.get('params')

            # 尝试从缓存获取
            cached_data = storage.get(url, params)
            if cached_data is not None:
                return cached_data

            # 调用原函数
            result = func(*args, **kwargs)

            # 保存到缓存
            storage.set(url, params, result)

            return result

        return wrapper

    return decorator


class APICache:
    """
    API 缓存上下文管理器

    使用示例:
        with APICache(ttl=3600) as cache:
            result1 = cache.get_or_call(url1, params1, fetch_func)
            result2 = cache.get_or_call(url2, params2, fetch_func)
    """

    def __init__(self, ttl: int = DEFAULT_TTL, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.storage = CacheStorage(cache_dir=cache_dir, ttl=ttl)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 退出时记录统计信息
        CacheStats.log_summary()

    def get_or_call(self, url: str, params: Optional[Dict],
                    fetch_func: Callable, *args, **kwargs) -> Any:
        """
        从缓存获取或调用API

        Args:
            url: 请求URL
            params: 请求参数
            fetch_func: API获取函数
            *args, **kwargs: 传递给fetch_func的额外参数

        Returns:
            API响应数据
        """
        cached_data = self.storage.get(url, params)
        if cached_data is not None:
            return cached_data

        # 调用API
        result = fetch_func(url, params, *args, **kwargs)

        # 保存到缓存
        self.storage.set(url, params, result)

        return result

    def clear(self):
        """清空缓存"""
        self.storage.clear()

    def cleanup_expired(self):
        """清理过期缓存"""
        self.storage.cleanup_expired()


# ============================================================================
# 便捷函数：直接缓存的requests调用
# ============================================================================

def cached_get(url: str, params: Optional[Dict] = None,
               ttl: int = DEFAULT_TTL,
               cache_dir: Path = DEFAULT_CACHE_DIR,
               **kwargs) -> Any:
    """
    带缓存的 GET 请求

    Args:
        url: 请求URL
        params: 请求参数
        ttl: 缓存过期时间
        cache_dir: 缓存目录
        **kwargs: 传递给requests.get的额外参数

    Returns:
        响应JSON数据
    """
    import requests

    storage = CacheStorage(cache_dir=cache_dir, ttl=ttl)

    # 尝试从缓存获取
    cached_data = storage.get(url, params)
    if cached_data is not None:
        return cached_data

    # 发起请求
    response = requests.get(url, params=params, **kwargs)
    response.raise_for_status()
    result = response.json()

    # 保存到缓存
    storage.set(url, params, result)

    return result


# ============================================================================
# 命令行接口（用于缓存管理）
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='API缓存管理工具')
    parser.add_argument('--clear', action='store_true', help='清空缓存')
    parser.add_argument('--cleanup', action='store_true', help='清理过期缓存')
    parser.add_argument('--stats', action='store_true', help='显示缓存统计')
    parser.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE_DIR,
                       help='缓存目录路径')

    args = parser.parse_args()

    storage = CacheStorage(cache_dir=args.cache_dir)

    if args.clear:
        storage.clear()
        print("✓ 缓存已清空")

    if args.cleanup:
        storage.cleanup_expired()

    if args.stats:
        # 显示缓存统计
        total_entries = len(storage.meta.get('entries', {}))
        print(f"缓存目录: {args.cache_dir}")
        print(f"缓存条目: {total_entries}")
        print(f"缓存统计: {CacheStats.get_summary()}")

        # 显示最近的缓存条目
        if total_entries > 0:
            print("\n最近缓存条目:")
            entries = list(storage.meta.get('entries', {}).items())
            entries.sort(key=lambda x: x[1].get('timestamp', ''), reverse=True)
            for key, entry in entries[:10]:
                print(f"  {key[:8]}: {entry.get('url', 'N/A')[:60]}")
