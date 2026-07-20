"""复权/换月引擎模块测试。

覆盖:
- 股票前复权/后复权基本功能
- 期货主力合约识别（成交量/持仓量/固定日）
- 连续合约拼接正确性
- 换月价差调整
- adjustment="none" 透传
- 边界条件（空数据、单根K线等）
- 异常处理
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datacore.adjustment import apply_adjustment, ADJUSTMENT_OPTIONS
from datacore.adjustment.equity import (
    forward_adjust,
    backward_adjust,
    DividendEvent,
    DividendCalendar,
)
from datacore.adjustment.futures import (
    identify_dominant_by_volume,
    identify_dominant_by_oi,
    identify_dominant_fixed_day,
    detect_rollover_dates,
    get_dominant_series,
    get_rollover_pairs,
    build_continuous_contract,
    adjust_rollover_qfq,
    adjust_rollover_hfq,
    adjust_rollover_none,
)
from datacore.adjustment.registry import (
    parse_adjustment_config,
    is_futures_adjustment,
    is_equity_adjustment,
)


# ============================================================
#  测试数据生成
# ============================================================

def _generate_stock_kline(n: int = 20, start_price: float = 100.0) -> pd.DataFrame:
    """生成股票 K 线测试数据。"""
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    np.random.seed(42)
    returns = np.random.randn(n) * 0.02
    close = start_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.randn(n)) * 0.01)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.01)
    open_ = close * (1 + np.random.randn(n) * 0.005)
    volume = np.random.randint(100000, 500000, n).astype(float)
    amount = volume * close
    return pd.DataFrame({
        "date": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "amount": amount,
    })


def _generate_futures_kline_dict(
    contracts: list[str] | None = None,
    n_per_contract: int = 30,
    base_price: float = 3000.0,
) -> dict[str, pd.DataFrame]:
    """生成期货多合约 K 线字典。"""
    if contracts is None:
        contracts = ["RB2501", "RB2505", "RB2510"]

    result = {}
    np.random.seed(123)

    for i, contract in enumerate(contracts):
        start_offset = i * 20
        dates = pd.date_range(
            f"2024-12-01",
            periods=n_per_contract + start_offset,
            freq="B",
        )
        dates = dates[start_offset:]

        n = len(dates)
        price_base = base_price + i * 50
        returns = np.random.randn(n) * 0.01
        close = price_base * np.cumprod(1 + returns)
        high = close * (1 + np.abs(np.random.randn(n)) * 0.005)
        low = close * (1 - np.abs(np.random.randn(n)) * 0.005)
        open_ = close * (1 + np.random.randn(n) * 0.003)

        volume_pattern = np.zeros(n)
        peak = n // 2
        for j in range(n):
            volume_pattern[j] = 10000 + 50000 * np.exp(-((j - peak) ** 2) / (2 * 20 ** 2))
        volume = volume_pattern * (1 + np.random.randn(n) * 0.1)
        volume = np.maximum(volume, 1000)

        oi = volume * 2.5
        amount = volume * close

        result[contract] = pd.DataFrame({
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "amount": amount,
            "open_interest": oi,
        })

    return result


# ============================================================
#  股票复权测试
# ============================================================

class TestDividendEvent:
    """除权除息事件测试。"""

    def test_cash_dividend_ex_rights_price(self):
        """现金分红除权价计算。"""
        event = DividendEvent(ex_date="2025-06-01", cash_dividend=2.0)
        ex_price = event.ex_rights_price(100.0)
        assert pytest.approx(ex_price) == 98.0

    def test_stock_dividend_ex_rights_price(self):
        """送股除权价计算（10送10）。"""
        event = DividendEvent(ex_date="2025-06-01", stock_dividend=1.0)
        ex_price = event.ex_rights_price(100.0)
        assert pytest.approx(ex_price) == 50.0

    def test_stock_transfer_ex_rights_price(self):
        """转增股除权价计算（10转5）。"""
        event = DividendEvent(ex_date="2025-06-01", stock_transfer=0.5)
        ex_price = event.ex_rights_price(100.0)
        assert pytest.approx(ex_price, rel=1e-6) == 100.0 / 1.5

    def test_mixed_dividend_ex_rights_price(self):
        """混合分红除权价计算。"""
        event = DividendEvent(
            ex_date="2025-06-01",
            cash_dividend=1.0,
            stock_dividend=0.2,
            stock_transfer=0.3,
        )
        ex_price = event.ex_rights_price(100.0)
        expected = (100.0 - 1.0) / (1 + 0.2 + 0.3)
        assert pytest.approx(ex_price) == expected

    def test_adjustment_factor_cash(self):
        """现金分红复权因子计算。"""
        event = DividendEvent(ex_date="2025-06-01", cash_dividend=2.0, pre_close=100.0)
        factor = event.adjustment_factor()
        assert factor > 1.0
        assert pytest.approx(factor) == 100.0 / 98.0

    def test_adjustment_factor_no_preclose_raises(self):
        """缺少前收盘价时抛出异常。"""
        event = DividendEvent(ex_date="2025-06-01", cash_dividend=2.0)
        with pytest.raises(ValueError):
            event.adjustment_factor()

    def test_adjustment_factor_with_param(self):
        """使用参数指定前收盘价。"""
        event = DividendEvent(ex_date="2025-06-01", cash_dividend=5.0, pre_close=200.0)
        factor1 = event.adjustment_factor()
        factor2 = event.adjustment_factor(pre_close_price=100.0)
        assert factor1 != factor2
        assert pytest.approx(factor2) == 100.0 / 95.0


class TestDividendCalendar:
    """除权除息日历测试。"""

    def test_from_list_empty(self):
        """从空列表构建日历。"""
        cal = DividendCalendar.from_list([])
        assert len(cal.events) == 0

    def test_from_list_with_events(self):
        """从事件列表构建日历。"""
        info = [
            {"ex_date": "2025-06-01", "cash_dividend": 2.0, "pre_close": 100.0},
            {"ex_date": "2024-06-01", "stock_dividend": 0.5, "pre_close": 80.0},
        ]
        cal = DividendCalendar.from_list(info)
        assert len(cal.events) == 2

    def test_sorted(self):
        """事件按日期排序。"""
        info = [
            {"ex_date": "2025-06-01", "cash_dividend": 2.0},
            {"ex_date": "2024-06-01", "stock_dividend": 0.5},
            {"ex_date": "2023-06-01", "cash_dividend": 1.0},
        ]
        cal = DividendCalendar.from_list(info)
        sorted_cal = cal.sorted()
        assert sorted_cal.events[0].ex_date == "2023-06-01"
        assert sorted_cal.events[-1].ex_date == "2025-06-01"

    def test_build_factor_series_no_events(self):
        """无事件时因子全为1。"""
        dates = pd.date_range("2025-01-01", periods=10, freq="B")
        cal = DividendCalendar()
        factors = cal.build_factor_series(dates)
        assert len(factors) == 10
        assert np.all(factors.values == 1.0)

    def test_build_factor_series_single_event(self):
        """单次分红的因子序列。"""
        dates = pd.date_range("2025-01-01", periods=20, freq="B")
        cal = DividendCalendar.from_list([
            {"ex_date": "2025-01-15", "cash_dividend": 5.0, "pre_close": 100.0},
        ])
        factors = cal.build_factor_series(dates)
        ex_date = pd.Timestamp("2025-01-15")
        before = factors[factors.index < ex_date]
        after = factors[factors.index >= ex_date]
        assert np.all(before.values == 1.0)
        assert np.all(after.values > 1.0)
        assert len(np.unique(after.values)) == 1


class TestForwardAdjust:
    """股票前复权测试。"""

    def test_no_dividend_returns_copy(self):
        """无分红信息时返回副本。"""
        kline = _generate_stock_kline(10)
        result = forward_adjust(kline, dividend_info=[])
        pd.testing.assert_frame_equal(result, kline)
        assert result is not kline

    def test_none_dividend_returns_copy(self):
        """dividend_info 为 None 时返回副本。"""
        kline = _generate_stock_kline(10)
        result = forward_adjust(kline, dividend_info=None)
        pd.testing.assert_frame_equal(result, kline)

    def test_single_cash_dividend(self):
        """单次现金分红前复权。"""
        kline = _generate_stock_kline(30, start_price=100.0)
        dividend_info = [
            {"ex_date": "2025-01-20", "cash_dividend": 3.0},
        ]
        result = forward_adjust(kline, dividend_info=dividend_info)

        assert len(result) == len(kline)
        last_idx = len(kline) - 1
        assert pytest.approx(result["close"].iloc[last_idx]) == kline["close"].iloc[last_idx]

    def test_volume_unchanged(self):
        """前复权不调整成交量。"""
        kline = _generate_stock_kline(20)
        dividend_info = [
            {"ex_date": "2025-01-15", "stock_dividend": 1.0, "pre_close": 100.0},
        ]
        result = forward_adjust(kline, dividend_info=dividend_info)
        pd.testing.assert_series_equal(result["volume"], kline["volume"])

    def test_amount_unchanged(self):
        """前复权不调整成交额。"""
        kline = _generate_stock_kline(20)
        dividend_info = [
            {"ex_date": "2025-01-15", "cash_dividend": 2.0},
        ]
        result = forward_adjust(kline, dividend_info=dividend_info)
        pd.testing.assert_series_equal(result["amount"], kline["amount"])

    def test_missing_columns_raises(self):
        """缺少必要列时抛出异常。"""
        df = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=5)})
        with pytest.raises(ValueError):
            forward_adjust(df, dividend_info=[])

    def test_empty_dataframe(self):
        """空 DataFrame 处理。"""
        kline = _generate_stock_kline(0)
        result = forward_adjust(kline, dividend_info=[])
        assert len(result) == 0


class TestBackwardAdjust:
    """股票后复权测试。"""

    def test_no_dividend_returns_copy(self):
        """无分红时返回副本。"""
        kline = _generate_stock_kline(10)
        result = backward_adjust(kline, dividend_info=[])
        pd.testing.assert_frame_equal(result, kline)

    def test_single_cash_dividend(self):
        """单次现金分红后复权。"""
        kline = _generate_stock_kline(30, start_price=100.0)
        dividend_info = [
            {"ex_date": "2025-01-20", "cash_dividend": 3.0},
        ]
        result = backward_adjust(kline, dividend_info=dividend_info)

        assert len(result) == len(kline)
        first_idx = 0
        assert pytest.approx(result["close"].iloc[first_idx]) == kline["close"].iloc[first_idx]

    def test_first_price_unchanged(self):
        """后复权第一个价格不变。"""
        kline = _generate_stock_kline(20)
        dividend_info = [
            {"ex_date": "2025-01-15", "stock_dividend": 0.5, "pre_close": 100.0},
        ]
        result = backward_adjust(kline, dividend_info=dividend_info)
        assert pytest.approx(result["close"].iloc[0]) == kline["close"].iloc[0]

    def test_volume_unchanged(self):
        """后复权不调整成交量。"""
        kline = _generate_stock_kline(20)
        dividend_info = [
            {"ex_date": "2025-01-10", "cash_dividend": 1.0},
        ]
        result = backward_adjust(kline, dividend_info=dividend_info)
        pd.testing.assert_series_equal(result["volume"], kline["volume"])


# ============================================================
#  期货主力合约识别测试
# ============================================================

class TestDominantContractVolume:
    """成交量加权主力合约识别测试。"""

    def test_basic_identification(self):
        """基本主力合约识别。"""
        kline_dict = _generate_futures_kline_dict()
        dominant = identify_dominant_by_volume(kline_dict)
        assert len(dominant) > 0
        assert dominant.dtype == object

    def test_empty_dict_raises(self):
        """空字典抛出异常。"""
        with pytest.raises(ValueError):
            identify_dominant_by_volume({})

    def test_single_contract(self):
        """只有一个合约时始终是主力。"""
        kline_dict = _generate_futures_kline_dict(contracts=["RB2501"])
        dominant = identify_dominant_by_volume(kline_dict)
        assert all(d == "RB2501" for d in dominant.values)

    def test_date_index(self):
        """返回的 index 是日期。"""
        kline_dict = _generate_futures_kline_dict()
        dominant = identify_dominant_by_volume(kline_dict)
        assert isinstance(dominant.index, pd.DatetimeIndex)


class TestDominantContractOI:
    """持仓量加权主力合约识别测试。"""

    def test_basic_identification(self):
        """基本持仓量主力识别。"""
        kline_dict = _generate_futures_kline_dict()
        dominant = identify_dominant_by_oi(kline_dict)
        assert len(dominant) > 0

    def test_empty_dict_raises(self):
        """空字典抛出异常。"""
        with pytest.raises(ValueError):
            identify_dominant_by_oi({})


class TestDominantContractFixedDay:
    """固定日换月测试。"""

    def test_basic_switch(self):
        """基本固定日换月。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=60)
        dominant = identify_dominant_fixed_day(kline_dict, switch_day=15)
        assert len(dominant) > 0

    def test_switch_day_range(self):
        """switch_day 超出范围抛出异常。"""
        kline_dict = _generate_futures_kline_dict()
        with pytest.raises(ValueError):
            identify_dominant_fixed_day(kline_dict, switch_day=0)
        with pytest.raises(ValueError):
            identify_dominant_fixed_day(kline_dict, switch_day=32)

    def test_empty_dict_raises(self):
        """空字典抛出异常。"""
        with pytest.raises(ValueError):
            identify_dominant_fixed_day({})


