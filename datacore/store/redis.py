"""Redis 缓存存储后端。

可选依赖：redis
配置方式：环境变量 DATACORE_STORE_REDIS_URL 或 YAML 文件

Redis 作为热缓存层，支持跨进程共享和 TTL 自动过期。
"""

from __future__ import annotations

import os
import pickle
from typing import Any, Optional

from datacore.config import get_config


def _redis_available() -> bool:
    try:
        __import__("redis")
        return True
    except ImportError:
        return False


class RedisStore:
    """Redis 缓存存储引擎。"""

    def __init__(self, url: Optional[str] = None):
        if not _redis_available():
            raise ImportError("redis not installed: pip install redis")
        import redis
        self._url = url or get_config().redis_url
        if not self._url:
            raise ValueError("Redis URL not configured")
        self._r = redis.from_url(self._url, decode_responses=False)
        self._r.ping()

    def cache_get(self, key: str) -> Optional[Any]:
        raw = self._r.get(key)
        if raw is None:
            return None
        return pickle.loads(raw)

    def cache_set(self, key: str, value: Any, ttl_seconds: float) -> None:
        self._r.set(key, pickle.dumps(value), ex=int(ttl_seconds))

    def cache_invalidate(self, key: str) -> None:
        self._r.delete(key)
        try:
            self._r.publish("datacore_cache_invalidate", key)
        except Exception:
            pass

    def cache_purge(self) -> int:
        return 0

    def close(self):
        pass


def build_redis_store() -> Optional[RedisStore]:
    """构造 Redis 存储后端；不可用返回 None。"""
    if not _redis_available():
        return None
    url = get_config().redis_url
    if not url:
        return None
    try:
        return RedisStore(url)
    except Exception:
        return None
