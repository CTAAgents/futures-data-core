"""TA-Lib 封装兜底模块。

提供 TA-Lib 的可选封装，当 TA-Lib 可用时作为兜底计算方案。
导入失败时自动降级，不影响 core.py 的纯 numpy 实现。

使用三层路由: TDX(有则用) → numpy core → TA-Lib(兜底)
"""

from __future__ import annotations

import importlib.util
from typing import Optional

import numpy as np


_talib_available = None


def is_talib_available() -> bool:
    """检查 TA-Lib 是否可用。

    Returns:
        True 表示 TA-Lib 已安装且可导入
    """
    global _talib_available
    if _talib_available is not None:
        return _talib_available

    _talib_available = importlib.util.find_spec("talib") is not None
    return _talib_available


def _get_talib():
    """延迟导入 TA-Lib。

    Returns:
        talib 模块，如果不可用则返回 None
    """
    if not is_talib_available():
        return None
    try:
        import talib
        return talib
    except ImportError:
        global _talib_available
        _talib_available = False
        return None


def talib_ma(close: np.ndarray, period: int = 5,
             matype: int = 0) -> Optional[np.ndarray]:
    """TA-Lib MA 封装。

    Args:
        close: 收盘价序列
        period: 周期
        matype: MA 类型 (0=SMA, 1=EMA, 2=WMA, 3=DEMA, ...)

    Returns:
        MA 序列，TA-Lib 不可用时返回 None
    """
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.MA(close, timeperiod=period, matype=matype)
    except Exception:
        return None


def talib_ema(close: np.ndarray, period: int = 12) -> Optional[np.ndarray]:
    """TA-Lib EMA 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.EMA(close, timeperiod=period)
    except Exception:
        return None


def talib_rsi(close: np.ndarray, period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib RSI 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.RSI(close, timeperiod=period)
    except Exception:
        return None


def talib_macd(close: np.ndarray, fast_period: int = 12, slow_period: int = 26,
               signal_period: int = 9) -> Optional[dict[str, np.ndarray]]:
    """TA-Lib MACD 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        macd, signal, hist = talib.MACD(
            close,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period,
        )
        return {
            "macd": macd,
            "signal": signal,
            "histogram": hist,
        }
    except Exception:
        return None


def talib_boll(close: np.ndarray, period: int = 20,
               nbdev: float = 2.0) -> Optional[dict[str, np.ndarray]]:
    """TA-Lib BBANDS 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=period,
            nbdevup=nbdev,
            nbdevdn=nbdev,
            matype=0,
        )
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
        }
    except Exception:
        return None


def talib_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
              period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib ATR 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.ATR(high, low, close, timeperiod=period)
    except Exception:
        return None


def talib_stoch(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                fastk_period: int = 5, slowk_period: int = 3,
                slowd_period: int = 3) -> Optional[dict[str, np.ndarray]]:
    """TA-Lib STOCH 封装（KDJ 对应）。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        slowk, slowd = talib.STOCH(
            high, low, close,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowk_matype=0,
            slowd_period=slowd_period,
            slowd_matype=0,
        )
        slowj = 3 * slowk - 2 * slowd
        return {
            "k": slowk,
            "d": slowd,
            "j": slowj,
        }
    except Exception:
        return None


