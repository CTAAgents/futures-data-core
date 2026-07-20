"""FuturesContractMapper — 期货合约符号映射器。

不同数据源对同一期货合约使用不同代码格式：
  - TDX/东方财富: SM2609 (2位年份, prefix + YY + MM)
  - TqSDK/天勤:     SM609   (1位年份, prefix + Y + MM)

映射器负责自动检测格式并在格式间双向转换，使下游消费端无感知。
"""

from __future__ import annotations

import re
from typing import Optional


class FuturesContractMapper:
    """期货合约符号映射器。

    支持 2 种合约代码格式之间的自动检测与转换：
      - 2位年份格式 (TDX风格): ``SM2609`` (SM + 26 + 09, 6 字符)
      - 1位年份格式 (TqSDK风格): ``SM609`` (SM + 6 + 09, 5 字符)

    用法::

        FuturesContractMapper.is_contract_code("SM2609")   # True
        FuturesContractMapper.is_contract_code("SM")        # False
        FuturesContractMapper.to_2digit_format("SM609")    # "SM2609"
        FuturesContractMapper.to_1digit_format("SM2609")   # "SM609"
        FuturesContractMapper.extract_prefix("SM2609")     # "SM"
    """

    # 合约代码正则: 1-2位字母前缀 + 3-4位数字（年份+月份）
    _CONTRACT_RE = re.compile(r"^([A-Za-z]{1,2})(\d{3,4})$")

    @staticmethod
    def is_contract_code(symbol: str) -> bool:
        """判断是否为具体合约代码（含数字后缀）。

        >>> FuturesContractMapper.is_contract_code("SM2609")
        True
        >>> FuturesContractMapper.is_contract_code("SM609")
        True
        >>> FuturesContractMapper.is_contract_code("SM")
        False
        """
        return bool(FuturesContractMapper._CONTRACT_RE.match(symbol.strip().upper()))

    @staticmethod
    def extract_prefix(symbol: str) -> str:
        """提取品种前缀字母部分。

        >>> FuturesContractMapper.extract_prefix("SM2609")
        'SM'
        >>> FuturesContractMapper.extract_prefix("I2609")
        'I'
        >>> FuturesContractMapper.extract_prefix("RB")
        'RB'
        """
        match = re.match(r"^([A-Za-z]+)", symbol.strip())
        return match.group(1).upper() if match else symbol.upper()

    @staticmethod
    def get_digit_part(symbol: str) -> Optional[str]:
        """从合约代码中提取数字部分。

        >>> FuturesContractMapper.get_digit_part("SM2609")
        '2609'
        >>> FuturesContractMapper.get_digit_part("SM609")
        '609'
        >>> FuturesContractMapper.get_digit_part("SM")
        None
        """
        match = FuturesContractMapper._CONTRACT_RE.match(symbol.strip().upper())
        return match.group(2) if match else None

    @staticmethod
    def detect_format(symbol: str) -> Optional[int]:
        """检测年份格式: 1 (1位年份) / 2 (2位年份) / None (非合约代码)。

        判断规则: 4位数字 = 2位年份 + 2位月份; 3位数字 = 1位年份 + 2位月份。

        >>> FuturesContractMapper.detect_format("SM2609")
        2
        >>> FuturesContractMapper.detect_format("SM609")
        1
        >>> FuturesContractMapper.detect_format("SM")
        None
        """
        digits = FuturesContractMapper.get_digit_part(symbol)
        if digits is None:
            return None
        if len(digits) == 4:
            return 2
        if len(digits) == 3:
            return 1
        return None

    @staticmethod
    def to_2digit_format(symbol: str) -> str:
        """转换为2位年份格式（TDX/东方财富风格）。

        >>> FuturesContractMapper.to_2digit_format("SM609")
        'SM2609'
        >>> FuturesContractMapper.to_2digit_format("SM2609")
        'SM2609'
        """
        return FuturesContractMapper._convert(symbol, target_len=4)

    @staticmethod
    def to_1digit_format(symbol: str) -> str:
        """转换为1位年份格式（TqSDK/天勤风格）。

        >>> FuturesContractMapper.to_1digit_format("SM2609")
        'SM609'
        >>> FuturesContractMapper.to_1digit_format("SM609")
        'SM609'
        """
        return FuturesContractMapper._convert(symbol, target_len=3)

    @staticmethod
    def is_same_contract(code1: str, code2: str) -> bool:
        """判断两个合约代码是否指向同一合约（格式可能不同）。

        >>> FuturesContractMapper.is_same_contract("SM2609", "SM609")
        True
        >>> FuturesContractMapper.is_same_contract("SM2609", "SM2609")
        True
        >>> FuturesContractMapper.is_same_contract("SM2609", "RB2501")
        False
        """
        norm1 = FuturesContractMapper.to_2digit_format(code1)
        norm2 = FuturesContractMapper.to_2digit_format(code2)
        return norm1 == norm2

    @staticmethod
    def try_resolve_variety(symbol: str, known_prefixes: set[str]) -> Optional[str]:
        """尝试从合约代码中解析出已知的品种代码。

        如果 ``symbol`` 是合约代码（如 ``SM2609``）且前缀（``SM``）在
        ``known_prefixes`` 中，返回品种代码；否则返回 None。

        这用于 SymbolRegistry 识别期货合约代码并路由到期货市场。
        """
        prefix = FuturesContractMapper.extract_prefix(symbol)
        if prefix in known_prefixes:
            return prefix
        # 有些品种的前缀是单字母（如 I, A, B, C, M 等）
        # 提取前缀后检查是否为已知品种
        return None

    # ---- 内部方法 ----

    @staticmethod
    def _convert(symbol: str, target_len: int) -> str:
        """内部转换实现。

        Args:
            symbol: 输入合约代码
            target_len: 目标数字部分长度（3=1位年份, 4=2位年份）

        Returns:
            转换后的合约代码，若无法识别则原样返回
        """
        s = symbol.strip().upper()
        match = FuturesContractMapper._CONTRACT_RE.match(s)
        if not match:
            return s  # 不是合约代码，原样返回

        prefix = match.group(1)
        digits = match.group(2)
        current_len = len(digits)

        if current_len == target_len:
            return s  # 已经是目标格式

        if current_len == 4 and target_len == 3:
            # 2位年份 → 1位年份: 取年份十位数
            year_2d = digits[:2]
            month = digits[2:]
            year_1d = str(int(year_2d) % 10)
            return f"{prefix}{year_1d}{month}"

        if current_len == 3 and target_len == 4:
            # 1位年份 → 2位年份: 补当前年代前缀
            year_1d = digits[:1]
            month = digits[1:]
            # 当前为 2020 年代，补 "2"
            year_2d = f"2{year_1d}"
            return f"{prefix}{year_2d}{month}"

        return s  # 无法转换，原样返回
