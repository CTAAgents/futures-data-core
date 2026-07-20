"""QMT 迅投期货数据源 — P2。

数据来源: xtquant (QMT Python SDK)
  - K 线数据
  - 实时行情
  - 合约链
"""
from __future__ import annotations
from typing import Optional
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.models.enums import DataType
from datacore.models.futures import ContractChain

try:
    import xtquant  # noqa: F401
    _XTV_AVAILABLE = True
except ImportError:
    _XTV_AVAILABLE = False


class QMTProvider(FuturesDataSource):
    """QMT 迅投期货数据源。"""
    name = "qmt"
    priority = 2
    supported_types = {
        DataType.OHLCV,
        DataType.QUOTE,
        DataType.FUTURES_CONTRACT_CHAIN,
    }

    def check_available(self) -> bool:
        return _XTV_AVAILABLE

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        if not _XTV_AVAILABLE:
            return None
        try:
            from xtquant import xtdata
            period_map = {
                "daily": "1d",
                "weekly": "1w",
                "monthly": "1m",
                "60min": "1h",
                "30min": "30m",
                "15min": "15m",
                "5min": "5m",
                "1min": "1m",
            }
            xt_period = period_map.get(period, "1d")
            data = xtdata.get_market_data_ex(
                field_list=["time", "open", "high", "low", "close", "volume", "amount"],
                stock_list=[symbol.upper()],
                period=xt_period,
                count=days,
            )
            if not data or symbol.upper() not in data:
                return None
            df = data[symbol.upper()]
            if df is None or df.empty:
                return None
            bars = []
            for _, row in df.iterrows():
                try:
                    bars.append(KBar(
                        date=str(row.get("time", "")),
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=float(row.get("volume", 0)),
                        amount=float(row.get("amount", 0)),
                    ))
                except (KeyError, TypeError, ValueError):
                    continue
            return KlineData(symbol=symbol, period=period, bars=bars, source=self.name)
        except Exception:
            return None

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        if not _XTV_AVAILABLE:
            return None
        try:
            from xtquant import xtdata
            data = xtdata.get_full_tick([symbol.upper()])
            if not data or symbol.upper() not in data:
                return None
            tick = data[symbol.upper()]
            return QuoteData(
                symbol=symbol,
                last_price=float(tick.get("lastPrice", 0)),
                open=float(tick.get("open", 0)),
                high=float(tick.get("high", 0)),
                low=float(tick.get("low", 0)),
                pre_close=float(tick.get("lastClose", 0)),
                volume=float(tick.get("volume", 0)),
                amount=float(tick.get("amount", 0)),
                source=self.name,
            )
        except Exception:
            return None

    def fetch_contract_chain(self, symbol: str, num_contracts: int = 5,
                             period: str = "daily", days: int = 120) -> Optional[ContractChain]:
        if not _XTV_AVAILABLE:
            return None
        return None
