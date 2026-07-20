"""UnifiedDataProvider - Data-Core unified data entry point."""

from __future__ import annotations
import time
from typing import Any, Optional

from .models.enums import DataType, MarketType, SourceGrade
from .models.payload import DataPayload
from .models.ohlcv import KBar, KlineData
from .registry.symbol_registry import SymbolRegistry
from .issue import IssueRegistry, DataIssue

_futures_provider: Any = None
_equity_provider: Any = None
_news_provider: Any = None
_macro_provider: Any = None
_sentiment_rule: Any = None
_sentiment_llm: Any = None
_sentiment_aggregator: Any = None
_market_regime: Any = None
_breaker_pool: dict[str, Any] = {}


def _get_futures():
    global _futures_provider
    if _futures_provider is None:
        from .futures import FuturesDataProvider
        _futures_provider = FuturesDataProvider()
    return _futures_provider


def _get_equity():
    global _equity_provider
    if _equity_provider is None:
        from .equity import EquityDataProvider
        _equity_provider = EquityDataProvider()
    return _equity_provider


def _get_news():
    global _news_provider
    if _news_provider is None:
        from .news import NewsDataProvider
        _news_provider = NewsDataProvider()
    return _news_provider


def _get_macro():
    global _macro_provider
    if _macro_provider is None:
        from .macro import MacroDataProvider
        _macro_provider = MacroDataProvider()
    return _macro_provider


def _get_sentiment_llm():
    """获取情绪打分器（LLM 优先，降级到规则基线）。"""
    global _sentiment_llm
    if _sentiment_llm is None:
        from .processing.sentiment.sentiment_llm import SentimentLLMStage
        _sentiment_llm = SentimentLLMStage(fallback_to_rule=True)
    return _sentiment_llm


def _get_sentiment_aggregator():
    global _sentiment_aggregator
    if _sentiment_aggregator is None:
        from .processing.sentiment.sentiment_aggregator import SentimentAggregator
        _sentiment_aggregator = SentimentAggregator()
    return _sentiment_aggregator


def _get_market_regime():
    global _market_regime
    if _market_regime is None:
        from .processing.market_regime import MarketRegimeDetector
        _market_regime = MarketRegimeDetector()
    return _market_regime


def _get_breaker(name: str) -> Any:
    if name not in _breaker_pool:
        from .breaker import Breaker
        _breaker_pool[name] = Breaker(name)
    return _breaker_pool[name]


_cache: Any = None
_duckdb_store: Any = None


def _get_cache():
    global _cache
    if _cache is None:
        from .store.cache import MemoryCache
        _cache = MemoryCache()
    return _cache


def _get_duckdb():
    global _duckdb_store
    if _duckdb_store is None:
        try:
            from .store.duckdb import DuckDBStore
            _duckdb_store = DuckDBStore()
            _duckdb_store.init_schema()
        except ImportError:
            _duckdb_store = None
    return _duckdb_store


