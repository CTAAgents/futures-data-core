"""通达信 (TDX) 风格指标对齐实现。

提供与通达信公式系统行为一致的指标实现，
包括 TDX 特有的算法细节和参数默认值。

与 core.py 的主要区别:
- TDX 的 MA 函数支持多种移动平均类型（通过 M1/M2 参数指定）
- TDX 的 KDJ 使用特定的 SMA 平滑方式
- TDX 的 MACD 参数默认值与标准略有不同
- 部分指标的边界处理和初始值计算方式不同
"""

from __future__ import annotations

import numpy as np

from datacore.indicators.core import _shift


def tdx_ma(close: np.ndarray, period: int, ma_type: int = 0) -> np.ndarray:
    """通达信风格 MA 函数。

    TDX 的 MA 支持多种平均类型:
    0=SMA 简单移动平均
    1=EMA 指数移动平均
    2=WMA 加权移动平均
    3=SMA 平滑移动平均（通达信特有的SMA）

    Args:
        close: 收盘价序列
        period: 周期
        ma_type: 平均类型 (0-3)

    Returns:
        MA 序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)

    if ma_type == 0:
        return _tdx_simple_ma(close, period)
    elif ma_type == 1:
        return _tdx_ema(close, period)
    elif ma_type == 2:
        return _tdx_wma(close, period)
    elif ma_type == 3:
        return _tdx_smoothed_ma(close, period)
    else:
        return _tdx_simple_ma(close, period)


def _tdx_simple_ma(close: np.ndarray, period: int) -> np.ndarray:
    """TDX 风格简单移动平均。"""
    result = np.full_like(close, np.nan, dtype=float)
    cumsum = np.cumsum(close, dtype=float)
    result[period - 1:] = (
        cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])
    ) / period
    return result


def _tdx_ema(close: np.ndarray, period: int) -> np.ndarray:
    """TDX 风格指数移动平均。

    TDX 的 EMA 与标准 EMA 算法一致，alpha = 2 / (period + 1)
    """
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(close, dtype=float)
    result[0] = close[0]
    for i in range(1, len(close)):
        result[i] = alpha * close[i] + (1 - alpha) * result[i - 1]
    result[:period - 1] = np.nan
    return result


def _tdx_wma(close: np.ndarray, period: int) -> np.ndarray:
    """TDX 风格加权移动平均。

    权重为 1, 2, ..., period，越近权重越大。
    """
    weights = np.arange(1, period + 1, dtype=float)
    weights /= weights.sum()
    result = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        result[i] = np.sum(close[i - period + 1:i + 1] * weights)
    return result


def _tdx_smoothed_ma(close: np.ndarray, period: int) -> np.ndarray:
    """TDX 风格平滑移动平均（SMA函数）。

    TDX 的 SMA(X, N, M) 等价于:
    Y = (M * X + (N - M) * Y') / N
    这里 M=1（默认）
    """
    result = np.zeros_like(close, dtype=float)
    result[0] = close[0]
    for i in range(1, len(close)):
        result[i] = (result[i - 1] * (period - 1) + close[i]) / period
    result[:period - 1] = np.nan
    return result


def tdx_kdj(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            n: int = 9, m1: int = 3, m2: int = 3) -> dict[str, np.ndarray]:
    """通达信风格 KDJ 指标。

    TDX 的 KDJ 计算方式:
    RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
    K = SMA(RSV, M1, 1)
    D = SMA(K, M2, 1)
    J = 3 * K - 2 * D

    与 core.py 的区别在于初始值的处理和边界条件。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        n: RSV 周期
        m1: K 线周期
        m2: D 线周期

    Returns:
        包含 k, d, j 三个序列的字典
    """
    if n <= 0 or len(close) < n:
        return {
            "k": np.full_like(close, np.nan, dtype=float),
            "d": np.full_like(close, np.nan, dtype=float),
            "j": np.full_like(close, np.nan, dtype=float),
        }

    hhv = np.full_like(high, np.nan, dtype=float)
    llv = np.full_like(low, np.nan, dtype=float)
    for i in range(n - 1, len(close)):
        hhv[i] = np.max(high[i - n + 1:i + 1])
        llv[i] = np.min(low[i - n + 1:i + 1])

    rsv = np.where(hhv == llv, 50.0, (close - llv) / (hhv - llv) * 100.0)
    rsv[:n - 1] = np.nan

    k_line = np.full_like(close, np.nan, dtype=float)
    d_line = np.full_like(close, np.nan, dtype=float)

    k_val = 50.0
    d_val = 50.0
    for i in range(n - 1, len(close)):
        k_val = (rsv[i] + (m1 - 1) * k_val) / m1
        d_val = (k_val + (m2 - 1) * d_val) / m2
        k_line[i] = k_val
        d_line[i] = d_val

    j_line = 3 * k_line - 2 * d_line

    return {
        "k": k_line,
        "d": d_line,
        "j": j_line,
    }


def tdx_macd(close: np.ndarray, fast_period: int = 12, slow_period: int = 26,
             signal_period: int = 9) -> dict[str, np.ndarray]:
    """通达信风格 MACD 指标。

    TDX 的 MACD 输出:
    DIF = EMA(CLOSE, FAST) - EMA(CLOSE, SLOW)
    DEA = EMA(DIF, SIGNAL)
    MACD = 2 * (DIF - DEA)

    注意: TDX 的 MACD 柱是 2*(DIF-DEA)，而不是 DIF-DEA

    Args:
        close: 收盘价序列
        fast_period: 快线周期
        slow_period: 慢线周期
        signal_period: 信号线周期

    Returns:
        包含 dif, dea, macd 三个序列的字典
    """
    ema_fast = _tdx_ema(close, fast_period)
    ema_slow = _tdx_ema(close, slow_period)

    dif = ema_fast - ema_slow
    dif = np.where(np.isnan(dif), 0.0, dif)

    dea = np.zeros_like(close, dtype=float)
    dea[0] = dif[0]
    alpha = 2.0 / (signal_period + 1)
    for i in range(1, len(close)):
        dea[i] = alpha * dif[i] + (1 - alpha) * dea[i - 1]

    macd_hist = 2 * (dif - dea)

    dif = np.where(ema_slow == 0, np.nan, dif)
    dea = np.where(ema_slow == 0, np.nan, dea)
    macd_hist = np.where(ema_slow == 0, np.nan, macd_hist)

    return {
        "dif": dif,
        "dea": dea,
        "macd": macd_hist,
    }


def tdx_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """通达信风格 RSI 指标。

    TDX 的 RSI 计算:
    LC = REF(CLOSE, 1)
    RSI = SMA(MAX(CLOSE - LC, 0), N, 1) / SMA(ABS(CLOSE - LC), N, 1) * 100

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        RSI 序列
    """
    if period <= 0 or len(close) < period + 1:
        return np.full_like(close, np.nan, dtype=float)

    delta = close - _shift(close, 1)
    delta[0] = 0.0

    gain = np.maximum(delta, 0.0)
    abs_delta = np.abs(delta)

    gain_sma = np.zeros_like(close, dtype=float)
    loss_sma = np.zeros_like(close, dtype=float)
    gain_sma[0] = gain[0]
    loss_sma[0] = abs_delta[0]

    for i in range(1, len(close)):
        gain_sma[i] = (gain[i] + (period - 1) * gain_sma[i - 1]) / period
        loss_sma[i] = (abs_delta[i] + (period - 1) * loss_sma[i - 1]) / period

    rsi_val = np.where(loss_sma == 0, 100.0, gain_sma / loss_sma * 100.0)
    rsi_val[:period] = np.nan

    return rsi_val


def tdx_boll(close: np.ndarray, period: int = 20, width: float = 2.0) -> dict[str, np.ndarray]:
    """通达信风格布林带。

    TDX 布林带:
    MID = MA(CLOSE, N)
    UPPER = MID + WIDTH * STD(CLOSE, N)
    LOWER = MID - WIDTH * STD(CLOSE, N)

    Args:
        close: 收盘价序列
        period: 周期
        width: 带宽倍数

    Returns:
        包含 upper, middle, lower 三个序列的字典
    """
    if period <= 0 or len(close) < period:
        return {
            "upper": np.full_like(close, np.nan, dtype=float),
            "middle": np.full_like(close, np.nan, dtype=float),
            "lower": np.full_like(close, np.nan, dtype=float),
        }

    mid = _tdx_simple_ma(close, period)
    std = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1:i + 1], ddof=0)

    upper = mid + width * std
    lower = mid - width * std

    return {
        "upper": upper,
        "middle": mid,
        "lower": lower,
    }


def tdx_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """通达信风格 ATR 指标。

    TDX 的 ATR 使用 MA(TR, N) 而不是 Wilder 平滑。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        ATR 序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)

    prev_close = _shift(close, 1)
    prev_close[0] = close[0]

    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ),
    )

    return _tdx_simple_ma(tr, period)


