"""连续合约拼接。

将多个合约的 K 线数据按主力合约序列拼接成连续合约数据。

拼接逻辑:
1. 获取每日主力合约
2. 按日期从早到晚，每个交易日取当日主力合约的 K 线数据
3. 如当日主力合约无数据，尝试用次主力合约填充
4. 最终输出一个连续的 K 线 DataFrame
"""

from __future__ import annotations


import pandas as pd

from .rollover import (
    get_dominant_series,
    get_rollover_pairs,
)
from .adjust_methods import (
    adjust_rollover_qfq,
    adjust_rollover_hfq,
    adjust_rollover_none,
)


def build_continuous_contract(
    kline_dict: dict[str, pd.DataFrame],
    rollover_method: str = "volume",
    adjust_method: str = "none",
    date_col: str = "date",
    switch_day: int = 15,
    gap_price_col: str = "close",
) -> pd.DataFrame:
    """构建期货连续合约。

    步骤:
    1. 根据 rollover_method 识别每日主力合约
    2. 按主力合约序列拼接 K 线数据
    3. 根据 adjust_method 进行换月价差调整

    Args:
        kline_dict: 合约代码 -> K 线 DataFrame 的字典
        rollover_method: 换月方法
            - "volume": 成交量加权
            - "open_interest" 或 "oi": 持仓量加权
            - "fixed_day": 固定日换月
        adjust_method: 换月调整方法
            - "none" 或 "equal_weight": 不调整
            - "qfq" 或 "forward": 前复权
            - "hfq" 或 "backward": 后复权
        date_col: 日期列名
        switch_day: 固定日换月的换月日（仅 rollover_method="fixed_day" 时有效）
        gap_price_col: 计算换月价差使用的价格列

    Returns:
        连续合约 K 线 DataFrame，包含 date, open, high, low, close,
        volume, amount, open_interest 等列，以及额外的 contract 列
        标记当日使用的合约。

    Raises:
        ValueError: kline_dict 为空或参数不合法
    """
    if not kline_dict:
        raise ValueError("kline_dict 不能为空")

    dominant_series = get_dominant_series(
        kline_dict,
        method=rollover_method,
        date_col=date_col,
        switch_day=switch_day,
    )

    if len(dominant_series) == 0:
        return _empty_kline_df(date_col)

    continuous_df = _concat_by_dominant(
        kline_dict, dominant_series, date_col
    )

    rollover_pairs = get_rollover_pairs(dominant_series)

    adjust_lower = adjust_method.lower()
    if adjust_lower in ("none", "equal_weight", ""):
        result = adjust_rollover_none(continuous_df)
    elif adjust_lower in ("qfq", "forward"):
        result = adjust_rollover_qfq(
            continuous_df, rollover_pairs, kline_dict,
            date_col=date_col, price_col=gap_price_col,
        )
    elif adjust_lower in ("hfq", "backward"):
        result = adjust_rollover_hfq(
            continuous_df, rollover_pairs, kline_dict,
            date_col=date_col, price_col=gap_price_col,
        )
    else:
        raise ValueError(
            f"不支持的换月调整方法: {adjust_method}。"
            f"支持: none, qfq/forward, hfq/backward"
        )

    return result


def _concat_by_dominant(
    kline_dict: dict[str, pd.DataFrame],
    dominant_series: pd.Series,
    date_col: str,
) -> pd.DataFrame:
    """按主力合约序列拼接 K 线数据。

    Args:
        kline_dict: 合约 -> K 线 DataFrame
        dominant_series: 每日主力合约序列
        date_col: 日期列名

    Returns:
        拼接后的连续合约 DataFrame，含 contract 列
    """
    all_dates = dominant_series.index
    result_rows = []

    for dt in all_dates:
        contract = dominant_series.loc[dt]
        if contract is None or pd.isna(contract):
            continue

        if contract not in kline_dict:
            continue

        df = kline_dict[contract]
        dates = pd.to_datetime(df[date_col])
        mask = dates == dt

        if not mask.any():
            continue

        row = df.loc[mask].iloc[0].copy()
        row["contract"] = contract
        result_rows.append(row)

    if not result_rows:
        return _empty_kline_df(date_col)

    result = pd.DataFrame(result_rows).reset_index(drop=True)

    if date_col in result.columns:
        result[date_col] = pd.to_datetime(result[date_col])
        result = result.sort_values(date_col).reset_index(drop=True)

    return result


def _empty_kline_df(date_col: str) -> pd.DataFrame:
    """返回空的 K 线 DataFrame（包含标准列）。

    Args:
        date_col: 日期列名

    Returns:
        空 DataFrame
    """
    cols = [date_col, "open", "high", "low", "close",
            "volume", "amount", "open_interest", "contract"]
    return pd.DataFrame(columns=cols)


__all__ = ["build_continuous_contract"]
