"""内存缓存 (TTL) — 零依赖，热数据加速。"""

from __future__ import annotations

import time
import pickle
from typing import Any, Optional

from datacore.config import get_config


class MemoryCache:
    """进程内字典缓存，TTL 过期自动失效。"""

    def __init__(self, default_ttl: Optional[float] = None):
        self._store: dict[str, tuple[bytes, float]] = {}
        self.default_ttl = default_ttl or get_config().cache_ttl

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires = item
        if expires < time.time():
            del self._store[key]
            return None
        return pickle.loads(value)

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        expires = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._store[key] = (pickle.dumps(value), expires)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def purge(self) -> int:
        now = time.time()
        expired = [k for k, (_, e) in self._store.items() if e < now]
        for k in expired:
            del self._store[k]
        return len(expired)

    def clear(self) -> None:
        self._store.clear()
