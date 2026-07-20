"""技术指标核心实现 — 纯 NumPy 版本。

提供 40+ 常用技术指标的 NumPy 实现，零外部依赖。
所有指标函数接受 np.ndarray 输入，返回 np.ndarray 或 dict。

指标分类:
- 移动平均线: MA, EMA, SMA, WMA, DMA
- 动量指标: RSI, MACD, MTM, ROC, BIAS, TRIX
- 震荡指标: KDJ, CCI, WR, PSY
- 波动率指标: BOLL, ATR, MASS
- 成交量指标: OBV, VR
- 趋势指标: DMI, BRAR, CR, Keltner, Chandelier
"""

from __future__ import annotations

import numpy as np


# ============================================================
#  工具函数
# ============================================================

def _shift(arr: np.ndarray, n: int, fill_value: float = np.nan) -> np.ndarray:
    """数组右移 n 位，前面填充 fill_value。

    Args:
        arr: 输入数组
        n: 移位位数（正数右移，负数左移）
        fill_value: 填充值

    Returns:
        移位后的数组，与输入等长
    """
    if n == 0:
        return arr.copy()
    result = np.full_like(arr, fill_value, dtype=float)
    if n > 0:
        result[n:] = arr[:-n]
    else:
        result[:n] = arr[-n:]
    return result


def _rolling_window(arr: np.ndarray, window: int) -> np.ndarray:
    """创建滚动窗口视图（高效实现）。

    Args:
        arr: 输入数组 (n,)
        window: 窗口大小

    Returns:
        形状为 (n - window + 1, window) 的数组
    """
    n = len(arr)
    if window <= 0 or window > n:
        return np.array([])
    shape = (n - window + 1, window)
    strides = (arr.strides[0], arr.strides[0])
    return np.lib.stride_tricks.as_strided(arr, shape=shape, strides=strides)


def _nan_to_num(x: np.ndarray, nan: float = 0.0) -> np.ndarray:
    """将 NaN 替换为指定值。"""
    return np.where(np.isnan(x), nan, x)


# ============================================================
#  移动平均线类
# ============================================================

def ma(close: np.ndarray, period: int = 5) -> np.ndarray:
    """简单移动平均线 (Simple Moving Average)。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        MA 序列，前 period-1 个为 NaN
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    result = np.full_like(close, np.nan, dtype=float)
    cumsum = np.cumsum(close, dtype=float)
    result[period - 1:] = (cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])) / period
    return result


def ema(close: np.ndarray, period: int = 12) -> np.ndarray:
    """指数移动平均线 (Exponential Moving Average)。

    使用平滑系数 alpha = 2 / (period + 1) 的标准 EMA 算法。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        EMA 序列
    """
    if period <= 0 or len(close) == 0:
        return np.full_like(close, np.nan, dtype=float)
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(close, dtype=float)
    result[0] = close[0]
    for i in range(1, len(close)):
        result[i] = alpha * close[i] + (1 - alpha) * result[i - 1]
    result[:period - 1] = np.nan
    return result


def sma(close: np.ndarray, period: int = 12, weight: int = 1) -> np.ndarray:
    """平滑移动平均线 (Smoothed Moving Average)。

    SMA = (SMA_prev * (period - weight) + close * weight) / period

    Args:
        close: 收盘价序列
        period: 周期
        weight: 权重

    Returns:
        SMA 序列
    """
    if period <= 0 or len(close) == 0:
        return np.full_like(close, np.nan, dtype=float)
    result = np.zeros_like(close, dtype=float)
    result[0] = close[0]
    for i in range(1, len(close)):
        result[i] = (result[i - 1] * (period - weight) + close[i] * weight) / period
    result[:period - 1] = np.nan
    return result


def wma(close: np.ndarray, period: int = 5) -> np.ndarray:
    """加权移动平均线 (Weighted Moving Average)。

    权重为 period, period-1, ..., 1，越近权重越大。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        WMA 序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    weights = np.arange(period, 0, -1, dtype=float)
    weights /= weights.sum()
    result = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        result[i] = np.sum(close[i - period + 1:i + 1] * weights)
    return result


