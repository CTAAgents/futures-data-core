"""技术指标模块测试。

覆盖:
- core.py: 40+ 基础指标的 numpy 实现
- tdx_compat.py: TDX 对齐指标
- legacy_numpy.py: 旧版兼容实现
- trend_maturity.py: 趋势成熟度评估
- talib_wrapper.py: TA-Lib 封装（可选）
- __init__.py: compute_indicators 统一入口
"""

from __future__ import annotations

import numpy as np
import pytest

from datacore.indicators import (
    compute_indicators,
    INDICATOR_NAMES,
    assess_trend_maturity,
    TrendMaturityResult,
)
from datacore.indicators.core import (
    ma, ema, sma, wma, dma,
    rsi, macd, mtm, roc, bias, trix,
    kdj, cci, wr, psy,
    boll, atr, mass,
    obv, vr,
    dmi, brar, cr, keltner, chandelier,
    median_price, typical_price, weighted_close, avg_price, trange,
    adx, stddev, variance,
    linear_regression, linear_reg_slope, tsf, ultimate_osc,
    INDICATOR_MAP,
)
from datacore.indicators.tdx_compat import (
    tdx_ma, tdx_kdj, tdx_macd, tdx_rsi, tdx_boll, tdx_atr,
    tdx_dmi, tdx_obv, tdx_wr, tdx_cci,
    TDX_INDICATOR_MAP,
)
from datacore.indicators.legacy_numpy import (
    old_ma, old_ema, old_rsi, old_macd, old_kdj, old_boll, old_atr,
)
from datacore.indicators.talib_wrapper import is_talib_available


# ============================================================
#  测试数据生成
# ============================================================

def _generate_test_data(n: int = 100, seed: int = 42) -> dict:
    """生成测试用 OHLCV 数据。"""
    np.random.seed(seed)
    base_price = 100.0
    returns = np.random.randn(n) * 0.02
    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.randn(n)) * 0.01)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.01)
    open_ = close * (1 + np.random.randn(n) * 0.005)
    volume = np.random.randint(1000, 10000, n).astype(float)
    return {
        "close": close,
        "high": high,
        "low": low,
        "open": open_,
        "volume": volume,
    }


def _generate_trend_data(n: int = 60, direction: str = "up") -> dict:
    """生成趋势性测试数据。"""
    base_price = 100.0
    if direction == "up":
        returns = 0.005 + np.random.randn(n) * 0.01
    elif direction == "down":
        returns = -0.005 + np.random.randn(n) * 0.01
    else:
        returns = np.random.randn(n) * 0.005

    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.randn(n)) * 0.008)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.008)
    open_ = close * (1 + np.random.randn(n) * 0.003)
    volume = np.random.randint(5000, 15000, n).astype(float)
    return {
        "close": close,
        "high": high,
        "low": low,
        "open": open_,
        "volume": volume,
    }


# ============================================================
#  基础移动平均线测试
# ============================================================

class TestMovingAverages:
    """移动平均线类指标测试。"""

    def test_ma_basic(self):
        """MA 基本计算测试。"""
        data = _generate_test_data()
        result = ma(data["close"], period=5)
        assert len(result) == len(data["close"])
        assert np.all(np.isnan(result[:4]))
        assert not np.isnan(result[4])

    def test_ma_known_values(self):
        """MA 已知值验证。"""
        close = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ma(close, period=3)
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert pytest.approx(result[2]) == 2.0
        assert pytest.approx(result[3]) == 3.0
        assert pytest.approx(result[4]) == 4.0

    def test_ma_period_zero(self):
        """MA 周期为 0 时返回全 NaN。"""
        close = np.array([1.0, 2.0, 3.0])
        result = ma(close, period=0)
        assert np.all(np.isnan(result))

    def test_ema_basic(self):
        """EMA 基本计算测试。"""
        data = _generate_test_data()
        result = ema(data["close"], period=12)
        assert len(result) == len(data["close"])
        assert np.all(np.isnan(result[:11]))
        assert not np.isnan(result[11])

    def test_ema_smooth(self):
        """EMA 应该比原始数据平滑。"""
        data = _generate_test_data(200)
        ema_val = ema(data["close"], period=20)
        half = len(data["close"]) // 2
        close_half = data["close"][half:]
        ema_half = ema_val[half:]
        valid = ~np.isnan(ema_half)
        assert np.std(ema_half[valid]) < np.std(close_half[valid])

    def test_sma_basic(self):
        """SMA（平滑移动平均）基本测试。"""
        data = _generate_test_data()
        result = sma(data["close"], period=12)
        assert len(result) == len(data["close"])

    def test_wma_basic(self):
        """WMA 加权移动平均测试。"""
        data = _generate_test_data()
        result = wma(data["close"], period=5)
        assert len(result) == len(data["close"])
        assert np.all(np.isnan(result[:4]))

    def test_dma_basic(self):
        """DMA 平均线差测试。"""
        data = _generate_test_data()
        result = dma(data["close"], fast_period=10, slow_period=50)
        assert len(result) == len(data["close"])


