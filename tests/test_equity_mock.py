import pytest
from unittest.mock import patch
from datacore.equity.providers.tencent import TencentProvider
from datacore.models.enums import DataType

class TestTencentMock:
    def test_check_available_false(self):
        p = TencentProvider()
        with patch('httpx.Client') as mc:
            mc.return_value.__enter__.return_value.get.side_effect = Exception('fail')
            assert not p.check_available()
            
    def test_fetch_quote_fail_returns_none(self):
        p = TencentProvider()
        with patch('httpx.Client') as mc:
            mc.return_value.__enter__.return_value.get.side_effect = Exception('fail')
            assert p.fetch('600519', DataType.QUOTE) is None
            
    def test_fetch_kline_fail_returns_none(self):
        p = TencentProvider()
        with patch('httpx.Client') as mc:
            mc.return_value.__enter__.return_value.get.side_effect = Exception('fail')
            assert p.fetch('600519', DataType.OHLCV) is None
            
    def test_provider_attributes(self):
        p = TencentProvider()
        assert p.name == 'tencent'
        assert p.priority == 0
        assert DataType.OHLCV in p.supported_types
