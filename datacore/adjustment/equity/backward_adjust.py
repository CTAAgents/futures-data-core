"""股票后复权算法。

后复权（Backward Adjustment / 向后复权）:
    以最早日期价格为基准，保持初始价格不变，将后续价格向上调整。
    即「前段对齐后段」——历史价不变，最新价反映累计分红送股的价值。

价格调整公式:
    调整价 = 原始价 * 累计复权因子

    （其中累计复权因子从最早日期向最新日期累积，
      最早日期因子为 1，越新越大）

成交量/成交额不调整。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .dividend_calendar import DividendCalendar


PRICE_COLS = ["open", "high", "low", "close"]


def backward_adjust(
    kline: pd.DataFrame,
    dividend_info: Optional[list[dict]] = None,
    date_col: str = "date",
) -> pd.DataFrame:
    """对股票 K 线数据执行后复权。

    后复权: 保持历史价格不变，最新价格按复权因子向上调整。
    调整列: open, high, low, close
    不调整: volume, amount, open_interest

    Args:
        kline: K 线 DataFrame，需包含 date/datetime, open, high, low, close 等列
        dividend_info: 分红送股信息列表，每个元素为 dict，字段见 DividendEvent
        date_col: 日期列名，默认为 "date"

    Returns:
        后复权后的 K 线 DataFrame（副本，不修改原数据）

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

    for col in PRICE_COLS:
        if col in result.columns:
            result[col] = result[col].values * cum_factor.values

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


__all__ = ["backward_adjust"]
