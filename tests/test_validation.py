"""Tests for datacore.validation — 数据校验模块测试。"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np

from datacore.validation.weight_score import (
    SourceWeight,
    DEFAULT_SOURCE_WEIGHTS,
    calculate_source_score,
    get_source_weight,
)
from datacore.validation.cross_source import (
    cross_validate_sources,
    calculate_deviation_rate,
    consistency_report,
)
from datacore.validation.missing_detect import (
    detect_missing_values,
    find_continuous_missing,
    calculate_completeness,
)
from datacore.validation.cal_math import (
    calc_yoy,
    calc_mom,
    calc_basis_rate,
    calc_inventory_consumption_ratio,
    calc_processing_profit,
    calc_seasonal_index,
)


# ============================================================
#  weight_score 测试
# ============================================================

class TestWeightScore:
    """数据源权重测试。"""

    def test_source_weight_default(self):
        """SourceWeight 默认值。"""
        sw = SourceWeight(name="test")
        assert sw.name == "test"
        assert sw.weight == 0.5

    def test_source_weight_clamp(self):
        """权重限制在 0-1 之间。"""
        sw = SourceWeight(name="test", weight=2.0)
        assert sw.weight == 1.0
        sw2 = SourceWeight(name="test", weight=-0.5)
        assert sw2.weight == 0.0

    def test_get_source_weight_exchange(self):
        """获取交易所权重。"""
        weight = get_source_weight("exchange")
        assert weight == 0.98

    def test_get_source_weight_unknown(self):
        """未知数据源返回默认权重。"""
        weight = get_source_weight("unknown_source")
        assert weight == 0.5

    def test_default_weights_not_empty(self):
        """默认权重表不为空。"""
        assert len(DEFAULT_SOURCE_WEIGHTS) > 0
        assert "exchange" in DEFAULT_SOURCE_WEIGHTS

    def test_calculate_source_score(self):
        """计算数据源得分。"""
        data = {
            "src_a": {"completeness": 0.95, "freshness": 0.9},
            "src_b": {"completeness": 0.8, "freshness": 0.95},
        }
        scores = calculate_source_score(data)
        assert len(scores) == 2
        assert 0 <= scores["src_a"] <= 1
        assert 0 <= scores["src_b"] <= 1

    def test_calculate_source_score_custom_weights(self):
        """自定义权重计算得分。"""
        data = {"src_a": {"completeness": 1.0}}
        scores = calculate_source_score(data, custom_weights={"src_a": 0.9})
        assert scores["src_a"] >= 0.5

    def test_calculate_source_score_known_source(self):
        """已知数据源计算得分（走 DEFAULT_SOURCE_WEIGHTS 分支）。"""
        data = {"exchange": {"completeness": 1.0, "freshness": 1.0, "accuracy": 1.0}}
        scores = calculate_source_score(data)
        assert scores["exchange"] > 0.9

    def test_calculate_source_score_empty(self):
        """空输入计算得分。"""
        scores = calculate_source_score({})
        assert scores == {}


# ============================================================
#  cross_source 测试
# ============================================================

class TestCrossSource:
    """多源交叉验证测试。"""

    def test_calculate_deviation_rate(self):
        """计算偏差率。"""
        base = [100, 200, 300]
        compare = [101, 198, 305]
        result = calculate_deviation_rate(base, compare)
        assert "avg_deviation" in result
        assert "max_deviation" in result
        assert "consistent_rate" in result
        assert result["valid_points"] == 3

    def test_calculate_deviation_rate_zero_base(self):
        """基准值为 0 的情况。"""
        base = [0, 0, 0]
        compare = [1, 2, 3]
        result = calculate_deviation_rate(base, compare)
        assert result["valid_points"] == 0

    def test_cross_validate_sources_basic(self):
        """多源交叉验证基础测试。"""
        s1 = pd.DataFrame({"date": [1, 2, 3], "price": [100, 200, 300]})
        s2 = pd.DataFrame({"date": [1, 2, 3], "price": [101, 198, 305]})
        result = cross_validate_sources(
            {"s1": s1, "s2": s2},
            field="price",
            key_field="date",
        )
        assert result["success"] is True
        assert "comparisons" in result
        assert "s2" in result["comparisons"]

    def test_cross_validate_sources_insufficient(self):
        """数据源不足的情况。"""
        s1 = pd.DataFrame({"date": [1], "price": [100]})
        result = cross_validate_sources({"s1": s1}, field="price")
        assert result["success"] is False

    def test_consistency_report(self):
        """一致性报告。"""
        s1 = pd.DataFrame({
            "date": [1, 2],
            "price": [100, 200],
            "vol": [10, 20],
        })
        s2 = pd.DataFrame({
            "date": [1, 2],
            "price": [101, 198],
            "vol": [11, 19],
        })
        report = consistency_report(
            {"s1": s1, "s2": s2},
            ["price", "vol"],
            "date",
        )
        assert isinstance(report, pd.DataFrame)
        assert len(report) == 2

    def test_cross_validate_sources_base_source(self):
        """指定基准源。"""
        s1 = pd.DataFrame({"date": [1, 2, 3], "price": [100, 200, 300]})
        s2 = pd.DataFrame({"date": [1, 2, 3], "price": [101, 198, 305]})
        result = cross_validate_sources(
            {"s1": s1, "s2": s2},
            field="price",
            key_field="date",
            base_source="s2",
        )
        assert result["success"] is True
        assert result["base_source"] == "s2"

    def test_cross_validate_sources_invalid_base_source(self):
        """基准源不存在。"""
        s1 = pd.DataFrame({"date": [1], "price": [100]})
        result = cross_validate_sources(
            {"s1": s1, "s2": s1},
            field="price",
            base_source="nonexistent",
        )
        assert result["success"] is False
        assert "基准源" in result["error"]

    def test_cross_validate_sources_base_missing_field(self):
        """基准源缺少字段。"""
        s1 = pd.DataFrame({"date": [1, 2], "vol": [10, 20]})
        s2 = pd.DataFrame({"date": [1, 2], "price": [100, 200]})
        result = cross_validate_sources(
            {"s1": s1, "s2": s2},
            field="price",
            key_field="date",
        )
        assert result["success"] is False
        assert "缺少字段" in result["error"]

    def test_cross_validate_sources_source_missing_field(self):
        """对比源缺少字段。"""
        s1 = pd.DataFrame({"date": [1, 2], "price": [100, 200]})
        s2 = pd.DataFrame({"date": [1, 2], "vol": [10, 20]})
        result = cross_validate_sources(
            {"s1": s1, "s2": s2},
            field="price",
            key_field="date",
        )
        assert result["success"] is True
        assert "s2" in result["comparisons"]
        assert "缺少字段" in result["comparisons"]["s2"]["error"]

    def test_cross_validate_sources_empty_merge(self):
        """无交集数据。"""
        s1 = pd.DataFrame({"date": [1, 2], "price": [100, 200]})
        s2 = pd.DataFrame({"date": [3, 4], "price": [300, 400]})
        result = cross_validate_sources(
            {"s1": s1, "s2": s2},
            field="price",
            key_field="date",
        )
        assert result["success"] is True
        assert result["comparisons"]["s2"]["valid_points"] == 0

    def test_consistency_report_with_error(self):
        """一致性报告包含错误字段。"""
        s1 = pd.DataFrame({"date": [1], "price": [100]})
        s2 = pd.DataFrame({"date": [1], "vol": [10]})
        report = consistency_report(
            {"s1": s1, "s2": s2},
            ["nonexistent_field"],
            "date",
        )
        assert isinstance(report, pd.DataFrame)
        assert "error" in report.columns

    def test_calculate_deviation_rate_with_nan(self):
        """偏差率计算含 NaN 值。"""
        base = [100, None, 300]
        compare = [101, 200, float('nan')]
        result = calculate_deviation_rate(base, compare)
        assert result["valid_points"] == 1

    def test_consistency_report_single_source_error(self):
        """单源一致性报告返回错误。"""
        s1 = pd.DataFrame({"date": [1, 2], "price": [100, 200]})
        report = consistency_report({"s1": s1}, ["price"], "date")
        assert isinstance(report, pd.DataFrame)
        assert "error" in report.columns
        assert report["error"].iloc[0] is not None


# ============================================================
#  missing_detect 测试
# ============================================================

class TestMissingDetect:
    """缺失检测测试。"""

    def test_detect_missing_values_basic(self):
        """基础缺失检测。"""
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})
        result = detect_missing_values(df)
        assert result["total_rows"] == 3
        assert result["missing_cells"] == 2
        assert 0 < result["completeness"] < 1

    def test_detect_missing_values_empty(self):
        """空 DataFrame 检测。"""
        df = pd.DataFrame()
        result = detect_missing_values(df)
        assert result["completeness"] == 1.0

    def test_detect_missing_values_columns(self):
        """指定列检测。"""
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})
        result = detect_missing_values(df, columns=["a"])
        assert result["total_fields"] == 1
        assert result["field_missing"]["a"]["missing_count"] == 1

    def test_find_continuous_missing(self):
        """查找连续缺失。"""
        data = [1, None, None, None, 5, 6, None, None]
        gaps = find_continuous_missing(data, min_length=3)
        assert len(gaps) == 1
        assert gaps[0]["length"] == 3
        assert gaps[0]["start"] == 1

    def test_find_continuous_missing_no_gaps(self):
        """无连续缺失。"""
        data = [1, 2, 3, 4, 5]
        gaps = find_continuous_missing(data, min_length=3)
        assert len(gaps) == 0

    def test_find_continuous_missing_at_end(self):
        """尾部连续缺失。"""
        data = [1, 2, None, None, None]
        gaps = find_continuous_missing(data, min_length=3)
        assert len(gaps) == 1
        assert gaps[0]["end"] == 4

    def test_calculate_completeness(self):
        """计算完整度。"""
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01", periods=5, freq="B"),
            "value": [1, 2, None, 4, 5],
        })
        result = calculate_completeness(df)
        assert "date_completeness" in result
        assert "value_completeness" in result
        assert "overall_completeness" in result

    def test_find_continuous_missing_series(self):
        """查找连续缺失 - 传入 pd.Series。"""
        series = pd.Series([1, None, None, None, 5, 6, None, None])
        gaps = find_continuous_missing(series, min_length=3)
        assert len(gaps) == 1
        assert gaps[0]["length"] == 3

    def test_calculate_completeness_empty(self):
        """计算完整度 - 空 DataFrame。"""
        df = pd.DataFrame()
        result = calculate_completeness(df)
        assert result["overall_completeness"] == 0.0
        assert result["expected_count"] == 0

    def test_detect_missing_values_invalid_columns(self):
        """缺失检测 - 指定不存在的列。"""
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = detect_missing_values(df, columns=["nonexistent", "a"])
        assert result["total_fields"] == 1
        assert "a" in result["field_missing"]


# ============================================================
#  cal_math 测试
# ============================================================

class TestCalMath:
    """衍生因子计算测试。"""

    def test_calc_yoy(self):
        """计算同比。"""
        df = pd.DataFrame({
            "datetime": pd.date_range("2023-01-01", periods=13, freq="MS"),
            "value": range(100, 113),
        })
        yoy = calc_yoy(df, "value")
        assert len(yoy) == 13
        assert pd.isna(yoy.iloc[0])
        assert not pd.isna(yoy.iloc[-1])

    def test_calc_mom(self):
        """计算环比。"""
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
            "value": [100, 105, 103, 110, 108],
        })
        mom = calc_mom(df, "value")
        assert len(mom) == 5
        assert pd.isna(mom.iloc[0])

    def test_calc_basis_rate(self):
        """计算基差率。"""
        spot = [100, 105, 103]
        futures = [102, 104, 101]
        basis = calc_basis_rate(spot, futures)
        assert len(basis) == 3
        assert basis.iloc[0] == (100 - 102) / 100

    def test_calc_inventory_consumption_ratio(self):
        """计算库存消费比。"""
        inv = [1000, 1200, 1100]
        cons = [500, 600, 550]
        ratio = calc_inventory_consumption_ratio(inv, cons)
        assert len(ratio) == 3
        assert ratio.iloc[0] == 2.0

    def test_calc_processing_profit(self):
        """计算加工利润。"""
        prod = [3000, 3100, 3200]
        raw = [2000, 2100, 2200]
        profit = calc_processing_profit(prod, raw, processing_fee=100)
        assert len(profit) == 3
        assert profit.iloc[0] == 900.0

    def test_calc_processing_profit_with_ratio(self):
        """带转化率的加工利润。"""
        prod = [1000]
        raw = [800]
        profit = calc_processing_profit(prod, raw, conversion_ratio=1.2)
        assert profit.iloc[0] == 1000 - 800 * 1.2

    def test_calc_seasonal_index(self):
        """计算季节性指数。"""
        dates = pd.date_range("2020-01-01", periods=24, freq="MS")
        df = pd.DataFrame({
            "datetime": dates,
            "value": [10, 12, 15, 18, 20, 18, 16, 14, 12, 10, 8, 6] * 2,
        })
        idx = calc_seasonal_index(df, "value")
        assert len(idx) == 12
        assert "seasonal_index" in idx.columns

    def test_calc_yoy_missing_column(self):
        """calc_yoy 缺少 value_col 时返回空 Series。"""
        df = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=5, freq="D")})
        result = calc_yoy(df, "nonexistent")
        assert len(result) == 0

    def test_calc_mom_missing_column(self):
        """calc_mom 缺少 value_col 时返回空 Series。"""
        df = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=5, freq="D")})
        result = calc_mom(df, "nonexistent")
        assert len(result) == 0

    def test_calc_seasonal_index_missing_column(self):
        """calc_seasonal_index 缺少 value_col 时返回空 DataFrame。"""
        df = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=5, freq="MS")})
        result = calc_seasonal_index(df, "nonexistent")
        assert len(result) == 0

    def test_calc_seasonal_index_week(self):
        """calc_seasonal_index 按周计算。"""
        dates = pd.date_range("2020-01-05", periods=104, freq="W")
        df = pd.DataFrame({
            "datetime": dates,
            "value": list(range(52)) + list(range(52)),
        })
        idx = calc_seasonal_index(df, "value", period="week")
        assert len(idx) >= 52
        assert "seasonal_index" in idx.columns

    def test_calc_seasonal_index_quarter(self):
        """calc_seasonal_index 按季度计算。"""
        dates = pd.date_range("2020-01-01", periods=8, freq="QS")
        df = pd.DataFrame({
            "datetime": dates,
            "value": [10, 20, 30, 40, 10, 20, 30, 40],
        })
        idx = calc_seasonal_index(df, "value", period="quarter")
        assert len(idx) == 4
        assert "seasonal_index" in idx.columns

    def test_calc_seasonal_index_unknown_period(self):
        """calc_seasonal_index 未知周期类型默认用 month。"""
        dates = pd.date_range("2020-01-01", periods=24, freq="MS")
        df = pd.DataFrame({
            "datetime": dates,
            "value": [10, 12, 15, 18, 20, 18, 16, 14, 12, 10, 8, 6] * 2,
        })
        idx = calc_seasonal_index(df, "value", period="unknown")
        assert len(idx) == 12

    def test_calc_inventory_consumption_ratio_zero_consumption(self):
        """库存消费比 - 消费量为 0 时返回 NaN。"""
        inv = [1000, 2000]
        cons = [0, 500]
        ratio = calc_inventory_consumption_ratio(inv, cons)
        assert pd.isna(ratio.iloc[0])
        assert ratio.iloc[1] == 4.0
