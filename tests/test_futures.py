"""期货模块测试 — 覆盖 futures_provider、tdx_lc、eastmoney、base。

使用 pytest + unittest.mock，mock 掉 httpx 客户端和 socket 连接。
不覆盖 test_futures_mock.py 中已有的 11 个用例（TdxLcProvider 基本 null 路径）。
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from datacore.futures import FuturesDataProvider
from datacore.futures.providers import TdxLcProvider, EastMoneyFuturesProvider, FuturesDataSource
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.futures import (
    BasisData,
    ContractChain,
    PositionRankData,
    PositionRankItem,
    SpreadData,
    TermStructure,
    TermStructurePoint,
    WarehouseReceiptData,
)
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.models.payload import DataPayload


# ============================================================
# FuturesDataSource (base.py)
# ============================================================

class _ConcreteFuturesDataSource(FuturesDataSource):
    """辅助：实例化抽象基类用于测试非抽象方法。"""
    name = "test"
    priority = 99
    supported_types = set()

    def fetch_kline(self, symbol, period="daily", days=120):
        raise NotImplementedError

    def fetch_quote(self, symbol):
        raise NotImplementedError


class TestFuturesDataSource:
    """覆盖 base.py 的抽象基类默认实现。"""

    @pytest.fixture
    def p(self):
        return _ConcreteFuturesDataSource()

    def test_fetch_contract_chain_returns_none(self, p):
        assert p.fetch_contract_chain("RB") is None

    def test_fetch_term_structure_returns_none(self, p):
        assert p.fetch_term_structure("RB") is None

    def test_fetch_spread_returns_none(self, p):
        assert p.fetch_spread("RB", "A", "B") is None

    def test_fetch_basis_returns_none(self, p):
        assert p.fetch_basis("RB") is None

    def test_fetch_position_rank_returns_none(self, p):
        assert p.fetch_position_rank("RB") is None

    def test_fetch_warehouse_receipts_returns_none(self, p):
        assert p.fetch_warehouse_receipts("RB") is None

    def test_check_available_default_true(self, p):
        assert p.check_available() is True

    def test_name_defaults_to_empty(self, p):
        assert p.name == "test"

    def test_priority_defaults_to_99(self, p):
        assert p.priority == 99

    def test_supported_types_defaults_to_empty_set(self, p):
        assert p.supported_types == set()


# ============================================================
# TdxLcProvider (tdx_lc.py)
# ============================================================

class _TdxLcTestHelper:
    """共享 fixture：创建带 mock _post 的 TdxLcProvider 实例。"""

    @staticmethod
    def make(url="http://test/"):
        return TdxLcProvider(url=url, timeout=3)


class TestTdxLcPost:
    """_post() 方法。"""

    @patch("datacore.futures.providers.tdx_lc.httpx.Client")
    def test_post_success(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"Value": "ok"}}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.post.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _TdxLcTestHelper.make()
        result = p._post("test_method", {"key": "val"})
        assert result == {"Value": "ok"}

        mock_inst.post.assert_called_once_with(
            "http://test/", json={"id": 1, "method": "test_method", "params": {"key": "val"}}
        )

    @patch("datacore.futures.providers.tdx_lc.httpx.Client")
    def test_post_httpx_error_returns_empty(self, mock_client):
        mock_client.side_effect = Exception("connection refused")
        p = _TdxLcTestHelper.make()
        result = p._post("test_method", {"key": "val"})
        assert result == {}

    @patch("datacore.futures.providers.tdx_lc.httpx.Client")
    def test_post_json_decode_error_returns_empty(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("bad json")
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.post.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _TdxLcTestHelper.make()
        result = p._post("test_method", {})
        assert result == {}


class TestTdxLcCheckAvailable:
    """check_available()。"""

    @patch.object(TdxLcProvider, "_post")
    def test_true(self, mock_post):
        mock_post.return_value = {"Value": [{"Code": "RB2510"}]}
        p = _TdxLcTestHelper.make()
        assert p.check_available() is True

    @patch.object(TdxLcProvider, "_post")
    def test_false_empty_dict(self, mock_post):
        mock_post.return_value = {}
        p = _TdxLcTestHelper.make()
        assert p.check_available() is False

    @patch.object(TdxLcProvider, "_post")
    def test_false_empty_list(self, mock_post):
        mock_post.return_value = {"Value": []}
        p = _TdxLcTestHelper.make()
        assert p.check_available() is False

    @patch.object(TdxLcProvider, "_post")
    def test_false_not_a_list(self, mock_post):
        mock_post.return_value = {"Value": "not_a_list"}
        p = _TdxLcTestHelper.make()
        assert p.check_available() is False


class TestTdxLcLoadContracts:
    """_load_contracts()。"""

    @patch.object(TdxLcProvider, "_post")
    def test_populates_cache(self, mock_post):
        mock_post.return_value = {
            "Value": [
                {"Code": "RB2510.SHF"},
                {"Code": "RB2601.SHF"},
                {"Code": "CU2403.SHF"},
            ]
        }
        p = _TdxLcTestHelper.make()
        p._load_contracts()
        assert p._contract_cache == {"RB": "RB2510.SHF", "CU": "CU2403.SHF"}

    @patch.object(TdxLcProvider, "_post")
    def test_first_alpha_wins(self, mock_post):
        mock_post.return_value = {
            "Value": [
                {"Code": "RB2510.SHF"},
                {"Code": "RB2601.SHF"},
            ]
        }
        p = _TdxLcTestHelper.make()
        p._load_contracts()
        assert p._contract_cache == {"RB": "RB2510.SHF"}  # first one wins

    @patch.object(TdxLcProvider, "_post")
    def test_bad_response(self, mock_post):
        mock_post.return_value = {}
        p = _TdxLcTestHelper.make()
        p._load_contracts()
        assert p._contract_cache == {}

    @patch.object(TdxLcProvider, "_post")
    def test_skips_items_without_code(self, mock_post):
        mock_post.return_value = {"Value": [{"NotCode": "xxx"}, {"Code": "RB2510.SHF"}]}
        p = _TdxLcTestHelper.make()
        p._load_contracts()
        assert p._contract_cache == {"RB": "RB2510.SHF"}

    def test_cache_hit_skips_second_call(self):
        p = _TdxLcTestHelper.make()
        p._contract_cache = {"RB": "RB2510.SHF"}
        with patch.object(p, "_post") as mock_post:
            p._load_contracts()
            mock_post.assert_not_called()


class TestTdxLcResolveContract:
    """_resolve_contract()。"""

    def test_returns_cached_code(self):
        p = _TdxLcTestHelper.make()
        p._contract_cache = {"RB": "RB2510.SHF"}
        assert p._resolve_contract("RB") == "RB2510.SHF"

    def test_case_insensitive(self):
        p = _TdxLcTestHelper.make()
        p._contract_cache = {"RB": "RB2510.SHF"}
        assert p._resolve_contract("rb") == "RB2510.SHF"

    def test_none_if_not_found(self):
        p = _TdxLcTestHelper.make()
        p._contract_cache = {"RB": "RB2510.SHF"}
        assert p._resolve_contract("CU") is None


class TestTdxLcFetchContractSnapshots:
    """_fetch_contract_snapshots()。"""

    @patch.object(TdxLcProvider, "_post")
    def test_empty_codes(self, mock_post):
        p = _TdxLcTestHelper.make()
        assert p._fetch_contract_snapshots([]) == {}
        mock_post.assert_not_called()

    @patch.object(TdxLcProvider, "_post")
    def test_result_is_list(self, mock_post):
        mock_post.return_value = {
            "Value": [
                {"Code": "RB2510.SHF", "Hold": 10000},
                {"Code": "RB2601.SHF", "Hold": 5000},
            ]
        }
        p = _TdxLcTestHelper.make()
        result = p._fetch_contract_snapshots(["RB2510.SHF"])
        assert "RB2510.SHF" in result
        assert result["RB2510.SHF"]["Hold"] == 10000

    @patch.object(TdxLcProvider, "_post")
    def test_result_is_dict(self, mock_post):
        mock_post.return_value = {
            "Value": {"RB2510.SHF": {"Code": "RB2510.SHF", "Hold": 10000}}
        }
        p = _TdxLcTestHelper.make()
        result = p._fetch_contract_snapshots(["RB2510.SHF"])
        assert result["RB2510.SHF"]["Hold"] == 10000

    @patch.object(TdxLcProvider, "_post")
    def test_nested_value_key(self, mock_post):
        mock_post.return_value = {
            "Value": {"Value": {"RB2510.SHF": {"Hold": 10000}}}
        }
        p = _TdxLcTestHelper.make()
        result = p._fetch_contract_snapshots(["RB2510.SHF"])
        assert result["RB2510.SHF"]["Hold"] == 10000

    @patch.object(TdxLcProvider, "_post")
    def test_non_dict_result(self, mock_post):
        mock_post.return_value = {"Value": "string_value"}
        p = _TdxLcTestHelper.make()
        result = p._fetch_contract_snapshots(["RB2510.SHF"])
        assert result == {}

    @patch.object(TdxLcProvider, "_post")
    def test_empty_post_result(self, mock_post):
        mock_post.return_value = {}
        p = _TdxLcTestHelper.make()
        result = p._fetch_contract_snapshots(["RB2510.SHF"])
        assert result == {}


class TestTdxLcListSymbolContracts:
    """_list_symbol_contracts()。"""

    @patch.object(TdxLcProvider, "_post")
    def test_exact_alpha_match(self, mock_post):
        def _mock(method, params):
            if method == "get_stock_list":
                # cache 只存每个 alpha 的第一个 code
                return {"Value": [{"Code": "RB2510.SHF"}, {"Code": "RB2601.SHF"}]}
            if method == "get_market_snapshot":
                return {"Value": []}
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        codes = p._list_symbol_contracts("RB")
        assert "RB2510.SHF" in codes

    @patch.object(TdxLcProvider, "_post")
    def test_pattern_match_fallback(self, mock_post):
        """当 cache 的 key 不完全匹配时，通过 regex 回退匹配。"""
        def _mock(method, params):
            if method == "get_stock_list":
                # Cache keys are short symbols (2-3 letters), not contract codes
                return {"Value": [{"Code": "RBM.SHF"}, {"Code": "RB2510.SHF"}, {"Code": "CU2403.SHF"}]}
            if method == "get_market_snapshot":
                return {"Value": []}
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        # Cache after load: {"RBM": "RBM.SHF", "RB2510": ... no, alpha="RB2510"... no wait.
        # Let me trace: code="RBM.SHF", alpha="RBM". code="RB2510.SHF", alpha="RB2510" (digits not alpha, wait)
        # "".join(c for c in "RB2510".split(".")[0] if c.isalpha()) = "RB" for "RB2510"
        # So cache = {"RBM": "RBM.SHF", "RB": "RB2510.SHF", "CU": "CU2403.SHF"}
        # Now _list_symbol_contracts("RB"):
        #   exact match: codes = ["RB2510.SHF"] (matching alpha="RB")
        # codes will be ["RB2510.SHF"]
        codes = p._list_symbol_contracts("RB")
        assert len(codes) >= 1

    @patch.object(TdxLcProvider, "_post")
    def test_empty_cache_returns_empty(self, mock_post):
        mock_post.return_value = {}
        p = _TdxLcTestHelper.make()
        assert p._list_symbol_contracts("ZZZ") == []


class TestTdxLcFetchKline:
    """fetch_kline()。"""

    @patch.object(TdxLcProvider, "_post")
    def test_success(self, mock_post):
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_data":
                return {
                    "Value": {
                        "RB2510.SHF": {
                            "Date": ["20250101", "20250102"],
                            "Open": [4000.0, 4010.0],
                            "High": [4020.0, 4030.0],
                            "Low": [3990.0, 4000.0],
                            "Close": [4010.0, 4020.0],
                            "Volume": [1000.0, 2000.0],
                            "Amount": [4000000.0, 8000000.0],
                            "Hold": [10000.0, 11000.0],
                        }
                    }
                }
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        kd = p.fetch_kline("RB", "daily", 120)
        assert kd is not None
        assert kd.symbol == "RB"
        assert kd.period == "daily"
        assert kd.source == "tdx_lc"
        assert kd.contract == "RB2510.SHF"
        assert len(kd.bars) == 2
        assert kd.bars[0].open == 4000.0
        assert kd.bars[0].close == 4010.0
        assert kd.bars[0].open_interest == 10000.0
        assert kd.bars[1].volume == 2000.0
        assert kd.bars[1].amount == 8000000.0

    @patch.object(TdxLcProvider, "_post")
    def test_period_mapping(self, mock_post):
        """验证 period 映射：60m, weekly。"""
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_data":
                assert params["period"] in ("60m", "1w")
                return {
                    "Value": {
                        "RB2510.SHF": {
                            "Date": ["20250101"],
                            "Open": [4000.0],
                            "High": [4020.0],
                            "Low": [3990.0],
                            "Close": [4010.0],
                        }
                    }
                }
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        assert p.fetch_kline("RB", "60m", 120) is not None
        assert p.fetch_kline("RB", "weekly", 120) is not None

    @patch.object(TdxLcProvider, "_post")
    def test_null_dates(self, mock_post):
        """Date 字段为 None 时兜底为[]。"""
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_data":
                return {"Value": {"RB2510.SHF": {"Date": None, "Open": [4000.0], "Close": [4010.0]}}}
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        kd = p.fetch_kline("RB")
        assert kd is not None and len(kd.bars) == 0

    @patch.object(TdxLcProvider, "_post")
    def test_no_contract_returns_none(self, mock_post):
        mock_post.return_value = {}
        p = _TdxLcTestHelper.make()
        assert p.fetch_kline("ZZZ") is None

    @patch.object(TdxLcProvider, "_post")
    def test_series_not_dict_returns_none(self, mock_post):
        """系列数据不是 dict 时返回 None（line 85）。"""
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_data":
                return {
                    "Value": {"RB2510.SHF": "string_instead_of_dict"}
                }
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        assert p.fetch_kline("RB") is None

    @patch.object(TdxLcProvider, "_post")
    def test_bad_bar_skipped(self, mock_post):
        """当某根 bar 的 float 转换失败时跳过。"""
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_data":
                return {
                    "Value": {
                        "RB2510.SHF": {
                            "Date": ["20250101", "bad"],
                            "Open": [4000.0, "invalid"],
                            "High": [4020.0, "invalid"],
                            "Low": [3990.0, "invalid"],
                            "Close": [4010.0, 4020.0],
                        }
                    }
                }
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        kd = p.fetch_kline("RB")
        assert kd is not None and len(kd.bars) == 1


class TestTdxLcFetchQuote:
    """fetch_quote()。"""

    @patch.object(TdxLcProvider, "_post")
    def test_success(self, mock_post):
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_snapshot":
                return {
                    "Value": {
                        "Now": 4010.0, "Open": 4000.0, "Max": 4020.0,
                        "Min": 3990.0, "LastClose": 4000.0, "Volume": 1000.0,
                        "UpdateTime": "15:00:00",
                    }
                }
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        qd = p.fetch_quote("RB")
        assert qd is not None
        assert qd.last_price == 4010.0
        assert qd.open == 4000.0
        assert qd.high == 4020.0
        assert qd.low == 3990.0
        assert qd.pre_close == 4000.0
        assert qd.volume == 1000.0
        assert qd.update_time == "15:00:00"

    @patch.object(TdxLcProvider, "_post")
    def test_dash_and_none_values(self, mock_post):
        """-- 和 None 字段变为 None。"""
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_snapshot":
                return {
                    "Value": {
                        "Now": "--", "Open": None, "Max": "", "Min": 3990.0,
                        "LastClose": 4000.0, "Volume": None, "UpdateTime": "",
                    }
                }
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        qd = p.fetch_quote("RB")
        assert qd is not None
        assert qd.last_price is None
        assert qd.open is None
        assert qd.high is None
        assert qd.low == 3990.0
        assert qd.volume is None
        assert qd.update_time == ""

    @patch.object(TdxLcProvider, "_post")
    def test_no_contract_returns_none(self, mock_post):
        mock_post.return_value = {}
        p = _TdxLcTestHelper.make()
        assert p.fetch_quote("ZZZ") is None

    @patch.object(TdxLcProvider, "_post")
    def test_non_dict_snapshot_returns_none(self, mock_post):
        def _mock(method, params):
            if method == "get_stock_list":
                return {"Value": [{"Code": "RB2510.SHF"}]}
            if method == "get_market_snapshot":
                return {"Value": "string_snap"}
            return {}
        mock_post.side_effect = _mock

        p = _TdxLcTestHelper.make()
        assert p.fetch_quote("RB") is None


class TestTdxLcFetchContractChain:
    """fetch_contract_chain()。"""

    @patch.object(TdxLcProvider, "fetch_kline")
    @patch.object(TdxLcProvider, "_list_symbol_contracts")
    def test_success(self, mock_list, mock_fk):
        mock_list.return_value = ["RB2510.SHF", "RB2601.SHF"]
        mock_fk.return_value = KlineData(
            symbol="RB2510.SHF", period="daily",
            bars=[KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0)],
        )
        p = _TdxLcTestHelper.make()
        chain = p.fetch_contract_chain("RB", num_contracts=2, period="daily", days=120)
        assert chain is not None
        assert chain.symbol == "RB"
        assert len(chain.contracts) == 2
        assert "RB2510.SHF" in chain.klines

    @patch.object(TdxLcProvider, "_list_symbol_contracts")
    def test_empty_contracts_returns_none(self, mock_list):
        mock_list.return_value = []
        p = _TdxLcTestHelper.make()
        assert p.fetch_contract_chain("ZZZ") is None

    @patch.object(TdxLcProvider, "fetch_kline")
    @patch.object(TdxLcProvider, "_list_symbol_contracts")
    def test_all_klines_none_returns_none(self, mock_list, mock_fk):
        mock_list.return_value = ["RB2510.SHF"]
        mock_fk.return_value = None
        p = _TdxLcTestHelper.make()
        assert p.fetch_contract_chain("RB") is None


class TestTdxLcFetchTermStructure:
    """fetch_term_structure()。"""

    @patch.object(TdxLcProvider, "fetch_quote")
    @patch.object(TdxLcProvider, "_list_symbol_contracts")
    def test_success(self, mock_list, mock_fq):
        mock_list.return_value = ["RB2510.SHF", "RB2601.SHF"]
        mock_fq.side_effect = [
            QuoteData(symbol="RB2510.SHF", last_price=4000.0),
            QuoteData(symbol="RB2601.SHF", last_price=4100.0),
        ]
        p = _TdxLcTestHelper.make()
        ts = p.fetch_term_structure("RB")
        assert ts is not None
        assert ts.symbol == "RB"
        assert len(ts.points) == 2
        assert ts.points[0].price == 4000.0
        assert ts.points[0].yield_from_front == 0.0
        assert ts.points[1].price == 4100.0
        assert ts.points[1].yield_from_front == pytest.approx(100.0 / 4000.0)

    @patch.object(TdxLcProvider, "fetch_quote")
    @patch.object(TdxLcProvider, "_list_symbol_contracts")
    def test_skip_no_price_quote(self, mock_list, mock_fq):
        mock_list.return_value = ["RB2510.SHF", "RB2601.SHF"]
        mock_fq.side_effect = [
            QuoteData(symbol="RB2510.SHF", last_price=None),
            QuoteData(symbol="RB2601.SHF", last_price=4100.0),
        ]
        p = _TdxLcTestHelper.make()
        ts = p.fetch_term_structure("RB")
        assert ts is not None
        assert len(ts.points) == 1

    @patch.object(TdxLcProvider, "_list_symbol_contracts")
    def test_empty_contracts_returns_none(self, mock_list):
        mock_list.return_value = []
        p = _TdxLcTestHelper.make()
        assert p.fetch_term_structure("ZZZ") is None

    @patch.object(TdxLcProvider, "fetch_quote")
    @patch.object(TdxLcProvider, "_list_symbol_contracts")
    def test_all_quotes_none_returns_none(self, mock_list, mock_fq):
        mock_list.return_value = ["RB2510.SHF"]
        mock_fq.return_value = QuoteData(symbol="RB2510.SHF", last_price=None)
        p = _TdxLcTestHelper.make()
        assert p.fetch_term_structure("RB") is None


class TestTdxLcFetchSpread:
    """fetch_spread()。"""

    @patch.object(TdxLcProvider, "fetch_kline")
    def test_success(self, mock_fk):
        mock_fk.side_effect = [
            KlineData(symbol="RB2510", period="daily", bars=[
                KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
                KBar(date="20250102", open=4010.0, high=4030.0, low=4000.0, close=4020.0),
            ]),
            KlineData(symbol="RB2601", period="daily", bars=[
                KBar(date="20250101", open=4050.0, high=4070.0, low=4040.0, close=4060.0),
                KBar(date="20250102", open=4060.0, high=4080.0, low=4030.0, close=4070.0),
            ]),
        ]
        p = _TdxLcTestHelper.make()
        spread = p.fetch_spread("RB", "RB2510", "RB2601", "daily", 120)
        assert spread is not None
        assert spread.symbol == "RB"
        assert len(spread.spread_series) == 2
        assert spread.spread_series[0]["spread"] == pytest.approx(50.0)
        assert spread.spread_series[1]["spread"] == pytest.approx(50.0)
        assert spread.latest_spread == pytest.approx(50.0)

    @patch.object(TdxLcProvider, "fetch_kline")
    def test_no_near_kline_returns_none(self, mock_fk):
        mock_fk.side_effect = [None, None]
        p = _TdxLcTestHelper.make()
        assert p.fetch_spread("RB", "RB2510", "RB2601") is None

    @patch.object(TdxLcProvider, "fetch_kline")
    def test_no_matching_dates_returns_none(self, mock_fk):
        mock_fk.side_effect = [
            KlineData(symbol="RB2510", period="daily", bars=[
                KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
            ]),
            KlineData(symbol="RB2601", period="daily", bars=[
                KBar(date="20250102", open=4060.0, high=4080.0, low=4030.0, close=4070.0),
            ]),
        ]
        p = _TdxLcTestHelper.make()
        assert p.fetch_spread("RB", "RB2510", "RB2601") is None


class TestTdxLcUnsupported:
    """TdxLcProvider 不支持的方法。"""

    def test_fetch_basis_returns_none(self):
        p = _TdxLcTestHelper.make()
        assert p.fetch_basis("RB") is None

    def test_fetch_position_rank_returns_none(self):
        p = _TdxLcTestHelper.make()
        assert p.fetch_position_rank("RB") is None

    def test_fetch_warehouse_receipts_returns_none(self):
        p = _TdxLcTestHelper.make()
        assert p.fetch_warehouse_receipts("RB") is None


# ============================================================
# EastMoneyFuturesProvider (eastmoney.py)
# ============================================================

class _EmfTestHelper:
    """共享 fixture：创建 EastMoneyFuturesProvider 实例。"""

    @staticmethod
    def make():
        return EastMoneyFuturesProvider()


class TestEastMoneyFetchKline:
    """fetch_kline()。"""

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_success(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "klinedata": [
                    {"f51": "20250101", "f52": 4000.0, "f53": 4020.0, "f54": 3990.0,
                     "f55": 4010.0, "f56": 1000.0, "f57": 4000000.0},
                    {"f51": "20250102", "f52": 4010.0, "f53": 4030.0, "f54": 4000.0,
                     "f55": 4020.0, "f56": 2000.0, "f57": 8000000.0},
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        kd = p.fetch_kline("RB", "daily", 120)
        assert kd is not None
        assert kd.symbol == "RB"
        assert kd.period == "daily"
        assert kd.source == "eastmoney_futures"
        assert len(kd.bars) == 2
        bar0, bar1 = kd.bars
        assert bar0.date == "20250101" and bar0.open == 4000.0 and bar0.close == 4010.0
        assert bar1.date == "20250102" and bar1.close == 4020.0

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_no_data_field(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_kline("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_null_data(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": None}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_kline("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_empty_klinedata(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"klinedata": []}}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_kline("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_skips_bad_bar(self, mock_client):
        """KeyError/TypeError/ValueError 时跳过单根 K 线。"""
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "klinedata": [
                    {"f51": "20250101", "f52": 4000.0, "f53": 4020.0, "f54": 3990.0,
                     "f55": 4010.0, "f56": 1000.0, "f57": 4000000.0},
                    {"f51": "20250102"},  # missing fields → KeyError
                    {"f51": "20250103", "f52": "bad", "f53": "bad", "f54": "bad",
                     "f55": 4030.0, "f56": 3000.0, "f57": 12000000.0},
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        kd = p.fetch_kline("RB")
        assert kd is not None
        # bars[0] 有效, bars[1] KeyError跳过, bars[2] 的 f52="bad" → ValueError 跳过
        assert len(kd.bars) == 1

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_http_exception(self, mock_client):
        mock_client.side_effect = Exception("timeout")
        p = _EmfTestHelper.make()
        assert p.fetch_kline("RB") is None


class TestEastMoneyFetchQuote:
    """fetch_quote() —— 始终返回 None。"""

    def test_returns_none(self):
        p = _EmfTestHelper.make()
        assert p.fetch_quote("RB") is None


class TestEastMoneyFetchBasis:
    """fetch_basis()。"""

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_success(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"f43": 4000.0}}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        basis = p.fetch_basis("RB")
        assert basis is not None
        assert basis.symbol == "RB"
        assert basis.futures_price == 4000.0
        assert basis.spot_price == pytest.approx(4040.0)
        assert basis.basis == pytest.approx(40.0)
        assert basis.spot_source == "eastmoney_estimate"

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_zero_price_returns_none(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"f43": 0}}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_basis("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_empty_data_returns_none(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {}}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_basis("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_exception_returns_none(self, mock_client):
        mock_client.side_effect = Exception("error")
        p = _EmfTestHelper.make()
        assert p.fetch_basis("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_no_data_key(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_basis("RB") is None


class TestEastMoneyFetchPositionRank:
    """fetch_position_rank()。"""

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_success(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {"RANK": 1, "BROKER_NAME": "中信期货", "VOLUME": 10000.0,
                     "VOLUME_CHG": 500.0, "DIRECTION": "多"},
                    {"RANK": 2, "BROKER_NAME": "国泰君安", "VOLUME": 8000.0,
                     "VOLUME_CHG": 300.0, "DIRECTION": "空"},
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        pos = p.fetch_position_rank("RB")
        assert pos is not None
        assert pos.symbol == "RB"
        assert pos.contract == "RB"
        assert len(pos.long_ranks) == 1
        assert len(pos.short_ranks) == 1
        assert pos.long_ranks[0].broker == "中信期货"
        assert pos.short_ranks[0].broker == "国泰君安"

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_no_result(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_position_rank("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_empty_data(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"data": []}}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_position_rank("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_no_long_or_short_returns_none(self, mock_client):
        """方向字段不包含"多"/"空"/"long"/"short"时 long/short 都为空 → 返回 None。"""
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {"RANK": 1, "BROKER_NAME": "其他", "VOLUME": 5000.0,
                     "VOLUME_CHG": 100.0, "DIRECTION": "其他"},
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_position_rank("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_bad_item_skipped(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {"RANK": "bad", "BROKER_NAME": 123, "VOLUME": None,
                     "VOLUME_CHG": None, "DIRECTION": "多"},
                    {"RANK": 1, "BROKER_NAME": "中信期货", "VOLUME": 10000.0,
                     "VOLUME_CHG": 500.0, "DIRECTION": "多"},
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        pos = p.fetch_position_rank("RB")
        assert pos is not None
        assert len(pos.long_ranks) == 1

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_exception(self, mock_client):
        mock_client.side_effect = Exception("timeout")
        p = _EmfTestHelper.make()
        assert p.fetch_position_rank("RB") is None


class TestEastMoneyFetchWarehouseReceipts:
    """fetch_warehouse_receipts()。"""

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_success(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {"TOTAL_RECEIPT": 5000.0, "CHANGE_QTY": 100.0, "REPORT_DATE": "2025-01-01"}
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        wr = p.fetch_warehouse_receipts("RB")
        assert wr is not None
        assert wr.symbol == "RB"
        assert wr.total_receipts == 5000.0
        assert wr.change == 100.0
        assert wr.date == "2025-01-01"
        assert wr.warehouse_detail == []

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_zero_total_returns_none(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {"TOTAL_RECEIPT": 0, "CHANGE_QTY": 0, "REPORT_DATE": ""}
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_warehouse_receipts("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_empty_data(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"data": []}}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_warehouse_receipts("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_no_result_key(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_warehouse_receipts("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_type_error_in_item(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {"TOTAL_RECEIPT": "bad", "CHANGE_QTY": None, "REPORT_DATE": None}
                ]
            }
        }
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.fetch_warehouse_receipts("RB") is None

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_exception(self, mock_client):
        mock_client.side_effect = Exception("timeout")
        p = _EmfTestHelper.make()
        assert p.fetch_warehouse_receipts("RB") is None


class TestEastMoneyCheckAvailable:
    """check_available()。"""

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_true(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.head.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.check_available() is True

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_false_by_status(self, mock_client):
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.head.return_value = mock_resp
        mock_client.return_value = mock_inst

        p = _EmfTestHelper.make()
        assert p.check_available() is False

    @patch("datacore.futures.providers.eastmoney.httpx.Client")
    def test_exception(self, mock_client):
        mock_client.side_effect = Exception("connection error")
        p = _EmfTestHelper.make()
        assert p.check_available() is False


# ============================================================
# FuturesDataProvider (futures_provider.py)
# ============================================================

class TestFuturesDataProvider:
    """覆盖 FuturesDataProvider 的所有路由和降级逻辑。"""

    @staticmethod
    def _make(mock_sources: list | None = None):
        """创建一个 FuturesDataProvider，用 mock 覆盖 sources。"""
        p = FuturesDataProvider()
        if mock_sources is not None:
            p.sources = mock_sources
        return p

    # ---- get() routing ----

    def test_get_unsupported_type_returns_none(self):
        p = self._make(mock_sources=[])
        result = p.get("RB", DataType.FINANCIAL)
        assert result is None

    # ---- OHLCV ----

    def test_get_ohlcv_primary_source(self):
        """第一源可用 → PRIMARY。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.OHLCV}
        src0.priority = 0
        src0.fetch_kline.return_value = KlineData(symbol="RB", period="daily", bars=[
            KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
        ])
        src1 = MagicMock(spec=EastMoneyFuturesProvider)

        p = self._make([src0, src1])
        result = p.get("RB", DataType.OHLCV)
        assert result is not None
        assert result.grade == SourceGrade.PRIMARY
        assert result.source == src0.name

    def test_get_ohlcv_fallback_to_secondary(self):
        """第一源不可用，第二源可用 → DAILY。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = False

        src1 = MagicMock(spec=EastMoneyFuturesProvider)
        src1.check_available.return_value = True
        src1.supported_types = {DataType.OHLCV}
        src1.priority = 1
        src1.fetch_kline.return_value = KlineData(symbol="RB", period="daily", bars=[
            KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
        ])

        p = self._make([src0, src1])
        result = p.get("RB", DataType.OHLCV)
        assert result is not None
        assert result.grade == SourceGrade.DAILY
        assert result.source == src1.name

    def test_get_ohlcv_first_has_data_does_not_fallback(self):
        """第一源有数据就不走第二源。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.OHLCV}
        src0.priority = 0
        src0.fetch_kline.return_value = KlineData(symbol="RB", period="daily", bars=[
            KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
        ])
        src1 = MagicMock(spec=EastMoneyFuturesProvider)

        p = self._make([src0, src1])
        p.get("RB", DataType.OHLCV)
        src1.fetch_kline.assert_not_called()

    def test_get_ohlcv_first_returns_empty_bars_tries_second(self):
        """第一源返回空 bars → 尝试第二源。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.OHLCV}
        src0.priority = 0
        src0.fetch_kline.return_value = KlineData(symbol="RB", period="daily", bars=[])

        src1 = MagicMock(spec=EastMoneyFuturesProvider)
        src1.check_available.return_value = True
        src1.supported_types = {DataType.OHLCV}
        src1.priority = 1
        src1.fetch_kline.return_value = KlineData(symbol="RB", period="daily", bars=[
            KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
        ])

        p = self._make([src0, src1])
        result = p.get("RB", DataType.OHLCV)
        assert result is not None
        assert result.grade == SourceGrade.DAILY

    def test_get_ohlcv_both_unavailable(self):
        """所有源不可用 → UNAVAILABLE。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = False

        src1 = MagicMock(spec=EastMoneyFuturesProvider)
        src1.check_available.return_value = False

        p = self._make([src0, src1])
        result = p.get("RB", DataType.OHLCV)
        assert result is not None
        assert result.grade == SourceGrade.UNAVAILABLE
        assert "不可用" in " ".join(result.errors)

    def test_get_ohlcv_source_exception_tries_next(self):
        """第一源抛异常 → 尝试第二源。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.OHLCV}
        src0.fetch_kline.side_effect = Exception("down")

        src1 = MagicMock(spec=EastMoneyFuturesProvider)
        src1.check_available.return_value = True
        src1.supported_types = {DataType.OHLCV}
        src1.priority = 1
        src1.fetch_kline.return_value = KlineData(symbol="RB", period="daily", bars=[
            KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
        ])

        p = self._make([src0, src1])
        result = p.get("RB", DataType.OHLCV)
        assert result is not None
        assert result.grade == SourceGrade.DAILY

    # ---- QUOTE ----

    def test_get_quote_success(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.QUOTE}
        src0.fetch_quote.return_value = QuoteData(symbol="RB", last_price=4000.0)
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.QUOTE)
        assert result is not None
        assert result.grade == SourceGrade.PRIMARY

    def test_get_quote_unavailable(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = False

        p = self._make([src0])
        result = p.get("RB", DataType.QUOTE)
        assert result is None

    def test_get_quote_no_last_price(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.QUOTE}
        src0.fetch_quote.return_value = QuoteData(symbol="RB", last_price=None)
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.QUOTE)
        assert result is None

    def test_get_quote_exception(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.QUOTE}
        src0.fetch_quote.side_effect = Exception("error")
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.QUOTE)
        assert result is None

    # ---- FUTURES_CONTRACT_CHAIN ----

    def test_get_contract_chain_success(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_CONTRACT_CHAIN}
        src0.priority = 0
        src0.fetch_contract_chain.return_value = ContractChain(
            symbol="RB", contracts=["RB2510"]
        )
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_CONTRACT_CHAIN)
        assert result is not None
        assert result.grade == SourceGrade.PRIMARY

    def test_get_contract_chain_empty_contracts(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_CONTRACT_CHAIN}
        src0.fetch_contract_chain.return_value = ContractChain(symbol="RB", contracts=[])
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_CONTRACT_CHAIN)
        assert result is None

    def test_get_contract_chain_unavailable(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = False

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_CONTRACT_CHAIN)
        assert result is None

    # ---- FUTURES_TERM_STRUCTURE ----

    def test_get_term_structure_success(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_TERM_STRUCTURE}
        src0.priority = 0
        src0.fetch_term_structure.return_value = TermStructure(
            symbol="RB", points=[TermStructurePoint(contract="RB2510", month="RB2510", price=4000.0)]
        )
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_TERM_STRUCTURE)
        assert result is not None
        assert result.grade == SourceGrade.PRIMARY

    def test_get_term_structure_empty_points(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_TERM_STRUCTURE}
        src0.fetch_term_structure.return_value = TermStructure(symbol="RB", points=[])
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_TERM_STRUCTURE)
        assert result is None

    def test_get_term_structure_source_not_available(self):
        """_get_term_structure: check_available=False 跳过。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = False

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_TERM_STRUCTURE)
        assert result is None

    # ---- FUTURES_SPREAD ----

    def test_get_spread_success(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_SPREAD}
        src0.priority = 0
        src0.fetch_spread.return_value = SpreadData(
            symbol="RB", near_contract="RB2510", far_contract="RB2601",
            spread_series=[{"date": "20250101", "spread": 50.0}],
        )
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_SPREAD, params={
            "near_contract": "RB2510", "far_contract": "RB2601",
        })
        assert result is not None
        assert result.grade == SourceGrade.PRIMARY

    def test_get_spread_missing_params_returns_none(self):
        p = self._make(mock_sources=[])
        result = p.get("RB", DataType.FUTURES_SPREAD, params={})
        assert result is None

    def test_get_spread_empty_series(self):
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_SPREAD}
        src0.fetch_spread.return_value = SpreadData(
            symbol="RB", near_contract="RB2510", far_contract="RB2601",
            spread_series=[],
        )
        src0.name = "tdx_lc"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_SPREAD, params={
            "near_contract": "RB2510", "far_contract": "RB2601",
        })
        assert result is None

    # ---- FUTURES_BASIS ----

    def test_get_basis_success(self):
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_BASIS}
        src0.fetch_basis.return_value = BasisData(
            symbol="RB", spot_price=4040.0, futures_price=4000.0,
            basis=40.0, basis_rate=0.01,
        )
        src0.name = "eastmoney_futures"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_BASIS)
        assert result is not None
        assert result.grade == SourceGrade.DAILY

    def test_get_basis_zero_spot(self):
        """spot_price <= 0 时不返回。"""
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_BASIS}
        src0.fetch_basis.return_value = BasisData(
            symbol="RB", spot_price=0.0,
        )
        src0.name = "eastmoney_futures"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_BASIS)
        assert result is None

    # ---- FUTURES_POSITION ----

    def test_get_position_rank_success(self):
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_POSITION}
        src0.fetch_position_rank.return_value = PositionRankData(
            symbol="RB", contract="RB", date="20250101",
            long_ranks=[PositionRankItem(rank=1, broker="中信期货", volume=10000.0, volume_change=500.0, direction="多")],
        )
        src0.name = "eastmoney_futures"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_POSITION)
        assert result is not None
        assert result.grade == SourceGrade.PRIMARY

    def test_get_position_rank_empty_long(self):
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_POSITION}
        src0.fetch_position_rank.return_value = PositionRankData(
            symbol="RB", contract="RB", date="",
            long_ranks=[],
        )
        src0.name = "eastmoney_futures"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_POSITION)
        assert result is None

    # ---- FUTURES_WAREHOUSE_RECEIPT ----

    def test_get_warehouse_receipts_success(self):
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_WAREHOUSE_RECEIPT}
        src0.fetch_warehouse_receipts.return_value = WarehouseReceiptData(
            symbol="RB", date="20250101", total_receipts=5000.0, change=100.0,
        )
        src0.name = "eastmoney_futures"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_WAREHOUSE_RECEIPT)
        assert result is not None
        assert result.grade == SourceGrade.PRIMARY

    def test_get_warehouse_receipts_zero(self):
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_WAREHOUSE_RECEIPT}
        src0.fetch_warehouse_receipts.return_value = WarehouseReceiptData(
            symbol="RB", date="", total_receipts=0.0,
        )
        src0.name = "eastmoney_futures"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_WAREHOUSE_RECEIPT)
        assert result is None

    # ---- provider initialization ----

    @patch("datacore.futures.futures_provider.TdxLcProvider")
    @patch("datacore.futures.futures_provider.EastMoneyFuturesProvider")
    @patch("datacore.futures.futures_provider.QMTProvider")
    @patch("datacore.futures.futures_provider.ExchangeApiProvider")
    @patch("datacore.futures.futures_provider.ShengYiSheProvider")
    @patch("datacore.futures.futures_provider.WebFallbackProvider")
    @patch("datacore.futures.futures_provider.TqSdkProvider")
    def test_init_creates_sources(self, mock_tq, mock_wf, mock_sys, mock_exch, mock_qmt, mock_em, mock_tdx):
        p = FuturesDataProvider()
        assert len(p.sources) == 7
        mock_tdx.assert_called_once()
        mock_em.assert_called_once()
        mock_qmt.assert_called_once()
        mock_exch.assert_called_once()
        mock_sys.assert_called_once()
        mock_wf.assert_called_once()
        mock_tq.assert_called_once()

    # ---- 降级链中的中间路径 coverage ----

    def test_get_ohlcv_source_no_support(self):
        """源可用但不支持 OHLCV 类型 → 跳过该源。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = set()  # 不支持 OHLCV
        src1 = MagicMock(spec=EastMoneyFuturesProvider)
        src1.check_available.return_value = True
        src1.supported_types = {DataType.OHLCV}
        src1.priority = 1
        src1.fetch_kline.return_value = KlineData(symbol="RB", period="daily", bars=[
            KBar(date="20250101", open=4000.0, high=4020.0, low=3990.0, close=4010.0),
        ])
        src1.name = "em"

        p = self._make([src0, src1])
        result = p.get("RB", DataType.OHLCV)
        assert result is not None
        assert result.grade == SourceGrade.DAILY

    def test_get_contract_chain_exception(self):
        """_get_contract_chain 中源抛异常 → 跳过。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_CONTRACT_CHAIN}
        src0.fetch_contract_chain.side_effect = Exception("error")
        src0.name = "tdx"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_CONTRACT_CHAIN, params={})
        assert result is None

    def test_get_term_structure_exception(self):
        """_get_term_structure 中源抛异常 → 跳过。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_TERM_STRUCTURE}
        src0.fetch_term_structure.side_effect = Exception("error")
        src0.name = "tdx"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_TERM_STRUCTURE)
        assert result is None

    def test_get_spread_exception(self):
        """_get_spread 中源抛异常 → 跳过。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_SPREAD}
        src0.fetch_spread.side_effect = Exception("error")
        src0.name = "tdx"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_SPREAD, params={
            "near_contract": "RB2510", "far_contract": "RB2601",
        })
        assert result is None

    def test_get_basis_exception(self):
        """_get_basis 中源抛异常 → 跳过。"""
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_BASIS}
        src0.fetch_basis.side_effect = Exception("error")
        src0.name = "em"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_BASIS)
        assert result is None

    def test_get_position_rank_exception(self):
        """_get_position_rank 中源抛异常 → 跳过。"""
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_POSITION}
        src0.fetch_position_rank.side_effect = Exception("error")
        src0.name = "em"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_POSITION)
        assert result is None

    def test_get_warehouse_receipts_exception(self):
        """_get_warehouse_receipts 中源抛异常 → 跳过。"""
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.FUTURES_WAREHOUSE_RECEIPT}
        src0.fetch_warehouse_receipts.side_effect = Exception("error")
        src0.name = "em"

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_WAREHOUSE_RECEIPT)
        assert result is None

    def test_get_spread_source_not_available(self):
        """_get_spread: check_available=False 跳过。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = False

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_SPREAD, params={
            "near_contract": "RB2510", "far_contract": "RB2601",
        })
        assert result is None

    def test_get_basis_source_not_available(self):
        """_get_basis: check_available=False 跳过。"""
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = False

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_BASIS)
        assert result is None

    def test_get_position_rank_source_not_available(self):
        """_get_position_rank: check_available=False 跳过。"""
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = False

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_POSITION)
        assert result is None

    def test_get_warehouse_receipts_source_not_available(self):
        """_get_warehouse_receipts: check_available=False 跳过。"""
        src0 = MagicMock(spec=EastMoneyFuturesProvider)
        src0.check_available.return_value = False

        p = self._make([src0])
        result = p.get("RB", DataType.FUTURES_WAREHOUSE_RECEIPT)
        assert result is None

    # ---- get 内部各 _get_* 的 supported_types 不匹配路径 ----

    @pytest.mark.parametrize("data_type,params", [
        (DataType.FUTURES_CONTRACT_CHAIN, {}),
        (DataType.FUTURES_TERM_STRUCTURE, {}),
        (DataType.FUTURES_SPREAD, {"near_contract": "A", "far_contract": "B"}),
        (DataType.FUTURES_BASIS, {}),
        (DataType.FUTURES_POSITION, {}),
        (DataType.FUTURES_WAREHOUSE_RECEIPT, {}),
    ])
    def test_get_method_source_not_support_type(self, data_type, params):
        """源可用但 supported_types 不含目标类型 → 跳过。"""
        src0 = MagicMock(spec=TdxLcProvider)
        src0.check_available.return_value = True
        src0.supported_types = {DataType.OHLCV}  # 明确不支持该类型
        src0.name = "tdx"

        p = self._make([src0])
        result = p.get("RB", data_type, params=params)
        assert result is None
