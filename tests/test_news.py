"""news 模块测试。"""

import pytest
from unittest.mock import patch, MagicMock
from datacore.news.models import NewsItem, NewsData
from datacore.news.news_provider import NewsDataProvider
from datacore.news.providers.base import NewsDataSource
from datacore.news.providers.cls import ClsProvider
from datacore.news.providers.wallstreet_cn import WallStreetCnProvider
from datacore.news.providers.eastmoney_research import EastMoneyResearchProvider
from datacore.news.classifier import NewsClassifier
from datacore.models.enums import DataType, MarketType, SourceGrade


# ── NewsData 模型测试 ──

class TestNewsData:
    """datacore.news.models"""

    def test_filter_by_tag_matches(self):
        """filter_by_tag 返回匹配标签的条目。"""
        data = NewsData(
            items=[
                NewsItem(title="a", tags=["macro"]),
                NewsItem(title="b", tags=["industry"]),
                NewsItem(title="c", tags=["macro", "policy"]),
            ],
        )
        result = data.filter_by_tag("macro")
        assert len(result) == 2
        assert result[0].title == "a"
        assert result[1].title == "c"

    def test_filter_by_tag_no_match(self):
        """filter_by_tag 无匹配时返回空列表。"""
        data = NewsData(items=[NewsItem(title="a", tags=["industry"])])
        result = data.filter_by_tag("macro")
        assert result == []

    def test_filter_by_symbol_matches(self):
        """filter_by_symbol 按符号过滤。"""
        data = NewsData(
            items=[
                NewsItem(title="a", related_symbols=["RB", "HC"]),
                NewsItem(title="b", related_symbols=["I"]),
                NewsItem(title="c", related_symbols=["RB"]),
            ],
        )
        result = data.filter_by_symbol("RB")
        assert len(result) == 2
        assert result[0].title == "a"
        assert result[1].title == "c"

    def test_filter_by_symbol_case_insensitive(self):
        """filter_by_symbol 不区分大小写。"""
        data = NewsData(
            items=[NewsItem(title="a", related_symbols=["RB"])],
        )
        result = data.filter_by_symbol("rb")
        assert len(result) == 1

    def test_filter_by_symbol_no_match(self):
        """filter_by_symbol 无匹配时返回空列表。"""
        data = NewsData(items=[NewsItem(title="a", related_symbols=["HC"])])
        result = data.filter_by_symbol("RB")
        assert result == []


# ── 基类测试 ──

class TestNewsDataSourceBase:
    """datacore.news.providers.base"""

    def test_abstract_method_raises(self):
        """fetch_news 是抽象方法，直接调用应抛 TypeError。"""
        with pytest.raises(TypeError):
            NewsDataSource()

    def test_concrete_subclass_must_implement_fetch_news(self):
        """未实现 fetch_news 的子类无法实例化。"""
        class Incomplete(NewsDataSource):
            pass
        with pytest.raises(TypeError):
            Incomplete()

    def test_check_available_default(self):
        """默认 check_available 返回 True。"""
        class Concrete(NewsDataSource):
            def fetch_news(self, symbol=None, days=7, limit=50):
                return None
        inst = Concrete()
        assert inst.check_available() is True

    def test_name_and_priority_defaults(self):
        """name 和 priority 有默认值。"""
        class Concrete(NewsDataSource):
            def fetch_news(self, symbol=None, days=7, limit=50):
                return None
        inst = Concrete()
        assert inst.name == ""
        assert inst.priority == 99


# ── ClsProvider 测试 ──

