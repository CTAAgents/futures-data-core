from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from datacore import UnifiedDataProvider
from datacore.config import DataCoreConfig
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.payload import DataPayload


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

    # ──────────── api.py 模块级懒加载函数测试 ────────────

    def test_get_futures_lazy_init(self):
        import datacore.api as api_module
        with patch('datacore.api._futures_provider', None), \
             patch('datacore.futures.FuturesDataProvider') as mock_cls:
            provider = api_module._get_futures()
            mock_cls.assert_called_once()
            assert provider == mock_cls.return_value

    def test_get_equity_lazy_init(self):
        import datacore.api as api_module
        with patch('datacore.api._equity_provider', None), \
             patch('datacore.equity.EquityDataProvider') as mock_cls:
            provider = api_module._get_equity()
            mock_cls.assert_called_once()
            assert provider == mock_cls.return_value

    def test_get_news_lazy_init(self):
        import datacore.api as api_module
        with patch('datacore.api._news_provider', None), \
             patch('datacore.news.NewsDataProvider') as mock_cls:
            provider = api_module._get_news()
            mock_cls.assert_called_once()
            assert provider == mock_cls.return_value

    def test_get_macro_lazy_init(self):
        import datacore.api as api_module
        with patch('datacore.api._macro_provider', None), \
             patch('datacore.macro.MacroDataProvider') as mock_cls:
            provider = api_module._get_macro()
            mock_cls.assert_called_once()
            assert provider == mock_cls.return_value

    def test_get_sentiment_llm_lazy_init(self):
        import datacore.api as api_module
        with patch('datacore.api._sentiment_llm', None), \
             patch('datacore.processing.sentiment.sentiment_llm.SentimentLLMStage') as mock_cls:
            provider = api_module._get_sentiment_llm()
            mock_cls.assert_called_once_with(fallback_to_rule=True)
            assert provider == mock_cls.return_value

    def test_get_sentiment_aggregator_lazy_init(self):
        import datacore.api as api_module
        with patch('datacore.api._sentiment_aggregator', None), \
             patch('datacore.processing.sentiment.sentiment_aggregator.SentimentAggregator') as mock_cls:
            provider = api_module._get_sentiment_aggregator()
            mock_cls.assert_called_once()
            assert provider == mock_cls.return_value

    def test_get_market_regime_lazy_init(self):
        import datacore.api as api_module
        with patch('datacore.api._market_regime', None), \
             patch('datacore.processing.market_regime.MarketRegimeDetector') as mock_cls:
            provider = api_module._get_market_regime()
            mock_cls.assert_called_once()
            assert provider == mock_cls.return_value

    # ──────────── 市场行情路由测试 ────────────

    def test_get_futures_route(self):
        """路由到期货市场时返回正确结果"""
        mock_futures = MagicMock()
        mock_futures.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.OHLCV,
            market=MarketType.FUTURES, grade=SourceGrade.PRIMARY,
            data=[{'close': 4000}],
        )
        with patch('datacore.api._get_futures', return_value=mock_futures):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.OHLCV)
            assert payload.available
            assert payload.data == [{'close': 4000}]

    def test_get_equity_route(self):
        """路由到股票市场时返回正确结果"""
        mock_equity = MagicMock()
        mock_equity.get.return_value = DataPayload(
            symbol='600519', data_type=DataType.OHLCV,
            market=MarketType.STOCK, grade=SourceGrade.PRIMARY,
            data=[{'close': 1800}],
        )
        with patch('datacore.api._get_equity', return_value=mock_equity):
            dc = UnifiedDataProvider()
            with patch.object(dc.registry, 'resolve_market', return_value=MarketType.STOCK):
                payload = dc.get('600519', DataType.OHLCV)
            assert payload.available
            assert payload.data == [{'close': 1800}]

    def test_get_futures_payload_none(self):
        """provider 返回 None 时返回 UNAVAILABLE"""
        mock_futures = MagicMock()
        mock_futures.get.return_value = None
        with patch('datacore.api._get_futures', return_value=mock_futures), \
             patch('datacore.api._get_cache', return_value=MagicMock()), \
             patch('datacore.api._get_duckdb', return_value=None):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.OHLCV)
            assert not payload.available
            assert 'does not support' in payload.errors[0]

    # ──────────── NEWS 路由测试 ────────────

    def test_get_news_data_success(self):
        mock_news = MagicMock()
        mock_news.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.NEWS,
            market=MarketType.FUTURES, grade=SourceGrade.PRIMARY,
            data=[{'title': 'news1'}],
        )
        with patch('datacore.api._get_news', return_value=mock_news):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.NEWS)
            assert payload.available
            assert payload.data == [{'title': 'news1'}]

    def test_get_news_data_none(self):
        mock_news = MagicMock()
        mock_news.get.return_value = None
        with patch('datacore.api._get_news', return_value=mock_news):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.NEWS)
            assert not payload.available
            assert 'news provider returned None' in payload.errors[0]

    def test_get_news_data_exception(self):
        with patch('datacore.api._get_news', side_effect=Exception('http error')):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.NEWS)
            assert not payload.available
            assert 'news fetch error' in payload.errors[0]

    # ──────────── MACRO 路由测试 ────────────

    def test_get_macro_data_success(self):
        mock_macro = MagicMock()
        mock_macro.get.return_value = DataPayload(
            symbol='GDP', data_type=DataType.MACRO,
            market=MarketType.FUTURES, grade=SourceGrade.PRIMARY,
            data={'gdp': 5.5},
        )
        with patch('datacore.api._get_macro', return_value=mock_macro):
            dc = UnifiedDataProvider()
            payload = dc.get('GDP', DataType.MACRO, {'indicator': 'gdp'})
            assert payload.available
            assert payload.data == {'gdp': 5.5}
            mock_macro.get.assert_called_once_with(indicator='gdp', params={'indicator': 'gdp'})

    def test_get_macro_data_none(self):
        mock_macro = MagicMock()
        mock_macro.get.return_value = None
        with patch('datacore.api._get_macro', return_value=mock_macro):
            dc = UnifiedDataProvider()
            payload = dc.get('GDP', DataType.MACRO)
            assert not payload.available
            assert 'macro provider returned None' in payload.errors[0]

    def test_get_macro_data_exception(self):
        with patch('datacore.api._get_macro', side_effect=Exception('db error')):
            dc = UnifiedDataProvider()
            payload = dc.get('GDP', DataType.MACRO)
            assert not payload.available
            assert 'macro fetch error' in payload.errors[0]

    # ──────────── SENTIMENT 管线测试 ────────────

    def test_get_sentiment_full_llm(self):
        """LLM 打分 + 聚合 完整流程"""
        mock_news = MagicMock()
        mock_news.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.NEWS,
            market=MarketType.FUTURES, grade=SourceGrade.PRIMARY,
            data=[{'title': 'n1', 'content': 'good'}, {'title': 'n2', 'content': 'bad'}],
        )

        mock_scorer = MagicMock()
        mock_scorer.process.side_effect = [
            {'score': 0.8, 'text': 'positive'},
            {'score': 0.2, 'text': 'negative'},
        ]
        mock_scorer.check_available.return_value = True

        mock_aggregator = MagicMock()
        mock_aggregator.aggregate.return_value = {'avg_score': 0.5, 'count': 2}

        with patch('datacore.api._get_news', return_value=mock_news), \
             patch('datacore.api._get_sentiment_llm', return_value=mock_scorer), \
             patch('datacore.api._get_sentiment_aggregator', return_value=mock_aggregator):

            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.SENTIMENT)

            assert payload.available
            assert payload.data == {'avg_score': 0.5, 'count': 2}
            assert payload.source == 'llm'
            assert payload.grade == SourceGrade.PRIMARY
            assert mock_scorer.process.call_count == 2
            mock_aggregator.aggregate.assert_called_once()

    def test_get_sentiment_rule_fallback(self):
        """LLM 不可用时降级到规则基线"""
        mock_news = MagicMock()
        mock_news.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.NEWS,
            market=MarketType.FUTURES, grade=SourceGrade.PRIMARY,
            data=[{'title': 'test'}],
        )

        mock_scorer = MagicMock()
        mock_scorer.process.return_value = {'score': 0.3}
        mock_scorer.check_available.return_value = False  # LLM 不可用

        mock_aggregator = MagicMock()
        mock_aggregator.aggregate.return_value = {'score': 0.3}

        with patch('datacore.api._get_news', return_value=mock_news), \
             patch('datacore.api._get_sentiment_llm', return_value=mock_scorer), \
             patch('datacore.api._get_sentiment_aggregator', return_value=mock_aggregator):

            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.SENTIMENT)

            assert payload.available
            assert payload.source == 'rule_fallback'
            assert payload.grade == SourceGrade.DAILY

    def test_get_sentiment_no_news(self):
        """新闻不可用时返回 UNAVAILABLE"""
        mock_news = MagicMock()
        mock_news.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.NEWS,
            market=MarketType.FUTURES, grade=SourceGrade.UNAVAILABLE,
        )

        with patch('datacore.api._get_news', return_value=mock_news):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.SENTIMENT)

            assert not payload.available
            assert 'no news data for sentiment' in payload.errors[0]

    def test_get_sentiment_no_items(self):
        """新闻列表包含非 dict 元素时无情绪项产生"""
        mock_news = MagicMock()
        mock_news.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.NEWS,
            market=MarketType.FUTURES, grade=SourceGrade.PRIMARY,
            data=['string_item'],  # 非 dict → isinstnace(dict) 为 False
        )

        with patch('datacore.api._get_news', return_value=mock_news), \
             patch('datacore.api._get_sentiment_llm', return_value=MagicMock()), \
             patch('datacore.api._get_sentiment_aggregator', return_value=MagicMock()):

            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.SENTIMENT)

            assert not payload.available
            assert 'no sentiment items produced' in payload.errors[0]

    def test_get_sentiment_exception(self):
        """情感管道异常时返回 UNAVAILABLE"""
        with patch('datacore.api._get_news', side_effect=RuntimeError('unexpected')):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.SENTIMENT)

            assert not payload.available
            assert 'sentiment error' in payload.errors[0]

    # ──────────── MARKET_STATE 管线测试 ────────────

    def test_get_market_state_full(self):
        """OHLCV → 市场制度检测 完整流程"""
        mock_futures = MagicMock()
        mock_futures.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.OHLCV,
            market=MarketType.FUTURES, grade=SourceGrade.PRIMARY,
            data=[{'close': 4000, 'high': 4050, 'low': 3950}],
        )

        mock_detector = MagicMock()
        mock_detector.process.return_value = {'regime': 'bull', 'confidence': 0.85}

        with patch('datacore.api._get_futures', return_value=mock_futures), \
             patch('datacore.api._get_market_regime', return_value=mock_detector):

            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.MARKET_STATE)

            assert payload.available
            assert payload.data == {'regime': 'bull', 'confidence': 0.85}
            assert payload.source == 'market_regime'
            assert payload.grade == SourceGrade.PRIMARY
            mock_detector.process.assert_called_once()

    def test_get_market_state_no_ohlcv(self):
        """OHLCV 不可用时返回 UNAVAILABLE"""
        mock_futures = MagicMock()
        mock_futures.get.return_value = DataPayload(
            symbol='RB', data_type=DataType.OHLCV,
            market=MarketType.FUTURES, grade=SourceGrade.UNAVAILABLE,
        )

        with patch('datacore.api._get_futures', return_value=mock_futures), \
             patch('datacore.api._get_cache', return_value=MagicMock()), \
             patch('datacore.api._get_duckdb', return_value=None):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.MARKET_STATE)

            assert not payload.available
            assert 'no OHLCV data for market regime' in payload.errors[0]

    def test_get_market_state_exception(self):
        """市场制度管道异常时返回 UNAVAILABLE"""
        with patch('datacore.api._get_futures', side_effect=ValueError('bad data')), \
             patch('datacore.api._get_cache', return_value=MagicMock()), \
             patch('datacore.api._get_duckdb', return_value=None):
            dc = UnifiedDataProvider()
            payload = dc.get('RB', DataType.MARKET_STATE)

            assert not payload.available
            assert 'market regime error' in payload.errors[0]

    # ──────────── get_batch / list_symbols ────────────

    def test_list_symbols_by_market(self):
        dc = UnifiedDataProvider()
        result = dc.list_symbols(market=MarketType.FUTURES)
        assert len(result) > 0
        assert all(item['market'] == 'futures' for item in result)

    def test_list_symbols_by_market_etf(self):
        dc = UnifiedDataProvider()
        result = dc.list_symbols(market=MarketType.ETF)
        assert isinstance(result, list)

    # ──────────── get_health 健康检查 ────────────

    def test_get_health(self):
        """基本健康检查返回格式正确。"""
        dc = UnifiedDataProvider()
        mock_source = MagicMock()
        mock_source.check_available.return_value = True
        mock_provider = MagicMock()
        mock_provider.sources = [mock_source]

        with (
            patch("datacore.api._get_futures", return_value=mock_provider),
            patch("datacore.api._get_equity", return_value=mock_provider),
            patch("datacore.api._get_news", return_value=mock_provider),
            patch("datacore.api._get_macro", return_value=mock_provider),
        ):
            result = dc.get_health()
            assert isinstance(result, dict)
            assert "status" in result
            assert "version" in result
            assert "sources" in result
            assert "timestamp" in result

    def test_get_health_sources(self):
        """健康检查包含各数据源探测结果。"""
        dc = UnifiedDataProvider()
        src_a = MagicMock()
        src_a.check_available.return_value = True
        src_a.name = "tdx_lc"
        src_b = MagicMock()
        src_b.check_available.return_value = False
        src_b.name = "guosen"

        futures_provider = MagicMock()
        futures_provider.sources = [src_a, src_b]
        others = MagicMock()
        others.sources = []

        with (
            patch("datacore.api._get_futures", return_value=futures_provider),
            patch("datacore.api._get_equity", return_value=others),
            patch("datacore.api._get_news", return_value=others),
            patch("datacore.api._get_macro", return_value=others),
        ):
            result = dc.get_health()
            sources = result["sources"]
            assert "tdx_lc" in sources
            assert "guosen" in sources
            assert sources["tdx_lc"]["available"] is True
            assert sources["guosen"]["available"] is False
            assert "latency_ms" in sources["tdx_lc"]

    def test_get_health_version(self):
        """健康检查包含版本信息。"""
        dc = UnifiedDataProvider()
        mock_source = MagicMock()
        mock_source.check_available.return_value = True
        mock_provider = MagicMock()
        mock_provider.sources = [mock_source]

        with (
            patch("datacore.api._get_futures", return_value=mock_provider),
            patch("datacore.api._get_equity", return_value=mock_provider),
            patch("datacore.api._get_news", return_value=mock_provider),
            patch("datacore.api._get_macro", return_value=mock_provider),
        ):
            result = dc.get_health()
            assert result["version"] == "2.0.0"

    def test_get_health_status(self):
        """全源可用时返回 healthy。"""
        dc = UnifiedDataProvider()
        src = MagicMock()
        src.check_available.return_value = True
        mock_provider = MagicMock()
        mock_provider.sources = [src]

        with (
            patch("datacore.api._get_futures", return_value=mock_provider),
            patch("datacore.api._get_equity", return_value=mock_provider),
            patch("datacore.api._get_news", return_value=mock_provider),
            patch("datacore.api._get_macro", return_value=mock_provider),
        ):
            result = dc.get_health()
            assert result["status"] == "healthy"

    def test_get_health_degraded(self):
        """部分源不可用时返回 healthy（任一源可用即算健康）。"""
        dc = UnifiedDataProvider()
        good_src = MagicMock()
        good_src.check_available.return_value = True
        bad_src = MagicMock()
        bad_src.check_available.return_value = False

        futures_provider = MagicMock()
        futures_provider.sources = [bad_src]
        equity_provider = MagicMock()
        equity_provider.sources = [good_src]
        empty = MagicMock()
        empty.sources = []

        with (
            patch("datacore.api._get_futures", return_value=futures_provider),
            patch("datacore.api._get_equity", return_value=equity_provider),
            patch("datacore.api._get_news", return_value=empty),
            patch("datacore.api._get_macro", return_value=empty),
        ):
            result = dc.get_health()
            assert result["status"] == "healthy"
            # 仅 equity 模块返回 available=True
            assert any(v["available"] for v in result["sources"].values())


