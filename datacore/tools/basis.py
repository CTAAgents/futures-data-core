"""DataCoreBasisTool - 期现基差工具。"""

from __future__ import annotations

from typing import Any, Optional

from .base import DataCoreBaseTool
from .ohlcv import _payload_to_dict


class DataCoreBasisTool(DataCoreBaseTool):
    """获取期现基差数据。

    返回期货价格与现货价格的基差、基差率等数据。
    """

    name = "datacore_basis"
    description = (
        "获取期现基差数据。返回基差、基差率等。"
        "参数：symbol (str, 必需) - 品种代码；"
        "spot_price (float, 可选) - 现货价格，不传则使用内置现货数据；"
        "basis_type (str, 可选) - 基差类型，'absolute'/'ratio'/'both'，默认 'both'"
    )

    def _run(self, symbol: str, spot_price: Optional[float] = None,
             basis_type: str = "both", **kwargs: Any) -> dict[str, Any]:
        from ..api import UnifiedDataProvider
        from ..models.enums import DataType

        provider = UnifiedDataProvider()
        params = {"basis_type": basis_type}
        if spot_price is not None:
            params["spot_price"] = spot_price

        payload = provider.get(symbol, DataType.FUTURES_BASIS, params=params)
        return _payload_to_dict(payload)
