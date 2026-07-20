"""DataCoreInstrumentProvider — Qlib 风格的 InstrumentProvider 适配器。

提供与 Qlib InstrumentProvider 接口一致的类，从 SymbolRegistry 获取合约列表。

支持的方法:
    - instruments(market, filter_pipe) -> dict/list
    - list_instruments(market, instruments_type) -> list[str]
"""

from __future__ import annotations

from typing import Any, Optional, Union

from ..registry.symbol_registry import SymbolRegistry
from ..models.enums import MarketType


class DataCoreInstrumentProvider:
    """Qlib 风格的 InstrumentProvider，使用 SymbolRegistry 获取合约列表。

    接口与 Qlib 的 InstrumentProvider 保持一致。

    Attributes:
        registry: SymbolRegistry 实例
    """

    def __init__(self, registry: Optional[SymbolRegistry] = None):
        self._registry = registry or SymbolRegistry()

    @property
    def registry(self) -> SymbolRegistry:
        return self._registry

    def instruments(
        self,
        market: Union[str, MarketType, None] = None,
        filter_pipe: Any = None,
    ) -> Union[dict, list]:
        """获取合约列表（兼容 Qlib 接口）。

        Args:
            market: 市场类型，如 "futures"、"stock"、"all"
            filter_pipe: 过滤管道（兼容参数，暂不支持）

        Returns:
            合约信息字典或列表
        """
        if market is None or market == "all":
            entries = self._registry.list_all()
        elif isinstance(market, MarketType):
            entries = self._registry.list_by_market(market)
        else:
            market_str = str(market).lower()
            try:
                mkt = MarketType(market_str)
                entries = self._registry.list_by_market(mkt)
            except ValueError:
                entries = self._registry.list_all()

        result = {}
        for entry in entries:
            result[entry.symbol] = {
                "name": entry.name,
                "market": entry.market.value if hasattr(entry.market, "value") else str(entry.market),
                "sector": entry.sector,
                "is_active": entry.is_active,
            }

        return result

    def list_instruments(
        self,
        market: Union[str, MarketType, None] = None,
        instruments_type: str = "all",
    ) -> list[str]:
        """列出合约代码。

        Args:
            market: 市场类型
            instruments_type: 合约类型（兼容参数，如 "Stock"、"Index" 等）

        Returns:
            合约代码列表
        """
        data = self.instruments(market=market)
        return sorted(list(data.keys()))

    def get_instrument(
        self,
        instrument: str,
        market: Union[str, MarketType, None] = None,
    ) -> Optional[dict]:
        """获取单个合约的信息。

        Args:
            instrument: 合约代码
            market: 市场类型（可选）

        Returns:
            合约信息字典，不存在则返回 None
        """
        entry = self._registry.resolve(instrument)
        if entry is None:
            return None

        if market is not None:
            if isinstance(market, MarketType):
                if entry.market != market:
                    return None
            else:
                try:
                    mkt = MarketType(str(market).lower())
                    if entry.market != mkt:
                        return None
                except ValueError:
                    pass

        return {
            "symbol": entry.symbol,
            "name": entry.name,
            "market": entry.market.value if hasattr(entry.market, "value") else str(entry.market),
            "sector": entry.sector,
            "is_active": entry.is_active,
        }

    def is_instrument(
        self,
        instrument: str,
        market: Union[str, MarketType, None] = None,
    ) -> bool:
        """判断合约是否存在。

        Args:
            instrument: 合约代码
            market: 市场类型（可选）

        Returns:
            True 表示存在
        """
        return self.get_instrument(instrument, market=market) is not None

    def add_instrument(
        self,
        instrument: str,
        name: str = "",
        market: Union[str, MarketType] = MarketType.FUTURES,
        sector: str = "",
        is_active: bool = True,
    ) -> None:
        """添加合约。

        Args:
            instrument: 合约代码
            name: 合约名称
            market: 市场类型
            sector: 行业/板块
            is_active: 是否活跃
        """
        if isinstance(market, str):
            market = MarketType(market.lower())

        self._registry.register(
            symbol=instrument,
            name=name,
            market=market,
            sector=sector,
            is_active=is_active,
        )

    def __repr__(self) -> str:
        count = len(self._registry.list_all())
        return f"<DataCoreInstrumentProvider instruments={count}>"
