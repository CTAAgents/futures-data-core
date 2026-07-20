"""DataCoreFundamentalTool - 基本面数据工具。"""

from __future__ import annotations

from typing import Any

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreFundamentalTool(DataCoreBaseTool):
    """获取基本面数据。

    支持财务报表、财务指标、盈利预测等基本面数据。
    """

    name = "datacore_fundamental"
    description = (
        "获取基本面数据。支持财务报表、财务指标等。"
        "参数：symbol (str, 必需) - 品种代码；"
        "report_type (str, 可选) - 报表类型，'income'/'balance'/'cashflow'/'indicator'，默认 'indicator'；"
        "period (str, 可选) - 报告期，'annual'/'quarterly'，默认 'quarterly'；"
        "limit (int, 可选) - 返回期数，默认 10"
    )

    def _run(self, symbol: str, report_type: str = "indicator",
             period: str = "quarterly", limit: int = 10,
             **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {
            "report_type": report_type,
            "period": period,
            "limit": limit,
        }

        payload = provider.get(symbol, DataType.FUNDAMENTAL, params=params)
        return _payload_to_dict(payload)
