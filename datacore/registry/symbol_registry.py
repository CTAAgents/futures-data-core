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
    """统一符号注册表。

    期货品种通过显式注册识别；A 股/ETF/可转债通过代码前缀规则自动识别。
    """

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

    @staticmethod
    def _guess_equity_market(symbol: str) -> Optional[MarketType]:
        """根据代码前缀规则识别 A 股/ETF/可转债市场。

        规则:
            - 6 位纯数字: A 股股票（沪市 60/68、深市 00/30、北交所 8/4 开头）
            - 510/511/512/513/515/516/588: 沪市 ETF
            - 159: 深市 ETF
            - 110/113/118/127/128/132/133: 可转债
        """
        s = symbol.strip()
        if not s.isdigit() or len(s) != 6:
            return None

        # ETF 前缀
        if s[:3] in ("510", "511", "512", "513", "515", "516", "588", "159"):
            return MarketType.ETF
        # 可转债前缀
        if s[:3] in ("110", "113", "118", "127", "128", "132", "133"):
            return MarketType.CB
        # A 股股票前缀
        if s[0] in ("6", "0", "3", "8", "4"):
            return MarketType.STOCK
        return None

    def register(self, symbol: str, name: str, market: MarketType,
                 sector: str = "", is_active: bool = True) -> SymbolEntry:
        entry = SymbolEntry(symbol, name, market, sector, is_active)
        self._entries[symbol.upper()] = entry
        return entry

    def resolve(self, symbol: str) -> Optional[SymbolEntry]:
        """解析符号，返回条目或 None。

        先查显式注册表（期货品种）；检查是否为期货合约代码（如 ``SM2609``）；
        未命中则按 A 股代码规则自动识别。
        """
        s = symbol.upper().strip()
        entry = self._entries.get(s)
        if entry is not None:
            return entry

        # 检查是否为期货合约代码（如 "SM2609"、"SM609"），提取品种前缀后查注册表
        variety = self._extract_futures_variety(s)
        if variety and variety in self._entries:
            return self._entries[variety]

        # A 股/ETF/CB 自动识别
        market = self._guess_equity_market(s)
        if market is not None:
            return SymbolEntry(symbol=s, name=s, market=market)
        return None

    @staticmethod
    def _extract_futures_variety(symbol: str) -> Optional[str]:
        """从合约代码（如 ``SM2609``、``I2609``）中提取品种前缀。

        仅当符号匹配 ``1-2 字母 + 3-4 数字`` 模式时返回字母部分。
        """
        import re
        match = re.match(r"^([A-Za-z]{1,2})\d{3,4}$", symbol.strip())
        return match.group(1).upper() if match else None

    def resolve_market(self, symbol: str) -> Optional[MarketType]:
        """解析符号所属市场。"""
        entry = self.resolve(symbol)
        return entry.market if entry else None

    def list_by_market(self, market: MarketType) -> list[SymbolEntry]:
        return [e for e in self._entries.values() if e.market == market]

    def list_all(self) -> list[SymbolEntry]:
        return list(self._entries.values())
