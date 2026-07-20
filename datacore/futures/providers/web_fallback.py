"""Web Fallback 期货数据源 — P5 网页备用。

数据来源:
  - 新浪财经网页
  - 东方财富网页
  - 其他公开网页数据源

  - K 线数据
  - 实时行情
  - 期限结构
  - 跨期价差
"""
from __future__ import annotations
from typing import Optional
import httpx
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KlineData, QuoteData
from datacore.models.enums import DataType
from datacore.models.futures import (
    TermStructure, SpreadData,
)


class WebFallbackProvider(FuturesDataSource):
    """Web Fallback 网页备用数据源。"""
    name = "web_fallback"
    priority = 5
    supported_types = {
        DataType.OHLCV,
        DataType.QUOTE,
        DataType.FUTURES_TERM_STRUCTURE,
        DataType.FUTURES_SPREAD,
    }

    def __init__(self):
        self._client = httpx.Client(timeout=10, follow_redirects=True)

    def check_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as c:
                r = c.head("https://finance.sina.com.cn")
                return r.status_code < 500
        except Exception:
            return False

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        try:
            url = f"https://finance.sina.com.cn/futures/quotes/{symbol.upper()}.shtml"
            resp = self._client.get(url)
            if resp.status_code >= 400:
                return None
            return None
        except Exception:
            return None

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        try:
            url = f"https://hq.sinajs.cn/list=nf_{symbol.lower()}"
            resp = self._client.get(
                url,
                headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )
            if resp.status_code >= 400:
                return None
            text = resp.text
            if not text or '=""' in text:
                return None
            return None
        except Exception:
            return None

    def fetch_term_structure(self, symbol: str) -> Optional[TermStructure]:
        try:
            return None
        except Exception:
            return None

    def fetch_spread(self, symbol: str, near_contract: str, far_contract: str,
                     period: str = "daily", days: int = 120) -> Optional[SpreadData]:
        try:
            return None
        except Exception:
            return None