def dma(close: np.ndarray, fast_period: int = 10, slow_period: int = 50) -> np.ndarray:
    """平均线差 (Different of Moving Average)。

    DMA = MA(fast) - MA(slow)

    Args:
        close: 收盘价序列
        fast_period: 快线周期
        slow_period: 慢线周期

    Returns:
        DMA 序列
    """
    fast_ma = ma(close, fast_period)
    slow_ma = ma(close, slow_period)
    return fast_ma - slow_ma


# ============================================================
#  动量指标类
# ============================================================

def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """相对强弱指标 (Relative Strength Index)。

    RSI = 100 - 100 / (1 + RS)
    RS = 平均涨幅 / 平均跌幅

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        RSI 序列，取值范围 [0, 100]
    """
    if period <= 0 or len(close) < period + 1:
        return np.full_like(close, np.nan, dtype=float)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.zeros_like(close, dtype=float)
    avg_loss = np.zeros_like(close, dtype=float)
    avg_gain[period] = np.mean(gain[1:period + 1])
    avg_loss[period] = np.mean(loss[1:period + 1])
    for i in range(period + 1, len(close)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i]) / period
    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    rsi_val = 100.0 - 100.0 / (1.0 + rs)
    rsi_val[:period] = np.nan
    return rsi_val


def macd(close: np.ndarray, fast_period: int = 12, slow_period: int = 26,
         signal_period: int = 9) -> dict[str, np.ndarray]:
    """MACD 指标 (Moving Average Convergence Divergence)。

    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal_period)
    Histogram = MACD - Signal

    Args:
        close: 收盘价序列
        fast_period: 快线周期
        slow_period: 慢线周期
        signal_period: 信号线周期

    Returns:
        包含 macd, signal, histogram 三个序列的字典
    """
    ema_fast = ema(close, fast_period)
    ema_slow = ema(close, slow_period)
    macd_line = ema_fast - ema_slow
    macd_valid = np.where(np.isnan(macd_line), 0.0, macd_line)
    signal_line = ema(macd_valid, signal_period)
    signal_line = np.where(np.isnan(macd_line), np.nan, signal_line)
    histogram = macd_line - signal_line
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def mtm(close: np.ndarray, period: int = 10) -> np.ndarray:
    """动量指标 (Momentum)。

    MTM = close - close[period 日前]

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        MTM 序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    result = close - _shift(close, period)
    return result


def roc(close: np.ndarray, period: int = 10) -> np.ndarray:
    """变动率指标 (Rate of Change)。

    ROC = (close - close[period日前]) / close[period日前] * 100

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        ROC 序列（百分比）
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    prev_close = _shift(close, period)
    result = np.where(prev_close == 0, np.nan, (close - prev_close) / prev_close * 100.0)
    return result


def bias(close: np.ndarray, period: int = 6) -> np.ndarray:
    """乖离率 (BIAS)。

    BIAS = (close - MA(period)) / MA(period) * 100

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        BIAS 序列（百分比）
    """
    ma_val = ma(close, period)
    return np.where(ma_val == 0, np.nan, (close - ma_val) / ma_val * 100.0)


def trix(close: np.ndarray, period: int = 12) -> np.ndarray:
    """三重指数平滑平均线 (TRIX)。

    TRIX = (EMA3 - EMA3_prev) / EMA3_prev * 100
    EMA3 = EMA(EMA(EMA(close, period), period), period)

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        TRIX 序列
    """
    ema1 = ema(close, period)
    ema1_valid = np.where(np.isnan(ema1), close, ema1)
    ema2 = ema(ema1_valid, period)
    ema2_valid = np.where(np.isnan(ema2), ema1_valid, ema2)
    ema3 = ema(ema2_valid, period)
    prev_ema3 = _shift(ema3, 1)
    trix_val = np.where(prev_ema3 == 0, np.nan, (ema3 - prev_ema3) / prev_ema3 * 100.0)
    trix_val[:period * 3 - 2] = np.nan
    return trix_val


# ============================================================
#  震荡指标类
# ============================================================