# ============================================================
#  动量指标测试
# ============================================================

class TestMomentumIndicators:
    """动量指标类测试。"""

    def test_rsi_basic(self):
        """RSI 基本计算测试。"""
        data = _generate_test_data()
        result = rsi(data["close"], period=14)
        assert len(result) == len(data["close"])
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)

    def test_rsi_trending_up(self):
        """上升趋势中 RSI 应偏高。"""
        data = _generate_trend_data(80, "up")
        result = rsi(data["close"], period=14)
        valid = result[~np.isnan(result)]
        assert np.mean(valid) > 50

    def test_rsi_trending_down(self):
        """下降趋势中 RSI 应偏低。"""
        data = _generate_trend_data(80, "down")
        result = rsi(data["close"], period=14)
        valid = result[~np.isnan(result)]
        assert np.mean(valid) < 50

    def test_macd_basic(self):
        """MACD 基本计算测试。"""
        data = _generate_test_data()
        result = macd(data["close"])
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert len(result["macd"]) == len(data["close"])

    def test_macd_components(self):
        """MACD 各分量关系正确。"""
        data = _generate_test_data()
        result = macd(data["close"])
        hist = result["histogram"]
        expected = result["macd"] - result["signal"]
        valid = ~np.isnan(hist)
        np.testing.assert_allclose(hist[valid], expected[valid])

    def test_mtm_basic(self):
        """MTM 动量指标测试。"""
        data = _generate_test_data()
        result = mtm(data["close"], period=10)
        assert len(result) == len(data["close"])

    def test_roc_basic(self):
        """ROC 变动率测试。"""
        data = _generate_test_data()
        result = roc(data["close"], period=10)
        assert len(result) == len(data["close"])

    def test_bias_basic(self):
        """BIAS 乖离率测试。"""
        data = _generate_test_data()
        result = bias(data["close"], period=6)
        assert len(result) == len(data["close"])

    def test_trix_basic(self):
        """TRIX 三重指数平滑测试。"""
        data = _generate_test_data()
        result = trix(data["close"], period=12)
        assert len(result) == len(data["close"])


# ============================================================
#  震荡指标测试
# ============================================================

class TestOscillatorIndicators:
    """震荡指标类测试。"""

    def test_kdj_basic(self):
        """KDJ 基本计算测试。"""
        data = _generate_test_data()
        result = kdj(data["high"], data["low"], data["close"])
        assert "k" in result
        assert "d" in result
        assert "j" in result
        assert len(result["k"]) == len(data["close"])

    def test_kdj_range(self):
        """KDJ 的 K/D 应在合理范围内。"""
        data = _generate_test_data()
        result = kdj(data["high"], data["low"], data["close"])
        valid_k = result["k"][~np.isnan(result["k"])]
        valid_d = result["d"][~np.isnan(result["d"])]
        assert np.all((valid_k >= 0) & (valid_k <= 100))
        assert np.all((valid_d >= 0) & (valid_d <= 100))

    def test_kdj_j_relation(self):
        """J = 3K - 2D 关系验证。"""
        data = _generate_test_data()
        result = kdj(data["high"], data["low"], data["close"])
        expected_j = 3 * result["k"] - 2 * result["d"]
        valid = ~np.isnan(result["j"])
        np.testing.assert_allclose(result["j"][valid], expected_j[valid])

    def test_cci_basic(self):
        """CCI 顺势指标测试。"""
        data = _generate_test_data()
        result = cci(data["high"], data["low"], data["close"], period=14)
        assert len(result) == len(data["close"])

    def test_wr_basic(self):
        """WR 威廉指标测试。"""
        data = _generate_test_data()
        result = wr(data["high"], data["low"], data["close"], period=14)
        assert len(result) == len(data["close"])
        valid = result[~np.isnan(result)]
        assert np.all(valid >= -100)
        assert np.all(valid <= 0)

    def test_psy_basic(self):
        """PSY 心理线测试。"""
        data = _generate_test_data()
        result = psy(data["close"], period=12)
        assert len(result) == len(data["close"])
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)


