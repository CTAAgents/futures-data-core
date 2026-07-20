"""国家统计局宏观数据源 — 宏观数据 P0。"""
from __future__ import annotations
from typing import Optional
import httpx
from datacore.macro.providers.base import MacroDataSource
from datacore.macro.models import MacroData, MacroIndicator

NATIONAL_BUREAU_INDICATORS = {
    "cpi": {"name": "居民消费价格指数", "url": "https://data.stats.gov.cn/easyquery.htm"},
    "ppi": {"name": "工业生产者出厂价格指数", "url": "https://data.stats.gov.cn/easyquery.htm"},
    "gdp": {"name": "国内生产总值", "url": "https://data.stats.gov.cn/easyquery.htm"},
}


class NationalBureauProvider(MacroDataSource):
    """国家统计局宏观数据。"""
    name = "national_bureau"
    priority = 0  # P0: 最高优先级

    def fetch_macro(self, indicator: Optional[str] = None,
                    limit: int = 50) -> Optional[MacroData]:
        """从国家统计局获取宏观数据。
        
        使用 stats.gov.cn 的 EasyQuery API 获取数据。
        参数:
            indicator: "cpi", "ppi", "gdp" 之一
            limit: 返回条数
        """
        try:
            ind_key = (indicator or "cpi").lower()
            if ind_key not in NATIONAL_BUREAU_INDICATORS:
                ind_key = "cpi"
            with httpx.Client(timeout=10) as c:
                resp = c.post(
                    NATIONAL_BUREAU_INDICATORS[ind_key]["url"],
                    data={
                        "m": "QueryData",
                        "dbcode": "fsnd",
                        "rowcode": "zb",
                        "colcode": "sj",
                        "wds": "[]",
                        "dfwds": '[{"wdcode":"zb","valuecode":"A01010101"}]',
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "https://data.stats.gov.cn/",
                    },
                )
                result = resp.json()
                data_list = result.get("returndata", {}).get("datanodes", []) if result else []
        except Exception:
            return None
        if not data_list:
            return None
        indicators = []
        for item in data_list[:limit]:
            try:
                period_val = str(item.get("code", "") or "")
                indicators.append(MacroIndicator(
                    indicator=ind_key,
                    period=period_val,
                    value=float(item.get("data", {}).get("data", 0) or 0),
                    source="national_bureau",
                    unit="",
                ))
            except (TypeError, ValueError):
                continue
        if not indicators:
            return None
        return MacroData(indicator=ind_key, total=len(indicators), data=indicators)

    def check_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as c:
                r = c.head("https://data.stats.gov.cn")
                return r.status_code < 500
        except Exception:
            return False
