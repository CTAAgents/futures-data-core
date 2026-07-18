# Data-Core Architecture

Version: v0.1.0 | Updated: 2026-07-18

## 1. System Positioning

Data-Core is an independent data infrastructure module providing unified data interfaces for FTS (Factor Trading System) and other research tools. All data sources are self-contained with zero external MCP/Skill/Agent dependencies.

## 2. Layered Architecture

UnifiedDataProvider (api.py) -> futures/ + equity/ -> models/ + registry/ + store/

## 3. Market Routing
- Pure letter code (RB, CU) -> futures
- Pure digit code (600519, 510300) -> equity
- Unknown symbol -> UNAVAILABLE

## 4. Data Source Fallback Chain
- Futures: TQ-Local (P0) -> EastMoney HTTP (P1) -> TQSDK (P2, optional)
- Equity: Tencent HTTP (P0) -> EastMoney HTTP (P1) -> Guosen HTTP (P2, pending)

## 5. Storage Architecture
- Hot cache: MemoryCache (in-process dict, TTL)
- Cold storage: DuckDB (persistent, optional)
