"""AKShare 封装骨架。

提供 AKShare 开源数据接口的适配器。
AKShare 为可选依赖，不可用时返回空结果。
"""

from __future__ import annotations

from typing import Any


class AKShareClient:
    """AKShare 开源数据客户端。

    封装 AKShare 的常用数据接口，提供统一调用方式。
    AKShare 为可选依赖，未安装时返回空结果。

    Attributes:
        name: 采集器名称。
        description: 采集器描述。
    """

    name: str = "akshare"
    description: str = "AKShare 开源金融数据接口封装"

    def __init__(self) -> None:
        """初始化 AKShare 客户端。"""
        self._ak = None

    def check_available(self) -> bool:
        """检查 AKShare 是否可用。

        Returns:
            True 表示可用，False 表示不可用。
        """
        try:
            import akshare  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_akshare(self) -> Any | None:
        """获取 akshare 模块。

        Returns:
            akshare 模块或 None。
        """
        if not self.check_available():
            return None
        if self._ak is None:
            import akshare
            self._ak = akshare
        return self._ak

    def fetch(self, api_name: str, **kwargs: Any) -> dict[str, Any]:
        """调用 AKShare 接口获取数据。

        Args:
            api_name: AKShare 接口函数名，如 'stock_zh_a_hist'。
            **kwargs: 接口参数。

        Returns:
            数据结果字典，包含：
            - success: 是否成功
            - api_name: 接口名
            - data: 数据（DataFrame 转 dict 列表）
            - error: 错误信息（失败时）
        """
        ak = self._get_akshare()
        if ak is None:
            return {
                "success": False,
                "api_name": api_name,
                "data": [],
                "error": "AKShare 未安装，请先 pip install akshare",
            }

        try:
            func = getattr(ak, api_name)
            result = func(**kwargs)

            if hasattr(result, "to_dict"):
                data = result.to_dict("records")
            else:
                data = result

            return {
                "success": True,
                "api_name": api_name,
                "data": data,
                "row_count": len(data) if isinstance(data, list) else None,
            }
        except AttributeError:
            return {
                "success": False,
                "api_name": api_name,
                "data": [],
                "error": f"接口不存在: {api_name}",
                "error_type": "AttributeError",
            }
        except Exception as e:
            return {
                "success": False,
                "api_name": api_name,
                "data": [],
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def get_stock_hist(self, symbol: str, period: str = "daily",
                       adjust: str = "", start_date: str = "",
                       end_date: str = "") -> dict[str, Any]:
        """获取股票历史行情数据（便捷方法）。

        Args:
            symbol: 股票代码。
            period: 周期，'daily' / 'weekly' / 'monthly'。
            adjust: 复权方式，'qfq' / 'hfq' / ''。
            start_date: 开始日期。
            end_date: 结束日期。

        Returns:
            行情数据结果。
        """
        params = {
            "symbol": symbol,
            "period": period,
        }
        if adjust:
            params["adjust"] = adjust
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self.fetch("stock_zh_a_hist", **params)

    def get_futures_hist(self, symbol: str, period: str = "daily",
                         start_date: str = "", end_date: str = "") -> dict[str, Any]:
        """获取期货历史行情数据（便捷方法）。

        Args:
            symbol: 期货合约代码。
            period: 周期。
            start_date: 开始日期。
            end_date: 结束日期。

        Returns:
            行情数据结果。
        """
        params = {
            "symbol": symbol,
            "period": period,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self.fetch("futures_hist", **params)