def kdj(high: np.ndarray, low: np.ndarray, close: np.ndarray,
        n: int = 9, m1: int = 3, m2: int = 3) -> dict[str, np.ndarray]:
    """KDJ 随机指标 (Stochastic Oscillator)。

    RSV = (close - LLV(low, n)) / (HHV(high, n) - LLV(low, n)) * 100
    K = SMA(RSV, m1)
    D = SMA(K, m2)
    J = 3 * K - 2 * D

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        n: RSV 周期
        m1: K 线平滑周期
        m2: D 线平滑周期

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
    rsv_valid = np.where(np.isnan(rsv), 50.0, rsv)
    k_line = sma(rsv_valid, m1, 1)
    k_line = np.where(np.isnan(rsv), np.nan, k_line)
    k_valid = np.where(np.isnan(k_line), 50.0, k_line)
    d_line = sma(k_valid, m2, 1)
    d_line = np.where(np.isnan(k_line), np.nan, d_line)
    j_line = 3 * k_line - 2 * d_line
    return {
        "k": k_line,
        "d": d_line,
        "j": j_line,
    }


def cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """顺势指标 (Commodity Channel Index)。

    TP = (high + low + close) / 3
    MA_TP = MA(TP, period)
    MD = 平均绝对偏差
    CCI = (TP - MA_TP) / (0.015 * MD)

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
    tp = (high + low + close) / 3.0
    ma_tp = ma(tp, period)
    md = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        md[i] = np.mean(np.abs(tp[i - period + 1:i + 1] - ma_tp[i]))
    cci_val = np.where(md == 0, 0.0, (tp - ma_tp) / (0.015 * md))
    return cci_val


def wr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """威廉指标 (Williams %R)。

    WR = (HHV(high, period) - close) / (HHV(high, period) - LLV(low, period)) * -100

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        WR 序列，取值范围 [-100, 0]
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    hhv = np.full_like(high, np.nan, dtype=float)
    llv = np.full_like(low, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        hhv[i] = np.max(high[i - period + 1:i + 1])
        llv[i] = np.min(low[i - period + 1:i + 1])
    wr_val = np.where(hhv == llv, -50.0, (hhv - close) / (hhv - llv) * -100.0)
    return wr_val


def psy(close: np.ndarray, period: int = 12) -> np.ndarray:
    """心理线 (Psychological Line)。

    PSY = 周期内上涨天数 / 周期 * 100

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        PSY 序列（百分比）
    """
    if period <= 0 or len(close) < period + 1:
        return np.full_like(close, np.nan, dtype=float)
    delta = np.diff(close, prepend=close[0])
    up_days = np.where(delta > 0, 1.0, 0.0)
    result = np.full_like(close, np.nan, dtype=float)
    cumsum = np.cumsum(up_days)
    result[period:] = (cumsum[period:] - cumsum[:-period]) / period * 100.0
    return result


# ============================================================
#  波动率指标类
# ============================================================

def boll(close: np.ndarray, period: int = 20, nbdev: float = 2.0) -> dict[str, np.ndarray]:
    """布林带 (Bollinger Bands)。

    MID = MA(close, period)
    STD = 标准差(close, period)
    UPPER = MID + nbdev * STD
    LOWER = MID - nbdev * STD

    Args:
        close: 收盘价序列
        period: 周期
        nbdev: 标准差倍数

    Returns:
        包含 upper, middle, lower 三个序列的字典
    """
    if period <= 0 or len(close) < period:
        return {
            "upper": np.full_like(close, np.nan, dtype=float),
            "middle": np.full_like(close, np.nan, dtype=float),
            "lower": np.full_like(close, np.nan, dtype=float),
        }
    mid = ma(close, period)
    std = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1:i + 1], ddof=0)
    upper = mid + nbdev * std
    lower = mid - nbdev * std
    return {
        "upper": upper,
        "middle": mid,
        "lower": lower,
    }


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """平均真实波幅 (Average True Range)。

    TR = max(high - low, |high - close_prev|, |low - close_prev|)
    ATR = EMA(TR, period) （Wilder 平滑）

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
    atr_val = np.zeros_like(close, dtype=float)
    atr_val[period - 1] = np.mean(tr[:period])
    for i in range(period, len(close)):
        atr_val[i] = (atr_val[i - 1] * (period - 1) + tr[i]) / period
    atr_val[:period - 1] = np.nan
    return atr_val


