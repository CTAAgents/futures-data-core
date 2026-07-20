"""Tavily 搜索封装骨架。

提供 Tavily AI 搜索接口的适配器。
Tavily 为可选依赖，需要 API key，不可用时返回空结果。
"""

from __future__ import annotations

import os
from typing import Any


class TavilyClient:
    """Tavily AI 搜索客户端。

    封装 Tavily 搜索 API，提供 AI 驱动的信息检索能力。
    为可选依赖，需要 API key 配置。

    Attributes:
        name: 采集器名称。
        description: 采集器描述。
    """

    name: str = "tavily_search"
    description: str = "Tavily AI 搜索接口封装"

    def __init__(self, api_key: str = "", base_url: str = "") -> None:
        """初始化 Tavily 客户端。

        Args:
            api_key: Tavily API Key，默认从环境变量 TAVILY_API_KEY 读取。
            base_url: API 基础 URL。
        """
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        self.base_url = base_url or "https://api.tavily.com"
        self._client = None

    def check_available(self) -> bool:
        """检查 Tavily 是否可用。

        需要同时满足：httpx 可用 + API Key 已配置。

        Returns:
            True 表示可用。
        """
        if not self.api_key:
            return False
        try:
            import httpx  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_client(self) -> Any | None:
        """获取 httpx 客户端。"""
        if not self.check_available():
            return None
        if self._client is None:
            import httpx
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=30.0,
            )
        return self._client

    def fetch(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """执行搜索查询。

        Args:
            query: 搜索关键词。
            **kwargs: 额外参数：
                - search_depth: 搜索深度，'basic' / 'advanced'
                - max_results: 最大结果数
                - include_answer: 是否包含 AI 回答
                - include_images: 是否包含图片
                - include_raw_content: 是否包含原始内容

        Returns:
            搜索结果字典。
        """
        client = self._get_client()
        if client is None:
            return {
                "success": False,
                "query": query,
                "results": [],
                "answer": "",
                "error": "Tavily 不可用（缺少 API Key 或 httpx 未安装）",
            }

        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": kwargs.get("search_depth", "basic"),
                "max_results": kwargs.get("max_results", 5),
                "include_answer": kwargs.get("include_answer", True),
                "include_images": kwargs.get("include_images", False),
                "include_raw_content": kwargs.get("include_raw_content", False),
            }

            response = client.post("/search", json=payload)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "query": query,
                    "results": data.get("results", []),
                    "answer": data.get("answer", ""),
                    "images": data.get("images", []),
                    "result_count": len(data.get("results", [])),
                }
            else:
                return {
                    "success": False,
                    "query": query,
                    "results": [],
                    "answer": "",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "error_type": "HTTPError",
                }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "results": [],
                "answer": "",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def search(self, query: str, max_results: int = 5,
               include_answer: bool = True) -> dict[str, Any]:
        """便捷搜索方法。

        Args:
            query: 搜索关键词。
            max_results: 最大结果数。
            include_answer: 是否包含 AI 生成的答案。

        Returns:
            搜索结果。
        """
        return self.fetch(
            query,
            max_results=max_results,
            include_answer=include_answer,
        )

    def close(self) -> None:
        """关闭客户端连接。"""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "TavilyClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
