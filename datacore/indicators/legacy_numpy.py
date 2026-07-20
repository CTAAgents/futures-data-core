"""旧版兼容指标实现。

提供与早期版本 numpy 指标计算兼容的实现，
保持向后兼容性，旧代码可无缝迁移。

与 core.py 的主要区别:
- 保留旧版 API 接口和参数命名
- 保留旧版计算逻辑（可能与标准算法有差异）
- 作为 deprecated 接口，新代码应使用 core.py
"""

from __future__ import annotations

import numpy as np


def old_ma(values: np.ndarray, n: int) -> np.ndarray:
    """旧版简单移动平均。

    旧版实现，使用 Python 循环而不是向量化操作。
    保留用于向后兼容。

    Args:
        values: 输入序列
        n: 周期

    Returns:
        MA 序列
    """
    if n <= 0 or len(values) < n:
        return np.full(len(values), np.nan, dtype=float)

    result = np.zeros(len(values), dtype=float)
    for i in range(n - 1):
        result[i] = np.nan

    for i in range(n - 1, len(values)):
        result[i] = np.mean(values[i - n + 1:i + 1])

    return result


def old_ema(values: np.ndarray, n: int) -> np.ndarray:
    """旧版指数移动平均。

    旧版实现，使用简化的 EMA 算法。
    保留用于向后兼容。

    Args:
        values: 输入序列
        n: 周期

    Returns:
        EMA 序列
    """
    if n <= 0 or len(values) == 0:
        return np.full(len(values), np.nan, dtype=float)

    k = 2.0 / (n + 1)
    result = np.zeros(len(values), dtype=float)
    result[0] = values[0]

    for i in range(1, len(values)):
        result[i] = values[i] * k + result[i - 1] * (1 - k)

    result[:n - 1] = np.nan
    return result


def old_rsi(close: np.ndarray, n: int = 14) -> np.ndarray:
    """旧版 RSI 实现。

    旧版使用简单平均而不是 Wilder 平滑。
    保留用于向后兼容。

    Args:
        close: 收盘价序列
        n: 周期

    Returns:
        RSI 序列
    """
    if n <= 0 or len(close) < n + 1:
        return np.full(len(close), np.nan, dtype=float)

    delta = np.diff(close)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)

    avg_gains = np.zeros(len(close), dtype=float)
    avg_losses = np.zeros(len(close), dtype=float)

    avg_gains[n] = np.mean(gains[:n])
    avg_losses[n] = np.mean(losses[:n])

    for i in range(n + 1, len(close)):
        avg_gains[i] = (avg_gains[i - 1] * (n - 1) + gains[i - 1]) / n
        avg_losses[i] = (avg_losses[i - 1] * (n - 1) + losses[i - 1]) / n

    rs = np.where(avg_losses == 0, np.inf, avg_gains / avg_losses)
    rsi_val = 100.0 - 100.0 / (1.0 + rs)
    rsi_val[:n] = np.nan

    return rsi_val


def old_macd(close: np.ndarray, fast: int = 12, slow: int = 26,
             signal: int = 9) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """旧版 MACD 实现。

    旧版返回 tuple 而不是 dict。
    保留用于向后兼容。

    Args:
        close: 收盘价序列
        fast: 快线周期
        slow: 慢线周期
        signal: 信号线周期

    Returns:
        (dif, dea, macd_bar) 元组
    """
    ema_fast = old_ema(close, fast)
    ema_slow = old_ema(close, slow)

    dif = ema_fast - ema_slow
    dif_valid = np.where(np.isnan(dif), 0.0, dif)

    dea = old_ema(dif_valid, signal)
    dea = np.where(np.isnan(dif), np.nan, dea)

    macd_bar = 2 * (dif - dea)

    return dif, dea, macd_bar


def old_kdj(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            n: int = 9, m1: int = 3, m2: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """旧版 KDJ 实现。

    旧版返回 tuple 而不是 dict。
    保留用于向后兼容。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        n: RSV 周期
        m1: K 周期
        m2: D 周期

    Returns:
        (k, d, j) 元组
    """
    if n <= 0 or len(close) < n:
        k = np.full(len(close), np.nan, dtype=float)
        d = np.full(len(close), np.nan, dtype=float)
        j = np.full(len(close), np.nan, dtype=float)
        return k, d, j

    hhv = np.full(len(high), np.nan, dtype=float)
    llv = np.full(len(low), np.nan, dtype=float)

    for i in range(n - 1, len(close)):
        hhv[i] = np.max(high[i - n + 1:i + 1])
        llv[i] = np.min(low[i - n + 1:i + 1])

    rsv = np.where(hhv == llv, 50.0, (close - llv) / (hhv - llv) * 100.0)
    rsv[:n - 1] = np.nan

    k = np.full(len(close), np.nan, dtype=float)
    d = np.full(len(close), np.nan, dtype=float)

    k_val = 50.0
    d_val = 50.0
    for i in range(n - 1, len(close)):
        k_val = (rsv[i] + (m1 - 1) * k_val) / m1
        d_val = (k_val + (m2 - 1) * d_val) / m2
        k[i] = k_val
        d[i] = d_val

    j = 3 * k - 2 * d

    return k, d, j


def old_boll(close: np.ndarray, n: int = 20, k: float = 2.0
             ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """旧版布林带实现。

    旧版返回 tuple 而不是 dict。
    保留用于向后兼容。

    Args:
        close: 收盘价序列
        n: 周期
        k: 标准差倍数

    Returns:
        (upper, mid, lower) 元组
    """
    if n <= 0 or len(close) < n:
        upper = np.full(len(close), np.nan, dtype=float)
        mid = np.full(len(close), np.nan, dtype=float)
        lower = np.full(len(close), np.nan, dtype=float)
        return upper, mid, lower

    mid = old_ma(close, n)
    std = np.full(len(close), np.nan, dtype=float)

    for i in range(n - 1, len(close)):
        std[i] = np.std(close[i - n + 1:i + 1], ddof=0)

    upper = mid + k * std
    lower = mid - k * std

    return upper, mid, lower


def old_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            n: int = 14) -> np.ndarray:
    """旧版 ATR 实现。

    旧版使用简单平均而不是 Wilder 平滑。
    保留用于向后兼容。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        n: 周期

    Returns:
        ATR 序列
    """
    if n <= 0 or len(close) < n:
        return np.full(len(close), np.nan, dtype=float)

    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close))
    )

    return old_ma(tr, n)


LEGACY_FUNCTIONS: dict[str, callable] = {
    "old_ma": old_ma,
    "old_ema": old_ema,
    "old_rsi": old_rsi,
    "old_macd": old_macd,
    "old_kdj": old_kdj,
    "old_boll": old_boll,
    "old_atr": old_atr,
}


def get_legacy_function_names() -> list[str]:
    """获取所有旧版函数名称列表。

    Returns:
        旧版函数名称列表
    """
    return sorted(list(LEGACY_FUNCTIONS.keys()))
