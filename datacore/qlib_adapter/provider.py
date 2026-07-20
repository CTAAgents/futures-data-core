"""DataCoreQLibProvider — Qlib 风格的 DataProvider 适配器。

提供与 Qlib DataProvider 接口一致的类，内部使用 AsyncDataProvider 获取数据，
将结果组织为 Qlib 期望的 MultiIndex DataFrame 格式 (instrument × datetime)。

支持的字段映射:
    $open / $high / $low / $close / $volume → OHLCV 字段
    $factor → 复权因子
    $vwap → 成交量加权平均价
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Union

import pandas as pd
import numpy as np

from ..api_async import AsyncDataProvider
from ..models.enums import DataType


# 字段名映射: qlib字段名 -> datacore字段名
_FIELD_MAP = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$vwap": "vwap",
    "$factor": "factor",
    "$turnover": "turnover",
}


def _qlib_field_to_datacore(field: str) -> str:
    """将 Qlib 风格的字段名转换为 Data-Core 内部字段名。"""
    return _FIELD_MAP.get(field, field.lstrip("$"))


def _normalize_freq(freq: str) -> str:
    """将 Qlib 风格的 freq 转换为 Data-Core 的 period 格式。"""
    freq_map = {
        "day": "daily",
        "1d": "daily",
        "daily": "daily",
        "week": "weekly",
        "1w": "weekly",
        "weekly": "weekly",
        "month": "monthly",
        "1m": "monthly",
        "monthly": "monthly",
        "1min": "1m",
        "5min": "5m",
        "5m": "5m",
        "15min": "15m",
        "15m": "15m",
        "30min": "30m",
        "30m": "30m",
        "60min": "60m",
        "60m": "60m",
        "1h": "60m",
    }
    return freq_map.get(freq.lower(), freq.lower())


class DataCoreQLibProvider:
    """Qlib 风格的 DataProvider，使用 Data-Core 作为数据源。

    接口与 Qlib 的 LocalProvider / DALProvider 保持一致，
    支持 features() 方法获取 MultiIndex DataFrame 格式的数据。

    Attributes:
        provider: 内部使用的 AsyncDataProvider 实例
    """

    def __init__(self, provider: Optional[AsyncDataProvider] = None):
        self._provider = provider or AsyncDataProvider()

    @property
    def provider(self) -> AsyncDataProvider:
        return self._provider

    def features(
        self,
        instruments: Union[str, list[str]],
        fields: list[str],
        start_time: Union[str, pd.Timestamp, None] = None,
        end_time: Union[str, pd.Timestamp, None] = None,
        freq: str = "day",
        disk_cache: int = 1,
    ) -> pd.DataFrame:
        """获取特征数据（同步接口）。

        Args:
            instruments: 合约代码或合约列表
            fields: 字段列表，如 ["$close", "$volume"]
            start_time: 开始时间
            end_time: 结束时间
            freq: 频率，如 "day", "1min", "5min"
            disk_cache: 磁盘缓存级别（兼容参数，实际未使用）

        Returns:
            MultiIndex DataFrame，索引为 (instrument, datetime)
        """
        return asyncio.run(
            self._features_async(instruments, fields, start_time, end_time, freq)
        )

    async def _features_async(
        self,
        instruments: Union[str, list[str]],
        fields: list[str],
        start_time: Union[str, pd.Timestamp, None],
        end_time: Union[str, pd.Timestamp, None],
        freq: str,
    ) -> pd.DataFrame:
        """异步获取特征数据。"""
        if isinstance(instruments, str):
            instruments = [instruments]

        period = _normalize_freq(freq)
        params: dict[str, Any] = {"period": period}

        if start_time is not None:
            params["start_date"] = pd.Timestamp(start_time).strftime("%Y-%m-%d")
        if end_time is not None:
            params["end_date"] = pd.Timestamp(end_time).strftime("%Y-%m-%d")

        # 估算 limit
        if start_time is not None and end_time is not None:
            days = (pd.Timestamp(end_time) - pd.Timestamp(start_time)).days
            params["limit"] = max(days + 10, 100)
        else:
            params["limit"] = 500

        # 批量获取数据
        results = await self._provider.get_batch(
            instruments, DataType.OHLCV, params=params
        )

        # 构建 MultiIndex DataFrame
        all_data = []
        for instrument in instruments:
            payload = results.get(instrument)
            if payload is None or not payload.available:
                continue

            df = _payload_to_dataframe(payload, fields)
            if df is not None and not df.empty:
                df["instrument"] = instrument
                all_data.append(df)

        if not all_data:
            return pd.DataFrame(
                columns=fields,
                index=pd.MultiIndex(
                    levels=[[], []],
                    codes=[[], []],
                    names=["instrument", "datetime"],
                ),
            )

        result = pd.concat(all_data, ignore_index=False)
        result = result.reset_index()
        result = result.set_index(["instrument", "datetime"])
        result = result.sort_index()

        return result[fields]

    def list_instruments(
        self,
        type: str = "all",
        market: str = "all",
    ) -> list[str]:
        """列出可用的合约（兼容接口）。

        Args:
            type: 合约类型（兼容参数）
            market: 市场（兼容参数）

        Returns:
            合约代码列表
        """
        from ..registry.symbol_registry import SymbolRegistry

        registry = SymbolRegistry()
        return [e.symbol for e in registry.list_all()]

    def __repr__(self) -> str:
        return f"<DataCoreQLibProvider provider={self._provider}>"


def _payload_to_dataframe(
    payload: Any,
    fields: list[str],
) -> Optional[pd.DataFrame]:
    """将 DataPayload 转换为 DataFrame。"""
    data = payload.data

    if data is None:
        return None

    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif hasattr(data, "to_dict"):
        df = pd.DataFrame(data.to_dict())
    elif isinstance(data, dict):
        df = pd.DataFrame(data)
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        return None

    if df.empty:
        return None

    # 处理日期列
    date_col = None
    for col in ["datetime", "date", "time", "timestamp"]:
        if col in df.columns:
            date_col = col
            break

    if date_col is not None:
        df["datetime"] = pd.to_datetime(df[date_col])
        df = df.set_index("datetime")
        if date_col != "datetime":
            df = df.drop(columns=[date_col])
    elif isinstance(df.index, pd.DatetimeIndex):
        df.index.name = "datetime"
    else:
        df.index.name = "datetime"

    # 列名映射
    col_map = {}
    for field in fields:
        dc_field = _qlib_field_to_datacore(field)
        if dc_field in df.columns:
            col_map[dc_field] = field
        elif dc_field.upper() in df.columns:
            col_map[dc_field.upper()] = field

    df = df.rename(columns=col_map)

    # 确保所有请求的字段都存在
    for field in fields:
        if field not in df.columns:
            df[field] = np.nan

    return df
