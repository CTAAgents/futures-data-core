"""腾讯 HTTP 数据源 — A 股第一源。"""
from __future__ import annotations
from typing import Optional
import httpx
import time
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.equity.providers.base import EquityDataSource

_EXCHANGE_MAP = {
    "6": "sh", "5": "sh", "11": "sh", "50": "sh",
    "0": "sz", "1": "sz", "12": "sz", "18": "sz", "3": "sz",
}

_KL_DAY_PARAM = {DataType.OHLCV: "day", "1d": "day", "daily": "day",
                 "week": "week", "month": "month"}


def _detect_market_code(symbol: str) -> str:
    """根据代码前缀判断沪/深市场。"""
    sym = symbol.strip()
    for prefix, market in _EXCHANGE_MAP.items():
        if sym.startswith(prefix):
            return market
    return "sh"


def _parse_tencent_quote(text: str, symbol: str) -> Optional[QuoteData]:
    """解析腾讯行情文本。"""
    try:
        parts = text.split("~")
        qd = QuoteData(symbol=symbol, source="tencent")
        qd.last_price = _f(parts[3])
        qd.pre_close = _f(parts[4])
        qd.open = _f(parts[5])
        qd.volume = _f(parts[6])
        qd.amount = _f(parts[7]) * 10000 if parts[7] else None
        qd.high = _f(parts[33]) if len(parts) > 33 else None
        qd.low = _f(parts[34]) if len(parts) > 34 else None
        qd.change_pct = _f(parts[32]) if len(parts) > 32 else None
        qd.update_time = parts[31] if len(parts) > 31 else None
        qd.bid_price = [_f(parts[9]), _f(parts[11]), _f(parts[13]), _f(parts[15]), _f(parts[17])]
        qd.ask_price = [_f(parts[10]), _f(parts[12]), _f(parts[14]), _f(parts[16]), _f(parts[18])]
        return qd
    except (IndexError, ValueError):
        return None


def _f(v) -> Optional[float]:
    if v in (None, "", "--", "N/A"):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


class TencentProvider(EquityDataSource):
    name = "tencent"
    priority = 0
    supported_types = {DataType.OHLCV, DataType.QUOTE}

    def fetch(self, symbol: str, data_type: DataType,
              params: dict | None = None) -> Optional[DataPayload]:
        if data_type == DataType.QUOTE:
            return self._fetch_quote(symbol)
        if data_type == DataType.OHLCV:
            return self._fetch_kline(symbol, params)
        return None

    def _fetch_quote(self, symbol: str) -> Optional[DataPayload]:
        market = _detect_market_code(symbol)
        try:
            with httpx.Client(timeout=5) as c:
                resp = c.get(f"http://qt.gtimg.cn/q={market}{symbol}")
                resp.encoding = "gbk"
                text = resp.text.strip().strip(";")
                if not text or "=" not in text:
                    return None
                _, value = text.split("=", 1)
                value = value.strip('"')
        except Exception:
            return None
        qd = _parse_tencent_quote(value, symbol)
        if not qd:
            return None
        return DataPayload(
            symbol=symbol, data_type=DataType.QUOTE,
            market=MarketType.STOCK, data=qd,
            source="tencent", grade=SourceGrade.PRIMARY,
            collected_at=time.time(),
        )

    def _fetch_kline(self, symbol: str, params: dict | None = None) -> Optional[DataPayload]:
        params = params or {}
        period = params.get("period", "daily")
        days = int(params.get("days", 320))
        market = _detect_market_code(symbol)
        _p = _KL_DAY_PARAM.get(period, period)
        try:
            with httpx.Client(timeout=10) as c:
                url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
                resp = c.get(url, params={"param": f"{market}{symbol},{_p},,{days},qfq"})
                data = resp.json()
            # 解析 K 线
            series = None
            if data and "data" in data:
                d = data["data"]
                ks = d.get(f"{market}{symbol}") or d.get(symbol) or {}
                series = ks.get(_p) or ks.get("qfq" + _p) or ks.get("day")
            if not series:
                return None
            bars = []
            for row in series:
                try:
                    bars.append(KBar(
                        date=str(row[0]), open=float(row[1]),
                        close=float(row[2]), high=float(row[3]),
                        low=float(row[4]), volume=float(row[5]) if len(row) > 5 else 0,
                        amount=float(row[6]) if len(row) > 6 else 0,
                    ))
                except (IndexError, ValueError, TypeError):
                    continue
            if not bars:
                return None
            kd = KlineData(symbol=symbol, period=period, bars=bars, source="tencent")
            return DataPayload(
                symbol=symbol, data_type=DataType.OHLCV,
                market=MarketType.STOCK, data=kd,
                source="tencent", grade=SourceGrade.PRIMARY,
                collected_at=time.time(),
            )
        except Exception:
            return None

    def check_available(self) -> bool:
        try:
            with httpx.Client(timeout=3) as c:
                r = c.get("http://qt.gtimg.cn/q=sh000001")
                return r.status_code == 200
        except Exception:
            return False
