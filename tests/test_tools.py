"""Tests for datacore.tools - 工具接口层模块测试。"""

from __future__ import annotations

import asyncio
import pytest

from datacore.tools.base import DataCoreBaseTool
from datacore.tools import (
    all_tools,
    get_tool_by_name,
    DataCoreOHLCVTool,
    DataCoreQuoteTool,
    DataCoreSentimentTool,
    DataCoreHealthTool,
    DataCoreListSymbolsTool,
    DataCoreMacroTool,
    DataCoreFundamentalTool,
    DataCoreF10Tool,
    DataCoreIndicatorsTool,
    DataCoreTermStructureTool,
    DataCoreBasisTool,
    DataCoreMarketRegimeTool,
    DataCoreNewsTool,
    DataCoreAdjustmentTool,
    DataCorePeriodTool,
    UnitUnifyTool,
    DateAlignTool,
    DuplicateMergeTool,
    OutlierFilterTool,
    CrossSourceVerifyTool,
    DataMissingDetectTool,
    CalMathComputeTool,
    ConfigReadTool,
)


class _ConcreteTool(DataCoreBaseTool):
    """测试用的具体工具类。"""

    name = "test_concrete_tool"
    description = "测试用的具体工具"

    def _run(self, x: int = 0, y: int = 0, **kwargs):
        return {"sum": x + y, "product": x * y}


class _AsyncTool(DataCoreBaseTool):
    """测试用的异步工具类。"""

    name = "test_async_tool"
    description = "测试用的异步工具"

    def _run(self, value: str = "", **kwargs):
        return f"sync_{value}"

    async def _arun(self, value: str = "", **kwargs):
        await asyncio.sleep(0.01)
        return f"async_{value}"


class _ErrorTool(DataCoreBaseTool):
    """测试用的抛错工具类。"""

    name = "test_error_tool"
    description = "测试用的抛错工具"

    def _run(self, **kwargs):
        raise ValueError("故意抛出的错误")


# ============================================================
#  基类功能测试
# ============================================================

class TestDataCoreBaseTool:
    """DataCoreBaseTool 基类测试。"""

    def test_base_tool_is_abstract(self):
        """基类不能直接实例化。"""
        with pytest.raises(TypeError):
            DataCoreBaseTool()

    def test_concrete_tool_instantiation(self):
        """具体工具类可以实例化。"""
        tool = _ConcreteTool()
        assert tool is not None
        assert tool.name == "test_concrete_tool"
        assert tool.description == "测试用的具体工具"

    def test_tool_has_name_and_description(self):
        """工具必须有 name 和 description 属性。"""
        tool = _ConcreteTool()
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert tool.name != ""
        assert tool.description != ""

    def test_tool_has_run_method(self):
        """工具必须有 _run 方法。"""
        tool = _ConcreteTool()
        assert hasattr(tool, "_run")
        assert callable(tool._run)

    def test_tool_has_arun_method(self):
        """工具必须有 _arun 方法。"""
        tool = _ConcreteTool()
        assert hasattr(tool, "_arun")
        assert callable(tool._arun)

    def test_tool_has_invoke_method(self):
        """工具必须有 invoke 方法（LangChain 兼容）。"""
        tool = _ConcreteTool()
        assert hasattr(tool, "invoke")
        assert callable(tool.invoke)

    def test_tool_has_ainvoke_method(self):
        """工具必须有 ainvoke 异步方法。"""
        tool = _ConcreteTool()
        assert hasattr(tool, "ainvoke")
        assert callable(tool.ainvoke)

    def test_run_sync_execution(self):
        """同步 _run 正常执行。"""
        tool = _ConcreteTool()
        result = tool._run(x=3, y=4)
        assert result["sum"] == 7
        assert result["product"] == 12

    def test_invoke_success(self):
        """invoke 成功返回结果。"""
        tool = _ConcreteTool()
        result = tool.invoke({"x": 5, "y": 3})
        assert result["success"] is True
        assert result["result"]["sum"] == 8
        assert result["tool_name"] == "test_concrete_tool"

    def test_invoke_with_kwargs(self):
        """invoke 支持 kwargs 参数。"""
        tool = _ConcreteTool()
        result = tool.invoke(x=2, y=5)
        assert result["success"] is True
        assert result["result"]["sum"] == 7

    def test_invoke_error_handling(self):
        """invoke 错误处理。"""
        tool = _ErrorTool()
        result = tool.invoke()
        assert result["success"] is False
        assert "error" in result
        assert "error_type" in result
        assert result["error_type"] == "ValueError"
        assert "故意抛出的错误" in result["error"]

    def test_arun_default_calls_sync(self):
        """默认 _arun 调用同步版本。"""
        tool = _ConcreteTool()
        result = asyncio.run(tool._arun(x=2, y=3))
        assert result["sum"] == 5

    def test_arun_custom_implementation(self):
        """自定义 _arun 实现。"""
        tool = _AsyncTool()
        result = asyncio.run(tool._arun(value="hello"))
        assert result == "async_hello"

    def test_ainvoke_success(self):
        """ainvoke 成功返回结果。"""
        tool = _AsyncTool()
        result = asyncio.run(tool.ainvoke({"value": "test"}))
        assert result["success"] is True
        assert result["result"] == "async_test"
        assert result["tool_name"] == "test_async_tool"

    def test_ainvoke_error_handling(self):
        """ainvoke 错误处理。"""
        tool = _ErrorTool()
        result = asyncio.run(tool.ainvoke())
        assert result["success"] is False
        assert "error" in result

    def test_call_method(self):
        """__call__ 方法直接调用 _run。"""
        tool = _ConcreteTool()
        result = tool(x=4, y=5)
        assert result["sum"] == 9

    def test_to_dict(self):
        """_to_dict 序列化。"""
        tool = _ConcreteTool()
        d = tool._to_dict()
        assert d["name"] == "test_concrete_tool"
        assert d["description"] == "测试用的具体工具"
        assert "args_schema" in d

    def test_repr(self):
        """__repr__ 方法。"""
        tool = _ConcreteTool()
        r = repr(tool)
        assert "test_concrete_tool" in r
        assert "_ConcreteTool" in r

    def test_kwargs_initialization(self):
        """通过 kwargs 初始化属性。"""
        tool = _ConcreteTool(verbose=True, return_direct=True)
        assert tool.verbose is True
        assert tool.return_direct is True

    def test_default_return_direct_false(self):
        """默认 return_direct 为 False。"""
        tool = _ConcreteTool()
        assert tool.return_direct is False

    def test_default_verbose_false(self):
        """默认 verbose 为 False。"""
        tool = _ConcreteTool()
        assert tool.verbose is False

    def test_args_schema_default_none(self):
        """默认 args_schema 为 None。"""
        tool = _ConcreteTool()
        assert tool.args_schema is None


# ============================================================
#  all_tools 自动发现测试
# ============================================================

