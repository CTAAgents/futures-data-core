"""异常过滤 — 3σ 法和 IQR 法两种异常值检测和过滤。"""

from __future__ import annotations


import numpy as np
import pandas as pd


def detect_outliers(
    data: pd.Series | np.ndarray | list[float],
    method: str = "3sigma",
    threshold: float | None = None,
) -> np.ndarray:
    """检测异常值，返回布尔掩码数组。

    Args:
        data: 输入数据序列。
        method: 检测方法：
            - '3sigma' / 'zscore': 3σ 法（Z-score）
            - 'iqr': 四分位距法（IQR）
        threshold: 阈值：
            - 3σ 法默认为 3.0
            - IQR 法默认为 1.5

    Returns:
        布尔数组，True 表示异常值。

    Examples:
        >>> data = [1, 2, 3, 4, 5, 100]
        >>> detect_outliers(data, method="iqr")
        array([False, False, False, False, False,  True])
    """
    if isinstance(data, pd.Series):
        values = data.values.astype(float)
    elif isinstance(data, np.ndarray):
        values = data.astype(float)
    else:
        values = np.array(data, dtype=float)

    valid_mask = ~np.isnan(values)
    result = np.zeros_like(values, dtype=bool)

    if not valid_mask.any():
        return result

    clean_values = values[valid_mask]

    if method in ("3sigma", "zscore"):
        thresh = threshold if threshold is not None else 3.0
        mean = np.mean(clean_values)
        std = np.std(clean_values)
        if std == 0:
            return result
        z_scores = (values - mean) / std
        result = np.abs(z_scores) > thresh
        result[~valid_mask] = False

    elif method == "iqr":
        thresh = threshold if threshold is not None else 1.5
        q1 = np.percentile(clean_values, 25)
        q3 = np.percentile(clean_values, 75)
        iqr = q3 - q1
        lower = q1 - thresh * iqr
        upper = q3 + thresh * iqr
        result = (values < lower) | (values > upper)
        result[~valid_mask] = False

    else:
        pass

    return result


def filter_outliers_3sigma(
    df: pd.DataFrame,
    column: str,
    sigma: float = 3.0,
    action: str = "remove",
    replace_value: float | str = "median",
) -> pd.DataFrame:
    """使用 3σ 法过滤异常值。

    Args:
        df: 输入 DataFrame。
        column: 要检测的列名。
        sigma: 标准差倍数，默认 3.0。
        action: 处理方式：
            - 'remove': 移除异常行
            - 'replace': 替换为指定值
            - 'mark': 标记（新增 {column}_is_outlier 列）
        replace_value: 替换值，可为数值或 'mean'/'median'。

    Returns:
        处理后的 DataFrame。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
        >>> result = filter_outliers_3sigma(df, "val", action="mark")
        >>> "val_is_outlier" in result.columns
        True
    """
    result = df.copy()
    result[column] = result[column].astype(float)
    mask = detect_outliers(result[column], method="3sigma", threshold=sigma)

    if action == "remove":
        return result[~mask].reset_index(drop=True)
    elif action == "replace":
        if replace_value == "mean":
            clean_vals = result.loc[~mask, column]
            rep_val = float(clean_vals.mean())
        elif replace_value == "median":
            clean_vals = result.loc[~mask, column]
            rep_val = float(clean_vals.median())
        else:
            rep_val = float(replace_value)
        result.loc[mask, column] = rep_val
        return result
    elif action == "mark":
        result[f"{column}_is_outlier"] = mask
        return result
    else:
        return result[~mask].reset_index(drop=True)


def filter_outliers_iqr(
    df: pd.DataFrame,
    column: str,
    iqr_factor: float = 1.5,
    action: str = "remove",
    replace_value: float | str = "median",
) -> pd.DataFrame:
    """使用 IQR 法过滤异常值。

    Args:
        df: 输入 DataFrame。
        column: 要检测的列名。
        iqr_factor: IQR 倍数，默认 1.5。
        action: 处理方式：'remove' / 'replace' / 'mark'。
        replace_value: 替换值，可为数值或 'mean'/'median'。

    Returns:
        处理后的 DataFrame。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
        >>> result = filter_outliers_iqr(df, "val", action="remove")
        >>> len(result)
        5
    """
    result = df.copy()
    result[column] = result[column].astype(float)
    mask = detect_outliers(result[column], method="iqr", threshold=iqr_factor)

    if action == "remove":
        return result[~mask].reset_index(drop=True)
    elif action == "replace":
        if replace_value == "mean":
            clean_vals = result.loc[~mask, column]
            rep_val = float(clean_vals.mean())
        elif replace_value == "median":
            clean_vals = result.loc[~mask, column]
            rep_val = float(clean_vals.median())
        else:
            rep_val = float(replace_value)
        result.loc[mask, column] = rep_val
        return result
    elif action == "mark":
        result[f"{column}_is_outlier"] = mask
        return result
    else:
        return result[~mask].reset_index(drop=True)


def mark_outliers(
    df: pd.DataFrame,
    columns: list[str],
    method: str = "3sigma",
    threshold: float | None = None,
) -> pd.DataFrame:
    """标记多个列的异常值，为每列添加 _is_outlier 标记列。

    Args:
        df: 输入 DataFrame。
        columns: 要检测的列名列表。
        method: 检测方法，'3sigma' 或 'iqr'。
        threshold: 检测阈值。

    Returns:
        添加了标记列的 DataFrame。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"a": [1, 2, 100], "b": [3, 4, 5]})
        >>> result = mark_outliers(df, ["a", "b"], method="iqr")
        >>> "a_is_outlier" in result.columns
        True
        >>> "b_is_outlier" in result.columns
        True
    """
    result = df.copy()
    for col in columns:
        if col in result.columns:
            mask = detect_outliers(result[col], method=method, threshold=threshold)
            result[f"{col}_is_outlier"] = mask
    return result
