"""Tests for datacore.cleaning — 数据清洗模块测试。"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np

from datacore.cleaning.unit_unify import (
    convert_unit,
    batch_convert_units,
    auto_detect_unit,
    UNIT_FACTORS,
)
from datacore.cleaning.date_align import (
    align_to_trading_calendar,
    fill_missing_dates,
    infer_frequency,
)
from datacore.cleaning.duplicate_merge import (
    merge_by_weight,
    deduplicate_dataframe,
    merge_sources,
)
from datacore.cleaning.outlier_filter import (
    filter_outliers_3sigma,
    filter_outliers_iqr,
    detect_outliers,
    mark_outliers,
)


# ============================================================
#  unit_unify 测试
# ============================================================

class TestUnitUnify:
    """单位标准化测试。"""

    def test_convert_unit_wan_to_ton(self):
        """万吨转吨。"""
        result = convert_unit(1, "万吨", "吨")
        assert result == 10000.0

    def test_convert_unit_yuan_to_wanyuan(self):
        """元转万元。"""
        result = convert_unit(10000, "元", "万元")
        assert result == 1.0

    def test_convert_unit_percent_to_decimal(self):
        """百分比转小数。"""
        result = convert_unit(50, "%", "percent")
        assert result == 50.0

    def test_convert_unit_same_unit(self):
        """相同单位转换，值不变。"""
        result = convert_unit(100, "吨", "吨")
        assert result == 100.0

    def test_auto_detect_unit_wan(self):
        """自动检测单位 - 万吨。"""
        result = auto_detect_unit("产量(万吨)")
        assert result == "万吨"

    def test_auto_detect_unit_yuan(self):
        """自动检测单位 - 元。"""
        result = auto_detect_unit("金额(元)")
        assert result == "元"

    def test_auto_detect_unit_not_found(self):
        """自动检测单位 - 未找到。"""
        result = auto_detect_unit("some_text")
        assert result is None

    def test_batch_convert_units(self):
        """批量转换单位。"""
        df = pd.DataFrame({"产量": [1, 2], "金额": [10000, 20000]})
        result = batch_convert_units(df, {
            "产量": ("万吨", "吨"),
            "金额": ("元", "万元"),
        })
        assert result["产量"].tolist() == [10000.0, 20000.0]
        assert result["金额"].tolist() == [1.0, 2.0]

    def test_unit_factors_not_empty(self):
        """单位因子表不为空。"""
        assert len(UNIT_FACTORS) > 0
        assert "吨" in UNIT_FACTORS
        assert "元" in UNIT_FACTORS


# ============================================================
#  date_align 测试
# ============================================================

class TestDateAlign:
    """时间对齐测试。"""

    def test_infer_frequency_business_days(self):
        """推断工作日频率。"""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        result = infer_frequency(dates)
        assert result == "B"

    def test_infer_frequency_daily(self):
        """推断自然日频率。"""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        result = infer_frequency(dates)
        assert result == "D"

    def test_infer_frequency_short(self):
        """短序列频率推断（<2个）。"""
        result = infer_frequency(["2024-01-01"])
        assert result == "D"

    def test_fill_missing_dates_ffill(self):
        """填充缺失日期 - 前向填充。"""
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "value": [10, 30],
        })
        result = fill_missing_dates(df, freq="D", method="ffill")
        assert len(result) == 3
        assert result["value"].iloc[1] == 10

    def test_fill_missing_dates_zero(self):
        """填充缺失日期 - 填零。"""
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "value": [10, 30],
        })
        result = fill_missing_dates(df, freq="D", method="zero")
        assert result["value"].iloc[1] == 0

    def test_fill_missing_dates_custom_range(self):
        """填充缺失日期 - 自定义范围。"""
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-02"]),
            "value": [10],
        })
        result = fill_missing_dates(
            df,
            freq="D",
            method="ffill",
            start_date="2024-01-01",
            end_date="2024-01-03",
        )
        assert len(result) == 3

    def test_align_to_trading_calendar_outer(self):
        """多序列对齐 - outer 方式。"""
        s1 = pd.DataFrame({
            "datetime": ["2024-01-01", "2024-01-02"],
            "price": [100, 101],
        })
        s2 = pd.DataFrame({
            "datetime": ["2024-01-02", "2024-01-03"],
            "price": [200, 201],
        })
        result = align_to_trading_calendar({"a": s1, "b": s2}, freq="D")
        assert "a" in result
        assert "b" in result
        assert len(result["a"]) == 3
        assert len(result["b"]) == 3

    def test_align_to_trading_calendar_inner(self):
        """多序列对齐 - inner 方式。"""
        s1 = pd.DataFrame({
            "datetime": ["2024-01-01", "2024-01-02"],
            "price": [100, 101],
        })
        s2 = pd.DataFrame({
            "datetime": ["2024-01-02", "2024-01-03"],
            "price": [200, 201],
        })
        result = align_to_trading_calendar(
            {"a": s1, "b": s2}, freq="D", how="inner"
        )
        assert len(result["a"]) == 1

    def test_fill_missing_dates_nan_method(self):
        """填充缺失日期 - nan 方法（保留 NaN）。"""
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "value": [10, 30],
        })
        result = fill_missing_dates(df, freq="D", method="nan")
        assert len(result) == 3
        assert pd.isna(result["value"].iloc[1])

    def test_fill_missing_dates_bfill(self):
        """填充缺失日期 - 后向填充。"""
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "value": [10, 30],
        })
        result = fill_missing_dates(df, freq="D", method="bfill")
        assert result["value"].iloc[1] == 30

    def test_fill_missing_dates_interpolate(self):
        """填充缺失日期 - 线性插值。"""
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "value": [10, 30],
        })
        result = fill_missing_dates(df, freq="D", method="interpolate")
        assert result["value"].iloc[1] == 20

    def test_infer_frequency_invalid(self):
        """推断频率 - 无效日期序列返回 D。"""
        result = infer_frequency(["2024-01-01", "2024-01-05", "2024-01-03"])
        assert result == "D"

    def test_align_to_trading_calendar_left(self):
        """多序列对齐 - left 方式。"""
        s1 = pd.DataFrame({
            "datetime": ["2024-01-01", "2024-01-02"],
            "price": [100, 101],
        })
        s2 = pd.DataFrame({
            "datetime": ["2024-01-02", "2024-01-03"],
            "price": [200, 201],
        })
        result = align_to_trading_calendar(
            {"a": s1, "b": s2}, freq="D", how="left"
        )
        assert len(result["a"]) == 2

    def test_align_to_trading_calendar_unknown_how(self):
        """多序列对齐 - 未知 how 默认 outer。"""
        s1 = pd.DataFrame({
            "datetime": ["2024-01-01", "2024-01-02"],
            "price": [100, 101],
        })
        s2 = pd.DataFrame({
            "datetime": ["2024-01-02", "2024-01-03"],
            "price": [200, 201],
        })
        result = align_to_trading_calendar(
            {"a": s1, "b": s2}, freq="D", how="unknown"
        )
        assert len(result["a"]) == 3

    def test_align_to_trading_calendar_zero_method(self):
        """多序列对齐 - zero 填充方法。"""
        s1 = pd.DataFrame({
            "datetime": ["2024-01-01"],
            "price": [100],
        })
        s2 = pd.DataFrame({
            "datetime": ["2024-01-03"],
            "price": [200],
        })
        result = align_to_trading_calendar(
            {"a": s1, "b": s2}, freq="D", method="zero"
        )
        assert result["a"]["price"].iloc[1] == 0


# ============================================================
#  duplicate_merge 测试
# ============================================================

class TestDuplicateMerge:
    """多源去重测试。"""

    def test_deduplicate_first(self):
        """去重 - first 策略。"""
        df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 20, 30]})
        result = deduplicate_dataframe(df, ["id"], "first")
        assert len(result) == 2
        assert result["value"].iloc[0] == 10

    def test_deduplicate_last(self):
        """去重 - last 策略。"""
        df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 20, 30]})
        result = deduplicate_dataframe(df, ["id"], "last")
        assert result["value"].iloc[0] == 20

    def test_deduplicate_mean(self):
        """去重 - mean 策略。"""
        df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 30, 30]})
        result = deduplicate_dataframe(df, ["id"], "mean")
        assert result["value"].iloc[0] == 20

    def test_deduplicate_empty(self):
        """去重 - 空 DataFrame。"""
        df = pd.DataFrame()
        result = deduplicate_dataframe(df, ["id"])
        assert result.empty

    def test_merge_by_weight(self):
        """按权重合并。"""
        src1 = pd.DataFrame({"date": ["2024-01-01"], "price": [100]})
        src2 = pd.DataFrame({"date": ["2024-01-01"], "price": [110]})
        result = merge_by_weight(
            {"s1": src1, "s2": src2},
            {"s1": 0.4, "s2": 0.6},
            ["date"],
            ["price"],
        )
        assert round(result["price"].iloc[0], 1) == 106.0

    def test_merge_sources_priority(self):
        """按优先级合并。"""
        src1 = pd.DataFrame({"date": ["2024-01-01"], "val": [100]})
        src2 = pd.DataFrame({"date": ["2024-01-01"], "val": [200]})
        result = merge_sources(
            {"high": src1, "low": src2},
            ["date"],
            ["high", "low"],
        )
        assert result["val"].iloc[0] == 100

    def test_merge_sources_empty(self):
        """合并 - 空输入。"""
        result = merge_sources({}, ["id"])
        assert result.empty

    def test_deduplicate_max(self):
        """去重 - max 策略。"""
        df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 30, 30]})
        result = deduplicate_dataframe(df, ["id"], "max")
        assert result["value"].iloc[0] == 30

    def test_deduplicate_min(self):
        """去重 - min 策略。"""
        df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 30, 30]})
        result = deduplicate_dataframe(df, ["id"], "min")
        assert result["value"].iloc[0] == 10

    def test_deduplicate_unknown_strategy(self):
        """去重 - 未知策略默认 first。"""
        df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 30, 30]})
        result = deduplicate_dataframe(df, ["id"], "unknown")
        assert result["value"].iloc[0] == 10

    def test_merge_by_weight_empty(self):
        """按权重合并 - 空输入。"""
        result = merge_by_weight({}, {}, ["id"])
        assert result.empty

    def test_merge_by_weight_no_available_sources(self):
        """按权重合并 - 无可用源。"""
        result = merge_by_weight({}, {"s1": 0.5}, ["id"])
        assert result.empty

    def test_merge_sources_default_priority(self):
        """按优先级合并 - 默认优先级。"""
        src1 = pd.DataFrame({"date": ["2024-01-01"], "val": [100]})
        src2 = pd.DataFrame({"date": ["2024-01-01"], "val": [200]})
        result = merge_sources({"s1": src1, "s2": src2}, ["date"])
        assert result["val"].iloc[0] == 100

    def test_merge_sources_missing_priority_source(self):
        """按优先级合并 - 优先级列表中有的源不存在。"""
        src1 = pd.DataFrame({"date": ["2024-01-01"], "val": [100]})
        result = merge_sources({"s1": src1}, ["date"], ["nonexistent", "s1"])
        assert result["val"].iloc[0] == 100


# ============================================================
#  outlier_filter 测试
# ============================================================

class TestOutlierFilter:
    """异常过滤测试。"""

    def test_detect_outliers_iqr(self):
        """IQR 法检测异常值。"""
        data = [1, 2, 3, 4, 5, 100]
        mask = detect_outliers(data, method="iqr")
        assert mask[-1] == True
        assert mask[0] == False

    def test_detect_outliers_3sigma(self):
        """3σ 法检测异常值。"""
        np.random.seed(42)
        data = list(np.random.normal(0, 1, 1000)) + [10.0]
        mask = detect_outliers(data, method="3sigma")
        assert mask[-1] == True

    def test_detect_outliers_constant(self):
        """常量数据检测（无异常）。"""
        data = [5, 5, 5, 5, 5]
        mask = detect_outliers(data, method="3sigma")
        assert not any(mask)

    def test_filter_outliers_remove(self):
        """移除异常值。"""
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
        result = filter_outliers_iqr(df, "val", action="remove")
        assert len(result) == 5

    def test_filter_outliers_mark(self):
        """标记异常值。"""
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
        result = filter_outliers_3sigma(df, "val", action="mark")
        assert "val_is_outlier" in result.columns

    def test_filter_outliers_replace_median(self):
        """替换异常值为中位数。"""
        df = pd.DataFrame({"val": [1, 2, 3, 4, 100]})
        result = filter_outliers_iqr(df, "val", action="replace", replace_value="median")
        assert result["val"].iloc[-1] != 100

    def test_mark_outliers_multi_columns(self):
        """标记多列异常值。"""
        df = pd.DataFrame({"a": [1, 2, 100], "b": [3, 4, 5]})
        result = mark_outliers(df, ["a", "b"], method="iqr")
        assert "a_is_outlier" in result.columns
        assert "b_is_outlier" in result.columns

    def test_detect_outliers_all_nan(self):
        """检测异常值 - 全 NaN 数据。"""
        data = [None, None, None]
        mask = detect_outliers(data, method="iqr")
        assert not any(mask)

    def test_detect_outliers_unknown_method(self):
        """检测异常值 - 未知方法返回全 False。"""
        data = [1, 2, 3, 100]
        mask = detect_outliers(data, method="unknown")
        assert not any(mask)

    def test_detect_outliers_with_nan(self):
        """检测异常值 - 含 NaN 数据。"""
        data = [1, 2, None, 4, 100]
        mask = detect_outliers(data, method="iqr")
        assert mask[-1] == True
        assert mask[2] == False

    def test_filter_outliers_3sigma_replace_mean(self):
        """3σ 法替换异常值为均值。"""
        np.random.seed(42)
        data = list(np.random.normal(0, 1, 1000)) + [10.0]
        df = pd.DataFrame({"val": data})
        result = filter_outliers_3sigma(df, "val", action="replace", replace_value="mean")
        assert result["val"].iloc[-1] != 10.0

    def test_filter_outliers_3sigma_replace_custom(self):
        """3σ 法替换异常值为自定义值。"""
        np.random.seed(42)
        data = list(np.random.normal(0, 1, 1000)) + [10.0]
        df = pd.DataFrame({"val": data})
        result = filter_outliers_3sigma(df, "val", action="replace", replace_value=0)
        assert result["val"].iloc[-1] == 0

    def test_filter_outliers_3sigma_unknown_action(self):
        """3σ 法未知动作默认 remove。"""
        np.random.seed(42)
        data = list(np.random.normal(0, 1, 1000)) + [10.0]
        df = pd.DataFrame({"val": data})
        result = filter_outliers_3sigma(df, "val", action="unknown")
        assert len(result) < len(df)

    def test_filter_outliers_iqr_replace_mean(self):
        """IQR 法替换异常值为均值。"""
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
        result = filter_outliers_iqr(df, "val", action="replace", replace_value="mean")
        assert result["val"].iloc[-1] != 100

    def test_filter_outliers_iqr_replace_custom(self):
        """IQR 法替换异常值为自定义值。"""
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
        result = filter_outliers_iqr(df, "val", action="replace", replace_value=-1)
        assert result["val"].iloc[-1] == -1

    def test_filter_outliers_iqr_unknown_action(self):
        """IQR 法未知动作默认 remove。"""
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
        result = filter_outliers_iqr(df, "val", action="unknown")
        assert len(result) < len(df)
