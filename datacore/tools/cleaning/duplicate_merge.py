"""DuplicateMergeTool - 重复数据合并工具。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..base import DataCoreBaseTool


class DuplicateMergeTool(DataCoreBaseTool):
    """重复数据检测与合并。

    检测并合并重复数据记录，支持多种合并策略。
    """

    name = "datacore_duplicate_merge"
    description = (
        "重复数据检测与合并。检测并合并重复记录。"
        "参数：data (list, 必需) - 数据列表；"
        "keys (list, 必需) - 判断重复的键字段列表；"
        "strategy (str, 可选) - 合并策略，'first'/'last'/'mean'/'max'/'min'/'concat'，默认 'first'；"
        "keep_source (bool, 可选) - 是否保留来源信息，默认 False"
    )

    def _run(self, data: list[dict[str, Any]], keys: list[str],
             strategy: str = "first", keep_source: bool = False,
             **kwargs: Any) -> dict[str, Any]:
        try:
            df = pd.DataFrame(data)

            if df.empty:
                return {
                    "success": True,
                    "original_count": 0,
                    "duplicate_count": 0,
                    "merged_count": 0,
                    "data": [],
                }

            original_count = len(df)
            dup_mask = df.duplicated(subset=keys, keep=False)
            duplicate_count = dup_mask.sum()

            if strategy == "first":
                merged = df.drop_duplicates(subset=keys, keep="first")
            elif strategy == "last":
                merged = df.drop_duplicates(subset=keys, keep="last")
            elif strategy == "mean":
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                agg_dict = {col: "mean" for col in numeric_cols if col not in keys}
                other_cols = [col for col in df.columns if col not in keys and col not in numeric_cols]
                for col in other_cols:
                    agg_dict[col] = "first"
                merged = df.groupby(keys, as_index=False).agg(agg_dict)
            elif strategy == "max":
                merged = df.sort_values(keys).drop_duplicates(subset=keys, keep="last")
            elif strategy == "min":
                merged = df.sort_values(keys).drop_duplicates(subset=keys, keep="first")
            else:
                merged = df.drop_duplicates(subset=keys, keep="first")

            merged_count = original_count - len(merged)
            result_data = merged.to_dict("records")

            return {
                "success": True,
                "original_count": original_count,
                "duplicate_count": int(duplicate_count),
                "merged_count": int(merged_count),
                "final_count": len(result_data),
                "strategy": strategy,
                "data": result_data,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