class TestAllToolsDiscovery:
    """all_tools 自动发现测试。"""

    def test_all_tools_is_list(self):
        """all_tools 是列表。"""
        assert isinstance(all_tools, list)

    def test_all_tools_not_empty(self):
        """all_tools 不为空。"""
        assert len(all_tools) > 0

    def test_all_tools_count(self):
        """all_tools 包含预期数量的工具。"""
        assert len(all_tools) >= 20

    def test_all_tools_are_instances(self):
        """all_tools 中的元素都是工具实例。"""
        for tool in all_tools:
            assert isinstance(tool, DataCoreBaseTool)

    def test_all_tools_have_unique_names(self):
        """所有工具名称唯一。"""
        names = [tool.name for tool in all_tools]
        assert len(names) == len(set(names))

    def test_all_tools_name_prefix(self):
        """所有工具名称以 datacore_ 开头。"""
        for tool in all_tools:
            assert tool.name.startswith("datacore_"), f"{tool.name} 不以 datacore_ 开头"

    def test_get_tool_by_name_exists(self):
        """get_tool_by_name 能找到存在的工具。"""
        tool = get_tool_by_name("datacore_ohlcv")
        assert tool is not None
        assert isinstance(tool, DataCoreOHLCVTool)

    def test_get_tool_by_name_not_exists(self):
        """get_tool_by_name 找不到返回 None。"""
        tool = get_tool_by_name("nonexistent_tool")
        assert tool is None

    def test_all_tools_have_description(self):
        """所有工具有非空描述。"""
        for tool in all_tools:
            assert tool.description != "", f"{tool.name} 没有 description"


# ============================================================
#  各 Tool 实例化和基本功能测试
# ============================================================

class TestToolInstantiation:
    """各 Tool 实例化测试。"""

    def test_ohlcv_tool_instantiate(self):
        """OHLCV 工具实例化。"""
        tool = DataCoreOHLCVTool()
        assert tool.name == "datacore_ohlcv"
        assert "OHLCV" in tool.description

    def test_quote_tool_instantiate(self):
        """Quote 工具实例化。"""
        tool = DataCoreQuoteTool()
        assert tool.name == "datacore_quote"

    def test_sentiment_tool_instantiate(self):
        """Sentiment 工具实例化。"""
        tool = DataCoreSentimentTool()
        assert tool.name == "datacore_sentiment"

    def test_health_tool_instantiate(self):
        """Health 工具实例化。"""
        tool = DataCoreHealthTool()
        assert tool.name == "datacore_health"

    def test_list_symbols_tool_instantiate(self):
        """ListSymbols 工具实例化。"""
        tool = DataCoreListSymbolsTool()
        assert tool.name == "datacore_list_symbols"

    def test_macro_tool_instantiate(self):
        """Macro 工具实例化。"""
        tool = DataCoreMacroTool()
        assert tool.name == "datacore_macro"

    def test_fundamental_tool_instantiate(self):
        """Fundamental 工具实例化。"""
        tool = DataCoreFundamentalTool()
        assert tool.name == "datacore_fundamental"

    def test_f10_tool_instantiate(self):
        """F10 工具实例化。"""
        tool = DataCoreF10Tool()
        assert tool.name == "datacore_f10"

    def test_indicators_tool_instantiate(self):
        """Indicators 工具实例化。"""
        tool = DataCoreIndicatorsTool()
        assert tool.name == "datacore_indicators"

    def test_term_structure_tool_instantiate(self):
        """TermStructure 工具实例化。"""
        tool = DataCoreTermStructureTool()
        assert tool.name == "datacore_term_structure"

    def test_basis_tool_instantiate(self):
        """Basis 工具实例化。"""
        tool = DataCoreBasisTool()
        assert tool.name == "datacore_basis"

    def test_market_regime_tool_instantiate(self):
        """MarketRegime 工具实例化。"""
        tool = DataCoreMarketRegimeTool()
        assert tool.name == "datacore_market_regime"

    def test_news_tool_instantiate(self):
        """News 工具实例化。"""
        tool = DataCoreNewsTool()
        assert tool.name == "datacore_news"

    def test_adjustment_tool_instantiate(self):
        """Adjustment 工具实例化。"""
        tool = DataCoreAdjustmentTool()
        assert tool.name == "datacore_adjustment"

    def test_period_tool_instantiate(self):
        """Period 工具实例化。"""
        tool = DataCorePeriodTool()
        assert tool.name == "datacore_period"

    def test_unit_unify_tool_instantiate(self):
        """UnitUnify 工具实例化。"""
        tool = UnitUnifyTool()
        assert tool.name == "datacore_unit_unify"

    def test_date_align_tool_instantiate(self):
        """DateAlign 工具实例化。"""
        tool = DateAlignTool()
        assert tool.name == "datacore_date_align"

    def test_duplicate_merge_tool_instantiate(self):
        """DuplicateMerge 工具实例化。"""
        tool = DuplicateMergeTool()
        assert tool.name == "datacore_duplicate_merge"

    def test_outlier_filter_tool_instantiate(self):
        """OutlierFilter 工具实例化。"""
        tool = OutlierFilterTool()
        assert tool.name == "datacore_outlier_filter"

    def test_cross_source_tool_instantiate(self):
        """CrossSourceVerify 工具实例化。"""
        tool = CrossSourceVerifyTool()
        assert tool.name == "datacore_cross_source_verify"

    def test_missing_detect_tool_instantiate(self):
        """DataMissingDetect 工具实例化。"""
        tool = DataMissingDetectTool()
        assert tool.name == "datacore_missing_detect"

    def test_cal_math_tool_instantiate(self):
        """CalMathCompute 工具实例化。"""
        tool = CalMathComputeTool()
        assert tool.name == "datacore_cal_math"

    def test_config_read_tool_instantiate(self):
        """ConfigRead 工具实例化。"""
        tool = ConfigReadTool()
        assert tool.name == "datacore_config_read"


# ============================================================
#  LangChain 协议兼容性测试
# ============================================================

class TestLangChainCompatibility:
    """LangChain 协议兼容性测试。"""

    def test_invoke_signature(self):
        """invoke 方法签名兼容 LangChain。"""
        tool = _ConcreteTool()
        result = tool.invoke(input={"x": 1, "y": 2})
        assert "success" in result
        assert "result" in result

    def test_invoke_with_config(self):
        """invoke 支持 config 参数（LangChain 兼容）。"""
        tool = _ConcreteTool()
        result = tool.invoke({"x": 1, "y": 2}, config={"callbacks": []})
        assert result["success"] is True

    def test_ainvoke_signature(self):
        """ainvoke 方法签名兼容 LangChain。"""
        tool = _AsyncTool()
        result = asyncio.run(tool.ainvoke(input={"value": "x"}))
        assert "success" in result

    def test_ainvoke_with_config(self):
        """ainvoke 支持 config 参数。"""
        tool = _AsyncTool()
        result = asyncio.run(tool.ainvoke({"value": "x"}, config=None))
        assert result["success"] is True

    def test_return_dict_structure(self):
        """返回字典结构一致。"""
        tool = _ConcreteTool()
        result = tool.invoke({"x": 1, "y": 1})
        assert set(result.keys()) >= {"success", "result", "tool_name"}


