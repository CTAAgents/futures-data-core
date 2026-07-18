"""DuckDB 持久化存储 — 冷数据持久化（默认后端）。"""

from __future__ import annotations

import os
from typing import Optional

from datacore.config import get_config

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False


class DuckDBStore:
    """DuckDB 持久化存储引擎。"""

    def __init__(self, db_path: Optional[str] = None):
        if not HAS_DUCKDB:
            raise ImportError("duckdb not installed: pip install duckdb")
        self.db_path = db_path or get_config().duckdb_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
        return self._conn

    def init_schema(self):
        """建表（幂等）。"""
        schemas = [
            """CREATE TABLE IF NOT EXISTS kline_cache (
                symbol VARCHAR NOT NULL, period VARCHAR NOT NULL,
                date VARCHAR NOT NULL, open DOUBLE, high DOUBLE,
                low DOUBLE, close DOUBLE, volume DOUBLE, amount DOUBLE,
                PRIMARY KEY (symbol, period, date)
            )""",
            """CREATE TABLE IF NOT EXISTS quote_cache (
                symbol VARCHAR NOT NULL, collected_at TIMESTAMP NOT NULL,
                last_price DOUBLE, volume DOUBLE, amount DOUBLE
            )""",
            """CREATE TABLE IF NOT EXISTS macro_cache (
                indicator VARCHAR NOT NULL, date VARCHAR NOT NULL,
                value DOUBLE, PRIMARY KEY (indicator, date)
            )""",
        ]
        for sql in schemas:
            self.conn.execute(sql)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
