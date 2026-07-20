"""数据校验模块 — 纯函数风格的数据校验工具集。

提供数据源权重、多源交叉验证、缺失检测、衍生因子计算等能力。
所有函数均为纯函数，输入输出为 DataFrame 或 dict。
"""

from .weight_score import (
    SourceWeight,
    DEFAULT_SOURCE_WEIGHTS,
    calculate_source_score,
    get_source_weight,
)
from .cross_source import (
    cross_validate_sources,
    calculate_deviation_rate,
    consistency_report,
)
from .missing_detect import (
    detect_missing_values,
    find_continuous_missing,
    calculate_completeness,
)
from .cal_math import (
    calc_yoy,
    calc_mom,
    calc_basis_rate,
    calc_inventory_consumption_ratio,
    calc_processing_profit,
    calc_seasonal_index,
)

__all__ = [
    "SourceWeight",
    "DEFAULT_SOURCE_WEIGHTS",
    "calculate_source_score",
    "get_source_weight",
    "cross_validate_sources",
    "calculate_deviation_rate",
    "consistency_report",
    "detect_missing_values",
    "find_continuous_missing",
    "calculate_completeness",
    "calc_yoy",
    "calc_mom",
    "calc_basis_rate",
    "calc_inventory_consumption_ratio",
    "calc_processing_profit",
    "calc_seasonal_index",
]
