"""Qlib/RD-Agent 适配器 — 让 Data-Core 可以作为 Qlib 的数据提供方。

提供与 Qlib DataProvider/CalendarProvider/InstrumentProvider 接口一致的类，
内部使用 AsyncDataProvider 获取数据，将结果组织为 Qlib 期望的格式。

使用方式:
    from datacore.qlib_adapter import (
        DataCoreQLibProvider,
        DataCoreCalendarProvider,
        DataCoreInstrumentProvider,
    )

    provider = DataCoreQLibProvider()
    df = provider.features(
        instruments=["RB", "CU"],
        fields=["$close", "$volume"],
        start_time="2024-01-01",
        end_time="2024-12-31",
        freq="day",
    )
"""

from __future__ import annotations

from .provider import DataCoreQLibProvider
from .calendar import DataCoreCalendarProvider
from .instrument import DataCoreInstrumentProvider

__all__ = [
    "DataCoreQLibProvider",
    "DataCoreCalendarProvider",
    "DataCoreInstrumentProvider",
]
