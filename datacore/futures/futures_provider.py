"""FuturesDataProvider — 期货数据统一入口。"""
from __future__ import annotations
import time
from typing import Optional
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.futures.providers import (
    TdxLcProvider, EastMoneyFuturesProvider, QMTProvider,
    ExchangeApiProvider, SinaProvider, ShengYiSheProvider, WebFallbackProvider, TqSdkProvider,
)


class FuturesDataProvider:
    """期货数据提供者 — 多源降级链: TdxLc(0) → EastMoney(1) → QMT(2) → ExchangeApi(3) → ShengYiShe(4) → WebFallback(5) → TqSdk(6)。"""

    def __init__(self):
        self.sources = [
            TdxLcProvider(),
            EastMoneyFuturesProvider(),
            QMTProvider(),
            ExchangeApiProvider(),
            SinaProvider(),
            ShengYiSheProvider(),
            WebFallbackProvider(),
            TqSdkProvider(),
        ]

    def get(self, symbol: str, data_type: DataType,
            params: dict | None = None) -> Optional[DataPayload]:
        params = params or {}
        period = params.get("period", "daily")
        days = int(params.get("days", 120))

        if data_type == DataType.OHLCV:
            return self._get_kline(symbol, period, days)
        if data_type == DataType.QUOTE:
            return self._get_quote(symbol)
        if data_type == DataType.FUTURES_CONTRACT_CHAIN:
            return self._get_contract_chain(symbol, params)
        if data_type == DataType.FUTURES_TERM_STRUCTURE:
            return self._get_term_structure(symbol)
        if data_type == DataType.FUTURES_SPREAD:
            return self._get_spread(symbol, params)
        if data_type == DataType.FUTURES_BASIS:
            return self._get_basis(symbol)
        if data_type == DataType.FUTURES_POSITION:
            return self._get_position_rank(symbol)
        if data_type == DataType.FUTURES_WAREHOUSE_RECEIPT:
            return self._get_warehouse_receipts(symbol, params)
        return None

    def _get_kline(self, symbol: str, period: str, days: int) -> Optional[DataPayload]:
        primary_kd = None
        primary_src = None
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.OHLCV not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                kd = src.fetch_kline(local_symbol, period, days)
                if kd and kd.bars:
                    primary_kd = kd
                    primary_src = src
                    break
            except Exception:
                continue

        if primary_kd is None or primary_src is None:
            return DataPayload(
                symbol=symbol, data_type=DataType.OHLCV,
                market=MarketType.FUTURES,
                grade=SourceGrade.UNAVAILABLE,
                errors=["所有期货源不可用"], collected_at=time.time(),
            )

        # 多源拼凑：主数据源缺少 open_interest 时，从其他源补齐
        self._merge_open_interest(symbol, period, days, primary_kd, primary_src)

        grade = SourceGrade.PRIMARY if primary_src.priority == 0 else SourceGrade.DAILY
        return DataPayload(
            symbol=symbol, data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            data=primary_kd, source=primary_src.name, grade=grade,
            collected_at=time.time(),
        )

    def _merge_open_interest(
        self, symbol: str, period: str, days: int,
        primary_kd: Any, used_src: Any,
    ) -> None:
        """当主数据源 K 线缺少持仓量时，从其他源按日期合并 open_interest。"""
        if not primary_kd.bars:
            return
        if not all(bar.open_interest == 0 for bar in primary_kd.bars):
            return

        for src in self.sources:
            if src is used_src:
                continue
            if not src.check_available():
                continue
            if DataType.OHLCV not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                kd = src.fetch_kline(local_symbol, period, days)
                if not kd or not kd.bars:
                    continue
                if not any(bar.open_interest != 0 for bar in kd.bars):
                    continue
                oi_map = {
                    bar.date: bar.open_interest
                    for bar in kd.bars if bar.open_interest != 0
                }
                filled = 0
                for bar in primary_kd.bars:
                    if bar.date in oi_map:
                        bar.open_interest = oi_map[bar.date]
                        filled += 1
                if filled:
                    break
            except Exception:
                continue

    def _get_quote(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available() or DataType.QUOTE not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                qd = src.fetch_quote(local_symbol)
                if qd and qd.last_price:
                    return DataPayload(
                        symbol=symbol, data_type=DataType.QUOTE,
                        market=MarketType.FUTURES,
                        data=qd, source=src.name,
                        grade=SourceGrade.PRIMARY,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None

    def _get_contract_chain(self, symbol: str, params: dict) -> Optional[DataPayload]:
        num_contracts = int(params.get("num_contracts", 5))
        period = params.get("period", "daily")
        days = int(params.get("days", 120))
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_CONTRACT_CHAIN not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                chain = src.fetch_contract_chain(local_symbol, num_contracts, period, days)
                if chain and chain.contracts:
                    grade = SourceGrade.PRIMARY if src.priority == 0 else SourceGrade.DAILY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.FUTURES_CONTRACT_CHAIN,
                        market=MarketType.FUTURES,
                        data=chain, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None

    def _get_term_structure(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_TERM_STRUCTURE not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                ts = src.fetch_term_structure(local_symbol)
                if ts and ts.points:
                    grade = SourceGrade.PRIMARY if src.priority == 0 else SourceGrade.DAILY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.FUTURES_TERM_STRUCTURE,
                        market=MarketType.FUTURES,
                        data=ts, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None

    def _get_spread(self, symbol: str, params: dict) -> Optional[DataPayload]:
        near = params.get("near_contract", "")
        far = params.get("far_contract", "")
        if not near or not far:
            return None
        period = params.get("period", "daily")
        days = int(params.get("days", 120))
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_SPREAD not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                spread = src.fetch_spread(local_symbol, near, far, period, days)
                if spread and spread.spread_series:
                    grade = SourceGrade.PRIMARY if src.priority == 0 else SourceGrade.DAILY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.FUTURES_SPREAD,
                        market=MarketType.FUTURES,
                        data=spread, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None

    def _get_basis(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_BASIS not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                basis = src.fetch_basis(local_symbol)
                if basis and basis.spot_price > 0:
                    # 多源拼凑：现货源缺少期货价格时，从行情源补齐
                    if basis.futures_price <= 0:
                        self._fill_basis_futures_price(symbol, basis)
                    if basis.futures_price > 0:
                        basis.basis = basis.spot_price - basis.futures_price
                        basis.basis_rate = (
                            basis.basis / basis.futures_price
                            if basis.futures_price > 0 else 0.0
                        )
                        basis.basis_pct = basis.basis_rate * 100
                    grade = SourceGrade.DAILY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.FUTURES_BASIS,
                        market=MarketType.FUTURES,
                        data=basis, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None

    def _fill_basis_futures_price(self, symbol: str, basis: Any) -> None:
        """当基差数据缺少期货价格时，从行情源获取最新期货价格。"""
        quote_payload = self._get_quote(symbol)
        if quote_payload and quote_payload.data:
            last_price = getattr(quote_payload.data, "last_price", None)
            if last_price and last_price > 0:
                basis.futures_price = float(last_price)
                basis.futures_source = quote_payload.source or "quote"

    def _get_position_rank(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_POSITION not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                pos = src.fetch_position_rank(local_symbol)
                if pos and pos.long_ranks:
                    grade = SourceGrade.PRIMARY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.FUTURES_POSITION,
                        market=MarketType.FUTURES,
                        data=pos, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None

    def _get_warehouse_receipts(
        self, symbol: str, params: dict | None = None,
    ) -> Optional[DataPayload]:
        params = params or {}
        history_days = int(params.get("history_days", 252))
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_WAREHOUSE_RECEIPT not in src.supported_types:
                continue
            try:
                local_symbol = src.normalize_symbol(symbol)
                wr = src.fetch_warehouse_receipts(local_symbol, history_days=history_days)
                if wr and wr.total_receipts > 0:
                    grade = SourceGrade.PRIMARY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.FUTURES_WAREHOUSE_RECEIPT,
                        market=MarketType.FUTURES,
                        data=wr, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return None
