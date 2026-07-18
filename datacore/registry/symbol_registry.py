"""统一符号注册表 — 符号解析 + 市场路由。"""

from __future__ import annotations
from typing import Optional
from datacore.models.enums import MarketType


class SymbolEntry:
    """符号条目。"""
    def __init__(self, symbol: str, name: str, market: MarketType,
                 sector: str = "", is_active: bool = True):
        self.symbol = symbol
        self.name = name
        self.market = market
        self.sector = sector
        self.is_active = is_active


class SymbolRegistry:
    """统一符号注册表。"""

    def __init__(self):
        self._entries: dict[str, SymbolEntry] = {}
        self._init_builtin()

    def _init_builtin(self):
        """初始化内置期货品种。"""
        futures = [
            # 黑色系
            ("RB", "螺纹钢", "黑色系"), ("HC", "热卷", "黑色系"),
            ("I", "铁矿石", "黑色系"), ("J", "焦炭", "黑色系"),
            ("JM", "焦煤", "黑色系"), ("SF", "硅铁", "黑色系"), ("SM", "锰硅", "黑色系"),
            # 能源
            ("SC", "原油", "能源链"), ("LU", "低硫燃油", "能源链"),
            ("FU", "燃油", "能源链"), ("BU", "沥青", "能源链"),
            ("PG", "液化气", "能源链"), ("PX", "对二甲苯", "能源链"),
            # 聚酯链
            ("TA", "PTA", "聚酯链"), ("PF", "短纤", "聚酯链"),
            ("EG", "乙二醇", "聚酯链"), ("EB", "苯乙烯", "聚酯链"),
            # 化工
            ("V", "PVC", "塑化链"), ("PP", "聚丙烯", "塑化链"),
            ("L", "聚乙烯", "塑化链"), ("MA", "甲醇", "塑化链"),
            ("SA", "纯碱", "化工"), ("UR", "尿素", "化工"), ("SH", "烧碱", "化工"),
            # 有色
            ("CU", "沪铜", "有色金属"), ("AL", "沪铝", "有色金属"),
            ("ZN", "沪锌", "有色金属"), ("PB", "沪铅", "有色金属"),
            ("NI", "沪镍", "有色金属"), ("SN", "沪锡", "有色金属"),
            ("AO", "氧化铝", "有色金属"), ("SS", "不锈钢", "有色金属"),
            # 贵金属
            ("AU", "黄金", "贵金属"), ("AG", "白银", "贵金属"),
            # 油脂油料
            ("A", "豆一", "油脂油料"), ("B", "豆二", "油脂油料"),
            ("M", "豆粕", "油脂油料"), ("Y", "豆油", "油脂油料"),
            ("P", "棕榈油", "油脂油料"), ("OI", "菜油", "油脂油料"),
            ("RM", "菜粕", "油脂油料"), ("PK", "花生", "油脂油料"),
            # 农产品
            ("C", "玉米", "农产品"), ("CS", "淀粉", "农产品"),
            ("SR", "白糖", "农产品"), ("CF", "棉花", "农产品"),
            ("JD", "鸡蛋", "农产品"), ("LH", "生猪", "农产品"),
            # 建材
            ("FG", "玻璃", "建材化工"), ("RU", "橡胶", "建材化工"),
            ("NR", "20号胶", "建材化工"), ("BR", "丁二烯胶", "建材化工"),
            ("SP", "纸浆", "建材化工"),
            # 新能源
            ("LC", "碳酸锂", "新能源"), ("SI", "工业硅", "新能源"),
            # 航运
            ("EC", "欧线集运", "航运"),
        ]
        for sym, name, sector in futures:
            self.register(sym, name, MarketType.FUTURES, sector)

    def register(self, symbol: str, name: str, market: MarketType,
                 sector: str = "", is_active: bool = True) -> SymbolEntry:
        entry = SymbolEntry(symbol, name, market, sector, is_active)
        self._entries[symbol.upper()] = entry
        return entry

    def resolve(self, symbol: str) -> Optional[SymbolEntry]:
        """解析符号，返回条目或 None。"""
        s = symbol.upper().strip()
        return self._entries.get(s)

    def resolve_market(self, symbol: str) -> Optional[MarketType]:
        """解析符号所属市场。"""
        entry = self.resolve(symbol)
        return entry.market if entry else None

    def list_by_market(self, market: MarketType) -> list[SymbolEntry]:
        return [e for e in self._entries.values() if e.market == market]

    def list_all(self) -> list[SymbolEntry]:
        return list(self._entries.values())
