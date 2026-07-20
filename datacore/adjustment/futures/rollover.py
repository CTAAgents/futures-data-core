"""换月算法。

基于主力合约序列确定换月日，并提供换月检测和换月点提取。

换月日判定:
    当某一日的主力合约与前一日不同时，该日即为换月日。

支持的换月方法:
- volume: 成交量加权换月
- open_interest / oi: 持仓量加权换月
- fixed_day: 固定日换月
"""

from __future__ import annotations


import pandas as pd

from .dominant_contract import (
    identify_dominant_by_volume,
    identify_dominant_by_oi,
    identify_dominant_fixed_day,
)


def detect_rollover_dates(
    dominant_series: pd.Series,
) -> pd.DatetimeIndex:
    """从主力合约序列中检测换月日。

    换月日定义: 当日主力合约与前一日不同，则当日为换月日。

    Args:
        dominant_series: pd.Series，index 为日期，值为主力合约代码

    Returns:
        换月日的 DatetimeIndex（排序后）
    """
    if len(dominant_series) < 2:
        return pd.DatetimeIndex([])

    shifted = dominant_series.shift(1)
    rollover_mask = (dominant_series != shifted) & (shifted.notna()) & (dominant_series.notna())
    rollover_dates = dominant_series.index[rollover_mask]

    return pd.DatetimeIndex(rollover_dates)


def get_dominant_series(
    kline_dict: dict[str, pd.DataFrame],
    method: str = "volume",
    date_col: str = "date",
    switch_day: int = 15,
) -> pd.Series:
    """根据指定方法获取主力合约序列。

    Args:
        kline_dict: 合约代码 -> K 线 DataFrame 的字典
        method: 换月方法
            - "volume": 成交量加权
            - "open_interest" 或 "oi": 持仓量加权
            - "fixed_day": 固定日换月
        date_col: 日期列名
        switch_day: 固定日换月的换月日（仅 method="fixed_day" 时有效）

    Returns:
        pd.Series，index 为日期，值为当日主力合约代码

    Raises:
        ValueError: method 不支持
    """
    method_lower = method.lower()

    if method_lower == "volume":
        return identify_dominant_by_volume(kline_dict, date_col=date_col)
    elif method_lower in ("open_interest", "oi"):
        return identify_dominant_by_oi(kline_dict, date_col=date_col)
    elif method_lower == "fixed_day":
        return identify_dominant_fixed_day(kline_dict, switch_day=switch_day, date_col=date_col)
    else:
        raise ValueError(
            f"不支持的换月方法: {method}。"
            f"支持的方法: volume, open_interest/oi, fixed_day"
        )


def get_rollover_pairs(
    dominant_series: pd.Series,
) -> list[tuple[pd.Timestamp, str, str]]:
    """获取换月点列表 — (换月日, 旧合约, 新合约)。

    Args:
        dominant_series: pd.Series，index 为日期，值为主力合约代码

    Returns:
        list of (换月日, 旧合约, 新合约) 元组
    """
    rollover_dates = detect_rollover_dates(dominant_series)
    pairs = []

    for dt in rollover_dates:
        idx = dominant_series.index.get_loc(dt)
        if idx > 0:
            old_contract = dominant_series.iloc[idx - 1]
            new_contract = dominant_series.iloc[idx]
            if old_contract is not None and new_contract is not None:
                pairs.append((dt, old_contract, new_contract))

    return pairs


__all__ = [
    "detect_rollover_dates",
    "get_dominant_series",
    "get_rollover_pairs",
]
