"""DataCoreIndicatorsTool - 技术指标计算工具。"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from .base import DataCoreBaseTool


class DataCoreIndicatorsTool(DataCoreBaseTool):
    """计算技术指标。

    支持 40+ 常用技术指标，包括移动平均线、动量指标、震荡指标、
    波动率指标、成交量指标、趋势指标等。
    """

    name = "datacore_indicators"
    description = (
        "计算技术指标。支持 MA、EMA、RSI、MACD、KDJ、BOLL、ATR 等 40+ 指标。"
        "参数：indicator (str, 必需) - 指标名称，如 'MA'、'EMA'、'RSI'、'MACD'、'KDJ'、'BOLL'、'ATR' 等；"
        "close (list, 必需) - 收盘价序列；"
        "high (list, 可选) - 最高价序列（部分指标需要）；"
        "low (list, 可选) - 最低价序列（部分指标需要）；"
        "volume (list, 可选) - 成交量序列（部分指标需要）；"
        "period (int, 可选) - 周期参数，默认指标特定；"
        "params (dict, 可选) - 其他指标特定参数"
    )

    def _run(self, indicator: str, close: list[float],
             high: Optional[list[float]] = None, low: Optional[list[float]] = None,
             volume: Optional[list[float]] = None, period: Optional[int] = None,
             params: Optional[dict[str, Any]] = None, **kwargs: Any) -> dict[str, Any]:

        close_arr = np.array(close, dtype=float)
        high_arr = np.array(high, dtype=float) if high is not None else None
        low_arr = np.array(low, dtype=float) if low is not None else None
        volume_arr = np.array(volume, dtype=float) if volume is not None else None

        indicator_lower = indicator.lower()
        params = params or {}

        try:
            result = self._calculate(
                indicator_lower, close_arr, high_arr, low_arr, volume_arr,
                period, params
            )

            if isinstance(result, np.ndarray):
                result_list = result.tolist()
            elif isinstance(result, dict):
                result_list = {k: v.tolist() if isinstance(v, np.ndarray) else v
                               for k, v in result.items()}
            else:
                result_list = result

            return {
                "success": True,
                "indicator": indicator,
                "period": period,
                "result": result_list,
                "length": len(close),
            }
        except Exception as e:
            return {
                "success": False,
                "indicator": indicator,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _calculate(self, indicator: str, close: np.ndarray,
                   high: np.ndarray | None, low: np.ndarray | None,
                   volume: np.ndarray | None, period: int | None,
                   params: dict[str, Any]) -> Any:
        from ..indicators.core import (
            ma, ema, rsi, macd, kdj, boll, atr, sma, wma, dma, mtm, roc,
            bias, trix, cci, wr, psy, mass, obv, vr, dmi, brar, cr,
        )

        indicator_map = {
            "ma": lambda: ma(close, period or 5),
            "sma": lambda: sma(close, period or 5),
            "ema": lambda: ema(close, period or 12),
            "wma": lambda: wma(close, period or 5),
            "dma": lambda: dma(close, period or 10),
            "rsi": lambda: rsi(close, period or 14),
            "macd": lambda: macd(close, **params) if params else macd(close),
            "kdj": lambda: kdj(high, low, close, period or 9),
            "boll": lambda: boll(close, period or 20),
            "atr": lambda: atr(high, low, close, period or 14),
            "mtm": lambda: mtm(close, period or 10),
            "roc": lambda: roc(close, period or 12),
            "bias": lambda: bias(close, period or 6),
            "trix": lambda: trix(close, period or 12),
            "cci": lambda: cci(high, low, close, period or 14),
            "wr": lambda: wr(high, low, close, period or 14),
            "psy": lambda: psy(close, period or 12),
            "mass": lambda: mass(high, low, period or 9),
            "obv": lambda: obv(close, volume),
            "vr": lambda: vr(close, volume, period or 26),
            "dmi": lambda: dmi(high, low, close, period or 14),
            "brar": lambda: brar(high, low, close, period or 26),
            "cr": lambda: cr(high, low, close, period or 26),
        }

        calc_fn = indicator_map.get(indicator)
        if calc_fn is None:
            raise ValueError(f"不支持的指标: {indicator}")

        return calc_fn()
