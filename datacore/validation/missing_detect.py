"""缺失检测 — 检测数据中的缺失值、连续缺失段。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def detect_missing_values(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """检测 DataFrame 中的缺失值。

    Args:
        df: 输入 DataFrame。
        columns: 要检测的列名列表，默认检测所有列。

    Returns:
        缺失检测结果字典，包含：
        - total_rows: 总行数
        - total_cells: 总单元格数
        - missing_cells: 缺失单元格数
        - completeness: 完整度（0-1）
        - field_missing: 各字段缺失详情

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})
        >>> result = detect_missing_values(df)
        >>> result["total_rows"]
        3
        >>> result["missing_cells"]
        2
    """
    if df.empty:
        return {
            "total_rows": 0,
            "total_cells": 0,
            "missing_cells": 0,
            "completeness": 1.0,
            "field_missing": {},
        }

    target_cols = columns if columns else df.columns.tolist()
    target_cols = [c for c in target_cols if c in df.columns]

    field_missing: dict[str, dict[str, Any]] = {}
    total_missing = 0
    total_cells = len(df) * len(target_cols)

    for col in target_cols:
        missing_count = int(df[col].isna().sum())
        field_missing[col] = {
            "missing_count": missing_count,
            "missing_rate": float(missing_count / len(df)) if len(df) > 0 else 0.0,
            "total_count": len(df),
        }
        total_missing += missing_count

    completeness = float(1 - total_missing / total_cells) if total_cells > 0 else 1.0

    return {
        "total_rows": len(df),
        "total_fields": len(target_cols),
        "total_cells": total_cells,
        "missing_cells": total_missing,
        "completeness": completeness,
        "field_missing": field_missing,
    }


def find_continuous_missing(
    series: pd.Series | list[Any],
    min_length: int = 3,
) -> list[dict[str, Any]]:
    """查找连续缺失的片段。

    Args:
        series: 数据序列。
        min_length: 最小连续缺失长度，默认 3。

    Returns:
        连续缺失段列表，每个元素包含：
        - start: 起始位置索引
        - end: 结束位置索引
        - length: 连续缺失长度

    Examples:
        >>> data = [1, None, None, None, 5, 6, None, None]
        >>> gaps = find_continuous_missing(data, min_length=3)
        >>> len(gaps)
        1
        >>> gaps[0]["length"]
        3
    """
    if isinstance(series, pd.Series):
        values = series.values
    else:
        values = np.array(series, dtype=object)

    is_missing = pd.isna(values)
    gaps: list[dict[str, Any]] = []
    start = None

    for i, missing in enumerate(is_missing):
        if missing and start is None:
            start = i
        elif not missing and start is not None:
            length = i - start
            if length >= min_length:
                gaps.append({
                    "start": start,
                    "end": i - 1,
                    "length": length,
                })
            start = None

    if start is not None:
        length = len(is_missing) - start
        if length >= min_length:
            gaps.append({
                "start": start,
                "end": len(is_missing) - 1,
                "length": length,
            })

    return gaps


def calculate_completeness(
    df: pd.DataFrame,
    date_col: str = "datetime",
    expected_freq: str = "B",
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """计算时间序列数据的完整度。

    综合考虑日期缺失和数值缺失。

    Args:
        df: 输入 DataFrame。
        date_col: 日期列名。
        expected_freq: 期望频率，'B' 为工作日。
        fields: 要检查的字段列表，默认所有数值字段。

    Returns:
        完整度评估结果。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "datetime": pd.date_range("2024-01-01", periods=5, freq="B"),
        ...     "value": [1, 2, None, 4, 5],
        ... })
        >>> result = calculate_completeness(df)
        >>> "date_completeness" in result
        True
    """
    if df.empty:
        return {
            "date_completeness": 0.0,
            "value_completeness": 0.0,
            "overall_completeness": 0.0,
            "expected_count": 0,
            "actual_count": 0,
        }

    result_df = df.copy()
    result_df[date_col] = pd.to_datetime(result_df[date_col])
    result_df = result_df.set_index(date_col).sort_index()

    start = result_df.index.min()
    end = result_df.index.max()
    expected_dates = pd.date_range(start=start, end=end, freq=expected_freq)
    expected_count = len(expected_dates)
    actual_count = len(result_df)

    date_completeness = (
        float(actual_count / expected_count) if expected_count > 0 else 0.0
    )

    if fields is None:
        fields = result_df.select_dtypes(include=[np.number]).columns.tolist()

    valid_fields = [f for f in fields if f in result_df.columns]

    value_missing = 0
    value_total = 0
    for f in valid_fields:
        value_missing += int(result_df[f].isna().sum())
        value_total += len(result_df)

    value_completeness = (
        float(1 - value_missing / value_total) if value_total > 0 else 1.0
    )

    overall = date_completeness * 0.5 + value_completeness * 0.5

    return {
        "date_completeness": date_completeness,
        "value_completeness": value_completeness,
        "overall_completeness": overall,
        "expected_count": expected_count,
        "actual_count": actual_count,
        "value_missing_cells": value_missing,
        "value_total_cells": value_total,
        "fields_checked": valid_fields,
    }
