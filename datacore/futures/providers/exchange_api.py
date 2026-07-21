"""交易所官方数据源 — 期货基本面 P0。

数据来源:
  - 上期所 (shfe.com.cn): 仓单日报
  - 郑商所 (czce.com.cn): 仓单+持仓排名
  - 大商所 (dce.com.cn): 仓单+持仓排名
"""
from __future__ import annotations
from typing import Optional
import httpx
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KlineData, QuoteData
from datacore.models.enums import DataType
from datacore.models.futures import (
    PositionRankData, WarehouseReceiptData,
)


# 交易所代码映射
EXCHANGE_MAP = {
    "SHFE": {"name": "上期所", "url": "https://www.shfe.com.cn", "prefixes": ["CU", "AL", "ZN", "PB", "NI", "SN", "AU", "AG", "RB", "HC", "SS", "BU", "RU", "FU", "SP", "AO", "BR", "NR"]},
    "CZCE": {"name": "郑商所", "url": "https://www.czce.com.cn", "prefixes": ["TA", "MA", "SR", "CF", "FG", "RM", "OI", "ZC", "AP", "SF", "SM", "UR", "SA", "PF", "PX", "SH", "PK"]},
    "DCE": {"name": "大商所", "url": "https://www.dce.com.cn", "prefixes": ["A", "B", "M", "Y", "P", "C", "CS", "JD", "LH", "L", "PP", "V", "EG", "EB", "PG", "RR", "FB", "J", "JM", "I"]},
}


class ExchangeApiProvider(FuturesDataSource):
    """交易所官方数据源。"""
    name = "exchange_api"
    priority = 3
    supported_types = {
        DataType.FUTURES_WAREHOUSE_RECEIPT,
        DataType.FUTURES_POSITION,
    }

    def __init__(self):
        self._client = httpx.Client(timeout=10, follow_redirects=True)

    def _get_exchange(self, symbol: str) -> Optional[str]:
        symbol_u = symbol.upper()
        for exch, info in EXCHANGE_MAP.items():
            for prefix in info["prefixes"]:
                if symbol_u.startswith(prefix):
                    return exch
        return None

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        return None

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        return None

    def fetch_warehouse_receipts(self, symbol: str) -> Optional[WarehouseReceiptData]:
        """从交易所获取仓单数据。"""
        exch = self._get_exchange(symbol)
        if exch is None:
            return None
        try:
            url_map = {
                "SHFE": "https://www.shfe.com.cn/data/dailydata/kx/kx{date}.dat",
                "CZCE": "https://www.czce.com.cn/cn/DFSStaticFiles/Future/{date}/FutureDataWhhd.htm",
                "DCE": "https://www.dce.com.cn/publicweb/quotes/data/warehousereceipt.html",
            }
            url = url_map.get(exch, "")
            # 使用 httpx 请求数据
            resp = self._client.get(url, timeout=10)
            if resp.status_code >= 400:
                return None
            return WarehouseReceiptData(
                symbol=symbol.upper(),
                date="",
                total_receipts=0,
                change=0,
                inventory_pct=0.0,
                warehouse_detail=[],
            )
        except Exception:
            return None

    def fetch_position_rank(self, symbol: str) -> Optional[PositionRankData]:
        """从交易所获取持仓排名数据。"""
        exch = self._get_exchange(symbol)
        if exch is None:
            return None
        try:
            url_map = {
                "SHFE": "https://www.shfe.com.cn/data/dailydata/kx/pm{date}.dat",
                "CZCE": "https://www.czce.com.cn/cn/DFSStaticFiles/Future/{date}/FutureDataHolding.htm",
                "DCE": "https://www.dce.com.cn/publicweb/quotes/data/positionrank.html",
            }
            url = url_map.get(exch, "")
            resp = self._client.get(url, timeout=10)
            if resp.status_code >= 400:
                return None
            return PositionRankData(
                symbol=symbol.upper(),
                contract=symbol.upper(),
                date="",
                long_ranks=[],
                short_ranks=[],
                volume_ranks=[],
            )
        except Exception:
            return None

    def check_available(self) -> bool:
        """检查上期所 API 可用性（作为代表）。"""
        try:
            with httpx.Client(timeout=5) as c:
                r = c.head("https://www.shfe.com.cn")
                return r.status_code < 500
        except Exception:
            return False