# ============================================================
#  数据清洗工具测试
# ============================================================

class TestCleaningTools:
    """数据清洗工具测试。"""

    def test_unit_unify_basic(self):
        """单位统一基础测试。"""
        tool = UnitUnifyTool()
        data = [{"value": 10000, "name": "test"}]
        result = tool.invoke({
            "data": data,
            "target_unit": "万元",
            "source_unit": "元",
            "fields": ["value"],
        })
        assert result["success"] is True
        assert result["result"]["data"][0]["value"] == 1

    def test_date_align_basic(self):
        """日期对齐基础测试。"""
        tool = DateAlignTool()
        series = {
            "a": [
                {"datetime": "2024-01-01", "value": 1},
                {"datetime": "2024-01-02", "value": 2},
            ],
            "b": [
                {"datetime": "2024-01-02", "value": 3},
                {"datetime": "2024-01-03", "value": 4},
            ],
        }
        result = tool.invoke({"series": series, "method": "drop"})
        assert result["success"] is True

    def test_duplicate_merge_first(self):
        """重复数据合并（first 策略）。"""
        tool = DuplicateMergeTool()
        data = [
            {"id": 1, "value": 10},
            {"id": 1, "value": 20},
            {"id": 2, "value": 30},
        ]
        result = tool.invoke({
            "data": data,
            "keys": ["id"],
            "strategy": "first",
        })
        assert result["success"] is True
        assert result["result"]["final_count"] == 2
        assert result["result"]["data"][0]["value"] == 10

    def test_outlier_filter_iqr(self):
        """异常值过滤（IQR 方法）。"""
        tool = OutlierFilterTool()
        data = [
            {"val": 1}, {"val": 2}, {"val": 3}, {"val": 4}, {"val": 5},
            {"val": 100},
        ]
        result = tool.invoke({
            "data": data,
            "field": "val",
            "method": "iqr",
            "action": "mark",
        })
        assert result["success"] is True
        assert result["result"]["outlier_count"] >= 0

    def test_outlier_filter_zscore(self):
        """异常值过滤（Z-score 方法）。"""
        tool = OutlierFilterTool()
        data = [{"val": i} for i in range(100)] + [{"val": 1000}]
        result = tool.invoke({
            "data": data,
            "field": "val",
            "method": "zscore",
            "action": "mark",
        })
        assert result["success"] is True

    def test_outlier_filter_remove(self):
        """异常值过滤 - remove 动作。"""
        tool = OutlierFilterTool()
        data = [
            {"val": 1}, {"val": 2}, {"val": 3}, {"val": 4}, {"val": 5},
            {"val": 100},
        ]
        result = tool.invoke({
            "data": data,
            "field": "val",
            "method": "iqr",
            "action": "remove",
        })
        assert result["success"] is True
        assert len(result["result"]["data"]) < len(data)

    def test_outlier_filter_replace_median(self):
        """异常值过滤 - replace 动作用中位数替换。"""
        tool = OutlierFilterTool()
        data = [
            {"val": 1}, {"val": 2}, {"val": 3}, {"val": 4}, {"val": 5},
            {"val": 100},
        ]
        result = tool.invoke({
            "data": data,
            "field": "val",
            "method": "iqr",
            "action": "replace",
            "replace_value": "median",
        })
        assert result["success"] is True
        assert result["result"]["data"][-1]["val"] != 100

    def test_outlier_filter_replace_mean(self):
        """异常值过滤 - replace 动作用均值替换。"""
        tool = OutlierFilterTool()
        data = [
            {"val": 1}, {"val": 2}, {"val": 3}, {"val": 4}, {"val": 5},
            {"val": 100},
        ]
        result = tool.invoke({
            "data": data,
            "field": "val",
            "method": "iqr",
            "action": "replace",
            "replace_value": "mean",
        })
        assert result["success"] is True

    def test_outlier_filter_replace_custom(self):
        """异常值过滤 - replace 动作用自定义值替换。"""
        tool = OutlierFilterTool()
        data = [
            {"val": 1}, {"val": 2}, {"val": 3}, {"val": 4}, {"val": 5},
            {"val": 100},
        ]
        result = tool.invoke({
            "data": data,
            "field": "val",
            "method": "iqr",
            "action": "replace",
            "replace_value": 0,
        })
        assert result["success"] is True
        assert result["result"]["data"][-1]["val"] == 0

    def test_outlier_filter_empty_data(self):
        """异常值过滤 - 空数据。"""
        tool = OutlierFilterTool()
        result = tool.invoke({
            "data": [],
            "field": "val",
            "method": "iqr",
        })
        assert result["success"] is True
        assert result["result"]["outlier_count"] == 0

    def test_outlier_filter_missing_field(self):
        """异常值过滤 - 缺少字段。"""
        tool = OutlierFilterTool()
        data = [{"other": 1}]
        result = tool.invoke({
            "data": data,
            "field": "nonexistent",
            "method": "iqr",
        })
        assert result["success"] is True
        assert result["result"]["outlier_count"] == 0

    def test_duplicate_merge_last(self):
        """重复数据合并（last 策略）。"""
        tool = DuplicateMergeTool()
        data = [
            {"id": 1, "value": 10},
            {"id": 1, "value": 20},
            {"id": 2, "value": 30},
        ]
        result = tool.invoke({
            "data": data,
            "keys": ["id"],
            "strategy": "last",
        })
        assert result["success"] is True
        assert result["result"]["data"][0]["value"] == 20

    def test_duplicate_merge_mean(self):
        """重复数据合并（mean 策略）。"""
        tool = DuplicateMergeTool()
        data = [
            {"id": 1, "value": 10},
            {"id": 1, "value": 30},
            {"id": 2, "value": 30},
        ]
        result = tool.invoke({
            "data": data,
            "keys": ["id"],
            "strategy": "mean",
        })
        assert result["success"] is True
        assert result["result"]["data"][0]["value"] == 20

    def test_duplicate_merge_max(self):
        """重复数据合并（max 策略）。"""
        tool = DuplicateMergeTool()
        data = [
            {"id": 1, "value": 10},
            {"id": 1, "value": 30},
        ]
        result = tool.invoke({
            "data": data,
            "keys": ["id"],
            "strategy": "max",
        })
        assert result["success"] is True
        assert result["result"]["data"][0]["value"] == 30

    def test_duplicate_merge_min(self):
        """重复数据合并（min 策略）。"""
        tool = DuplicateMergeTool()
        data = [
            {"id": 1, "value": 10},
            {"id": 1, "value": 30},
        ]
        result = tool.invoke({
            "data": data,
            "keys": ["id"],
            "strategy": "min",
        })
        assert result["success"] is True
        assert result["result"]["data"][0]["value"] == 10

    def test_duplicate_merge_empty(self):
        """重复数据合并 - 空数据。"""
        tool = DuplicateMergeTool()
        result = tool.invoke({
            "data": [],
            "keys": ["id"],
        })
        assert result["success"] is True
        assert result["result"]["original_count"] == 0
        assert len(result["result"]["data"]) == 0

    def test_date_align_bfill(self):
        """日期对齐 - bfill 方法。"""
        tool = DateAlignTool()
        series = {
            "a": [
                {"datetime": "2024-01-01", "value": 1},
                {"datetime": "2024-01-02", "value": 2},
            ],
            "b": [
                {"datetime": "2024-01-02", "value": 3},
                {"datetime": "2024-01-03", "value": 4},
            ],
        }
        result = tool.invoke({"series": series, "method": "bfill"})
        assert result["success"] is True

    def test_date_align_interpolate(self):
        """日期对齐 - interpolate 方法。"""
        tool = DateAlignTool()
        series = {
            "a": [
                {"datetime": "2024-01-01", "value": 1},
                {"datetime": "2024-01-03", "value": 3},
            ],
        }
        result = tool.invoke({"series": series, "method": "interpolate"})
        assert result["success"] is True


