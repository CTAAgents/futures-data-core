"""TQ-Local 期货数据源 — 通达信本地 HTTP 服务。"""

from __future__ import annotations

import time
from typing import Optional

import httpx

import re
from datacore.config import get_config
from datacore.futures.providers.base import FuturesDataSource
from datacore.models.ohlcv import KBar, KlineData, QuoteData
from datacore.models.enums import DataType
from datacore.models.futures import (
    ContractChain, TermStructure, TermStructurePoint,
    SpreadData,
)

FUTURES_MARKET = "92"
PERIOD_MAP = {"daily": "1d", "60m": "60m", "120m": "120m", "240m": "240m", "weekly": "1w"}


class TdxLcProvider(FuturesDataSource):
    name = "tdx_lc"
    priority = 0
    supported_types = {
        DataType.OHLCV, DataType.QUOTE, DataType.TECHNICAL,
        DataType.FUTURES_CONTRACT_CHAIN, DataType.FUTURES_TERM_STRUCTURE,
        DataType.FUTURES_SPREAD,
    }

    def __init__(self, url: Optional[str] = None, timeout: Optional[int] = None):
        config = get_config()
        self.url = url or config.tdx_url
        self.timeout = timeout or config.tdx_timeout
        self._contract_cache: Optional[dict] = None

    def _post(self, method: str, params: dict) -> dict:
        payload = {"id": 1, "method": method, "params": params}
        try:
            with httpx.Client(timeout=self.timeout) as c:
                resp = c.post(self.url, json=payload)
            return resp.json().get("result", {})
        except Exception:
            return {}

    def _load_contracts(self):
        if self._contract_cache is not None:
            return
        self._contract_cache = {}
        resp = self._post("get_stock_list", {"market": FUTURES_MARKET, "list_type": 1})
        result = resp.get("Value", resp) if isinstance(resp, dict) else resp
        if not isinstance(result, list):
            return
        for item in result:
            code = item.get("Code", "")
            alpha = "".join(c for c in code.split(".")[0] if c.isalpha()).upper()
            if alpha and alpha not in self._contract_cache:
                self._contract_cache[alpha] = code

    def _resolve_contract(self, symbol: str) -> Optional[str]:
        """解析合约代码。

        若 ``symbol`` 已是具体合约代码（如 ``SM2609``），直接返回（尝试从缓存中补全后缀）；
        若 ``symbol`` 是品种代码（如 ``SM``），从缓存中查找默认合约。
        """
        from datacore.registry.contract_mapper import FuturesContractMapper

        self._load_contracts()
        cache = self._contract_cache or {}

        if FuturesContractMapper.is_contract_code(symbol):
            sym_upper = symbol.upper()
            # 尝试在缓存中找到完整的合约代码（带市场后缀如 .XZSE）
            for alpha, code in cache.items():
                if code.split(".")[0].upper() == sym_upper:
                    return code
            # 未找到后缀，直接返回大写
            return sym_upper

        return cache.get(symbol.upper())

    def normalize_symbol(self, symbol: str) -> str:
        """TDX 使用 2 位年份格式: SM2609 → 不做转换。"""
        from datacore.registry.contract_mapper import FuturesContractMapper

        if FuturesContractMapper.is_contract_code(symbol):
            fmt = FuturesContractMapper.detect_format(symbol)
            if fmt == 1:  # 1 位年份 → 转 2 位年份
                return FuturesContractMapper.to_2digit_format(symbol)
        return symbol

    def check_available(self) -> bool:
        resp = self._post("get_stock_list", {"market": FUTURES_MARKET, "list_type": 1})
        result = resp.get("Value", resp) if isinstance(resp, dict) else resp
        return isinstance(result, list) and len(result) > 0

    def fetch_kline(self, symbol: str, period: str = "daily", days: int = 120) -> Optional[KlineData]:
        contract = self._resolve_contract(symbol)
        if not contract:
            return None
        tdx_period = PERIOD_MAP.get(period, "1d")
        resp = self._post("get_market_data", {
            "stock_list": [contract], "count": days,
            "dividend_type": "none", "period": tdx_period,
        })
        value = resp.get("Value", resp) if isinstance(resp, dict) else resp
        series = None
        if isinstance(value, dict):
            series = value.get(contract) or value.get("Value", {}).get(contract) if isinstance(value, dict) else None
        if not isinstance(series, dict):
            return None
        dates = series.get("Date", []) or []
        bars = []
        for i in range(min(len(dates), len(series.get("Open", [])))):
            try:
                bars.append(KBar(
                    date=str(dates[i]),
                    open=float(series["Open"][i]),
                    high=float(series["High"][i]),
                    low=float(series["Low"][i]),
                    close=float(series["Close"][i]),
                    volume=float(series.get("Volume", [0])[i] if i < len(series.get("Volume", [])) else 0),
                    amount=float(series.get("Amount", [0])[i] if i < len(series.get("Amount", [])) else 0),
                    open_interest=float(series.get("Hold", [0])[i] if i < len(series.get("Hold", [])) else 0),
                ))
            except (TypeError, ValueError):
                continue
        return KlineData(symbol=symbol, period=period, bars=bars, source=self.name, contract=contract)

    def fetch_quote(self, symbol: str) -> Optional[QuoteData]:
        contract = self._resolve_contract(symbol)
        if not contract:
            return None
        resp = self._post("get_market_snapshot", {"stock_code": contract})
        snap = resp.get("Value", resp) if isinstance(resp, dict) else resp
        if not isinstance(snap, dict):
            return None

        def _f(k: str):
            v = snap.get(k)
            return float(v) if v not in (None, "", "--") else None

        return QuoteData(
            symbol=symbol, source=self.name,
            last_price=_f("Now"), open=_f("Open"),
            high=_f("Max"), low=_f("Min"),
            pre_close=_f("LastClose"), volume=_f("Volume"),
            update_time=str(snap.get("UpdateTime", "")),
        )

    def _list_symbol_contracts(self, symbol: str) -> list[str]:
        """获取某个品种的所有合约代码（按持仓量排序，主力在前）。"""
        self._load_contracts()
        cache = self._contract_cache or {}
        symbol_upper = symbol.upper()
        codes = [code for alpha, code in cache.items() if alpha == symbol_upper]
        if not codes:
            pattern = re.compile(rf"^{symbol_upper}\d{{3,4}}$")
            all_codes = [
                code for code in cache.values()
                if pattern.match(code.split(".")[0])
            ]
            codes = sorted(set(all_codes))

        snap_list = self._fetch_contract_snapshots(codes)
        codes.sort(key=lambda c: -snap_list.get(c, {}).get("Hold", 0) if isinstance(snap_list, dict) else 0)
        return codes

    def _fetch_contract_snapshots(self, codes: list[str]) -> dict:
        """批量获取合约快照，返回 {code: snapshot}。"""
        if not codes:
            return {}
        resp = self._post("get_market_snapshot", {"stock_code": codes[0]})
        result = resp.get("Value", resp) if isinstance(resp, dict) else resp
        if isinstance(result, dict) and "Value" in result:
            result = result["Value"]
        if isinstance(result, list):
            return {item.get("Code", ""): item for item in result}
        if isinstance(result, dict):
            return result
        return {}

    def fetch_contract_chain(self, symbol: str, num_contracts: int = 5,
                             period: str = "daily",
                             days: int = 120) -> Optional[ContractChain]:
        """获取合约链数据 — 按持仓量取前 N 个合约的 K线。"""
        contracts = self._list_symbol_contracts(symbol)
        if not contracts:
            return None
        selected = contracts[:num_contracts]
        chain = ContractChain(symbol=symbol, contracts=selected)
        for contract in selected:
            kd = self.fetch_kline(contract, period, days)
            if kd:
                chain.klines[contract] = kd
        return chain if chain.klines else None

    def fetch_term_structure(self, symbol: str) -> Optional[TermStructure]:
        """获取期限结构快照 — 所有合约的最新价格和收益率。"""
        contracts = self._list_symbol_contracts(symbol)
        if not contracts:
            return None
        points = []
        prev_price = 0.0
        for i, contract in enumerate(contracts):
            q = self.fetch_quote(contract)
            if not q or not q.last_price:
                continue
            price = q.last_price
            month_code = contract.split(".")[0]
            yld_front = 0.0
            yld_annual = 0.0
            if prev_price > 0:
                yld_front = (price - prev_price) / prev_price
                yld_annual = yld_front * 12
            points.append(TermStructurePoint(
                contract=contract,
                month=month_code,
                price=price,
                yield_from_front=yld_front,
                yield_annual=yld_annual,
            ))
            prev_price = price
        if not points:
            return None
        return TermStructure(symbol=symbol, points=points, snapshot_at=time.time())

    def fetch_spread(self, symbol: str, near_contract: str, far_contract: str,
                     period: str = "daily", days: int = 120) -> Optional[SpreadData]:
        """获取跨期价差 — 计算两个合约的价差时间序列。"""
        near_k = self.fetch_kline(near_contract, period, days)
        far_k = self.fetch_kline(far_contract, period, days)
        if not near_k or not far_k:
            return None
        near_map = {b.date: b for b in near_k.bars}
        spread_series = []
        for far_bar in far_k.bars:
            near_bar = near_map.get(far_bar.date)
            if near_bar:
                spread = far_bar.close - near_bar.close
                spread_series.append({
                    "date": far_bar.date,
                    "near_close": near_bar.close,
                    "far_close": far_bar.close,
                    "spread": spread,
                })
        if not spread_series:
            return None
        return SpreadData(
            symbol=symbol,
            near_contract=near_contract,
            far_contract=far_contract,
            spread_series=spread_series,
        )
