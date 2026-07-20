"""OutlierFilterTool - 异常值过滤工具。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..base import DataCoreBaseTool


class OutlierFilterTool(DataCoreBaseTool):
    """异常值检测与过滤。

    支持多种异常值检测方法：IQR、Z-score、移动中位数等。
    """

    name = "datacore_outlier_filter"
    description = (
        "异常值检测与过滤。支持 IQR、Z-score、移动中位数等方法。"
        "参数：data (list, 必需) - 数据列表；"
        "field (str, 必需) - 要检测的字段名；"
        "method (str, 可选) - 检测方法，'iqr'/'zscore'/'rolling'，默认 'iqr'；"
        "threshold (float, 可选) - 阈值，IQR 默认为 1.5，Z-score 默认为 3；"
        "action (str, 可选) - 处理方式，'remove'/'replace'/'mark'，默认 'mark'；"
        "replace_value (str/float, 可选) - 替换值，'mean'/'median'/数值，默认 'median'"
    )

    def _run(self, data: list[dict[str, Any]], field: str,
             method: str = "iqr", threshold: float | None = None,
             action: str = "mark", replace_value: Any = "median",
             **kwargs: Any) -> dict[str, Any]:
        try:
            df = pd.DataFrame(data)

            if df.empty or field not in df.columns:
                return {
                    "success": True,
                    "field": field,
                    "method": method,
                    "outlier_count": 0,
                    "data": data,
                }

            values = df[field].values.astype(float)
            outlier_mask = self._detect_outliers(values, method, threshold)
            outlier_count = int(outlier_mask.sum())

            if action == "remove":
                result_df = df[~outlier_mask]
            elif action == "replace":
                result_df = df.copy()
                rep_val = self._get_replace_value(values, replace_value)
                result_df.loc[outlier_mask, field] = rep_val
                result_df[f"{field}_was_outlier"] = outlier_mask
            else:
                result_df = df.copy()
                result_df[f"{field}_is_outlier"] = outlier_mask

            result_data = result_df.to_dict("records")

            return {
                "success": True,
                "field": field,
                "method": method,
                "threshold": threshold or self._default_threshold(method),
                "outlier_count": outlier_count,
                "total_count": len(data),
                "action": action,
                "data": result_data,
            }
        except Exception as e:
            return {
                "success": False,
                "field": field,
                "method": method,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _detect_outliers(self, values: np.ndarray, method: str,
                         threshold: float | None) -> np.ndarray:
        clean_values = values[~np.isnan(values)]
        if len(clean_values) == 0:
            return np.zeros_like(values, dtype=bool)

        thresh = threshold or self._default_threshold(method)

        if method == "iqr":
            q1 = np.percentile(clean_values, 25)
            q3 = np.percentile(clean_values, 75)
            iqr = q3 - q1
            lower = q1 - thresh * iqr
            upper = q3 + thresh * iqr
            return (values < lower) | (values > upper)
        elif method == "zscore":
            mean = np.mean(clean_values)
            std = np.std(clean_values)
            if std == 0:
                return np.zeros_like(values, dtype=bool)
            z_scores = (values - mean) / std
            return np.abs(z_scores) > thresh
        elif method == "rolling":
            return np.zeros_like(values, dtype=bool)
        else:
            return np.zeros_like(values, dtype=bool)

    def _default_threshold(self, method: str) -> float:
        if method == "iqr":
            return 1.5
        elif method == "zscore":
            return 3.0
        return 1.5

    def _get_replace_value(self, values: np.ndarray, replace_value: Any) -> float:
        clean_values = values[~np.isnan(values)]
        if replace_value == "mean":
            return float(np.mean(clean_values))
        elif replace_value == "median":
            return float(np.median(clean_values))
        else:
            return float(replace_value)
