"""FuturesDataProvider — 期货数据统一入口。"""
from __future__ import annotations
import time
from typing import Optional
from datacore.models.enums import DataType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.futures.providers import TdxLcProvider, EastMoneyFuturesProvider


class FuturesDataProvider:
    """期货数据提供者 — 多源降级链: TQ-Local → 东方财富。"""

    def __init__(self):
        self.sources = [TdxLcProvider(), EastMoneyFuturesProvider()]

    def get(self, symbol: str, data_type: DataType,
            params: dict | None = None) -> Optional[DataPayload]:
        params = params or {}
        period = params.get("period", "daily")
        days = int(params.get("days", 120))

        if data_type == DataType.OHLCV:
            return self._get_kline(symbol, period, days)
        elif data_type == DataType.QUOTE:
            return self._get_quote(symbol)
        return None

    def _get_kline(self, symbol: str, period: str, days: int) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.OHLCV not in src.supported_types:
                continue
            try:
                kd = src.fetch_kline(symbol, period, days)
                if kd and kd.bars:
                    grade = SourceGrade.PRIMARY if src.priority == 0 else SourceGrade.DAILY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.OHLCV,
                        market=type(self).__module__,
                        data=kd, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return DataPayload(
            symbol=symbol, data_type=DataType.OHLCV,
            market=type(self).__module__,
            grade=SourceGrade.UNAVAILABLE,
            errors=["所有期货源不可用"], collected_at=time.time(),
        )

    def _get_quote(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available() or DataType.QUOTE not in src.supported_types:
                continue
            try:
                qd = src.fetch_quote(symbol)
                if qd and qd.last_price:
                    return DataPayload(
                        symbol=symbol, data_type=DataType.QUOTE,
                        market=type(self).__module__,
                        data=qd, source=src.name,
                        grade=SourceGrade.PRIMARY,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None
