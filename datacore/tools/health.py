"""DataCoreHealthTool - 数据源健康检查工具。"""

from __future__ import annotations

from typing import Any, Optional

from .base import DataCoreBaseTool


class DataCoreHealthTool(DataCoreBaseTool):
    """检查数据源健康状态。

    检查所有或指定数据源的可用性和延迟。
    """

    name = "datacore_health"
    description = (
        "检查数据源健康状态。返回各数据源的可用性和延迟。"
        "参数：source (str, 可选) - 指定数据源名称，不传则检查所有；"
        "detail (bool, 可选) - 是否返回详细信息，默认 True"
    )

    def _run(self, source: Optional[str] = None, detail: bool = True,
             **kwargs: Any) -> dict[str, Any]:
        from ..health import HealthChecker

        hc = HealthChecker()
        self._register_default_sources(hc)

        if source:
            result = hc.check(source)
            return {
                "success": True,
                "source": source,
                "result": result,
                "detail": detail,
            }
        else:
            results = hc.check_all()
            return {
                "success": True,
                "total": len(results),
                "available_count": sum(
                    1 for r in results.values() if r.get("available")
                ),
                "results": results,
            }

    def _register_default_sources(self, hc: Any) -> None:
        """注册默认的健康检查项。"""
        def _check_memory() -> bool:
            return True

        def _check_config() -> bool:
            from ..config import DataCoreConfig
            try:
                cfg = DataCoreConfig()
                return cfg is not None
            except Exception:
                return False

        hc.register("memory", _check_memory)
        hc.register("config", _check_config)
