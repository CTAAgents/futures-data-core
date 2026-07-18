# Data-Core Testing

Version: v0.1.0 | Updated: 2026-07-18

## Test Files
- tests/test_models.py: 6 cases (enums/payload/ohlcv)
- tests/test_registry.py: 5 cases (SymbolRegistry)
- tests/test_store.py: 5 cases (MemoryCache)
- tests/test_futures_mock.py: 4 cases (TdxLcProvider mock)
- tests/test_equity_mock.py: 4 cases (TencentProvider mock)
- tests/test_api.py: 4 cases (UnifiedDataProvider routing)
Total: 28 test cases

## Run
cd D:\\Programs\\data-core
python -m pytest tests/ -v