def mass(high: np.ndarray, low: np.ndarray, fast_period: int = 9,
         slow_period: int = 25) -> np.ndarray:
    """梅斯线 (Mass Index)。

    EMA_HL = EMA(high - low, fast_period)
    EMA_EMA = EMA(EMA_HL, fast_period)
    Ratio = EMA_HL / EMA_EMA
    MASS = SUM(Ratio, slow_period)

    Args:
        high: 最高价序列
        low: 最低价序列
        fast_period: 快线周期
        slow_period: 慢线周期

    Returns:
        MASS 序列
    """
    hl = high - low
    ema_hl = ema(hl, fast_period)
    ema_hl_valid = np.where(np.isnan(ema_hl), hl, ema_hl)
    ema_ema = ema(ema_hl_valid, fast_period)
    ratio = np.where(ema_ema == 0, np.nan, ema_hl / ema_ema)
    ratio_valid = np.where(np.isnan(ratio), 1.0, ratio)
    mass_val = np.full_like(high, np.nan, dtype=float)
    if len(high) >= slow_period:
        cumsum = np.cumsum(ratio_valid)
        mass_val[slow_period - 1:] = (
            cumsum[slow_period - 1:] - np.concatenate([[0], cumsum[:-slow_period]])
        )
    return mass_val


# ============================================================
#  成交量指标类
# ============================================================

def obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """能量潮 (On Balance Volume)。

    OBV = OBV_prev + (close > close_prev ? volume : -volume)

    Args:
        close: 收盘价序列
        volume: 成交量序列

    Returns:
        OBV 序列
    """
    if len(close) == 0:
        return np.array([], dtype=float)
    delta = np.diff(close, prepend=close[0])
    sign = np.sign(delta)
    sign[0] = 0
    obv_val = np.cumsum(sign * volume)
    obv_val[0] = volume[0]
    return obv_val


def vr(close: np.ndarray, volume: np.ndarray, period: int = 26) -> np.ndarray:
    """成交量变异率 (Volume Ratio)。

    VR = (上涨日成交量 + 1/2 平盘日成交量) / (下跌日成交量 + 1/2 平盘日成交量) * 100

    Args:
        close: 收盘价序列
        volume: 成交量序列
        period: 周期

    Returns:
        VR 序列
    """
    if period <= 0 or len(close) < period + 1:
        return np.full_like(close, np.nan, dtype=float)
    delta = np.diff(close, prepend=close[0])
    up_vol = np.where(delta > 0, volume, 0.0)
    down_vol = np.where(delta < 0, volume, 0.0)
    flat_vol = np.where(delta == 0, volume, 0.0)
    result = np.full_like(close, np.nan, dtype=float)
    up_cumsum = np.cumsum(up_vol)
    down_cumsum = np.cumsum(down_vol)
    flat_cumsum = np.cumsum(flat_vol)
    for i in range(period, len(close)):
        up_sum = up_cumsum[i] - up_cumsum[i - period]
        down_sum = down_cumsum[i] - down_cumsum[i - period]
        flat_sum = flat_cumsum[i] - flat_cumsum[i - period]
        denom = down_sum + 0.5 * flat_sum
        result[i] = (up_sum + 0.5 * flat_sum) / denom * 100.0 if denom > 0 else np.nan
    return result


# ============================================================
#  趋势指标类
# ============================================================