# ============================================================
#  波动率指标测试
# ============================================================

class TestVolatilityIndicators:
    """波动率指标类测试。"""

    def test_boll_basic(self):
        """BOLL 布林带基本测试。"""
        data = _generate_test_data()
        result = boll(data["close"], period=20)
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result
        assert len(result["upper"]) == len(data["close"])

    def test_boll_bands(self):
        """布林带上轨 > 中轨 > 下轨。"""
        data = _generate_test_data()
        result = boll(data["close"], period=20)
        valid = ~np.isnan(result["upper"])
        assert np.all(result["upper"][valid] >= result["middle"][valid])
        assert np.all(result["middle"][valid] >= result["lower"][valid])

    def test_atr_basic(self):
        """ATR 平均真实波幅测试。"""
        data = _generate_test_data()
        result = atr(data["high"], data["low"], data["close"], period=14)
        assert len(result) == len(data["close"])
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)

    def test_atr_always_positive(self):
        """ATR 应为非负值。"""
        data = _generate_test_data(200)
        result = atr(data["high"], data["low"], data["close"], period=14)
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)

    def test_mass_basic(self):
        """MASS 梅斯线测试。"""
        data = _generate_test_data()
        result = mass(data["high"], data["low"])
        assert len(result) == len(data["close"])


# ============================================================
#  成交量指标测试
# ============================================================

class TestVolumeIndicators:
    """成交量指标类测试。"""

    def test_obv_basic(self):
        """OBV 能量潮基本测试。"""
        data = _generate_test_data()
        result = obv(data["close"], data["volume"])
        assert len(result) == len(data["close"])

    def test_obv_trend(self):
        """上升趋势中 OBV 应上升。"""
        data = _generate_trend_data(80, "up")
        result = obv(data["close"], data["volume"])
        assert result[-1] > result[0]

    def test_vr_basic(self):
        """VR 成交量变异率测试。"""
        data = _generate_test_data()
        result = vr(data["close"], data["volume"], period=26)
        assert len(result) == len(data["close"])


# ============================================================
#  趋势指标测试
# ============================================================

class TestTrendIndicators:
    """趋势指标类测试。"""

    def test_dmi_basic(self):
        """DMI 趋向指标基本测试。"""
        data = _generate_test_data()
        result = dmi(data["high"], data["low"], data["close"], period=14)
        assert "plus_di" in result
        assert "minus_di" in result
        assert "adx" in result
        assert "dx" in result

    def test_dmi_adx_range(self):
        """ADX 应在 0-100 范围内。"""
        data = _generate_test_data(200)
        result = dmi(data["high"], data["low"], data["close"], period=14)
        valid = result["adx"][~np.isnan(result["adx"])]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)

    def test_brar_basic(self):
        """BRAR 情绪指标测试。"""
        data = _generate_test_data()
        result = brar(data["high"], data["low"], data["close"], data["open"])
        assert "br" in result
        assert "ar" in result

    def test_cr_basic(self):
        """CR 能量指标测试。"""
        data = _generate_test_data()
        result = cr(data["high"], data["low"], data["close"], period=26)
        assert len(result) == len(data["close"])

    def test_keltner_basic(self):
        """Keltner 通道测试。"""
        data = _generate_test_data()
        result = keltner(data["high"], data["low"], data["close"])
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result

    def test_chandelier_basic(self):
        """Chandelier 吊灯止损测试。"""
        data = _generate_test_data()
        result = chandelier(data["high"], data["low"], data["close"])
        assert "long_exit" in result
        assert "short_exit" in result


# ============================================================
#  价格类指标测试
# ============================================================