# ════════════════════════════════════════════════════════════
# DataCoreConfig 配置系统测试
# ════════════════════════════════════════════════════════════

class TestDataCoreConfig:
    """datacore.config 配置系统 100% 覆盖率测试。"""

    # ──── _load_yaml ────

    def test_load_yaml_no_yaml_module(self):
        """HAS_YAML=False 时返回空 dict"""
        with patch('datacore.config.HAS_YAML', False):
            from datacore.config import DataCoreConfig
            config = DataCoreConfig()
            assert config._yaml_config == {}

    def test_load_yaml_success(self):
        """YAML 文件找到并成功加载"""
        yaml_data = {'sources': {'tdx_lc': {'url': 'http://test:17709/'}}}
        with patch('datacore.config.yaml') as mock_yaml:
            mock_yaml.safe_load.return_value = yaml_data
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data='dummy')):
                    from datacore.config import DataCoreConfig
                    config = DataCoreConfig()
                    assert config._yaml_config == yaml_data
                    mock_yaml.safe_load.assert_called_once()

    def test_load_yaml_parse_error(self):
        """YAML 解析异常时跳过该文件"""
        with patch('datacore.config.yaml') as mock_yaml:
            mock_yaml.safe_load.side_effect = Exception('parse error')
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data='bad: data')):
                    from datacore.config import DataCoreConfig
                    config = DataCoreConfig()
                    assert config._yaml_config == {}

    def test_load_yaml_not_found(self):
        """所有配置文件都不存在时返回空 dict"""
        with patch('datacore.config.yaml') as mock_yaml:
            with patch('pathlib.Path.exists', return_value=False):
                from datacore.config import DataCoreConfig
                config = DataCoreConfig()
                assert config._yaml_config == {}
                mock_yaml.safe_load.assert_not_called()

    # ──── _load_env ────

    def test_load_env_reads_prefix(self):
        """仅读取 DATACORE_ 前缀的环境变量"""
        with patch.dict(os.environ, {
            'DATACORE_TDX_URL': 'http://env:17709/',
            'DATACORE_TIMEOUT': '10',
            'OTHER_VAR': 'ignore',
        }, clear=True):
            with patch.object(DataCoreConfig, '_load_yaml', return_value={}):
                config = DataCoreConfig()
                assert config._env_config['tdx_url'] == 'http://env:17709/'
                assert config._env_config['timeout'] == '10'
                assert 'other_var' not in config._env_config

    # ──── _get ────

    def test_get_env_overrides_yaml(self):
        """环境变量优先级高于 yaml"""
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'sources': {'tdx_lc': {'url': 'http://yaml:17709/'}},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            # _get 内部 env_key = key.upper().replace('.', '_')
            config._env_config = {'SOURCES_TDX_LC_URL': 'http://env:17709/'}
            assert config._get('sources.tdx_lc.url') == 'http://env:17709/'

    def test_get_yaml_value(self):
        """无环境变量时读取 yaml 值"""
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'sources': {'tdx_lc': {'url': 'http://yaml:17709/'}},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config._get('sources.tdx_lc.url') == 'http://yaml:17709/'

    def test_get_default_value(self):
        """键不存在时返回默认值"""
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config._get('nonexistent.key', 'fallback') == 'fallback'

    def test_get_none_default(self):
        """无默认值时返回 None"""
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config._get('nonexistent.key') is None

    # ──── property: tdx_url ────

    def test_tdx_url_default(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.tdx_url == 'http://127.0.0.1:17709/'

    def test_tdx_url_from_yaml(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'sources': {'tdx_lc': {'url': 'http://custom:17709/'}},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.tdx_url == 'http://custom:17709/'

    # ──── property: tdx_timeout ────

    def test_tdx_timeout_default(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.tdx_timeout == 3

    def test_tdx_timeout_from_env(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            config._env_config = {'SOURCES_TDX_LC_TIMEOUT': '10'}
            assert config.tdx_timeout == 10

    # ──── property: cache_ttl ────

    def test_cache_ttl_default(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.cache_ttl == 3600

    def test_cache_ttl_from_env(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            config._env_config = {'STORE_CACHE_TTL': '7200'}
            assert config.cache_ttl == 7200

    # ──── property: duckdb_path ────

    def test_duckdb_path_default(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}), \
             patch('os.path.expanduser', side_effect=lambda x: x.replace('~', '/home/user')):
            config = DataCoreConfig()
            assert config.duckdb_path == '/home/user/.datacore/datacore.db'
            assert '~' not in config.duckdb_path

    def test_duckdb_path_from_yaml(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'store': {'duckdb_path': '/custom/path/db.duckdb'},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.duckdb_path == '/custom/path/db.duckdb'

    # ──── property: pg_dsn ────

    def test_pg_dsn_none(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.pg_dsn is None

    # ──── property: redis_url ────

    def test_redis_url_none(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.redis_url is None

    # ──── property: store_backend ────

    def test_store_backend_default(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.store_backend == 'duckdb'

    def test_store_backend_from_yaml(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'store': {'backend': 'postgres'},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.store_backend == 'postgres'

    # ──── property: guosen_api_key ────

    def test_guosen_api_key_none(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.guosen_api_key is None

    def test_guosen_api_key_from_yaml(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'sources': {'guosen': {'api_key': 'test-key-123'}},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.guosen_api_key == 'test-key-123'

    # ──── property: guosen_url ────

    def test_guosen_url_default(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.guosen_url == 'https://api.guosen.com.cn/'

    def test_guosen_url_from_yaml(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'sources': {'guosen': {'url': 'https://custom.guosen.com/'}},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.guosen_url == 'https://custom.guosen.com/'

    # ──── property: guosen_timeout ────

    def test_guosen_timeout_default(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.guosen_timeout == 5

    def test_guosen_timeout_from_yaml(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={
            'sources': {'guosen': {'timeout': '15'}},
        }), patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert config.guosen_timeout == 15

    # ──── __repr__ ────

    def test_repr(self):
        with patch.object(DataCoreConfig, '_load_yaml', return_value={}), \
             patch.object(DataCoreConfig, '_load_env', return_value={}):
            config = DataCoreConfig()
            assert repr(config) == 'DataCoreConfig(backend=duckdb)'

    # ──── get_config 单例 ────

    def test_get_config_singleton(self):
        from datacore.config import get_config, _config_instance
        # 重置单例
        with patch('datacore.config._config_instance', None):
            c1 = get_config()
            c2 = get_config()
            assert c1 is c2
