"""DataCoreF10Tool - F10 综合报告工具。"""

from __future__ import annotations

from typing import Any

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreF10Tool(DataCoreBaseTool):
    """获取 F10 综合报告。

    聚合期现结构、价差、基差、仓单、持仓排名、基本面等多个数据模块，
    生成综合 F10 报告。
    """

    name = "datacore_f10"
    description = (
        "获取 F10 综合报告。聚合期现结构、价差、基差、仓单、持仓排名、基本面等多个模块。"
        "参数：symbol (str, 必需) - 品种代码；"
        "modules (list, 可选) - 指定包含的模块，默认全部，可选: term_structure, spread, basis, warehouse_receipt, position_rank, fundamental"
    )

    def _run(self, symbol: str, modules: list[str] | None = None,
             **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..api_f10 import get_f10_sync

        provider = UnifiedDataProvider()
        payload = get_f10_sync(provider, symbol)

        result = _payload_to_dict(payload)

        if modules and isinstance(result.get("data"), dict):
            result["data"] = {
                k: v for k, v in result["data"].items() if k in modules
            }

        return result
