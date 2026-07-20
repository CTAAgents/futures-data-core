"""TqSdk 期货数据源 — P6 兜底。

数据来源: tqsdk (天勤量化 SDK)
  - K 线数据
  - 实时行情
"""
from __future__ import annotations
from typing import Optional
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.models.enums import DataType

try:
    import tqsdk  # noqa: F401
    _TQ_AVAILABLE = True
except ImportError:
    _TQ_AVAILABLE = False


class TqSdkProvider(FuturesDataSource):
    """TqSdk 天勤量化期货数据源。"""
    name = "tqsdk"
    priority = 6
    supported_types = {
        DataType.OHLCV,
        DataType.QUOTE,
    }

    def check_available(self) -> bool:
        return _TQ_AVAILABLE

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        if not _TQ_AVAILABLE:
            return None
        try:
            from tqsdk import TqApi, TqAuth
            api = TqApi(auth=TqAuth("", ""))
            try:
                klines = api.get_kline_serial(symbol.upper(), duration_seconds=86400, data_length=days)
                if klines is None or klines.empty:
                    return None
                bars = []
                for _, row in klines.iterrows():
                    try:
                        bars.append(KBar(
                            date=str(row.get("datetime", "")),
                            open=float(row.get("open", 0)),
                            high=float(row.get("high", 0)),
                            low=float(row.get("low", 0)),
                            close=float(row.get("close", 0)),
                            volume=float(row.get("volume", 0)),
                            amount=float(row.get("close", 0)) * float(row.get("volume", 0)),
                        ))
                    except (KeyError, TypeError, ValueError):
                        continue
                return KlineData(symbol=symbol, period=period, bars=bars, source=self.name)
            finally:
                api.close()
        except Exception:
            return None

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        if not _TQ_AVAILABLE:
            return None
        try:
            from tqsdk import TqApi, TqAuth
            api = TqApi(auth=TqAuth("", ""))
            try:
                quote = api.get_quote(symbol.upper())
                if quote is None:
                    return None
                return QuoteData(
                    symbol=symbol,
                    last_price=float(getattr(quote, "last_price", 0)),
                    open=float(getattr(quote, "open", 0)),
                    high=float(getattr(quote, "highest", 0)),
                    low=float(getattr(quote, "lowest", 0)),
                    pre_close=float(getattr(quote, "pre_close", 0)),
                    volume=float(getattr(quote, "volume", 0)),
                    amount=float(getattr(quote, "amount", 0)),
                    source=self.name,
                )
            finally:
                api.close()
        except Exception:
            return None