# ============================================================
#  数据验证工具测试
# ============================================================

class TestValidationTools:
    """数据验证工具测试。"""

    def test_cross_source_verify_basic(self):
        """跨源校验基础测试。"""
        tool = CrossSourceVerifyTool()
        source_data = {
            "src_a": [
                {"datetime": "2024-01-01", "price": 100},
                {"datetime": "2024-01-02", "price": 101},
            ],
            "src_b": [
                {"datetime": "2024-01-01", "price": 100.5},
                {"datetime": "2024-01-02", "price": 101.5},
            ],
        }
        result = tool.invoke({
            "source_data": source_data,
            "field": "price",
            "tolerance": 0.01,
        })
        assert result["success"] is True

    def test_cross_source_verify_diff_method(self):
        """跨源校验 - diff 方法。"""
        tool = CrossSourceVerifyTool()
        source_data = {
            "src_a": [
                {"datetime": "2024-01-01", "price": 100},
                {"datetime": "2024-01-02", "price": 101},
            ],
            "src_b": [
                {"datetime": "2024-01-01", "price": 101},
                {"datetime": "2024-01-02", "price": 102},
            ],
        }
        result = tool.invoke({
            "source_data": source_data,
            "field": "price",
            "method": "diff",
            "tolerance": 2.0,
        })
        assert result["success"] is True

    def test_cross_source_verify_correlation_method(self):
        """跨源校验 - correlation 方法。"""
        tool = CrossSourceVerifyTool()
        source_data = {
            "src_a": [
                {"datetime": "2024-01-01", "price": 100},
                {"datetime": "2024-01-02", "price": 200},
                {"datetime": "2024-01-03", "price": 300},
            ],
            "src_b": [
                {"datetime": "2024-01-01", "price": 101},
                {"datetime": "2024-01-02", "price": 202},
                {"datetime": "2024-01-03", "price": 303},
            ],
        }
        result = tool.invoke({
            "source_data": source_data,
            "field": "price",
            "method": "correlation",
            "tolerance": 0.05,
        })
        assert result["success"] is True

    def test_cross_source_verify_single_source(self):
        """跨源校验 - 单源报错。"""
        tool = CrossSourceVerifyTool()
        source_data = {
            "src_a": [{"datetime": "2024-01-01", "price": 100}],
        }
        result = tool.invoke({
            "source_data": source_data,
            "field": "price",
        })
        assert result["success"] is True
        assert result["result"]["success"] is False

    def test_cross_source_verify_no_valid_points(self):
        """跨源校验 - 无有效对比点（两源无交集日期）。"""
        tool = CrossSourceVerifyTool()
        source_data = {
            "src_a": [
                {"datetime": "2024-01-01", "price": 100},
            ],
            "src_b": [
                {"datetime": "2024-01-02", "price": 101},
            ],
        }
        result = tool.invoke({
            "source_data": source_data,
            "field": "price",
        })
        assert result["success"] is True
        assert "comparisons" in result["result"]
        src_b_result = result["result"]["comparisons"]["src_b"]
        assert src_b_result["valid_points"] == 0

    def test_missing_detect_basic(self):
        """缺失检测基础测试。"""
        tool = DataMissingDetectTool()
        data = [
            {"datetime": "2024-01-01", "value": 1},
            {"datetime": "2024-01-02", "value": None},
            {"datetime": "2024-01-03", "value": 3},
        ]
        result = tool.invoke({"data": data, "fields": ["value"]})
        assert result["success"] is True
        assert 0 <= result["result"]["completeness"] <= 1

    def test_missing_detect_empty(self):
        """缺失检测 - 空数据。"""
        tool = DataMissingDetectTool()
        result = tool.invoke({"data": []})
        assert result["success"] is True
        assert result["result"]["total_rows"] == 0
        assert result["result"]["completeness"] == 1.0

    def test_missing_detect_no_date_col(self):
        """缺失检测 - 无日期列（非时间序列）。"""
        tool = DataMissingDetectTool()
        data = [
            {"a": 1, "b": None},
            {"a": 2, "b": 3},
        ]
        result = tool.invoke({"data": data})
        assert result["success"] is True
        assert result["result"]["is_timeseries"] is False

    def test_missing_detect_with_details(self):
        """缺失检测 - 返回详细缺失位置。"""
        tool = DataMissingDetectTool()
        data = [
            {"datetime": "2024-01-01", "value": 1},
            {"datetime": "2024-01-02", "value": None},
            {"datetime": "2024-01-03", "value": 3},
        ]
        result = tool.invoke({"data": data, "return_details": True})
        assert result["success"] is True
        assert "missing_details" in result["result"]

    def test_cal_math_ohlc_validate(self):
        """数学校验 OHLC 验证。"""
        tool = CalMathComputeTool()
        data = [
            {"open": 10, "high": 12, "low": 9, "close": 11},
            {"open": 11, "high": 8, "low": 10, "close": 9},
        ]
        result = tool.invoke({"data": data, "operation": "ohlc_validate"})
        assert result["success"] is True
        assert result["result"]["issue_count"] > 0

    def test_cal_math_sum(self):
        """数学校验求和。"""
        tool = CalMathComputeTool()
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        result = tool.invoke({"data": data, "operation": "sum"})
        assert result["success"] is True
        assert result["result"]["results"]["a"] == 4

    def test_cal_math_unsupported_operation(self):
        """数学校验不支持的操作。"""
        tool = CalMathComputeTool()
        result = tool.invoke({"data": [], "operation": "invalid_op"})
        assert result["success"] is True
        assert result["result"]["success"] is False

    def test_cal_math_mean(self):
        """数学校验 - 均值计算。"""
        tool = CalMathComputeTool()
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        result = tool.invoke({"data": data, "operation": "mean"})
        assert result["success"] is True
        assert result["result"]["results"]["a"] == 2.0

    def test_cal_math_std(self):
        """数学校验 - 标准差计算。"""
        tool = CalMathComputeTool()
        data = [{"val": 1}, {"val": 2}, {"val": 3}]
        result = tool.invoke({"data": data, "operation": "std", "fields": ["val"]})
        assert result["success"] is True
        assert "val" in result["result"]["results"]

    def test_cal_math_correlation(self):
        """数学校验 - 相关性计算。"""
        tool = CalMathComputeTool()
        data = [{"x": 1, "y": 2}, {"x": 2, "y": 4}, {"x": 3, "y": 6}]
        result = tool.invoke({"data": data, "operation": "correlation"})
        assert result["success"] is True
        assert "correlation_matrix" in result["result"]

    def test_cal_math_rolling_mean(self):
        """数学校验 - 滚动均值计算。"""
        tool = CalMathComputeTool()
        data = [{"val": i} for i in range(10)]
        result = tool.invoke({
            "data": data,
            "operation": "rolling_calc",
            "params": {"window": 3, "func": "mean"},
        })
        assert result["success"] is True
        assert len(result["result"]["results"]["val"]) == 10

    def test_cal_math_rolling_std(self):
        """数学校验 - 滚动标准差计算。"""
        tool = CalMathComputeTool()
        data = [{"val": i} for i in range(10)]
        result = tool.invoke({
            "data": data,
            "operation": "rolling_calc",
            "params": {"window": 3, "func": "std"},
        })
        assert result["success"] is True

    def test_cal_math_rolling_max(self):
        """数学校验 - 滚动最大值。"""
        tool = CalMathComputeTool()
        data = [{"val": i} for i in range(10)]
        result = tool.invoke({
            "data": data,
            "operation": "rolling_calc",
            "params": {"window": 3, "func": "max"},
        })
        assert result["success"] is True

    def test_cal_math_rolling_min(self):
        """数学校验 - 滚动最小值。"""
        tool = CalMathComputeTool()
        data = [{"val": i} for i in range(10)]
        result = tool.invoke({
            "data": data,
            "operation": "rolling_calc",
            "params": {"window": 3, "func": "min"},
        })
        assert result["success"] is True

    def test_cal_math_rolling_sum(self):
        """数学校验 - 滚动求和。"""
        tool = CalMathComputeTool()
        data = [{"val": i} for i in range(10)]
        result = tool.invoke({
            "data": data,
            "operation": "rolling_calc",
            "params": {"window": 3, "func": "sum"},
        })
        assert result["success"] is True

    def test_cal_math_ohlc_missing_column(self):
        """数学校验 OHLC 验证 - 缺少列。"""
        tool = CalMathComputeTool()
        data = [{"open": 10, "high": 12}]
        result = tool.invoke({"data": data, "operation": "ohlc_validate"})
        assert result["success"] is True
        assert result["result"]["success"] is False

    def test_cal_math_ohlc_nan_values(self):
        """数学校验 OHLC 验证 - NaN 值跳过。"""
        tool = CalMathComputeTool()
        data = [
            {"open": None, "high": 12, "low": 9, "close": 11},
            {"open": 10, "high": 12, "low": 9, "close": 11},
        ]
        result = tool.invoke({"data": data, "operation": "ohlc_validate"})
        assert result["success"] is True
        assert result["result"]["issue_count"] == 0


