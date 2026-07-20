"""AsyncDataProvider — async wrapper around UnifiedDataProvider.

Uses run_in_executor (thread pool) to bridge sync code into async context.
This is Phase 1 of v2.0 upgrade — a zero-breaking-change async layer.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from .models.enums import DataType, MarketType
from .models.payload import DataPayload


class AsyncDataProvider:
    """Async interface to Data-Core.

    Wraps UnifiedDataProvider with thread-pool-based async bridge.
    All sync methods are exposed as async equivalents.

    Usage::

        adc = AsyncDataProvider()
        payload = await adc.get("RB", DataType.OHLCV)
    """

    def __init__(self, executor: Optional[asyncio.AbstractEventLoop] = None):
        self._sync: Optional[object] = None
        self._executor = executor

    def _ensure_sync(self):
        if self._sync is None:
            from .api import UnifiedDataProvider
            self._sync = UnifiedDataProvider()
        return self._sync

    async def get(self, symbol: str, data_type: DataType,
                  params: dict | None = None) -> DataPayload:
        """Async version of UnifiedDataProvider.get()."""
        sync = self._ensure_sync()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, sync.get, symbol, data_type, params
        )

    async def get_batch(self, symbols: list[str], data_type: DataType,
                        params: dict | None = None) -> dict[str, DataPayload]:
        """Async batch fetch — concurrent via gather."""
        tasks = [self.get(s, data_type, params) for s in symbols]
        results = await asyncio.gather(*tasks)
        return dict(zip(symbols, results))

    async def list_symbols(self, market: MarketType | None = None) -> list[dict]:
        sync = self._ensure_sync()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, sync.list_symbols, market
        )

    async def get_health(self) -> dict:
        sync = self._ensure_sync()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, sync.get_health
        )

    async def get_f10(self, symbol: str) -> DataPayload:
        """F10 comprehensive report — convenience wrapper.

        Aggregates multiple data types into a single payload.
        """
        from .models.enums import DataType
        from .models.payload import DataPayload

        tasks = {
            "term_structure": self.get(symbol, DataType.FUTURES_TERM_STRUCTURE),
            "spread": self.get(symbol, DataType.FUTURES_SPREAD),
            "basis": self.get(symbol, DataType.FUTURES_BASIS),
            "warehouse_receipt": self.get(symbol, DataType.FUTURES_WAREHOUSE_RECEIPT),
            "position_rank": self.get(symbol, DataType.FUTURES_POSITION),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        data: dict = {}
        errors: list[str] = []
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                errors.append(f"{key}: {result}")
            elif isinstance(result, DataPayload):
                if result.available:
                    data[key] = result.data
                if result.errors:
                    errors.extend(f"{key}: {e}" for e in result.errors)

        any_ok = any(k in data for k in ("term_structure", "spread"))
        from .models.enums import SourceGrade
        from .registry.symbol_registry import SymbolRegistry
        market = SymbolRegistry().resolve_market(symbol) or MarketType.FUTURES

        return DataPayload(
            symbol=symbol,
            data_type=DataType.F10_REPORT,
            market=market,
            data=data,
            source="f10_aggregator",
            grade=SourceGrade.PRIMARY if any_ok else SourceGrade.UNAVAILABLE,
            collected_at=__import__("time").time(),
            errors=errors,
            meta={"sub_modules": list(tasks.keys())},
        )
