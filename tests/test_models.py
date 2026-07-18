import pytest
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.models.ohlcv import KBar, KlineData, QuoteData

class TestEnums:
    def test_data_type_values(self):
        assert DataType.OHLCV.value == 'ohlcv'

    def test_market_type(self):
        assert MarketType.FUTURES.value == 'futures'

    def test_source_grade(self):
        assert SourceGrade.PRIMARY.value == 'primary'

class TestPayload:
    def test_default_unavailable(self):
        dp = DataPayload(symbol='RB', data_type=DataType.OHLCV, market=MarketType.FUTURES)
        assert not dp.available

    def test_primary_available(self):
        dp = DataPayload(symbol='RB', data_type=DataType.OHLCV, market=MarketType.FUTURES, grade=SourceGrade.PRIMARY)
        assert dp.available

class TestOHLCV:
    def test_kbar(self):
        kb = KBar(date='20260717', open=100.0, high=101.0, low=99.0, close=100.5, volume=1000)
        assert kb.date == '20260717'

    def test_kline_data(self):
        kd = KlineData(symbol='RB', period='daily')
        assert len(kd.bars) == 0
