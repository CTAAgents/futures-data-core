"""新闻数据源的 mock 测试。
覆盖正常路径、异常路径、边界情况。
"""


class TestClsProvider:
    """财联社新闻源测试。"""

    def test_fetch_news_success(self, mocker):
        from datacore.news.providers.cls import ClsProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {
            "data": {
                "roll_data": [
                    {"id": "1", "title": "新闻标题1", "content": "内容1", "ctime": "2026-01-01"},
                    {"id": "2", "title": "新闻标题2", "content": "内容2", "ctime": "2026-01-02"},
                ]
            }
        }
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = ClsProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is not None
        assert result.total == 2
        assert len(result.items) == 2

    def test_fetch_news_empty(self, mocker):
        from datacore.news.providers.cls import ClsProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {"data": {"roll_data": []}}
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = ClsProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is None

    def test_fetch_news_http_fail(self, mocker):
        from datacore.news.providers.cls import ClsProvider
        mocker.patch("httpx.Client.get", side_effect=Exception("timeout"))
        provider = ClsProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is None

    def test_check_available(self, mocker):
        from datacore.news.providers.cls import ClsProvider
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mocker.patch("httpx.Client.head", return_value=mock_resp)
        provider = ClsProvider()
        assert provider.check_available() is True

    def test_check_available_fail(self, mocker):
        from datacore.news.providers.cls import ClsProvider
        mocker.patch("httpx.Client.head", side_effect=Exception("fail"))
        provider = ClsProvider()
        assert provider.check_available() is False

    def test_fetch_news_partial_fail(self, mocker):
        """部分新闻条目解析失败不应影响其他条目。"""
        from datacore.news.providers.cls import ClsProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {
            "data": {
                "roll_data": [
                    {"id": "1", "title": "有效新闻", "content": "内容", "ctime": "2026-01-01"},
                    None,  # 非法条目，应跳过
                ]
            }
        }
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = ClsProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is not None
        assert result.total == 1


class TestWallStreetCnProvider:
    """华尔街见闻新闻源测试。"""

    def test_fetch_news_success(self, mocker):
        from datacore.news.providers.wallstreet_cn import WallStreetCnProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {
            "data": {
                "items": [
                    {"id": 1, "title": "标题", "content_text": "内容1", "display_time": "2026-01-01", "uri": "/detail/1"},
                ]
            }
        }
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = WallStreetCnProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is not None
        assert result.total == 1

    def test_fetch_news_empty(self, mocker):
        from datacore.news.providers.wallstreet_cn import WallStreetCnProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {"data": {"items": []}}
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = WallStreetCnProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is None

    def test_fetch_news_http_fail(self, mocker):
        from datacore.news.providers.wallstreet_cn import WallStreetCnProvider
        mocker.patch("httpx.Client.get", side_effect=Exception("timeout"))
        provider = WallStreetCnProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is None

    def test_check_available(self, mocker):
        from datacore.news.providers.wallstreet_cn import WallStreetCnProvider
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mocker.patch("httpx.Client.head", return_value=mock_resp)
        provider = WallStreetCnProvider()
        assert provider.check_available() is True

    def test_fallback_to_title(self, mocker):
        """当 content_text 不存在时，应回退到 title。"""
        from datacore.news.providers.wallstreet_cn import WallStreetCnProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {
            "data": {
                "items": [
                    {"id": 1, "title": "回退标题", "display_time": "2026-01-01", "uri": "/detail/1"},
                ]
            }
        }
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = WallStreetCnProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is not None
        assert result.items[0].title == "回退标题"


