"""统一数据载荷信封。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .enums import DataType, MarketType, SourceGrade


@dataclass
class DataPayload:
    """统一数据载荷信封。"""
    symbol: str
    data_type: DataType
    market: MarketType
    data: Any = None
    source: str = ""
    grade: SourceGrade = SourceGrade.UNAVAILABLE
    collected_at: float = 0.0
    meta: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.grade != SourceGrade.UNAVAILABLE
