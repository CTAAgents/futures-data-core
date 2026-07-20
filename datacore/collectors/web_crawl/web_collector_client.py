"""Web 爬虫 HTTP 客户端骨架。

提供网页数据采集的基础适配器，依赖 httpx（已在项目依赖中）。
如果 httpx 不可用，返回空结果。
"""

from __future__ import annotations

from typing import Any


class WebCollectorClient:
    """Web 爬虫 HTTP 客户端。

    提供网页内容获取、简单 HTML 解析等能力。
    外部依赖可选，不可用时返回空结果。

    Attributes:
        name: 采集器名称。
        description: 采集器描述。
    """

    name: str = "web_collector"
    description: str = "Web 爬虫 HTTP 客户端，支持网页内容抓取和简单解析"

    def __init__(self, timeout: float = 10.0, headers: dict[str, str] | None = None) -> None:
        """初始化 Web 爬虫客户端。

        Args:
            timeout: 请求超时时间（秒）。
            headers: 默认请求头。
        """
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "DataCore/1.0 (Web Collector)",
        }
        self._client = None

    def check_available(self) -> bool:
        """检查采集器是否可用。

        Returns:
            True 表示可用，False 表示不可用。
        """
        try:
            import httpx  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_client(self) -> Any | None:
        """获取 httpx 客户端实例。

        Returns:
            httpx.Client 实例或 None。
        """
        if not self.check_available():
            return None
        if self._client is None:
            import httpx
            self._client = httpx.Client(
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True,
            )
        return self._client

    def fetch(self, url: str, method: str = "GET", **kwargs: Any) -> dict[str, Any]:
        """抓取指定 URL 的内容。

        Args:
            url: 目标 URL。
            method: HTTP 方法，默认 GET。
            **kwargs: 额外请求参数。

        Returns:
            抓取结果字典，包含：
            - success: 是否成功
            - url: 目标 URL
            - status_code: HTTP 状态码
            - content: 响应内容（文本）
            - error: 错误信息（失败时）
        """
        client = self._get_client()
        if client is None:
            return {
                "success": False,
                "url": url,
                "status_code": None,
                "content": "",
                "error": "httpx 不可用",
            }

        try:
            response = client.request(method, url, **kwargs)
            return {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers),
            }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "status_code": None,
                "content": "",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def fetch_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """抓取 JSON 接口数据。

        Args:
            url: 目标 URL。
            **kwargs: 额外请求参数。

        Returns:
            JSON 数据结果。
        """
        result = self.fetch(url, **kwargs)
        if not result["success"]:
            return result

        try:
            import json
            data = json.loads(result["content"])
            return {
                "success": True,
                "url": url,
                "status_code": result["status_code"],
                "data": data,
            }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "status_code": result["status_code"],
                "error": f"JSON 解析失败: {e}",
                "error_type": "JSONDecodeError",
            }

    def close(self) -> None:
        """关闭客户端连接。"""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "WebCollectorClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
