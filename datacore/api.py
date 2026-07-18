"""UnifiedDataProvider - Data-Core unified data entry point."""

from __future__ import annotations
import time
from typing import Any, Optional

from .models.enums import DataType, MarketType, SourceGrade
from .models.payload import DataPayload
from .registry.symbol_registry import SymbolRegistry

_futures_provider: Any = None
_equity_provider: Any = None


def _get_futures():
    global _futures_provider
    if _futures_provider is None:
        from .futures import FuturesDataProvider
        _futures_provider = FuturesDataProvider()
    return _futures_provider


def _get_equity():
    global _equity_provider
    if _equity_provider is None:
        from .equity import EquityDataProvider
        _equity_provider = EquityDataProvider()
    return _equity_provider


class UnifiedDataProvider:
    """Data-Core unified data entry point.

    All consumers obtain data through this interface,
    automatically routing to futures or equity modules.
    """

    def __init__(self):
        self.registry = SymbolRegistry()

    def get(self, symbol: str, data_type: DataType,
            params: dict | None = None) -> DataPayload:
        """Fetch data for the given symbol and type."""
        market = self.registry.resolve_market(symbol)
        if market is None:
            return DataPayload(
                symbol=symbol, data_type=data_type,
                market=MarketType.FUTURES,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"Unknown symbol: {symbol}"],
            )

        payload: Optional[DataPayload] = None
        collected_at = time.time()

        if market == MarketType.FUTURES:
            payload = _get_futures().get(symbol, data_type, params)
        elif market in (MarketType.STOCK, MarketType.ETF,
                        MarketType.CB, MarketType.REIT):
            payload = _get_equity().get(symbol, data_type, params)

        if payload is None:
            return DataPayload(
                symbol=symbol, data_type=data_type, market=market,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"{market} module does not support {data_type}"],
                collected_at=collected_at,
            )
        return payload

    def get_batch(self, symbols: list[str], data_type: DataType,
                  params: dict | None = None) -> dict[str, DataPayload]:
        """Batch fetch data for multiple symbols."""
        return {sym: self.get(sym, data_type, params) for sym in symbols}

    def list_symbols(self, market: MarketType | None = None) -> list[dict]:
        """List all available symbols."""
        if market:
            return [
                {"symbol": e.symbol, "name": e.name, "market": e.market.value}
                for e in self.registry.list_by_market(market)
            ]
        return [
            {"symbol": e.symbol, "name": e.name, "market": e.market.value}
            for e in self.registry.list_all()
        ]
