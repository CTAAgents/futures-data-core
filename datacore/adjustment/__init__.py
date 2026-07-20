"""复权/换月引擎模块 — 统一入口。

提供股票复权（前复权/后复权）和期货连续合约（主力识别/换月/拼接/价差调整）
的统一处理框架。

主要接口:
- apply_adjustment(kline_data, adjustment="qfq", ...) -> pd.DataFrame

支持的 adjustment 类型:
- "none": 不处理
- "qfq": 股票前复权
- "hfq": 股票后复权
- "continuous": 期货主力连续（不调整价格）
- "continuous_qfq": 期货主力连续 + 前复权
- "continuous_hfq": 期货主力连续 + 后复权
- "continuous_volume": 成交量加权换月
- "continuous_oi": 持仓量加权换月

使用方式:
    from datacore.adjustment import apply_adjustment

    # 股票前复权
    result = apply_adjustment(kline_df, adjustment="qfq", dividend_info=[...])

    # 期货主力连续 + 前复权
    result = apply_adjustment(kline_dict, adjustment="continuous_qfq")
"""

from __future__ import annotations

from .engine import apply_adjustment
from .registry import ADJUSTMENT_OPTIONS


__all__ = [
    "apply_adjustment",
    "ADJUSTMENT_OPTIONS",
]
