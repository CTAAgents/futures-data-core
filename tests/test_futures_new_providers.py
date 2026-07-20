"""新增期货数据源测试 — QMT / TqSdk / WebFallback。"""
from unittest.mock import patch, MagicMock
import pytest


class TestQMTProvider:
    def test_instance_attributes(self):
        from datacore.futures.providers.qmt import QMTProvider
        from datacore.models.enums import DataType
        p = QMTProvider()
        assert p.name == "qmt"
        assert p.priority == 2
        assert DataType.OHLCV in p.supported_types
        assert DataType.QUOTE in p.supported_types
        assert DataType.FUTURES_CONTRACT_CHAIN in p.supported_types

    def test_check_available_no_dependency(self):
        from datacore.futures.providers import qmt as qmt_mod
        original = qmt_mod._XTV_AVAILABLE
        try:
            qmt_mod._XTV_AVAILABLE = False
            from datacore.futures.providers.qmt import QMTProvider
            p = QMTProvider()
            assert p.check_available() is False
        finally:
            qmt_mod._XTV_AVAILABLE = original

    def test_fetch_kline_unavailable(self):
        from datacore.futures.providers import qmt as qmt_mod
        original = qmt_mod._XTV_AVAILABLE
        try:
            qmt_mod._XTV_AVAILABLE = False
            from datacore.futures.providers.qmt import QMTProvider
            p = QMTProvider()
            result = p.fetch_kline("RB2501")
            assert result is None
        finally:
            qmt_mod._XTV_AVAILABLE = original

    def test_fetch_quote_unavailable(self):
        from datacore.futures.providers import qmt as qmt_mod
        original = qmt_mod._XTV_AVAILABLE
        try:
            qmt_mod._XTV_AVAILABLE = False
            from datacore.futures.providers.qmt import QMTProvider
            p = QMTProvider()
            result = p.fetch_quote("RB2501")
            assert result is None
        finally:
            qmt_mod._XTV_AVAILABLE = original

    def test_fetch_contract_chain_unavailable(self):
        from datacore.futures.providers import qmt as qmt_mod
        original = qmt_mod._XTV_AVAILABLE
        try:
            qmt_mod._XTV_AVAILABLE = False
            from datacore.futures.providers.qmt import QMTProvider
            p = QMTProvider()
            result = p.fetch_contract_chain("RB")
            assert result is None
        finally:
            qmt_mod._XTV_AVAILABLE = original


class TestTqSdkProvider:
    def test_instance_attributes(self):
        from datacore.futures.providers.tqsdk import TqSdkProvider
        from datacore.models.enums import DataType
        p = TqSdkProvider()
        assert p.name == "tqsdk"
        assert p.priority == 6
        assert DataType.OHLCV in p.supported_types
        assert DataType.QUOTE in p.supported_types

    def test_check_available_no_dependency(self):
        from datacore.futures.providers import tqsdk as tq_mod
        original = tq_mod._TQ_AVAILABLE
        try:
            tq_mod._TQ_AVAILABLE = False
            from datacore.futures.providers.tqsdk import TqSdkProvider
            p = TqSdkProvider()
            assert p.check_available() is False
        finally:
            tq_mod._TQ_AVAILABLE = original

    def test_fetch_kline_unavailable(self):
        from datacore.futures.providers import tqsdk as tq_mod
        original = tq_mod._TQ_AVAILABLE
        try:
            tq_mod._TQ_AVAILABLE = False
            from datacore.futures.providers.tqsdk import TqSdkProvider
            p = TqSdkProvider()
            result = p.fetch_kline("RB2501")
            assert result is None
        finally:
            tq_mod._TQ_AVAILABLE = original

    def test_fetch_quote_unavailable(self):
        from datacore.futures.providers import tqsdk as tq_mod
        original = tq_mod._TQ_AVAILABLE
        try:
            tq_mod._TQ_AVAILABLE = False
            from datacore.futures.providers.tqsdk import TqSdkProvider
            p = TqSdkProvider()
            result = p.fetch_quote("RB2501")
            assert result is None
        finally:
            tq_mod._TQ_AVAILABLE = original