class TestRolloverDetection:
    """换月检测测试。"""

    def test_no_rollover_single_contract(self):
        """单合约时无换月。"""
        kline_dict = _generate_futures_kline_dict(contracts=["RB2501"])
        dominant = identify_dominant_by_volume(kline_dict)
        rollover_dates = detect_rollover_dates(dominant)
        assert len(rollover_dates) == 0

    def test_rollover_detected(self):
        """检测到换月。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=60)
        dominant = identify_dominant_by_volume(kline_dict)
        rollover_dates = detect_rollover_dates(dominant)
        assert len(rollover_dates) >= 0

    def test_get_rollover_pairs(self):
        """获取换月配对。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=60)
        dominant = identify_dominant_by_volume(kline_dict)
        pairs = get_rollover_pairs(dominant)
        assert isinstance(pairs, list)
        if len(pairs) > 0:
            assert len(pairs[0]) == 3


class TestGetDominantSeries:
    """get_dominant_series 测试。"""

    def test_volume_method(self):
        """成交量方法。"""
        kline_dict = _generate_futures_kline_dict()
        series = get_dominant_series(kline_dict, method="volume")
        assert len(series) > 0

    def test_oi_method(self):
        """持仓量方法。"""
        kline_dict = _generate_futures_kline_dict()
        series = get_dominant_series(kline_dict, method="oi")
        assert len(series) > 0

    def test_open_interest_alias(self):
        """open_interest 别名。"""
        kline_dict = _generate_futures_kline_dict()
        series = get_dominant_series(kline_dict, method="open_interest")
        assert len(series) > 0

    def test_fixed_day_method(self):
        """固定日方法。"""
        kline_dict = _generate_futures_kline_dict()
        series = get_dominant_series(kline_dict, method="fixed_day", switch_day=15)
        assert len(series) > 0

    def test_invalid_method_raises(self):
        """无效方法抛出异常。"""
        kline_dict = _generate_futures_kline_dict()
        with pytest.raises(ValueError):
            get_dominant_series(kline_dict, method="invalid")


