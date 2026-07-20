"""FuturesDataProvider — 期货数据统一入口。"""
from __future__ import annotations
import time
from typing import Optional
from datacore.models.enums import DataType, MarketType, SourceGrade
from datacore.models.payload import DataPayload
from datacore.futures.providers import (
    TdxLcProvider, EastMoneyFuturesProvider, QMTProvider,
    ExchangeApiProvider, ShengYiSheProvider, WebFallbackProvider, TqSdkProvider,
)


class FuturesDataProvider:
    """期货数据提供者 — 多源降级链: TdxLc(0) → EastMoney(1) → QMT(2) → ExchangeApi(3) → ShengYiShe(4) → WebFallback(5) → TqSdk(6)。"""

    def __init__(self):
        self.sources = [
            TdxLcProvider(),
            EastMoneyFuturesProvider(),
            QMTProvider(),
            ExchangeApiProvider(),
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
            return self._get_warehouse_receipts(symbol)
        return None

    def _get_kline(self, symbol: str, period: str, days: int) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.OHLCV not in src.supported_types:
                continue
            try:
                kd = src.fetch_kline(symbol, period, days)
                if kd and kd.bars:
                    grade = SourceGrade.PRIMARY if src.priority == 0 else SourceGrade.DAILY
                    return DataPayload(
                        symbol=symbol, data_type=DataType.OHLCV,
                        market=MarketType.FUTURES,
                        data=kd, source=src.name, grade=grade,
                        collected_at=time.time(),
                    )
            except Exception:
                continue
        return DataPayload(
            symbol=symbol, data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            grade=SourceGrade.UNAVAILABLE,
            errors=["所有期货源不可用"], collected_at=time.time(),
        )

    def _get_quote(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available() or DataType.QUOTE not in src.supported_types:
                continue
            try:
                qd = src.fetch_quote(symbol)
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
                chain = src.fetch_contract_chain(symbol, num_contracts, period, days)
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
                ts = src.fetch_term_structure(symbol)
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
                spread = src.fetch_spread(symbol, near, far, period, days)
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
                basis = src.fetch_basis(symbol)
                if basis and basis.spot_price > 0:
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

    def _get_position_rank(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_POSITION not in src.supported_types:
                continue
            try:
                pos = src.fetch_position_rank(symbol)
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

    def _get_warehouse_receipts(self, symbol: str) -> Optional[DataPayload]:
        for src in self.sources:
            if not src.check_available():
                continue
            if DataType.FUTURES_WAREHOUSE_RECEIPT not in src.supported_types:
                continue
            try:
                wr = src.fetch_warehouse_receipts(symbol)
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
