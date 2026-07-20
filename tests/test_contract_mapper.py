"""测试 FuturesContractMapper 期货合约符号映射器。"""

from datacore.registry.contract_mapper import FuturesContractMapper


class TestIsContractCode:
    def test_2digit_year_code(self):
        assert FuturesContractMapper.is_contract_code("SM2609") is True
        assert FuturesContractMapper.is_contract_code("RB2501") is True
        assert FuturesContractMapper.is_contract_code("CU2503") is True

    def test_1digit_year_code(self):
        assert FuturesContractMapper.is_contract_code("SM609") is True
        assert FuturesContractMapper.is_contract_code("RB501") is True
        assert FuturesContractMapper.is_contract_code("CU503") is True

    def test_1letter_prefix(self):
        assert FuturesContractMapper.is_contract_code("I2609") is True
        assert FuturesContractMapper.is_contract_code("M2505") is True
        assert FuturesContractMapper.is_contract_code("A609") is True

    def test_variety_code(self):
        assert FuturesContractMapper.is_contract_code("SM") is False
        assert FuturesContractMapper.is_contract_code("RB") is False
        assert FuturesContractMapper.is_contract_code("CU") is False

    def test_invalid(self):
        assert FuturesContractMapper.is_contract_code("") is False
        assert FuturesContractMapper.is_contract_code("123456") is False
        assert FuturesContractMapper.is_contract_code("ABC") is False


class TestExtractPrefix:
    def test_two_letter_prefix(self):
        assert FuturesContractMapper.extract_prefix("SM2609") == "SM"
        assert FuturesContractMapper.extract_prefix("RB2501") == "RB"

    def test_one_letter_prefix(self):
        assert FuturesContractMapper.extract_prefix("I2609") == "I"
        assert FuturesContractMapper.extract_prefix("M2505") == "M"

    def test_variety_code(self):
        assert FuturesContractMapper.extract_prefix("SM") == "SM"
        assert FuturesContractMapper.extract_prefix("RB") == "RB"


class TestDetectFormat:
    def test_detect_2digit(self):
        assert FuturesContractMapper.detect_format("SM2609") == 2
        assert FuturesContractMapper.detect_format("RB2501") == 2

    def test_detect_1digit(self):
        assert FuturesContractMapper.detect_format("SM609") == 1
        assert FuturesContractMapper.detect_format("RB501") == 1

    def test_detect_variety(self):
        assert FuturesContractMapper.detect_format("SM") is None


class TestConvertTo2Digit:
    def test_1digit_to_2digit(self):
        assert FuturesContractMapper.to_2digit_format("SM609") == "SM2609"
        assert FuturesContractMapper.to_2digit_format("RB501") == "RB2501"

    def test_2digit_unchanged(self):
        assert FuturesContractMapper.to_2digit_format("SM2609") == "SM2609"

    def test_1letter_prefix(self):
        assert FuturesContractMapper.to_2digit_format("I609") == "I2609"

    def test_variety_unchanged(self):
        assert FuturesContractMapper.to_2digit_format("SM") == "SM"


class TestConvertTo1Digit:
    def test_2digit_to_1digit(self):
        assert FuturesContractMapper.to_1digit_format("SM2609") == "SM609"
        assert FuturesContractMapper.to_1digit_format("RB2501") == "RB501"

    def test_1digit_unchanged(self):
        assert FuturesContractMapper.to_1digit_format("SM609") == "SM609"

    def test_1letter_prefix(self):
        assert FuturesContractMapper.to_1digit_format("I2609") == "I609"

    def test_variety_unchanged(self):
        assert FuturesContractMapper.to_1digit_format("SM") == "SM"


class TestIsSameContract:
    def test_same_contract_different_formats(self):
        assert FuturesContractMapper.is_same_contract("SM2609", "SM609") is True
        assert FuturesContractMapper.is_same_contract("RB2501", "RB501") is True

    def test_same_format(self):
        assert FuturesContractMapper.is_same_contract("SM2609", "SM2609") is True

    def test_different_contracts(self):
        assert FuturesContractMapper.is_same_contract("SM2609", "SM2501") is False
        assert FuturesContractMapper.is_same_contract("SM2609", "RB2501") is False


class TestTryResolveVariety:
    def test_known_variety(self):
        known = {"SM", "RB", "CU", "I", "A"}
        assert FuturesContractMapper.try_resolve_variety("SM2609", known) == "SM"
        assert FuturesContractMapper.try_resolve_variety("SM609", known) == "SM"
        assert FuturesContractMapper.try_resolve_variety("I2609", known) == "I"

    def test_unknown_variety(self):
        known = {"RB", "CU"}
        assert FuturesContractMapper.try_resolve_variety("SM2609", known) is None

    def test_variety_code_itself(self):
        known = {"SM", "RB"}
        assert FuturesContractMapper.try_resolve_variety("SM", known) == "SM"


class TestNormalizeInProviders:
    """模拟 FuturesDataSource 子类的 normalize_symbol 行为。"""

    def test_tdx_normalize(self):
        """TDX 用 2 位年份: SM609 → SM2609, SM2609 不变"""
        from datacore.registry.contract_mapper import FuturesContractMapper

        def tdx_normalize(symbol: str) -> str:
            if FuturesContractMapper.is_contract_code(symbol):
                fmt = FuturesContractMapper.detect_format(symbol)
                if fmt == 1:
                    return FuturesContractMapper.to_2digit_format(symbol)
            return symbol

        assert tdx_normalize("SM2609") == "SM2609"
        assert tdx_normalize("SM609") == "SM2609"
        assert tdx_normalize("SM") == "SM"

    def test_tqsdk_normalize(self):
        """TqSDK 用 1 位年份: SM2609 → SM609, SM609 不变"""
        from datacore.registry.contract_mapper import FuturesContractMapper

        def tqsdk_normalize(symbol: str) -> str:
            if FuturesContractMapper.is_contract_code(symbol):
                fmt = FuturesContractMapper.detect_format(symbol)
                if fmt == 2:
                    return FuturesContractMapper.to_1digit_format(symbol)
            return symbol

        assert tqsdk_normalize("SM609") == "SM609"
        assert tqsdk_normalize("SM2609") == "SM609"
        assert tqsdk_normalize("SM") == "SM"


class TestEdgeCases:
    def test_lowercase_input(self):
        assert FuturesContractMapper.to_2digit_format("sm609") == "SM2609"
        assert FuturesContractMapper.to_2digit_format("sm2609") == "SM2609"

    def test_mixed_case(self):
        assert FuturesContractMapper.to_2digit_format("Sm609") == "SM2609"

    def test_get_digit_part(self):
        assert FuturesContractMapper.get_digit_part("SM2609") == "2609"
        assert FuturesContractMapper.get_digit_part("SM609") == "609"
        assert FuturesContractMapper.get_digit_part("SM") is None

    def test_current_year_assumption(self):
        """1位年份→2位年份补 '2' 前缀，适用于 2020-2029 年代。"""
        assert FuturesContractMapper.to_2digit_format("SM701") == "SM2701"
        assert FuturesContractMapper.to_2digit_format("SM803") == "SM2803"
