"""东方财富 HTTP 期货数据源 — 回退源。"""
from __future__ import annotations
from typing import Optional
import httpx
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.models.enums import DataType


class EastMoneyFuturesProvider(FuturesDataSource):
    name = "eastmoney_futures"
    priority = 1
    supported_types = {DataType.OHLCV}

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        """通过东方财富公开 API 获取期货 K 线。"""
        secid = f"CF.{symbol.upper()}"
        try:
            with httpx.Client(timeout=10) as c:
                resp = c.get(
                    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                    params={
                        "secid": secid,
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                        "klt": 101 if period == "daily" else 60,
                        "fqt": 1,
                        "end": "20500101",
                        "lmt": days,
                    },
                )
                data = resp.json().get("data", {})
                klinedata = data.get("klinedata", []) if data else []
        except Exception:
            return None
        if not klinedata:
            return None
        bars = []
        for k in klinedata:
            try:
                bars.append(KBar(
                    date=str(k["f51"]), open=float(k["f52"]),
                    high=float(k["f53"]), low=float(k["f54"]),
                    close=float(k["f55"]), volume=float(k["f56"]),
                    amount=float(k["f57"]),
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return KlineData(symbol=symbol, period=period, bars=bars, source=self.name)

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        return None

    def check_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as c:
                r = c.head("https://push2his.eastmoney.com")
                return r.status_code < 500
        except Exception:
            return False