def tdx_dmi(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            period: int = 14) -> dict[str, np.ndarray]:
    """通达信风格 DMI 指标。

    TDX 的 DMI:
    MTR = SUM(TR, N) （累加 N 周期 TR）
    HD = HIGH - REF(HIGH, 1)
    LD = REF(LOW, 1) - LOW
    DMP = SUM(IF(HD > 0 AND HD > LD, HD, 0), N)
    DMM = SUM(IF(LD > 0 AND LD > HD, LD, 0), N)
    PDI = DMP * 100 / MTR
    MDI = DMM * 100 / MTR
    ADX = MA(ABS(MDI - PDI) / (MDI + PDI) * 100, 6)

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        包含 pdi, mdi, adx, adxr 四个序列的字典
    """
    if period <= 0 or len(close) < period + 1:
        return {
            "pdi": np.full_like(close, np.nan, dtype=float),
            "mdi": np.full_like(close, np.nan, dtype=float),
            "adx": np.full_like(close, np.nan, dtype=float),
            "adxr": np.full_like(close, np.nan, dtype=float),
        }

    prev_high = _shift(high, 1)
    prev_low = _shift(low, 1)
    prev_close = _shift(close, 1)
    prev_high[0] = high[0]
    prev_low[0] = low[0]
    prev_close[0] = close[0]

    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ),
    )

    hd = high - prev_high
    ld = prev_low - low

    dmp = np.where((hd > 0) & (hd > ld), hd, 0.0)
    dmm = np.where((ld > 0) & (ld > hd), ld, 0.0)

    tr_sum = np.zeros_like(close, dtype=float)
    dmp_sum = np.zeros_like(close, dtype=float)
    dmm_sum = np.zeros_like(close, dtype=float)

    tr_cumsum = np.cumsum(tr)
    dmp_cumsum = np.cumsum(dmp)
    dmm_cumsum = np.cumsum(dmm)

    for i in range(period - 1, len(close)):
        if i >= period:
            tr_sum[i] = tr_cumsum[i] - tr_cumsum[i - period]
            dmp_sum[i] = dmp_cumsum[i] - dmp_cumsum[i - period]
            dmm_sum[i] = dmm_cumsum[i] - dmm_cumsum[i - period]
        else:
            tr_sum[i] = tr_cumsum[i]
            dmp_sum[i] = dmp_cumsum[i]
            dmm_sum[i] = dmm_cumsum[i]

    pdi = np.where(tr_sum == 0, 0.0, dmp_sum / tr_sum * 100.0)
    mdi = np.where(tr_sum == 0, 0.0, dmm_sum / tr_sum * 100.0)
    pdi[:period - 1] = np.nan
    mdi[:period - 1] = np.nan

    di_sum = pdi + mdi
    dx = np.where(di_sum == 0, 0.0, np.abs(pdi - mdi) / di_sum * 100.0)
    dx[:period - 1] = np.nan
    dx_valid = np.where(np.isnan(dx), 0.0, dx)

    adx_period = 6
    adx_val = _tdx_simple_ma(dx_valid, adx_period)
    adx_val[:period + adx_period - 2] = np.nan

    adxr_period = 6
    adxr_val = np.full_like(close, np.nan, dtype=float)
    adxr_valid = np.where(np.isnan(adx_val), 0.0, adx_val)
    adxr_shift = _shift(adxr_valid, adxr_period)
    adxr_val = (adxr_valid + adxr_shift) / 2.0
    adxr_val[:period + adx_period + adxr_period - 3] = np.nan

    return {
        "pdi": pdi,
        "mdi": mdi,
        "adx": adx_val,
        "adxr": adxr_val,
    }


