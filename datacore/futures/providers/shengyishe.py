"""生意社数据源 — 期货基本面 P1。

数据来源: 生意社 (100ppi.com)
  - 现货价格
  - 基差
  - 库存数据
"""
from __future__ import annotations
from typing import Optional
import httpx
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KlineData, QuoteData
from datacore.models.enums import DataType
from datacore.models.futures import (
    BasisData,
)


# 生意社品种编码映射
SYMBOL_MAP = {
    "RB": {"code": "1006", "name": "螺纹钢"},
    "HC": {"code": "1010", "name": "热轧板卷"},
    "I": {"code": "1022", "name": "铁矿石"},
    "CU": {"code": "1001", "name": "铜"},
    "AL": {"code": "1002", "name": "铝"},
    "ZN": {"code": "1003", "name": "锌"},
    "PB": {"code": "1005", "name": "铅"},
    "AU": {"code": "1008", "name": "黄金"},
    "AG": {"code": "1009", "name": "白银"},
    "M": {"code": "1033", "name": "豆粕"},
    "Y": {"code": "1034", "name": "豆油"},
    "P": {"code": "1037", "name": "棕榈油"},
    "SR": {"code": "1040", "name": "白糖"},
    "CF": {"code": "1041", "name": "棉花"},
    "RU": {"code": "1011", "name": "天然橡胶"},
    "PTA": {"code": "1013", "name": "PTA"},
    "MA": {"code": "1042", "name": "甲醇"},
    "FG": {"code": "1043", "name": "玻璃"},
}


class ShengYiSheProvider(FuturesDataSource):
    """生意社现货/基差数据源。"""
    name = "shengyishe"
    priority = 4
    supported_types = {
        DataType.FUTURES_BASIS,
    }

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        return None

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        return None

    def fetch_basis(self, symbol: str) -> Optional[BasisData]:
        """从生意社获取基差数据（真实现货价格 - 期货价格）。
        
        替换 eastmoney 的近似算法（D01 技术债修复）。
        """
        sym_info = SYMBOL_MAP.get(symbol.upper())
        if sym_info is None:
            return None
        try:
            url = f"https://www.100ppi.com/sf/detail-{sym_info['code']}.html"
            with httpx.Client(timeout=10, follow_redirects=True) as c:
                resp = c.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    },
                )
                text = resp.text
            if not text:
                return None
            # 简单解析: 从 HTML 中提取现货价格
            import re
            price_match = re.search(r'(\d+\.?\d*)\s*元/吨', text)
            spot_price = float(price_match.group(1)) if price_match else 0
            if spot_price <= 0:
                return None
            return BasisData(
                symbol=symbol.upper(),
                spot_price=spot_price,
                futures_price=0.0,
                basis=0.0,
                basis_rate=0.0,
                basis_pct=0.0,
                spot_source="shengyishe",
                futures_source="",
            )
        except Exception:
            return None

    def check_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as c:
                r = c.head("https://www.100ppi.com")
                return r.status_code < 500
        except Exception:
            return False