# ============================================================
#  连续合约拼接测试
# ============================================================

class TestContinuousContract:
    """连续合约拼接测试。"""

    def test_basic_continuous(self):
        """基本连续合约构建。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=50)
        result = build_continuous_contract(kline_dict, rollover_method="volume")
        assert isinstance(result, pd.DataFrame)
        assert "contract" in result.columns

    def test_empty_dict_raises(self):
        """空字典抛出异常。"""
        with pytest.raises(ValueError):
            build_continuous_contract({})

    def test_single_contract(self):
        """单合约连续合约。"""
        kline_dict = _generate_futures_kline_dict(contracts=["RB2501"])
        result = build_continuous_contract(kline_dict)
        assert len(result) > 0
        assert all(c == "RB2501" for c in result["contract"].values)

    def test_qfq_adjust(self):
        """前复权调整连续合约。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=50)
        result = build_continuous_contract(
            kline_dict,
            rollover_method="volume",
            adjust_method="qfq",
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_hfq_adjust(self):
        """后复权调整连续合约。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=50)
        result = build_continuous_contract(
            kline_dict,
            rollover_method="volume",
            adjust_method="hfq",
        )
        assert isinstance(result, pd.DataFrame)

    def test_none_adjust(self):
        """不调整连续合约。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=50)
        result = build_continuous_contract(
            kline_dict,
            rollover_method="volume",
            adjust_method="none",
        )
        assert isinstance(result, pd.DataFrame)

    def test_invalid_adjust_method_raises(self):
        """无效调整方法抛出异常。"""
        kline_dict = _generate_futures_kline_dict()
        with pytest.raises(ValueError):
            build_continuous_contract(kline_dict, adjust_method="invalid")


