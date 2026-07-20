"""期货复权与连续合约子模块。

提供期货主力合约识别、换月、连续合约拼接和换月价差调整功能。

主要接口:
- build_continuous_contract(): 构建连续合约（统一入口）
- identify_dominant_by_volume(): 成交量主力识别
- identify_dominant_by_oi(): 持仓量主力识别
- identify_dominant_fixed_day(): 固定日换月
- detect_rollover_dates(): 检测换月日
- adjust_rollover_qfq(): 前复权调整
- adjust_rollover_hfq(): 后复权调整
- adjust_rollover_none(): 不调整

使用方式:
    from datacore.adjustment.futures import build_continuous_contract
    result = build_continuous_contract(kline_dict, 
                                       rollover_method="volume",
                                       adjust_method="qfq")
"""

from __future__ import annotations

from .dominant_contract import (
    identify_dominant_by_volume,
    identify_dominant_by_oi,
    identify_dominant_fixed_day,
)
from .rollover import (
    detect_rollover_dates,
    get_dominant_series,
    get_rollover_pairs,
)
from .continuous import build_continuous_contract
from .adjust_methods import (
    adjust_rollover_qfq,
    adjust_rollover_hfq,
    adjust_rollover_none,
)


__all__ = [
    "build_continuous_contract",
    "identify_dominant_by_volume",
    "identify_dominant_by_oi",
    "identify_dominant_fixed_day",
    "detect_rollover_dates",
    "get_dominant_series",
    "get_rollover_pairs",
    "adjust_rollover_qfq",
    "adjust_rollover_hfq",
    "adjust_rollover_none",
]
