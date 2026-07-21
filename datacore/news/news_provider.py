"""新闻资讯数据提供者 — 多源降级链。

新闻采集 + 分类加工，产出携带 tags 的 NEWS 数据。
"""

from __future__ import annotations
import time
from typing import Optional
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.news.models import NewsData
from datacore.news.classifier import NewsClassifier


class NewsDataProvider:
    """新闻数据提供者 — 多源降级链。

    P0: 财联社（快讯，最及时）
    P1: 华尔街见闻（综合财经）
    P2: 东方财富研报（深度分析）
    P3: 交易所公告（官方公告）
    """

    def __init__(self):
        self.sources = []
        self.classifier = NewsClassifier()
        self._init_sources()

    def _init_sources(self):
        """懒加载数据源。"""
        try:
            from datacore.news.providers.jin10 import Jin10Provider
            self.sources.append(Jin10Provider())
        except Exception:
            pass
        try:
            from datacore.news.providers.cls import ClsProvider
            self.sources.append(ClsProvider())
        except Exception:
            pass
        try:
            from datacore.news.providers.wallstreet_cn import WallStreetCnProvider
            self.sources.append(WallStreetCnProvider())
        except Exception:
            pass
        try:
            from datacore.news.providers.eastmoney_research import EastMoneyResearchProvider
            self.sources.append(EastMoneyResearchProvider())
        except Exception:
            pass

    def get(self, symbol: Optional[str] = None,
            params: dict | None = None) -> DataPayload:
        """获取新闻资讯（已分类，携带 tags）。

        Args:
            symbol: 品种代码（如 "RB"），None 表示全市场
            params: {"days": 7, "categories": ["macro", "industry"], "limit": 50}
        """
        params = params or {}
        days = int(params.get("days", 7))
        categories = params.get("categories")
        limit = int(params.get("limit", 50))

        for src in self.sources:
            if not hasattr(src, "check_available") or not src.check_available():
                continue
            try:
                news_data = src.fetch_news(symbol=symbol, days=days, limit=limit)
                if news_data and news_data.items:
                    for item in news_data.items:
                        if not item.tags:
                            item.tags = self.classifier.classify_item(item.title, item.content)
                        if symbol and symbol.upper() not in item.related_symbols:
                            item.related_symbols.append(symbol.upper())
                    if categories:
                        filtered = []
                        for item in news_data.items:
                            if any(cat in item.tags for cat in categories):
                                filtered.append(item)
                        news_data.items = filtered[:limit]
                        news_data.total = len(filtered)
                    grade = SourceGrade.DAILY if len(self.sources) > 0 else SourceGrade.CACHED
                    return DataPayload(
                        symbol=symbol or "*",
                        data_type=DataType.NEWS,
                        market=MarketType.FUTURES,
                        data=news_data,
                        source=src.name,
                        grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue

        return DataPayload(
            symbol=symbol or "*",
            data_type=DataType.NEWS,
            market=MarketType.FUTURES,
            data=NewsData(symbol=symbol),
            grade=SourceGrade.UNAVAILABLE,
            errors=["所有新闻源不可用"],
            collected_at=time.time(),
        )
