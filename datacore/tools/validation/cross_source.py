"""CrossSourceVerifyTool - 跨源数据校验工具。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..base import DataCoreBaseTool


class CrossSourceVerifyTool(DataCoreBaseTool):
    """多数据源交叉验证。

    对比不同数据源的同一指标数据，计算差异度，
    评估数据一致性和可靠性。
    """

    name = "datacore_cross_source_verify"
    description = (
        "多数据源交叉验证。对比不同数据源的同一指标数据。"
        "参数：source_data (dict, 必需) - 各数据源的数据，key 为源名，value 为数据列表；"
        "field (str, 必需) - 要对比的字段名；"
        "key_field (str, 可选) - 对齐键字段，默认 'datetime'；"
        "tolerance (float, 可选) - 容差阈值，默认 0.01 (1%)；"
        "method (str, 可选) - 对比方法，'diff'/'pct_diff'/'correlation'，默认 'pct_diff'"
    )

    def _run(self, source_data: dict[str, list[dict[str, Any]]], field: str,
             key_field: str = "datetime", tolerance: float = 0.01,
             method: str = "pct_diff", **kwargs: Any) -> dict[str, Any]:
        try:
            dfs = {}
            for source_name, data_list in source_data.items():
                df = pd.DataFrame(data_list)
                if key_field in df.columns:
                    if key_field == "datetime":
                        df[key_field] = pd.to_datetime(df[key_field])
                    df = df.set_index(key_field)
                dfs[source_name] = df

            sources = list(dfs.keys())
            if len(sources) < 2:
                return {
                    "success": False,
                    "error": "至少需要 2 个数据源进行对比",
                    "provided_sources": sources,
                }

            comparison = pd.DataFrame()
            for name, df in dfs.items():
                if field in df.columns:
                    comparison[name] = df[field]

            comparison = comparison.dropna(how="all")
            result = self._compare(comparison, method, tolerance)

            return {
                "success": True,
                "sources": sources,
                "field": field,
                "method": method,
                "tolerance": tolerance,
                "compared_points": len(comparison),
                **result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _compare(self, comparison: pd.DataFrame, method: str,
                 tolerance: float) -> dict[str, Any]:
        sources = comparison.columns.tolist()
        base_source = sources[0]

        results = {}
        total_consistent = 0
        total_points = len(comparison)

        for source in sources[1:]:
            valid_mask = comparison[[base_source, source]].notna().all(axis=1)
            valid_count = valid_mask.sum()

            if valid_count == 0:
                results[source] = {
                    "valid_points": 0,
                    "consistent_points": 0,
                    "consistency_rate": 0.0,
                    "avg_diff": None,
                    "max_diff": None,
                }
                continue

            base_vals = comparison.loc[valid_mask, base_source].values
            comp_vals = comparison.loc[valid_mask, source].values

            if method == "pct_diff":
                diff = np.abs(comp_vals - base_vals) / np.abs(base_vals)
                consistent = (diff <= tolerance).sum()
                avg_diff = float(np.mean(diff))
                max_diff = float(np.max(diff))
            elif method == "diff":
                diff = np.abs(comp_vals - base_vals)
                consistent = (diff <= tolerance).sum()
                avg_diff = float(np.mean(diff))
                max_diff = float(np.max(diff))
            elif method == "correlation":
                corr = np.corrcoef(base_vals, comp_vals)[0, 1]
                consistent = int(valid_count * (1 if corr >= 1 - tolerance else 0))
                avg_diff = None
                max_diff = None
            else:
                diff = np.abs(comp_vals - base_vals)
                consistent = (diff <= tolerance).sum()
                avg_diff = float(np.mean(diff))
                max_diff = float(np.max(diff))

            results[source] = {
                "valid_points": int(valid_count),
                "consistent_points": int(consistent),
                "consistency_rate": float(consistent / valid_count) if valid_count > 0 else 0.0,
                "avg_diff": avg_diff,
                "max_diff": max_diff,
            }
            total_consistent += consistent

        overall_consistency = (
            float(total_consistent / (len(sources) - 1) / total_points)
            if total_points > 0 and len(sources) > 1 else 0.0
        )

        return {
            "base_source": base_source,
            "comparisons": results,
            "overall_consistency": overall_consistency,
        }