# ============================================================
#  运维工具测试
# ============================================================

class TestOperationsTools:
    """运维工具测试。"""

    def test_config_read_all(self):
        """读取所有配置。"""
        tool = ConfigReadTool()
        result = tool.invoke()
        assert result["success"] is True
        assert "yaml_config" in result["result"]
        assert "env_config" in result["result"]

    def test_config_read_key(self):
        """读取指定配置键。"""
        tool = ConfigReadTool()
        result = tool.invoke({"key": "sources.tdx_lc.url"})
        assert result["success"] is True
        assert "value" in result["result"]

    def test_config_read_with_default(self):
        """读取配置带默认值。"""
        tool = ConfigReadTool()
        result = tool.invoke({
            "key": "nonexistent.key",
            "default": "fallback_value",
        })
        assert result["success"] is True
        assert result["result"]["value"] == "fallback_value"


# ============================================================
#  错误处理测试
# ============================================================

class TestErrorHandling:
    """错误处理测试。"""

    def test_invoke_returns_error_dict(self):
        """invoke 错误返回标准格式。"""
        tool = _ErrorTool()
        result = tool.invoke()
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert "tool_name" in result

    def test_ainvoke_returns_error_dict(self):
        """ainvoke 错误返回标准格式。"""
        tool = _ErrorTool()
        result = asyncio.run(tool.ainvoke())
        assert isinstance(result, dict)
        assert result["success"] is False

    def test_error_contains_type(self):
        """错误包含错误类型。"""
        tool = _ErrorTool()
        result = tool.invoke()
        assert "error_type" in result
        assert result["error_type"] == "ValueError"

    def test_tool_name_in_error(self):
        """错误结果包含工具名。"""
        tool = _ErrorTool()
        result = tool.invoke()
        assert result["tool_name"] == "test_error_tool"


# ============================================================
#  品种列表工具测试
# ============================================================

class TestListSymbolsTool:
    """品种列表工具测试。"""

    def test_list_all_symbols(self):
        """列出所有品种。"""
        tool = DataCoreListSymbolsTool()
        result = tool.invoke()
        assert result["success"] is True
        assert result["result"]["total"] > 0

    def test_list_futures_symbols(self):
        """列出期货品种。"""
        tool = DataCoreListSymbolsTool()
        result = tool.invoke({"market": "futures"})
        assert result["success"] is True
        assert result["result"]["total"] > 0

    def test_list_invalid_market(self):
        """无效市场类型。"""
        tool = DataCoreListSymbolsTool()
        result = tool.invoke({"market": "invalid"})
        assert result["success"] is True
        assert result["result"]["success"] is False

    def test_list_by_sector(self):
        """按板块筛选。"""
        tool = DataCoreListSymbolsTool()
        result = tool.invoke({"market": "futures", "sector": "黑色系"})
        assert result["success"] is True

    def test_list_symbols_have_required_fields(self):
        """品种包含必要字段。"""
        tool = DataCoreListSymbolsTool()
        result = tool.invoke({"market": "futures"})
        symbols = result["result"]["symbols"]
        if symbols:
            first = symbols[0]
            assert "symbol" in first
            assert "name" in first
            assert "market" in first
            assert "sector" in first


# ============================================================
#  技术指标工具测试
# ============================================================

class TestIndicatorsTool:
    """技术指标工具测试。"""

    def test_ma_indicator(self):
        """MA 移动平均线。"""
        tool = DataCoreIndicatorsTool()
        close = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = tool.invoke({
            "indicator": "MA",
            "close": close,
            "period": 5,
        })
        assert result["success"] is True
        assert len(result["result"]["result"]) == len(close)

    def test_rsi_indicator(self):
        """RSI 相对强弱指标。"""
        tool = DataCoreIndicatorsTool()
        close = [1.0, 2.0, 1.5, 2.5, 3.0, 2.0, 3.5, 4.0, 3.0, 4.5]
        result = tool.invoke({
            "indicator": "RSI",
            "close": close,
            "period": 6,
        })
        assert result["success"] is True

    def test_unsupported_indicator(self):
        """不支持的指标返回错误。"""
        tool = DataCoreIndicatorsTool()
        result = tool.invoke({
            "indicator": "INVALID_INDICATOR",
            "close": [1.0, 2.0, 3.0],
        })
        assert result["success"] is True
        assert result["result"]["success"] is False


