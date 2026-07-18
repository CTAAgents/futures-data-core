"""A 股数据统一入口。"""
from __future__ import annotations
import time
from typing import Optional
from datacore.models.enums import DataType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.equity.providers import TencentProvider, EastMoneyEquityProvider


class EquityDataProvider:
    """A 股数据提供者 — 多源降级链: 腾讯 → 东方财富。"""

    def __init__(self):
        self.sources = [TencentProvider(), EastMoneyEquityProvider()]

    def get(self, symbol: str, data_type: DataType,
            params: dict | None = None) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if data_type not in src.supported_types:
                continue
            try:
                payload = src.fetch(symbol, data_type, params)
                if payload and payload.available:
                    return payload
            except Exception:
                continue
        return DataPayload(
            symbol=symbol, data_type=data_type,
            market=type(self).__module__,
            grade=SourceGrade.UNAVAILABLE,
            errors=["所有 A 股源不可用"], collected_at=time.time(),
        )
