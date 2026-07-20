"""交易日历对齐 — 周线/月线的日期边界处理。

处理周线（周一为起始日）、月线（自然月）等周期的日期对齐。
"""

from __future__ import annotations

import pandas as pd


def align_to_week_start(
    index: pd.DatetimeIndex,
    week_start: int = 0,
) -> pd.DatetimeIndex:
    """将日期索引对齐到周起始日。

    Args:
        index: datetime 索引
        week_start: 一周的起始日，0=周一，1=周二，...，6=周日

    Returns:
        对齐到周起始日的 DatetimeIndex
    """
    if len(index) == 0:
        return index

    dayofweek = index.dayofweek
    offset = (dayofweek - week_start) % 7
    aligned = index - pd.to_timedelta(offset, unit="D")
    aligned = aligned.normalize()
    return pd.DatetimeIndex(aligned)


def align_to_month_start(
    index: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    """将日期索引对齐到月初。

    Args:
        index: datetime 索引

    Returns:
        对齐到月初的 DatetimeIndex
    """
    if len(index) == 0:
        return index
    return pd.DatetimeIndex(index.to_period("M").to_timestamp("D"))


def align_to_quarter_start(
    index: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    """将日期索引对齐到季初。

    Args:
        index: datetime 索引

    Returns:
        对齐到季初的 DatetimeIndex
    """
    if len(index) == 0:
        return index
    return pd.DatetimeIndex(index.to_period("Q").to_timestamp("D"))


def is_trading_day(
    date: pd.Timestamp,
    holidays: set | None = None,
) -> bool:
    """判断是否为交易日。

    简单实现：周一到周五且不在节假日列表中。

    Args:
        date: 日期
        holidays: 节假日集合，默认为空

    Returns:
        True 表示是交易日
    """
    if holidays is None:
        holidays = set()

    if date.dayofweek >= 5:
        return False

    return date.normalize() not in holidays


def get_trading_days_in_range(
    start: pd.Timestamp,
    end: pd.Timestamp,
    holidays: set | None = None,
) -> pd.DatetimeIndex:
    """获取指定日期范围内的所有交易日。

    Args:
        start: 起始日期
        end: 结束日期
        holidays: 节假日集合

    Returns:
        交易日 DatetimeIndex
    """
    all_days = pd.date_range(start=start, end=end, freq="D")
    trading_days = [d for d in all_days if is_trading_day(d, holidays)]
    return pd.DatetimeIndex(trading_days)


def weekly_ohlcv(
    df: pd.DataFrame,
    week_start: int = 0,
) -> pd.DataFrame:
    """将日 K 线聚合为周 K 线，自定义周起始日。

    Args:
        df: 日 K 线 DataFrame，datetime 索引
        week_start: 周起始日，0=周一

    Returns:
        周 K 线 DataFrame
    """
    if df.empty:
        return df.copy()

    week_offset = pd.offsets.Week(weekday=week_start)
    result = df.resample(week_offset, label="left", closed="left").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "amount": "sum",
            "open_interest": "last",
        }
    )

    return result.dropna(how="all")


def monthly_ohlcv(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """将日 K 线聚合为月 K 线（自然月）。

    Args:
        df: 日 K 线 DataFrame，datetime 索引

    Returns:
        月 K 线 DataFrame
    """
    if df.empty:
        return df.copy()

    result = df.resample("1ME", label="left", closed="left").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "amount": "sum",
            "open_interest": "last",
        }
    )

    return result.dropna(how="all")


def count_bars_per_period(
    index: pd.DatetimeIndex,
    freq: str,
) -> pd.Series:
    """统计每个周期内的 K 线数量。

    Args:
        index: K 线的 datetime 索引
        freq: 目标周期频率

    Returns:
        每个周期的 K 线数量 Series
    """
    if len(index) == 0:
        return pd.Series(dtype="int64")

    s = pd.Series(1, index=index)
    return s.resample(freq, label="left", closed="left").sum()


__all__ = [
    "align_to_week_start",
    "align_to_month_start",
    "align_to_quarter_start",
    "is_trading_day",
    "get_trading_days_in_range",
    "weekly_ohlcv",
    "monthly_ohlcv",
    "count_bars_per_period",
]
