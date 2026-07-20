"""复权/换月引擎 — 统一入口。

提供 apply_adjustment() 函数，根据 adjustment 参数
自动路由到股票复权或期货连续合约处理。
"""

from __future__ import annotations

from typing import Optional, Union

import pandas as pd

from .registry import (
    parse_adjustment_config,
)


def apply_adjustment(
    kline_data: Union[pd.DataFrame, dict[str, pd.DataFrame]],
    adjustment: str = "none",
    dividend_info: Optional[list[dict]] = None,
    rollover_method: Optional[str] = None,
    adjust_method: Optional[str] = None,
    date_col: str = "date",
    switch_day: int = 15,
    **kwargs,
) -> pd.DataFrame:
    """统一复权/换月入口。

    根据 adjustment 参数自动选择处理路径:
    - 股票复权 (qfq/hfq)
    - 期货连续合约 (continuous*)

    Args:
        kline_data: K 线数据。
            股票复权: pd.DataFrame，需包含 date, open, high, low, close 等列
            期货连续: dict[str, pd.DataFrame]，key 为合约代码，value 为 K 线
        adjustment: 复权/换月类型，选项:
            - "none": 不处理
            - "qfq": 前复权（股票）
            - "hfq": 后复权（股票）
            - "continuous": 期货主力连续，不调整
            - "continuous_qfq": 期货主力连续 + 前复权
            - "continuous_hfq": 期货主力连续 + 后复权
            - "continuous_volume": 成交量加权换月（不调整）
            - "continuous_oi": 持仓量加权换月（不调整）
        dividend_info: 股票分红送股信息（仅股票复权时使用）
        rollover_method: 期货换月方法，可选覆盖 adjustment 中的设定
        adjust_method: 期货换月调整方法，可选覆盖 adjustment 中的设定
        date_col: 日期列名，默认 "date"
        switch_day: 固定日换月的换月日（默认 15）
        **kwargs: 其他参数透传

    Returns:
        处理后的 K 线 DataFrame

    Raises:
        ValueError: adjustment 参数不支持或数据格式不正确
        TypeError: kline_data 类型不正确
    """
    adj = adjustment.lower() if adjustment else "none"

    if adj == "none":
        return _passthrough(kline_data, date_col)

    config = parse_adjustment_config(adjustment)

    if rollover_method is not None:
        config["rollover_method"] = rollover_method
    if adjust_method is not None:
        config["adjust_method"] = adjust_method

    if config["type"] == "equity":
        return _apply_equity_adjustment(
            kline_data, config, dividend_info, date_col
        )
    elif config["type"] == "futures":
        return _apply_futures_adjustment(
            kline_data, config, date_col, switch_day, **kwargs
        )
    else:
        return _passthrough(kline_data, date_col)


def _passthrough(
    kline_data: Union[pd.DataFrame, dict[str, pd.DataFrame]],
    date_col: str,
) -> pd.DataFrame:
    """透传处理 — 直接返回数据副本。

    对于 dict 类型，返回第一个合约的 K 线或空 DataFrame。

    Args:
        kline_data: K 线数据
        date_col: 日期列名

    Returns:
        K 线 DataFrame 副本
    """
    if isinstance(kline_data, pd.DataFrame):
        return kline_data.copy()

    if isinstance(kline_data, dict):
        if not kline_data:
            return pd.DataFrame()
        first_key = next(iter(kline_data))
        return kline_data[first_key].copy()

    raise TypeError(
        f"kline_data 类型不支持: {type(kline_data)}。"
        f"支持 pd.DataFrame 或 dict[str, pd.DataFrame]"
    )


def _apply_equity_adjustment(
    kline_data,
    config: dict,
    dividend_info,
    date_col: str,
) -> pd.DataFrame:
    """应用股票复权。

    Args:
        kline_data: K 线 DataFrame
        config: 配置字典
        dividend_info: 分红信息
        date_col: 日期列名

    Returns:
        复权后的 DataFrame
    """
    if not isinstance(kline_data, pd.DataFrame):
        raise TypeError(
            "股票复权需要 kline_data 为 pd.DataFrame 类型"
        )

    from .equity import forward_adjust, backward_adjust

    method = config.get("equity_method", "qfq")

    if method == "qfq":
        return forward_adjust(kline_data, dividend_info=dividend_info, date_col=date_col)
    elif method == "hfq":
        return backward_adjust(kline_data, dividend_info=dividend_info, date_col=date_col)
    else:
        return kline_data.copy()


def _apply_futures_adjustment(
    kline_data,
    config: dict,
    date_col: str,
    switch_day: int,
    **kwargs,
) -> pd.DataFrame:
    """应用期货连续合约处理。

    Args:
        kline_data: dict[str, pd.DataFrame]
        config: 配置字典
        date_col: 日期列名
        switch_day: 固定换月日
        **kwargs: 其他参数

    Returns:
        连续合约 DataFrame
    """
    if not isinstance(kline_data, dict):
        raise TypeError(
            "期货连续合约需要 kline_data 为 dict[str, pd.DataFrame] 类型"
        )

    from .futures import build_continuous_contract

    rollover_method = config.get("rollover_method", "volume")
    adjust_method = config.get("adjust_method", "none")
    gap_price_col = config.get("gap_price_col", "close")

    return build_continuous_contract(
        kline_data,
        rollover_method=rollover_method,
        adjust_method=adjust_method,
        date_col=date_col,
        switch_day=switch_day,
        gap_price_col=gap_price_col,
    )


__all__ = ["apply_adjustment"]
