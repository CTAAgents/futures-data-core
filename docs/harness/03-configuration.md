# Data-Core Configuration

Version: v0.1.0 | Updated: 2026-07-18

## Config Sources (priority high to low)
- P0: Environment variables (DATACORE_* prefix)
- P1: config/settings.yaml
- P2: Code defaults

## Key Config Items
- DATACORE_TDX_URL: TQ-Local address (default: http://127.0.0.1:17709/)
- DATACORE_TDX_TIMEOUT: HTTP timeout seconds (default: 3)
- DATACORE_CACHE_TTL: Memory cache TTL seconds (default: 3600)
- DATACORE_DB_PATH: DuckDB path (default: ~/.datacore/datacore.db)