def dmi(high: np.ndarray, low: np.ndarray, close: np.ndarray,
        period: int = 14) -> dict[str, np.ndarray]:
    """趋向指标 (Directional Movement Index)。

    +DM = 上涨动向（high - high_prev > low_prev - low 且 > 0 时取差值，否则 0）
    -DM = 下跌动向（low_prev - low > high - high_prev 且 > 0 时取差值，否则 0）
    +DI = 100 * EMA(+DM, period) / ATR
    -DI = 100 * EMA(-DM, period) / ATR
    DX = 100 * |+DI - -DI| / (+DI + -DI)
    ADX = EMA(DX, period)

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        包含 plus_di, minus_di, adx, dx 四个序列的字典
    """
    if period <= 0 or len(close) < period + 1:
        return {
            "plus_di": np.full_like(close, np.nan, dtype=float),
            "minus_di": np.full_like(close, np.nan, dtype=float),
            "adx": np.full_like(close, np.nan, dtype=float),
            "dx": np.full_like(close, np.nan, dtype=float),
        }
    prev_high = _shift(high, 1)
    prev_low = _shift(low, 1)
    prev_high[0] = high[0]
    prev_low[0] = low[0]
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr_val = atr(high, low, close, period)
    plus_dm_smooth = np.zeros_like(close, dtype=float)
    minus_dm_smooth = np.zeros_like(close, dtype=float)
    plus_dm_smooth[period - 1] = np.sum(plus_dm[1:period])
    minus_dm_smooth[period - 1] = np.sum(minus_dm[1:period])
    for i in range(period, len(close)):
        plus_dm_smooth[i] = (plus_dm_smooth[i - 1] * (period - 1) + plus_dm[i]) / period
        minus_dm_smooth[i] = (minus_dm_smooth[i - 1] * (period - 1) + minus_dm[i]) / period
    plus_di = np.where(atr_val == 0, 0.0, plus_dm_smooth / atr_val * 100.0)
    minus_di = np.where(atr_val == 0, 0.0, minus_dm_smooth / atr_val * 100.0)
    di_sum = plus_di + minus_di
    dx = np.where(di_sum == 0, 0.0, np.abs(plus_di - minus_di) / di_sum * 100.0)
    dx[:period - 1] = np.nan
    dx_valid = np.where(np.isnan(dx), 0.0, dx)
    adx_val = np.zeros_like(close, dtype=float)
    adx_val[2 * period - 2] = np.mean(dx_valid[period - 1:2 * period - 1])
    for i in range(2 * period - 1, len(close)):
        adx_val[i] = (adx_val[i - 1] * (period - 1) + dx_valid[i]) / period
    adx_val[:2 * period - 2] = np.nan
    plus_di[:period - 1] = np.nan
    minus_di[:period - 1] = np.nan
    return {
        "plus_di": plus_di,
        "minus_di": minus_di,
        "adx": adx_val,
        "dx": dx,
    }


def brar(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         open_: np.ndarray, period: int = 26) -> dict[str, np.ndarray]:
    """BRAR 情绪指标。

    AR（人气指标）= (HH - OL) / (LC - LL) * 100
    BR（意愿指标）= (HC - PC) / (PC - LC) * 100
    HH = N 日内（最高价 - 开盘价）之和
    OL = N 日内（开盘价 - 最低价）之和
    HC = N 日内（最高价 - 昨收）之和
    PC = N 日内（昨收 - 最低价）之和

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        open_: 开盘价序列
        period: 周期

    Returns:
        包含 br, ar 两个序列的字典
    """
    if period <= 0 or len(close) < period + 1:
        return {
            "br": np.full_like(close, np.nan, dtype=float),
            "ar": np.full_like(close, np.nan, dtype=float),
        }
    prev_close = _shift(close, 1)
    prev_close[0] = close[0]
    ho = high - open_
    ol = open_ - low
    hc = np.maximum(high - prev_close, 0.0)
    cl = np.maximum(prev_close - low, 0.0)
    ar = np.full_like(close, np.nan, dtype=float)
    br = np.full_like(close, np.nan, dtype=float)
    ho_cumsum = np.cumsum(ho)
    ol_cumsum = np.cumsum(ol)
    hc_cumsum = np.cumsum(hc)
    cl_cumsum = np.cumsum(cl)
    for i in range(period - 1, len(close)):
        if i >= period:
            ho_sum = ho_cumsum[i] - ho_cumsum[i - period]
            ol_sum = ol_cumsum[i] - ol_cumsum[i - period]
            hc_sum = hc_cumsum[i] - hc_cumsum[i - period]
            cl_sum = cl_cumsum[i] - cl_cumsum[i - period]
        else:
            ho_sum = ho_cumsum[i]
            ol_sum = ol_cumsum[i]
            hc_sum = hc_cumsum[i]
            cl_sum = cl_cumsum[i]
        ar[i] = ho_sum / ol_sum * 100.0 if ol_sum > 0 else np.nan
        br[i] = hc_sum / cl_sum * 100.0 if cl_sum > 0 else np.nan
    return {
        "br": br,
        "ar": ar,
    }


