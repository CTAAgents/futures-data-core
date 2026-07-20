"""数据源可信度权重表。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SourceWeight:
    """数据源权重配置。

    Attributes:
        name: 数据源名称。
        weight: 可信度权重（0-1），数值越大数据越可信。
        description: 数据源描述。
        category: 数据源类别，如 'exchange'、'broker'、'web' 等。
        update_frequency: 数据更新频率，如 'daily'、'realtime'。
    """

    name: str
    weight: float = 0.5
    description: str = ""
    category: str = ""
    update_frequency: str = ""

    def __post_init__(self) -> None:
        self.weight = max(0.0, min(1.0, self.weight))


DEFAULT_SOURCE_WEIGHTS: dict[str, SourceWeight] = {
    "exchange": SourceWeight(
        name="exchange",
        weight=0.98,
        description="交易所官方数据",
        category="exchange",
        update_frequency="realtime",
    ),
    "tqsdk": SourceWeight(
        name="tqsdk",
        weight=0.95,
        description="天勤量化数据",
        category="broker",
        update_frequency="realtime",
    ),
    "eastmoney": SourceWeight(
        name="eastmoney",
        weight=0.90,
        description="东方财富数据",
        category="web",
        update_frequency="daily",
    ),
    "guosen": SourceWeight(
        name="guosen",
        weight=0.92,
        description="国信证券数据",
        category="broker",
        update_frequency="daily",
    ),
    "tencent": SourceWeight(
        name="tencent",
        weight=0.88,
        description="腾讯财经数据",
        category="web",
        update_frequency="daily",
    ),
    "shengyishe": SourceWeight(
        name="shengyishe",
        weight=0.85,
        description="生意社数据",
        category="web",
        update_frequency="daily",
    ),
    "qmt": SourceWeight(
        name="qmt",
        weight=0.93,
        description="迅投QMT数据",
        category="broker",
        update_frequency="realtime",
    ),
    "tdx_lc": SourceWeight(
        name="tdx_lc",
        weight=0.91,
        description="通达信数据",
        category="broker",
        update_frequency="daily",
    ),
    "national_bureau": SourceWeight(
        name="national_bureau",
        weight=0.96,
        description="国家统计局数据",
        category="official",
        update_frequency="monthly",
    ),
    "pboc": SourceWeight(
        name="pboc",
        weight=0.97,
        description="央行数据",
        category="official",
        update_frequency="monthly",
    ),
    "akshare": SourceWeight(
        name="akshare",
        weight=0.82,
        description="AKShare开源数据",
        category="open_source",
        update_frequency="daily",
    ),
    "web_crawl": SourceWeight(
        name="web_crawl",
        weight=0.70,
        description="网络爬虫数据",
        category="web",
        update_frequency="daily",
    ),
}


def get_source_weight(source_name: str) -> float:
    """获取指定数据源的可信度权重。

    Args:
        source_name: 数据源名称。

    Returns:
        权重值（0-1），未找到则返回默认权重 0.5。

    Examples:
        >>> get_source_weight("exchange")
        0.98
        >>> get_source_weight("unknown_source")
        0.5
    """
    if source_name in DEFAULT_SOURCE_WEIGHTS:
        return DEFAULT_SOURCE_WEIGHTS[source_name].weight
    return 0.5


def calculate_source_score(
    source_data: dict[str, Any],
    custom_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """计算多个数据源的可信度得分。

    综合考虑数据源权重、数据完整度、数据时效性等因素。

    Args:
        source_data: 数据源信息字典，key 为源名，value 为数据源信息。
            可包含 'weight'、'completeness'、'freshness' 等字段。
        custom_weights: 自定义权重覆盖表。

    Returns:
        各数据源的得分字典，key 为源名，value 为得分（0-1）。

    Examples:
        >>> data = {
        ...     "src_a": {"completeness": 0.95, "freshness": 0.9},
        ...     "src_b": {"completeness": 0.8, "freshness": 0.95},
        ... }
        >>> scores = calculate_source_score(data)
        >>> len(scores)
        2
    """
    scores: dict[str, float] = {}

    for source_name, info in source_data.items():
        base_weight = 0.5
        if custom_weights and source_name in custom_weights:
            base_weight = custom_weights[source_name]
        elif source_name in DEFAULT_SOURCE_WEIGHTS:
            base_weight = DEFAULT_SOURCE_WEIGHTS[source_name].weight

        completeness = float(info.get("completeness", 1.0))
        freshness = float(info.get("freshness", 1.0))
        accuracy = float(info.get("accuracy", 1.0))

        score = (
            base_weight * 0.4
            + completeness * 0.25
            + freshness * 0.2
            + accuracy * 0.15
        )
        scores[source_name] = max(0.0, min(1.0, score))

    return scores
