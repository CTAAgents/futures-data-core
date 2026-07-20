"""DataCoreNewsTool - 新闻资讯工具。"""

from __future__ import annotations

from typing import Any, Optional

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreNewsTool(DataCoreBaseTool):
    """获取新闻资讯数据。

    支持按品种、时间范围、分类等筛选新闻，返回已分类的新闻列表。
    """

    name = "datacore_news"
    description = (
        "获取新闻资讯数据。支持按品种、时间范围筛选。"
        "参数：symbol (str, 可选) - 品种代码，不传则返回全市场新闻；"
        "limit (int, 可选) - 返回新闻条数，默认 50；"
        "start_date (str, 可选) - 开始日期，格式 'YYYY-MM-DD'；"
        "end_date (str, 可选) - 结束日期，格式 'YYYY-MM-DD'；"
        "category (str, 可选) - 新闻分类，如 '宏观'、'行业'、'公司' 等；"
        "source (str, 可选) - 新闻来源"
    )

    def _run(self, symbol: Optional[str] = None, limit: int = 50,
             start_date: Optional[str] = None, end_date: Optional[str] = None,
             category: Optional[str] = None, source: Optional[str] = None,
             **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {"limit": limit}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if category:
            params["category"] = category
        if source:
            params["source"] = source

        sym = symbol or "ALL"
        payload = provider.get(sym, DataType.NEWS, params=params)
        return _payload_to_dict(payload)