# ============================================================
#  周期转换工具测试
# ============================================================

class TestPeriodTool:
    """周期转换工具测试。"""

    def test_period_resample_daily(self):
        """周期转换测试。"""
        tool = DataCorePeriodTool()
        data = [
            {"datetime": "2024-01-01 09:30:00", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100},
            {"datetime": "2024-01-01 10:30:00", "open": 11, "high": 13, "low": 10, "close": 12, "volume": 200},
            {"datetime": "2024-01-02 09:30:00", "open": 12, "high": 14, "low": 11, "close": 13, "volume": 150},
        ]
        result = tool.invoke({
            "data": data,
            "target_period": "daily",
        })
        assert result["success"] is True
        assert result["result"]["resampled_count"] == 2

    def test_period_empty_data(self):
        """空数据处理。"""
        tool = DataCorePeriodTool()
        result = tool.invoke({"data": [], "target_period": "daily"})
        assert result["success"] is True
        assert result["result"]["success"] is True
        assert result["result"]["resampled_count"] == 0

    def test_period_missing_datetime(self):
        """缺少 datetime 列报错。"""
        tool = DataCorePeriodTool()
        data = [{"open": 10, "close": 11}]
        result = tool.invoke({"data": data, "target_period": "daily"})
        assert result["success"] is True
        assert result["result"]["success"] is False

    def test_period_weekly(self):
        """周期转换 - 周线。"""
        tool = DataCorePeriodTool()
        data = [
            {"datetime": "2024-01-01", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100, "amount": 1000, "open_interest": 50},
            {"datetime": "2024-01-02", "open": 11, "high": 13, "low": 10, "close": 12, "volume": 200, "amount": 2000, "open_interest": 60},
            {"datetime": "2024-01-08", "open": 12, "high": 14, "low": 11, "close": 13, "volume": 150, "amount": 1500, "open_interest": 70},
        ]
        result = tool.invoke({
            "data": data,
            "target_period": "weekly",
        })
        assert result["success"] is True
        assert result["result"]["resampled_count"] >= 1

    def test_period_no_volume(self):
        """周期转换 - 不包含成交量。"""
        tool = DataCorePeriodTool()
        data = [
            {"datetime": "2024-01-01 09:30:00", "open": 10, "high": 12, "low": 9, "close": 11},
            {"datetime": "2024-01-01 10:30:00", "open": 11, "high": 13, "low": 10, "close": 12},
        ]
        result = tool.invoke({
            "data": data,
            "target_period": "daily",
            "include_volume": False,
        })
        assert result["success"] is True


# ============================================================
#  健康检查工具测试
# ============================================================

class TestHealthTool:
    """健康检查工具测试。"""

    def test_health_check_all(self):
        """检查所有数据源。"""
        tool = DataCoreHealthTool()
        result = tool.invoke()
        assert result["success"] is True
        assert "total" in result["result"]
        assert "results" in result["result"]

    def test_health_check_single(self):
        """检查单个数据源。"""
        tool = DataCoreHealthTool()
        result = tool.invoke({"source": "memory"})
        assert result["success"] is True

    def test_health_check_unknown(self):
        """检查未知数据源。"""
        tool = DataCoreHealthTool()
        result = tool.invoke({"source": "nonexistent"})
        assert result["success"] is True
        assert result["result"]["result"]["available"] is False


# ============================================================
#  OHLCV Tool 测试（mock 底层 provider）
# ============================================================

class TestOHLCVToolWithMock:
    """OHLCV 工具 mock 测试。"""

    def test_ohlcv_invoke_with_mock(self, mocker):
        """测试 OHLCV tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            data=[{"datetime": "2024-01-01", "open": 100, "high": 105, "low": 98, "close": 102, "volume": 1000}],
            source="test_source",
            grade=SourceGrade.PRIMARY,
            collected_at=1234567890.0,
            meta={"test": "meta"},
            errors=[],
            warnings=[],
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreOHLCVTool()
        result = tool.invoke({"symbol": "RB", "period": "daily", "limit": 100})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_ohlcv"
        assert result["result"]["symbol"] == "RB"
        assert result["result"]["data_type"] == "ohlcv"
        assert result["result"]["market"] == "futures"
        assert isinstance(result["result"]["data"], list)
        assert len(result["result"]["data"]) == 1
        assert result["result"]["source"] == "test_source"
        assert result["result"]["available"] is True
        mock_provider.get.assert_called_once()

    def test_ohlcv_invoke_with_dates(self, mocker):
        """测试 OHLCV tool 带 start_date/end_date 参数。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.OHLCV,
            market=MarketType.FUTURES,
            data=[],
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreOHLCVTool()
        result = tool.invoke({
            "symbol": "RB",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "adjust": "forward",
        })

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert "start_date" in params
        assert "end_date" in params
        assert params["adjust"] == "forward"

    def test_ohlcv_invoke_with_kwargs(self, mocker):
        """测试 OHLCV tool 通过 kwargs 传参。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="000001",
            data_type=DataType.OHLCV,
            market=MarketType.STOCK,
            data=[{"close": 10.0}],
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreOHLCVTool()
        result = tool.invoke(symbol="000001", period="weekly")

        assert result["success"] is True
        assert result["result"]["symbol"] == "000001"


# ============================================================
#  Quote Tool 测试（mock 底层 provider）
# ============================================================

class TestQuoteToolWithMock:
    """Quote 工具 mock 测试。"""

    def test_quote_invoke_with_mock(self, mocker):
        """测试 Quote tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.QUOTE,
            market=MarketType.FUTURES,
            data={"last_price": 3500, "change": 50, "change_pct": 1.45},
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreQuoteTool()
        result = tool.invoke({"symbol": "RB"})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_quote"
        assert result["result"]["data_type"] == "quote"
        assert isinstance(result["result"]["data"], dict)
        assert result["result"]["data"]["last_price"] == 3500
        mock_provider.get.assert_called_once()

    def test_quote_invoke_with_fields(self, mocker):
        """测试 Quote tool 带 fields 参数。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.QUOTE,
            market=MarketType.FUTURES,
            data={},
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreQuoteTool()
        result = tool.invoke({"symbol": "RB", "fields": ["last_price", "volume"]})

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert "fields" in params


# ============================================================
#  Macro Tool 测试（mock 底层 provider）
# ============================================================

class TestMacroToolWithMock:
    """Macro 工具 mock 测试。"""

    def test_macro_invoke_with_mock(self, mocker):
        """测试 Macro tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="GDP",
            data_type=DataType.MACRO,
            market=MarketType.FUTURES,
            data=[{"date": "2024-01-01", "value": 5.2}],
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreMacroTool()
        result = tool.invoke({"indicator": "GDP", "limit": 50})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_macro"
        assert result["result"]["data_type"] == "macro"
        assert isinstance(result["result"]["data"], list)
        mock_provider.get.assert_called_once()

    def test_macro_invoke_with_all_params(self, mocker):
        """测试 Macro tool 带所有参数。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="CPI",
            data_type=DataType.MACRO,
            market=MarketType.FUTURES,
            data=[],
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreMacroTool()
        result = tool.invoke({
            "indicator": "CPI",
            "category": "inflation",
            "frequency": "monthly",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "limit": 12,
        })

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert params["indicator"] == "CPI"
        assert params["category"] == "inflation"
        assert params["frequency"] == "monthly"
        assert params["start_date"] == "2024-01-01"
        assert params["end_date"] == "2024-12-31"
        assert params["limit"] == 12

    def test_macro_invoke_no_indicator(self, mocker):
        """测试 Macro tool 不传 indicator。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="macro",
            data_type=DataType.MACRO,
            market=MarketType.FUTURES,
            data=[],
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreMacroTool()
        result = tool.invoke()

        assert result["success"] is True
        assert result["result"]["symbol"] == "macro"


