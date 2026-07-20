"""衍生因子计算 — 库存同比/基差率/季节性/加工利润等。"""

from __future__ import annotations


import numpy as np
import pandas as pd


def calc_yoy(
    df: pd.DataFrame,
    value_col: str,
    date_col: str = "datetime",
    periods: int = 12,
) -> pd.Series:
    """计算同比增长率。

    同比 = (本期值 - 同期值) / |同期值| * 100%

    Args:
        df: 输入 DataFrame，必须包含日期列和数值列。
        value_col: 数值列名。
        date_col: 日期列名。
        periods: 同比周期数，月度数据用 12，周度数据用 52。

    Returns:
        同比增长率序列（单位：小数，如 0.05 表示 5%）。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "datetime": pd.date_range("2023-01-01", periods=13, freq="MS"),
        ...     "value": range(100, 113),
        ... })
        >>> yoy = calc_yoy(df, "value")
        >>> not pd.isna(yoy.iloc[-1])
        True
    """
    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col])
    result = result.set_index(date_col).sort_index()

    if value_col not in result.columns:
        return pd.Series(dtype=float)

    prev = result[value_col].shift(periods)
    yoy = (result[value_col] - prev) / prev.abs()

    return yoy.reset_index(drop=True)


def calc_mom(
    df: pd.DataFrame,
    value_col: str,
    date_col: str = "datetime",
    periods: int = 1,
) -> pd.Series:
    """计算环比增长率。

    环比 = (本期值 - 上期值) / |上期值| * 100%

    Args:
        df: 输入 DataFrame。
        value_col: 数值列名。
        date_col: 日期列名。
        periods: 环比周期数，默认 1。

    Returns:
        环比增长率序列（单位：小数）。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
        ...     "value": [100, 105, 103, 110, 108],
        ... })
        >>> mom = calc_mom(df, "value")
        >>> len(mom)
        5
    """
    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col])
    result = result.set_index(date_col).sort_index()

    if value_col not in result.columns:
        return pd.Series(dtype=float)

    prev = result[value_col].shift(periods)
    mom = (result[value_col] - prev) / prev.abs()

    return mom.reset_index(drop=True)


def calc_basis_rate(
    spot_price: pd.Series | np.ndarray | list[float],
    futures_price: pd.Series | np.ndarray | list[float],
) -> pd.Series:
    """计算基差率。

    基差率 = (现货价格 - 期货价格) / 现货价格 * 100%

    Args:
        spot_price: 现货价格序列。
        futures_price: 期货价格序列。

    Returns:
        基差率序列（单位：小数，正值表示现货升水）。

    Examples:
        >>> spot = [100, 105, 103]
        >>> futures = [102, 104, 101]
        >>> basis = calc_basis_rate(spot, futures)
        >>> len(basis)
        3
    """
    spot_arr = pd.Series(spot_price).astype(float)
    fut_arr = pd.Series(futures_price).astype(float)

    basis_rate = (spot_arr - fut_arr) / spot_arr.abs()

    return basis_rate


def calc_inventory_consumption_ratio(
    inventory: pd.Series | np.ndarray | list[float],
    consumption: pd.Series | np.ndarray | list[float],
) -> pd.Series:
    """计算库存消费比。

    库存消费比 = 库存 / 消费

    Args:
        inventory: 库存量序列。
        consumption: 消费量序列（同期）。

    Returns:
        库存消费比序列。

    Examples:
        >>> inv = [1000, 1200, 1100]
        >>> cons = [500, 600, 550]
        >>> ratio = calc_inventory_consumption_ratio(inv, cons)
        >>> ratio.iloc[0]
        2.0
    """
    inv_arr = pd.Series(inventory).astype(float)
    cons_arr = pd.Series(consumption).astype(float)

    ratio = inv_arr / cons_arr.replace(0, np.nan)

    return ratio


def calc_processing_profit(
    product_price: pd.Series | np.ndarray | list[float],
    raw_material_price: pd.Series | np.ndarray | list[float],
    processing_fee: float = 0.0,
    conversion_ratio: float = 1.0,
) -> pd.Series:
    """计算加工利润。

    加工利润 = 成品价格 - 原料价格 * 转化率 - 加工费

    Args:
        product_price: 成品价格序列。
        raw_material_price: 原料价格序列。
        processing_fee: 单位加工费，默认 0。
        conversion_ratio: 转化率（每吨原料生产多少吨成品），默认 1.0。

    Returns:
        加工利润序列。

    Examples:
        >>> prod = [3000, 3100, 3200]
        >>> raw = [2000, 2100, 2200]
        >>> profit = calc_processing_profit(prod, raw, processing_fee=100, conversion_ratio=1.0)
        >>> profit.iloc[0]
        900.0
    """
    prod_arr = pd.Series(product_price).astype(float)
    raw_arr = pd.Series(raw_material_price).astype(float)

    profit = prod_arr - raw_arr * conversion_ratio - processing_fee

    return profit


def calc_seasonal_index(
    df: pd.DataFrame,
    value_col: str,
    date_col: str = "datetime",
    period: str = "month",
) -> pd.DataFrame:
    """计算季节性指数。

    季节性指数 = 同期均值 / 总均值

    Args:
        df: 输入 DataFrame。
        value_col: 数值列名。
        date_col: 日期列名。
        period: 周期类型，'month' / 'week' / 'quarter'。

    Returns:
        季节性指数 DataFrame，包含 period 和 seasonal_index 列。

    Examples:
        >>> import pandas as pd
        >>> dates = pd.date_range("2020-01-01", periods=24, freq="MS")
        >>> df = pd.DataFrame({
        ...     "datetime": dates,
        ...     "value": [10, 12, 15, 18, 20, 18, 16, 14, 12, 10, 8, 6] * 2,
        ... })
        >>> idx = calc_seasonal_index(df, "value")
        >>> len(idx)
        12
    """
    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col])

    if value_col not in result.columns:
        return pd.DataFrame(columns=[period, "seasonal_index"])

    if period == "month":
        result["_period"] = result[date_col].dt.month
    elif period == "week":
        result["_period"] = result[date_col].dt.isocalendar().week.astype(int)
    elif period == "quarter":
        result["_period"] = result[date_col].dt.quarter
    else:
        result["_period"] = result[date_col].dt.month

    overall_mean = result[value_col].mean()

    seasonal = result.groupby("_period")[value_col].mean().reset_index()
    seasonal.columns = [period, "seasonal_index"]
    seasonal["seasonal_index"] = seasonal["seasonal_index"] / overall_mean

    return seasonal.reset_index(drop=True)
