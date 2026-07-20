"""CalMathComputeTool - 数据计算和校验工具。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..base import DataCoreBaseTool


class CalMathComputeTool(DataCoreBaseTool):
    """数据计算和数学校验。

    执行各种数学计算并验证数据的数学一致性，
    如 OHLC 合法性校验、成交量关系验证等。
    """

    name = "datacore_cal_math"
    description = (
        "数据计算和数学校验。执行数学计算并验证数据一致性。"
        "参数：data (list, 必需) - 数据列表；"
        "operation (str, 必需) - 操作类型：'ohlc_validate'/'sum'/'mean'/'std'/'correlation'/'rolling_calc'；"
        "fields (list, 可选) - 涉及的字段列表；"
        "params (dict, 可选) - 额外参数"
    )

    def _run(self, data: list[dict[str, Any]], operation: str,
             fields: list[str] | None = None,
             params: dict[str, Any] | None = None,
             **kwargs: Any) -> dict[str, Any]:
        try:
            df = pd.DataFrame(data)
            params = params or {}

            if operation == "ohlc_validate":
                return self._validate_ohlc(df)
            elif operation == "sum":
                return self._compute_sum(df, fields)
            elif operation == "mean":
                return self._compute_mean(df, fields)
            elif operation == "std":
                return self._compute_std(df, fields)
            elif operation == "correlation":
                return self._compute_correlation(df, fields)
            elif operation == "rolling_calc":
                return self._rolling_calc(df, fields, params)
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作: {operation}",
                    "valid_operations": [
                        "ohlc_validate", "sum", "mean", "std",
                        "correlation", "rolling_calc",
                    ],
                }
        except Exception as e:
            return {
                "success": False,
                "operation": operation,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _validate_ohlc(self, df: pd.DataFrame) -> dict[str, Any]:
        required = ["open", "high", "low", "close"]
        for col in required:
            if col not in df.columns:
                return {
                    "success": False,
                    "error": f"缺少必要列: {col}",
                    "required_columns": required,
                }

        issues = []
        for idx, row in df.iterrows():
            o, h, low_p, c = row["open"], row["high"], row["low"], row["close"]

            if pd.isna(o) or pd.isna(h) or pd.isna(low_p) or pd.isna(c):
                continue

            if h < max(o, c):
                issues.append({"index": idx, "type": "high_too_low",
                               "high": h, "max_open_close": max(o, c)})
            if low_p > min(o, c):
                issues.append({"index": idx, "type": "low_too_high",
                               "low": low_p, "min_open_close": min(o, c)})
            if h < low_p:
                issues.append({"index": idx, "type": "high_below_low",
                               "high": h, "low": low_p})

        return {
            "success": True,
            "operation": "ohlc_validate",
            "total_rows": len(df),
            "issue_count": len(issues),
            "valid_rows": len(df) - len(issues),
            "issues": issues[:100],
        }

    def _compute_sum(self, df: pd.DataFrame,
                     fields: list[str] | None) -> dict[str, Any]:
        target_fields = fields if fields else df.select_dtypes(
            include=[np.number]
        ).columns.tolist()

        results = {}
        for field in target_fields:
            if field in df.columns:
                results[field] = float(df[field].sum())

        return {
            "success": True,
            "operation": "sum",
            "fields": target_fields,
            "results": results,
        }

    def _compute_mean(self, df: pd.DataFrame,
                      fields: list[str] | None) -> dict[str, Any]:
        target_fields = fields if fields else df.select_dtypes(
            include=[np.number]
        ).columns.tolist()

        results = {}
        for field in target_fields:
            if field in df.columns:
                results[field] = float(df[field].mean())

        return {
            "success": True,
            "operation": "mean",
            "fields": target_fields,
            "results": results,
        }

    def _compute_std(self, df: pd.DataFrame,
                     fields: list[str] | None) -> dict[str, Any]:
        target_fields = fields if fields else df.select_dtypes(
            include=[np.number]
        ).columns.tolist()

        results = {}
        for field in target_fields:
            if field in df.columns:
                results[field] = float(df[field].std())

        return {
            "success": True,
            "operation": "std",
            "fields": target_fields,
            "results": results,
        }

    def _compute_correlation(self, df: pd.DataFrame,
                             fields: list[str] | None) -> dict[str, Any]:
        target_fields = fields if fields else df.select_dtypes(
            include=[np.number]
        ).columns.tolist()

        corr_df = df[target_fields].corr()
        corr_matrix = corr_df.to_dict()

        return {
            "success": True,
            "operation": "correlation",
            "fields": target_fields,
            "correlation_matrix": corr_matrix,
        }

    def _rolling_calc(self, df: pd.DataFrame,
                      fields: list[str] | None,
                      params: dict[str, Any]) -> dict[str, Any]:
        window = params.get("window", 20)
        func = params.get("func", "mean")

        target_fields = fields if fields else df.select_dtypes(
            include=[np.number]
        ).columns.tolist()

        results = {}
        for field in target_fields:
            if field in df.columns:
                series = df[field].rolling(window=window)
                if func == "mean":
                    result = series.mean()
                elif func == "std":
                    result = series.std()
                elif func == "max":
                    result = series.max()
                elif func == "min":
                    result = series.min()
                elif func == "sum":
                    result = series.sum()
                else:
                    result = series.mean()

                results[field] = result.tolist()

        return {
            "success": True,
            "operation": "rolling_calc",
            "fields": target_fields,
            "window": window,
            "func": func,
            "results": results,
        }
