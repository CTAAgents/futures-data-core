"""DataCoreMacroTool - 宏观经济数据工具。"""

from __future__ import annotations

from typing import Any, Optional

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreMacroTool(DataCoreBaseTool):
    """获取宏观经济数据。

    支持 GDP、CPI、PPI、PMI、利率、汇率等宏观经济指标。
    """

    name = "datacore_macro"
    description = (
        "获取宏观经济数据。支持 GDP、CPI、PPI、PMI、利率、汇率等指标。"
        "参数：indicator (str, 可选) - 指标名称，如 'GDP'、'CPI'、'PPI' 等；"
        "category (str, 可选) - 指标类别，'growth'/'inflation'/'finance'/'trade' 等；"
        "frequency (str, 可选) - 数据频率，'monthly'/'quarterly'/'yearly'；"
        "start_date (str, 可选) - 开始日期；"
        "end_date (str, 可选) - 结束日期；"
        "limit (int, 可选) - 返回数据条数，默认 100"
    )

    def _run(self, indicator: Optional[str] = None, category: Optional[str] = None,
             frequency: Optional[str] = None, start_date: Optional[str] = None,
             end_date: Optional[str] = None, limit: int = 100,
             **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {"limit": limit}
        if indicator:
            params["indicator"] = indicator
        if category:
            params["category"] = category
        if frequency:
            params["frequency"] = frequency
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        symbol = indicator or "macro"
        payload = provider.get(symbol, DataType.MACRO, params=params)
        return _payload_to_dict(payload)
