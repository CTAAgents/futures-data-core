import pytest
from datacore.registry.symbol_registry import SymbolRegistry
from datacore.models.enums import MarketType

class TestSymbolRegistry:
    def test_init_has_futures(self):
        sr = SymbolRegistry()
        assert sr.resolve('RB') is not None
        
    def test_resolve_market(self):
        sr = SymbolRegistry()
        assert sr.resolve_market('RB') == MarketType.FUTURES
        
    def test_unknown_returns_none(self):
        sr = SymbolRegistry()
        assert sr.resolve('ZZZ') is None
        
    def test_list_by_market(self):
        sr = SymbolRegistry()
        assert len(sr.list_by_market(MarketType.FUTURES)) > 50
        
    def test_register_dynamic(self):
        sr = SymbolRegistry()
        sr.register('TEST', 'Test', MarketType.STOCK)
        assert sr.resolve('TEST') is not None