class UnifiedDataProvider:
    """Data-Core unified data entry point.

    All consumers obtain data through this interface,
    automatically routing to futures or equity modules.
    """

    def __init__(self):
        self.registry = SymbolRegistry()
        self._issues = IssueRegistry()

    def get(self, symbol: str, data_type: DataType,
            params: dict | None = None) -> DataPayload:
        """Fetch data for the given symbol and type."""
        collected_at = time.time()

        # ── 数据加工层路由（v0.3.0 新增）──
        if data_type == DataType.SENTIMENT:
            return self._get_sentiment(symbol, params, collected_at)
        if data_type == DataType.MARKET_STATE:
            return self._get_market_state(symbol, params, collected_at)
        if data_type == DataType.NEWS:
            return self._get_news_data(symbol, params, collected_at)
        if data_type == DataType.MACRO:
            return self._get_macro_data(symbol, params, collected_at)

        # ── 市场行情数据路由 ──
        market = self.registry.resolve_market(symbol)
        if market is None:
            return DataPayload(
                symbol=symbol, data_type=data_type,
                market=MarketType.FUTURES,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"Unknown symbol: {symbol}"],
            )

        # ── 缓存层（v0.5.0: MemoryCache → DuckDB）──
        cache_key = f"{symbol}:{data_type.value}:{self._cache_params_key(params)}"
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached

        payload: Optional[DataPayload] = None

        if market == MarketType.FUTURES:
            payload = _get_futures().get(symbol, data_type, params)
        elif market in (MarketType.STOCK, MarketType.ETF,
                        MarketType.CB, MarketType.REIT):
            payload = _get_equity().get(symbol, data_type, params, market=market)

        if payload is None:
            return DataPayload(
                symbol=symbol, data_type=data_type, market=market,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"{market} module does not support {data_type}"],
                collected_at=collected_at,
            )

        # ── 缓存写回（v0.5.0）──
        if payload.available:
            self._write_cache(cache_key, payload)

        return payload

    def _get_news_data(self, symbol: str, params: dict | None,
                       collected_at: float) -> DataPayload:
        """获取新闻资讯（已分类，携带 tags）。"""
        try:
            provider = _get_news()
            payload = provider.get(symbol, params)
            if payload is None:
                return DataPayload(
                    symbol=symbol, data_type=DataType.NEWS,
                    market=MarketType.FUTURES,
                    grade=SourceGrade.UNAVAILABLE,
                    errors=["news provider returned None"],
                    collected_at=collected_at,
                )
            return payload
        except Exception as e:
            return DataPayload(
                symbol=symbol, data_type=DataType.NEWS,
                market=MarketType.FUTURES,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"news fetch error: {e}"],
                collected_at=collected_at,
            )

    def _get_macro_data(self, symbol: str, params: dict | None,
                        collected_at: float) -> DataPayload:
        """获取宏观数据。"""
        try:
            provider = _get_macro()
            indicator = (params or {}).get("indicator")
            payload = provider.get(indicator=indicator, params=params)
            if payload is None:
                return DataPayload(
                    symbol=symbol, data_type=DataType.MACRO,
                    market=MarketType.FUTURES,
                    grade=SourceGrade.UNAVAILABLE,
                    errors=["macro provider returned None"],
                    collected_at=collected_at,
                )
            return payload
        except Exception as e:
            return DataPayload(
                symbol=symbol, data_type=DataType.MACRO,
                market=MarketType.FUTURES,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"macro fetch error: {e}"],
                collected_at=collected_at,
            )

    def _get_sentiment(self, symbol: str, params: dict | None,
                       collected_at: float) -> DataPayload:
        """获取情绪数据（已打分+聚合）— Data-Core 数据加工层产出。

        流程: 获取 NEWS → 情绪打分（LLM 优先，降级规则）→ 聚合
        """
        params = params or {}

        try:
            # Step 1: 获取新闻
            news_payload = _get_news().get(symbol, params)
            if not news_payload.available or not news_payload.data:
                return DataPayload(
                    symbol=symbol, data_type=DataType.SENTIMENT,
                    market=MarketType.FUTURES,
                    grade=SourceGrade.UNAVAILABLE,
                    errors=["no news data for sentiment"],
                    collected_at=collected_at,
                )

            # Step 2: 情绪打分
            scorer = _get_sentiment_llm()
            news_list = news_payload.data if isinstance(news_payload.data, list) else []
            sentiment_items = []
            for news_item in news_list:
                if isinstance(news_item, dict):
                    item = scorer.process(news_item, symbol)
                    sentiment_items.append(item)

            if not sentiment_items:
                return DataPayload(
                    symbol=symbol, data_type=DataType.SENTIMENT,
                    market=MarketType.FUTURES,
                    grade=SourceGrade.UNAVAILABLE,
                    errors=["no sentiment items produced"],
                    collected_at=collected_at,
                )

            # Step 3: 聚合
            aggregator = _get_sentiment_aggregator()
            sentiment_data = aggregator.aggregate(
                sentiment_items, symbol=symbol, params=params
            )

            # 确定数据质量等级
            if scorer.check_available():
                grade = SourceGrade.PRIMARY
                source = "llm"
            else:
                grade = SourceGrade.DAILY
                source = "rule_fallback"

            return DataPayload(
                symbol=symbol, data_type=DataType.SENTIMENT,
                market=MarketType.FUTURES,
                data=sentiment_data,
                source=source,
                grade=grade,
                collected_at=collected_at,
            )
        except Exception as e:
            return DataPayload(
                symbol=symbol, data_type=DataType.SENTIMENT,
                market=MarketType.FUTURES,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"sentiment error: {e}"],
                collected_at=collected_at,
            )

    def _get_market_state(self, symbol: str, params: dict | None,
                          collected_at: float) -> DataPayload:
        """获取市场制度状态 — Data-Core 数据加工层产出。

        流程: 获取 OHLCV → 市场制度检测
        """
        params = params or {}

        try:
            # Step 1: 获取 OHLCV 数据
            ohlcv_payload = self.get(symbol, DataType.OHLCV, params)
            if not ohlcv_payload.available or not ohlcv_payload.data:
                return DataPayload(
                    symbol=symbol, data_type=DataType.MARKET_STATE,
                    market=MarketType.FUTURES,
                    grade=SourceGrade.UNAVAILABLE,
                    errors=["no OHLCV data for market regime"],
                    collected_at=collected_at,
                )

            # Step 2: 市场制度检测
            detector = _get_market_regime()
            market_state = detector.process(
                ohlcv_payload.data, symbol=symbol, params=params
            )

            return DataPayload(
                symbol=symbol, data_type=DataType.MARKET_STATE,
                market=MarketType.FUTURES,
                data=market_state,
                source="market_regime",
                grade=SourceGrade.PRIMARY,
                collected_at=collected_at,
            )
        except Exception as e:
            return DataPayload(
                symbol=symbol, data_type=DataType.MARKET_STATE,
                market=MarketType.FUTURES,
                grade=SourceGrade.UNAVAILABLE,
                errors=[f"market regime error: {e}"],
                collected_at=collected_at,
            )

    # ─────────────────────────────────────────────────────────
    # 缓存层辅助方法（v0.5.0: MemoryCache → DuckDB → HTTP）
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _cache_params_key(params: dict | None) -> str:
        """生成缓存参数键，只取关键参数排序后拼接。"""
        if not params:
            return "default"
        keys = sorted(params.keys())
        return ":".join(f"{k}={params[k]}" for k in keys)

    def _check_cache(self, cache_key: str) -> Optional[DataPayload]:
        """MemoryCache → DuckDB 顺序检查。"""
        # L1: MemoryCache
        mem = _get_cache()
        cached = mem.get(cache_key)
        if cached is not None and isinstance(cached, dict):
            try:
                dp = DataPayload(**cached)
                dp.grade = SourceGrade.CACHED
                return dp
            except (TypeError, ValueError):
                pass

        # L2: DuckDB（仅对 OHLCV 类型生效）
        if _get_duckdb() is not None:
            try:
                parts = cache_key.split(":")
                if len(parts) >= 3 and parts[1] == "ohlcv":
                    symbol = parts[0]
                    period = "daily"
                    for seg in parts[2:]:
                        if seg.startswith("period="):
                            period = seg.split("=", 1)[1]
                            break
                    db = _get_duckdb()
                    rows = db.load_kline(symbol, period, days=120)
                    if rows:
                        bars_data = [
                            {k: r[k] for k in ("date", "open", "high", "low",
                                                "close", "volume", "amount")}
                            for r in rows
                        ]
                        bars = [KBar(**b) for b in bars_data]
                        if bars:
                            kd = KlineData(symbol=symbol, period=period,
                                           bars=bars, source="duckdb_cache")
                            return DataPayload(
                                symbol=symbol, data_type=DataType.OHLCV,
                                market=MarketType.FUTURES,
                                data=kd, source="duckdb_cache",
                                grade=SourceGrade.CACHED,
                                collected_at=time.time(),
                            )
            except Exception:
                pass

        return None

    def _write_cache(self, cache_key: str, payload: DataPayload) -> None:
        """写入 MemoryCache + DuckDB。"""
        if not payload.available:
            return

        # L1: MemoryCache
        import dataclasses
        mem = _get_cache()
        mem.set(cache_key, dataclasses.asdict(payload))

        # L2: DuckDB（仅对 OHLCV 类型生效）
        db = _get_duckdb()
        if db is not None and payload.data_type == DataType.OHLCV and hasattr(payload.data, "bars"):
            try:
                bars_dict = [dataclasses.asdict(b) for b in payload.data.bars]
                period = getattr(payload.data, "period", "daily")
                db.store_kline(payload.symbol, period, bars_dict)
            except Exception:
                pass

    def get_batch(self, symbols: list[str], data_type: DataType,
                  params: dict | None = None) -> dict[str, DataPayload]:
        """Batch fetch data for multiple symbols."""
        return {sym: self.get(sym, data_type, params) for sym in symbols}

    def report_issue(self, issue: DataIssue) -> dict:
        """上报消费者反馈的数据问题。

        Args:
            issue: 数据问题实例

        Returns:
            包含上报结果和自动应对措施的 dict
        """
        return self._issues.report(issue)

    def get_f10(self, symbol: str) -> DataPayload:
        """F10 综合报告。聚合期限结构/价差/基差/仓单/持仓排名等子模块。"""
        from .api_f10 import get_f10_sync
        return get_f10_sync(self, symbol)

    def list_symbols(self, market: MarketType | None = None) -> list[dict]:
        """List all available symbols."""
        if market:
            return [
                {"symbol": e.symbol, "name": e.name, "market": e.market.value}
                for e in self.registry.list_by_market(market)
            ]
        return [
            {"symbol": e.symbol, "name": e.name, "market": e.market.value}
            for e in self.registry.list_all()
        ]

    def get_health(self) -> dict:
        """检查所有数据源健康状态。

        遍历所有模块并探测各数据源可用性及延迟，返回结构化健康报告。
        """
        sources: dict[str, dict] = {}

        # ── 期货模块 ──
        for s in _get_futures().sources:
            sources[s.name] = self._probe_source(s)

        # ── A 股模块 ──
        for s in _get_equity().sources:
            sources[s.name] = self._probe_source(s)

        # ── 新闻模块 ──
        for s in _get_news().sources:
            sources[s.name] = self._probe_source(s)

        # ── 宏观模块 ──
        for s in _get_macro().sources:
            sources[s.name] = self._probe_source(s)

        # ── 缓存层状态（v0.5.0）──
        sources["memory_cache"] = {
            "available": True,
            "latency_ms": 0,
            "grade": "active",
        }
        db = _get_duckdb()
        sources["duckdb_cache"] = {
            "available": db is not None,
            "latency_ms": 0,
            "grade": "active" if db is not None else "unavailable",
        }

        any_ok = any(v.get("available", False) for v in sources.values())
        return {
            "status": "healthy" if any_ok else "unavailable",
            "version": "2.0.0",
            "sources": sources,
            "consumer_issues": self._issues.stats(),
            "timestamp": time.time(),
        }

    @staticmethod
    def _probe_source(source: Any) -> dict:
        """探测单个数据源并返回可用性及延迟。"""
        t0 = time.time()
        try:
            ok = source.check_available()
        except Exception:
            ok = False
        elapsed = round((time.time() - t0) * 1000, 1)
        return {"available": ok, "latency_ms": elapsed}
