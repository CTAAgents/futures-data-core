"""周期转换引擎 — K 线重采样模块。

提供从细粒度到粗粒度的 K 线周期转换，支持分钟线、日线、周线、月线，
以及 auto 模式自动选择最合适的周期。

主要接口:
    resample_kline(df, target_period, source_period) -> DataFrame

支持的周期:
    - 分钟线: "1m", "5m", "15m", "30m", "60m"
    - 日线: "daily"
    - 周线: "weekly"
    - 月线: "monthly"
    - 自动: "auto"

使用方式:
    from datacore.resampler import resample_kline

    # 将 1min K 线重采样为 5min
    result = resample_kline(df, target_period="5m", source_period="1m")

    # 将日线重采样为周线
    result = resample_kline(df, target_period="weekly", source_period="daily")

    # auto 模式：从可用数据自动选最合适的周期
    result = resample_kline(df, target_period="auto")
"""

from __future__ import annotations

import pandas as pd

from datacore.resampler.ohlcv import resample_ohlcv
from datacore.resampler.registry import (
    validate_period,
    is_finer,
)
from datacore.resampler.auto import infer_source_period, auto_select_period

__all__ = [
    "resample_ohlcv",
    "resample_kline",
    "validate_period",
    "is_finer",
    "infer_source_period",
    "auto_select_period",
]


def resample_kline(
    df: pd.DataFrame,
    target_period: str,
    source_period: str | None = None,
) -> pd.DataFrame:
    """K 线周期转换（重采样）。

    将源周期的 K 线数据重采样为目标周期。只支持从细粒度到粗粒度的转换。

    聚合规则:
        - open: first（周期内第一个开盘价）
        - high: max（周期内最高价）
        - low: min（周期内最低价）
        - close: last（周期内最后一个收盘价）
        - volume: sum（周期内总成交量）
        - amount: sum（周期内总成交额）
        - open_interest: last（周期末持仓量）

    Args:
        df: 输入 DataFrame，必须包含 datetime 索引，以及 open/high/low/close 列
            可选列: volume, amount, open_interest
        target_period: 目标周期，如 "5m", "15m", "daily", "weekly", "auto" 等
        source_period: 源周期，如 "1m", "5m", "daily" 等
            为 None 或 target_period 为 "auto" 时自动推断

    Returns:
        重采样后的 DataFrame，保持原有列名和 datetime 索引

    Raises:
        ValueError:
            - 源周期比目标周期更粗（不支持反向重采样）
            - 不支持的周期名称
            - auto 模式下无法推断源周期
        TypeError: 输入不是 DataFrame 或索引不是 datetime 类型
        KeyError: 缺少必要的 OHLC 列

    Examples:
        >>> # 1min -> 5min
        >>> result = resample_kline(df_1m, "5m", "1m")

        >>> # daily -> weekly
        >>> result = resample_kline(df_daily, "weekly", "daily")

        >>> # auto 模式
        >>> result = resample_kline(df, "auto")
    """
    if target_period == "auto":
        return _resample_auto(df)

    validate_period(target_period)

    if source_period is None:
        source_period = infer_source_period(df)
        if source_period is None:
            raise ValueError(
                "无法自动推断源周期，请显式指定 source_period 参数"
            )
    else:
        validate_period(source_period)

    if not is_finer(source_period, target_period):
        raise ValueError(
            f"只能从细粒度重采样到粗粒度："
            f"源周期 {source_period} 不比目标周期 {target_period} 更细"
        )

    return resample_ohlcv(df, target_period, source_period)


def _resample_auto(df: pd.DataFrame) -> pd.DataFrame:
    """auto 模式：自动选择最合适的周期并重采样。

    Args:
        df: 输入 DataFrame

    Returns:
        重采样后的 DataFrame
    """
    if df.empty:
        return df.copy()

    source_period = infer_source_period(df)
    if source_period is None:
        raise ValueError(
            "auto 模式无法推断源周期，请显式指定 source_period 参数"
        )

    target_period = auto_select_period(df)

    if target_period == source_period:
        return df.copy()

    return resample_ohlcv(df, target_period, source_period)


__all__ = [
    "resample_kline",
]
