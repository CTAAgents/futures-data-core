"""Shared typed data structures for Data-Core core layer.

These types are consumed by providers, processing layers, and tools.
They are deliberately kept lightweight (pure dataclasses, no business logic).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class KlineBar:
    """Single K-line / OHLCV bar.

    Compatible with FDC's KlineBar for seamless migration.
    """

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0
    open_interest: float = 0.0

    def __post_init__(self):
        for f in ("open", "high", "low", "close", "volume", "amount", "open_interest"):
            setattr(self, f, float(getattr(self, f) or 0.0))


@dataclass
class QuoteData:
    """Real-time / delayed quote snapshot.

    Compatible with FDC's QuoteData for seamless migration.
    """

    symbol: str
    name: str = ""
    last_price: float = 0.0
    prev_close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    bid1: float = 0.0
    ask1: float = 0.0
    update_time: Optional[datetime] = None
    source: str = ""

    @property
    def change_pct(self) -> float:
        if self.prev_close <= 0:
            return 0.0
        return round((self.last_price - self.prev_close) / self.prev_close * 100, 2)


@dataclass
class FreshnessStatus:
    """Data freshness assessment result."""

    is_fresh: bool
    age_seconds: float
    threshold_seconds: float
    status: str  # "fresh" | "stale" | "expired"
    last_updated: float = 0.0
    message: str = ""
