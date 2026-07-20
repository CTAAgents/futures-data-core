"""DateAlignTool - 日期对齐工具。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..base import DataCoreBaseTool


class DateAlignTool(DataCoreBaseTool):
    """多序列日期对齐。

    将多个时间序列对齐到同一时间轴，缺失值用指定方法填充。
    """

    name = "datacore_date_align"
    description = (
        "多序列日期对齐。将多个时间序列对齐到同一时间轴。"
        "参数：series (dict, 必需) - 多个数据序列，key 为序列名，value 为数据列表；"
        "date_col (str, 可选) - 日期列名，默认 'datetime'；"
        "method (str, 可选) - 缺失值填充方法，'ffill'/'bfill'/'interpolate'/'drop'，默认 'ffill'；"
        "how (str, 可选) - 对齐方式，'inner'/'outer'/'left'/'right'，默认 'outer'"
    )

    def _run(self, series: dict[str, list[dict[str, Any]]],
             date_col: str = "datetime", method: str = "ffill",
             how: str = "outer", **kwargs: Any) -> dict[str, Any]:
        try:
            dfs = {}
            for name, data_list in series.items():
                df = pd.DataFrame(data_list)
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col])
                    df = df.set_index(date_col)
                dfs[name] = df

            all_dates = pd.DatetimeIndex([])
            for df in dfs.values():
                all_dates = all_dates.union(df.index)

            all_dates = all_dates.sort_values()

            result = {}
            for name, df in dfs.items():
                aligned = df.reindex(all_dates)
                if method == "ffill":
                    aligned = aligned.ffill()
                elif method == "bfill":
                    aligned = aligned.bfill()
                elif method == "interpolate":
                    aligned = aligned.interpolate()
                elif method == "drop":
                    aligned = aligned.dropna()

                result[name] = aligned.reset_index().to_dict("records")

            return {
                "success": True,
                "date_count": len(all_dates),
                "series_count": len(series),
                "method": method,
                "how": how,
                "data": result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
