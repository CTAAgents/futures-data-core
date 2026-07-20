"""Data-Core — 统一数据中心。

为股票、期货市场的投研提供统一数据接口的独立基础设施模块。
所有数据源自包含，零外部 MCP/Skill/Agent 依赖。

使用方式:
    from datacore import UnifiedDataProvider
    from datacore.models.enums import DataType

    dc = UnifiedDataProvider()
    ohlcv = dc.get("RB", DataType.OHLCV, {"period": "daily", "days": 400})
    quote = dc.get("600519", DataType.QUOTE)
"""

__version__ = "2.0.0"
__all__ = ["UnifiedDataProvider", "AsyncDataProvider"]

from .api import UnifiedDataProvider
from .api_async import AsyncDataProvider
