"""期货专用数据模型 — 合约链、期限结构、基差、持仓等。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datacore.models.ohlcv import KlineData


@dataclass
class ContractInfo:
    """合约基本信息。"""
    code: str
    month: str
    is_main: bool = False
    open_interest: float = 0.0
    last_price: float = 0.0


@dataclass
class ContractChain:
    """期货合约链 — 同一品种的多个合约 K线数据。"""
    symbol: str
    contracts: list[str] = field(default_factory=list)
    klines: dict[str, KlineData] = field(default_factory=dict)

    @property
    def main_contract(self) -> Optional[str]:
        """主力合约代码。"""
        return self.contracts[0] if self.contracts else None


@dataclass
class TermStructurePoint:
    """期限结构上的一个点。"""
    contract: str
    month: str
    price: float
    yield_from_front: float = 0.0
    yield_annual: float = 0.0


@dataclass
class TermStructure:
    """期货期限结构 — 完整的合约价格曲线。"""
    symbol: str
    points: list[TermStructurePoint] = field(default_factory=list)
    snapshot_at: float = 0.0

    @property
    def is_contango(self) -> bool:
        """是否为升水结构（远期 > 近期）。"""
        if len(self.points) < 2:
            return False
        return self.points[-1].price > self.points[0].price

    @property
    def slope(self) -> float:
        """期限结构斜率（最远-最近）/最近。"""
        if len(self.points) < 2 or self.points[0].price == 0:
            return 0.0
        return (self.points[-1].price - self.points[0].price) / self.points[0].price


@dataclass
class SpreadData:
    """跨期价差数据。"""
    symbol: str
    near_contract: str
    far_contract: str
    spread_series: list[dict] = field(default_factory=list)

    @property
    def latest_spread(self) -> float:
        """最新价差。"""
        if not self.spread_series:
            return 0.0
        return self.spread_series[-1].get("spread", 0.0)


@dataclass
class BasisData:
    """基差数据。"""
    symbol: str
    spot_price: float = 0.0
    futures_price: float = 0.0
    basis: float = 0.0
    basis_rate: float = 0.0
    basis_pct: float = 0.0
    spot_source: str = ""
    futures_source: str = ""


@dataclass
class PositionRankItem:
    """持仓排名条目。"""
    rank: int
    broker: str
    volume: float
    volume_change: float
    direction: str


@dataclass
class PositionRankData:
    """持仓排名数据。"""
    symbol: str
    contract: str
    date: str
    long_ranks: list[PositionRankItem] = field(default_factory=list)
    short_ranks: list[PositionRankItem] = field(default_factory=list)
    volume_ranks: list[PositionRankItem] = field(default_factory=list)


@dataclass
class WarehouseReceiptData:
    """仓单数据。"""
    symbol: str
    date: str
    total_receipts: float = 0.0
    change: float = 0.0
    inventory_pct: float = 0.0
    warehouse_detail: list[dict] = field(default_factory=list)
