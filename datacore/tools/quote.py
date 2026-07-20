"""DataCoreQuoteTool - 实时行情数据工具。"""

from __future__ import annotations

from typing import Any, Optional

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreQuoteTool(DataCoreBaseTool):
    """获取实时行情报价数据。

    支持期货、股票、ETF 等品种的实时行情，
    包含最新价、涨跌额、涨跌幅、成交量、成交额等。
    """

    name = "datacore_quote"
    description = (
        "获取实时行情报价数据。支持期货、股票、ETF 等品种。"
        "参数：symbol (str, 必需) - 品种代码，如 'RB'、'000001'；"
        "fields (list, 可选) - 指定返回字段，默认返回全部字段"
    )

    def _run(self, symbol: str, fields: Optional[list[str]] = None,
             **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {}
        if fields:
            params["fields"] = fields

        payload = provider.get(symbol, DataType.QUOTE, params=params)
        return _payload_to_dict(payload)
