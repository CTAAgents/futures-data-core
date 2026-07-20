"""Phase 1 (v1.1) tests: AsyncDataProvider, core types, data freshness, F10."""

from __future__ import annotations

import asyncio
import time

import pytest

from datacore import AsyncDataProvider, UnifiedDataProvider
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.core.types import KlineBar, QuoteData, FreshnessStatus
from datacore.core.data_freshness import DataFreshnessAssessor


class TestKlineBar:
    def test_basic_construction(self):
        bar = KlineBar(date="2025-01-02", open=100, high=105, low=98, close=103, volume=1000)
        assert bar.open == 100.0
        assert bar.close == 103.0
        assert bar.volume == 1000.0

    def test_numeric_coercion(self):
        bar = KlineBar(date="2025-01-02", open="100", high="105", low="98", close="103", volume="1000")
        assert isinstance(bar.open, float)
        assert isinstance(bar.high, float)
        assert bar.volume == 1000.0

    def test_default_amount_and_oi(self):
        bar = KlineBar(date="2025-01-02", open=100, high=105, low=98, close=103, volume=1000)
        assert bar.amount == 0.0
        assert bar.open_interest == 0.0

    def test_none_values_coerce_to_zero(self):
        bar = KlineBar(date="2025-01-02", open=None, high=105, low=98, close=None, volume=None)
        assert bar.open == 0.0
        assert bar.close == 0.0
        assert bar.volume == 0.0


class TestQuoteData:
    def test_basic_construction(self):
        q = QuoteData(symbol="RB", name="螺纹钢", last_price=3500, prev_close=3480)
        assert q.symbol == "RB"
        assert q.name == "螺纹钢"

    def test_change_pct(self):
        q = QuoteData(symbol="RB", last_price=3500, prev_close=3480)
        assert abs(q.change_pct - 0.57) < 0.01

    def test_change_pct_zero_prev_close(self):
        q = QuoteData(symbol="RB", last_price=3500, prev_close=0)
        assert q.change_pct == 0.0

    def test_defaults(self):
        q = QuoteData(symbol="RB")
        assert q.last_price == 0.0
        assert q.bid1 == 0.0
        assert q.ask1 == 0.0


class TestFreshnessStatus:
    def test_construction(self):
        fs = FreshnessStatus(
            is_fresh=True, age_seconds=10, threshold_seconds=60, status="fresh")
        assert fs.is_fresh is True
        assert fs.status == "fresh"
        assert fs.message == ""


class TestDataFreshnessAssessor:
    def test_fresh_data(self):
        assessor = DataFreshnessAssessor()
        now = time.time()
        result = assessor.assess(now, "quote")
        assert result.is_fresh is True
        assert result.status == "fresh"

    def test_stale_data(self):
        assessor = DataFreshnessAssessor()
        old = time.time() - 20
        result = assessor.assess(old, "quote")
        assert result.status == "stale"
        assert result.is_fresh is True

    def test_expired_data(self):
        assessor = DataFreshnessAssessor()
        old = time.time() - 120
        result = assessor.assess(old, "quote")
        assert result.status == "expired"
        assert result.is_fresh is False

    def test_custom_threshold(self):
        assessor = DataFreshnessAssessor({"custom": 100})
        assessor.set_threshold("custom", 200)
        assert assessor.get_threshold("custom") == 200

    def test_default_threshold_for_unknown(self):
        assessor = DataFreshnessAssessor()
        assert assessor.get_threshold("nonexistent") == 3600.0

    def test_period_to_category(self):
        assert DataFreshnessAssessor.period_to_category("daily") == "ohlcv_daily"
        assert DataFreshnessAssessor.period_to_category("60m") == "ohlcv_60m"
        assert DataFreshnessAssessor.period_to_category("weekly") == "ohlcv_weekly"
        assert DataFreshnessAssessor.period_to_category("unknown") == "ohlcv_daily"
        assert DataFreshnessAssessor.period_to_category("1h") == "ohlcv_60m"
        assert DataFreshnessAssessor.period_to_category("monthly") == "ohlcv_monthly"

    def test_future_timestamp(self):
        assessor = DataFreshnessAssessor()
        future = time.time() + 100
        result = assessor.assess(future, "quote")
        assert result.age_seconds == 0.0
        assert result.is_fresh is True

    def test_thresholds_init(self):
        assessor = DataFreshnessAssessor(thresholds={"quote": 999})
        assert assessor.get_threshold("quote") == 999


class TestAsyncDataProvider:
    @pytest.mark.asyncio
    async def test_get_ohlcv(self):
        adc = AsyncDataProvider()
        payload = await adc.get("RB", DataType.OHLCV, {"period": "daily", "days": 20})
        assert payload is not None
        assert payload.symbol == "RB"
        assert payload.data_type == DataType.OHLCV

    @pytest.mark.asyncio
    async def test_get_returns_consistent_with_sync(self):
        adc = AsyncDataProvider()
        dc = UnifiedDataProvider()
        async_result = await adc.get("RB", DataType.OHLCV, {"period": "daily", "days": 5})
        sync_result = dc.get("RB", DataType.OHLCV, {"period": "daily", "days": 5})
        assert async_result.symbol == sync_result.symbol
        assert async_result.data_type == sync_result.data_type
        assert async_result.available == sync_result.available

    @pytest.mark.asyncio
    async def test_get_batch(self):
        adc = AsyncDataProvider()
        results = await adc.get_batch(["RB", "CU"], DataType.OHLCV, {"period": "daily", "days": 5})
        assert "RB" in results
        assert "CU" in results
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_symbols(self):
        adc = AsyncDataProvider()
        result = await adc.list_symbols()
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_list_symbols_with_market(self):
        adc = AsyncDataProvider()
        result = await adc.list_symbols(MarketType.FUTURES)
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    @pytest.mark.asyncio
    async def test_get_health(self):
        adc = AsyncDataProvider()
        health = await adc.get_health()
        assert "status" in health
        assert "sources" in health
        assert "version" in health
        assert health["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_get_f10(self):
        adc = AsyncDataProvider()
        result = await adc.get_f10("RB")
        assert result.symbol == "RB"
        assert result.data_type == DataType.F10_REPORT
        assert isinstance(result.data, dict)
        assert "sub_modules" in result.meta

    def test_ensure_sync_creates_provider(self):
        adc = AsyncDataProvider()
        assert adc._sync is None
        adc._ensure_sync()
        assert adc._sync is not None
        assert isinstance(adc._sync, UnifiedDataProvider)


class TestGetF10Sync:
    def test_f10_contains_submodules(self):
        dc = UnifiedDataProvider()
        result = dc.get_f10("RB")
        assert result.symbol == "RB"
        assert result.data_type == DataType.F10_REPORT
        assert isinstance(result.data, dict)
        assert "sub_modules" in result.meta
        assert isinstance(result.meta["sub_modules"], list)
        assert len(result.meta["sub_modules"]) >= 3

    def test_f10_grade(self):
        dc = UnifiedDataProvider()
        result = dc.get_f10("RB")
        assert result.grade in (SourceGrade.PRIMARY, SourceGrade.UNAVAILABLE)

    def test_f10_unknown_symbol(self):
        dc = UnifiedDataProvider()
        result = dc.get_f10("ZZZZZ")
        assert result.symbol == "ZZZZZ"
