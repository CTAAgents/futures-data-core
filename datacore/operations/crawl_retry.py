"""指数退避重试 — 指数退避重试装饰器/函数。"""

from __future__ import annotations

import functools
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Type


@dataclass
class RetryConfig:
    """重试配置。

    Attributes:
        max_retries: 最大重试次数。
        base_delay: 基础延迟时间（秒）。
        max_delay: 最大延迟时间（秒）。
        backoff_factor: 退避因子。
        jitter: 是否添加随机抖动。
        retry_exceptions: 需要重试的异常类型列表。
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> float:
    """计算指数退避延迟时间。

    Args:
        attempt: 当前尝试次数（从 0 开始）。
        base_delay: 基础延迟时间（秒）。
        max_delay: 最大延迟时间（秒）。
        backoff_factor: 退避因子。
        jitter: 是否添加随机抖动。

    Returns:
        计算出的延迟时间（秒）。

    Examples:
        >>> delay = exponential_backoff(0, base_delay=1.0)
        >>> delay >= 1.0
        True
        >>> delay = exponential_backoff(3, base_delay=1.0, max_delay=10.0)
        >>> delay <= 10.0
        True
    """
    delay = base_delay * (backoff_factor ** attempt)
    delay = min(delay, max_delay)

    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)

    return delay


def retry_with_backoff(
    func: Callable[..., Any] | None = None,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: tuple[Type[Exception], ...] | None = None,
) -> Callable[..., Any]:
    """指数退避重试装饰器。

    可以直接作为装饰器使用，也可以带参数使用。

    Args:
        func: 被装饰的函数。
        max_retries: 最大重试次数。
        base_delay: 基础延迟时间（秒）。
        max_delay: 最大延迟时间（秒）。
        backoff_factor: 退避因子。
        jitter: 是否添加随机抖动。
        retry_exceptions: 需要重试的异常类型，默认所有 Exception。

    Returns:
        装饰后的函数。

    Examples:
        >>> @retry_with_backoff(max_retries=2, base_delay=0.01)
        ... def unstable_func():
        ...     return "success"
        >>> unstable_func()
        'success'
    """
    exceptions = retry_exceptions or (Exception,)

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = exponential_backoff(
                            attempt,
                            base_delay=base_delay,
                            max_delay=max_delay,
                            backoff_factor=backoff_factor,
                            jitter=jitter,
                        )
                        time.sleep(delay)
                    else:
                        raise

            raise last_exception  # type: ignore[misc]

        return wrapper

    if func is not None:
        return decorator(func)

    return decorator


def retry_call(
    func: Callable[..., Any],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Any:
    """带重试的函数调用（命令式风格）。

    Args:
        func: 要调用的函数。
        *args: 函数位置参数。
        config: 重试配置。
        **kwargs: 函数关键字参数。

    Returns:
        函数返回值。

    Raises:
        Exception: 超过最大重试次数后抛出最后一次异常。
    """
    cfg = config or RetryConfig()
    last_exception = None

    for attempt in range(cfg.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except cfg.retry_exceptions as e:
            last_exception = e
            if attempt < cfg.max_retries:
                delay = exponential_backoff(
                    attempt,
                    base_delay=cfg.base_delay,
                    max_delay=cfg.max_delay,
                    backoff_factor=cfg.backoff_factor,
                    jitter=cfg.jitter,
                )
                time.sleep(delay)
            else:
                raise

    raise last_exception  # type: ignore[misc]
