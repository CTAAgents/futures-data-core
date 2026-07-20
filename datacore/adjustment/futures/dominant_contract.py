"""主力合约识别。

识别每个交易日的主力合约，支持三种方式:
1. 成交量加权 (volume): 选择当日成交量最大的合约
2. 持仓量加权 (open_interest / oi): 选择当日持仓量最大的合约
3. 固定日换月 (fixed_day): 每月固定日期换月到下一个合约

输入:
    kline_dict: dict[str, pd.DataFrame]
        key: 合约代码（如 "RB2501", "RB2505"）
        value: 该合约的 K 线 DataFrame，需包含 date, volume, open_interest 等
"""

from __future__ import annotations


import numpy as np
import pandas as pd


def identify_dominant_by_volume(
    kline_dict: dict[str, pd.DataFrame],
    date_col: str = "date",
    volume_col: str = "volume",
) -> pd.Series:
    """基于成交量识别每日主力合约。

    对每个交易日，选择成交量最大的合约作为主力合约。

    Args:
        kline_dict: 合约代码 -> K 线 DataFrame 的字典
        date_col: 日期列名
        volume_col: 成交量列名

    Returns:
        pd.Series，index 为日期，值为当日主力合约代码

    Raises:
        ValueError: kline_dict 为空或数据格式不正确
    """
    if not kline_dict:
        raise ValueError("kline_dict 不能为空")

    all_dates = _collect_all_dates(kline_dict, date_col)
    if len(all_dates) == 0:
        return pd.Series(dtype=str)

    volume_matrix = _build_indicator_matrix(kline_dict, all_dates, date_col, volume_col)
    result = volume_matrix.idxmax(axis=1)
    result.name = "dominant_contract"
    return result


def identify_dominant_by_oi(
    kline_dict: dict[str, pd.DataFrame],
    date_col: str = "date",
    oi_col: str = "open_interest",
) -> pd.Series:
    """基于持仓量识别每日主力合约。

    对每个交易日，选择持仓量最大的合约作为主力合约。

    Args:
        kline_dict: 合约代码 -> K 线 DataFrame 的字典
        date_col: 日期列名
        oi_col: 持仓量列名

    Returns:
        pd.Series，index 为日期，值为当日主力合约代码

    Raises:
        ValueError: kline_dict 为空或数据格式不正确
    """
    if not kline_dict:
        raise ValueError("kline_dict 不能为空")

    all_dates = _collect_all_dates(kline_dict, date_col)
    if len(all_dates) == 0:
        return pd.Series(dtype=str)

    oi_matrix = _build_indicator_matrix(kline_dict, all_dates, date_col, oi_col)
    result = oi_matrix.idxmax(axis=1)
    result.name = "dominant_contract"
    return result


def identify_dominant_fixed_day(
    kline_dict: dict[str, pd.DataFrame],
    switch_day: int = 15,
    date_col: str = "date",
) -> pd.Series:
    """固定日换月 — 每月固定日期切换到下一个合约。

    在每月 switch_day 当天（含）之后，切换到到期月更晚的合约。
    合约顺序按合约代码字典序或从合约名中解析的月份排序。

    Args:
        kline_dict: 合约代码 -> K 线 DataFrame 的字典
        switch_day: 换月日（1-31），默认 15 日
        date_col: 日期列名

    Returns:
        pd.Series，index 为日期，值为当日主力合约代码

    Raises:
        ValueError: kline_dict 为空或参数不合法
    """
    if not kline_dict:
        raise ValueError("kline_dict 不能为空")
    if switch_day < 1 or switch_day > 31:
        raise ValueError("switch_day 必须在 1-31 之间")

    all_dates = _collect_all_dates(kline_dict, date_col)
    if len(all_dates) == 0:
        return pd.Series(dtype=str)

    contract_names = sorted(kline_dict.keys())
    n_contracts = len(contract_names)

    result = pd.Series(index=all_dates, dtype=object)

    current_contract_idx = 0

    for i, dt in enumerate(all_dates):
        day = dt.day

        if i == 0:
            result.iloc[i] = contract_names[current_contract_idx]
            continue

        if day >= switch_day:
            next_idx = min(current_contract_idx + 1, n_contracts - 1)
            next_contract = contract_names[next_idx]
            if next_contract in kline_dict and next_idx > current_contract_idx:
                next_df = kline_dict[next_contract]
                next_dates = pd.to_datetime(next_df[date_col])
                if dt in next_dates.values:
                    current_contract_idx = next_idx

        if current_contract_idx < n_contracts:
            result.iloc[i] = contract_names[current_contract_idx]
        else:
            result.iloc[i] = contract_names[-1]

    result.name = "dominant_contract"
    return result


def _collect_all_dates(
    kline_dict: dict[str, pd.DataFrame],
    date_col: str,
) -> pd.DatetimeIndex:
    """收集所有合约的所有日期，去重排序。

    Args:
        kline_dict: 合约 -> K 线 DataFrame
        date_col: 日期列名

    Returns:
        排序后的 DatetimeIndex
    """
    all_dates = set()
    for df in kline_dict.values():
        if date_col not in df.columns:
            raise ValueError(f"K 线数据缺少日期列: {date_col}")
        dates = pd.to_datetime(df[date_col])
        all_dates.update(dates.tolist())

    return pd.DatetimeIndex(sorted(all_dates))


def _build_indicator_matrix(
    kline_dict: dict[str, pd.DataFrame],
    all_dates: pd.DatetimeIndex,
    date_col: str,
    value_col: str,
) -> pd.DataFrame:
    """构建指标矩阵 — 行为日期，列为合约，值为指标（成交量/持仓量等）。

    Args:
        kline_dict: 合约 -> K 线 DataFrame
        all_dates: 所有日期
        date_col: 日期列名
        value_col: 指标列名

    Returns:
        DataFrame，index=all_dates, columns=合约代码顺序，值为指标值
    """
    contract_names = list(kline_dict.keys())
    n_dates = len(all_dates)
    n_contracts = len(contract_names)

    matrix = pd.DataFrame(
        np.full((n_dates, n_contracts), np.nan),
        index=all_dates,
        columns=contract_names,
    )

    for idx, (contract, df) in enumerate(kline_dict.items()):
        if value_col not in df.columns:
            continue
        dates = pd.to_datetime(df[date_col])
        values = pd.to_numeric(df[value_col], errors="coerce").values
        matrix.loc[dates, contract] = values

    return matrix


__all__ = [
    "identify_dominant_by_volume",
    "identify_dominant_by_oi",
    "identify_dominant_fixed_day",
]
