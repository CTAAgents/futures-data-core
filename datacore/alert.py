"""告警系统 — 基于指标收集框架。

v1.0.0 新增: 基于 MetricsCollector 的告警评估引擎。

功能:
  - 定义告警规则（成功率 < 90%、延迟 > 5s、熔断触发）
  - 告警评估引擎（定时评估规则）
  - 通知渠道（日志/文件/webhook）
"""
from __future__ import annotations
import json
import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """告警严重等级。"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态。"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AlertRule:
    """告警规则定义。"""
    name: str
    description: str = ""
    metric_key: str = ""           # 监控的指标键（如 "futures.tdx_lc.kline"）
    metric_field: str = ""         # 监控的指标字段（如 "success_rate"）
    operator: str = "lt"           # 比较操作符: lt/gt/eq
    threshold: float = 0.0         # 阈值
    severity: AlertSeverity = AlertSeverity.WARNING
    duration_seconds: int = 0      # 持续多久才触发（0=立即）
    enabled: bool = True


@dataclass
class AlertEvent:
    """告警事件。"""
    rule_name: str
    severity: AlertSeverity
    message: str
    status: AlertStatus = AlertStatus.ACTIVE
    triggered_at: float = 0.0
    resolved_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)


class AlertNotifier:
    """告警通知渠道基类。"""
    def send(self, event: AlertEvent) -> None:
        raise NotImplementedError


class LogNotifier(AlertNotifier):
    """日志通知渠道。"""
    def send(self, event: AlertEvent) -> None:
        level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.ERROR,
        }.get(event.severity, logging.INFO)
        logger.log(level, f"[ALERT] {event.severity.value}: {event.message}")


class FileNotifier(AlertNotifier):
    """文件通知渠道。"""
    def __init__(self, filepath: str = "alerts.log"):
        self.filepath = filepath

    def send(self, event: AlertEvent) -> None:
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "time": event.triggered_at,
                "severity": event.severity.value,
                "rule": event.rule_name,
                "message": event.message,
                "status": event.status.value,
            }, ensure_ascii=False) + "\n")


class WebhookNotifier(AlertNotifier):
    """Webhook 通知渠道。"""
    def __init__(self, url: str):
        self.url = url

    def send(self, event: AlertEvent) -> None:
        try:
            import httpx
            with httpx.Client(timeout=5) as c:
                c.post(self.url, json={
                    "severity": event.severity.value,
                    "rule": event.rule_name,
                    "message": event.message,
                    "timestamp": event.triggered_at,
                })
        except Exception as e:
            logger.warning(f"Webhook 通知失败: {e}")


class AlertEngine:
    """告警评估引擎。

    定时检查指标数据，匹配规则，触发告警。
    """

    def __init__(self):
        self.rules: list[AlertRule] = []
        self.notifiers: list[AlertNotifier] = [LogNotifier()]
        self._events: list[AlertEvent] = []
        self._last_check: dict[str, float] = {}

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def add_notifier(self, notifier: AlertNotifier) -> None:
        self.notifiers.append(notifier)

    def evaluate(self, metrics_snapshot: dict[str, dict]) -> list[AlertEvent]:
        """评估所有规则，返回新触发的告警事件。"""
        new_events = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.metric_key not in metrics_snapshot:
                continue
            metric = metrics_snapshot[rule.metric_key]
            if rule.metric_field not in metric:
                continue
            value = float(metric[rule.metric_field])

            # 比较
            triggered = False
            if rule.operator == "lt":
                triggered = value < rule.threshold
            elif rule.operator == "gt":
                triggered = value > rule.threshold
            elif rule.operator == "eq":
                triggered = abs(value - rule.threshold) < 0.001

            if triggered:
                # 检查是否已经触发过（避免重复告警）
                last_time = self._last_check.get(rule.name, 0)
                if time.time() - last_time > 300:  # 5分钟内不重复
                    event = AlertEvent(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"规则 {rule.name} 触发: {rule.metric_key}.{rule.metric_field} = {value} {self._op_symbol(rule.operator)} {rule.threshold}",
                        triggered_at=time.time(),
                        metadata={"metric_value": value, "threshold": rule.threshold},
                    )
                    self._events.append(event)
                    new_events.append(event)
                    self._last_check[rule.name] = time.time()
                    # 通知
                    for notifier in self.notifiers:
                        try:
                            notifier.send(event)
                        except Exception:
                            pass
            else:
                # 规则已恢复
                if rule.name in self._last_check:
                    # 查找之前 active 的告警并标记 resolved
                    for evt in self._events:
                        if evt.rule_name == rule.name and evt.status == AlertStatus.ACTIVE:
                            evt.status = AlertStatus.RESOLVED
                            evt.resolved_at = time.time()
                    del self._last_check[rule.name]

        return new_events

    @staticmethod
    def _op_symbol(op: str) -> str:
        return {"lt": "<", "gt": ">", "eq": "=="}.get(op, op)

    def get_active_alerts(self) -> list[AlertEvent]:
        return [e for e in self._events if e.status == AlertStatus.ACTIVE]

    def get_history(self, limit: int = 100) -> list[AlertEvent]:
        return self._events[-limit:]

    def acknowledge(self, rule_name: str) -> bool:
        for evt in self._events:
            if evt.rule_name == rule_name and evt.status == AlertStatus.ACTIVE:
                evt.status = AlertStatus.ACKNOWLEDGED
                return True
        return False


# 预置规则
DEFAULT_RULES = [
    AlertRule(
        name="success_rate_low",
        description="数据源成功率低于 90%",
        metric_key="",
        metric_field="success_rate",
        operator="lt",
        threshold=90.0,
        severity=AlertSeverity.WARNING,
    ),
    AlertRule(
        name="high_latency",
        description="数据源延迟超过 5s",
        metric_key="",
        metric_field="avg_duration",
        operator="gt",
        threshold=5.0,
        severity=AlertSeverity.WARNING,
    ),
    AlertRule(
        name="breaker_open",
        description="熔断器开启",
        metric_key="",
        metric_field="failures",
        operator="gt",
        threshold=3,
        severity=AlertSeverity.CRITICAL,
    ),
]


def create_default_engine() -> AlertEngine:
    """创建默认告警引擎（含预置规则）。"""
    engine = AlertEngine()
    for rule in DEFAULT_RULES:
        engine.add_rule(rule)
    engine.add_notifier(LogNotifier())
    return engine


# 全局单例
_engine: Optional[AlertEngine] = None


def get_alert_engine() -> AlertEngine:
    global _engine
    if _engine is None:
        _engine = create_default_engine()
    return _engine