# ============================================================
#  News Tool 测试（mock 底层 provider）
# ============================================================

class TestNewsToolWithMock:
    """News 工具 mock 测试。"""

    def test_news_invoke_with_mock(self, mocker):
        """测试 News tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.NEWS,
            market=MarketType.FUTURES,
            data=[{"title": "测试新闻", "content": "内容", "datetime": "2024-01-01"}],
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreNewsTool()
        result = tool.invoke({"symbol": "RB", "limit": 20})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_news"
        assert result["result"]["data_type"] == "news"
        assert isinstance(result["result"]["data"], list)
        assert len(result["result"]["data"]) == 1
        mock_provider.get.assert_called_once()

    def test_news_invoke_with_all_params(self, mocker):
        """测试 News tool 带所有参数。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="ALL",
            data_type=DataType.NEWS,
            market=MarketType.FUTURES,
            data=[],
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreNewsTool()
        result = tool.invoke({
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "category": "宏观",
            "source": "test_source",
        })

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert params["start_date"] == "2024-01-01"
        assert params["end_date"] == "2024-01-31"
        assert params["category"] == "宏观"
        assert params["source"] == "test_source"

    def test_news_invoke_no_symbol(self, mocker):
        """测试 News tool 不传 symbol（返回全市场新闻）。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="ALL",
            data_type=DataType.NEWS,
            market=MarketType.FUTURES,
            data=[],
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreNewsTool()
        result = tool.invoke()

        assert result["success"] is True
        assert result["result"]["symbol"] == "ALL"


# ============================================================
#  Basis Tool 测试（mock 底层 provider）
# ============================================================

class TestBasisToolWithMock:
    """Basis 工具 mock 测试。"""

    def test_basis_invoke_with_mock(self, mocker):
        """测试 Basis tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_BASIS,
            market=MarketType.FUTURES,
            data={"basis": 50, "basis_ratio": 0.014},
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreBasisTool()
        result = tool.invoke({"symbol": "RB"})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_basis"
        assert result["result"]["data_type"] == "futures_basis"
        assert isinstance(result["result"]["data"], dict)
        mock_provider.get.assert_called_once()

    def test_basis_invoke_with_spot_price(self, mocker):
        """测试 Basis tool 带 spot_price 参数。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_BASIS,
            market=MarketType.FUTURES,
            data={},
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreBasisTool()
        result = tool.invoke({"symbol": "RB", "spot_price": 3400.0, "basis_type": "absolute"})

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert params["spot_price"] == 3400.0
        assert params["basis_type"] == "absolute"


# ============================================================
#  F10 Tool 测试（mock 底层 provider）
# ============================================================

class TestF10ToolWithMock:
    """F10 工具 mock 测试。"""

    def test_f10_invoke_with_mock(self, mocker):
        """测试 F10 tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.F10_REPORT,
            market=MarketType.FUTURES,
            data={
                "term_structure": {"2501": 3500, "2505": 3550},
                "spread": {"spread_01_05": 50},
                "basis": {"basis": 30},
            },
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)
        mocker.patch("datacore.api_f10.get_f10_sync", return_value=mock_payload)

        tool = DataCoreF10Tool()
        result = tool.invoke({"symbol": "RB"})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_f10"
        assert result["result"]["data_type"] == "f10_report"
        assert isinstance(result["result"]["data"], dict)
        assert "term_structure" in result["result"]["data"]

    def test_f10_invoke_with_modules(self, mocker):
        """测试 F10 tool 带 modules 参数筛选模块。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.F10_REPORT,
            market=MarketType.FUTURES,
            data={
                "term_structure": {"2501": 3500},
                "spread": {"spread_01_05": 50},
                "basis": {"basis": 30},
            },
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)
        mocker.patch("datacore.api_f10.get_f10_sync", return_value=mock_payload)

        tool = DataCoreF10Tool()
        result = tool.invoke({"symbol": "RB", "modules": ["term_structure", "basis"]})

        assert result["success"] is True
        assert "term_structure" in result["result"]["data"]
        assert "basis" in result["result"]["data"]
        assert "spread" not in result["result"]["data"]


# ============================================================
#  Sentiment Tool 测试（mock 底层 provider）
# ============================================================

class TestSentimentToolWithMock:
    """Sentiment 工具 mock 测试。"""

    def test_sentiment_invoke_with_mock(self, mocker):
        """测试 Sentiment tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.SENTIMENT,
            market=MarketType.FUTURES,
            data={"score": 0.65, "label": "positive", "detail": []},
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreSentimentTool()
        result = tool.invoke({"symbol": "RB", "limit": 30, "method": "rule"})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_sentiment"
        assert result["result"]["data_type"] == "sentiment"
        assert isinstance(result["result"]["data"], dict)
        mock_provider.get.assert_called_once()

    def test_sentiment_invoke_default_params(self, mocker):
        """测试 Sentiment tool 默认参数。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.SENTIMENT,
            market=MarketType.FUTURES,
            data={},
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreSentimentTool()
        result = tool.invoke({"symbol": "RB"})

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert params["limit"] == 50
        assert params["method"] == "auto"


# ============================================================
#  Fundamental Tool 测试（mock 底层 provider）
# ============================================================

class TestFundamentalToolWithMock:
    """Fundamental 工具 mock 测试。"""

    def test_fundamental_invoke_with_mock(self, mocker):
        """测试 Fundamental tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUNDAMENTAL,
            market=MarketType.FUTURES,
            data={"inventory": 100000, "production": 5000},
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreFundamentalTool()
        result = tool.invoke({"symbol": "RB", "report_type": "indicator", "period": "quarterly", "limit": 10})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_fundamental"
        assert result["result"]["data_type"] == "fundamental"
        assert isinstance(result["result"]["data"], dict)
        mock_provider.get.assert_called_once()

    def test_fundamental_invoke_params(self, mocker):
        """测试 Fundamental tool 参数正确传递。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUNDAMENTAL,
            market=MarketType.FUTURES,
            data={},
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreFundamentalTool()
        result = tool.invoke({
            "symbol": "RB",
            "report_type": "balance",
            "period": "annual",
            "limit": 5,
        })

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert params["report_type"] == "balance"
        assert params["period"] == "annual"
        assert params["limit"] == 5


# ============================================================
#  MarketRegime Tool 测试（mock 底层 provider）
# ============================================================

class TestMarketRegimeToolWithMock:
    """MarketRegime 工具 mock 测试。"""

    def test_market_regime_invoke_with_mock(self, mocker):
        """测试 MarketRegime tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.MARKET_STATE,
            market=MarketType.FUTURES,
            data={"regime": "trending_up", "confidence": 0.75},
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreMarketRegimeTool()
        result = tool.invoke({"symbol": "RB", "period": "daily", "lookback": 60, "method": "auto"})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_market_regime"
        assert result["result"]["data_type"] == "market_state"
        assert isinstance(result["result"]["data"], dict)
        mock_provider.get.assert_called_once()

    def test_market_regime_invoke_default_params(self, mocker):
        """测试 MarketRegime tool 默认参数。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.MARKET_STATE,
            market=MarketType.FUTURES,
            data={},
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreMarketRegimeTool()
        result = tool.invoke({"symbol": "RB"})

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert params["period"] == "daily"
        assert params["lookback"] == 60
        assert params["method"] == "auto"


# ============================================================
#  TermStructure Tool 测试（mock 底层 provider）
# ============================================================

class TestTermStructureToolWithMock:
    """TermStructure 工具 mock 测试。"""

    def test_term_structure_invoke_with_mock(self, mocker):
        """测试 TermStructure tool invoke 调用底层 provider。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="RB",
            data_type=DataType.FUTURES_TERM_STRUCTURE,
            market=MarketType.FUTURES,
            data={"2501": 3500, "2505": 3550, "2510": 3600},
            source="test_source",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreTermStructureTool()
        result = tool.invoke({"symbol": "RB", "price_type": "close", "include_volume": True})

        assert result["success"] is True
        assert result["tool_name"] == "datacore_term_structure"
        assert result["result"]["data_type"] == "futures_term_structure"
        assert isinstance(result["result"]["data"], dict)
        mock_provider.get.assert_called_once()

    def test_term_structure_invoke_params(self, mocker):
        """测试 TermStructure tool 参数正确传递。"""
        from datacore.models.enums import DataType, MarketType, SourceGrade
        from datacore.models.payload import DataPayload

        mock_payload = DataPayload(
            symbol="CU",
            data_type=DataType.FUTURES_TERM_STRUCTURE,
            market=MarketType.FUTURES,
            data={},
            source="test",
            grade=SourceGrade.PRIMARY,
        )

        mock_provider = mocker.MagicMock()
        mock_provider.get.return_value = mock_payload
        mocker.patch("datacore.api.UnifiedDataProvider", return_value=mock_provider)

        tool = DataCoreTermStructureTool()
        result = tool.invoke({
            "symbol": "CU",
            "price_type": "settle",
            "include_volume": False,
        })

        assert result["success"] is True
        call_args = mock_provider.get.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
        assert params["price_type"] == "settle"
        assert params["include_volume"] is False