class TestPriceIndicators:
    """价格类指标测试。"""

    def test_median_price(self):
        """中位价测试。"""
        data = _generate_test_data()
        result = median_price(data["high"], data["low"])
        assert len(result) == len(data["close"])
        np.testing.assert_allclose(result, (data["high"] + data["low"]) / 2)

    def test_typical_price(self):
        """典型价格测试。"""
        data = _generate_test_data()
        result = typical_price(data["high"], data["low"], data["close"])
        assert len(result) == len(data["close"])
        np.testing.assert_allclose(result, (data["high"] + data["low"] + data["close"]) / 3)

    def test_weighted_close(self):
        """加权收盘价测试。"""
        data = _generate_test_data()
        result = weighted_close(data["high"], data["low"], data["close"])
        assert len(result) == len(data["close"])
        np.testing.assert_allclose(result, (data["high"] + data["low"] + 2 * data["close"]) / 4)

    def test_avg_price(self):
        """平均价测试。"""
        data = _generate_test_data()
        result = avg_price(data["open"], data["high"], data["low"], data["close"])
        assert len(result) == len(data["close"])

    def test_trange(self):
        """真实波幅测试。"""
        data = _generate_test_data()
        result = trange(data["high"], data["low"], data["close"])
        assert len(result) == len(data["close"])
        assert np.all(result >= 0)


# ============================================================
#  统计类指标测试
# ============================================================

class TestStatisticalIndicators:
    """统计类指标测试。"""

    def test_stddev_basic(self):
        """标准差测试。"""
        data = _generate_test_data()
        result = stddev(data["close"], period=20)
        assert len(result) == len(data["close"])
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)

    def test_variance_basic(self):
        """方差测试。"""
        data = _generate_test_data()
        result = variance(data["close"], period=20)
        assert len(result) == len(data["close"])
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)

    def test_stddev_vs_variance(self):
        """标准差是方差的平方根。"""
        data = _generate_test_data()
        std_result = stddev(data["close"], period=20)
        var_result = variance(data["close"], period=20)
        valid = ~np.isnan(std_result)
        np.testing.assert_allclose(std_result[valid], np.sqrt(var_result[valid]))

    def test_linear_regression_basic(self):
        """线性回归测试。"""
        data = _generate_test_data()
        result = linear_regression(data["close"], period=14)
        assert len(result) == len(data["close"])

    def test_linear_reg_slope_basic(self):
        """线性回归斜率测试。"""
        data = _generate_test_data()
        result = linear_reg_slope(data["close"], period=14)
        assert len(result) == len(data["close"])

    def test_tsf_basic(self):
        """时间序列预测测试。"""
        data = _generate_test_data()
        result = tsf(data["close"], period=14)
        assert len(result) == len(data["close"])

    def test_ultimate_osc_basic(self):
        """终极震荡指标测试。"""
        data = _generate_test_data()
        result = ultimate_osc(data["high"], data["low"], data["close"])
        assert len(result) == len(data["close"])
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)


# ============================================================
#  TDX 兼容测试
# ============================================================

class TestTdxCompat:
    """TDX 对齐指标测试。"""

    def test_tdx_ma_basic(self):
        """TDX MA 基本测试。"""
        data = _generate_test_data()
        result = tdx_ma(data["close"], period=5, ma_type=0)
        assert len(result) == len(data["close"])

    def test_tdx_ma_types(self):
        """TDX MA 支持多种类型。"""
        data = _generate_test_data()
        for ma_type in range(4):
            result = tdx_ma(data["close"], period=10, ma_type=ma_type)
            assert len(result) == len(data["close"])

    def test_tdx_kdj_basic(self):
        """TDX KDJ 基本测试。"""
        data = _generate_test_data()
        result = tdx_kdj(data["high"], data["low"], data["close"])
        assert "k" in result
        assert "d" in result
        assert "j" in result

    def test_tdx_macd_basic(self):
        """TDX MACD 基本测试。"""
        data = _generate_test_data()
        result = tdx_macd(data["close"])
        assert "dif" in result
        assert "dea" in result
        assert "macd" in result

    def test_tdx_rsi_basic(self):
        """TDX RSI 基本测试。"""
        data = _generate_test_data()
        result = tdx_rsi(data["close"], period=14)
        assert len(result) == len(data["close"])

    def test_tdx_atr_basic(self):
        """TDX ATR 基本测试。"""
        data = _generate_test_data()
        result = tdx_atr(data["high"], data["low"], data["close"], period=14)
        assert len(result) == len(data["close"])

    def test_tdx_indicator_map(self):
        """TDX 指标映射表非空。"""
        assert len(TDX_INDICATOR_MAP) > 0


# ============================================================
#  旧版兼容测试
# ============================================================