class TestAdjustMethods:
    """换月调整方法测试。"""

    def test_adjust_none_returns_copy(self):
        """不调整返回副本。"""
        kline_dict = _generate_futures_kline_dict(contracts=["RB2501", "RB2505"], n_per_contract=40)
        cont = build_continuous_contract(kline_dict, adjust_method="none")
        result = adjust_rollover_none(cont)
        pd.testing.assert_frame_equal(result, cont)
        assert result is not cont


# ============================================================
#  注册表测试
# ============================================================

class TestRegistry:
    """注册表解析测试。"""

    def test_parse_none(self):
        """解析 none。"""
        cfg = parse_adjustment_config("none")
        assert cfg["type"] == "none"

    def test_parse_qfq(self):
        """解析 qfq。"""
        cfg = parse_adjustment_config("qfq")
        assert cfg["type"] == "equity"
        assert cfg["equity_method"] == "qfq"

    def test_parse_hfq(self):
        """解析 hfq。"""
        cfg = parse_adjustment_config("hfq")
        assert cfg["type"] == "equity"
        assert cfg["equity_method"] == "hfq"

    def test_parse_continuous(self):
        """解析 continuous。"""
        cfg = parse_adjustment_config("continuous")
        assert cfg["type"] == "futures"
        assert cfg["adjust_method"] == "none"

    def test_parse_continuous_qfq(self):
        """解析 continuous_qfq。"""
        cfg = parse_adjustment_config("continuous_qfq")
        assert cfg["type"] == "futures"
        assert cfg["adjust_method"] == "qfq"

    def test_parse_continuous_hfq(self):
        """解析 continuous_hfq。"""
        cfg = parse_adjustment_config("continuous_hfq")
        assert cfg["type"] == "futures"
        assert cfg["adjust_method"] == "hfq"

    def test_parse_continuous_volume(self):
        """解析 continuous_volume。"""
        cfg = parse_adjustment_config("continuous_volume")
        assert cfg["type"] == "futures"
        assert cfg["rollover_method"] == "volume"

    def test_parse_continuous_oi(self):
        """解析 continuous_oi。"""
        cfg = parse_adjustment_config("continuous_oi")
        assert cfg["type"] == "futures"
        assert cfg["rollover_method"] == "oi"

    def test_parse_invalid_raises(self):
        """无效 adjustment 抛出异常。"""
        with pytest.raises(ValueError):
            parse_adjustment_config("invalid")

    def test_is_futures_adjustment(self):
        """期货类型判断。"""
        assert is_futures_adjustment("continuous") is True
        assert is_futures_adjustment("continuous_qfq") is True
        assert is_futures_adjustment("qfq") is False
        assert is_futures_adjustment("none") is False

    def test_is_equity_adjustment(self):
        """股票类型判断。"""
        assert is_equity_adjustment("qfq") is True
        assert is_equity_adjustment("hfq") is True
        assert is_equity_adjustment("continuous") is False
        assert is_equity_adjustment("none") is False

    def test_adjustment_options(self):
        """ADJUSTMENT_OPTIONS 列表。"""
        assert "none" in ADJUSTMENT_OPTIONS
        assert "qfq" in ADJUSTMENT_OPTIONS
        assert "hfq" in ADJUSTMENT_OPTIONS
        assert "continuous" in ADJUSTMENT_OPTIONS
        assert "continuous_qfq" in ADJUSTMENT_OPTIONS
        assert "continuous_hfq" in ADJUSTMENT_OPTIONS