# ============================================================
#  Adjustment Tool 测试
# ============================================================

class TestAdjustmentTool:
    """Adjustment 工具测试。"""

    def test_adjustment_forward(self):
        """前复权调整测试。"""
        tool = DataCoreAdjustmentTool()
        data = [
            {"datetime": "2025-01-10", "open": 100, "high": 105, "low": 98, "close": 102, "volume": 1000},
            {"datetime": "2025-01-15", "open": 102, "high": 108, "low": 100, "close": 105, "volume": 1200},
            {"datetime": "2025-01-20", "open": 103, "high": 110, "low": 101, "close": 108, "volume": 1500},
        ]
        dividend_data = [
            {"ex_date": "2025-01-15", "dividend": 2.0},
        ]
        result = tool.invoke({
            "data": data,
            "adjust_type": "forward",
            "dividend_data": dividend_data,
        })

        assert result["success"] is True
        assert result["result"]["success"] is True
        assert result["result"]["adjust_type"] == "forward"
        assert result["result"]["original_count"] == 3
        assert result["result"]["adjusted_count"] == 3
        assert len(result["result"]["data"]) == 3

    def test_adjustment_backward(self):
        """后复权调整测试。"""
        tool = DataCoreAdjustmentTool()
        data = [
            {"datetime": "2025-01-10", "open": 100, "high": 105, "low": 98, "close": 102, "volume": 1000},
            {"datetime": "2025-01-20", "open": 103, "high": 110, "low": 101, "close": 108, "volume": 1500},
        ]
        dividend_data = [
            {"ex_date": "2025-01-15", "dividend": 2.0},
        ]
        result = tool.invoke({
            "data": data,
            "adjust_type": "backward",
            "dividend_data": dividend_data,
        })

        assert result["success"] is True
        assert result["result"]["success"] is True
        assert result["result"]["adjust_type"] == "backward"

    def test_adjustment_rollover(self):
        """期货换月调整测试。"""
        tool = DataCoreAdjustmentTool()
        data = [
            {"datetime": "2024-01-01", "open": 100, "high": 105, "low": 98, "close": 102, "volume": 1000},
            {"datetime": "2024-01-02", "open": 102, "high": 108, "low": 100, "close": 105, "volume": 1200},
        ]
        result = tool.invoke({
            "data": data,
            "adjust_type": "rollover",
            "rollover_method": "volume",
        })

        assert result["success"] is True
        assert result["result"]["success"] is True
        assert result["result"]["adjust_type"] == "rollover"

    def test_adjustment_invalid_type(self):
        """无效调整类型测试。"""
        tool = DataCoreAdjustmentTool()
        data = [{"datetime": "2024-01-01", "close": 100}]
        result = tool.invoke({
            "data": data,
            "adjust_type": "invalid_type",
        })

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "error" in result["result"]

    def test_adjustment_no_dividend(self):
        """无分红数据时前复权测试。"""
        tool = DataCoreAdjustmentTool()
        data = [
            {"datetime": "2025-01-10", "open": 100, "high": 105, "low": 98, "close": 102},
        ]
        result = tool.invoke({
            "data": data,
            "adjust_type": "forward",
        })

        assert result["success"] is True
        assert result["result"]["success"] is True

    def test_adjustment_empty_data(self):
        """空数据调整测试。"""
        tool = DataCoreAdjustmentTool()
        result = tool.invoke({
            "data": [],
            "adjust_type": "forward",
        })

        assert result["success"] is True
        assert result["result"]["success"] is True
        assert result["result"]["adjusted_count"] == 0
