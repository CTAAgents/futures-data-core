"""OHLCV K 线数据结构。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KBar:
    """单根 K 线"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    amount: float = 0.0
    open_interest: Optional[float] = None
    settlement: Optional[float] = None


@dataclass
class KlineData:
    """K 线数据集"""
    symbol: str
    period: str
    bars: list[KBar] = field(default_factory=list)
    source: str = ""
    contract: str = ""


@dataclass
class QuoteData:
    """实时行情快照"""
    symbol: str
    source: str = ""
    last_price: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    bid_price: list[float] = field(default_factory=list)
    ask_price: list[float] = field(default_factory=list)
    change_pct: Optional[float] = None
    update_time: Optional[str] = None
