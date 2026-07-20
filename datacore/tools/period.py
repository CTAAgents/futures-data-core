"""DataCorePeriodTool - 周期转换工具。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .base import DataCoreBaseTool


class DataCorePeriodTool(DataCoreBaseTool):
    """OHLCV 数据周期转换。

    支持从细粒度周期转换为粗粒度周期，如 1m → 5m → 15m → 60m → daily。
    """

    name = "datacore_period"
    description = (
        "OHLCV 数据周期转换。支持从细粒度转换为粗粒度。"
        "参数：data (list, 必需) - OHLCV 数据列表，每条需包含 datetime, open, high, low, close；"
        "target_period (str, 必需) - 目标周期，如 '5m', '15m', '30m', '60m', 'daily', 'weekly', 'monthly'；"
        "source_period (str, 可选) - 源周期，默认自动推断；"
        "include_volume (bool, 可选) - 是否包含成交量，默认 True"
    )

    def _run(self, data: list[dict[str, Any]], target_period: str,
             source_period: str = "", include_volume: bool = True,
             **kwargs: Any) -> dict[str, Any]:
        try:
            df = pd.DataFrame(data)

            if df.empty:
                return {
                    "success": True,
                    "source_period": source_period or "auto",
                    "target_period": target_period,
                    "original_count": 0,
                    "resampled_count": 0,
                    "data": [],
                }

            if "datetime" not in df.columns:
                raise ValueError("数据中缺少 datetime 列")

            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.set_index("datetime")

            result_df = self._resample(df, target_period, include_volume)

            result_data = result_df.reset_index().to_dict("records")

            return {
                "success": True,
                "source_period": source_period or "auto",
                "target_period": target_period,
                "original_count": len(data),
                "resampled_count": len(result_data),
                "data": result_data,
            }
        except Exception as e:
            return {
                "success": False,
                "target_period": target_period,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _resample(self, df: pd.DataFrame, target_period: str,
                  include_volume: bool) -> pd.DataFrame:
        period_map = {
            "1m": "1min", "5m": "5min", "10m": "10min",
            "15m": "15min", "30m": "30min", "60m": "60min",
            "1h": "1h", "2h": "2h", "4h": "4h",
            "daily": "D", "day": "D", "weekly": "W", "monthly": "M",
        }

        freq = period_map.get(target_period.lower(), target_period)

        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }

        if include_volume and "volume" in df.columns:
            agg_dict["volume"] = "sum"

        if "amount" in df.columns:
            agg_dict["amount"] = "sum"

        if "open_interest" in df.columns:
            agg_dict["open_interest"] = "last"

        result = df.resample(freq, label="left", closed="left").agg(agg_dict)
        result = result.dropna(how="all")

        return result
