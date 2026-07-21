"""金十期货快讯数据源 — 新闻源 P0。

通过金十 MCP Server（HTTP 协议）获取期货快讯、资讯、财经日历。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import httpx

from datacore.news.models import NewsData, NewsItem
from datacore.news.providers.base import NewsDataSource

MCP_SERVER_URL = "https://mcp.jin10.com/mcp"
MCP_PROTOCOL_VERSION = "2025-11-25"


class Jin10Provider(NewsDataSource):
    """金十期货快讯数据源（MCP HTTP 客户端）。"""

    name = "jin10"
    priority = 0

    def __init__(self, api_key: str | None = None, server_url: str | None = None):
        self.api_key = api_key or os.environ.get("JIN10_API_KEY", "")
        self.server_url = server_url or os.environ.get("JIN10_MCP_URL", MCP_SERVER_URL)
        self._session_id: str | None = None
        self._initialized = False
        self._available: bool | None = None
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _rpc_request(self, method: str, params: dict | None = None) -> dict | None:
        """发送 JSON-RPC 请求并返回 result 字段。"""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        try:
            with httpx.Client(timeout=15) as c:
                resp = c.post(self.server_url, json=payload, headers=self._headers())
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except Exception:
            return None

        if not isinstance(data, dict):
            return None
        if "error" in data:
            return None
        return data.get("result")

    def _initialize(self) -> bool:
        """执行 MCP initialize 握手。"""
        if self._initialized:
            return True
        if not self.api_key:
            self._available = False
            return False

        result = self._rpc_request("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "datacore", "version": "2.4.0"},
        })
        if not result:
            self._available = False
            return False

        self._rpc_request("notifications/initialized")
        self._initialized = True
        self._available = True
        return True

    def _call_tool(self, name: str, arguments: dict | None = None) -> dict | None:
        """调用 MCP 工具，优先返回 structuredContent。"""
        if not self._initialize():
            return None

        result = self._rpc_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        if not result:
            return None

        structured = result.get("structuredContent")
        if structured:
            if isinstance(structured, dict):
                return structured
            if isinstance(structured, str):
                try:
                    return json.loads(structured)
                except (json.JSONDecodeError, TypeError):
                    pass

        content = result.get("content")
        if content and isinstance(content, list):
            for item in content:
                text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if text:
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, TypeError):
                        return {"text": text}

        return None

    def fetch_news(self, symbol: Optional[str] = None,
                   days: int = 7, limit: int = 50) -> Optional[NewsData]:
        """从金十获取期货快讯/资讯。

        Args:
            symbol: 品种代码，如 "XAUUSD"、"RB"，None 表示全市场
            days: 获取最近多少天的快讯
            limit: 返回条数上限
        """
        items: list[NewsItem] = []

        if symbol:
            keyword = self._symbol_to_keyword(symbol)
            result = self._call_tool("search_flash", {"keyword": keyword})
            if result:
                data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
                raw = data.get("items", []) if isinstance(data, dict) else []
                items.extend(self._parse_flash_items(raw))

            if len(items) < limit:
                result = self._call_tool("search_news", {"keyword": keyword})
                if result:
                    data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
                    raw = data.get("items", []) if isinstance(data, dict) else []
                    items.extend(self._parse_news_items(raw))
        else:
            result = self._call_tool("list_flash")
            if result:
                data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
                raw = data.get("items", []) if isinstance(data, dict) else []
                items.extend(self._parse_flash_items(raw))

            if len(items) < limit:
                result = self._call_tool("list_news")
                if result:
                    data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
                    raw = data.get("items", []) if isinstance(data, dict) else []
                    items.extend(self._parse_news_items(raw))

        if not items:
            return None

        items = items[:limit]
        return NewsData(symbol=symbol, total=len(items), items=items)

    @staticmethod
    def _symbol_to_keyword(symbol: str) -> str:
        """将品种代码映射为搜索关键词。"""
        mapping = {
            "XAUUSD": "黄金",
            "XAGUSD": "白银",
            "USOIL": "原油",
            "UKOIL": "原油",
            "COPPER": "铜",
            "USDJPY": "日元",
            "EURUSD": "欧元",
            "USDCNH": "人民币",
            "RB": "螺纹钢",
            "CU": "铜",
            "AU": "黄金",
            "AG": "白银",
            "SC": "原油",
            "I": "铁矿石",
            "J": "焦炭",
            "JM": "焦煤",
        }
        s = symbol.upper()
        if s in mapping:
            return mapping[s]
        if s.startswith(("AU", "沪金")):
            return "黄金"
        if s.startswith(("AG", "沪银")):
            return "白银"
        if s.startswith(("CU", "沪铜")):
            return "铜"
        return symbol

    def _parse_flash_items(self, raw: list[dict]) -> list[NewsItem]:
        """解析快讯列表为 NewsItem。"""
        items = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                raw_title = str(item.get("title") or "")
                raw_content = str(item.get("content") or item.get("text") or "")
                if not raw_title and not raw_content:
                    continue
                title = raw_title if raw_title else raw_content[:60]
                content = raw_content if raw_content else raw_title

                published_at = str(
                    item.get("time") or item.get("published_at")
                    or item.get("pub_time") or item.get("ctime") or ""
                )
                url = str(item.get("url") or "")
                tags_raw = item.get("tags") or []
                if isinstance(tags_raw, list):
                    tags = [str(t) for t in tags_raw if t]
                elif isinstance(tags_raw, str):
                    tags = [tags_raw]
                else:
                    tags = ["flash"]

                related = []
                syms = item.get("related_symbols") or item.get("symbols") or []
                if isinstance(syms, list):
                    related = [str(s).upper() for s in syms if s]

                items.append(NewsItem(
                    title=title,
                    content=content,
                    published_at=published_at,
                    source="jin10_flash",
                    url=url,
                    tags=tags,
                    related_symbols=related,
                ))
            except Exception:
                continue
        return items

    def _parse_news_items(self, raw: list[dict]) -> list[NewsItem]:
        """解析资讯列表为 NewsItem。"""
        items = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                title = str(item.get("title") or "")
                content = str(item.get("introduction") or item.get("summary") or "")
                if not title:
                    continue

                published_at = str(
                    item.get("time") or item.get("published_at")
                    or item.get("pub_time") or ""
                )
                url = str(item.get("url") or "")
                news_id = str(item.get("id") or "")

                tags_raw = item.get("tags") or ["news"]
                if isinstance(tags_raw, list):
                    tags = [str(t) for t in tags_raw if t]
                else:
                    tags = ["news"]

                items.append(NewsItem(
                    title=title,
                    content=content,
                    published_at=published_at,
                    source="jin10_news",
                    url=url,
                    tags=tags,
                    related_symbols=[],
                    summary=content,
                ))
            except Exception:
                continue
        return items

    def check_available(self) -> bool:
        """检查金十 MCP 服务是否可用。"""
        if self._available is not None:
            return self._available
        return self._initialize()
