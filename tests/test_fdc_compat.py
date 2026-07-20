"""FDT/FDC 兼容层测试。

覆盖:
- compute_indicators 各种输入格式
- assess_trend_maturity 兼容性
- 异步函数的接口签名
- 数据格式转换工具函数
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest

from datacore.fdc_compat import (
    compute_indicators,
    assess_trend_maturity,
    _normalize_indicator_data,
    _kline_list_to_arrays,
    _kline_payload_to_list,
    _payload_to_data,
    get_kline,
    get_quote,
    batch_get_quotes,
    get_term_structure,
    get_spread,
    get_basis,
    get_warrant,
    get_fundamental,
    get_f10,
    get_position_ranking,
)
from datacore.indicators import TrendMaturityResult


# ============================================================
#  测试数据生成
# ============================================================

def _generate_test_data(n: int = 100, seed: int = 42) -> dict:
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


def _generate_kline_list(n: int = 50) -> list[dict]:
    data = _generate_test_data(n)
    result = []
    for i in range(n):
        result.append({
            "open": float(data["open"][i]),
            "high": float(data["high"][i]),
            "low": float(data["low"][i]),
            "close": float(data["close"][i]),
            "volume": float(data["volume"][i]),
        })
    return result


# ============================================================
#  compute_indicators 测试
# ============================================================

class TestComputeIndicators:

    def test_dict_input_ma(self):
        data = _generate_test_data()
        result = compute_indicators(data, names=["MA"])
        assert "MA" in result
        assert isinstance(result["MA"], np.ndarray)
        assert len(result["MA"]) == len(data["close"])

    def test_dict_input_multiple_indicators(self):
        data = _generate_test_data()
        result = compute_indicators(data, names=["MA", "RSI", "MACD"])
        assert "MA" in result
        assert "RSI" in result
        assert "MACD" in result

    def test_dict_input_all(self):
        data = _generate_test_data()
        result = compute_indicators(data, names="all")
        assert isinstance(result, dict)
        assert len(result) > 10

    def test_kline_list_input(self):
        kline_list = _generate_kline_list(60)
        result = compute_indicators(kline_list, names=["MA"])
        assert "MA" in result
        assert isinstance(result["MA"], np.ndarray)
        assert len(result["MA"]) == 60

    def test_kline_list_with_macd(self):
        kline_list = _generate_kline_list(60)
        result = compute_indicators(kline_list, names=["MACD"])
        assert "MACD" in result
        assert "macd" in result["MACD"]
        assert "signal" in result["MACD"]
        assert "histogram" in result["MACD"]

    def test_dataframe_input(self):
        pd = pytest.importorskip("pandas")
        data = _generate_test_data(50)
        df = pd.DataFrame({
            "Open": data["open"],
            "High": data["high"],
            "Low": data["low"],
            "Close": data["close"],
            "Volume": data["volume"],
        })
        result = compute_indicators(df, names=["MA"])
        assert "MA" in result

    def test_unsupported_format_raises(self):
        with pytest.raises(TypeError):
            compute_indicators(123, names=["MA"])

    def test_with_params(self):
        data = _generate_test_data()
        result = compute_indicators(data, names=["MA"], period=10)
        assert "MA" in result
        assert not np.isnan(result["MA"][9])
        assert np.isnan(result["MA"][8])

    def test_string_name(self):
        data = _generate_test_data()
        result = compute_indicators(data, names="MA")
        assert "MA" in result

    def test_empty_kline_list(self):
        result = compute_indicators([], names=["MA"])
        assert "MA" in result


# ============================================================
#  assess_trend_maturity 测试
# ============================================================

class TestAssessTrendMaturity:

    def test_basic_call(self):
        data = _generate_test_data(80)
        result = assess_trend_maturity(data["close"])
        assert isinstance(result, TrendMaturityResult)
        assert hasattr(result, "stage")
        assert hasattr(result, "score")

    def test_with_high_low(self):
        data = _generate_test_data(80)
        result = assess_trend_maturity(
            data["close"],
            high_prices=data["high"],
            low_prices=data["low"],
        )
        assert isinstance(result, TrendMaturityResult)

    def test_with_volume(self):
        data = _generate_test_data(80)
        result = assess_trend_maturity(
            data["close"],
            volume=data["volume"],
        )
        assert isinstance(result, TrendMaturityResult)

    def test_list_input(self):
        close_list = [100.0, 101.0, 102.0, 103.0, 104.0] * 20
        result = assess_trend_maturity(close_list)
        assert isinstance(result, TrendMaturityResult)

    def test_short_data(self):
        close = np.array([100.0, 101.0, 102.0])
        result = assess_trend_maturity(close)
        assert isinstance(result, TrendMaturityResult)
        assert result.stage == "unknown"

    def test_with_lookback_param(self):
        data = _generate_test_data(80)
        result = assess_trend_maturity(data["close"], lookback=30)
        assert isinstance(result, TrendMaturityResult)

    def test_full_params(self):
        data = _generate_test_data(80)
        result = assess_trend_maturity(
            data["close"],
            high_prices=data["high"],
            low_prices=data["low"],
            volume=data["volume"],
            lookback=40,
        )
        assert isinstance(result, TrendMaturityResult)


# ============================================================
#  工具函数测试
# ============================================================

class TestUtilityFunctions:

    def test_kline_list_to_arrays(self):
        kline_list = _generate_kline_list(10)
        result = _kline_list_to_arrays(kline_list)
        assert "close" in result
        assert "high" in result
        assert "low" in result
        assert "open" in result
        assert "volume" in result
        assert len(result["close"]) == 10

    def test_kline_list_to_arrays_empty(self):
        result = _kline_list_to_arrays([])
        assert "close" in result
        assert len(result["close"]) == 0

    def test_normalize_dict_with_close(self):
        data = _generate_test_data()
        result = _normalize_indicator_data(data)
        assert result is data

    def test_normalize_dict_with_kline_key(self):
        kline_list = _generate_kline_list(10)
        data = {"kline": kline_list}
        result = _normalize_indicator_data(data)
        assert "close" in result
        assert len(result["close"]) == 10

    def test_normalize_list(self):
        kline_list = _generate_kline_list(10)
        result = _normalize_indicator_data(kline_list)
        assert "close" in result

    def test_payload_to_data_with_dict(self):
        class MockPayload:
            def __init__(self):
                self.data = {"price": 100, "volume": 1000}

        payload = MockPayload()
        result = _payload_to_data(payload)
        assert result == {"price": 100, "volume": 1000}

    def test_kline_payload_to_list_with_list(self):
        class MockPayload:
            def __init__(self):
                self.data = [{"close": 100}, {"close": 101}]

        payload = MockPayload()
        result = _kline_payload_to_list(payload)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["close"] == 100


# ============================================================
#  异步函数签名测试（不实际调用）
# ============================================================

class TestAsyncFunctionSignatures:

    def test_get_kline_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_kline)

    def test_get_quote_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_quote)

    def test_batch_get_quotes_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(batch_get_quotes)

    def test_get_term_structure_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_term_structure)

    def test_get_spread_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_spread)

    def test_get_basis_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_basis)

    def test_get_warrant_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_warrant)

    def test_get_fundamental_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_fundamental)

    def test_get_f10_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_f10)

    def test_get_position_ranking_is_coroutine(self):
        import inspect
        assert inspect.iscoroutinefunction(get_position_ranking)

    def test_all_async_functions_exist(self):
        import datacore.fdc_compat as fdc
        assert hasattr(fdc, "get_kline")
        assert hasattr(fdc, "get_quote")
        assert hasattr(fdc, "batch_get_quotes")
        assert hasattr(fdc, "get_term_structure")
        assert hasattr(fdc, "get_spread")
        assert hasattr(fdc, "get_basis")
        assert hasattr(fdc, "get_warrant")
        assert hasattr(fdc, "get_fundamental")
        assert hasattr(fdc, "get_f10")
        assert hasattr(fdc, "get_position_ranking")


# ============================================================
#  异步函数 mock 测试
# ============================================================

class TestAsyncFunctionsWithMock:
    """异步函数 mock 测试。"""

    def _setup_mock(self, mocker):
        """设置 mock provider，重置全局缓存。"""
        import datacore.fdc_compat as fdc_module
        fdc_module._provider = None
        mock_provider = mocker.AsyncMock()
        return fdc_module, mock_provider

    def test_get_kline_with_mock(self, mocker):
        """测试 get_kline 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            data=[{"close": 3500, "volume": 1000}],
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_kline("RB", period="daily", days=10))
        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_quote_with_mock(self, mocker):
        """测试 get_quote 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.QUOTE,
            market=MarketType.FUTURES,
            data={"last_price": 3500, "change": 50},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_quote("RB"))
        assert isinstance(result, dict)
        assert result["last_price"] == 3500

    def test_get_quote_list_data(self, mocker):
        """测试 get_quote 返回非 dict 数据时的包装。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.QUOTE,
            market=MarketType.FUTURES,
            data=[{"price": 3500}],
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_quote("RB"))
        assert isinstance(result, dict)
        assert result["symbol"] == "RB"
        assert "data" in result

    def test_batch_get_quotes_with_mock(self, mocker):
        """测试 batch_get_quotes 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload_rb = DataPayload(
            symbol="RB",
            data_type=DataType.QUOTE,
            market=MarketType.FUTURES,
            data={"last_price": 3500},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_payload_cu = DataPayload(
            symbol="CU",
            data_type=DataType.QUOTE,
            market=MarketType.FUTURES,
            data={"last_price": 70000},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get_batch = mocker.AsyncMock(return_value={
            "RB": mock_payload_rb,
            "CU": mock_payload_cu,
        })
        fdc_module._provider = mock_provider

        result = asyncio.run(batch_get_quotes(["RB", "CU"]))
        assert isinstance(result, dict)
        assert "RB" in result
        assert "CU" in result
        assert result["RB"]["last_price"] == 3500
        assert result["CU"]["last_price"] == 70000

    def test_batch_get_quotes_list_data(self, mocker):
        """测试 batch_get_quotes 返回非 dict 数据时的包装。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.QUOTE,
            market=MarketType.FUTURES,
            data=[{"price": 3500}],
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get_batch = mocker.AsyncMock(return_value={"RB": mock_payload})
        fdc_module._provider = mock_provider

        result = asyncio.run(batch_get_quotes(["RB"]))
        assert isinstance(result["RB"], dict)
        assert result["RB"]["symbol"] == "RB"
        assert "data" in result["RB"]

    def test_get_term_structure_with_mock(self, mocker):
        """测试 get_term_structure 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_TERM_STRUCTURE,
            market=MarketType.FUTURES,
            data={"2501": 3500, "2505": 3550},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_term_structure("RB"))
        assert isinstance(result, dict)
        assert "2501" in result

    def test_get_spread_with_mock(self, mocker):
        """测试 get_spread 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_SPREAD,
            market=MarketType.FUTURES,
            data={"spread_01_05": 50},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_spread("RB"))
        assert isinstance(result, dict)
        assert "spread_01_05" in result

    def test_get_basis_with_mock(self, mocker):
        """测试 get_basis 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_BASIS,
            market=MarketType.FUTURES,
            data={"basis": 30, "basis_ratio": 0.008},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_basis("RB"))
        assert isinstance(result, dict)
        assert "basis" in result

    def test_get_warrant_with_mock(self, mocker):
        """测试 get_warrant 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_WAREHOUSE_RECEIPT,
            market=MarketType.FUTURES,
            data={"warehouse": "上海", "quantity": 100000},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_warrant("RB"))
        assert isinstance(result, dict)
        assert "warehouse" in result

    def test_get_fundamental_with_mock(self, mocker):
        """测试 get_fundamental 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUNDAMENTAL,
            market=MarketType.FUTURES,
            data={"inventory": 100000},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_fundamental("RB"))
        assert isinstance(result, dict)
        assert "inventory" in result

    def test_get_f10_with_mock(self, mocker):
        """测试 get_f10 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.F10_REPORT,
            market=MarketType.FUTURES,
            data={"term_structure": {}, "basis": {}},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get_f10 = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_f10("RB"))
        assert isinstance(result, dict)
        assert "term_structure" in result

    def test_get_position_ranking_with_mock(self, mocker):
        """测试 get_position_ranking 异步函数。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_POSITION,
            market=MarketType.FUTURES,
            data={"long_rank": [], "short_rank": []},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_position_ranking("RB"))
        assert isinstance(result, dict)
        assert "long_rank" in result

    def test_get_kline_kline_dict_data(self, mocker):
        """测试 get_kline 处理 dict 格式 data 的 kline 数据。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            data={"kline": [{"close": 3500}]},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_kline("RB"))
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["close"] == 3500

    def test_get_kline_array_data(self, mocker):
        """测试 get_kline 处理 numpy array 格式的 data。"""
        import asyncio
        import numpy as np
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            data={"close": np.array([3500.0, 3510.0])},
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_kline("RB"))
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["close"] == 3500.0

    def test_kline_empty_data(self, mocker):
        """测试 get_kline 空数据处理。"""
        import asyncio
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        fdc_module, mock_provider = self._setup_mock(mocker)

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            data="not_list_or_dict",
            source="test",
            grade=SourceGrade.PRIMARY,
        )
        mock_provider.get = mocker.AsyncMock(return_value=mock_payload)
        fdc_module._provider = mock_provider

        result = asyncio.run(get_kline("RB"))
        assert isinstance(result, list)
        assert len(result) == 0