class TestClsProvider:
    """datacore.news.providers.cls"""

    MOCK_ROLL_DATA = [
        {"title": "标题1", "content": "内容1", "ctime": "2026-07-18 10:00", "id": "111"},
        {"title": "标题2", "content": "内容2", "ctime": "2026-07-18 09:00", "id": "222"},
    ]

    @pytest.fixture
    def provider(self):
        return ClsProvider()

    def test_name_and_priority(self, provider):
        assert provider.name == "cls"
        assert provider.priority == 0

    def test_fetch_news_success(self, provider):
        """成功获取财联社快讯。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"roll_data": self.MOCK_ROLL_DATA}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()

        assert result is not None
        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0].title == "标题1"
        assert result.items[0].source == "cls"
        assert result.items[0].url == "https://www.cls.cn/detail/111"
        assert result.items[1].title == "标题2"

    def test_fetch_news_with_symbol(self, provider):
        """带 symbol 参数获取新闻。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"roll_data": self.MOCK_ROLL_DATA}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news(symbol="RB")

        assert result is not None
        assert result.symbol == "RB"

    def test_fetch_news_limit(self, provider):
        """limit 参数正确传递。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"roll_data": self.MOCK_ROLL_DATA * 10}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            provider.fetch_news(limit=5)

            call_kwargs = mock_instance.get.call_args[1]
            assert call_kwargs["params"]["rn"] == 5

    def test_fetch_news_http_error_returns_none(self, provider):
        """HTTP 请求异常返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.side_effect = Exception("Connection error")
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_json_error_returns_none(self, provider):
        """JSON 解析异常返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.side_effect = ValueError("Invalid JSON")
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_empty_data_returns_none(self, provider):
        """返回空数据时返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"roll_data": []}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_missing_data_returns_none(self, provider):
        """response 不含 data 字段时返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_preserves_title_content(self, provider):
        """解析结果保留标题/内容/来源/URL。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "data": {
                    "roll_data": [
                        {"title": "标题A", "content": "内容A", "ctime": "now", "id": "1"},
                    ]
                }
            }
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is not None
        assert result.items[0].title == "标题A"
        assert result.items[0].content == "内容A"
        assert result.items[0].url == "https://www.cls.cn/detail/1"

    def test_fetch_news_all_items_skip(self, provider):
        """所有条目解析失败时（item 不是 dict）返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"roll_data": [None]}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_check_available_success(self, provider):
        """站点可达时返回 True。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.head.return_value = mock_resp
            mock_client.return_value = mock_instance

            assert provider.check_available() is True

    def test_check_available_connection_error(self, provider):
        """网络异常时返回 False。"""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.head.side_effect = Exception("Timeout")
            mock_client.return_value = mock_instance

            assert provider.check_available() is False


# ── WallStreetCnProvider 测试 ──

