"""Tests for datacore.collectors — 采集模块骨架测试。"""

from __future__ import annotations

import os
import tempfile

import pytest
import pandas as pd

from datacore.collectors.web_crawl import WebCollectorClient
from datacore.collectors.open_source import AKShareClient
from datacore.collectors.local_doc import PdfExcelReader
from datacore.collectors.search import TavilyClient


# ============================================================
#  WebCollectorClient 测试
# ============================================================

class TestWebCollectorClient:
    """Web 爬虫客户端测试。"""

    def test_instantiation(self):
        """实例化测试。"""
        client = WebCollectorClient()
        assert client.name == "web_collector"
        assert client.description != ""

    def test_check_available(self):
        """检查可用性（httpx 应为可用）。"""
        client = WebCollectorClient()
        available = client.check_available()
        assert isinstance(available, bool)

    def test_custom_headers(self):
        """自定义请求头。"""
        headers = {"User-Agent": "TestAgent"}
        client = WebCollectorClient(headers=headers)
        assert client.headers["User-Agent"] == "TestAgent"

    def test_context_manager(self):
        """上下文管理器。"""
        with WebCollectorClient() as client:
            assert client is not None

    def test_fetch_invalid_url(self):
        """抓取无效 URL（应该失败但不崩溃）。"""
        client = WebCollectorClient(timeout=1.0)
        if not client.check_available():
            pytest.skip("httpx 不可用")
        result = client.fetch("http://invalid.url.example.com/test")
        assert "success" in result
        assert "url" in result


# ============================================================
#  AKShareClient 测试
# ============================================================

class TestAKShareClient:
    """AKShare 客户端测试。"""

    def test_instantiation(self):
        """实例化测试。"""
        client = AKShareClient()
        assert client.name == "akshare"
        assert client.description != ""

    def test_check_available(self):
        """检查可用性。"""
        client = AKShareClient()
        available = client.check_available()
        assert isinstance(available, bool)

    def test_fetch_unknown_api(self):
        """调用不存在的接口。"""
        client = AKShareClient()
        if not client.check_available():
            pytest.skip("AKShare 未安装")
        result = client.fetch("nonexistent_api_12345")
        assert result["success"] is False
        assert "api_name" in result

    def test_fetch_no_dependency(self):
        """无依赖时返回错误。"""
        client = AKShareClient()
        client._ak = None
        if not client.check_available():
            result = client.fetch("any_api")
            assert result["success"] is False
            assert "AKShare" in result["error"]


# ============================================================
#  PdfExcelReader 测试
# ============================================================

class TestPdfExcelReader:
    """PDF/Excel 读取器测试。"""

    def test_instantiation(self):
        """实例化测试。"""
        reader = PdfExcelReader()
        assert reader.name == "pdf_excel_reader"
        assert reader.description != ""

    def test_check_available(self):
        """检查可用性（pandas 应为可用）。"""
        reader = PdfExcelReader()
        assert reader.check_available() is True

    def test_read_nonexistent_file(self):
        """读取不存在的文件。"""
        reader = PdfExcelReader()
        result = reader.fetch("/nonexistent/path/file.xlsx")
        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_read_unsupported_type(self):
        """读取不支持的文件类型。"""
        reader = PdfExcelReader()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            result = reader.fetch(path)
            assert result["success"] is False
        finally:
            os.unlink(path)

    def test_read_csv(self):
        """读取 CSV 文件。"""
        reader = PdfExcelReader()
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name
        try:
            result = reader.fetch(path)
            assert result["success"] is True
            assert result["file_type"] == "excel"
            assert result["row_count"] == 3
        finally:
            os.unlink(path)


# ============================================================
#  TavilyClient 测试
# ============================================================

class TestTavilyClient:
    """Tavily 搜索客户端测试。"""

    def test_instantiation(self):
        """实例化测试。"""
        client = TavilyClient()
        assert client.name == "tavily_search"
        assert client.description != ""

    def test_check_available_no_key(self):
        """无 API Key 时不可用。"""
        client = TavilyClient(api_key="")
        assert client.check_available() is False

    def test_fetch_no_available(self):
        """不可用时返回错误。"""
        client = TavilyClient(api_key="")
        result = client.fetch("test query")
        assert result["success"] is False
        assert "不可用" in result["error"]

    def test_context_manager(self):
        """上下文管理器。"""
        with TavilyClient(api_key="test") as client:
            assert client is not None
