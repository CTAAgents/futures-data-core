"""数据类型、市场类型、数据质量等级枚举。"""

from __future__ import annotations
from enum import Enum


class DataType(str, Enum):
    """FTS 数据类型 — 按数据结构特征划分。"""

    OHLCV = "ohlcv"
    QUOTE = "quote"
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    NEWS = "news"
    ANNOUNCEMENT = "announcement"
    SENTIMENT = "sentiment"
    MARKET_STATE = "market_state"


class MarketType(str, Enum):
    """市场类型。"""
    FUTURES = "futures"
    STOCK = "stock"
    ETF = "etf"
    CB = "cb"
    REIT = "reit"


class SourceGrade(str, Enum):
    """数据质量等级（从高到低）。"""
    PRIMARY = "primary"
    DAILY = "daily"
    CACHED = "cached"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