def tdx_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """通达信风格 OBV 能量潮。

    TDX 的 OBV:
    VA = IF(CLOSE > REF(CLOSE, 1), VOLUME, IF(CLOSE < REF(CLOSE, 1), -VOLUME, 0))
    OBV = SUM(VA, 0) （从第一天开始累加）

    Args:
        close: 收盘价序列
        volume: 成交量序列

    Returns:
        OBV 序列
    """
    if len(close) == 0:
        return np.array([], dtype=float)

    prev_close = _shift(close, 1)
    prev_close[0] = close[0]

    va = np.where(
        close > prev_close, volume,
        np.where(close < prev_close, -volume, 0.0)
    )

    obv_val = np.cumsum(va)
    obv_val[0] = 0.0

    return obv_val


def tdx_wr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """通达信风格威廉指标。

    TDX 的 WR:
    WR = 100 * (HHV(HIGH, N) - CLOSE) / (HHV(HIGH, N) - LLV(LOW, N))

    注意: TDX 的 WR 是正值 (0-100)，而标准 Williams %R 是负值 (-100 到 0)

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        WR 序列 (0-100)
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)

    hhv = np.full_like(high, np.nan, dtype=float)
    llv = np.full_like(low, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        hhv[i] = np.max(high[i - period + 1:i + 1])
        llv[i] = np.min(low[i - period + 1:i + 1])

    wr_val = np.where(hhv == llv, 50.0, (hhv - close) / (hhv - llv) * 100.0)
    return wr_val


def tdx_cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """通达信风格 CCI 顺势指标。

    TDX 的 CCI:
    TYP = (HIGH + LOW + CLOSE) / 3
    CCI = (TYP - MA(TYP, N)) / (0.015 * AVEDEV(TYP, N))

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        CCI 序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)

    typ = (high + low + close) / 3.0
    ma_typ = _tdx_simple_ma(typ, period)

    md = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        md[i] = np.mean(np.abs(typ[i - period + 1:i + 1] - ma_typ[i]))

    cci_val = np.where(md == 0, 0.0, (typ - ma_typ) / (0.015 * md))
    return cci_val


TDX_INDICATOR_MAP: dict[str, callable] = {
    "MA": tdx_ma,
    "KDJ": tdx_kdj,
    "MACD": tdx_macd,
    "RSI": tdx_rsi,
    "BOLL": tdx_boll,
    "ATR": tdx_atr,
    "DMI": tdx_dmi,
    "OBV": tdx_obv,
    "WR": tdx_wr,
    "CCI": tdx_cci,
}


def get_tdx_indicator_names() -> list[str]:
    """获取所有 TDX 风格指标名称列表。

    Returns:
        TDX 指标名称列表
    """
    return sorted(list(TDX_INDICATOR_MAP.keys()))
