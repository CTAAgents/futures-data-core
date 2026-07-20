"""周期映射注册表 — 定义所有支持的周期及其粒度关系。

提供周期名称到 pandas 频率字符串的映射，以及粒度粗细比较功能。
"""

from __future__ import annotations



PERIOD_MAP: dict[str, str] = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "60min",
    "daily": "1D",
    "weekly": "1W-MON",
    "monthly": "1ME",
}


PERIOD_GRANULARITY: dict[str, int] = {
    "1m": 10,
    "5m": 20,
    "15m": 30,
    "30m": 40,
    "60m": 50,
    "daily": 60,
    "weekly": 70,
    "monthly": 80,
}


MINUTE_PERIODS = {"1m", "5m", "15m", "30m", "60m"}
DAILY_PERIODS = {"daily", "weekly", "monthly"}
ALL_PERIODS = set(PERIOD_MAP.keys())


def get_pandas_freq(period: str) -> str:
    """获取周期对应的 pandas 频率字符串。

    Args:
        period: 周期名称，如 "1m", "5m", "daily" 等

    Returns:
        pandas 频率字符串

    Raises:
        ValueError: 不支持的周期
    """
    if period not in PERIOD_MAP:
        raise ValueError(
            f"不支持的周期: {period}。支持的周期: {', '.join(sorted(PERIOD_MAP.keys()))}"
        )
    return PERIOD_MAP[period]


def is_finer(source: str, target: str) -> bool:
    """判断源周期是否比目标周期更细（可以重采样）。

    Args:
        source: 源周期
        target: 目标周期

    Returns:
        True 表示源周期更细，可以从重采样到目标周期

    Raises:
        ValueError: 不支持的周期
    """
    if source not in PERIOD_GRANULARITY:
        raise ValueError(f"不支持的源周期: {source}")
    if target not in PERIOD_GRANULARITY:
        raise ValueError(f"不支持的目标周期: {target}")
    return PERIOD_GRANULARITY[source] < PERIOD_GRANULARITY[target]


def is_same_category(period1: str, period2: str) -> bool:
    """判断两个周期是否属于同一大类（分钟线或日线）。

    Args:
        period1: 周期1
        period2: 周期2

    Returns:
        True 表示属于同一大类
    """
    p1_minute = period1 in MINUTE_PERIODS
    p2_minute = period2 in MINUTE_PERIODS
    return p1_minute == p2_minute


def validate_period(period: str) -> None:
    """验证周期是否合法。

    Args:
        period: 周期名称

    Raises:
        ValueError: 不支持的周期
    """
    if period not in PERIOD_MAP:
        raise ValueError(
            f"不支持的周期: {period}。支持的周期: {', '.join(sorted(PERIOD_MAP.keys()))}"
        )


def list_periods() -> list[str]:
    """列出所有支持的周期。

    Returns:
        周期名称列表
    """
    return sorted(PERIOD_MAP.keys(), key=lambda p: PERIOD_GRANULARITY[p])


__all__ = [
    "PERIOD_MAP",
    "PERIOD_GRANULARITY",
    "MINUTE_PERIODS",
    "DAILY_PERIODS",
    "ALL_PERIODS",
    "get_pandas_freq",
    "is_finer",
    "is_same_category",
    "validate_period",
    "list_periods",
]