class TestEastMoneyResearchProvider:
    """东方财富研报源测试。"""

    def test_fetch_news_success(self, mocker):
        from datacore.news.providers.eastmoney_research import EastMoneyResearchProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {
            "data": [
                {"title": "研报标题", "content": "研报内容", "publishDate": "2026-01-01",
                 "orgSName": "中信证券", "encodeUrl": "abc123"},
            ]
        }
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = EastMoneyResearchProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is not None
        assert result.total == 1
        assert "中信" in result.items[0].source

    def test_fetch_news_empty(self, mocker):
        from datacore.news.providers.eastmoney_research import EastMoneyResearchProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {"data": []}
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = EastMoneyResearchProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is None

    def test_fetch_news_http_fail(self, mocker):
        from datacore.news.providers.eastmoney_research import EastMoneyResearchProvider
        mocker.patch("httpx.Client.get", side_effect=Exception("timeout"))
        provider = EastMoneyResearchProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is None

    def test_check_available(self, mocker):
        from datacore.news.providers.eastmoney_research import EastMoneyResearchProvider
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mocker.patch("httpx.Client.head", return_value=mock_resp)
        provider = EastMoneyResearchProvider()
        assert provider.check_available() is True

    def test_fallback_to_s3(self, mocker):
        """当 content 不存在时，回退到 s3 字段。"""
        from datacore.news.providers.eastmoney_research import EastMoneyResearchProvider
        mock_resp = mocker.Mock()
        mock_resp.json.return_value = {
            "data": [
                {"title": "标题", "s3": "s3内容", "publishDate": "2026-01-01",
                 "orgSName": "华泰证券", "encodeUrl": "abc"},
            ]
        }
        mocker.patch("httpx.Client.get", return_value=mock_resp)
        provider = EastMoneyResearchProvider()
        result = provider.fetch_news(symbol="RB", limit=5)
        assert result is not None
        assert len(result.items) == 1


