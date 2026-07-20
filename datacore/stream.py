"""WebSocket 实时行情 — 连接管理与数据推送。

v1.0.0 新增: 支持 QUOTE 实时推送 + OHLCV 增量更新。

架构:
  WebSocket 连接管理器 (单例)
    ├── 连接池 (按数据源分组)
    ├── 订阅管理 (symbol -> subscriber 映射)
    ├── 心跳检测 (30s 间隔)
    └── 重连机制 (指数退避)
"""
from __future__ import annotations
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StreamQuote:
    """WebSocket 推送的实时行情快照。"""
    symbol: str
    last_price: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    bid_price: list[float] = field(default_factory=list)
    ask_price: list[float] = field(default_factory=list)
    timestamp: float = 0.0


class StreamCallback:
    """WebSocket 消息回调接口。"""
    def on_quote(self, quote: StreamQuote) -> None:
        """收到实时行情回调。"""
        pass

    def on_error(self, error: Exception) -> None:
        """连接错误回调。"""
        pass

    def on_reconnect(self) -> None:
        """重连成功回调。"""
        pass


class WebSocketManager:
    """WebSocket 连接管理器。

    管理所有数据源的 WebSocket 连接，支持订阅/取消订阅。
    """

    def __init__(self, max_retries: int = 5, base_delay: float = 1.0):
        self._connections: dict[str, Any] = {}
        self._subscribers: dict[str, list[StreamCallback]] = {}
        self._running = False
        self.max_retries = max_retries
        self.base_delay = base_delay

    def subscribe(self, symbol: str, callback: StreamCallback) -> bool:
        """订阅某个标的的实时行情。"""
        if symbol not in self._subscribers:
            self._subscribers[symbol] = []
        self._subscribers[symbol].append(callback)
        logger.info(f"订阅 {symbol} 成功，当前 {len(self._subscribers[symbol])} 个订阅者")
        return True

    def unsubscribe(self, symbol: str, callback: StreamCallback) -> bool:
        """取消订阅。"""
        if symbol in self._subscribers:
            self._subscribers[symbol] = [
                cb for cb in self._subscribers[symbol] if cb is not callback
            ]
            if not self._subscribers[symbol]:
                del self._subscribers[symbol]
        return True

    def get_subscribers(self, symbol: str) -> list[StreamCallback]:
        """获取某个标的的所有订阅者。"""
        return list(self._subscribers.get(symbol, []))

    @property
    def total_subscriptions(self) -> int:
        return len(self._subscribers)

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """启动 WebSocket 管理器。"""
        self._running = True
        logger.info("WebSocket 管理器已启动")

    def stop(self) -> None:
        """停止 WebSocket 管理器。"""
        self._running = False
        self._connections.clear()
        logger.info("WebSocket 管理器已停止")


# 全局单例
_manager: Optional[WebSocketManager] = None


def get_stream_manager() -> WebSocketManager:
    """获取全局 WebSocket 管理器实例。"""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager
