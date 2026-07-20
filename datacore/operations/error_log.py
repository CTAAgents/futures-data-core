"""结构化审计日志 — JSON 格式错误日志。"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorRecord:
    """错误记录。

    Attributes:
        timestamp: 时间戳（ISO 格式）。
        error_type: 错误类型。
        error_message: 错误信息。
        traceback: 堆栈信息。
        module: 模块名。
        function: 函数名。
        context: 上下文信息。
        severity: 严重级别。
    """

    timestamp: str
    error_type: str
    error_message: str
    traceback: str = ""
    module: str = ""
    function: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    severity: str = "ERROR"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "module": self.module,
            "function": self.function,
            "context": self.context,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


def create_error_record(
    exception: BaseException,
    *,
    module: str = "",
    function: str = "",
    context: dict[str, Any] | None = None,
    severity: str = "ERROR",
) -> ErrorRecord:
    """从异常创建错误记录。

    Args:
        exception: 异常对象。
        module: 模块名。
        function: 函数名。
        context: 上下文信息。
        severity: 严重级别。

    Returns:
        ErrorRecord 实例。

    Examples:
        >>> try:
        ...     raise ValueError("test error")
        ... except ValueError as e:
        ...     record = create_error_record(e, module="test", function="func")
        >>> record.error_type
        'ValueError'
        >>> record.error_message
        'test error'
    """
    from datetime import datetime

    tb_str = "".join(traceback.format_exception(
        type(exception), exception, exception.__traceback__
    ))

    return ErrorRecord(
        timestamp=datetime.now().isoformat(),
        error_type=type(exception).__name__,
        error_message=str(exception),
        traceback=tb_str,
        module=module,
        function=function,
        context=context or {},
        severity=severity,
    )


def log_error_json(
    exception: BaseException,
    *,
    module: str = "",
    function: str = "",
    context: dict[str, Any] | None = None,
    severity: str = "ERROR",
    logger: logging.Logger | None = None,
) -> str:
    """记录 JSON 格式的错误日志。

    Args:
        exception: 异常对象。
        module: 模块名。
        function: 函数名。
        context: 上下文信息。
        severity: 严重级别。
        logger: 日志记录器，默认使用 stderr 输出。

    Returns:
        JSON 格式的日志字符串。

    Examples:
        >>> try:
        ...     raise RuntimeError("test")
        ... except RuntimeError as e:
        ...     log_str = log_error_json(e, module="test")
        >>> isinstance(log_str, str)
        True
        >>> "RuntimeError" in log_str
        True
    """
    record = create_error_record(
        exception,
        module=module,
        function=function,
        context=context,
        severity=severity,
    )
    json_str = record.to_json()

    if logger:
        log_method = getattr(logger, severity.lower(), logger.error)
        log_method(json_str)
    else:
        print(json_str, file=sys.stderr)

    return json_str


class ErrorLogger:
    """结构化错误日志记录器。

    提供 JSON 格式的错误日志记录能力，支持上下文累积。
    """

    def __init__(
        self,
        name: str = "datacore",
        level: int = logging.INFO,
        output_file: str = "",
    ) -> None:
        """初始化错误日志记录器。

        Args:
            name: 日志记录器名称。
            level: 日志级别。
            output_file: 输出文件路径（可选）。
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self._context: dict[str, Any] = {}

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

        if output_file:
            file_handler = logging.FileHandler(output_file, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(file_handler)

    def add_context(self, **kwargs: Any) -> None:
        """添加上下文信息。

        Args:
            **kwargs: 上下文键值对。
        """
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """清除上下文信息。"""
        self._context.clear()

    def log_error(
        self,
        exception: BaseException,
        *,
        module: str = "",
        function: str = "",
        context: dict[str, Any] | None = None,
        severity: str = "ERROR",
    ) -> str:
        """记录错误。

        Args:
            exception: 异常对象。
            module: 模块名。
            function: 函数名。
            context: 额外上下文。
            severity: 严重级别。

        Returns:
            JSON 日志字符串。
        """
        merged_context = {**self._context, **(context or {})}
        return log_error_json(
            exception,
            module=module,
            function=function,
            context=merged_context,
            severity=severity,
            logger=self.logger,
        )

    def info(self, message: str, **kwargs: Any) -> None:
        """记录 INFO 级别日志。

        Args:
            message: 日志消息。
            **kwargs: 额外字段。
        """
        from datetime import datetime
        record = {
            "timestamp": datetime.now().isoformat(),
            "severity": "INFO",
            "message": message,
            **self._context,
            **kwargs,
        }
        self.logger.info(json.dumps(record, ensure_ascii=False, default=str))
