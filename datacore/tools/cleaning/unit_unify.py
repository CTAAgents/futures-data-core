"""UnitUnifyTool - 单位统一工具。"""

from __future__ import annotations

from typing import Any

from ..base import DataCoreBaseTool


class UnitUnifyTool(DataCoreBaseTool):
    """数据单位统一。

    将不同来源的数据单位统一为标准单位，如统一货币单位、
    统一数量级（万/亿/兆等）。
    """

    name = "datacore_unit_unify"
    description = (
        "数据单位统一。将不同来源的数据单位统一为标准单位。"
        "参数：data (list, 必需) - 数据列表；"
        "target_unit (str, 必需) - 目标单位；"
        "source_unit (str, 可选) - 源单位，不传则自动检测；"
        "fields (list, 可选) - 需要转换的字段名，默认转换所有数值字段"
    )

    def _run(self, data: list[dict[str, Any]], target_unit: str,
             source_unit: str = "", fields: list[str] | None = None,
             **kwargs: Any) -> dict[str, Any]:
        try:
            result_data = []
            converted_count = 0

            for item in data:
                new_item = dict(item)
                target_fields = fields if fields else [
                    k for k, v in item.items() if isinstance(v, (int, float))
                ]

                for field in target_fields:
                    if field in new_item and isinstance(new_item[field], (int, float)):
                        new_item[field] = self._convert(
                            new_item[field], source_unit, target_unit
                        )
                        converted_count += 1

                result_data.append(new_item)

            return {
                "success": True,
                "source_unit": source_unit or "auto",
                "target_unit": target_unit,
                "converted_fields": len(fields) if fields else "auto",
                "converted_count": converted_count,
                "data": result_data,
            }
        except Exception as e:
            return {
                "success": False,
                "target_unit": target_unit,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _convert(self, value: float, source_unit: str, target_unit: str) -> float:
        unit_factors = {
            "元": 1, "万元": 10000, "亿元": 100000000,
            "股": 1, "万股": 10000, "亿股": 100000000,
            "吨": 1, "万吨": 10000,
            "%": 0.01, "percent": 0.01,
        }

        src_factor = unit_factors.get(source_unit, 1)
        tgt_factor = unit_factors.get(target_unit, 1)

        return value * src_factor / tgt_factor