class TestWallStreetCnProvider:
    """datacore.news.providers.wallstreet_cn"""

    MOCK_ITEMS = [
        {
            "title": "华尔街标题1",
            "content_text": "华尔街内容1",
            "display_time": "2026-07-18 10:00",
            "uri": "https://wallstreetcn.com/111",
        },
        {
            "title": "华尔街标题2",
            "display_time": "2026-07-18 09:00",
            "uri": "https://wallstreetcn.com/222",
        },
    ]

    @pytest.fixture
    def provider(self):
        return WallStreetCnProvider()

    def test_name_and_priority(self, provider):
        assert provider.name == "wallstreet_cn"
        assert provider.priority == 1

    def test_fetch_news_success(self, provider):
        """成功获取华尔街见闻新闻。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"items": self.MOCK_ITEMS}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()

        assert result is not None
        assert result.total == 2
        assert result.items[0].title == "华尔街标题1"
        assert result.items[0].content == "华尔街内容1"
        assert result.items[0].source == "wallstreet_cn"
        assert result.items[0].url == "https://wallstreetcn.com/111"
        # content_text 不存在时回退到 title
        assert result.items[1].content == "华尔街标题2"

    def test_fetch_news_http_error_returns_none(self, provider):
        """HTTP 请求异常返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.side_effect = Exception("Connection error")
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_empty_data_returns_none(self, provider):
        """返回空数据时返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"items": []}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_missing_data_returns_none(self, provider):
        """response 不含 data 字段时返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_preserves_title_content(self, provider):
        """解析结果保留标题/内容/来源/URL。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "data": {
                    "items": [
                        {"title": "标题A", "content_text": "内容A", "display_time": "now", "uri": "url1"},
                    ]
                }
            }
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is not None
        assert result.items[0].title == "标题A"
        assert result.items[0].content == "内容A"
        assert result.items[0].url == "url1"

    def test_fetch_news_all_items_skip(self, provider):
        """所有条目解析失败时（item 不是 dict）返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"items": [None]}}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_check_available_success(self, provider):
        """站点可达时返回 True。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.head.return_value = mock_resp
            mock_client.return_value = mock_instance

            assert provider.check_available() is True

    def test_check_available_connection_error(self, provider):
        """网络异常时返回 False。"""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.head.side_effect = Exception("Timeout")
            mock_client.return_value = mock_instance

            assert provider.check_available() is False


# ── EastMoneyResearchProvider 测试 ──

class TestEastMoneyResearchProvider:
    """datacore.news.providers.eastmoney_research"""

    MOCK_DATA = [
        {
            "title": "研报标题1",
            "content": "研报内容1",
            "publishDate": "2026-07-18",
            "encodeUrl": "abc123",
            "orgSName": "中信证券",
        },
        {
            "title": "研报标题2",
            "s3": "研报摘要2",
            "publishDate": "2026-07-17",
            "encodeUrl": "def456",
            "orgSName": "华泰证券",
        },
    ]

    @pytest.fixture
    def provider(self):
        return EastMoneyResearchProvider()

    def test_name_and_priority(self, provider):
        assert provider.name == "eastmoney_research"
        assert provider.priority == 2

    def test_fetch_news_success(self, provider):
        """成功获取东方财富研报。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": self.MOCK_DATA}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()

        assert result is not None
        assert result.total == 2
        assert result.items[0].title == "研报标题1"
        assert result.items[0].content == "研报内容1"
        assert result.items[0].source == "eastmoney_中信证券"
        assert "abc123" in result.items[0].url
        # content 不存在时回退到 s3
        assert result.items[1].content == "研报摘要2"

    def test_fetch_news_http_error_returns_none(self, provider):
        """HTTP 请求异常返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.side_effect = Exception("Connection error")
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_empty_data_returns_none(self, provider):
        """返回空数据时返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": []}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_missing_data_returns_none(self, provider):
        """response 不含 data 字段时返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_fetch_news_preserves_title_content(self, provider):
        """解析结果保留标题/内容/来源/URL。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "data": [
                    {"title": "标题A", "content": "内容A", "publishDate": "now", "encodeUrl": "xyz", "orgSName": "券商"},
                ]
            }
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is not None
        assert result.items[0].title == "标题A"
        assert result.items[0].content == "内容A"
        assert result.items[0].source == "eastmoney_券商"
        assert "xyz" in result.items[0].url

    def test_fetch_news_all_items_skip(self, provider):
        """所有条目解析失败时（item 不是 dict）返回 None。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": [None]}
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_resp
            mock_client.return_value = mock_instance

            result = provider.fetch_news()
        assert result is None

    def test_check_available_success(self, provider):
        """站点可达时返回 True。"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.head.return_value = mock_resp
            mock_client.return_value = mock_instance

            assert provider.check_available() is True

    def test_check_available_connection_error(self, provider):
        """网络异常时返回 False。"""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.head.side_effect = Exception("Timeout")
            mock_client.return_value = mock_instance

            assert provider.check_available() is False


# ── NewsDataProvider 测试 ──

