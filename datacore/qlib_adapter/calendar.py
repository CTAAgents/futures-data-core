"""DataCoreCalendarProvider — Qlib 风格的 CalendarProvider 适配器。

提供与 Qlib CalendarProvider 接口一致的类，从 Data-Core 获取交易日历。

支持的方法:
    - calendar(start_time, end_time, freq) -> pd.DatetimeIndex
    - is_trading_day(date, freq) -> bool
    - trading_day_index(date, freq) -> int
    - add_trading_days(date, days, freq) -> pd.Timestamp
"""

from __future__ import annotations

from typing import Union

import pandas as pd


_FREQ_PERIOD_MAP = {
    "day": "daily",
    "1d": "daily",
    "daily": "daily",
    "week": "weekly",
    "1w": "weekly",
    "weekly": "weekly",
    "month": "monthly",
    "1m": "monthly",
    "monthly": "monthly",
}


class DataCoreCalendarProvider:
    """Qlib 风格的 CalendarProvider，使用 Data-Core 的交易日历。

    接口与 Qlib 的 CalendarProvider 保持一致。

    Attributes:
        holidays: 节假日集合
        weekmask: 周掩码（默认周一到周五）
    """

    def __init__(
        self,
        holidays: Union[set, list, None] = None,
        weekmask: str | None = None,
    ):
        self._holidays: set[pd.Timestamp] = set()
        if holidays is not None:
            self._holidays = {pd.Timestamp(d) for d in holidays}

        self._weekmask = weekmask or "Mon Tue Wed Thu Fri"

    @property
    def holidays(self) -> set[pd.Timestamp]:
        return self._holidays

    @property
    def weekmask(self) -> str:
        return self._weekmask

    def calendar(
        self,
        start_time: Union[str, pd.Timestamp, None] = None,
        end_time: Union[str, pd.Timestamp, None] = None,
        freq: str = "day",
    ) -> pd.DatetimeIndex:
        """获取指定时间范围内的交易日历。

        Args:
            start_time: 开始时间
            end_time: 结束时间
            freq: 频率，"day" 表示日线

        Returns:
            交易日 DatetimeIndex
        """
        if freq not in ("day", "daily", "1d"):
            return self._calendar_minute(start_time, end_time, freq)

        if start_time is None:
            start_time = pd.Timestamp("2000-01-01")
        if end_time is None:
            end_time = pd.Timestamp.now()

        start = pd.Timestamp(start_time).normalize()
        end = pd.Timestamp(end_time).normalize()

        if start > end:
            return pd.DatetimeIndex([])

        all_days = pd.date_range(start=start, end=end, freq="B")
        if self._holidays:
            all_days = all_days.difference(pd.DatetimeIndex(sorted(self._holidays)))

        return all_days.sort_values()

    def _calendar_minute(
        self,
        start_time: Union[str, pd.Timestamp, None],
        end_time: Union[str, pd.Timestamp, None],
        freq: str,
    ) -> pd.DatetimeIndex:
        """分钟级别的交易日历（简化实现）。"""
        if start_time is None:
            start_time = pd.Timestamp("2000-01-01")
        if end_time is None:
            end_time = pd.Timestamp.now()

        start = pd.Timestamp(start_time)
        end = pd.Timestamp(end_time)

        if start > end:
            return pd.DatetimeIndex([])

        freq_map = {
            "1min": "1min",
            "1m": "1min",
            "5min": "5min",
            "5m": "5min",
            "15min": "15min",
            "15m": "15min",
            "30min": "30min",
            "30m": "30min",
            "60min": "60min",
            "60m": "60min",
            "1h": "60min",
        }
        pandas_freq = freq_map.get(freq, freq)

        all_times = pd.date_range(start=start, end=end, freq=pandas_freq)

        if self._holidays:
            holiday_dates = {h.normalize() for h in self._holidays}
            mask = ~all_times.normalize().isin(holiday_dates)
            all_times = all_times[mask]

        weekday_mask = all_times.dayofweek < 5
        all_times = all_times[weekday_mask]

        return all_times

    def is_trading_day(
        self,
        date: Union[str, pd.Timestamp],
        freq: str = "day",
    ) -> bool:
        """判断是否为交易日。

        Args:
            date: 日期
            freq: 频率

        Returns:
            True 表示是交易日
        """
        d = pd.Timestamp(date).normalize()

        if d.weekday() >= 5:
            return False

        if d in self._holidays:
            return False

        return True

    def trading_day_index(
        self,
        date: Union[str, pd.Timestamp],
        freq: str = "day",
    ) -> int:
        """获取日期在交易日历中的索引。

        Args:
            date: 日期
            freq: 频率

        Returns:
            索引值
        """
        cal = self.calendar(end_time=date, freq=freq)
        d = pd.Timestamp(date).normalize() if freq in ("day", "daily", "1d") else pd.Timestamp(date)
        if d not in cal:
            raise ValueError(f"{date} 不是交易日")
        return cal.get_loc(d)

    def add_trading_days(
        self,
        date: Union[str, pd.Timestamp],
        days: int,
        freq: str = "day",
    ) -> pd.Timestamp:
        """添加 N 个交易日。

        Args:
            date: 起始日期
            days: 添加的天数（负数表示往前）
            freq: 频率

        Returns:
            计算后的日期
        """
        d = pd.Timestamp(date)
        direction = 1 if days > 0 else -1
        remaining = abs(days)
        current = d

        while remaining > 0:
            current += pd.Timedelta(days=direction)
            if self.is_trading_day(current, freq=freq):
                remaining -= 1

        return current

    def __repr__(self) -> str:
        return (
            f"<DataCoreCalendarProvider "
            f"holidays={len(self._holidays)} "
            f"weekmask='{self._weekmask}'>"
        )
