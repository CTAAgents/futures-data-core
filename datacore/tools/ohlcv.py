"""DataCoreOHLCVTool - OHLCV K线数据工具。"""

from __future__ import annotations

from typing import Any, Optional

from .base import DataCoreBaseTool


class DataCoreOHLCVTool(DataCoreBaseTool):
    """获取 OHLCV K 线数据。

    支持期货、股票、ETF 等品种的 K 线数据获取，
    可指定周期（1m/5m/15m/30m/60m/daily/weekly/monthly）。
    """

    name = "datacore_ohlcv"
    description = (
        "获取 OHLCV K 线数据。支持期货、股票、ETF 等品种。"
        "参数：symbol (str, 必需) - 品种代码，如 'RB'、'000001'；"
        "period (str, 可选) - K线周期，默认 'daily'，可选值: 1m, 5m, 15m, 30m, 60m, daily, weekly, monthly；"
        "limit (int, 可选) - 返回数据条数，默认 100；"
        "start_date (str, 可选) - 开始日期，格式 'YYYY-MM-DD'；"
        "end_date (str, 可选) - 结束日期，格式 'YYYY-MM-DD'；"
        "adjust (str, 可选) - 复权方式，'none'/'forward'/'backward'，默认 'none'"
    )

    def _run(self, symbol: str, period: str = "daily", limit: int = 100,
             start_date: Optional[str] = None, end_date: Optional[str] = None,
             adjust: str = "none", **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {
            "period": period,
            "limit": limit,
            "adjust": adjust,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        payload = provider.get(symbol, DataType.OHLCV, params=params)
        return _payload_to_dict(payload)


def _payload_to_dict(payload: Any) -> dict[str, Any]:
    """将 DataPayload 转换为字典格式。"""
    data = payload.data
    if hasattr(data, "to_dict"):
        data = data.to_dict()
    elif hasattr(data, "tolist"):
        data = data.tolist()

    return {
        "symbol": payload.symbol,
        "data_type": payload.data_type.value if hasattr(payload.data_type, "value") else str(payload.data_type),
        "market": payload.market.value if hasattr(payload.market, "value") else str(payload.market),
        "data": data,
        "source": payload.source,
        "grade": payload.grade.value if hasattr(payload.grade, "value") else str(payload.grade),
        "available": payload.available,
        "collected_at": payload.collected_at,
        "meta": payload.meta,
        "errors": payload.errors,
        "warnings": payload.warnings,
    }
