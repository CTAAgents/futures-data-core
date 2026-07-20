"""ConfigReadTool - 配置读取工具。"""

from __future__ import annotations

from typing import Any

from ..base import DataCoreBaseTool


class ConfigReadTool(DataCoreBaseTool):
    """读取 Data-Core 配置。

    支持读取配置文件和环境变量中的配置项。
    """

    name = "datacore_config_read"
    description = (
        "读取 Data-Core 配置。支持读取配置文件和环境变量。"
        "参数：key (str, 可选) - 配置键，不传则返回所有配置；"
        "default (any, 可选) - 默认值，键不存在时返回；"
        "section (str, 可选) - 配置段，如 'sources.tdx_lc'"
    )

    def _run(self, key: str = "", default: Any = None,
             section: str = "", **kwargs: Any) -> dict[str, Any]:
        try:
            from ...config import DataCoreConfig

            config = DataCoreConfig()

            if key:
                full_key = f"{section}.{key}" if section else key
                value = config._get(full_key, default)
                return {
                    "success": True,
                    "key": full_key,
                    "value": value,
                    "exists": value is not None,
                }
            else:
                yaml_config = config._yaml_config
                env_config = config._env_config
                return {
                    "success": True,
                    "yaml_config": yaml_config,
                    "env_config": env_config,
                    "has_yaml": bool(yaml_config),
                    "has_env": bool(env_config),
                }
        except Exception as e:
            return {
                "success": False,
                "key": key,
                "error": str(e),
                "error_type": type(e).__name__,
            }
