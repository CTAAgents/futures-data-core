"""Data freshness assessor — evaluate how "fresh" a data payload is.

Used by caching, circuit breaker, and health check components.
"""

from __future__ import annotations

import time
from typing import Optional

from .types import FreshnessStatus


class DataFreshnessAssessor:
    """Assess data freshness based on collected_at timestamp and data type.

    Thresholds are per data type — real-time quote has a much shorter
    freshness window than daily OHLCV.
    """

    DEFAULT_THRESHOLDS: dict[str, float] = {
        "quote": 30,
        "tick": 5,
        "stream": 5,
        "ohlcv_1m": 120,
        "ohlcv_5m": 300,
        "ohlcv_15m": 900,
        "ohlcv_30m": 1800,
        "ohlcv_60m": 3600,
        "ohlcv_daily": 86400,
        "ohlcv_weekly": 604800,
        "ohlcv_monthly": 2592000,
        "macro": 86400,
        "news": 3600,
        "sentiment": 3600,
        "financial": 86400,
        "fundamental": 86400,
    }

    def __init__(self, thresholds: Optional[dict[str, float]] = None):
        self._thresholds = dict(self.DEFAULT_THRESHOLDS)
        if thresholds:
            self._thresholds.update(thresholds)

    def assess(self, collected_at: float, data_category: str = "ohlcv_daily") -> FreshnessStatus:
        """Assess freshness of a data point collected at `collected_at`."""
        now = time.time()
        age = max(0.0, now - collected_at)
        threshold = self._thresholds.get(data_category, 3600.0)

        if age <= threshold * 0.5:
            status = "fresh"
            is_fresh = True
            message = f"fresh ({int(age)}s old, threshold {int(threshold)}s)"
        elif age <= threshold:
            status = "stale"
            is_fresh = True
            message = f"approaching stale ({int(age)}s/{int(threshold)}s)"
        else:
            status = "expired"
            is_fresh = False
            message = f"expired ({int(age)}s old, threshold {int(threshold)}s)"

        return FreshnessStatus(
            is_fresh=is_fresh,
            age_seconds=age,
            threshold_seconds=threshold,
            status=status,
            last_updated=collected_at,
            message=message,
        )

    def set_threshold(self, category: str, seconds: float) -> None:
        self._thresholds[category] = seconds

    def get_threshold(self, category: str) -> float:
        return self._thresholds.get(category, 3600.0)

    @staticmethod
    def period_to_category(period: str) -> str:
        """Map a period string (e.g. '60m', 'daily') to a freshness category."""
        mapping = {
            "1m": "ohlcv_1m",
            "5m": "ohlcv_5m",
            "15m": "ohlcv_15m",
            "30m": "ohlcv_30m",
            "60m": "ohlcv_60m",
            "1h": "ohlcv_60m",
            "daily": "ohlcv_daily",
            "1d": "ohlcv_daily",
            "weekly": "ohlcv_weekly",
            "1w": "ohlcv_weekly",
            "monthly": "ohlcv_monthly",
            "1M": "ohlcv_monthly",
        }
        return mapping.get(period.lower(), "ohlcv_daily")
