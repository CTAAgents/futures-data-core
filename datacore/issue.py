"""消费者反馈通道 — 数据问题上报与自动降级应对。

v1.2.0 新增: 统一的消费者问题反馈机制，支持:
  - IssueType 枚举定义常见数据问题类型
  - DataIssue 数据类记录单条问题详情
  - IssueRegistry 问题注册表，支持上报、查询、解决、统计
  - _auto_mitigate 根据问题类型自动触发应对策略
"""

from __future__ import annotations
import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """数据问题类型枚举。"""

    DATA_EMPTY = "data_empty"
    DATA_STALE = "data_stale"
    DATA_ANOMALY = "data_anomaly"
    SOURCE_UNAVAILABLE = "source_unavailable"
    TYPE_UNSUPPORTED = "type_unsupported"
    SLOW_RESPONSE = "slow_response"


@dataclass
class DataIssue:
    """单条消费者反馈的数据问题。"""

    symbol: str
    data_type: str
    issue_type: IssueType
    detail: str
    source: str
    consumer: str
    timestamp: float = 0.0
    resolved: bool = False
    resolution: str = ""


class IssueRegistry:
    """消费者问题注册表。

    记录所有消费者上报的数据问题，支持按类型/品种过滤，
    并根据问题类型自动触发降级应对策略。
    """

    def __init__(self):
        self._issues: list[DataIssue] = []

    def report(self, issue: DataIssue) -> dict:
        """记录问题并自动降级应对。

        Args:
            issue: 数据问题实例

        Returns:
            包含上报结果和自动应对措施的 dict
        """
        if issue.timestamp == 0.0:
            issue.timestamp = time.time()

        self._issues.append(issue)
        logger.info(
            f"[Issue] reported: {issue.issue_type.value} - "
            f"{issue.symbol}/{issue.data_type} by {issue.consumer}"
        )

        mitigation = self._auto_mitigate(issue)

        return {
            "reported": True,
            "issue_index": len(self._issues) - 1,
            "mitigation": mitigation,
        }

    def _auto_mitigate(self, issue: DataIssue) -> dict:
        """根据问题类型自动触发应对策略。

        Args:
            issue: 数据问题实例

        Returns:
            应对策略详情 dict
        """
        strategy = {
            "action": "none",
            "description": "",
            "severity": "info",
        }

        if issue.issue_type == IssueType.DATA_EMPTY:
            strategy.update({
                "action": "fallback_to_cache",
                "description": "数据为空，尝试从缓存层回退",
                "severity": "warning",
            })
        elif issue.issue_type == IssueType.DATA_STALE:
            strategy.update({
                "action": "use_stale_with_warning",
                "description": "数据过期，继续使用但标记警告",
                "severity": "warning",
            })
        elif issue.issue_type == IssueType.DATA_ANOMALY:
            strategy.update({
                "action": "validate_and_flag",
                "description": "数据异常，标记并触发二次校验",
                "severity": "warning",
            })
        elif issue.issue_type == IssueType.SOURCE_UNAVAILABLE:
            strategy.update({
                "action": "switch_secondary_source",
                "description": "主源不可用，切换到备用数据源",
                "severity": "critical",
            })
        elif issue.issue_type == IssueType.TYPE_UNSUPPORTED:
            strategy.update({
                "action": "return_unsupported_error",
                "description": "数据类型不支持，返回明确错误",
                "severity": "info",
            })
        elif issue.issue_type == IssueType.SLOW_RESPONSE:
            strategy.update({
                "action": "enable_caching",
                "description": "响应慢，启用更激进的缓存策略",
                "severity": "warning",
            })

        logger.debug(
            f"[Issue] mitigation for {issue.issue_type.value}: "
            f"{strategy['action']}"
        )
        return strategy

    def unresolved(self, symbol: Optional[str] = None) -> list[DataIssue]:
        """获取未解决的问题列表。

        Args:
            symbol: 可选，按品种过滤

        Returns:
            未解决的 DataIssue 列表
        """
        if symbol is not None:
            return [
                i for i in self._issues
                if not i.resolved and i.symbol == symbol
            ]
        return [i for i in self._issues if not i.resolved]

    def resolve(self, symbol: str, data_type: str, resolution: str = "") -> int:
        """标记指定问题为已解决。

        Args:
            symbol: 品种代码
            data_type: 数据类型
            resolution: 解决说明

        Returns:
            标记解决的问题数量
        """
        count = 0
        for issue in self._issues:
            if (
                not issue.resolved
                and issue.symbol == symbol
                and issue.data_type == data_type
            ):
                issue.resolved = True
                issue.resolution = resolution
                count += 1
        return count

    def stats(self) -> dict:
        """聚合统计，供 get_health() 展示。

        Returns:
            包含各类统计数据的 dict
        """
        total = len(self._issues)
        resolved = sum(1 for i in self._issues if i.resolved)
        unresolved_count = total - resolved

        by_type: dict[str, int] = {}
        by_consumer: dict[str, int] = {}
        by_source: dict[str, int] = {}

        for issue in self._issues:
            type_key = issue.issue_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            by_consumer[issue.consumer] = by_consumer.get(issue.consumer, 0) + 1
            by_source[issue.source] = by_source.get(issue.source, 0) + 1

        unresolved_by_type: dict[str, int] = {}
        for issue in self._issues:
            if not issue.resolved:
                type_key = issue.issue_type.value
                unresolved_by_type[type_key] = unresolved_by_type.get(
                    type_key, 0
                ) + 1

        return {
            "total": total,
            "resolved": resolved,
            "unresolved": unresolved_count,
            "by_type": by_type,
            "by_consumer": by_consumer,
            "by_source": by_source,
            "unresolved_by_type": unresolved_by_type,
        }