class TestLegacyNumpy:
    """旧版兼容实现测试。"""

    def test_old_ma_basic(self):
        """旧版 MA 基本测试。"""
        data = _generate_test_data()
        result = old_ma(data["close"], 5)
        assert len(result) == len(data["close"])

    def test_old_ema_basic(self):
        """旧版 EMA 基本测试。"""
        data = _generate_test_data()
        result = old_ema(data["close"], 12)
        assert len(result) == len(data["close"])

    def test_old_rsi_basic(self):
        """旧版 RSI 基本测试。"""
        data = _generate_test_data()
        result = old_rsi(data["close"], 14)
        assert len(result) == len(data["close"])

    def test_old_macd_returns_tuple(self):
        """旧版 MACD 返回元组。"""
        data = _generate_test_data()
        result = old_macd(data["close"])
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_old_kdj_returns_tuple(self):
        """旧版 KDJ 返回元组。"""
        data = _generate_test_data()
        result = old_kdj(data["high"], data["low"], data["close"])
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_old_boll_returns_tuple(self):
        """旧版 BOLL 返回元组。"""
        data = _generate_test_data()
        result = old_boll(data["close"])
        assert isinstance(result, tuple)
        assert len(result) == 3


# ============================================================
#  趋势成熟度测试
# ============================================================

class TestTrendMaturity:
    """趋势成熟度评估测试。"""

    def test_assess_trend_maturity_basic(self):
        """趋势成熟度基本评估测试。"""
        data = _generate_trend_data(80, "up")
        result = assess_trend_maturity(
            data["close"], data["high"], data["low"], data["volume"]
        )
        assert isinstance(result, TrendMaturityResult)
        assert result.stage in ["early", "mid", "late", "unknown"]
        assert 0 <= result.score <= 100
        assert 0 <= result.confidence <= 1

    def test_assess_trend_maturity_minimal(self):
        """最小化输入（只有 close）。"""
        data = _generate_test_data(60)
        result = assess_trend_maturity(data["close"])
        assert isinstance(result, TrendMaturityResult)

    def test_assess_trend_maturity_insufficient_data(self):
        """数据不足时返回 unknown。"""
        close = np.array([1.0, 2.0, 3.0])
        result = assess_trend_maturity(close)
        assert result.stage == "unknown"
        assert result.confidence == 0.0

    def test_trend_maturity_result_fields(self):
        """结果应包含所有必要字段。"""
        data = _generate_trend_data(80, "up")
        result = assess_trend_maturity(
            data["close"], data["high"], data["low"], data["volume"]
        )
        assert hasattr(result, "stage")
        assert hasattr(result, "score")
        assert hasattr(result, "confidence")
        assert hasattr(result, "trend_direction")
        assert hasattr(result, "strength_score")
        assert hasattr(result, "momentum_score")
        assert hasattr(result, "volatility_score")
        assert hasattr(result, "volume_score")
        assert hasattr(result, "features")

    def test_trend_detection_up(self):
        """上升趋势应被检测。"""
        data = _generate_trend_data(80, "up")
        result = assess_trend_maturity(
            data["close"], data["high"], data["low"], data["volume"]
        )
        assert result.trend_direction in ["up", "mid"]

    def test_trend_detection_down(self):
        """下降趋势应被检测。"""
        data = _generate_trend_data(80, "down")
        result = assess_trend_maturity(
            data["close"], data["high"], data["low"], data["volume"]
        )
        assert result.trend_direction in ["down", "mid"]


# ============================================================
#  统一入口测试
# ============================================================

