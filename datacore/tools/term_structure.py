"""DataCoreTermStructureTool - 期货期限结构工具。"""

from __future__ import annotations

from typing import Any

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreTermStructureTool(DataCoreBaseTool):
    """获取期货期限结构数据。

    返回同一品种不同到期月份合约的价格，形成期限结构曲线。
    """

    name = "datacore_term_structure"
    description = (
        "获取期货期限结构数据。返回同一品种不同到期月份合约的价格。"
        "参数：symbol (str, 必需) - 品种代码，如 'RB'、'CU'；"
        "price_type (str, 可选) - 价格类型，'close'/'settle'，默认 'close'；"
        "include_volume (bool, 可选) - 是否包含成交量，默认 True"
    )

    def _run(self, symbol: str, price_type: str = "close",
             include_volume: bool = True, **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {
            "price_type": price_type,
            "include_volume": include_volume,
        }

        payload = provider.get(symbol, DataType.FUTURES_TERM_STRUCTURE, params=params)
        return _payload_to_dict(payload)
