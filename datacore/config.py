"""Data-Core 统一配置系统。

配置加载优先级（从高到低）:
    1. 环境变量 (DATACORE_* 前缀)
    2. config/settings.yaml
    3. 代码默认值

所有敏感信息（如数据库密码）必须通过环境变量注入，禁止硬编码。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class DataCoreConfig:
    """Data-Core 配置对象。"""

    def __init__(self):
        self._yaml_config = self._load_yaml()
        self._env_config = self._load_env()

    def _load_yaml(self) -> dict:
        if not HAS_YAML:
            return {}
        config_paths = [
            Path.cwd() / "config" / "settings.yaml",
            Path.home() / ".datacore" / "settings.yaml",
        ]
        for path in config_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    continue
        return {}

    def _load_env(self) -> dict:
        prefix = "DATACORE_"
        env = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                env[key[len(prefix):].lower()] = value
        return env

    def _get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        env_key = key.upper().replace(".", "_")
        if env_key in self._env_config:
            return self._env_config[env_key]
        keys = key.split(".")
        value = self._yaml_config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                value = None
                break
        if value is not None:
            return str(value)
        return default

    @property
    def tdx_url(self) -> str:
        return self._get("sources.tdx_lc.url", "http://127.0.0.1:17709/")

    @property
    def tdx_timeout(self) -> int:
        return int(self._get("sources.tdx_lc.timeout", "3"))

    @property
    def cache_ttl(self) -> int:
        return int(self._get("store.cache_ttl", "3600"))

    @property
    def duckdb_path(self) -> str:
        path = self._get("store.duckdb_path", "~/.datacore/datacore.db")
        return os.path.expanduser(path)

    @property
    def pg_dsn(self) -> Optional[str]:
        return self._get("store.postgresql.dsn")

    @property
    def redis_url(self) -> Optional[str]:
        return self._get("store.redis.url")

    @property
    def store_backend(self) -> str:
        return self._get("store.backend", "duckdb")

    @property
    def guosen_api_key(self) -> Optional[str]:
        return self._get("sources.guosen.api_key")

    @property
    def guosen_url(self) -> str:
        return self._get("sources.guosen.url", "https://api.guosen.com.cn/")

    @property
    def guosen_timeout(self) -> int:
        return int(self._get("sources.guosen.timeout", "5"))

    def __repr__(self) -> str:
        return f"DataCoreConfig(backend={self.store_backend})"


_config_instance: Optional[DataCoreConfig] = None


def get_config() -> DataCoreConfig:
    """获取全局配置实例（单例）。"""
    global _config_instance
    if _config_instance is None:
        _config_instance = DataCoreConfig()
    return _config_instance
