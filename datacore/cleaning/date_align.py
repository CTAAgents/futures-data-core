"""时间对齐 — 按交易日历对齐数据，缺失日填充。"""

from __future__ import annotations

from typing import Any

import pandas as pd


def infer_frequency(dates: pd.DatetimeIndex | list[Any]) -> str:
    """推断时间序列的频率。

    Args:
        dates: 日期序列，可以是 DatetimeIndex 或列表。

    Returns:
        频率字符串，如 'D'、'B'、'W'、'M'；无法推断则返回 'D'。

    Examples:
        >>> import pandas as pd
        >>> dates = pd.date_range("2024-01-01", periods=5, freq="B")
        >>> infer_frequency(dates)
        'B'
    """
    if not isinstance(dates, pd.DatetimeIndex):
        dates = pd.DatetimeIndex(dates)
    if len(dates) < 2:
        return "D"
    try:
        inferred = pd.infer_freq(dates)
        return inferred if inferred else "D"
    except (ValueError, TypeError):
        return "D"


def fill_missing_dates(
    df: pd.DataFrame,
    date_col: str = "datetime",
    freq: str = "B",
    method: str = "ffill",
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """填充缺失的日期，生成完整的时间序列。

    Args:
        df: 输入 DataFrame，必须包含日期列。
        date_col: 日期列名，默认为 'datetime'。
        freq: 目标频率，'B' 为工作日（交易日近似），'D' 为自然日，
            默认为 'B'。
        method: 缺失值填充方法：
            - 'ffill': 前向填充
            - 'bfill': 后向填充
            - 'interpolate': 线性插值
            - 'zero': 填 0
            - 'nan': 保留 NaN
        start_date: 起始日期，默认使用数据的最早日期。
        end_date: 结束日期，默认使用数据的最晚日期。

    Returns:
        日期对齐且填充后的 DataFrame，日期列设为索引。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "datetime": ["2024-01-01", "2024-01-03"],
        ...     "value": [10, 30],
        ... })
        >>> result = fill_missing_dates(df, freq="D", method="ffill")
        >>> len(result)
        3
    """
    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col])
    result = result.set_index(date_col)
    result = result.sort_index()

    start = pd.Timestamp(start_date) if start_date else result.index.min()
    end = pd.Timestamp(end_date) if end_date else result.index.max()

    full_index = pd.date_range(start=start, end=end, freq=freq)
    result = result.reindex(full_index)

    if method == "ffill":
        result = result.ffill()
    elif method == "bfill":
        result = result.bfill()
    elif method == "interpolate":
        result = result.interpolate(method="linear")
    elif method == "zero":
        result = result.fillna(0)
    elif method == "nan":
        pass

    result.index.name = date_col
    return result


def align_to_trading_calendar(
    series_dict: dict[str, pd.DataFrame],
    date_col: str = "datetime",
    freq: str = "B",
    method: str = "ffill",
    how: str = "outer",
) -> dict[str, pd.DataFrame]:
    """将多个时间序列对齐到同一交易日历。

    Args:
        series_dict: 多个数据序列的字典，key 为序列名，value 为 DataFrame。
        date_col: 日期列名，默认为 'datetime'。
        freq: 目标频率，'B' 为工作日，默认为 'B'。
        method: 缺失值填充方法，默认为 'ffill'。
        how: 对齐方式：
            - 'outer': 取所有日期的并集
            - 'inner': 取所有序列共有的日期
            - 'left': 以第一个序列的日期为准

    Returns:
        对齐后的字典，key 与输入相同，value 为对齐后的 DataFrame。

    Examples:
        >>> import pandas as pd
        >>> s1 = pd.DataFrame({
        ...     "datetime": ["2024-01-01", "2024-01-02"],
        ...     "price": [100, 101],
        ... })
        >>> s2 = pd.DataFrame({
        ...     "datetime": ["2024-01-02", "2024-01-03"],
        ...     "price": [200, 201],
        ... })
        >>> result = align_to_trading_calendar({"a": s1, "b": s2}, freq="D")
        >>> set(result.keys())
        {'a', 'b'}
    """
    processed = {}
    all_indexes = []

    for name, df in series_dict.items():
        temp = df.copy()
        temp[date_col] = pd.to_datetime(temp[date_col])
        temp = temp.set_index(date_col).sort_index()
        processed[name] = temp
        all_indexes.append(temp.index)

    if how == "outer":
        full_index = all_indexes[0]
        for idx in all_indexes[1:]:
            full_index = full_index.union(idx)
    elif how == "inner":
        full_index = all_indexes[0]
        for idx in all_indexes[1:]:
            full_index = full_index.intersection(idx)
    elif how == "left":
        full_index = all_indexes[0]
    else:
        full_index = all_indexes[0]
        for idx in all_indexes[1:]:
            full_index = full_index.union(idx)

    full_index = full_index.sort_values()

    if freq and freq.upper() != "D":
        cal_dates = pd.date_range(
            start=full_index.min(), end=full_index.max(), freq=freq
        )
        full_index = full_index.intersection(cal_dates).union(cal_dates)
        full_index = full_index.sort_values()

    result = {}
    for name, df in processed.items():
        aligned = df.reindex(full_index)
        if method == "ffill":
            aligned = aligned.ffill()
        elif method == "bfill":
            aligned = aligned.bfill()
        elif method == "interpolate":
            aligned = aligned.interpolate()
        elif method == "zero":
            aligned = aligned.fillna(0)

        aligned.index.name = date_col
        result[name] = aligned.reset_index()

    return result
