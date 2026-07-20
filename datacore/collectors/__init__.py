"""数据采集模块 — 轻量版骨架。

提供多种数据源采集能力的适配器接口，外部依赖可选。
所有采集器遵循统一接口：name / description / check_available / fetch。
"""

from .web_crawl import WebCollectorClient
from .open_source import AKShareClient
from .local_doc import PdfExcelReader
from .search import TavilyClient

__all__ = [
    "WebCollectorClient",
    "AKShareClient",
    "PdfExcelReader",
    "TavilyClient",
]
