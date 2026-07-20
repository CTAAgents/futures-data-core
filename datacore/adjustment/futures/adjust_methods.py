"""换月价差调整方法。

期货连续合约拼接时，由于不同合约之间存在价差，
直接拼接会导致价格跳空。换月调整用于平滑这种价差。

调整方法:
- none / equal_weight: 不调整（等权拼接）
- qfq / forward: 前复权调整（前段对齐后段 — 后段不变，前段调整）
- hfq / backward: 后复权调整（后段对齐前段 — 前段不变，后段调整）

对于期货连续合约的前复权/后复权的定义:
- 前复权 (qfq): 保持最新价格不变，历史价格按换月价差调整。
  即从最后一根K线向前看，每次换月都用新合约与旧合约的价差去调整旧数据。
  （更准确地说：以最新合约为基准，将历史合约的价格都减去累计价差，
   使价格序列在换月日连续）

- 后复权 (hfq): 保持最早价格不变，后续价格按换月价差调整。
  即以第一个合约为基准，后续每次换月都加上累计价差。

- 等权 (none): 不做调整，直接拼接，保留换月跳空。
"""

from __future__ import annotations


import pandas as pd


PRICE_COLS = ["open", "high", "low", "close"]


def adjust_rollover_qfq(
    continuous_df: pd.DataFrame,
    rollover_info: list[tuple[pd.Timestamp, str, str]],
    kline_dict: dict[str, pd.DataFrame],
    date_col: str = "date",
    price_col: str = "close",
) -> pd.DataFrame:
    """期货前复权调整 — 以最新价格为基准，历史价格减去累计价差。

    前复权定义: 保持最新合约的价格不变，将历史合约的价格
    按换月日的价差向下（或向上）调整，使价格序列连续。

    具体做法:
    从后向前遍历换月点，在每个换月日计算「新合约开盘价 - 旧合约收盘价」
    的价差，将换月日之前的所有价格减去这个累计价差。

    Args:
        continuous_df: 已拼接的连续合约 DataFrame
        rollover_info: 换月信息列表 [(换月日, 旧合约, 新合约), ...]
        kline_dict: 所有合约的 K 线字典
        date_col: 日期列名
        price_col: 用于计算价差的价格列（通常用 close 或 open）

    Returns:
        前复权调整后的连续合约 DataFrame（副本）
    """
    result = continuous_df.copy()
    dates = pd.to_datetime(result[date_col])

    cum_gap = 0.0
    gap_list = []

    for dt, old_contract, new_contract in reversed(rollover_info):
        gap = _calculate_rollover_gap(
            dt, old_contract, new_contract, kline_dict, date_col, price_col
        )
        cum_gap += gap
        gap_list.append((dt, cum_gap))

    gap_list.reverse()

    for dt, cum_gap_val in gap_list:
        mask = dates < dt
        for col in PRICE_COLS:
            if col in result.columns:
                result.loc[mask, col] = result.loc[mask, col] - cum_gap_val

    return result


def adjust_rollover_hfq(
    continuous_df: pd.DataFrame,
    rollover_info: list[tuple[pd.Timestamp, str, str]],
    kline_dict: dict[str, pd.DataFrame],
    date_col: str = "date",
    price_col: str = "close",
) -> pd.DataFrame:
    """期货后复权调整 — 以最早价格为基准，后续价格加上累计价差。

    后复权定义: 保持最早合约的价格不变，将后续合约的价格
    按换月日的价差向上（或向下）调整，使价格序列连续。

    具体做法:
    从前向后遍历换月点，在每个换月日计算「新合约开盘价 - 旧合约收盘价」
    的价差，将换月日及之后的所有价格加上这个累计价差。

    Args:
        continuous_df: 已拼接的连续合约 DataFrame
        rollover_info: 换月信息列表 [(换月日, 旧合约, 新合约), ...]
        kline_dict: 所有合约的 K 线字典
        date_col: 日期列名
        price_col: 用于计算价差的价格列

    Returns:
        后复权调整后的连续合约 DataFrame（副本）
    """
    result = continuous_df.copy()
    dates = pd.to_datetime(result[date_col])

    cum_gap = 0.0

    for dt, old_contract, new_contract in rollover_info:
        gap = _calculate_rollover_gap(
            dt, old_contract, new_contract, kline_dict, date_col, price_col
        )
        cum_gap += gap
        mask = dates >= dt
        for col in PRICE_COLS:
            if col in result.columns:
                result.loc[mask, col] = result.loc[mask, col] + cum_gap

    return result


def adjust_rollover_none(
    continuous_df: pd.DataFrame,
    **kwargs,
) -> pd.DataFrame:
    """等权拼接 — 不做任何价格调整。

    Args:
        continuous_df: 已拼接的连续合约 DataFrame
        **kwargs: 忽略的其他参数（为了统一接口）

    Returns:
        原始连续合约 DataFrame 的副本
    """
    return continuous_df.copy()


def _calculate_rollover_gap(
    rollover_date: pd.Timestamp,
    old_contract: str,
    new_contract: str,
    kline_dict: dict[str, pd.DataFrame],
    date_col: str,
    price_col: str,
) -> float:
    """计算换月日的价差 = 新合约换月日价格 - 旧合约换月前一日价格。

    若无法从数据中获取价格，则返回 0。

    Args:
        rollover_date: 换月日
        old_contract: 旧合约代码
        new_contract: 新合约代码
        kline_dict: 合约 K 线字典
        date_col: 日期列名
        price_col: 价格列名

    Returns:
        价差（新合约价格 - 旧合约价格），无法计算时返回 0
    """
    new_price = None
    old_price = None

    if new_contract in kline_dict:
        new_df = kline_dict[new_contract]
        new_dates = pd.to_datetime(new_df[date_col])
        mask = new_dates == rollover_date
        if mask.any() and price_col in new_df.columns:
            new_price = float(new_df.loc[mask, price_col].iloc[0])

    if old_contract in kline_dict:
        old_df = kline_dict[old_contract]
        old_dates = pd.to_datetime(old_df[date_col])
        before_mask = old_dates < rollover_date
        if before_mask.any() and price_col in old_df.columns:
            old_price = float(old_df.loc[before_mask, price_col].iloc[-1])

    if new_price is not None and old_price is not None:
        return new_price - old_price

    return 0.0


__all__ = [
    "adjust_rollover_qfq",
    "adjust_rollover_hfq",
    "adjust_rollover_none",
]