class TestWebFallbackProvider:
    def test_instance_attributes(self):
        from datacore.futures.providers.web_fallback import WebFallbackProvider
        from datacore.models.enums import DataType
        p = WebFallbackProvider()
        assert p.name == "web_fallback"
        assert p.priority == 5
        assert DataType.OHLCV in p.supported_types
        assert DataType.QUOTE in p.supported_types
        assert DataType.FUTURES_TERM_STRUCTURE in p.supported_types
        assert DataType.FUTURES_SPREAD in p.supported_types

    @patch("datacore.futures.providers.web_fallback.httpx.Client")
    def test_check_available_ok(self, mock_client):
        from datacore.futures.providers.web_fallback import WebFallbackProvider
        p = WebFallbackProvider()
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_inst.__enter__.return_value = mock_inst
        mock_inst.head.return_value = mock_resp
        mock_client.return_value = mock_inst
        assert p.check_available() is True

    @patch("datacore.futures.providers.web_fallback.httpx.Client")
    def test_check_available_fail(self, mock_client):
        from datacore.futures.providers.web_fallback import WebFallbackProvider
        p = WebFallbackProvider()
        mock_client.side_effect = Exception("network error")
        assert p.check_available() is False

    @patch("datacore.futures.providers.web_fallback.httpx.Client")
    def test_fetch_kline_returns_none(self, mock_client):
        from datacore.futures.providers.web_fallback import WebFallbackProvider
        p = WebFallbackProvider()
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_inst.get.return_value = mock_resp
        mock_client.return_value = mock_inst
        result = p.fetch_kline("RB2501")
        assert result is None

    def test_fetch_term_structure_returns_none(self):
        from datacore.futures.providers.web_fallback import WebFallbackProvider
        p = WebFallbackProvider()
        result = p.fetch_term_structure("RB")
        assert result is None

    def test_fetch_spread_returns_none(self):
        from datacore.futures.providers.web_fallback import WebFallbackProvider
        p = WebFallbackProvider()
        result = p.fetch_spread("RB", "RB2501", "RB2505")
        assert result is None


class TestFallbackChain:
    def test_chain_order(self):
        from datacore.futures.futures_provider import FuturesDataProvider
        fp = FuturesDataProvider()
        names = [s.name for s in fp.sources]
        expected = [
            "tdx_lc",
            "eastmoney_futures",
            "qmt",
            "exchange_api",
            "shengyishe",
            "web_fallback",
            "tqsdk",
        ]
        assert names == expected

    def test_chain_priority_order(self):
        from datacore.futures.futures_provider import FuturesDataProvider
        fp = FuturesDataProvider()
        expected_priorities = [0, 1, 2, 3, 4, 5, 6]
        actual_priorities = [s.priority for s in fp.sources]
        assert actual_priorities == expected_priorities

    def test_chain_names_match_priority_order(self):
        from datacore.futures.futures_provider import FuturesDataProvider
        fp = FuturesDataProvider()
        names = [s.name for s in fp.sources]
        expected = [
            "tdx_lc",
            "eastmoney_futures",
            "qmt",
            "exchange_api",
            "shengyishe",
            "web_fallback",
            "tqsdk",
        ]
        assert names == expected

    def test_degradation_works_when_all_unavailable(self):
        from datacore.futures.futures_provider import FuturesDataProvider
        from datacore.models.enums import DataType
        fp = FuturesDataProvider()
        for src in fp.sources:
            src.check_available = MagicMock(return_value=False)
        result = fp.get("RB2501", DataType.OHLCV)
        assert result is not None
        assert result.grade.value == "unavailable"
        assert len(result.errors) > 0

    def test_providers_init_in_module(self):
        from datacore.futures.providers import (
            QMTProvider, WebFallbackProvider, TqSdkProvider,
        )
        assert QMTProvider is not None
        assert WebFallbackProvider is not None
        assert TqSdkProvider is not None
