"""auto 模式 — 自动选择最合适的重采样周期。

根据数据量、时间间隔自动推断源周期并选择最合适的目标周期。
"""

from __future__ import annotations

import pandas as pd

from datacore.resampler.registry import (
    list_periods,
)


def infer_source_period(df: pd.DataFrame) -> str | None:
    """根据数据索引推断源数据周期。

    通过计算索引中最常见的时间间隔来推断周期。

    Args:
        df: 输入 DataFrame，datetime 索引

    Returns:
        推断出的周期名称，无法推断时返回 None
    """
    if df.empty or len(df) < 2:
        return None

    if not isinstance(df.index, pd.DatetimeIndex):
        return None

    diffs = df.index.to_series().diff().dropna()
    if len(diffs) == 0:
        return None

    mode_diff = diffs.mode()
    if len(mode_diff) == 0:
        return None

    typical_interval = mode_diff.iloc[0]

    total_seconds = typical_interval.total_seconds()

    if 55 <= total_seconds <= 65:
        return "1m"
    elif 290 <= total_seconds <= 310:
        return "5m"
    elif 890 <= total_seconds <= 910:
        return "15m"
    elif 1790 <= total_seconds <= 1810:
        return "30m"
    elif 3590 <= total_seconds <= 3610:
        return "60m"
    elif 82800 <= total_seconds <= 90000:
        return "daily"
    elif total_seconds > 86400 * 5 and total_seconds < 86400 * 9:
        return "weekly"
    elif total_seconds > 86400 * 25 and total_seconds < 86400 * 35:
        return "monthly"

    return None


def auto_select_period(
    df: pd.DataFrame,
    target_bars: int = 200,
) -> str:
    """自动选择最合适的目标周期。

    优先选择数据量接近 target_bars 的最细粒度周期。

    Args:
        df: 输入 DataFrame，datetime 索引
        target_bars: 目标 K 线数量，默认 200

    Returns:
        推荐的目标周期名称
    """
    if df.empty:
        return "daily"

    source_period = infer_source_period(df)
    if source_period is None:
        return "daily"

    n_bars = len(df)

    all_periods = list_periods()

    source_idx = all_periods.index(source_period)

    candidates = []
    for i in range(source_idx, len(all_periods)):
        period = all_periods[i]
        ratio = _period_ratio(source_period, period)
        estimated_bars = max(1, n_bars // ratio)
        candidates.append((period, estimated_bars))

    if not candidates:
        return source_period

    best_period = candidates[0][0]
    best_diff = abs(candidates[0][1] - target_bars)

    for period, est_bars in candidates:
        diff = abs(est_bars - target_bars)
        if diff < best_diff:
            best_diff = diff
            best_period = period

    return best_period


def _period_ratio(source: str, target: str) -> int:
    """计算目标周期相对于源周期的倍数。

    粗略估算，用于估计重采样后的 K 线数量。

    Args:
        source: 源周期
        target: 目标周期

    Returns:
        目标周期包含多少个源周期
    """
    minute_values = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "60m": 60,
    }

    daily_values = {
        "daily": 1,
        "weekly": 5,
        "monthly": 22,
    }

    if source in minute_values and target in minute_values:
        return minute_values[target] // minute_values[source]

    if source in daily_values and target in daily_values:
        return daily_values[target] // daily_values[source]

    if source in minute_values and target in daily_values:
        minutes_per_day = 240
        source_minutes = minute_values[source]
        target_days = daily_values[target]
        return (minutes_per_day // source_minutes) * target_days

    return 1


def suggest_periods(
    df: pd.DataFrame,
) -> list[tuple[str, int]]:
    """建议可用的周期及预估 K 线数量。

    Args:
        df: 输入 DataFrame

    Returns:
        (周期名称, 预估K线数) 的列表，按粒度从细到粗排序
    """
    if df.empty:
        return []

    source_period = infer_source_period(df)
    if source_period is None:
        return []

    n_bars = len(df)
    all_periods = list_periods()
    source_idx = all_periods.index(source_period)

    result = []
    for i in range(source_idx, len(all_periods)):
        period = all_periods[i]
        ratio = _period_ratio(source_period, period)
        estimated_bars = max(1, n_bars // ratio)
        result.append((period, estimated_bars))

    return result


__all__ = [
    "infer_source_period",
    "auto_select_period",
    "suggest_periods",
]
