"""技术指标计算模块 — 统一入口。

提供三层路由的指标计算框架:
1. TDX 对齐实现（通达信公式风格）— 有则用
2. NumPy 核心实现（纯 numpy）— 主力
3. TA-Lib 封装（可选依赖）— 兜底

主要接口:
- compute_indicators(data, names, **params) -> dict
- INDICATOR_NAMES: 所有支持的指标名列表
- assess_trend_maturity(): 趋势成熟度评估

使用方式:
    from datacore.indicators import compute_indicators, INDICATOR_NAMES

    data = {
        "close": np.array([...]),
        "high": np.array([...]),
        "low": np.array([...]),
        "open": np.array([...]),
        "volume": np.array([...]),
    }
    result = compute_indicators(data, ["MA", "RSI", "MACD"])
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from datacore.indicators.core import (
    INDICATOR_MAP,
    get_indicator_names,
)
from datacore.indicators.trend_maturity import (
    assess_trend_maturity,
    TrendMaturityResult,
)


INDICATOR_NAMES: list[str] = get_indicator_names()


def compute_indicators(
    data: dict,
    names: str | list[str] = "all",
    use_tdx: bool = False,
    use_talib_fallback: bool = True,
    **params,
) -> dict[str, np.ndarray | dict[str, np.ndarray]]:
    """统一指标计算入口。

    三层路由: TDX（有则用）→ numpy core → TA-Lib（兜底）

    Args:
        data: 数据字典，需包含 close/high/low/open/volume 等 np.ndarray
        names: 指标名称或列表，"all" 表示计算所有支持的指标
        use_tdx: 是否优先使用 TDX 对齐实现
        use_talib_fallback: 是否使用 TA-Lib 作为兜底
        **params: 额外参数传递给指标函数（如 period, fast_period 等）

    Returns:
        指标结果字典，key 为指标名，value 为 ndarray 或 dict（多输出指标）

    Raises:
        ValueError: 指标名称不支持
        TypeError: data 格式不正确
    """
    if not isinstance(data, dict):
        raise TypeError("data 必须是 dict 类型，包含 close/high/low 等 ndarray")

    if "close" not in data:
        raise ValueError("data 必须包含 'close' 字段")

    close = data["close"]
    if not isinstance(close, np.ndarray):
        raise TypeError("data['close'] 必须是 np.ndarray")

    if names == "all" or names is None:
        names_list = INDICATOR_NAMES
    elif isinstance(names, str):
        names_list = [names.upper()]
    else:
        names_list = [n.upper() for n in names]

    results: dict[str, np.ndarray | dict[str, np.ndarray]] = {}

    for name in names_list:
        result = _compute_single_indicator(
            name, data, use_tdx, use_talib_fallback, params
        )
        if result is not None:
            results[name] = result

    return results


def _compute_single_indicator(
    name: str,
    data: dict,
    use_tdx: bool,
    use_talib_fallback: bool,
    params: dict,
) -> Optional[np.ndarray | dict[str, np.ndarray]]:
    """计算单个指标，按优先级尝试不同实现。

    优先级: TDX → numpy core → TA-Lib

    Args:
        name: 指标名（大写）
        data: 数据字典
        use_tdx: 是否使用 TDX 实现
        use_talib_fallback: 是否使用 TA-Lib 兜底
        params: 参数字典

    Returns:
        指标结果，所有实现都失败时返回 None
    """
    result = None

    # 第一层: TDX 对齐实现
    if use_tdx:
        result = _try_tdx(name, data, params)
        if result is not None:
            return result

    # 第二层: numpy core 实现（主力）
    result = _try_core(name, data, params)
    if result is not None:
        return result

    # 第三层: TA-Lib 兜底
    if use_talib_fallback:
        result = _try_talib(name, data, params)
        if result is not None:
            return result

    if name not in INDICATOR_MAP:
        raise ValueError(
            f"不支持的指标: {name}。支持的指标: {', '.join(INDICATOR_NAMES)}"
        )

    return None


def _try_core(name: str, data: dict, params: dict) -> Optional[np.ndarray | dict]:
    """尝试使用 numpy core 实现计算。"""
    func = INDICATOR_MAP.get(name)
    if func is None:
        return None

    try:
        close = data.get("close")
        high = data.get("high")
        low = data.get("low")
        volume = data.get("volume")
        open_ = data.get("open")

        if name in ["MA", "EMA", "SMA", "WMA", "RSI", "MTM", "ROC",
                     "BIAS", "TRIX", "PSY", "STDDEV", "VARIANCE",
                     "LINEARREG", "LINEARREG_SLOPE", "TSF"]:
            return func(close, **params)

        elif name in ["MACD", "BOLL"]:
            return func(close, **params)

        elif name == "DMA":
            return func(close, **params)

        elif name in ["KDJ", "CCI", "WR", "ATR", "DMI", "KELTNER",
                       "CHANDELIER", "MASS", "ULTOSC", "ADX"]:
            if high is None or low is None:
                return None
            return func(high, low, close, **params)

        elif name in ["MEDIAN_PRICE", "TYPICAL_PRICE", "WEIGHTED_CLOSE",
                       "TRANGE"]:
            if high is None or low is None:
                return None
            return func(high, low, close) if name != "MEDIAN_PRICE" else func(high, low)

        elif name == "AVG_PRICE":
            if high is None or low is None or open_ is None:
                return None
            return func(open_, high, low, close)

        elif name in ["OBV", "VR"]:
            if volume is None:
                return None
            return func(close, volume, **params) if name == "VR" else func(close, volume)

        elif name == "BRAR":
            if high is None or low is None or open_ is None:
                return None
            return func(high, low, close, open_, **params)

        elif name == "CR":
            if high is None or low is None:
                return None
            return func(high, low, close, **params)

        else:
            return None

    except Exception:
        return None


def _try_tdx(name: str, data: dict, params: dict) -> Optional[np.ndarray | dict]:
    """尝试使用 TDX 对齐实现计算。"""
    try:
        from datacore.indicators.tdx_compat import TDX_INDICATOR_MAP

        func = TDX_INDICATOR_MAP.get(name)
        if func is None:
            return None

        close = data.get("close")
        high = data.get("high")
        low = data.get("low")
        volume = data.get("volume")

        if name == "MA":
            return func(close, **params)

        elif name in ["MACD", "RSI", "BOLL"]:
            return func(close, **params)

        elif name in ["KDJ", "CCI", "WR", "ATR", "DMI"]:
            if high is None or low is None:
                return None
            return func(high, low, close, **params)

        elif name == "OBV":
            if volume is None:
                return None
            return func(close, volume)

        else:
            return None

    except Exception:
        return None


def _try_talib(name: str, data: dict, params: dict) -> Optional[np.ndarray | dict]:
    """尝试使用 TA-Lib 兜底计算。"""
    try:
        from datacore.indicators.talib_wrapper import compute_with_talib
        return compute_with_talib(name, data, **params)
    except Exception:
        return None


__all__ = [
    "compute_indicators",
    "INDICATOR_NAMES",
    "assess_trend_maturity",
    "TrendMaturityResult",
]
