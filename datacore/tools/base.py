"""DataCoreBaseTool - 自定义工具基类，兼容 LangChain BaseTool 协议。

不依赖 LangChain 的 BaseTool 类，而是实现符合其协议的自定义基类。
没有 langchain 也能用，有 langchain 时可以无缝接入。
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

try:
    import pydantic  # noqa: F401
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class DataCoreBaseTool(ABC):
    """DataCore 工具基类，兼容 LangChain BaseTool 协议。

    Attributes:
        name: 工具名称，格式为 "datacore_xxx"
        description: 工具功能描述
        args_schema: 参数 schema（可选，pydantic BaseModel 类）
        return_direct: 是否直接返回结果（LangChain 兼容）
        verbose: 是否输出详细日志
    """

    name: str = ""
    description: str = ""
    args_schema: Optional[Type[Any]] = None
    return_direct: bool = False
    verbose: bool = False

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @abstractmethod
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """同步执行工具。

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            工具执行结果
        """
        raise NotImplementedError

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """异步执行工具（默认调用同步版本）。

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            工具执行结果
        """
        return await asyncio.to_thread(self._run, *args, **kwargs)

    def invoke(self, input: dict[str, Any] | None = None,
               config: Any = None, **kwargs: Any) -> dict[str, Any]:
        """LangChain 兼容的调用接口。

        Args:
            input: 输入参数字典
            config: 配置（LangChain 兼容，可选）
            **kwargs: 额外关键字参数

        Returns:
            执行结果字典
        """
        input = input or {}
        merged = {**input, **kwargs}
        try:
            result = self._run(**merged)
            return {"success": True, "result": result, "tool_name": self.name}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool_name": self.name,
                "error_type": type(e).__name__,
            }

    async def ainvoke(self, input: dict[str, Any] | None = None,
                      config: Any = None, **kwargs: Any) -> dict[str, Any]:
        """异步版本的 invoke。

        Args:
            input: 输入参数字典
            config: 配置（LangChain 兼容，可选）
            **kwargs: 额外关键字参数

        Returns:
            执行结果字典
        """
        input = input or {}
        merged = {**input, **kwargs}
        try:
            result = await self._arun(**merged)
            return {"success": True, "result": result, "tool_name": self.name}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool_name": self.name,
                "error_type": type(e).__name__,
            }

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """支持直接调用工具实例。"""
        return self._run(*args, **kwargs)

    def _to_dict(self) -> dict[str, Any]:
        """序列化为字典（用于调试和序列化）。"""
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self.args_schema.__name__ if self.args_schema else None,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