class TestNewsDataProvider:
    """datacore.news.news_provider"""

    @pytest.fixture
    def mock_news_data(self):
        return NewsData(
            symbol="RB",
            total=2,
            items=[
                NewsItem(title="新闻1", content="央行降息", tags=["macro"]),
                NewsItem(title="新闻2", content="钢铁产量增加", tags=["industry"]),
            ],
        )

    @pytest.fixture
    def provider_with_mocks(self):
        """创建一个 NewsDataProvider，内部 sources 被替换为 mock。"""
        with patch("datacore.news.providers.cls.ClsProvider"), \
             patch("datacore.news.providers.wallstreet_cn.WallStreetCnProvider"), \
             patch("datacore.news.providers.eastmoney_research.EastMoneyResearchProvider"):
            provider = NewsDataProvider()
        # 替换为 mock sources
        mock_src0 = MagicMock()
        mock_src0.name = "cls"
        mock_src0.priority = 0
        mock_src0.check_available.return_value = True

        mock_src1 = MagicMock()
        mock_src1.name = "wallstreet_cn"
        mock_src1.priority = 1
        mock_src1.check_available.return_value = True

        mock_src2 = MagicMock()
        mock_src2.name = "eastmoney_research"
        mock_src2.priority = 2
        mock_src2.check_available.return_value = True

        provider.sources = [mock_src0, mock_src1, mock_src2]
        return provider, [mock_src0, mock_src1, mock_src2]

    # ── _init_sources ──

    def test_init_sources_loads_all_providers(self):
        """_init_sources 加载所有 4 个数据源。"""
        with patch("datacore.news.providers.jin10.Jin10Provider"), \
             patch("datacore.news.providers.cls.ClsProvider"), \
             patch("datacore.news.providers.wallstreet_cn.WallStreetCnProvider"), \
             patch("datacore.news.providers.eastmoney_research.EastMoneyResearchProvider"):
            provider = NewsDataProvider()
        assert len(provider.sources) == 4

    def test_init_sources_handles_partial_failure(self):
        """部分数据源构造失败时不影响其余。"""
        with patch("datacore.news.providers.jin10.Jin10Provider"), \
             patch("datacore.news.providers.cls.ClsProvider"), \
             patch("datacore.news.providers.wallstreet_cn.WallStreetCnProvider", side_effect=Exception("fail")), \
             patch("datacore.news.providers.eastmoney_research.EastMoneyResearchProvider"):
            provider = NewsDataProvider()
        assert len(provider.sources) == 3

    def test_init_sources_handles_all_failure(self):
        """所有数据源构造失败时 sources 为空。"""
        with patch("datacore.news.providers.jin10.Jin10Provider", side_effect=Exception("fail")), \
             patch("datacore.news.providers.cls.ClsProvider", side_effect=Exception("fail")), \
             patch("datacore.news.providers.wallstreet_cn.WallStreetCnProvider", side_effect=Exception("fail")), \
             patch("datacore.news.providers.eastmoney_research.EastMoneyResearchProvider", side_effect=Exception("fail")):
            provider = NewsDataProvider()
        assert len(provider.sources) == 0

    # ── get ──

    def test_get_success(self, provider_with_mocks, mock_news_data):
        """get 成功路径：第一可用 source 返回数据。"""
        provider, mocks = provider_with_mocks
        mocks[0].fetch_news.return_value = mock_news_data

        result = provider.get(symbol="RB")

        assert result is not None
        assert result.symbol == "RB"
        assert result.data_type == DataType.NEWS
        assert result.market == MarketType.FUTURES
        assert result.source == "cls"
        assert result.data is mock_news_data
        assert result.available is True

    def test_get_falls_back_to_next_source(self, provider_with_mocks, mock_news_data):
        """第一个 source 不可用时回退到第二个。"""
        provider, mocks = provider_with_mocks
        mocks[0].check_available.return_value = False
        mocks[1].fetch_news.return_value = mock_news_data

        result = provider.get()

        mocks[0].fetch_news.assert_not_called()
        assert result.source == "wallstreet_cn"

    def test_get_all_unavailable(self, provider_with_mocks):
        """所有 source 不可用时返回 UNAVAILABLE。"""
        provider, mocks = provider_with_mocks
        for m in mocks:
            m.check_available.return_value = False

        result = provider.get()

        assert result.grade == SourceGrade.UNAVAILABLE
        assert "所有新闻源不可用" in result.errors

    def test_get_source_returns_none_continues(self, provider_with_mocks, mock_news_data):
        """source 返回 None 时继续下一个。"""
        provider, mocks = provider_with_mocks
        mocks[0].fetch_news.return_value = None
        mocks[1].fetch_news.return_value = mock_news_data

        result = provider.get()

        assert result.source == "wallstreet_cn"

    def test_get_source_exception_continues(self, provider_with_mocks, mock_news_data):
        """source 抛出异常时继续下一个。"""
        provider, mocks = provider_with_mocks
        mocks[0].fetch_news.side_effect = Exception("Fetch error")
        mocks[1].fetch_news.return_value = mock_news_data

        result = provider.get()

        assert result.source == "wallstreet_cn"

    def test_get_with_symbol_success(self, provider_with_mocks):
        """带 symbol 参数，新闻项应追加 related_symbols。"""
        provider, mocks = provider_with_mocks
        news_data = NewsData(
            symbol="RB",
            total=1,
            items=[NewsItem(title="新闻", content="内容", tags=["macro"])],
        )
        mocks[0].fetch_news.return_value = news_data

        result = provider.get(symbol="RB")

        assert result.data.items[0].related_symbols == ["RB"]

    def test_get_with_categories_filter(self, provider_with_mocks):
        """categories 过滤只保留匹配标签的新闻。"""
        provider, mocks = provider_with_mocks
        news_data = NewsData(
            total=3,
            items=[
                NewsItem(title="宏观", content="央行消息", tags=["macro"]),
                NewsItem(title="产业", content="钢铁产量", tags=["industry"]),
                NewsItem(title="政策", content="新政策", tags=["policy"]),
            ],
        )
        mocks[0].fetch_news.return_value = news_data

        result = provider.get(params={"categories": ["macro", "policy"]})

        assert len(result.data.items) == 2
        assert result.data.items[0].title == "宏观"
        assert result.data.items[1].title == "政策"

    def test_get_with_categories_empty_filter(self, provider_with_mocks):
        """categories 过滤后无结果时 items 为空。"""
        provider, mocks = provider_with_mocks
        news_data = NewsData(
            total=2,
            items=[
                NewsItem(title="宏观", content="央行消息", tags=["macro"]),
                NewsItem(title="产业", content="钢铁产量", tags=["industry"]),
            ],
        )
        mocks[0].fetch_news.return_value = news_data

        result = provider.get(params={"categories": ["company"]})

        assert len(result.data.items) == 0

    def test_get_classifier_called_for_items_without_tags(self, provider_with_mocks):
        """tags 为空的新闻项会被分类器自动打标签。"""
        provider, mocks = provider_with_mocks
        news_data = NewsData(
            total=1,
            items=[NewsItem(title="央行降息", content="LPR下调")],
        )
        mocks[0].fetch_news.return_value = news_data

        result = provider.get()

        assert "macro" in result.data.items[0].tags

    def test_get_with_params(self, provider_with_mocks, mock_news_data):
        """params 中的参数正确传递。"""
        provider, mocks = provider_with_mocks
        mocks[0].fetch_news.return_value = mock_news_data

        provider.get(params={"days": 3, "limit": 10})

        mocks[0].fetch_news.assert_called_once_with(symbol=None, days=3, limit=10)

    def test_get_default_params(self, provider_with_mocks, mock_news_data):
        """未传 params 时使用默认值。"""
        provider, mocks = provider_with_mocks
        mocks[0].fetch_news.return_value = mock_news_data

        provider.get()

        mocks[0].fetch_news.assert_called_once_with(symbol=None, days=7, limit=50)

    def test_get_data_empty_continues(self, provider_with_mocks):
        """source 返回 items 为空的 NewsData 时继续下一个。"""
        provider, mocks = provider_with_mocks
        empty_data = NewsData(symbol="RB", total=0, items=[])
        mocks[0].fetch_news.return_value = empty_data
        mocks[1].check_available.return_value = False
        mocks[2].check_available.return_value = False

        result = provider.get()

        assert result.grade == SourceGrade.UNAVAILABLE


