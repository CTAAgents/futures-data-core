"""复权/换月参数注册表。

将 adjustment 字符串参数映射到具体的处理管线。

支持的 adjustment 取值:
- "none": 不处理，透传
- "qfq": 股票前复权
- "hfq": 股票后复权
- "continuous": 期货主力连续（不调整价格）
- "continuous_qfq": 期货主力连续 + 前复权
- "continuous_hfq": 期货主力连续 + 后复权
- "continuous_volume": 期货成交量加权换月（不调整）
- "continuous_oi": 期货持仓量加权换月（不调整）
"""

from __future__ import annotations




ADJUSTMENT_OPTIONS = [
    "none",
    "qfq",
    "hfq",
    "continuous",
    "continuous_qfq",
    "continuous_hfq",
    "continuous_volume",
    "continuous_oi",
]


def parse_adjustment_config(
    adjustment: str,
    **kwargs,
) -> dict:
    """解析 adjustment 字符串，返回标准化的配置字典。

    Args:
        adjustment: 复权/换月类型字符串
        **kwargs: 额外参数

    Returns:
        配置字典，包含:
        - type: 类型 ("none", "equity", "futures")
        - equity_method: 股票复权方法 ("qfq", "hfq")
        - rollover_method: 期货换月方法
        - adjust_method: 期货换月调整方法
        - 以及从 kwargs 透传的其他参数

    Raises:
        ValueError: adjustment 不支持
    """
    adj = adjustment.lower() if adjustment else "none"

    config = {
        "type": "none",
        "equity_method": None,
        "rollover_method": "volume",
        "adjust_method": "none",
    }

    for k, v in kwargs.items():
        if k not in config:
            config[k] = v

    if adj == "none":
        config["type"] = "none"
    elif adj == "qfq":
        config["type"] = "equity"
        config["equity_method"] = "qfq"
    elif adj == "hfq":
        config["type"] = "equity"
        config["equity_method"] = "hfq"
    elif adj == "continuous":
        config["type"] = "futures"
        config["rollover_method"] = "volume"
        config["adjust_method"] = "none"
    elif adj == "continuous_qfq":
        config["type"] = "futures"
        config["rollover_method"] = "volume"
        config["adjust_method"] = "qfq"
    elif adj == "continuous_hfq":
        config["type"] = "futures"
        config["rollover_method"] = "volume"
        config["adjust_method"] = "hfq"
    elif adj == "continuous_volume":
        config["type"] = "futures"
        config["rollover_method"] = "volume"
        config["adjust_method"] = "none"
    elif adj == "continuous_oi":
        config["type"] = "futures"
        config["rollover_method"] = "oi"
        config["adjust_method"] = "none"
    else:
        raise ValueError(
            f"不支持的 adjustment 参数: '{adjustment}'。\n"
            f"支持的选项: {', '.join(ADJUSTMENT_OPTIONS)}"
        )

    if "rollover_method" in kwargs:
        config["rollover_method"] = kwargs["rollover_method"]
    if "adjust_method" in kwargs:
        config["adjust_method"] = kwargs["adjust_method"]

    return config


def is_futures_adjustment(adjustment: str) -> bool:
    """判断是否为期货类复权。

    Args:
        adjustment: 复权类型字符串

    Returns:
        True 表示期货类，False 表示股票类或 none
    """
    adj = adjustment.lower() if adjustment else "none"
    return adj.startswith("continuous")


def is_equity_adjustment(adjustment: str) -> bool:
    """判断是否为股票类复权。

    Args:
        adjustment: 复权类型字符串

    Returns:
        True 表示股票类
    """
    adj = adjustment.lower() if adjustment else "none"
    return adj in ("qfq", "hfq")


__all__ = [
    "ADJUSTMENT_OPTIONS",
    "parse_adjustment_config",
    "is_futures_adjustment",
    "is_equity_adjustment",
]
