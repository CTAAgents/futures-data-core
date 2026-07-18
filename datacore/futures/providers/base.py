"""FuturesDataSource 抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional
from datacore.models.enums import DataType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.models.ohlcv import KlineData, QuoteData


class FuturesDataSource(ABC):
    name: str = ""
    priority: int = 99
    supported_types: set[DataType] = set()

    @abstractmethod
    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        """获取 K 线数据。"""

    @abstractmethod
    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        """获取实时行情。"""

    def check_available(self) -> bool:
        return True
