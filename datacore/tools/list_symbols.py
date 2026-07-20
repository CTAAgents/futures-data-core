"""DataCoreListSymbolsTool - 品种列表工具。"""

from __future__ import annotations

from typing import Any, Optional

from .base import DataCoreBaseTool


class DataCoreListSymbolsTool(DataCoreBaseTool):
    """获取支持的品种列表。

    可按市场类型筛选，返回品种代码、名称、所属板块等信息。
    """

    name = "datacore_list_symbols"
    description = (
        "获取支持的品种列表。可按市场类型筛选。"
        "参数：market (str, 可选) - 市场类型，'futures'/'stock'/'etf'/'cb'/'reit'，默认返回全部；"
        "sector (str, 可选) - 板块名称，如 '黑色系'、'能源链' 等；"
        "active_only (bool, 可选) - 仅返回活跃品种，默认 True"
    )

    def _run(self, market: Optional[str] = None, sector: Optional[str] = None,
             active_only: bool = True, **kwargs: Any) -> dict[str, Any]:
        from ..registry.symbol_registry import SymbolRegistry
        from ..models.enums import MarketType

        registry = SymbolRegistry()

        if market:
            try:
                market_type = MarketType(market)
                entries = registry.list_by_market(market_type)
            except ValueError:
                return {
                    "success": False,
                    "error": f"未知市场类型: {market}",
                    "valid_markets": [m.value for m in MarketType],
                }
        else:
            entries = registry.list_all()

        if active_only:
            entries = [e for e in entries if e.is_active]

        if sector:
            entries = [e for e in entries if e.sector == sector]

        symbols = [
            {
                "symbol": e.symbol,
                "name": e.name,
                "market": e.market.value if hasattr(e.market, "value") else str(e.market),
                "sector": e.sector,
                "active": e.is_active,
            }
            for e in entries
        ]

        return {
            "success": True,
            "total": len(symbols),
            "market": market,
            "sector": sector,
            "symbols": symbols,
        }
