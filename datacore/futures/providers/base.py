"""FuturesDataSource 抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from datacore.models.enums import DataType
from datacore.models.ohlcv import KlineData, QuoteData
from datacore.models.futures import (
    ContractChain, TermStructure, SpreadData,
    BasisData, PositionRankData, WarehouseReceiptData,
)


class FuturesDataSource(ABC):
    name: str = ""
    priority: int = 99
    supported_types: set[DataType] = set()

    def normalize_symbol(self, symbol: str) -> str:
        """将统一符号转换为本 Provider 的本地格式。

        不同数据源对同一期货合约可能使用不同代码格式
        （如 TDX 用 2 位年份、TqSDK 用 1 位年份）。
        各 Provider 可覆盖此方法以声明本地格式，由
        FuturesDataProvider 在路由时自动调用。

        默认实现：原样返回（不做转换）。
        """
        return symbol

    @abstractmethod
    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        """获取 K 线数据。"""

    @abstractmethod
    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        """获取实时行情。"""

    def fetch_contract_chain(self, symbol: str, num_contracts: int = 5,
                             period: str = "daily", days: int = 120) -> Optional[ContractChain]:
        """获取合约链数据（多合约 K线）。"""
        return None

    def fetch_term_structure(self, symbol: str) -> Optional[TermStructure]:
        """获取期限结构快照。"""
        return None

    def fetch_spread(self, symbol: str, near_contract: str, far_contract: str,
                     period: str = "daily", days: int = 120) -> Optional[SpreadData]:
        """获取跨期价差数据。"""
        return None

    def fetch_basis(self, symbol: str) -> Optional[BasisData]:
        """获取基差数据。"""
        return None

    def fetch_position_rank(self, symbol: str) -> Optional[PositionRankData]:
        """获取持仓排名数据。"""
        return None

    def fetch_warehouse_receipts(self, symbol: str) -> Optional[WarehouseReceiptData]:
        """获取仓单数据。"""
        return None

    def check_available(self) -> bool:
        return True
