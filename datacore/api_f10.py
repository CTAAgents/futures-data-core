"""F10 comprehensive report API.

Aggregates multiple data types (term structure, spread, basis, warehouse
receipts, position rank, fundamental) into a single F10 payload.
"""

from __future__ import annotations

import time

from .models.enums import DataType, MarketType, SourceGrade
from .models.payload import DataPayload
from .registry.symbol_registry import SymbolRegistry


F10_SUB_MODULES = [
    "term_structure",
    "spread",
    "basis",
    "warehouse_receipt",
    "position_rank",
    "fundamental",
]


def get_f10_sync(provider, symbol: str) -> DataPayload:
    """Build F10 report synchronously by calling provider for each sub-module.

    Args:
        provider: UnifiedDataProvider instance
        symbol: futures or equity symbol
    """
    data: dict = {}
    errors: list[str] = []
    collected_at = time.time()

    data_type_map = {
        "term_structure": DataType.FUTURES_TERM_STRUCTURE,
        "spread": DataType.FUTURES_SPREAD,
        "basis": DataType.FUTURES_BASIS,
        "warehouse_receipt": DataType.FUTURES_WAREHOUSE_RECEIPT,
        "position_rank": DataType.FUTURES_POSITION,
    }

    for key, dt in data_type_map.items():
        try:
            payload = provider.get(symbol, dt)
            if payload.available:
                data[key] = payload.data
            if payload.errors:
                errors.extend(f"{key}: {e}" for e in payload.errors)
        except Exception as e:
            errors.append(f"{key}: {e}")

    any_ok = any(k in data for k in ("term_structure", "spread", "basis"))
    market = SymbolRegistry().resolve_market(symbol) or MarketType.FUTURES

    return DataPayload(
        symbol=symbol,
        data_type=DataType.F10_REPORT,
        market=market,
        data=data,
        source="f10_aggregator",
        grade=SourceGrade.PRIMARY if any_ok else SourceGrade.UNAVAILABLE,
        collected_at=collected_at,
        errors=errors,
        meta={"sub_modules": list(data_type_map.keys())},
    )