def cr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
       period: int = 26) -> np.ndarray:
    """能量指标 (Commodity Research)。

    MID = (high + low + close) / 3
    CR = (上涨强度之和) / (下跌强度之和) * 100
    上涨强度 = max(0, high - MID_prev)
    下跌强度 = max(0, MID_prev - low)

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        CR 序列
    """
    if period <= 0 or len(close) < period + 1:
        return np.full_like(close, np.nan, dtype=float)
    mid = (high + low + close) / 3.0
    prev_mid = _shift(mid, 1)
    prev_mid[0] = mid[0]
    up_strength = np.maximum(high - prev_mid, 0.0)
    down_strength = np.maximum(prev_mid - low, 0.0)
    result = np.full_like(close, np.nan, dtype=float)
    up_cumsum = np.cumsum(up_strength)
    down_cumsum = np.cumsum(down_strength)
    for i in range(period - 1, len(close)):
        if i >= period:
            up_sum = up_cumsum[i] - up_cumsum[i - period]
            down_sum = down_cumsum[i] - down_cumsum[i - period]
        else:
            up_sum = up_cumsum[i]
            down_sum = down_cumsum[i]
        result[i] = up_sum / down_sum * 100.0 if down_sum > 0 else np.nan
    return result


def keltner(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            period: int = 20, atr_period: int = 10,
            mult: float = 2.0) -> dict[str, np.ndarray]:
    """肯特纳通道 (Keltner Channels)。

    MID = EMA(close, period)
    UPPER = MID + mult * ATR
    LOWER = MID - mult * ATR

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 中轨 EMA 周期
        atr_period: ATR 周期
        mult: ATR 倍数

    Returns:
        包含 upper, middle, lower 三个序列的字典
    """
    mid = ema(close, period)
    atr_val = atr(high, low, close, atr_period)
    upper = mid + mult * atr_val
    lower = mid - mult * atr_val
    return {
        "upper": upper,
        "middle": mid,
        "lower": lower,
    }


