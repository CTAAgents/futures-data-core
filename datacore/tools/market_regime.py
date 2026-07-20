"""DataCoreMarketRegimeTool - 市场制度检测工具。"""

from __future__ import annotations

from typing import Any

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreMarketRegimeTool(DataCoreBaseTool):
    """检测市场制度/状态。

    基于价格数据识别当前市场处于趋势、震荡、上涨、下跌等状态。
    """

    name = "datacore_market_regime"
    description = (
        "检测市场制度/状态。基于价格数据识别趋势、震荡、上涨、下跌等状态。"
        "参数：symbol (str, 必需) - 品种代码；"
        "period (str, 可选) - K线周期，默认 'daily'；"
        "lookback (int, 可选) - 回顾周期数，默认 60；"
        "method (str, 可选) - 检测方法，'ma'/'bb'/'regime'/'auto'，默认 'auto'"
    )

    def _run(self, symbol: str, period: str = "daily", lookback: int = 60,
             method: str = "auto", **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {
            "period": period,
            "lookback": lookback,
            "method": method,
        }

        payload = provider.get(symbol, DataType.MARKET_STATE, params=params)
        return _payload_to_dict(payload)
