"""多源去重 — 多源数据按权重合并，高优先级覆盖低优先级。"""

from __future__ import annotations


import numpy as np
import pandas as pd


def deduplicate_dataframe(
    df: pd.DataFrame,
    keys: list[str],
    strategy: str = "first",
) -> pd.DataFrame:
    """对 DataFrame 按指定键去重。

    Args:
        df: 输入 DataFrame。
        keys: 判断重复的键字段列表。
        strategy: 去重策略：
            - 'first': 保留第一条
            - 'last': 保留最后一条
            - 'mean': 数值字段取均值，非数值取第一条
            - 'max': 数值字段取最大值
            - 'min': 数值字段取最小值

    Returns:
        去重后的 DataFrame。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "id": [1, 1, 2],
        ...     "value": [10, 20, 30],
        ... })
        >>> deduplicate_dataframe(df, ["id"], "first")["value"].tolist()
        [10, 30]
    """
    if df.empty:
        return df.copy()

    if strategy == "first":
        return df.drop_duplicates(subset=keys, keep="first").reset_index(drop=True)
    elif strategy == "last":
        return df.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)
    elif strategy == "mean":
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        agg_dict: dict[str, str] = {}
        for col in df.columns:
            if col in keys:
                continue
            if col in numeric_cols:
                agg_dict[col] = "mean"
            else:
                agg_dict[col] = "first"
        return df.groupby(keys, as_index=False).agg(agg_dict)
    elif strategy == "max":
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        agg_dict = {}
        for col in df.columns:
            if col in keys:
                continue
            if col in numeric_cols:
                agg_dict[col] = "max"
            else:
                agg_dict[col] = "first"
        return df.groupby(keys, as_index=False).agg(agg_dict)
    elif strategy == "min":
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        agg_dict = {}
        for col in df.columns:
            if col in keys:
                continue
            if col in numeric_cols:
                agg_dict[col] = "min"
            else:
                agg_dict[col] = "first"
        return df.groupby(keys, as_index=False).agg(agg_dict)
    else:
        return df.drop_duplicates(subset=keys, keep="first").reset_index(drop=True)


def merge_by_weight(
    source_data: dict[str, pd.DataFrame],
    weights: dict[str, float],
    keys: list[str],
    value_cols: list[str] | None = None,
) -> pd.DataFrame:
    """按权重合并多源数据，高权重覆盖低权重。

    对于数值字段，使用加权平均；对于非数值字段，使用最高权重源的值。

    Args:
        source_data: 多源数据字典，key 为源名，value 为 DataFrame。
        weights: 各数据源的权重字典，key 为源名，value 为权重值（数值越大优先级越高）。
        keys: 对齐键字段列表。
        value_cols: 需要合并的值字段列表，默认所有数值字段。

    Returns:
        合并后的 DataFrame。

    Examples:
        >>> import pandas as pd
        >>> src1 = pd.DataFrame({"date": ["2024-01-01"], "price": [100]})
        >>> src2 = pd.DataFrame({"date": ["2024-01-01"], "price": [110]})
        >>> result = merge_by_weight(
        ...     {"s1": src1, "s2": src2},
        ...     {"s1": 0.4, "s2": 0.6},
        ...     ["date"],
        ...     ["price"],
        ... )
        >>> round(result["price"].iloc[0], 1)
        106.0
    """
    if not source_data:
        return pd.DataFrame()

    sorted_sources = sorted(weights.keys(), key=lambda s: weights[s], reverse=True)
    available_sources = [s for s in sorted_sources if s in source_data]

    if not available_sources:
        return pd.DataFrame()

    all_dfs = []
    for src in available_sources:
        df = source_data[src].copy()
        df["_source"] = src
        df["_weight"] = weights[src]
        all_dfs.append(df)

    combined = pd.concat(all_dfs, ignore_index=True)

    if value_cols is None:
        value_cols = combined.select_dtypes(include=[np.number]).columns.tolist()
        value_cols = [c for c in value_cols if c not in keys and c != "_weight"]

    top_source = available_sources[0]
    base_df = source_data[top_source].copy()
    base_df = base_df.set_index(keys)

    result = base_df.copy()

    for src in available_sources[1:]:
        src_df = source_data[src].set_index(keys)
        for col in value_cols:
            if col in src_df.columns and col in result.columns:
                mask = result[col].isna() & src_df[col].notna()
                result.loc[mask, col] = src_df.loc[mask, col]

    numeric_cols = [c for c in value_cols if c in result.columns]

    for col in numeric_cols:
        values_by_source = {}
        for src in available_sources:
            src_df = source_data[src]
            if col in src_df.columns:
                temp = src_df.set_index(keys)[col]
                values_by_source[src] = temp

        if not values_by_source:
            continue

        combined_col = pd.DataFrame(values_by_source)
        weighted_sum = pd.Series(0.0, index=combined_col.index)
        weight_sum = pd.Series(0.0, index=combined_col.index)

        for src in available_sources:
            if src not in combined_col.columns:
                continue
            w = weights[src]
            valid = combined_col[src].notna()
            weighted_sum[valid] += combined_col.loc[valid, src] * w
            weight_sum[valid] += w

        result[col] = weighted_sum / weight_sum.replace(0, np.nan)

    return result.reset_index()


def merge_sources(
    source_data: dict[str, pd.DataFrame],
    keys: list[str],
    priority: list[str] | None = None,
) -> pd.DataFrame:
    """按优先级合并多源数据，高优先级覆盖低优先级。

    Args:
        source_data: 多源数据字典。
        keys: 对齐键字段列表。
        priority: 优先级列表（从高到低），默认按字典顺序。

    Returns:
        合并后的 DataFrame。

    Examples:
        >>> import pandas as pd
        >>> src1 = pd.DataFrame({"date": ["2024-01-01"], "val": [100]})
        >>> src2 = pd.DataFrame({"date": ["2024-01-01"], "val": [200]})
        >>> result = merge_sources(
        ...     {"high": src1, "low": src2},
        ...     ["date"],
        ...     ["high", "low"],
        ... )
        >>> result["val"].iloc[0]
        100
    """
    if not source_data:
        return pd.DataFrame()

    if priority is None:
        priority = list(source_data.keys())

    result = None
    for src_name in priority:
        if src_name not in source_data:
            continue
        src_df = source_data[src_name].set_index(keys)
        if result is None:
            result = src_df.copy()
        else:
            for col in src_df.columns:
                if col not in result.columns:
                    result[col] = src_df[col]
                else:
                    mask = result[col].isna()
                    result.loc[mask, col] = src_df.loc[mask, col]

    return result.reset_index() if result is not None else pd.DataFrame()
