"""数据清洗模块 — 纯函数风格的数据清洗工具集。

提供单位标准化、时间对齐、多源去重、异常过滤等核心清洗能力。
所有函数均为纯函数，输入输出为 DataFrame 或 dict。
"""

from .unit_unify import (
    convert_unit,
    batch_convert_units,
    auto_detect_unit,
    UNIT_FACTORS,
)
from .date_align import (
    align_to_trading_calendar,
    fill_missing_dates,
    infer_frequency,
)
from .duplicate_merge import (
    merge_by_weight,
    deduplicate_dataframe,
    merge_sources,
)
from .outlier_filter import (
    filter_outliers_3sigma,
    filter_outliers_iqr,
    detect_outliers,
    mark_outliers,
)

__all__ = [
    "convert_unit",
    "batch_convert_units",
    "auto_detect_unit",
    "UNIT_FACTORS",
    "align_to_trading_calendar",
    "fill_missing_dates",
    "infer_frequency",
    "merge_by_weight",
    "deduplicate_dataframe",
    "merge_sources",
    "filter_outliers_3sigma",
    "filter_outliers_iqr",
    "detect_outliers",
    "mark_outliers",
]
