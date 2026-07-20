"""周期转换引擎测试。

覆盖:
- registry.py: 周期映射、粒度比较
- ohlcv.py: OHLCV 重采样核心逻辑
- volume.py: 成交量/持仓量聚合
- calendar.py: 周线/月线日期对齐
- auto.py: 自动周期选择
- __init__.py: resample_kline 统一入口
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datacore.resampler import resample_kline
from datacore.resampler.registry import (
    PERIOD_MAP,
    PERIOD_GRANULARITY,
    MINUTE_PERIODS,
    DAILY_PERIODS,
    get_pandas_freq,
    is_finer,
    is_same_category,
    validate_period,
    list_periods,
)
from datacore.resampler.ohlcv import (
    resample_ohlcv,
    resample_minute_to_minute,
    resample_daily_to_daily,
)
from datacore.resampler.volume import (
    aggregate_volume,
    aggregate_amount,
    aggregate_open_interest,
    compute_volume_profile,
    turnover_rate,
    amount_to_volume,
)
from datacore.resampler.calendar import (
    align_to_week_start,
    align_to_month_start,
    align_to_quarter_start,
    is_trading_day,
    get_trading_days_in_range,
    weekly_ohlcv,
    monthly_ohlcv,
    count_bars_per_period,
)
from datacore.resampler.auto import (
    infer_source_period,
    auto_select_period,
    suggest_periods,
)


# ============================================================
#  测试数据生成
# ============================================================

def _generate_minute_data(
    n: int = 120,
    start: str = "2024-01-02 09:30:00",
    freq: str = "1min",
    seed: int = 42,
) -> pd.DataFrame:
    """生成分钟级 OHLCV 测试数据。"""
    np.random.seed(seed)
    dates = pd.date_range(start=start, periods=n, freq=freq)
    base_price = 100.0
    returns = np.random.randn(n) * 0.001
    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.randn(n)) * 0.002)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.002)
    open_ = np.concatenate([[base_price], close[:-1]])
    volume = np.random.randint(100, 1000, n).astype(float)
    amount = volume * close
    open_interest = np.linspace(10000, 20000, n)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "amount": amount,
            "open_interest": open_interest,
        },
        index=dates,
    )


def _generate_daily_data(
    n: int = 60,
    start: str = "2024-01-01",
    seed: int = 42,
) -> pd.DataFrame:
    """生成日级 OHLCV 测试数据。"""
    np.random.seed(seed)
    dates = pd.bdate_range(start=start, periods=n)
    base_price = 100.0
    returns = np.random.randn(n) * 0.02
    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.randn(n)) * 0.01)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.01)
    open_ = np.concatenate([[base_price], close[:-1]])
    volume = np.random.randint(10000, 100000, n).astype(float)
    amount = volume * close
    open_interest = np.linspace(100000, 200000, n)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "amount": amount,
            "open_interest": open_interest,
        },
        index=dates,
    )


# ============================================================
#  registry.py 测试
# ============================================================

class TestRegistry:
    """周期映射注册表测试。"""

    def test_period_map_keys(self):
        """测试所有支持的周期都在映射中。"""
        expected = {"1m", "5m", "15m", "30m", "60m", "daily", "weekly", "monthly"}
        assert set(PERIOD_MAP.keys()) == expected

    def test_get_pandas_freq_valid(self):
        """测试获取合法周期的 pandas 频率。"""
        assert get_pandas_freq("1m") == "1min"
        assert get_pandas_freq("5m") == "5min"
        assert get_pandas_freq("daily") == "1D"
        assert get_pandas_freq("weekly") == "1W-MON"
        assert get_pandas_freq("monthly") == "1ME"

    def test_get_pandas_freq_invalid(self):
        """测试不合法周期抛出 ValueError。"""
        with pytest.raises(ValueError, match="不支持的周期"):
            get_pandas_freq("invalid")

    def test_is_finer_true(self):
        """测试细粒度到粗粒度返回 True。"""
        assert is_finer("1m", "5m") is True
        assert is_finer("1m", "daily") is True
        assert is_finer("5m", "15m") is True
        assert is_finer("daily", "weekly") is True
        assert is_finer("daily", "monthly") is True
        assert is_finer("weekly", "monthly") is True

    def test_is_finer_false(self):
        """测试粗粒度到细粒度返回 False。"""
        assert is_finer("5m", "1m") is False
        assert is_finer("daily", "1m") is False
        assert is_finer("weekly", "daily") is False
        assert is_finer("monthly", "weekly") is False

    def test_is_finer_same(self):
        """测试相同周期返回 False。"""
        assert is_finer("1m", "1m") is False
        assert is_finer("daily", "daily") is False

    def test_is_same_category(self):
        """测试同类周期判断。"""
        assert is_same_category("1m", "5m") is True
        assert is_same_category("daily", "weekly") is True
        assert is_same_category("1m", "daily") is False

    def test_validate_period_valid(self):
        """测试合法周期验证通过。"""
        for period in PERIOD_MAP.keys():
            validate_period(period)

    def test_validate_period_invalid(self):
        """测试不合法周期抛出异常。"""
        with pytest.raises(ValueError):
            validate_period("2m")
        with pytest.raises(ValueError):
            validate_period("yearly")

    def test_list_periods_order(self):
        """测试周期列表按粒度从细到粗排序。"""
        periods = list_periods()
        granularities = [PERIOD_GRANULARITY[p] for p in periods]
        assert granularities == sorted(granularities)

    def test_minute_periods(self):
        """测试分钟周期集合。"""
        assert MINUTE_PERIODS == {"1m", "5m", "15m", "30m", "60m"}

    def test_daily_periods(self):
        """测试日级别周期集合。"""
        assert DAILY_PERIODS == {"daily", "weekly", "monthly"}


# ============================================================
#  ohlcv.py 测试 - 分钟线逐级重采样
# ============================================================

class TestMinuteResampling:
    """分钟线逐级重采样测试。"""

    def test_1m_to_5m_shape(self):
        """测试 1m -> 5m 后行数约为 1/5。"""
        df = _generate_minute_data(n=120)
        result = resample_kline(df, "5m", "1m")
        assert len(result) <= len(df) / 5 + 1
        assert len(result) >= len(df) / 5 - 1

    def test_1m_to_15m_shape(self):
        """测试 1m -> 15m 后行数约为 1/15。"""
        df = _generate_minute_data(n=120)
        result = resample_kline(df, "15m", "1m")
        assert len(result) <= len(df) / 15 + 1

    def test_1m_to_30m_shape(self):
        """测试 1m -> 30m 后行数约为 1/30。"""
        df = _generate_minute_data(n=120)
        result = resample_kline(df, "30m", "1m")
        assert len(result) <= len(df) / 30 + 1

    def test_1m_to_60m_shape(self):
        """测试 1m -> 60m 后行数约为 1/60。"""
        df = _generate_minute_data(n=120)
        result = resample_kline(df, "60m", "1m")
        assert len(result) <= 3

    def test_5m_to_15m_shape(self):
        """测试 5m -> 15m 逐级重采样。"""
        df_1m = _generate_minute_data(n=120)
        df_5m = resample_kline(df_1m, "5m", "1m")
        df_15m = resample_kline(df_5m, "15m", "5m")
        assert len(df_15m) <= len(df_5m) / 3 + 1

    def test_5m_to_30m_shape(self):
        """测试 5m -> 30m 逐级重采样。"""
        df_1m = _generate_minute_data(n=120)
        df_5m = resample_kline(df_1m, "5m", "1m")
        df_30m = resample_kline(df_5m, "30m", "5m")
        assert len(df_30m) <= len(df_5m) / 6 + 1

    def test_cascaded_1m_5m_15m_30m_60m(self):
        """测试 1m->5m->15m->30m->60m 逐级重采样。"""
        df = _generate_minute_data(n=240)
        df_5m = resample_kline(df, "5m", "1m")
        df_15m = resample_kline(df_5m, "15m", "5m")
        df_30m = resample_kline(df_15m, "30m", "15m")
        df_60m = resample_kline(df_30m, "60m", "30m")
        assert len(df) > len(df_5m) > len(df_15m) > len(df_30m) > len(df_60m)


# ============================================================
#  ohlcv.py 测试 - OHLCV 聚合正确性
# ============================================================

class TestOHLCVAggregation:
    """OHLCV 各字段聚合正确性测试。"""

    def test_open_is_first(self):
        """测试 open 取周期内第一个值。"""
        df = _generate_minute_data(n=10)
        result = resample_kline(df, "5m", "1m")
        first_bar = df.iloc[:5]
        assert result["open"].iloc[0] == first_bar["open"].iloc[0]

    def test_high_is_max(self):
        """测试 high 取周期内最大值。"""
        df = _generate_minute_data(n=10)
        result = resample_kline(df, "5m", "1m")
        first_bar = df.iloc[:5]
        assert result["high"].iloc[0] == first_bar["high"].max()

    def test_low_is_min(self):
        """测试 low 取周期内最小值。"""
        df = _generate_minute_data(n=10)
        result = resample_kline(df, "5m", "1m")
        first_bar = df.iloc[:5]
        assert result["low"].iloc[0] == first_bar["low"].min()

    def test_close_is_last(self):
        """测试 close 取周期内最后一个值。"""
        df = _generate_minute_data(n=10)
        result = resample_kline(df, "5m", "1m")
        first_bar = df.iloc[:5]
        assert result["close"].iloc[0] == first_bar["close"].iloc[-1]

    def test_volume_is_sum(self):
        """测试 volume 取周期内总和。"""
        df = _generate_minute_data(n=10)
        result = resample_kline(df, "5m", "1m")
        first_bar = df.iloc[:5]
        assert result["volume"].iloc[0] == first_bar["volume"].sum()

    def test_amount_is_sum(self):
        """测试 amount 取周期内总和。"""
        df = _generate_minute_data(n=10)
        result = resample_kline(df, "5m", "1m")
        first_bar = df.iloc[:5]
        assert np.isclose(result["amount"].iloc[0], first_bar["amount"].sum())

    def test_open_interest_is_last(self):
        """测试 open_interest 取周期内最后一个值。"""
        df = _generate_minute_data(n=10)
        result = resample_kline(df, "5m", "1m")
        first_bar = df.iloc[:5]
        assert result["open_interest"].iloc[0] == first_bar["open_interest"].iloc[-1]

    def test_columns_preserved(self):
        """测试重采样后列名保持不变。"""
        df = _generate_minute_data(n=20)
        result = resample_kline(df, "5m", "1m")
        assert set(result.columns) == set(df.columns)


# ============================================================
#  ohlcv.py 测试 - 分钟线到日线
# ============================================================

class TestMinuteToDaily:
    """分钟线到日线聚合测试。"""

    def test_minute_to_daily(self):
        """测试分钟线聚合为日线。"""
        dates = pd.date_range("2024-01-02 09:30", periods=240, freq="1min")
        df = _generate_minute_data(n=240)
        df.index = dates
        result = resample_kline(df, "daily", "1m")
        assert len(result) >= 1
        assert "open" in result.columns
        assert "close" in result.columns


# ============================================================
#  ohlcv.py 测试 - 日线到周线到月线
# ============================================================

class TestDailyToWeeklyMonthly:
    """日线到周线、月线聚合测试。"""

    def test_daily_to_weekly_shape(self):
        """测试日线到周线后行数约为 1/5。"""
        df = _generate_daily_data(n=60)
        result = resample_kline(df, "weekly", "daily")
        assert len(result) <= len(df) / 4 + 1
        assert len(result) >= len(df) / 6

    def test_daily_to_monthly_shape(self):
        """测试日线到月线后行数。"""
        df = _generate_daily_data(n=60)
        result = resample_kline(df, "monthly", "daily")
        assert len(result) <= 4

    def test_weekly_to_monthly(self):
        """测试周线到月线逐级聚合。"""
        df_daily = _generate_daily_data(n=120)
        df_weekly = resample_kline(df_daily, "weekly", "daily")
        df_monthly = resample_kline(df_weekly, "monthly", "weekly")
        assert len(df_daily) > len(df_weekly) > len(df_monthly)

    def test_weekly_ohlcv_open_high_low_close(self):
        """测试周线 OHLC 聚合正确性。"""
        df = _generate_daily_data(n=10)
        result = weekly_ohlcv(df)
        first_week = df.iloc[:5]
        assert result["open"].iloc[0] == first_week["open"].iloc[0]
        assert result["high"].iloc[0] == first_week["high"].max()
        assert result["low"].iloc[0] == first_week["low"].min()
        assert result["close"].iloc[0] == first_week["close"].iloc[-1]

    def test_monthly_ohlcv_volume_sum(self):
        """测试月线成交量求和。"""
        df = _generate_daily_data(n=30)
        result = monthly_ohlcv(df)
        assert "volume" in result.columns
        assert result["volume"].iloc[0] > 0


# ============================================================
#  错误处理测试
# ============================================================

class TestErrorHandling:
    """错误处理和边界条件测试。"""

    def test_coarser_to_finer_raises(self):
        """测试反向请求（粗到细）抛出 ValueError。"""
        df = _generate_minute_data(n=10)
        with pytest.raises(ValueError, match="只能从细粒度重采样到粗粒度"):
            resample_kline(df, "1m", "5m")

    def test_daily_to_1m_raises(self):
        """测试日线到分钟线反向请求抛出异常。"""
        df = _generate_daily_data(n=10)
        with pytest.raises(ValueError, match="只能从细粒度重采样到粗粒度"):
            resample_kline(df, "1m", "daily")

    def test_monthly_to_weekly_raises(self):
        """测试月线到周线反向请求抛出异常。"""
        df = _generate_daily_data(n=60)
        df_monthly = resample_kline(df, "monthly", "daily")
        with pytest.raises(ValueError, match="只能从细粒度重采样到粗粒度"):
            resample_kline(df_monthly, "weekly", "monthly")

    def test_invalid_target_period(self):
        """测试无效目标周期。"""
        df = _generate_minute_data(n=10)
        with pytest.raises(ValueError, match="不支持的周期"):
            resample_kline(df, "2m", "1m")

    def test_invalid_source_period(self):
        """测试无效源周期。"""
        df = _generate_minute_data(n=10)
        with pytest.raises(ValueError, match="不支持的周期"):
            resample_kline(df, "5m", "2m")

    def test_not_dataframe_raises(self):
        """测试输入不是 DataFrame 抛出 TypeError。"""
        with pytest.raises(TypeError, match="df 必须是 pandas DataFrame"):
            resample_kline("not_a_df", "5m", "1m")

    def test_no_datetime_index_raises(self):
        """测试索引不是 DatetimeIndex 抛出 TypeError。"""
        df = pd.DataFrame({"open": [1, 2], "high": [3, 4], "low": [0, 1], "close": [2, 3]})
        with pytest.raises(TypeError, match="索引必须是 DatetimeIndex"):
            resample_kline(df, "5m", "1m")

    def test_missing_open_column(self):
        """测试缺少 open 列抛出 KeyError。"""
        df = _generate_minute_data(n=5).drop(columns=["open"])
        with pytest.raises(KeyError, match="缺少必要列"):
            resample_kline(df, "5m", "1m")


# ============================================================
#  边界条件测试
# ============================================================

class TestEdgeCases:
    """空数据、单根K线等边界条件测试。"""

    def test_empty_dataframe(self):
        """测试空 DataFrame 返回空 DataFrame。"""
        df = pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
            index=pd.DatetimeIndex([]),
        )
        result = resample_kline(df, "5m", "1m")
        assert result.empty

    def test_single_bar(self):
        """测试单根 K 线重采样。"""
        df = _generate_minute_data(n=1)
        result = resample_kline(df, "5m", "1m")
        assert len(result) == 1
        assert result["open"].iloc[0] == df["open"].iloc[0]

    def test_less_than_one_period(self):
        """测试不足一个周期的数据。"""
        df = _generate_minute_data(n=3)
        result = resample_kline(df, "5m", "1m")
        assert len(result) == 1

    def test_exact_one_period(self):
        """测试正好一个周期的数据。"""
        df = _generate_minute_data(n=5)
        result = resample_kline(df, "5m", "1m")
        assert len(result) == 1


# ============================================================
#  auto 模式测试
# ============================================================

class TestAutoMode:
    """auto 模式自动选择测试。"""

    def test_infer_source_period_1m(self):
        """测试推断 1分钟 周期。"""
        df = _generate_minute_data(n=20, freq="1min")
        assert infer_source_period(df) == "1m"

    def test_infer_source_period_5m(self):
        """测试推断 5分钟 周期。"""
        df = _generate_minute_data(n=20, freq="5min")
        assert infer_source_period(df) == "5m"

    def test_infer_source_period_daily(self):
        """测试推断日线周期。"""
        df = _generate_daily_data(n=20)
        assert infer_source_period(df) == "daily"

    def test_auto_select_period_many_bars(self):
        """测试大量数据时自动选择较粗周期。"""
        df = _generate_minute_data(n=1000, freq="1min")
        period = auto_select_period(df, target_bars=200)
        assert period != "1m"

    def test_auto_select_period_few_bars(self):
        """测试少量数据时保持原周期。"""
        df = _generate_daily_data(n=30)
        period = auto_select_period(df, target_bars=200)
        assert period == "daily"

    def test_suggest_periods_not_empty(self):
        """测试 suggest_periods 返回非空列表。"""
        df = _generate_minute_data(n=100)
        suggestions = suggest_periods(df)
        assert len(suggestions) > 0
        assert all(isinstance(s, tuple) and len(s) == 2 for s in suggestions)

    def test_resample_kline_auto(self):
        """测试 resample_kline auto 模式。"""
        df = _generate_minute_data(n=500, freq="1min")
        result = resample_kline(df, "auto")
        assert not result.empty
        assert "open" in result.columns

    def test_infer_source_period_empty(self):
        """测试空 DataFrame 推断周期返回 None。"""
        df = pd.DataFrame(
            columns=["open", "high", "low", "close"],
            index=pd.DatetimeIndex([]),
        )
        assert infer_source_period(df) is None

    def test_auto_select_period_empty(self):
        """测试空 DataFrame auto_select 返回 daily。"""
        df = pd.DataFrame(
            columns=["open", "high", "low", "close"],
            index=pd.DatetimeIndex([]),
        )
        assert auto_select_period(df) == "daily"


# ============================================================
#  volume.py 测试
# ============================================================

class TestVolumeAggregation:
    """成交量/持仓量聚合测试。"""

    def test_aggregate_volume_sum(self):
        """测试成交量聚合计。"""
        df = _generate_minute_data(n=10)
        result = aggregate_volume(df["volume"], "5min")
        assert len(result) < len(df)
        assert result.iloc[0] == df["volume"].iloc[:5].sum()

    def test_aggregate_amount_sum(self):
        """测试成交额聚合。"""
        df = _generate_minute_data(n=10)
        result = aggregate_amount(df["amount"], "5min")
        assert result.iloc[0] == pytest.approx(df["amount"].iloc[:5].sum())

    def test_aggregate_open_interest_last(self):
        """测试持仓量取最后值。"""
        df = _generate_minute_data(n=10)
        result = aggregate_open_interest(df["open_interest"], "5min")
        assert result.iloc[0] == df["open_interest"].iloc[4]

    def test_compute_volume_profile(self):
        """测试成交量分布特征计算。"""
        df = _generate_minute_data(n=20)
        result = compute_volume_profile(df, "5min")
        assert "volume" in result.columns
        assert "volume_avg" in result.columns
        assert "volume_max" in result.columns
        assert "volume_min" in result.columns
        assert "volume_std" in result.columns

    def test_turnover_rate(self):
        """测试换手率计算。"""
        df = _generate_minute_data(n=5)
        rate = turnover_rate(df["volume"], total_shares=1000000)
        assert (rate >= 0).all()
        assert (rate <= 1).all()

    def test_turnover_rate_invalid_total(self):
        """测试无效总股本抛出异常。"""
        with pytest.raises(ValueError, match="必须大于 0"):
            turnover_rate(pd.Series([100]), total_shares=0)

    def test_amount_to_volume(self):
        """测试成交额转成交量。"""
        amount = pd.Series([10000, 20000])
        price = pd.Series([10.0, 20.0])
        vol = amount_to_volume(amount, price)
        assert vol.iloc[0] == pytest.approx(1000.0)
        assert vol.iloc[1] == pytest.approx(1000.0)


# ============================================================
#  calendar.py 测试
# ============================================================

class TestCalendarAlignment:
    """交易日历对齐测试。"""

    def test_align_to_week_start_monday(self):
        """测试对齐到周一。"""
        dates = pd.DatetimeIndex(["2024-01-03", "2024-01-04", "2024-01-05"])
        aligned = align_to_week_start(dates, week_start=0)
        assert all(d.dayofweek == 0 for d in aligned)

    def test_align_to_month_start(self):
        """测试对齐到月初。"""
        dates = pd.DatetimeIndex(["2024-01-15", "2024-02-20"])
        aligned = align_to_month_start(dates)
        assert aligned[0].day == 1
        assert aligned[1].day == 1

    def test_align_to_quarter_start(self):
        """测试对齐到季初。"""
        dates = pd.DatetimeIndex(["2024-02-15", "2024-05-20"])
        aligned = align_to_quarter_start(dates)
        assert aligned[0].month == 1
        assert aligned[1].month == 4

    def test_is_trading_day_weekday(self):
        """测试工作日是交易日。"""
        assert is_trading_day(pd.Timestamp("2024-01-02")) is True

    def test_is_trading_day_weekend(self):
        """测试周末不是交易日。"""
        assert is_trading_day(pd.Timestamp("2024-01-06")) is False
        assert is_trading_day(pd.Timestamp("2024-01-07")) is False

    def test_is_trading_day_holiday(self):
        """测试节假日不是交易日。"""
        holidays = {pd.Timestamp("2024-01-01").normalize()}
        assert is_trading_day(pd.Timestamp("2024-01-01"), holidays) is False

    def test_get_trading_days_in_range(self):
        """测试获取日期范围内的交易日。"""
        trading_days = get_trading_days_in_range(
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-07"),
        )
        assert len(trading_days) == 5

    def test_count_bars_per_period(self):
        """测试统计每周期 K 线数量。"""
        df = _generate_minute_data(n=30)
        counts = count_bars_per_period(df.index, "5min")
        assert counts.iloc[0] == 5