class TestComputeIndicators:
    """compute_indicators 统一入口测试。"""

    def test_compute_single_indicator(self):
        """计算单个指标。"""
        data = _generate_test_data()
        result = compute_indicators(data, "MA", period=5)
        assert "MA" in result
        assert len(result["MA"]) == len(data["close"])

    def test_compute_multiple_indicators(self):
        """计算多个指标。"""
        data = _generate_test_data()
        result = compute_indicators(data, ["MA", "RSI", "MACD"])
        assert "MA" in result
        assert "RSI" in result
        assert "MACD" in result

    def test_compute_all_indicators(self):
        """计算所有指标。"""
        data = _generate_test_data(200)
        result = compute_indicators(data, "all")
        assert len(result) > 20

    def test_compute_with_params(self):
        """带参数计算。"""
        data = _generate_test_data()
        result = compute_indicators(data, "BOLL", period=20, nbdev=2.0)
        assert "BOLL" in result
        assert "upper" in result["BOLL"]

    def test_compute_invalid_indicator(self):
        """不支持的指标应抛出异常。"""
        data = _generate_test_data()
        with pytest.raises(ValueError):
            compute_indicators(data, "INVALID_INDICATOR")

    def test_compute_invalid_data_type(self):
        """无效数据类型应抛出异常。"""
        with pytest.raises(TypeError):
            compute_indicators("not_a_dict", "MA")

    def test_compute_missing_close(self):
        """缺少 close 应抛出异常。"""
        with pytest.raises(ValueError):
            compute_indicators({"high": np.array([1.0])}, "MA")

    def test_indicator_names_list(self):
        """INDICATOR_NAMES 非空且有序。"""
        assert len(INDICATOR_NAMES) > 30
        assert INDICATOR_NAMES == sorted(INDICATOR_NAMES)

    def test_indicator_map_consistency(self):
        """INDICATOR_NAMES 与 INDICATOR_MAP 一致。"""
        assert set(INDICATOR_NAMES) == set(INDICATOR_MAP.keys())

    def test_compute_with_tdx_flag(self):
        """use_tdx 参数测试。"""
        data = _generate_test_data()
        result = compute_indicators(data, ["MA", "RSI"], use_tdx=True)
        assert "MA" in result
        assert "RSI" in result

    def test_compute_case_insensitive(self):
        """指标名大小写不敏感。"""
        data = _generate_test_data()
        result_upper = compute_indicators(data, "ma")
        result_lower = compute_indicators(data, "MA")
        assert "MA" in result_upper
        assert "MA" in result_lower


# ============================================================
#  TA-Lib 封装测试（可选）
# ============================================================

class TestTalibWrapper:
    """TA-Lib 封装测试（可选）。"""

    def test_is_talib_available_returns_bool(self):
        """is_talib_available 返回布尔值。"""
        result = is_talib_available()
        assert isinstance(result, bool)

    def test_compute_fallback_none_when_unavailable(self):
        """TA-Lib 不可用时返回 None 不报错。"""
        from datacore.indicators.talib_wrapper import compute_with_talib
        data = _generate_test_data()
        result = compute_with_talib("INVALID", data)
        assert result is None


# ============================================================
#  边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试。"""

    def test_empty_array(self):
        """空数组输入。"""
        close = np.array([])
        result = ma(close, period=5)
        assert len(result) == 0

    def test_single_element(self):
        """单元素数组。"""
        close = np.array([100.0])
        result = ma(close, period=5)
        assert len(result) == 1
        assert np.isnan(result[0])

    def test_exact_period_length(self):
        """数据长度恰好等于周期。"""
        close = np.arange(10, dtype=float)
        result = ma(close, period=10)
        assert not np.isnan(result[-1])

    def test_constant_price(self):
        """价格恒定不变。"""
        close = np.full(50, 100.0)
        result = rsi(close, period=14)
        valid = result[~np.isnan(result)]
        assert len(valid) > 0

    def test_zero_price(self):
        """价格为 0 时不除以零。"""
        close = np.zeros(50)
        result = roc(close, period=10)
        assert len(result) == 50

    def test_nan_input_handling(self):
        """输入含 NaN 时的处理。"""
        close = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
        result = ma(close, period=3)
        assert len(result) == len(close)


# ============================================================
#  数据完整性测试
# ============================================================

class TestDataIntegrity:
    """数据完整性测试。"""

    def test_all_indicators_have_docstrings(self):
        """所有指标函数都应有 docstring。"""
        for name, func in INDICATOR_MAP.items():
            assert func.__doc__ is not None, f"{name} 缺少 docstring"

    def test_indicator_names_are_uppercase(self):
        """所有指标名都是大写。"""
        for name in INDICATOR_NAMES:
            assert name == name.upper()

    def test_output_length_matches_input(self):
        """输出长度应与输入一致。"""
        data = _generate_test_data()
        close = data["close"]
        indicators_to_test = ["MA", "EMA", "RSI", "CCI", "WR", "ATR", "MTM", "ROC", "BIAS"]

        for name in indicators_to_test:
            result = compute_indicators(data, name)
            assert name in result
            if isinstance(result[name], np.ndarray):
                assert len(result[name]) == len(close), f"{name} 输出长度不匹配"
