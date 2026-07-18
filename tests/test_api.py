import pytest
from datacore import UnifiedDataProvider
from datacore.models.enums import DataType, SourceGrade

class TestUnifiedDataProvider:
    def test_init(self):
        dc = UnifiedDataProvider()
        assert dc.registry is not None
        
    def test_list_symbols(self):
        dc = UnifiedDataProvider()
        assert len(dc.list_symbols()) > 0
        
    def test_unknown_symbol(self):
        dc = UnifiedDataProvider()
        p = dc.get('ZZZ', DataType.OHLCV)
        assert not p.available
        assert p.grade == SourceGrade.UNAVAILABLE
        
    def test_get_batch(self):
        dc = UnifiedDataProvider()
        r = dc.get_batch(['RB', 'CU'], DataType.OHLCV)
        assert len(r) == 2
