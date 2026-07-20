"""数据类型、市场类型、数据质量等级枚举。"""

from __future__ import annotations
from enum import Enum


class DataType(str, Enum):
    """数据类型枚举 — 按数据结构特征和市场特异性划分。

    通用类型（无市场前缀）: 全市场通用
    市场特异类型（带市场前缀）: 特定市场专用
    v0.3.0: SENTIMENT/MARKET_STATE 由 Data-Core 数据加工层产出（含LLM打分+聚合）
    """

    # ── 通用类型（全市场） ──
    OHLCV = "ohlcv"
    QUOTE = "quote"
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    NEWS = "news"
    ANNOUNCEMENT = "announcement"
    SENTIMENT = "sentiment"               # v0.3.0: Data-Core 数据加工层产出
    MARKET_STATE = "market_state"         # v0.3.0: Data-Core 数据加工层产出

    # ── 期货特异类型 ──
    FUTURES_CONTRACT_CHAIN = "futures_contract_chain"
    FUTURES_TERM_STRUCTURE = "futures_term_structure"
    FUTURES_SPREAD = "futures_spread"
    FUTURES_BASIS = "futures_basis"
    FUTURES_POSITION = "futures_position"
    FUTURES_WAREHOUSE_RECEIPT = "futures_warehouse_receipt"

    ETF_NAV = "etf_nav"
    ETF_PREMIUM = "etf_premium"
    ETF_FUND_FLOW = "etf_fund_flow"

    CB_CONVERSION = "cb_conversion"
    CB_TERMS = "cb_terms"
    CB_PURE_BOND = "cb_pure_bond"

    # ── 聚合类型（v1.1） ──
    F10_REPORT = "f10_report"


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
