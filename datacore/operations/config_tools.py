"""动态配置加载 — 环境变量读取、YAML 加载。"""

from __future__ import annotations

import os
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def get_env_var(
    key: str,
    default: Any = None,
    prefix: str = "DATACORE_",
) -> Any:
    """从环境变量读取配置。

    Args:
        key: 配置键名。
        default: 默认值。
        prefix: 环境变量前缀，默认 'DATACORE_'。

    Returns:
        环境变量值，不存在则返回默认值。

    Examples:
        >>> import os
        >>> os.environ["DATACORE_TEST_KEY"] = "test_value"
        >>> get_env_var("TEST_KEY")
        'test_value'
        >>> get_env_var("NONEXISTENT", "default")
        'default'
    """
    full_key = f"{prefix}{key}" if prefix else key
    value = os.environ.get(full_key, default)
    return value


def load_yaml_config(file_path: str) -> dict[str, Any]:
    """加载 YAML 配置文件。

    Args:
        file_path: YAML 文件路径。

    Returns:
        配置字典，文件不存在或解析失败返回空字典。

    Examples:
        >>> import tempfile, os
        >>> with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        ...     _ = f.write("key: value\\nnum: 123")
        ...     path = f.name
        >>> config = load_yaml_config(path)
        >>> config["key"]
        'value'
        >>> os.unlink(path)
    """
    if not os.path.exists(file_path):
        return {}

    if not HAS_YAML:
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _convert_value(value: str) -> Any:
    """尝试将字符串值转换为合适的类型。"""
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def load_config(
    yaml_path: str = "",
    env_prefix: str = "DATACORE_",
) -> dict[str, Any]:
    """加载配置（YAML + 环境变量覆盖）。

    优先级：环境变量 > YAML 配置 > 默认值。

    Args:
        yaml_path: YAML 配置文件路径。
        env_prefix: 环境变量前缀。

    Returns:
        合并后的配置字典。

    Examples:
        >>> import os
        >>> os.environ["DATACORE_APP_NAME"] = "test_app"
        >>> config = load_config()
        >>> "app_name" in config or "APP_NAME" in config
        True
    """
    config: dict[str, Any] = {}

    if yaml_path:
        yaml_config = load_yaml_config(yaml_path)
        config.update(yaml_config)

    for key, value in os.environ.items():
        if env_prefix and key.startswith(env_prefix):
            config_key = key[len(env_prefix):].lower()
            config[config_key] = _convert_value(value)

    return config


class ConfigLoader:
    """配置加载器。

    支持从 YAML 文件、环境变量加载配置，并提供便捷的访问方法。
    """

    def __init__(
        self,
        yaml_path: str = "",
        env_prefix: str = "DATACORE_",
        auto_reload: bool = False,
    ) -> None:
        """初始化配置加载器。

        Args:
            yaml_path: YAML 配置文件路径。
            env_prefix: 环境变量前缀。
            auto_reload: 是否自动重载（文件变化时）。
        """
        self.yaml_path = yaml_path
        self.env_prefix = env_prefix
        self.auto_reload = auto_reload
        self._config: dict[str, Any] = {}
        self._last_mtime: float = 0.0
        self.reload()

    def reload(self) -> None:
        """重新加载配置。"""
        self._config = load_config(
            yaml_path=self.yaml_path,
            env_prefix=self.env_prefix,
        )
        if self.yaml_path and os.path.exists(self.yaml_path):
            self._last_mtime = os.path.getmtime(self.yaml_path)

    def _check_reload(self) -> None:
        """检查是否需要自动重载。"""
        if not self.auto_reload or not self.yaml_path:
            return
        if not os.path.exists(self.yaml_path):
            return
        mtime = os.path.getmtime(self.yaml_path)
        if mtime > self._last_mtime:
            self.reload()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。

        支持点号分隔的嵌套键，如 'database.host'。

        Args:
            key: 配置键。
            default: 默认值。

        Returns:
            配置值。
        """
        self._check_reload()

        keys = key.split(".")
        value: Any = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值（内存中）。

        Args:
            key: 配置键。
            value: 配置值。
        """
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def to_dict(self) -> dict[str, Any]:
        """返回完整配置字典。"""
        self._check_reload()
        return dict(self._config)

    def __getitem__(self, key: str) -> Any:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None
