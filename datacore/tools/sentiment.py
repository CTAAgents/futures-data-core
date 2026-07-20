"""DataCoreSentimentTool - 市场情绪分析工具。"""

from __future__ import annotations

from typing import Any

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreSentimentTool(DataCoreBaseTool):
    """获取市场情绪分析数据。

    基于新闻资讯进行情绪打分（LLM 优先，规则基线降级），
    聚合后返回整体情绪指数和明细。
    """

    name = "datacore_sentiment"
    description = (
        "获取市场情绪分析数据。基于新闻资讯进行情绪打分和聚合。"
        "参数：symbol (str, 必需) - 品种代码；"
        "limit (int, 可选) - 使用的新闻条数，默认 50；"
        "method (str, 可选) - 情绪计算方法，'llm'/'rule'/'auto'，默认 'auto'"
    )

    def _run(self, symbol: str, limit: int = 50, method: str = "auto",
             **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {"limit": limit, "method": method}

        payload = provider.get(symbol, DataType.SENTIMENT, params=params)
        return _payload_to_dict(payload)