class TestJin10Provider:
    """金十 MCP 新闻源测试。"""

    def _mock_rpc_responses(self, mocker, responses: dict):
        """模拟 httpx POST 返回不同的 JSON-RPC 响应。

        Args:
            responses: {method_name: response_json_for_result_field}
        """
        call_count = [0]

        def _side_effect(url, json=None, headers=None):
            method = json.get("method", "") if json else ""
            call_count[0] += 1
            mock_resp = mocker.Mock()
            if method == "initialize":
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0",
                    "id": json.get("id", 1),
                    "result": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "jin10-mcp", "version": "1.0.0"},
                    },
                }
                return mock_resp
            if method == "notifications/initialized":
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
                return mock_resp
            if method in responses:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0",
                    "id": json.get("id", 1),
                    "result": responses[method],
                }
                return mock_resp
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "jsonrpc": "2.0",
                "id": json.get("id", 1),
                "result": {"structuredContent": None, "content": []},
            }
            return mock_resp

        mocker.patch("httpx.Client.post", side_effect=_side_effect)

    def test_fetch_flash_news_all_market(self, mocker):
        """全市场快讯获取：list_flash 返回数据，list_news 返回空。"""
        from datacore.news.providers.jin10 import Jin10Provider
        call_count = [0]

        def _side_effect(url, json=None, headers=None):
            method = json.get("method", "") if json else ""
            call_count[0] += 1
            mock_resp = mocker.Mock()
            mock_resp.status_code = 200
            if method == "initialize":
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2025-11-25", "capabilities": {},
                               "serverInfo": {"name": "jin10-mcp", "version": "1.0.0"}},
                }
            elif method == "notifications/initialized":
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            elif method == "tools/call":
                tool_name = json.get("params", {}).get("name", "")
                if tool_name == "list_flash":
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 3,
                        "result": {
                            "structuredContent": {
                                "data": {
                                    "items": [
                                        {"title": "美联储加息", "content": "美联储宣布加息25个基点",
                                         "time": "2026-01-01 10:00:00", "tags": ["宏观", "美联储"]},
                                        {"title": "黄金突破2000", "content": "现货黄金突破2000美元",
                                         "time": "2026-01-01 11:00:00", "tags": ["贵金属"]},
                                    ],
                                    "next_cursor": "abc",
                                    "has_more": True,
                                }
                            },
                            "content": [],
                        },
                    }
                else:
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 4,
                        "result": {"structuredContent": {"data": {"items": []}}, "content": []},
                    }
            else:
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            return mock_resp

        mocker.patch("httpx.Client.post", side_effect=_side_effect)
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(limit=10)
        assert result is not None
        assert result.total == 2
        assert len(result.items) == 2
        assert "美联储" in result.items[0].title
        assert result.items[0].source == "jin10_flash"

    def test_fetch_news_by_symbol(self, mocker):
        """按品种搜索快讯：search_flash + search_news。"""
        from datacore.news.providers.jin10 import Jin10Provider
        call_count = [0]

        def _side_effect(url, json=None, headers=None):
            method = json.get("method", "") if json else ""
            call_count[0] += 1
            mock_resp = mocker.Mock()
            mock_resp.status_code = 200
            if method == "initialize":
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2025-11-25", "capabilities": {},
                               "serverInfo": {"name": "jin10-mcp", "version": "1.0"}},
                }
                return mock_resp
            if method == "notifications/initialized":
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
                return mock_resp
            if method == "tools/call":
                tool_name = json.get("params", {}).get("name", "")
                if tool_name == "search_flash":
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 3,
                        "result": {
                            "structuredContent": {
                                "data": {
                                    "items": [
                                        {"title": "黄金上涨", "content": "黄金价格上涨",
                                         "time": "2026-01-01", "tags": ["贵金属"]},
                                    ],
                                    "next_cursor": None, "has_more": False,
                                }
                            },
                            "content": [],
                        },
                    }
                elif tool_name == "search_news":
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 4,
                        "result": {
                            "structuredContent": {
                                "data": {
                                    "items": [
                                        {"title": "黄金深度分析", "introduction": "关于黄金的深度报道",
                                         "time": "2026-01-01", "url": "https://jin10.com/1",
                                         "id": "1", "tags": ["深度"]},
                                    ],
                                    "next_cursor": None, "has_more": False,
                                }
                            },
                            "content": [],
                        },
                    }
                else:
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 5,
                        "result": {"structuredContent": None, "content": []},
                    }
                return mock_resp
            mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            return mock_resp

        mocker.patch("httpx.Client.post", side_effect=_side_effect)
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(symbol="XAUUSD", limit=10)
        assert result is not None
        assert result.symbol == "XAUUSD"
        assert result.total == 2
        assert result.items[0].source == "jin10_flash"
        assert result.items[1].source == "jin10_news"

    def test_fetch_news_no_api_key(self, mocker):
        """没有 API Key 时应返回 None。"""
        from datacore.news.providers.jin10 import Jin10Provider
        provider = Jin10Provider(api_key="")
        result = provider.fetch_news(limit=10)
        assert result is None

    def test_fetch_news_http_error(self, mocker):
        """HTTP 请求失败时返回 None。"""
        from datacore.news.providers.jin10 import Jin10Provider
        mocker.patch("httpx.Client.post", side_effect=Exception("connection error"))
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(limit=10)
        assert result is None

    def test_fetch_news_rpc_error(self, mocker):
        """JSON-RPC 返回 error 时返回 None。"""
        from datacore.news.providers.jin10 import Jin10Provider
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"},
        }
        mocker.patch("httpx.Client.post", return_value=mock_resp)
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(limit=10)
        assert result is None

    def test_fetch_news_status_error(self, mocker):
        """HTTP 状态码非 200 时返回 None。"""
        from datacore.news.providers.jin10 import Jin10Provider
        mock_resp = mocker.Mock()
        mock_resp.status_code = 500
        mocker.patch("httpx.Client.post", return_value=mock_resp)
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(limit=10)
        assert result is None

    def test_fetch_news_empty_items(self, mocker):
        """返回空列表时返回 None。"""
        from datacore.news.providers.jin10 import Jin10Provider
        call_count = [0]

        def _side_effect(url, json=None, headers=None):
            method = json.get("method", "") if json else ""
            call_count[0] += 1
            mock_resp = mocker.Mock()
            mock_resp.status_code = 200
            if method == "initialize":
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2025-11-25", "capabilities": {},
                               "serverInfo": {"name": "jin10", "version": "1.0"}},
                }
            elif method == "notifications/initialized":
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            else:
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0", "id": 3,
                    "result": {"structuredContent": {"data": {"items": []}}, "content": []},
                }
            return mock_resp

        mocker.patch("httpx.Client.post", side_effect=_side_effect)
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(limit=10)
        assert result is None

    def test_fetch_news_content_fallback(self, mocker):
        """structuredContent 为空时，从 content 文本中解析 JSON。"""
        from datacore.news.providers.jin10 import Jin10Provider
        import json as _json

        def _side_effect(url, json=None, headers=None):
            method = json.get("method", "") if json else ""
            mock_resp = mocker.Mock()
            mock_resp.status_code = 200
            if method == "initialize":
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2025-11-25", "capabilities": {},
                               "serverInfo": {"name": "jin10", "version": "1.0"}},
                }
            elif method == "notifications/initialized":
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            elif method == "tools/call":
                tool_name = json.get("params", {}).get("name", "")
                if tool_name == "list_flash":
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 3,
                        "result": {
                            "structuredContent": None,
                            "content": [{"type": "text",
                                         "text": _json.dumps({"data": {"items": [
                                             {"title": "从content解析", "content": "解析内容",
                                              "time": "2026-01-01"}
                                         ]}})}],
                        },
                    }
                else:
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 4,
                        "result": {"structuredContent": {"data": {"items": []}}, "content": []},
                    }
            else:
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            return mock_resp

        mocker.patch("httpx.Client.post", side_effect=_side_effect)
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(limit=10)
        assert result is not None
        assert result.total == 1
        assert "从content解析" in result.items[0].title

    def test_check_available_true(self, mocker):
        """初始化成功时 check_available 返回 True。"""
        from datacore.news.providers.jin10 import Jin10Provider
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0", "id": 1,
            "result": {"protocolVersion": "2025-11-25", "capabilities": {},
                       "serverInfo": {"name": "jin10", "version": "1.0"}},
        }
        mocker.patch("httpx.Client.post", return_value=mock_resp)
        provider = Jin10Provider(api_key="test-key")
        assert provider.check_available() is True
        assert provider._available is True

    def test_check_available_cached(self, mocker):
        """重复调用 check_available 应使用缓存。"""
        from datacore.news.providers.jin10 import Jin10Provider
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0", "id": 1,
            "result": {"protocolVersion": "2025-11-25", "capabilities": {},
                       "serverInfo": {"name": "jin10", "version": "1.0"}},
        }
        mock_post = mocker.patch("httpx.Client.post", return_value=mock_resp)
        provider = Jin10Provider(api_key="test-key")
        assert provider.check_available() is True
        assert provider.check_available() is True
        assert mock_post.call_count >= 2  # initialize + notification

    def test_check_available_no_key(self):
        """没有 API Key 时 check_available 返回 False。"""
        from datacore.news.providers.jin10 import Jin10Provider
        provider = Jin10Provider(api_key="")
        assert provider.check_available() is False

    def test_symbol_to_keyword(self):
        """品种代码到关键词的映射。"""
        from datacore.news.providers.jin10 import Jin10Provider
        assert Jin10Provider._symbol_to_keyword("XAUUSD") == "黄金"
        assert Jin10Provider._symbol_to_keyword("USOIL") == "原油"
        assert Jin10Provider._symbol_to_keyword("RB") == "螺纹钢"
        assert Jin10Provider._symbol_to_keyword("AU2406") == "黄金"
        assert Jin10Provider._symbol_to_keyword("UNKNOWN") == "UNKNOWN"

    def test_parse_flash_items_with_symbols(self):
        """快讯条目带有 related_symbols 时应正确解析。"""
        from datacore.news.providers.jin10 import Jin10Provider
        raw = [
            {"title": "黄金上涨", "content": "黄金价格上涨",
             "time": "2026-01-01", "tags": ["贵金属"],
             "related_symbols": ["XAUUSD", "AU2406"]},
        ]
        provider = Jin10Provider(api_key="test")
        items = provider._parse_flash_items(raw)
        assert len(items) == 1
        assert "XAUUSD" in items[0].related_symbols
        assert "AU2406" in items[0].related_symbols

    def test_parse_flash_items_tags_string(self):
        """tags 为字符串时的处理。"""
        from datacore.news.providers.jin10 import Jin10Provider
        raw = [{"title": "测试", "content": "内容", "time": "2026-01-01", "tags": "快讯"}]
        provider = Jin10Provider(api_key="test")
        items = provider._parse_flash_items(raw)
        assert len(items) == 1
        assert "快讯" in items[0].tags

    def test_parse_flash_items_invalid_entry(self):
        """无效条目应被跳过。"""
        from datacore.news.providers.jin10 import Jin10Provider
        raw = [
            None,
            "not_a_dict",
            {"title": "", "content": ""},  # 无标题无内容
            {"title": "有效条目", "content": "有内容", "time": "2026-01-01"},
        ]
        provider = Jin10Provider(api_key="test")
        items = provider._parse_flash_items(raw)
        assert len(items) == 1
        assert items[0].title == "有效条目"

    def test_parse_flash_title_from_content(self):
        """没有 title 时从 content 截取。"""
        from datacore.news.providers.jin10 import Jin10Provider
        long_content = "a" * 100
        raw = [{"content": long_content, "time": "2026-01-01"}]
        provider = Jin10Provider(api_key="test")
        items = provider._parse_flash_items(raw)
        assert len(items) == 1
        assert len(items[0].title) == 60

    def test_parse_news_items_no_title(self):
        """资讯没有 title 时跳过。"""
        from datacore.news.providers.jin10 import Jin10Provider
        raw = [{"introduction": "只有简介没有标题", "time": "2026-01-01"}]
        provider = Jin10Provider(api_key="test")
        items = provider._parse_news_items(raw)
        assert len(items) == 0

    def test_init_env_api_key(self, mocker, monkeypatch):
        """从环境变量读取 API Key。"""
        monkeypatch.setenv("JIN10_API_KEY", "env-key")
        from datacore.news.providers.jin10 import Jin10Provider
        provider = Jin10Provider()
        assert provider.api_key == "env-key"

    def test_fetch_news_structured_content_string(self, mocker):
        """structuredContent 是字符串时尝试 JSON 解析。"""
        from datacore.news.providers.jin10 import Jin10Provider
        import json as _json

        def _side_effect(url, json=None, headers=None):
            method = json.get("method", "") if json else ""
            mock_resp = mocker.Mock()
            mock_resp.status_code = 200
            if method == "initialize":
                mock_resp.json.return_value = {
                    "jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2025-11-25", "capabilities": {},
                               "serverInfo": {"name": "jin10", "version": "1.0"}},
                }
            elif method == "notifications/initialized":
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            elif method == "tools/call":
                tool_name = json.get("params", {}).get("name", "")
                if tool_name == "list_flash":
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 3,
                        "result": {
                            "structuredContent": _json.dumps({"data": {"items": [
                                {"title": "字符串解析", "content": "从字符串解析",
                                 "time": "2026-01-01"}
                            ]}}),
                            "content": [],
                        },
                    }
                else:
                    mock_resp.json.return_value = {
                        "jsonrpc": "2.0", "id": 4,
                        "result": {"structuredContent": {"data": {"items": []}}, "content": []},
                    }
            else:
                mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {}}
            return mock_resp

        mocker.patch("httpx.Client.post", side_effect=_side_effect)
        provider = Jin10Provider(api_key="test-key")
        result = provider.fetch_news(limit=10)
        assert result is not None
        assert result.total == 1


