"""TQ-Local 期货数据源 — 通达信本地 HTTP 服务。"""

from __future__ import annotations

import json
import time
from typing import Optional

import httpx

from datacore.config import get_config
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.models.enums import DataType

FUTURES_MARKET = "92"
PERIOD_MAP = {"daily": "1d", "60m": "60m", "120m": "120m", "240m": "240m", "weekly": "1w"}


class TdxLcProvider(FuturesDataSource):
    name = "tdx_lc"
    priority = 0
    supported_types = {DataType.OHLCV, DataType.QUOTE, DataType.TECHNICAL}

    def __init__(self, url: Optional[str] = None, timeout: Optional[int] = None):
        config = get_config()
        self.url = url or config.tdx_url
        self.timeout = timeout or config.tdx_timeout
        self._contract_cache: Optional[dict] = None

    def _post(self, method: str, params: dict) -> dict:
        payload = {"id": 1, "method": method, "params": params}
        try:
            with httpx.Client(timeout=self.timeout) as c:
                resp = c.post(self.url, json=payload)
            return resp.json().get("result", {})
        except Exception:
            return {}

    def _load_contracts(self):
        if self._contract_cache is not None:
            return
        self._contract_cache = {}
        resp = self._post("get_stock_list", {"market": FUTURES_MARKET, "list_type": 1})
        result = resp.get("Value", resp) if isinstance(resp, dict) else resp
        if not isinstance(result, list):
            return
        for item in result:
            code = item.get("Code", "")
            alpha = "".join(c for c in code.split(".")[0] if c.isalpha()).upper()
            if alpha and alpha not in self._contract_cache:
                self._contract_cache[alpha] = code

    def _resolve_contract(self, symbol: str) -> Optional[str]:
        self._load_contracts()
        return (self._contract_cache or {}).get(symbol.upper())

    def check_available(self) -> bool:
        resp = self._post("get_stock_list", {"market": FUTURES_MARKET, "list_type": 1})
        result = resp.get("Value", resp) if isinstance(resp, dict) else resp
        return isinstance(result, list) and len(result) > 0

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        contract = self._resolve_contract(symbol)
        if not contract:
            return None
        tdx_period = PERIOD_MAP.get(period, "1d")
        resp = self._post("get_market_data", {
            "stock_list": [contract], "count": days,
            "dividend_type": "none", "period": tdx_period,
        })
        value = resp.get("Value", resp) if isinstance(resp, dict) else resp
        series = None
        if isinstance(value, dict):
            series = value.get(contract) or value.get("Value", {}).get(contract) if isinstance(value, dict) else None
        if not isinstance(series, dict):
            return None
        dates = series.get("Date", []) or []
        bars = []
        for i in range(min(len(dates), len(series.get("Open", [])))):
            try:
                bars.append(KBar(
                    date=str(dates[i]),
                    open=float(series["Open"][i]),
                    high=float(series["High"][i]),
                    low=float(series["Low"][i]),
                    close=float(series["Close"][i]),
                    volume=float(series.get("Volume", [0])[i] if i < len(series.get("Volume", [])) else 0),
                    amount=float(series.get("Amount", [0])[i] if i < len(series.get("Amount", [])) else 0),
                    open_interest=float(series.get("Hold", [0])[i] if i < len(series.get("Hold", [])) else 0),
                ))
            except (TypeError, ValueError):
                continue
        return KlineData(symbol=symbol, period=period, bars=bars, source=self.name, contract=contract)

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        contract = self._resolve_contract(symbol)
        if not contract:
            return None
        resp = self._post("get_market_snapshot", {"stock_code": contract})
        snap = resp.get("Value", resp) if isinstance(resp, dict) else resp
        if not isinstance(snap, dict):
            return None

        def _f(k: str):
            v = snap.get(k)
            return float(v) if v not in (None, "", "--") else None

        return QuoteData(
            symbol=symbol, source=self.name,
            last_price=_f("Now"), open=_f("Open"),
            high=_f("Max"), low=_f("Min"),
            pre_close=_f("LastClose"), volume=_f("Volume"),
            update_time=str(snap.get("UpdateTime", "")),
        )
