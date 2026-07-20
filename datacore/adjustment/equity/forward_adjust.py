"""股票前复权算法。

前复权（Forward Adjustment / 向前复权）:
    以最新价格为基准，保持当前价格不变，将历史价格向下调整。
    即「后段对齐前段」不成立——前复权是让最新价不变，历史价调整。

价格调整公式:
    调整价 = 原始价 / 累计复权因子

    （其中累计复权因子从最新日期向历史日期累积，
      最新日期因子为 1，越远越大）

成交量/成交额不调整（股数变化已体现在价格中，量额保持原值）。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .dividend_calendar import DividendCalendar


PRICE_COLS = ["open", "high", "low", "close"]
VOLUME_COLS = ["volume", "amount", "open_interest"]


def forward_adjust(
    kline: pd.DataFrame,
    dividend_info: Optional[list[dict]] = None,
    date_col: str = "date",
) -> pd.DataFrame:
    """对股票 K 线数据执行前复权。

    前复权: 保持最新价格不变，历史价格按复权因子向下调整。
    调整列: open, high, low, close
    不调整: volume, amount, open_interest

    Args:
        kline: K 线 DataFrame，需包含 date/datetime, open, high, low, close 等列
        dividend_info: 分红送股信息列表，每个元素为 dict，字段见 DividendEvent
        date_col: 日期列名，默认为 "date"

    Returns:
        前复权后的 K 线 DataFrame（副本，不修改原数据）

    Raises:
        ValueError: kline 缺少必要列时抛出
    """
    _validate_kline_columns(kline, date_col)

    if dividend_info is None or len(dividend_info) == 0:
        return kline.copy()

    result = kline.copy()
    cal = DividendCalendar.from_list(dividend_info)

    dates = result[date_col]
    pre_close = result["close"].shift(1).values

    cum_factor = cal.build_factor_series(dates, pre_close_series=pre_close)

    last_factor = cum_factor.iloc[-1] if len(cum_factor) > 0 else 1.0
    if last_factor == 0:
        last_factor = 1.0

    forward_factor = cum_factor / last_factor

    for col in PRICE_COLS:
        if col in result.columns:
            result[col] = result[col].values / forward_factor.values

    return result


def _validate_kline_columns(kline: pd.DataFrame, date_col: str) -> None:
    """验证 K 线 DataFrame 包含必要的列。

    Args:
        kline: K 线 DataFrame
        date_col: 日期列名

    Raises:
        ValueError: 缺少必要列时抛出
    """
    if date_col not in kline.columns and "datetime" not in kline.columns:
        raise ValueError(
            f"K 线数据必须包含日期列 '{date_col}' 或 'datetime'"
        )
    for col in ["open", "high", "low", "close"]:
        if col not in kline.columns:
            raise ValueError(f"K 线数据缺少必要列: '{col}'")


__all__ = ["forward_adjust"]