def chandelier(high: np.ndarray, low: np.ndarray, close: np.ndarray,
               period: int = 22, mult: float = 3.0) -> dict[str, np.ndarray]:
    """吊灯止损 (Chandelier Exit)。

    ATR_val = ATR(period)
    Long Exit = HHV(high, period) - mult * ATR_val
    Short Exit = LLV(low, period) + mult * ATR_val

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期
        mult: ATR 倍数

    Returns:
        包含 long_exit, short_exit 两个序列的字典
    """
    if period <= 0 or len(close) < period:
        return {
            "long_exit": np.full_like(close, np.nan, dtype=float),
            "short_exit": np.full_like(close, np.nan, dtype=float),
        }
    atr_val = atr(high, low, close, period)
    hhv_high = np.full_like(high, np.nan, dtype=float)
    llv_low = np.full_like(low, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        hhv_high[i] = np.max(high[i - period + 1:i + 1])
        llv_low[i] = np.min(low[i - period + 1:i + 1])
    long_exit = hhv_high - mult * atr_val
    short_exit = llv_low + mult * atr_val
    return {
        "long_exit": long_exit,
        "short_exit": short_exit,
    }


# ============================================================
#  其他补充指标
# ============================================================

def median_price(high: np.ndarray, low: np.ndarray) -> np.ndarray:
    """中位价 (Median Price)。

    Median Price = (high + low) / 2

    Args:
        high: 最高价序列
        low: 最低价序列

    Returns:
        中位价序列
    """
    return (high + low) / 2.0


def typical_price(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """典型价格 (Typical Price)。

    Typical Price = (high + low + close) / 3

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列

    Returns:
        典型价格序列
    """
    return (high + low + close) / 3.0


def weighted_close(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """加权收盘价 (Weighted Close)。

    Weighted Close = (high + low + 2 * close) / 4

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列

    Returns:
        加权收盘价序列
    """
    return (high + low + 2 * close) / 4.0


def avg_price(open_: np.ndarray, high: np.ndarray,
              low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """平均价 (Average Price)。

    Average Price = (open + high + low + close) / 4

    Args:
        open_: 开盘价序列
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列

    Returns:
        平均价序列
    """
    return (open_ + high + low + close) / 4.0


def trange(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """真实波幅 (True Range)。

    TR = max(high - low, |high - close_prev|, |low - close_prev|)

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列

    Returns:
        TR 序列
    """
    prev_close = _shift(close, 1)
    prev_close[0] = close[0]
    return np.maximum(
        high - low,
        np.maximum(
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ),
    )


def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """平均趋向指数 (Average Directional Index)。

    这是 dmi() 的便捷函数，只返回 ADX 序列。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期

    Returns:
        ADX 序列
    """
    return dmi(high, low, close, period)["adx"]


def stddev(close: np.ndarray, period: int = 20) -> np.ndarray:
    """标准差 (Standard Deviation)。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        标准差序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    result = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        result[i] = np.std(close[i - period + 1:i + 1], ddof=0)
    return result


def variance(close: np.ndarray, period: int = 20) -> np.ndarray:
    """方差 (Variance)。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        方差序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    result = np.full_like(close, np.nan, dtype=float)
    for i in range(period - 1, len(close)):
        result[i] = np.var(close[i - period + 1:i + 1], ddof=0)
    return result


def linear_regression(close: np.ndarray, period: int = 14) -> np.ndarray:
    """线性回归 (Linear Regression)。

    使用最小二乘法拟合周期内收盘价的线性回归线，返回当前点的回归值。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        线性回归值序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    result = np.full_like(close, np.nan, dtype=float)
    x = np.arange(period, dtype=float)
    x_mean = np.mean(x)
    ssxx = np.sum((x - x_mean) ** 2)
    for i in range(period - 1, len(close)):
        y = close[i - period + 1:i + 1]
        y_mean = np.mean(y)
        ssxy = np.sum((x - x_mean) * (y - y_mean))
        slope = ssxy / ssxx if ssxx != 0 else 0.0
        intercept = y_mean - slope * x_mean
        result[i] = intercept + slope * (period - 1)
    return result


def linear_reg_slope(close: np.ndarray, period: int = 14) -> np.ndarray:
    """线性回归斜率 (Linear Regression Slope)。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        斜率序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    result = np.full_like(close, np.nan, dtype=float)
    x = np.arange(period, dtype=float)
    x_mean = np.mean(x)
    ssxx = np.sum((x - x_mean) ** 2)
    for i in range(period - 1, len(close)):
        y = close[i - period + 1:i + 1]
        y_mean = np.mean(y)
        ssxy = np.sum((x - x_mean) * (y - y_mean))
        result[i] = ssxy / ssxx if ssxx != 0 else 0.0
    return result


def tsf(close: np.ndarray, period: int = 14) -> np.ndarray:
    """时间序列预测 (Time Series Forecast)。

    等价于 linear_regression 的下一个周期预测值。

    Args:
        close: 收盘价序列
        period: 周期

    Returns:
        TSF 序列
    """
    if period <= 0 or len(close) < period:
        return np.full_like(close, np.nan, dtype=float)
    result = np.full_like(close, np.nan, dtype=float)
    x = np.arange(period, dtype=float)
    x_mean = np.mean(x)
    ssxx = np.sum((x - x_mean) ** 2)
    for i in range(period - 1, len(close)):
        y = close[i - period + 1:i + 1]
        y_mean = np.mean(y)
        ssxy = np.sum((x - x_mean) * (y - y_mean))
        slope = ssxy / ssxx if ssxx != 0 else 0.0
        intercept = y_mean - slope * x_mean
        result[i] = intercept + slope * period
    return result


def ultimate_osc(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 period1: int = 7, period2: int = 14, period3: int = 28) -> np.ndarray:
    """终极震荡指标 (Ultimate Oscillator)。

    BP = close - min(low, prev_close)
    TR = max(high, prev_close) - min(low, prev_close)
    AVG1 = SUM(BP, period1) / SUM(TR, period1)
    AVG2 = SUM(BP, period2) / SUM(TR, period2)
    AVG3 = SUM(BP, period3) / SUM(TR, period3)
    UO = 100 * (4 * AVG1 + 2 * AVG2 + AVG3) / 7

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period1: 第一周期
        period2: 第二周期
        period3: 第三周期

    Returns:
        UO 序列
    """
    if period3 <= 0 or len(close) < period3 + 1:
        return np.full_like(close, np.nan, dtype=float)
    prev_close = _shift(close, 1)
    prev_close[0] = close[0]
    bp = close - np.minimum(low, prev_close)
    tr = np.maximum(high, prev_close) - np.minimum(low, prev_close)
    bp_cumsum = np.cumsum(bp)
    tr_cumsum = np.cumsum(tr)
    def _avg(p):
        avg = np.full_like(close, np.nan, dtype=float)
        for i in range(p - 1, len(close)):
            bp_sum = bp_cumsum[i] - (bp_cumsum[i - p] if i >= p else 0)
            tr_sum = tr_cumsum[i] - (tr_cumsum[i - p] if i >= p else 0)
            avg[i] = bp_sum / tr_sum if tr_sum > 0 else 0.0
        return avg
    avg1 = _avg(period1)
    avg2 = _avg(period2)
    avg3 = _avg(period3)
    uo = 100.0 * (4 * avg1 + 2 * avg2 + avg3) / 7.0
    uo[:period3 - 1] = np.nan
    return uo


def williams_r(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """威廉指标别名，同 wr()。"""
    return wr(high, low, close, period)


def momentum(close: np.ndarray, period: int = 10) -> np.ndarray:
    """动量指标别名，同 mtm()。"""
    return mtm(close, period)


def rate_of_change(close: np.ndarray, period: int = 10) -> np.ndarray:
    """变动率别名，同 roc()。"""
    return roc(close, period)


def bbands(close: np.ndarray, period: int = 20, nbdev: float = 2.0) -> dict[str, np.ndarray]:
    """布林带别名，同 boll()。"""
    return boll(close, period, nbdev)


def stoch(high: np.ndarray, low: np.ndarray, close: np.ndarray,
          fastk_period: int = 5, slowk_period: int = 3,
          slowd_period: int = 3) -> dict[str, np.ndarray]:
    """随机指标别名（TA-Lib 风格），同 kdj()。"""
    result = kdj(high, low, close, fastk_period, slowk_period, slowd_period)
    return {
        "slowk": result["k"],
        "slowd": result["d"],
    }


# ============================================================
#  指标注册
# ============================================================

INDICATOR_MAP: dict[str, callable] = {
    "MA": ma,
    "EMA": ema,
    "SMA": sma,
    "WMA": wma,
    "DMA": dma,
    "RSI": rsi,
    "MACD": macd,
    "MTM": mtm,
    "ROC": roc,
    "BIAS": bias,
    "TRIX": trix,
    "KDJ": kdj,
    "CCI": cci,
    "WR": wr,
    "PSY": psy,
    "BOLL": boll,
    "ATR": atr,
    "MASS": mass,
    "OBV": obv,
    "VR": vr,
    "DMI": dmi,
    "BRAR": brar,
    "CR": cr,
    "KELTNER": keltner,
    "CHANDELIER": chandelier,
    "MEDIAN_PRICE": median_price,
    "TYPICAL_PRICE": typical_price,
    "WEIGHTED_CLOSE": weighted_close,
    "AVG_PRICE": avg_price,
    "TRANGE": trange,
    "ADX": adx,
    "STDDEV": stddev,
    "VARIANCE": variance,
    "LINEARREG": linear_regression,
    "LINEARREG_SLOPE": linear_reg_slope,
    "TSF": tsf,
    "ULTOSC": ultimate_osc,
}


def get_indicator_names() -> list[str]:
    """获取所有支持的指标名称列表。

    Returns:
        指标名称列表（大写）
    """
    return sorted(list(INDICATOR_MAP.keys()))
