"""单位标准化 — 支持吨/万吨/元/美元等单位映射和转换。"""

from __future__ import annotations


import pandas as pd

UNIT_FACTORS: dict[str, float] = {
    "吨": 1.0,
    "万吨": 10000.0,
    "亿吨": 100000000.0,
    "千克": 0.001,
    "公斤": 0.001,
    "克": 1e-6,
    "元": 1.0,
    "万元": 10000.0,
    "亿元": 100000000.0,
    "美元": 7.2,
    "万美元": 72000.0,
    "股": 1.0,
    "万股": 10000.0,
    "亿股": 100000000.0,
    "%": 0.01,
    "百分比": 0.01,
    "percent": 0.01,
    "bp": 0.0001,
    "基点": 0.0001,
}


def convert_unit(value: float, source_unit: str, target_unit: str) -> float:
    """将数值从源单位转换为目标单位。

    Args:
        value: 待转换的数值。
        source_unit: 源单位名称，必须在 UNIT_FACTORS 中。
        target_unit: 目标单位名称，必须在 UNIT_FACTORS 中。

    Returns:
        转换后的数值。

    Raises:
        KeyError: 源单位或目标单位不在支持列表中。

    Examples:
        >>> convert_unit(1, "万吨", "吨")
        10000.0
        >>> convert_unit(10000, "元", "万元")
        1.0
    """
    src_factor = UNIT_FACTORS[source_unit]
    tgt_factor = UNIT_FACTORS[target_unit]
    return value * src_factor / tgt_factor


def auto_detect_unit(text: str) -> str | None:
    """从文本中自动检测单位。

    Args:
        text: 包含单位的文本，如 "产量(万吨)"、"价格_元"。

    Returns:
        检测到的单位名称，未检测到则返回 None。

    Examples:
        >>> auto_detect_unit("产量(万吨)")
        '万吨'
        >>> auto_detect_unit("price_usd")
        '美元'
    """
    lower_text = text.lower()
    for unit in sorted(UNIT_FACTORS.keys(), key=len, reverse=True):
        if unit.lower() in lower_text:
            return unit
    usd_aliases = ["usd", "美元", "美金"]
    for alias in usd_aliases:
        if alias in lower_text:
            return "美元"
    return None


def batch_convert_units(
    df: pd.DataFrame,
    field_unit_map: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    """批量转换 DataFrame 中多个字段的单位。

    Args:
        df: 输入 DataFrame。
        field_unit_map: 字段映射字典，key 为字段名，
            value 为 (source_unit, target_unit) 元组。

    Returns:
        单位转换后的 DataFrame（副本，不修改原 DataFrame）。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"产量": [1, 2], "金额": [10000, 20000]})
        >>> result = batch_convert_units(df, {
        ...     "产量": ("万吨", "吨"),
        ...     "金额": ("元", "万元"),
        ... })
        >>> result["产量"].tolist()
        [10000.0, 20000.0]
        >>> result["金额"].tolist()
        [1.0, 2.0]
    """
    result = df.copy()
    for field, (src_unit, tgt_unit) in field_unit_map.items():
        if field in result.columns:
            result[field] = result[field].apply(
                lambda x: convert_unit(float(x), src_unit, tgt_unit)
                if pd.notna(x) else x
            )
    return result
