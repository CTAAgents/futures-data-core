"""成交量/持仓量聚合工具。

提供成交量 (volume)、成交额 (amount)、持仓量 (open_interest) 等
在周期转换时的聚合计算。
"""

from __future__ import annotations

import pandas as pd


def aggregate_volume(
    series: pd.Series,
    target_freq: str,
    method: str = "sum",
) -> pd.Series:
    """聚合成交量数据。

    Args:
        series: 成交量 Series，datetime 索引
        target_freq: 目标频率，pandas 频率字符串
        method: 聚合方法，默认为 "sum"

    Returns:
        聚合后的成交量 Series
    """
    if series.empty:
        return series.copy()

    result = series.resample(target_freq, label="left", closed="left").agg(method)
    return result.dropna()


def aggregate_amount(
    series: pd.Series,
    target_freq: str,
    method: str = "sum",
) -> pd.Series:
    """聚合成交额数据。

    Args:
        series: 成交额 Series，datetime 索引
        target_freq: 目标频率，pandas 频率字符串
        method: 聚合方法，默认为 "sum"

    Returns:
        聚合后的成交额 Series
    """
    if series.empty:
        return series.copy()

    result = series.resample(target_freq, label="left", closed="left").agg(method)
    return result.dropna()


def aggregate_open_interest(
    series: pd.Series,
    target_freq: str,
    method: str = "last",
) -> pd.Series:
    """聚合持仓量数据。

    持仓量采用期末值，即取每个周期最后一根 K 线的持仓量。

    Args:
        series: 持仓量 Series，datetime 索引
        target_freq: 目标频率，pandas 频率字符串
        method: 聚合方法，默认为 "last"（期末值）

    Returns:
        聚合后的持仓量 Series
    """
    if series.empty:
        return series.copy()

    result = series.resample(target_freq, label="left", closed="left").agg(method)
    return result.dropna()


def compute_volume_profile(
    df: pd.DataFrame,
    target_freq: str,
) -> pd.DataFrame:
    """计算成交量分布特征。

    在重采样的同时，计算成交量的附加统计信息：
    - volume_avg: 平均成交量
    - volume_max: 最大成交量
    - volume_min: 最小成交量
    - volume_std: 成交量标准差

    Args:
        df: 输入 DataFrame，必须包含 volume 列和 datetime 索引
        target_freq: 目标频率

    Returns:
        包含成交量统计特征的 DataFrame
    """
    if df.empty or "volume" not in df.columns:
        return pd.DataFrame()

    result = df["volume"].resample(
        target_freq, label="left", closed="left"
    ).agg(["sum", "mean", "max", "min", "std"])

    result.columns = ["volume", "volume_avg", "volume_max", "volume_min", "volume_std"]
    return result.dropna(how="all")


def turnover_rate(
    volume: pd.Series,
    total_shares: float,
) -> pd.Series:
    """计算换手率。

    Args:
        volume: 成交量 Series
        total_shares: 总股本/流通股数量

    Returns:
        换手率 Series
    """
    if total_shares <= 0:
        raise ValueError("total_shares 必须大于 0")
    return volume / total_shares


def amount_to_volume(
    amount: pd.Series,
    price: pd.Series,
) -> pd.Series:
    """根据成交额和价格估算成交量。

    Args:
        amount: 成交额 Series
        price: 价格 Series（通常用 close 或 vwap）

    Returns:
        估算的成交量 Series
    """
    return amount / price


__all__ = [
    "aggregate_volume",
    "aggregate_amount",
    "aggregate_open_interest",
    "compute_volume_profile",
    "turnover_rate",
    "amount_to_volume",
]
