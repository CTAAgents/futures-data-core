import pytest
from datacore.futures.providers.tdx_lc import TdxLcProvider

class TestTdxLcMock:
    def test_check_available_false(self):
        p = TdxLcProvider()
        p._post = lambda m, params: {}
        assert not p.check_available()
        
    def test_check_available_true(self):
        p = TdxLcProvider()
        p._post = lambda m, params: {'Value': [{'Code': 'RB2501'}]}
        assert p.check_available()
        
    def test_fetch_kline_no_contract(self):
        p = TdxLcProvider()
        p._post = lambda m, params: {}
        assert p.fetch_kline('ZZZ') is None
        
    def test_fetch_quote_no_contract(self):
        p = TdxLcProvider()
        p._post = lambda m, params: {}
        assert p.fetch_quote('ZZZ') is None
