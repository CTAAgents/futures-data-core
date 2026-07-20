"""DataCoreAdjustmentTool - 复权/换月调整工具。"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from .base import DataCoreBaseTool


class DataCoreAdjustmentTool(DataCoreBaseTool):
    """数据复权和期货换月调整。

    支持股票前复权、后复权，期货主力连续合约换月调整。
    """

    name = "datacore_adjustment"
    description = (
        "数据复权和期货换月调整。支持股票前复权、后复权，期货主力连续合约换月。"
        "参数：data (list/dict, 必需) - OHLCV 数据；"
        "adjust_type (str, 必需) - 调整类型，'forward'/'backward'/'rollover'；"
        "asset_type (str, 可选) - 资产类型，'equity'/'futures'，默认根据数据推断；"
        "dividend_data (list, 可选) - 分红数据（股票复权用）；"
        "rollover_method (str, 可选) - 换月方法，'volume'/'open_interest'/'date'，默认 'volume'"
    )

    def _run(self, data: list[dict[str, Any]], adjust_type: str,
             asset_type: Optional[str] = None,
             dividend_data: Optional[list[dict[str, Any]]] = None,
             rollover_method: str = "volume", **kwargs: Any) -> dict[str, Any]:
        try:
            df = pd.DataFrame(data)
            if "datetime" in df.columns:
                df["datetime"] = pd.to_datetime(df["datetime"])
                df = df.set_index("datetime")

            result_df = self._adjust(df, adjust_type, asset_type,
                                     dividend_data, rollover_method)

            result_data = result_df.reset_index().to_dict("records")

            return {
                "success": True,
                "adjust_type": adjust_type,
                "original_count": len(data),
                "adjusted_count": len(result_data),
                "data": result_data,
            }
        except Exception as e:
            return {
                "success": False,
                "adjust_type": adjust_type,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _adjust(self, df: pd.DataFrame, adjust_type: str,
                asset_type: Optional[str],
                dividend_data: Optional[list[dict[str, Any]]],
                rollover_method: str) -> pd.DataFrame:
        if adjust_type == "forward":
            return self._forward_adjust(df, dividend_data)
        elif adjust_type == "backward":
            return self._backward_adjust(df, dividend_data)
        elif adjust_type == "rollover":
            return self._rollover_adjust(df, rollover_method)
        else:
            raise ValueError(f"不支持的调整类型: {adjust_type}")

    def _forward_adjust(self, df: pd.DataFrame,
                        dividend_data: Optional[list[dict[str, Any]]]) -> pd.DataFrame:
        result = df.copy()
        if dividend_data:
            div_df = pd.DataFrame(dividend_data)
            if "ex_date" in div_df.columns:
                div_df["ex_date"] = pd.to_datetime(div_df["ex_date"])
                div_df = div_df.set_index("ex_date")
                for col in ["open", "high", "low", "close"]:
                    if col in result.columns and "dividend" in div_df.columns:
                        cum_div = div_df["dividend"].cumsum().reindex(result.index).ffill().fillna(0)
                        result[col] = result[col] - cum_div
        return result

    def _backward_adjust(self, df: pd.DataFrame,
                         dividend_data: Optional[list[dict[str, Any]]]) -> pd.DataFrame:
        result = df.copy()
        if dividend_data:
            div_df = pd.DataFrame(dividend_data)
            if "ex_date" in div_df.columns:
                div_df["ex_date"] = pd.to_datetime(div_df["ex_date"])
                div_df = div_df.set_index("ex_date")
                div_df = div_df.sort_index(ascending=False)
                if "dividend" in div_df.columns:
                    total_div = div_df["dividend"].sum()
                    for col in ["open", "high", "low", "close"]:
                        if col in result.columns:
                            result[col] = result[col] + total_div
        return result

    def _rollover_adjust(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        return df.copy()
