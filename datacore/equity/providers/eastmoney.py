"""东方财富 HTTP 数据源 — A 股降级源。"""
from __future__ import annotations
from typing import Optional
import httpx, time
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.models.ohlcv import KBar, KlineData
from datacore.equity.providers.base import EquityDataSource


class EastMoneyEquityProvider(EquityDataSource):
    name = "eastmoney_equity"
    priority = 1
    supported_types = {DataType.OHLCV, DataType.FINANCIAL, DataType.MACRO}

    def fetch(self, symbol: str, data_type: DataType,
              params: dict | None = None) -> Optional[DataPayload]:
        if data_type == DataType.OHLCV:
            return self._fetch_kline(symbol, params)
        if data_type == DataType.FINANCIAL:
            return self._fetch_financial(symbol)
        if data_type == DataType.MACRO:
            return self._fetch_macro()
        return None

    def _fetch_kline(self, symbol: str, params: dict | None = None) -> Optional[DataPayload]:
        params = params or {}
        period = params.get("period", "daily")
        days = int(params.get("days", 400))
        secid = f"1.{symbol}" if symbol.startswith(("6", "5", "11", "50")) else f"0.{symbol}"
        try:
            with httpx.Client(timeout=10) as c:
                resp = c.get(
                    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                    params={
                        "secid": secid,
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                        "klt": 101 if period == "daily" else 60,
                        "fqt": 1, "end": "20500101", "lmt": days,
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
                    close=float(k["f55"]), high=float(k["f53"]),
                    low=float(k["f54"]), volume=float(k["f56"]),
                    amount=float(k["f57"]),
                ))
            except (KeyError, TypeError, ValueError):
                continue
        kd = KlineData(symbol=symbol, period=period, bars=bars, source=self.name)
        return DataPayload(
            symbol=symbol, data_type=DataType.OHLCV,
            market=MarketType.STOCK, data=kd,
            source=self.name, grade=SourceGrade.DAILY,
            collected_at=time.time(),
        )

    def _fetch_financial(self, symbol: str) -> Optional[DataPayload]:
        """获取财务指标(PE/PB)。"""
        secid = f"1.{symbol}" if symbol.startswith(("6", "5", "11", "50")) else f"0.{symbol}"
        try:
            with httpx.Client(timeout=10) as c:
                resp = c.get(
                    "https://push2.eastmoney.com/api/qt/stock/get",
                    params={
                        "secid": secid,
                        "fields": "f43,f44,f45,f46,f57,f58,f162,f167,f168,f169,f170",
                    },
                )
                data = resp.json().get("data", {})
        except Exception:
            return None
        if not data:
            return None
        fin = {
            "pe": _f(data.get("f162")),
            "pe_ttm": _f(data.get("f167")),
            "pb": _f(data.get("f168")),
            "market_cap": _f(data.get("f45")),
            "total_share": _f(data.get("f46")),
        }
        return DataPayload(
            symbol=symbol, data_type=DataType.FINANCIAL,
            market=MarketType.STOCK, data=fin,
            source=self.name, grade=SourceGrade.DAILY,
            collected_at=time.time(),
        )

    def _fetch_macro(self) -> Optional[DataPayload]:
        """获取宏观数据(PMI/LPR)。"""
        macro = {}
        try:
            with httpx.Client(timeout=10) as c:
                r = c.get(
                    "https://datacenter-web.eastmoney.com/api/data/v1/get",
                    params={
                        "reportName": "RPT_ECONOMY_PMI",
                        "columns": "REPORT_DATE,INDICATOR_ID,CLOSE",
                        "pageNumber": 1, "pageSize": 2, "sortTypes": -1,
                        "sortColumns": "REPORT_DATE",
                    },
                )
                d = r.json()
                for item in (d.get("result", {}).get("data", []) or []):
                    macro["pmi"] = float(item.get("CLOSE", 0))
                    macro["pmi_date"] = str(item.get("REPORT_DATE", ""))
        except Exception:
            pass
        if not macro:
            return None
        return DataPayload(
            symbol="*", data_type=DataType.MACRO,
            market=MarketType.STOCK, data=macro,
            source=self.name, grade=SourceGrade.DAILY,
            collected_at=time.time(),
        )

    def check_available(self) -> bool:
        try:
            with httpx.Client(timeout=3) as c:
                r = c.head("https://push2.eastmoney.com")
                return r.status_code < 500
        except Exception:
            return False


def _f(v) -> Optional[float]:
    if v in (None, "", "--"):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