def talib_cci(high: np.ndarray, low: np.ndarray, close: np.ndarray,
              period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib CCI 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.CCI(high, low, close, timeperiod=period)
    except Exception:
        return None


def talib_willr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib WILLR 封装（威廉指标）。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.WILLR(high, low, close, timeperiod=period)
    except Exception:
        return None


def talib_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray,
              period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib ADX 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.ADX(high, low, close, timeperiod=period)
    except Exception:
        return None


def talib_dmi(high: np.ndarray, low: np.ndarray, close: np.ndarray,
              period: int = 14) -> Optional[dict[str, np.ndarray]]:
    """TA-Lib DMI 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        plus_di = talib.PLUS_DI(high, low, close, timeperiod=period)
        minus_di = talib.MINUS_DI(high, low, close, timeperiod=period)
        adx = talib.ADX(high, low, close, timeperiod=period)
        dx = talib.DX(high, low, close, timeperiod=period)
        return {
            "plus_di": plus_di,
            "minus_di": minus_di,
            "adx": adx,
            "dx": dx,
        }
    except Exception:
        return None


def talib_obv(close: np.ndarray, volume: np.ndarray) -> Optional[np.ndarray]:
    """TA-Lib OBV 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.OBV(close, volume)
    except Exception:
        return None


def talib_mom(close: np.ndarray, period: int = 10) -> Optional[np.ndarray]:
    """TA-Lib MOM 封装（动量）。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.MOM(close, timeperiod=period)
    except Exception:
        return None


def talib_roc(close: np.ndarray, period: int = 10) -> Optional[np.ndarray]:
    """TA-Lib ROC 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.ROC(close, timeperiod=period)
    except Exception:
        return None


def talib_trange(high: np.ndarray, low: np.ndarray,
                 close: np.ndarray) -> Optional[np.ndarray]:
    """TA-Lib TRANGE 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.TRANGE(high, low, close)
    except Exception:
        return None


def talib_stddev(close: np.ndarray, period: int = 20,
                 nbdev: float = 1.0) -> Optional[np.ndarray]:
    """TA-Lib STDDEV 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.STDDEV(close, timeperiod=period, nbdev=nbdev)
    except Exception:
        return None


def talib_linearreg(close: np.ndarray, period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib LINEARREG 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.LINEARREG(close, timeperiod=period)
    except Exception:
        return None


def talib_linearreg_slope(close: np.ndarray,
                          period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib LINEARREG_SLOPE 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.LINEARREG_SLOPE(close, timeperiod=period)
    except Exception:
        return None


def talib_tsf(close: np.ndarray, period: int = 14) -> Optional[np.ndarray]:
    """TA-Lib TSF 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.TSF(close, timeperiod=period)
    except Exception:
        return None


def talib_ultosc(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 period1: int = 7, period2: int = 14,
                 period3: int = 28) -> Optional[np.ndarray]:
    """TA-Lib ULTOSC 封装。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.ULTOSC(
            high, low, close,
            timeperiod1=period1,
            timeperiod2=period2,
            timeperiod3=period3,
        )
    except Exception:
        return None


def talib_mass(high: np.ndarray, low: np.ndarray,
               fast_period: int = 9, slow_period: int = 25) -> Optional[np.ndarray]:
    """TA-Lib MASS 封装（梅斯线）。"""
    talib = _get_talib()
    if talib is None:
        return None
    try:
        return talib.MASS(high, low,
                          fastperiod=fast_period,
                          slowperiod=slow_period)
    except Exception:
        return None


TALIB_FUNCTION_MAP: dict[str, callable] = {
    "MA": talib_ma,
    "EMA": talib_ema,
    "RSI": talib_rsi,
    "MACD": talib_macd,
    "BOLL": talib_boll,
    "ATR": talib_atr,
    "KDJ": talib_stoch,
    "CCI": talib_cci,
    "WR": talib_willr,
    "ADX": talib_adx,
    "DMI": talib_dmi,
    "OBV": talib_obv,
    "MTM": talib_mom,
    "ROC": talib_roc,
    "TRANGE": talib_trange,
    "STDDEV": talib_stddev,
    "LINEARREG": talib_linearreg,
    "LINEARREG_SLOPE": talib_linearreg_slope,
    "TSF": talib_tsf,
    "ULTOSC": talib_ultosc,
    "MASS": talib_mass,
}


def get_talib_indicator_names() -> list[str]:
    """获取所有 TA-Lib 封装的指标名称。

    Returns:
        TA-Lib 指标名称列表
    """
    return sorted(list(TALIB_FUNCTION_MAP.keys()))


def compute_with_talib(name: str, data: dict,
                       **params) -> Optional[np.ndarray | dict[str, np.ndarray]]:
    """使用 TA-Lib 计算指定指标。

    Args:
        name: 指标名称（大写）
        data: 数据字典，包含 close, high, low, volume 等
        **params: 额外参数

    Returns:
        指标结果（数组或字典），TA-Lib 不可用时返回 None
    """
    if not is_talib_available():
        return None

    func = TALIB_FUNCTION_MAP.get(name.upper())
    if func is None:
        return None

    try:
        close = data.get("close")
        high = data.get("high")
        low = data.get("low")
        volume = data.get("volume")

        if name in ["MA", "EMA", "RSI", "MTM", "ROC", "STDDEV",
                     "LINEARREG", "LINEARREG_SLOPE", "TSF"]:
            return func(close, **params)
        elif name in ["MACD", "BOLL"]:
            return func(close, **params)
        elif name in ["ATR", "CCI", "WR", "ADX", "DMI", "KDJ",
                       "TRANGE", "ULTOSC", "MASS"]:
            return func(high, low, close, **params)
        elif name == "OBV":
            return func(close, volume)
        else:
            return None
    except Exception:
        return None
