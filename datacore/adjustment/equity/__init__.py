"""股票复权子模块。

提供股票前复权、后复权和除权除息日历功能。

主要接口:
- forward_adjust(): 前复权
- backward_adjust(): 后复权
- DividendEvent: 单个除权除息事件
- DividendCalendar: 除权除息日历

使用方式:
    from datacore.adjustment.equity import forward_adjust, backward_adjust
    result = forward_adjust(kline_df, dividend_info=[...])
"""

from __future__ import annotations

from .dividend_calendar import DividendCalendar, DividendEvent
from .forward_adjust import forward_adjust
from .backward_adjust import backward_adjust


__all__ = [
    "forward_adjust",
    "backward_adjust",
    "DividendEvent",
    "DividendCalendar",
]