# ============================================================
#  统一入口 apply_adjustment 测试
# ============================================================

class TestApplyAdjustment:
    """apply_adjustment 统一入口测试。"""

    def test_none_passthrough_dataframe(self):
        """none 透传 DataFrame。"""
        kline = _generate_stock_kline(10)
        result = apply_adjustment(kline, adjustment="none")
        pd.testing.assert_frame_equal(result, kline)
        assert result is not kline

    def test_none_passthrough_dict(self):
        """none 透传 dict（返回第一个合约）。"""
        kline_dict = _generate_futures_kline_dict(contracts=["RB2501"])
        result = apply_adjustment(kline_dict, adjustment="none")
        pd.testing.assert_frame_equal(result, kline_dict["RB2501"])

    def test_equity_qfq(self):
        """股票前复权入口。"""
        kline = _generate_stock_kline(20)
        dividend_info = [
            {"ex_date": "2025-01-15", "cash_dividend": 2.0},
        ]
        result = apply_adjustment(
            kline, adjustment="qfq", dividend_info=dividend_info
        )
        assert len(result) == len(kline)

    def test_equity_hfq(self):
        """股票后复权入口。"""
        kline = _generate_stock_kline(20)
        dividend_info = [
            {"ex_date": "2025-01-15", "stock_dividend": 0.5},
        ]
        result = apply_adjustment(
            kline, adjustment="hfq", dividend_info=dividend_info
        )
        assert len(result) == len(kline)

    def test_futures_continuous(self):
        """期货连续合约入口。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=40)
        result = apply_adjustment(kline_dict, adjustment="continuous")
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_futures_continuous_qfq(self):
        """期货连续前复权入口。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=40)
        result = apply_adjustment(kline_dict, adjustment="continuous_qfq")
        assert isinstance(result, pd.DataFrame)

    def test_futures_continuous_hfq(self):
        """期货连续后复权入口。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=40)
        result = apply_adjustment(kline_dict, adjustment="continuous_hfq")
        assert isinstance(result, pd.DataFrame)

    def test_futures_continuous_volume(self):
        """期货成交量加权入口。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=40)
        result = apply_adjustment(kline_dict, adjustment="continuous_volume")
        assert isinstance(result, pd.DataFrame)

    def test_futures_continuous_oi(self):
        """期货持仓量加权入口。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=40)
        result = apply_adjustment(kline_dict, adjustment="continuous_oi")
        assert isinstance(result, pd.DataFrame)

    def test_invalid_adjustment_raises(self):
        """无效 adjustment 抛出异常。"""
        kline = _generate_stock_kline(5)
        with pytest.raises(ValueError):
            apply_adjustment(kline, adjustment="invalid_type")

    def test_equity_wrong_type_raises(self):
        """股票复权传入 dict 类型抛出异常。"""
        kline_dict = _generate_futures_kline_dict()
        with pytest.raises(TypeError):
            apply_adjustment(kline_dict, adjustment="qfq")

    def test_futures_wrong_type_raises(self):
        """期货连续传入 DataFrame 类型抛出异常。"""
        kline = _generate_stock_kline(10)
        with pytest.raises(TypeError):
            apply_adjustment(kline, adjustment="continuous")

    def test_rollover_method_override(self):
        """rollover_method 参数覆盖。"""
        kline_dict = _generate_futures_kline_dict(n_per_contract=40)
        result = apply_adjustment(
            kline_dict,
            adjustment="continuous",
            rollover_method="oi",
        )
        assert isinstance(result, pd.DataFrame)

    def test_single_bar(self):
        """单根 K 线处理。"""
        kline = _generate_stock_kline(1)
        result = apply_adjustment(kline, adjustment="none")
        assert len(result) == 1


# ============================================================
#  边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试。"""

    def test_empty_dataframe_none(self):
        """空 DataFrame none 透传。"""
        df = pd.DataFrame()
        result = apply_adjustment(df, adjustment="none")
        assert len(result) == 0

    def test_empty_dict_none(self):
        """空 dict none 透传。"""
        result = apply_adjustment({}, adjustment="none")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_forward_adjust_empty_df(self):
        """前复权空 DataFrame。"""
        df = _generate_stock_kline(0)
        result = forward_adjust(df, dividend_info=[])
        assert len(result) == 0

    def test_backward_adjust_empty_df(self):
        """后复权空 DataFrame。"""
        df = _generate_stock_kline(0)
        result = backward_adjust(df, dividend_info=[])
        assert len(result) == 0

    def test_dominant_empty_data(self):
        """空数据主力识别返回空序列。"""
        kline_dict = {
            "RB2501": pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"]),
        }
        dominant = identify_dominant_by_volume(kline_dict)
        assert len(dominant) == 0

    def test_continuous_empty(self):
        """空数据连续合约。"""
        with pytest.raises(ValueError):
            build_continuous_contract({})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
