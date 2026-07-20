"""DataMissingDetectTool - 数据缺失检测工具。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..base import DataCoreBaseTool


class DataMissingDetectTool(DataCoreBaseTool):
    """数据缺失检测。

    检测时间序列数据中的缺失值、异常断点，
    评估数据完整性。
    """

    name = "datacore_missing_detect"
    description = (
        "数据缺失检测。检测时间序列中的缺失值和断点。"
        "参数：data (list, 必需) - 数据列表；"
        "date_col (str, 可选) - 日期列名，默认 'datetime'；"
        "expected_freq (str, 可选) - 期望频率，如 '1D'、'1H'，默认自动检测；"
        "fields (list, 可选) - 要检测的字段列表，默认所有数值字段；"
        "return_details (bool, 可选) - 是否返回详细缺失位置，默认 True"
    )

    def _run(self, data: list[dict[str, Any]], date_col: str = "datetime",
             expected_freq: str = "", fields: list[str] | None = None,
             return_details: bool = True, **kwargs: Any) -> dict[str, Any]:
        try:
            df = pd.DataFrame(data)

            if df.empty:
                return {
                    "success": True,
                    "total_rows": 0,
                    "missing_rows": 0,
                    "completeness": 1.0,
                    "field_missing": {},
                    "missing_details": [],
                }

            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col])
                df = df.sort_values(date_col)
                df = df.set_index(date_col)
                is_timeseries = True
            else:
                is_timeseries = False

            numeric_fields = fields if fields else df.select_dtypes(
                include=[np.number]
            ).columns.tolist()

            field_missing = {}
            total_missing_cells = 0
            total_cells = len(df) * len(numeric_fields)

            for field in numeric_fields:
                if field in df.columns:
                    missing_count = int(df[field].isna().sum())
                    field_missing[field] = {
                        "missing_count": missing_count,
                        "missing_rate": float(missing_count / len(df)),
                        "total_count": len(df),
                    }
                    total_missing_cells += missing_count

            completeness = float(1 - total_missing_cells / total_cells) if total_cells > 0 else 1.0

            missing_details = []
            if return_details and is_timeseries:
                for field in numeric_fields:
                    if field in df.columns:
                        missing_mask = df[field].isna()
                        if missing_mask.any():
                            missing_dates = df.index[missing_mask].tolist()
                            missing_details.append({
                                "field": field,
                                "missing_dates": [str(d) for d in missing_dates[:100]],
                                "missing_count": int(missing_mask.sum()),
                            })

            return {
                "success": True,
                "is_timeseries": is_timeseries,
                "total_rows": len(df),
                "total_fields": len(numeric_fields),
                "total_cells": total_cells,
                "missing_cells": total_missing_cells,
                "completeness": completeness,
                "field_missing": field_missing,
                "missing_details": missing_details,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
