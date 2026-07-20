"""Tests for datacore.issue — 消费者反馈通道模块。"""
from __future__ import annotations

import pytest
from datacore.issue import IssueType, DataIssue, IssueRegistry
from datacore.api import UnifiedDataProvider


def _make_issue(
    symbol: str = "SHFE.ru2505",
    data_type: str = "ohlcv",
    issue_type: IssueType = IssueType.DATA_EMPTY,
    detail: str = "test detail",
    source: str = "tqsdk",
    consumer: str = "test_consumer",
) -> DataIssue:
    return DataIssue(
        symbol=symbol,
        data_type=data_type,
        issue_type=issue_type,
        detail=detail,
        source=source,
        consumer=consumer,
    )


class TestIssueType:
    def test_issue_type_has_six_values(self):
        """IssueType 枚举有 6 个值。"""
        assert len(IssueType) == 6

    def test_issue_type_data_empty(self):
        """IssueType.DATA_EMPTY 值正确。"""
        assert IssueType.DATA_EMPTY.value == "data_empty"

    def test_issue_type_data_stale(self):
        """IssueType.DATA_STALE 值正确。"""
        assert IssueType.DATA_STALE.value == "data_stale"

    def test_issue_type_data_anomaly(self):
        """IssueType.DATA_ANOMALY 值正确。"""
        assert IssueType.DATA_ANOMALY.value == "data_anomaly"

    def test_issue_type_source_unavailable(self):
        """IssueType.SOURCE_UNAVAILABLE 值正确。"""
        assert IssueType.SOURCE_UNAVAILABLE.value == "source_unavailable"

    def test_issue_type_type_unsupported(self):
        """IssueType.TYPE_UNSUPPORTED 值正确。"""
        assert IssueType.TYPE_UNSUPPORTED.value == "type_unsupported"

    def test_issue_type_slow_response(self):
        """IssueType.SLOW_RESPONSE 值正确。"""
        assert IssueType.SLOW_RESPONSE.value == "slow_response"

    def test_issue_type_is_str_enum(self):
        """IssueType 是 str 枚举，可直接比较字符串。"""
        assert IssueType.DATA_EMPTY == "data_empty"


