"""PostgreSQL 持久化存储后端。

可选依赖：psycopg2-binary
配置方式：环境变量 DATACORE_STORE_POSTGRESQL_DSN 或 YAML 文件
"""

from __future__ import annotations

import os
import pickle
import time
from typing import Any, Optional

from datacore.config import get_config


def _pg_available() -> bool:
    try:
        __import__("psycopg2")
        return True
    except ImportError:
        return False


class PostgresStore:
    """PostgreSQL 持久化存储引擎。"""

    def __init__(self, dsn: Optional[str] = None):
        if not _pg_available():
            raise ImportError("psycopg2 not installed: pip install psycopg2-binary")
        import psycopg2
        self._dsn = dsn or get_config().pg_dsn
        if not self._dsn:
            raise ValueError("PostgreSQL DSN not configured")
        self._conn: Optional[Any] = None
        self._ensure_tables()

    @property
    def conn(self):
        if self._conn is None:
            import psycopg2
            self._conn = psycopg2.connect(self._dsn)
            self._conn.autocommit = True
        return self._conn

    def _ensure_tables(self):
        schemas = [
            """CREATE TABLE IF NOT EXISTS kline_cache (
                symbol VARCHAR NOT NULL, period VARCHAR NOT NULL,
                date VARCHAR NOT NULL, open DOUBLE PRECISION, high DOUBLE PRECISION,
                low DOUBLE PRECISION, close DOUBLE PRECISION, volume DOUBLE PRECISION,
                amount DOUBLE PRECISION,
                PRIMARY KEY (symbol, period, date)
            )""",
            """CREATE TABLE IF NOT EXISTS quote_cache (
                symbol VARCHAR NOT NULL, collected_at TIMESTAMP NOT NULL,
                last_price DOUBLE PRECISION, volume DOUBLE PRECISION, amount DOUBLE PRECISION
            )""",
            """CREATE TABLE IF NOT EXISTS macro_cache (
                indicator VARCHAR NOT NULL, date VARCHAR NOT NULL,
                value DOUBLE PRECISION, PRIMARY KEY (indicator, date)
            )""",
            """CREATE TABLE IF NOT EXISTS datacore_cache (
                key TEXT PRIMARY KEY, value BYTEA, expires BIGINT
            )""",
        ]
        for sql in schemas:
            with self.conn.cursor() as cur:
                cur.execute(sql)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def cache_get(self, key: str) -> Optional[Any]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT value, expires FROM datacore_cache WHERE key = %s", (key,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        value, expires = row
        if expires < time.time():
            self.cache_invalidate(key)
            return None
        return pickle.loads(value)

    def cache_set(self, key: str, value: Any, ttl_seconds: float) -> None:
        expires = int(time.time() + ttl_seconds)
        blob = pickle.dumps(value)
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO datacore_cache (key, value, expires) VALUES (%s, %s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "
                "expires = EXCLUDED.expires",
                (key, blob, expires),
            )

    def cache_invalidate(self, key: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM datacore_cache WHERE key = %s", (key,))

    def cache_purge(self) -> int:
        now = int(time.time())
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM datacore_cache WHERE expires < %s", (now,))
            count = cur.fetchone()[0]
            cur.execute("DELETE FROM datacore_cache WHERE expires < %s", (now,))
        return int(count)


def build_postgres_store() -> Optional[PostgresStore]:
    """构造 PostgreSQL 存储后端；不可用返回 None。"""
    if not _pg_available():
        return None
    dsn = get_config().pg_dsn
    if not dsn:
        return None
    try:
        return PostgresStore(dsn)
    except Exception:
        return None
