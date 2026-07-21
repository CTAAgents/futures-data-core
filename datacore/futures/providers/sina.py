"""新浪期货数据源 — SinaProvider.

支持:
  - 日/周/月 K 线 (InnerFuturesNewService.getDailyKLine)
  - 分钟 K 线 1/5/15/30/60 (InnerFuturesNewService.getFewMinLine)
  - 实时行情 (hq.sinajs.cn)

数据来源: https://stock2.finance.sina.com.cn/futures/api/jsonp.php
"""
import json
import logging
from typing import Optional
from dataclasses import dataclass
import httpx

from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.models.enums import DataType


logger = logging.getLogger(__name__)

# 新浪期货分钟线周期映射
_MINUTE_TYPE_MAP = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60"}


@dataclass
class FuturesQuoteExtended:
    """期货实时行情扩展字段 — 新浪44字段解析。"""
    symbol: str
    source: str = ""
    name: str = ""
    exchange: str = ""
    date: str = ""
    last_price: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    settlement: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_volume: int = 0
    ask_volume: int = 0
    volume: float = 0.0
    amount: float = 0.0
    open_interest: int = 0
    change: float = 0.0
    change_pct: float = 0.0


class SinaProvider(FuturesDataSource):
    """新浪财经期货数据源 — 免费、无需认证。"""
    name = "sina"
    priority = 3
    supported_types = {DataType.OHLCV, DataType.QUOTE}

    def __init__(self):
        self._client = httpx.Client(timeout=15, follow_redirects=True)

    def check_available(self) -> bool:
        try:
            r = self._client.get(
                "https://hq.sinajs.cn/list=nf_SM2609",
                headers={"Referer": "https://finance.sina.com.cn"},
                timeout=5,
            )
            return r.status_code == 200 and '"' in r.text
        except Exception:
            return False

    def fetch_kline(self, symbol: str, period: str = "daily",
                    days: int = 120) -> Optional[KlineData]:
        """获取新浪期货 K 线数据。

        支持日/周/月线和 1/5/15/30/60 分钟线。
        数据量: 日线约200条历史，分钟线约1000条。
        """
        try:
            sym = symbol.upper()

            if period in ("daily", "weekly", "monthly"):
                rows = self._fetch_daily_kline(sym)
            else:
                rows = self._fetch_minute_kline(sym, period)

            if not rows:
                return None

            bars = []
            for row in rows:
                try:
                    bars.append(KBar(
                        date=row.get("d", ""),
                        open=float(row.get("o", 0)),
                        high=float(row.get("h", 0)),
                        low=float(row.get("l", 0)),
                        close=float(row.get("c", 0)),
                        volume=float(row.get("v", 0)),
                        amount=0.0,
                        open_interest=float(row.get("p", 0)),
                        settlement=float(row.get("s", 0)),
                    ))
                except (ValueError, TypeError):
                    continue

            if not bars:
                return None

            # 按日期排序并截取
            bars.sort(key=lambda b: b.date)
            if len(bars) > days:
                bars = bars[-days:]

            return KlineData(
                symbol=symbol, period=period, bars=bars, source=self.name,
            )

        except Exception as e:
            logger.debug("Sina fetch_kline error: %s %s", symbol, e)
            return None

    def _fetch_daily_kline(self, symbol: str) -> Optional[list[dict]]:
        """获取日线 K 线（JSONP 格式）。"""
        url = (
            "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/"
            "var%20_V21052021_4_12=/InnerFuturesNewService.getDailyKLine"
        )
        resp = self._client.get(url, params={"symbol": symbol, "type": "2026_7_21"})
        if resp.status_code >= 400:
            return None
        return self._parse_jsonp(resp.text)

    def _fetch_minute_kline(self, symbol: str, period: str) -> Optional[list[dict]]:
        """获取分钟 K 线（JSONP 格式）。"""
        minute_type = _MINUTE_TYPE_MAP.get(period)
        if minute_type is None:
            return None
        url = (
            "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/"
            "=/InnerFuturesNewService.getFewMinLine"
        )
        resp = self._client.get(url, params={"symbol": symbol, "type": minute_type})
        if resp.status_code >= 400:
            return None
        return self._parse_jsonp(resp.text)

    def _parse_jsonp(self, text: str) -> Optional[list[dict]]:
        """解析新浪 JSONP 响应，提取 JSON 数组。"""
        text = text.strip()
        if not text:
            return None
        # 跳过可能的 <script> 前缀
        if "=(" in text and ");" in text:
            json_str = text.split("=(", 1)[1].rsplit(");", 1)[0]
            return json.loads(json_str)
        if text.startswith("["):
            return json.loads(text)
        return None

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        """获取实时行情（基础版）。"""
        ext = self.fetch_quote_extended(symbol)
        if ext is None:
            return None
        return QuoteData(
            symbol=ext.symbol, source=ext.source, last_price=ext.last_price,
            open=ext.open, high=ext.high, low=ext.low, pre_close=ext.pre_close,
            volume=ext.volume, amount=ext.amount,
        )

    def fetch_quote_extended(self, symbol: str) -> Optional[FuturesQuoteExtended]:
        """获取实时行情（扩展版，44字段完整解析）。"""
        try:
            sym = symbol.upper()
            resp = self._client.get(
                f"https://hq.sinajs.cn/list=nf_{sym}",
                headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0",
                },
            )
            if resp.status_code >= 400:
                return None
            text = resp.text.strip()
            if not text or '""' in text or '"' not in text:
                return None
            parts = text.split('"')
            if len(parts) < 2:
                return None
            fields = parts[1].split(",")
            if len(fields) < 20:
                return None

            def _f(i, default=0.0):
                try:
                    v = fields[i].strip()
                    return float(v) if v else default
                except (ValueError, IndexError):
                    return default

            def _s(i, default=""):
                try:
                    return fields[i].strip()
                except IndexError:
                    return default

            last_price = _f(10)
            pre_close = _f(4)
            return FuturesQuoteExtended(
                symbol=sym, source=self.name, name=_s(0), exchange=_s(15),
                date=_s(17), last_price=last_price,
                open=_f(1) if _f(1) > 100 else last_price,
                high=_f(2), low=_f(3), pre_close=pre_close,
                settlement=_f(27), bid_price=_f(6), ask_price=_f(7),
                bid_volume=int(_f(12)) if _f(12) else 0,
                ask_volume=int(_f(11)) if _f(11) else 0,
                volume=_f(13),
                amount=_f(14) * 10000 if _f(14) < 100000 else _f(14),
                open_interest=int(_f(14)) if len(fields) > 14 else 0,
                change=last_price - pre_close if pre_close > 0 else 0.0,
                change_pct=((last_price - pre_close) / pre_close * 100)
                if pre_close > 0 else 0.0,
            )
        except Exception as e:
            logger.debug("Sina fetch_quote_extended error: %s %s", symbol, e)
            return None
