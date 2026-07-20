"""OHLCV K 线重采样核心。

基于 pandas resample 实现 OHLCV 数据的周期转换，支持分钟线、日线、周线、月线。
"""

from __future__ import annotations

import pandas as pd

from datacore.resampler.registry import get_pandas_freq, is_finer


def resample_ohlcv(
    df: pd.DataFrame,
    target_period: str,
    source_period: str,
) -> pd.DataFrame:
    """重采样 OHLCV K 线数据。

    将源周期的 K 线数据重采样为目标周期。只支持从细粒度到粗粒度的转换。

    聚合规则:
        - open: first
        - high: max
        - low: min
        - close: last
        - volume: sum
        - amount: sum
        - open_interest: last

    Args:
        df: 输入 DataFrame，必须包含 datetime 索引，以及 open/high/low/close 列
            可选列: volume, amount, open_interest
        target_period: 目标周期，如 "5m", "15m", "daily", "weekly" 等
        source_period: 源周期，如 "1m", "5m", "daily" 等

    Returns:
        重采样后的 DataFrame，保持原有列名

    Raises:
        ValueError: 源周期比目标周期更粗（不支持反向重采样）
        TypeError: 输入不是 DataFrame 或索引不是 datetime 类型
        KeyError: 缺少必要的 OHLC 列
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df 必须是 pandas DataFrame")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("df 的索引必须是 DatetimeIndex")

    if df.empty:
        return df.copy()

    if not is_finer(source_period, target_period):
        raise ValueError(
            f"只能从细粒度重采样到粗粒度，源周期 {source_period} 不比目标周期 {target_period} 更细"
        )

    required_cols = ["open", "high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"缺少必要列: {col}")

    target_freq = get_pandas_freq(target_period)

    agg_dict = _build_agg_dict(df.columns)

    result = df.resample(target_freq, label="left", closed="left").agg(agg_dict)

    result = result.dropna(how="all")

    return result


def _build_agg_dict(columns: pd.Index) -> dict:
    """根据可用列构建聚合函数字典。

    Args:
        columns: DataFrame 的列名

    Returns:
        列名 -> 聚合函数的字典
    """
    agg_map = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "amount": "sum",
        "open_interest": "last",
        "settlement": "last",
    }

    agg_dict = {}
    for col in columns:
        if col in agg_map:
            agg_dict[col] = agg_map[col]

    return agg_dict


def resample_minute_to_minute(
    df: pd.DataFrame,
    target_period: str,
) -> pd.DataFrame:
    """分钟线之间的重采样（1m → 5m/15m/30m/60m 等）。

    Args:
        df: 输入 DataFrame，datetime 索引
        target_period: 目标分钟周期，如 "5m", "15m", "30m", "60m"

    Returns:
        重采样后的 DataFrame
    """
    target_freq = get_pandas_freq(target_period)
    agg_dict = _build_agg_dict(df.columns)
    result = df.resample(target_freq, label="left", closed="left").agg(agg_dict)
    return result.dropna(how="all")


def resample_daily_to_daily(
    df: pd.DataFrame,
    target_period: str,
) -> pd.DataFrame:
    """日线级别的重采样（daily → weekly/monthly）。

    Args:
        df: 输入 DataFrame，datetime 索引
        target_period: 目标周期，"weekly" 或 "monthly"

    Returns:
        重采样后的 DataFrame
    """
    target_freq = get_pandas_freq(target_period)
    agg_dict = _build_agg_dict(df.columns)
    result = df.resample(target_freq, label="left", closed="left").agg(agg_dict)
    return result.dropna(how="all")


__all__ = [
    "resample_ohlcv",
    "resample_minute_to_minute",
    "resample_daily_to_daily",
]
