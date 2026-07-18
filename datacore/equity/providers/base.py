"""EquityDataSource 抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional
from datacore.models.enums import DataType, SourceGrade, MarketType
from datacore.models.payload import DataPayload


class EquityDataSource(ABC):
    name: str = ""
    priority: int = 99
    supported_types: set[DataType] = set()
    supported_markets: set[MarketType] = {MarketType.STOCK, MarketType.ETF, MarketType.CB, MarketType.REIT}

    @abstractmethod
    def fetch(self, symbol: str, data_type: DataType,
              params: dict | None = None) -> Optional[DataPayload]:
        """获取数据。"""

    def check_available(self) -> bool:
        return True
