"""FDT/FDC 兼容层 — 让原有 FDC 代码最小修改即可迁移到 Data-Core。

提供与 FDC 一致的函数签名，内部使用 AsyncDataProvider 和 indicators 模块实现。

使用方式:
    from datacore.fdc_compat import (
        get_kline, get_quote, batch_get_quotes,
        get_term_structure, get_spread, get_basis,
        get_warrant, get_fundamental, get_f10,
        get_position_ranking, compute_indicators,
        assess_trend_maturity,
    )

    kline = await get_kline("RB", period="daily", days=120)
    quote = await get_quote("RB")
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from .api_async import AsyncDataProvider
from .models.enums import DataType
from .indicators import compute_indicators as _compute_indicators
from .indicators import assess_trend_maturity as _assess_trend_maturity


_provider: Optional[AsyncDataProvider] = None


def _get_provider() -> AsyncDataProvider:
    global _provider
    if _provider is None:
        _provider = AsyncDataProvider()
    return _provider


def _kline_payload_to_list(payload: Any) -> list[dict]:
    data = payload.data
    if hasattr(data, "to_dict"):
        data = data.to_dict()
    elif hasattr(data, "tolist"):
        data = data.tolist()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "kline" in data:
            return data["kline"]
        keys = list(data.keys())
        if keys and isinstance(data[keys[0]], (list, np.ndarray)):
            result = []
            n = len(data[keys[0]])
            for i in range(n):
                row = {}
                for k in keys:
                    val = data[k]
                    if isinstance(val, np.ndarray):
                        row[k] = val[i].item()
                    else:
                        row[k] = val[i]
                result.append(row)
            return result
    return []


def _payload_to_data(payload: Any) -> Any:
    data = payload.data
    if hasattr(data, "to_dict"):
        data = data.to_dict()
    elif hasattr(data, "tolist"):
        data = data.tolist()
    return data


async def get_kline(
    symbol: str,
    period: str = "daily",
    days: int = 120,
    source: str = "auto",
) -> list[dict]:
    """兼容 FDC 的 get_kline 接口。

    Args:
        symbol: 品种代码，如 'RB'、'000001'
        period: K线周期，'1m'/'5m'/'15m'/'30m'/'60m'/'daily'/'weekly'/'monthly'
        days: 返回数据天数/条数
        source: 数据源（兼容参数，实际由 Data-Core 自动选择）

    Returns:
        K线数据列表，每个元素为包含 open/high/low/close/volume 等字段的字典
    """
    provider = _get_provider()
    params = {
        "period": period,
        "limit": days,
    }
    payload = await provider.get(symbol, DataType.OHLCV, params=params)
    return _kline_payload_to_list(payload)


async def get_quote(symbol: str) -> dict:
    """兼容 FDC 的 get_quote 接口。

    Args:
        symbol: 品种代码

    Returns:
        实时行情字典，包含最新价、涨跌额、涨跌幅等
    """
    provider = _get_provider()
    payload = await provider.get(symbol, DataType.QUOTE)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


async def batch_get_quotes(symbols: list[str]) -> dict[str, dict]:
    """批量获取行情。

    Args:
        symbols: 品种代码列表

    Returns:
        以品种代码为 key 的行情字典
    """
    provider = _get_provider()
    results = await provider.get_batch(symbols, DataType.QUOTE)
    output: dict[str, dict] = {}
    for sym, payload in results.items():
        data = _payload_to_data(payload)
        if isinstance(data, dict):
            output[sym] = data
        else:
            output[sym] = {"symbol": sym, "data": data}
    return output


async def get_term_structure(symbol: str) -> dict:
    """获取期限结构。

    Args:
        symbol: 品种代码

    Returns:
        期限结构数据字典
    """
    provider = _get_provider()
    payload = await provider.get(symbol, DataType.FUTURES_TERM_STRUCTURE)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


async def get_spread(symbol: str) -> dict:
    """获取跨期价差。

    Args:
        symbol: 品种代码

    Returns:
        跨期价差数据字典
    """
    provider = _get_provider()
    payload = await provider.get(symbol, DataType.FUTURES_SPREAD)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


async def get_basis(symbol: str) -> dict:
    """获取基差。

    Args:
        symbol: 品种代码

    Returns:
        基差数据字典
    """
    provider = _get_provider()
    payload = await provider.get(symbol, DataType.FUTURES_BASIS)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


async def get_warrant(symbol: str) -> dict:
    """获取仓单。

    Args:
        symbol: 品种代码

    Returns:
        仓单数据字典
    """
    provider = _get_provider()
    payload = await provider.get(symbol, DataType.FUTURES_WAREHOUSE_RECEIPT)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


async def get_fundamental(symbol: str) -> dict:
    """获取基本面。

    Args:
        symbol: 品种代码

    Returns:
        基本面数据字典
    """
    provider = _get_provider()
    payload = await provider.get(symbol, DataType.FUNDAMENTAL)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


async def get_f10(symbol: str) -> dict:
    """获取 F10 综合报告。

    Args:
        symbol: 品种代码

    Returns:
        F10 综合报告数据字典
    """
    provider = _get_provider()
    payload = await provider.get_f10(symbol)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


async def get_position_ranking(symbol: str) -> dict:
    """获取持仓排名。

    Args:
        symbol: 品种代码

    Returns:
        持仓排名数据字典
    """
    provider = _get_provider()
    payload = await provider.get(symbol, DataType.FUTURES_POSITION)
    data = _payload_to_data(payload)
    if isinstance(data, dict):
        return data
    return {"symbol": symbol, "data": data}


def compute_indicators(
    data: dict | list[dict] | Any,
    names: str | list[str] = "all",
    **params,
) -> dict:
    """兼容 FDC 的 compute_indicators。

    Args:
        data: 数据，可以是:
            - dict: 包含 close/high/low/open/volume 等 ndarray 的字典
            - list[dict]: K线数据列表（get_kline 的返回格式）
            - DataFrame: pandas DataFrame
        names: 指标名称或列表，"all" 表示计算所有
        **params: 额外参数

    Returns:
        指标结果字典
    """
    indicator_data = _normalize_indicator_data(data)
    return _compute_indicators(indicator_data, names=names, **params)


def _normalize_indicator_data(data: Any) -> dict:
    """将各种格式的输入数据转换为 compute_indicators 需要的 dict 格式。"""
    if isinstance(data, dict):
        if all(k in data for k in ("close",)):
            return data
        if "kline" in data:
            return _kline_list_to_arrays(data["kline"])
        return data

    if isinstance(data, list):
        return _kline_list_to_arrays(data)

    try:
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            result = {}
            for col in data.columns:
                col_lower = col.lower()
                if col_lower in ("open", "high", "low", "close", "volume"):
                    result[col_lower] = data[col].values
            return result
    except ImportError:
        pass

    raise TypeError(
        f"不支持的数据格式: {type(data)}。支持 dict、list[dict]、DataFrame"
    )


def _kline_list_to_arrays(kline_list: list[dict]) -> dict:
    """将 K线列表转换为 ndarray 字典。"""
    if not kline_list:
        return {"close": np.array([])}

    fields = ["open", "high", "low", "close", "volume"]
    result: dict[str, list] = {f: [] for f in fields}

    for item in kline_list:
        for f in fields:
            if f in item:
                result[f].append(item[f])
            elif f.upper() in item:
                result[f].append(item[f.upper()])

    return {k: np.array(v, dtype=float) for k, v in result.items() if v}


def assess_trend_maturity(
    close_prices: np.ndarray | list[float],
    high_prices: Optional[np.ndarray | list[float]] = None,
    low_prices: Optional[np.ndarray | list[float]] = None,
    volume: Optional[np.ndarray | list[float]] = None,
    **kwargs,
) -> Any:
    """兼容 FDC 的 assess_trend_maturity。

    Args:
        close_prices: 收盘价序列
        high_prices: 最高价序列（可选）
        low_prices: 最低价序列（可选）
        volume: 成交量序列（可选）
        **kwargs: 额外参数（lookback 等）

    Returns:
        TrendMaturityResult 评估结果
    """
    close = np.asarray(close_prices, dtype=float)
    high = np.asarray(high_prices, dtype=float) if high_prices is not None else None
    low = np.asarray(low_prices, dtype=float) if low_prices is not None else None
    vol = np.asarray(volume, dtype=float) if volume is not None else None

    return _assess_trend_maturity(close, high, low, vol, **kwargs)


__all__ = [
    "get_kline",
    "get_quote",
    "batch_get_quotes",
    "get_term_structure",
    "get_spread",
    "get_basis",
    "get_warrant",
    "get_fundamental",
    "get_f10",
    "get_position_ranking",
    "compute_indicators",
    "assess_trend_maturity",
]