class TestDataIssue:
    def test_data_issue_default_values(self):
        """DataIssue 默认值正确。"""
        issue = _make_issue()
        assert issue.timestamp == 0.0
        assert issue.resolved is False
        assert issue.resolution == ""

    def test_data_issue_fields(self):
        """DataIssue 所有字段赋值正确。"""
        issue = DataIssue(
            symbol="SHFE.ru2505",
            data_type="ohlcv",
            issue_type=IssueType.DATA_STALE,
            detail="data is 2 days old",
            source="tqsdk",
            consumer="strategy_alpha",
            timestamp=1234567890.0,
            resolved=True,
            resolution="fixed by restart",
        )
        assert issue.symbol == "SHFE.ru2505"
        assert issue.data_type == "ohlcv"
        assert issue.issue_type == IssueType.DATA_STALE
        assert issue.detail == "data is 2 days old"
        assert issue.source == "tqsdk"
        assert issue.consumer == "strategy_alpha"
        assert issue.timestamp == 1234567890.0
        assert issue.resolved is True
        assert issue.resolution == "fixed by restart"

    def test_data_issue_is_dataclass(self):
        """DataIssue 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(DataIssue)


class TestIssueRegistry:
    def test_init_empty(self):
        """初始时问题列表为空。"""
        reg = IssueRegistry()
        assert reg.unresolved() == []

    def test_report_adds_issue(self):
        """report() 添加问题到列表。"""
        reg = IssueRegistry()
        issue = _make_issue()
        result = reg.report(issue)
        assert result["reported"] is True
        assert result["issue_index"] == 0
        assert len(reg.unresolved()) == 1

    def test_report_sets_timestamp(self):
        """report() 自动设置 timestamp。"""
        reg = IssueRegistry()
        issue = _make_issue()
        assert issue.timestamp == 0.0
        reg.report(issue)
        assert issue.timestamp > 0.0

    def test_report_preserves_existing_timestamp(self):
        """report() 保留已有 timestamp。"""
        reg = IssueRegistry()
        issue = _make_issue()
        issue.timestamp = 999.0
        reg.report(issue)
        assert issue.timestamp == 999.0

    def test_report_returns_mitigation(self):
        """report() 返回自动应对策略。"""
        reg = IssueRegistry()
        issue = _make_issue(issue_type=IssueType.DATA_EMPTY)
        result = reg.report(issue)
        assert "mitigation" in result
        assert result["mitigation"]["action"] == "fallback_to_cache"

    def test_auto_mitigate_data_empty(self):
        """_auto_mitigate DATA_EMPTY 返回缓存回退。"""
        reg = IssueRegistry()
        issue = _make_issue(issue_type=IssueType.DATA_EMPTY)
        m = reg._auto_mitigate(issue)
        assert m["action"] == "fallback_to_cache"
        assert m["severity"] == "warning"

    def test_auto_mitigate_data_stale(self):
        """_auto_mitigate DATA_STALE 返回过期警告。"""
        reg = IssueRegistry()
        issue = _make_issue(issue_type=IssueType.DATA_STALE)
        m = reg._auto_mitigate(issue)
        assert m["action"] == "use_stale_with_warning"
        assert m["severity"] == "warning"

    def test_auto_mitigate_data_anomaly(self):
        """_auto_mitigate DATA_ANOMALY 返回校验标记。"""
        reg = IssueRegistry()
        issue = _make_issue(issue_type=IssueType.DATA_ANOMALY)
        m = reg._auto_mitigate(issue)
        assert m["action"] == "validate_and_flag"
        assert m["severity"] == "warning"

    def test_auto_mitigate_source_unavailable(self):
        """_auto_mitigate SOURCE_UNAVAILABLE 返回切换源。"""
        reg = IssueRegistry()
        issue = _make_issue(issue_type=IssueType.SOURCE_UNAVAILABLE)
        m = reg._auto_mitigate(issue)
        assert m["action"] == "switch_secondary_source"
        assert m["severity"] == "critical"

    def test_auto_mitigate_type_unsupported(self):
        """_auto_mitigate TYPE_UNSUPPORTED 返回不支持错误。"""
        reg = IssueRegistry()
        issue = _make_issue(issue_type=IssueType.TYPE_UNSUPPORTED)
        m = reg._auto_mitigate(issue)
        assert m["action"] == "return_unsupported_error"
        assert m["severity"] == "info"

    def test_auto_mitigate_slow_response(self):
        """_auto_mitigate SLOW_RESPONSE 返启用缓存。"""
        reg = IssueRegistry()
        issue = _make_issue(issue_type=IssueType.SLOW_RESPONSE)
        m = reg._auto_mitigate(issue)
        assert m["action"] == "enable_caching"
        assert m["severity"] == "warning"

    def test_unresolved_no_filter(self):
        """unresolved() 不过滤返回所有未解决问题。"""
        reg = IssueRegistry()
        reg.report(_make_issue(symbol="A"))
        reg.report(_make_issue(symbol="B"))
        assert len(reg.unresolved()) == 2

    def test_unresolved_with_symbol_filter(self):
        """unresolved(symbol) 按品种过滤。"""
        reg = IssueRegistry()
        reg.report(_make_issue(symbol="SHFE.ru2505"))
        reg.report(_make_issue(symbol="SHFE.au2506"))
        result = reg.unresolved(symbol="SHFE.ru2505")
        assert len(result) == 1
        assert result[0].symbol == "SHFE.ru2505"

    def test_resolve_marks_resolved(self):
        """resolve() 标记问题为已解决。"""
        reg = IssueRegistry()
        reg.report(_make_issue(symbol="SHFE.ru2505", data_type="ohlcv"))
        count = reg.resolve("SHFE.ru2505", "ohlcv", "data fixed")
        assert count == 1
        assert len(reg.unresolved()) == 0

    def test_resolve_returns_count(self):
        """resolve() 返回解决的问题数量。"""
        reg = IssueRegistry()
        reg.report(_make_issue(symbol="SHFE.ru2505", data_type="ohlcv"))
        reg.report(_make_issue(symbol="SHFE.ru2505", data_type="ohlcv"))
        reg.report(_make_issue(symbol="SHFE.au2506", data_type="ohlcv"))
        count = reg.resolve("SHFE.ru2505", "ohlcv", "fixed")
        assert count == 2

    def test_resolve_no_match(self):
        """resolve() 无匹配返回 0。"""
        reg = IssueRegistry()
        reg.report(_make_issue(symbol="A", data_type="ohlcv"))
        count = reg.resolve("B", "ohlcv", "fixed")
        assert count == 0
        assert len(reg.unresolved()) == 1

    def test_stats_empty(self):
        """stats() 空注册表返回零统计。"""
        reg = IssueRegistry()
        s = reg.stats()
        assert s["total"] == 0
        assert s["resolved"] == 0
        assert s["unresolved"] == 0
        assert s["by_type"] == {}
        assert s["by_consumer"] == {}
        assert s["by_source"] == {}
        assert s["unresolved_by_type"] == {}

    def test_stats_aggregates(self):
        """stats() 聚合统计正确。"""
        reg = IssueRegistry()
        reg.report(_make_issue(
            symbol="A", data_type="ohlcv", issue_type=IssueType.DATA_EMPTY,
            consumer="c1", source="s1",
        ))
        reg.report(_make_issue(
            symbol="A", data_type="kline", issue_type=IssueType.DATA_STALE,
            consumer="c1", source="s2",
        ))
        reg.report(_make_issue(
            symbol="B", data_type="ohlcv", issue_type=IssueType.DATA_EMPTY,
            consumer="c2", source="s1",
        ))
        reg.resolve("A", "ohlcv", "fixed")

        s = reg.stats()
        assert s["total"] == 3
        assert s["resolved"] == 1
        assert s["unresolved"] == 2
        assert s["by_type"]["data_empty"] == 2
        assert s["by_type"]["data_stale"] == 1
        assert s["by_consumer"]["c1"] == 2
        assert s["by_consumer"]["c2"] == 1
        assert s["by_source"]["s1"] == 2
        assert s["by_source"]["s2"] == 1
        assert s["unresolved_by_type"]["data_empty"] == 1
        assert s["unresolved_by_type"]["data_stale"] == 1


class TestUnifiedDataProviderIntegration:
    def test_provider_has_issue_registry(self):
        """UnifiedDataProvider 有 _issues 属性。"""
        dp = UnifiedDataProvider()
        assert hasattr(dp, "_issues")
        assert isinstance(dp._issues, IssueRegistry)

    def test_report_issue_method(self):
        """UnifiedDataProvider.report_issue() 方法可用。"""
        dp = UnifiedDataProvider()
        issue = _make_issue()
        result = dp.report_issue(issue)
        assert result["reported"] is True
        assert len(dp._issues.unresolved()) == 1

    def test_get_health_includes_consumer_issues(self):
        """get_health() 返回结果包含 consumer_issues 字段。"""
        dp = UnifiedDataProvider()
        health = dp.get_health()
        assert "consumer_issues" in health
        assert "total" in health["consumer_issues"]
        assert "unresolved" in health["consumer_issues"]

    def test_get_health_consumer_issues_updates(self):
        """get_health() 中 consumer_issues 随上报更新。"""
        dp = UnifiedDataProvider()
        health_before = dp.get_health()
        assert health_before["consumer_issues"]["total"] == 0

        dp.report_issue(_make_issue())
        health_after = dp.get_health()
        assert health_after["consumer_issues"]["total"] == 1
        assert health_after["consumer_issues"]["unresolved"] == 1


class TestMultiConsumerStats:
    def test_multiple_consumers_aggregation(self):
        """多消费者聚合统计正确。"""
        reg = IssueRegistry()

        consumers = ["alpha", "beta", "gamma"]
        for i, c in enumerate(consumers):
            for j in range(i + 1):
                reg.report(_make_issue(
                    symbol=f"SYM{i}{j}",
                    issue_type=list(IssueType)[j % len(IssueType)],
                    consumer=c,
                    source=f"src{j % 3}",
                ))

        s = reg.stats()
        assert s["total"] == 6  # 1 + 2 + 3
        assert s["by_consumer"]["alpha"] == 1
        assert s["by_consumer"]["beta"] == 2
        assert s["by_consumer"]["gamma"] == 3
        assert s["by_source"]["src0"] == 3
        assert s["by_source"]["src1"] == 2
        assert s["by_source"]["src2"] == 1
