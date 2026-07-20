"""Qlib 适配器测试。

覆盖:
- DataCoreQLibProvider
- DataCoreCalendarProvider
- DataCoreInstrumentProvider
- 字段映射和频率转换
- MultiIndex DataFrame 格式验证
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import pytest

from datacore.qlib_adapter import (
    DataCoreQLibProvider,
    DataCoreCalendarProvider,
    DataCoreInstrumentProvider,
)
from datacore.qlib_adapter.provider import (
    _qlib_field_to_datacore,
    _normalize_freq,
    _payload_to_dataframe,
)


# ============================================================
#  DataCoreCalendarProvider 测试
# ============================================================

class TestDataCoreCalendarProvider:

    def test_init_default(self):
        cal = DataCoreCalendarProvider()
        assert isinstance(cal, DataCoreCalendarProvider)
        assert cal.holidays == set()
        assert "Mon" in cal.weekmask

    def test_init_with_holidays(self):
        holidays = {"2024-01-01", "2024-01-02"}
        cal = DataCoreCalendarProvider(holidays=holidays)
        assert len(cal.holidays) == 2

    def test_calendar_basic(self):
        cal = DataCoreCalendarProvider()
        result = cal.calendar(
            start_time="2024-01-01",
            end_time="2024-01-10",
            freq="day",
        )
        assert isinstance(result, pd.DatetimeIndex)
        assert len(result) > 0
        assert result[0] >= pd.Timestamp("2024-01-01")
        assert result[-1] <= pd.Timestamp("2024-01-10")

    def test_calendar_weekdays_only(self):
        cal = DataCoreCalendarProvider()
        result = cal.calendar(
            start_time="2024-01-01",
            end_time="2024-01-07",
            freq="day",
        )
        for d in result:
            assert d.weekday() < 5

    def test_calendar_with_holidays(self):
        holidays = {pd.Timestamp("2024-01-02")}
        cal = DataCoreCalendarProvider(holidays=holidays)
        result = cal.calendar(
            start_time="2024-01-01",
            end_time="2024-01-05",
            freq="day",
        )
        assert pd.Timestamp("2024-01-02") not in result

    def test_is_trading_day_weekday(self):
        cal = DataCoreCalendarProvider()
        assert cal.is_trading_day("2024-01-02") is True

    def test_is_trading_day_weekend(self):
        cal = DataCoreCalendarProvider()
        assert cal.is_trading_day("2024-01-06") is False

    def test_is_trading_day_holiday(self):
        holidays = {pd.Timestamp("2024-01-02")}
        cal = DataCoreCalendarProvider(holidays=holidays)
        assert cal.is_trading_day("2024-01-02") is False

    def test_add_trading_days_forward(self):
        cal = DataCoreCalendarProvider()
        result = cal.add_trading_days("2024-01-02", 3)
        assert isinstance(result, pd.Timestamp)
        assert result > pd.Timestamp("2024-01-02")

    def test_add_trading_days_backward(self):
        cal = DataCoreCalendarProvider()
        result = cal.add_trading_days("2024-01-05", -2)
        assert isinstance(result, pd.Timestamp)
        assert result < pd.Timestamp("2024-01-05")

    def test_calendar_empty_range(self):
        cal = DataCoreCalendarProvider()
        result = cal.calendar(
            start_time="2024-01-10",
            end_time="2024-01-01",
            freq="day",
        )
        assert len(result) == 0

    def test_calendar_minute_freq(self):
        cal = DataCoreCalendarProvider()
        result = cal.calendar(
            start_time="2024-01-02 09:00:00",
            end_time="2024-01-02 10:00:00",
            freq="5min",
        )
        assert isinstance(result, pd.DatetimeIndex)
        assert len(result) > 0

    def test_repr(self):
        cal = DataCoreCalendarProvider()
        r = repr(cal)
        assert "DataCoreCalendarProvider" in r


# ============================================================
#  DataCoreInstrumentProvider 测试
# ============================================================

class TestDataCoreInstrumentProvider:

    def test_init_default(self):
        ip = DataCoreInstrumentProvider()
        assert isinstance(ip, DataCoreInstrumentProvider)

    def test_instruments_all(self):
        ip = DataCoreInstrumentProvider()
        result = ip.instruments(market="all")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_instruments_futures(self):
        ip = DataCoreInstrumentProvider()
        result = ip.instruments(market="futures")
        assert isinstance(result, dict)
        assert len(result) > 0
        for v in result.values():
            assert v["market"] == "futures"

    def test_list_instruments(self):
        ip = DataCoreInstrumentProvider()
        result = ip.list_instruments(market="futures")
        assert isinstance(result, list)
        assert len(result) > 0
        assert "RB" in result

    def test_get_instrument_exists(self):
        ip = DataCoreInstrumentProvider()
        result = ip.get_instrument("RB")
        assert result is not None
        assert result["symbol"] == "RB"
        assert result["name"] == "螺纹钢"

    def test_get_instrument_not_exists(self):
        ip = DataCoreInstrumentProvider()
        result = ip.get_instrument("NOTEXIST")
        assert result is None

    def test_is_instrument_true(self):
        ip = DataCoreInstrumentProvider()
        assert ip.is_instrument("RB") is True

    def test_is_instrument_false(self):
        ip = DataCoreInstrumentProvider()
        assert ip.is_instrument("NOTEXIST") is False

    def test_add_instrument(self):
        ip = DataCoreInstrumentProvider()
        ip.add_instrument("TEST", "测试品种", "futures", "测试板块")
        assert ip.is_instrument("TEST")
        info = ip.get_instrument("TEST")
        assert info["name"] == "测试品种"
        assert info["sector"] == "测试板块"

    def test_repr(self):
        ip = DataCoreInstrumentProvider()
        r = repr(ip)
        assert "DataCoreInstrumentProvider" in r


# ============================================================
#  工具函数测试
# ============================================================

class TestProviderUtils:

    def test_qlib_field_to_datacore_close(self):
        assert _qlib_field_to_datacore("$close") == "close"

    def test_qlib_field_to_datacore_volume(self):
        assert _qlib_field_to_datacore("$volume") == "volume"

    def test_qlib_field_to_datacore_open(self):
        assert _qlib_field_to_datacore("$open") == "open"

    def test_qlib_field_to_datacore_high(self):
        assert _qlib_field_to_datacore("$high") == "high"

    def test_qlib_field_to_datacore_low(self):
        assert _qlib_field_to_datacore("$low") == "low"

    def test_normalize_freq_day(self):
        assert _normalize_freq("day") == "daily"

    def test_normalize_freq_daily(self):
        assert _normalize_freq("daily") == "daily"

    def test_normalize_freq_1min(self):
        assert _normalize_freq("1min") == "1m"

    def test_normalize_freq_5min(self):
        assert _normalize_freq("5min") == "5m"

    def test_normalize_freq_1h(self):
        assert _normalize_freq("1h") == "60m"

    def test_normalize_freq_week(self):
        assert _normalize_freq("week") == "weekly"


# ============================================================
#  DataCoreQLibProvider 测试（Mock 方式）
# ============================================================

class TestDataCoreQLibProvider:

    def test_init_default(self):
        provider = DataCoreQLibProvider()
        assert isinstance(provider, DataCoreQLibProvider)

    def test_init_with_provider(self):
        from datacore.api_async import AsyncDataProvider
        adp = AsyncDataProvider()
        provider = DataCoreQLibProvider(adp)
        assert provider.provider is adp

    def test_list_instruments(self):
        provider = DataCoreQLibProvider()
        result = provider.list_instruments()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_repr(self):
        provider = DataCoreQLibProvider()
        r = repr(provider)
        assert "DataCoreQLibProvider" in r

    def test_payload_to_dataframe_with_dict(self):
        class MockPayload:
            def __init__(self):
                self.data = {
                    "datetime": ["2024-01-01", "2024-01-02"],
                    "close": [100.0, 101.0],
                    "volume": [1000, 2000],
                }

        payload = MockPayload()
        df = _payload_to_dataframe(payload, ["$close", "$volume"])
        assert df is not None
        assert not df.empty
        assert "$close" in df.columns
        assert "$volume" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_payload_to_dataframe_with_list(self):
        class MockPayload:
            def __init__(self):
                self.data = [
                    {"datetime": "2024-01-01", "close": 100.0, "volume": 1000},
                    {"datetime": "2024-01-02", "close": 101.0, "volume": 2000},
                ]

        payload = MockPayload()
        df = _payload_to_dataframe(payload, ["$close", "$volume"])
        assert df is not None
        assert not df.empty
        assert "$close" in df.columns
        assert "$volume" in df.columns

    def test_payload_to_dataframe_none(self):
        class MockPayload:
            def __init__(self):
                self.data = None

        payload = MockPayload()
        df = _payload_to_dataframe(payload, ["$close"])
        assert df is None

    def test_payload_to_dataframe_empty(self):
        class MockPayload:
            def __init__(self):
                self.data = []

        payload = MockPayload()
        df = _payload_to_dataframe(payload, ["$close"])
        assert df is None
