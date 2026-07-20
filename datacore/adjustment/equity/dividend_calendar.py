"""除权除息日历 — 简化版。

提供分红送股信息的结构化表示和复权因子计算。

除权除息事件类型:
- 现金分红 (cash_dividend): 每股派发现金红利
- 送股 (stock_dividend): 每股赠送股票
- 转增股 (stock_transfer): 每股资本公积金转增股本
- 配股 (rights_issue): 按比例配售新股（含配股价）

复权因子计算:
    除权价 = (前收盘价 - 现金分红 + 配股价 * 配股比例) / (1 + 送股比例 + 转增比例 + 配股比例)
    复权因子 = 前收盘价 / 除权价
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class DividendEvent:
    """单个除权除息事件。

    Attributes:
        ex_date: 除权除息日 (YYYY-MM-DD)
        cash_dividend: 每股现金分红（税前，元）
        stock_dividend: 每股送股比例（如 0.2 表示 10 送 2）
        stock_transfer: 每股转增比例（如 0.3 表示 10 转 3）
        rights_issue: 每股配股比例（如 0.1 表示 10 配 1）
        rights_price: 配股价（元），无配股时为 0
        pre_close: 除权前一日收盘价，可选
    """

    ex_date: str
    cash_dividend: float = 0.0
    stock_dividend: float = 0.0
    stock_transfer: float = 0.0
    rights_issue: float = 0.0
    rights_price: float = 0.0
    pre_close: Optional[float] = None

    def adjustment_factor(self, pre_close_price: Optional[float] = None) -> float:
        """计算本次除权的复权因子。

        复权因子 = 前收盘价 / 除权价

        Args:
            pre_close_price: 除权前一日收盘价，优先使用此值，其次用 self.pre_close

        Returns:
            复权因子（>= 1 表示向下调整，< 1 表示向上调整，一般 > 1）

        Raises:
            ValueError: 没有可用的前收盘价且无法计算时抛出
        """
        pc = pre_close_price if pre_close_price is not None else self.pre_close
        if pc is None or pc <= 0:
            raise ValueError("计算复权因子需要有效的前收盘价 (pre_close)")

        ex_price = self.ex_rights_price(pc)
        if ex_price <= 0:
            return 1.0
        return pc / ex_price

    def ex_rights_price(self, pre_close_price: float) -> float:
        """计算除权除息后的理论除权价。

        公式:
            除权价 = (前收盘价 - 现金分红 + 配股价 * 配股比例)
                    / (1 + 送股比例 + 转增比例 + 配股比例)

        Args:
            pre_close_price: 除权前一日收盘价

        Returns:
            理论除权价
        """
        numerator = pre_close_price - self.cash_dividend + self.rights_price * self.rights_issue
        denominator = 1.0 + self.stock_dividend + self.stock_transfer + self.rights_issue
        if denominator <= 0:
            return pre_close_price
        return numerator / denominator


@dataclass
class DividendCalendar:
    """除权除息日历 — 管理一系列分红送股事件。

    Attributes:
        events: 除权除息事件列表
    """

    events: list[DividendEvent] = field(default_factory=list)

    @classmethod
    def from_list(cls, dividend_info: list[dict]) -> DividendCalendar:
        """从字典列表构建 DividendCalendar。

        Args:
            dividend_info: 分红信息字典列表，每个 dict 需包含:
                - ex_date: 除权除息日
                - cash_dividend: 每股现金分红
                - stock_dividend: 每股送股比例
                - stock_transfer: 每股转增比例
                - rights_issue: 每股配股比例
                - rights_price: 配股价
                - pre_close: 前收盘价（可选）

        Returns:
            DividendCalendar 实例
        """
        events = []
        for info in dividend_info:
            event = DividendEvent(
                ex_date=str(info.get("ex_date", "")),
                cash_dividend=float(info.get("cash_dividend", 0.0)),
                stock_dividend=float(info.get("stock_dividend", 0.0)),
                stock_transfer=float(info.get("stock_transfer", 0.0)),
                rights_issue=float(info.get("rights_issue", 0.0)),
                rights_price=float(info.get("rights_price", 0.0)),
                pre_close=float(info["pre_close"]) if info.get("pre_close") is not None else None,
            )
            events.append(event)
        return cls(events=events)

    def sorted(self) -> DividendCalendar:
        """返回按 ex_date 升序排列的新日历。"""
        sorted_events = sorted(self.events, key=lambda e: e.ex_date)
        return DividendCalendar(events=sorted_events)

    def build_factor_series(
        self,
        dates: pd.Series | pd.DatetimeIndex | np.ndarray | list,
        pre_close_series: Optional[pd.Series | np.ndarray] = None,
    ) -> pd.Series:
        """构建每日的累计复权因子序列。

        前复权: 最新日期的因子为 1，历史日期乘以前向累积因子
        后复权: 最早日期的因子为 1，向后累积因子

        本函数返回「从最早日期向最新日期」的累积因子（即后复权风格的累积因子），
        调用方可根据需要转换。

        Args:
            dates: 日期序列，需可被 pandas 解析为 datetime
            pre_close_series: 每日前收盘价，长度与 dates 一致，
                              用于在除权日动态计算除权因子。
                              若为 None，则使用事件中存储的 pre_close。

        Returns:
            pd.Series，index 为日期，值为当日（收盘后生效的）累计复权因子，
            初始值为 1.0。
        """
        dt_index = pd.to_datetime(dates)
        n = len(dt_index)
        factors = np.ones(n, dtype=float)

        sorted_cal = self.sorted()

        for event in sorted_cal.events:
            ex_dt = pd.Timestamp(event.ex_date)
            mask = dt_index >= ex_dt
            if not mask.any():
                continue

            event_factor = 1.0
            if pre_close_series is not None:
                before_mask = dt_index < ex_dt
                if before_mask.any():
                    idx_before = int(np.where(before_mask.values)[0][-1])
                    pc = float(pre_close_series[idx_before])
                    if pc > 0:
                        event_factor = event.adjustment_factor(pc)
            elif event.pre_close is not None:
                event_factor = event.adjustment_factor(event.pre_close)

            if event_factor <= 0:
                event_factor = 1.0

            factors[mask] *= event_factor

        return pd.Series(factors, index=dt_index, name="adjust_factor")


__all__ = ["DividendEvent", "DividendCalendar"]
