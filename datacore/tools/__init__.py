"""Data-Core Tools - 工具接口层模块。

不依赖 LangChain 的 BaseTool 类，而是实现符合 LangChain BaseTool 协议的自定义基类。
没有 langchain 也能用，有 langchain 时可以无缝接入。
"""

from __future__ import annotations

from .base import DataCoreBaseTool
from .ohlcv import DataCoreOHLCVTool
from .quote import DataCoreQuoteTool
from .sentiment import DataCoreSentimentTool
from .health import DataCoreHealthTool
from .list_symbols import DataCoreListSymbolsTool
from .macro import DataCoreMacroTool
from .fundamental import DataCoreFundamentalTool
from .f10 import DataCoreF10Tool
from .indicators import DataCoreIndicatorsTool
from .term_structure import DataCoreTermStructureTool
from .basis import DataCoreBasisTool
from .market_regime import DataCoreMarketRegimeTool
from .news import DataCoreNewsTool
from .adjustment import DataCoreAdjustmentTool
from .period import DataCorePeriodTool

from .cleaning import (
    UnitUnifyTool,
    DateAlignTool,
    DuplicateMergeTool,
    OutlierFilterTool,
)

from .validation import (
    CrossSourceVerifyTool,
    DataMissingDetectTool,
    CalMathComputeTool,
)

from .operations import (
    ConfigReadTool,
)

__all__ = [
    "DataCoreBaseTool",
    "DataCoreOHLCVTool",
    "DataCoreQuoteTool",
    "DataCoreSentimentTool",
    "DataCoreHealthTool",
    "DataCoreListSymbolsTool",
    "DataCoreMacroTool",
    "DataCoreFundamentalTool",
    "DataCoreF10Tool",
    "DataCoreIndicatorsTool",
    "DataCoreTermStructureTool",
    "DataCoreBasisTool",
    "DataCoreMarketRegimeTool",
    "DataCoreNewsTool",
    "DataCoreAdjustmentTool",
    "DataCorePeriodTool",
    "UnitUnifyTool",
    "DateAlignTool",
    "DuplicateMergeTool",
    "OutlierFilterTool",
    "CrossSourceVerifyTool",
    "DataMissingDetectTool",
    "CalMathComputeTool",
    "ConfigReadTool",
    "all_tools",
    "get_tool_by_name",
]


def _build_all_tools() -> list[DataCoreBaseTool]:
    """构建所有工具实例列表。

    Returns:
        所有工具实例的列表
    """
    tool_classes = [
        DataCoreOHLCVTool,
        DataCoreQuoteTool,
        DataCoreSentimentTool,
        DataCoreHealthTool,
        DataCoreListSymbolsTool,
        DataCoreMacroTool,
        DataCoreFundamentalTool,
        DataCoreF10Tool,
        DataCoreIndicatorsTool,
        DataCoreTermStructureTool,
        DataCoreBasisTool,
        DataCoreMarketRegimeTool,
        DataCoreNewsTool,
        DataCoreAdjustmentTool,
        DataCorePeriodTool,
        UnitUnifyTool,
        DateAlignTool,
        DuplicateMergeTool,
        OutlierFilterTool,
        CrossSourceVerifyTool,
        DataMissingDetectTool,
        CalMathComputeTool,
        ConfigReadTool,
    ]

    return [cls() for cls in tool_classes]


all_tools: list[DataCoreBaseTool] = _build_all_tools()


def get_tool_by_name(name: str) -> DataCoreBaseTool | None:
    """根据名称获取工具实例。

    Args:
        name: 工具名称

    Returns:
        工具实例，找不到返回 None
    """
    for tool in all_tools:
        if tool.name == name:
            return tool
    return None