# ── NewsClassifier 测试 ──

class TestNewsClassifier:
    """datacore.news.classifier"""

    @pytest.fixture
    def classifier(self):
        return NewsClassifier()

    # ── classify ──

    def test_classify_macro(self, classifier):
        """宏观关键词匹配。"""
        result = classifier.classify("央行降息")
        assert "macro" in result

    def test_classify_policy(self, classifier):
        """政策关键词匹配。"""
        result = classifier.classify("证监会新规")
        assert "policy" in result

    def test_classify_industry(self, classifier):
        """产业关键词匹配。"""
        result = classifier.classify("钢铁产量增加")
        assert "industry" in result

    def test_classify_company(self, classifier):
        """公司关键词匹配。"""
        result = classifier.classify("公司营收增长")
        assert "company" in result

    def test_classify_empty_text(self, classifier):
        """空文本返回空列表。"""
        assert classifier.classify("") == []

    def test_classify_no_match(self, classifier):
        """无匹配关键词返回空列表。"""
        assert classifier.classify("不相关的内容") == []

    def test_classify_multiple_categories(self, classifier):
        """文本匹配多个分类。"""
        result = classifier.classify("央行降息 钢铁产量")
        assert "macro" in result
        assert "industry" in result

    # ── classify_item ──

    def test_classify_item_title_only(self, classifier):
        """仅标题匹配。"""
        result = classifier.classify_item(title="央行降息")
        assert "macro" in result

    def test_classify_item_title_and_content(self, classifier):
        """标题和正文组合匹配。"""
        result = classifier.classify_item(title="标题", content="证监会新规出炉")
        assert "policy" in result

    # ── __init__ with custom_keywords ──

    def test_init_custom_keywords_extend_existing(self):
        """custom_keywords 扩展已有分类关键词。"""
        c = NewsClassifier(custom_keywords={"macro": ["新增关键词"]})
        result = c.classify("新增关键词")
        assert "macro" in result

    def test_init_custom_keywords_new_category(self):
        """custom_keywords 新增分类。"""
        c = NewsClassifier(custom_keywords={"custom_cat": ["专属词汇"]})
        result = c.classify("专属词汇")
        assert "custom_cat" in result

    # ── extract_symbols ──

    def test_extract_symbols_empty_text(self, classifier):
        """空文本返回空列表。"""
        assert classifier.extract_symbols("", ["RB"]) == []

    def test_extract_symbols_empty_symbol_list(self, classifier):
        """空 symbol_list 返回空列表。"""
        assert classifier.extract_symbols("螺纹钢", []) == []

    def test_extract_symbols_found(self, classifier):
        """从文本中提取到匹配的品种符号。"""
        result = classifier.extract_symbols("螺纹钢RB主力合约", ["RB", "HC"])
        assert result == ["RB"]

    def test_extract_symbols_not_found(self, classifier):
        """文本中无匹配品种符号。"""
        result = classifier.extract_symbols("钢铁市场分析", ["RB", "HC"])
        assert result == []

    def test_extract_symbols_case_insensitive(self, classifier):
        """品种符号匹配不区分大小写。"""
        result = classifier.extract_symbols("关注rb走势", ["RB"])
        assert result == ["RB"]

    def test_extract_symbols_multiple_matches(self, classifier):
        """文本匹配多个品种符号。"""
        result = classifier.extract_symbols("RB和HC价差分析", ["RB", "HC", "I"])
        assert result == ["RB", "HC"]