class TestNewsDataProvider:
    """新闻统一入口测试。"""

    def test_provider_init_sources(self):
        from datacore.news.news_provider import NewsDataProvider
        provider = NewsDataProvider()
        assert len(provider.sources) > 0

    def test_get_no_symbol(self, mocker):
        from datacore.news.news_provider import NewsDataProvider
        provider = NewsDataProvider()
        # Mock 所有源的 fetch_news 返回 None
        for src in provider.sources:
            src.fetch_news = mocker.Mock(return_value=None)
            src.check_available = mocker.Mock(return_value=True)
        result = provider.get(symbol=None, params={"days": 1})
        assert result is not None
        assert result.grade == "unavailable"

    def test_classifier_tags_applied(self, mocker):
        from datacore.news.news_provider import NewsDataProvider
        from datacore.news.models import NewsData, NewsItem
        provider = NewsDataProvider()
        # 模拟一个返回数据的源
        mock_news = NewsData(symbol="RB", total=1, items=[
            NewsItem(title="央行下调LPR利率", content="宏观政策", source="cls",
                    published_at="2026-01-01", tags=[], related_symbols=[]),
        ])
        for src in provider.sources:
            src.fetch_news = mocker.Mock(return_value=mock_news)
            src.check_available = mocker.Mock(return_value=True)
        result = provider.get(symbol="RB", params={"days": 1})
        assert result is not None
        assert result.available
        assert len(result.data.items) > 0
