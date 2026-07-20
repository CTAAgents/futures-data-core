"""多源交叉验证 — 多源数据之间的一致性校验，计算偏差率。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def calculate_deviation_rate(
    base: pd.Series | np.ndarray | list[float],
    compare: pd.Series | np.ndarray | list[float],
) -> dict[str, float]:
    """计算两组数据的偏差率。

    Args:
        base: 基准数据序列。
        compare: 对比数据序列。

    Returns:
        偏差统计字典，包含：
        - avg_deviation: 平均偏差率
        - max_deviation: 最大偏差率
        - min_deviation: 最小偏差率
        - std_deviation: 偏差率标准差
        - consistent_rate: 一致率（偏差<1%的比例）

    Examples:
        >>> base = [100, 200, 300]
        >>> compare = [101, 198, 305]
        >>> result = calculate_deviation_rate(base, compare)
        >>> "avg_deviation" in result
        True
    """
    base_arr = np.array(base, dtype=float)
    compare_arr = np.array(compare, dtype=float)

    valid_mask = (base_arr != 0) & ~np.isnan(base_arr) & ~np.isnan(compare_arr)
    if not valid_mask.any():
        return {
            "avg_deviation": 0.0,
            "max_deviation": 0.0,
            "min_deviation": 0.0,
            "std_deviation": 0.0,
            "consistent_rate": 0.0,
            "valid_points": 0,
        }

    base_valid = base_arr[valid_mask]
    compare_valid = compare_arr[valid_mask]

    deviation = np.abs(compare_valid - base_valid) / np.abs(base_valid)

    consistent = (deviation <= 0.01).sum()
    total = len(deviation)

    return {
        "avg_deviation": float(np.mean(deviation)),
        "max_deviation": float(np.max(deviation)),
        "min_deviation": float(np.min(deviation)),
        "std_deviation": float(np.std(deviation)),
        "consistent_rate": float(consistent / total) if total > 0 else 0.0,
        "valid_points": int(total),
    }


def cross_validate_sources(
    source_data: dict[str, pd.DataFrame],
    field: str,
    key_field: str = "datetime",
    base_source: str | None = None,
) -> dict[str, Any]:
    """多源数据交叉验证。

    Args:
        source_data: 多源数据字典，key 为源名，value 为 DataFrame。
        field: 要对比的字段名。
        key_field: 对齐键字段，默认 'datetime'。
        base_source: 基准源名，默认使用第一个数据源。

    Returns:
        交叉验证结果字典，包含各源与基准源的偏差统计。

    Examples:
        >>> import pandas as pd
        >>> s1 = pd.DataFrame({"date": [1, 2, 3], "price": [100, 200, 300]})
        >>> s2 = pd.DataFrame({"date": [1, 2, 3], "price": [101, 198, 305]})
        >>> result = cross_validate_sources(
        ...     {"s1": s1, "s2": s2},
        ...     field="price",
        ...     key_field="date",
        ... )
        >>> "comparisons" in result
        True
    """
    if len(source_data) < 2:
        return {
            "success": False,
            "error": "至少需要2个数据源进行交叉验证",
            "source_count": len(source_data),
        }

    sources = list(source_data.keys())
    base = base_source if base_source else sources[0]

    if base not in source_data:
        return {
            "success": False,
            "error": f"基准源 {base} 不存在",
            "available_sources": sources,
        }

    base_df = source_data[base].set_index(key_field)
    if field not in base_df.columns:
        return {
            "success": False,
            "error": f"基准源缺少字段 {field}",
            "base_source": base,
        }

    comparisons: dict[str, dict[str, float]] = {}
    all_valid_count = 0

    for src_name, src_df in source_data.items():
        if src_name == base:
            continue

        src = src_df.set_index(key_field)
        if field not in src.columns:
            comparisons[src_name] = {
                "error": f"缺少字段 {field}",
                "valid_points": 0,
            }
            continue

        merged = pd.merge(
            base_df[[field]],
            src[[field]],
            left_index=True,
            right_index=True,
            suffixes=("_base", "_comp"),
        )

        if merged.empty:
            comparisons[src_name] = {
                "valid_points": 0,
                "avg_deviation": 0.0,
                "consistent_rate": 0.0,
            }
            continue

        stats = calculate_deviation_rate(
            merged[f"{field}_base"].values,
            merged[f"{field}_comp"].values,
        )
        comparisons[src_name] = stats
        all_valid_count += stats["valid_points"]

    overall_consistency = 0.0
    valid_comparisons = [
        v for v in comparisons.values() if "consistent_rate" in v
    ]
    if valid_comparisons:
        overall_consistency = float(
            np.mean([v["consistent_rate"] for v in valid_comparisons])
        )

    return {
        "success": True,
        "base_source": base,
        "field": field,
        "source_count": len(source_data),
        "comparisons": comparisons,
        "overall_consistency": overall_consistency,
    }


def consistency_report(
    source_data: dict[str, pd.DataFrame],
    fields: list[str],
    key_field: str = "datetime",
) -> pd.DataFrame:
    """生成多源数据一致性报告。

    Args:
        source_data: 多源数据字典。
        fields: 要对比的字段列表。
        key_field: 对齐键字段。

    Returns:
        一致性报告 DataFrame，每行是一个字段的对比结果。

    Examples:
        >>> import pandas as pd
        >>> s1 = pd.DataFrame({"date": [1, 2], "price": [100, 200], "vol": [10, 20]})
        >>> s2 = pd.DataFrame({"date": [1, 2], "price": [101, 198], "vol": [11, 19]})
        >>> report = consistency_report({"s1": s1, "s2": s2}, ["price", "vol"], "date")
        >>> isinstance(report, pd.DataFrame)
        True
    """
    rows = []

    for field in fields:
        result = cross_validate_sources(source_data, field, key_field)
        if not result["success"]:
            rows.append({
                "field": field,
                "error": result.get("error", "未知错误"),
                "overall_consistency": None,
            })
            continue

        row = {
            "field": field,
            "base_source": result["base_source"],
            "overall_consistency": result["overall_consistency"],
        }
        for src_name, stats in result["comparisons"].items():
            if "consistent_rate" in stats:
                row[f"{src_name}_consistency"] = stats["consistent_rate"]
                row[f"{src_name}_avg_deviation"] = stats["avg_deviation"]
                row[f"{src_name}_valid_points"] = stats["valid_points"]
        rows.append(row)

    return pd.DataFrame(rows)
