"""Tests for datacore.operations — 运维工具模块测试。"""

from __future__ import annotations

import os
import tempfile
import time

import pytest
import pandas as pd

from datacore.operations.crawl_retry import (
    retry_with_backoff,
    exponential_backoff,
    RetryConfig,
    retry_call,
)
from datacore.operations.error_log import (
    log_error_json,
    create_error_record,
    ErrorLogger,
    ErrorRecord,
)
from datacore.operations.config_tools import (
    load_yaml_config,
    get_env_var,
    load_config,
    ConfigLoader,
)


# ============================================================
#  crawl_retry 测试
# ============================================================

class TestCrawlRetry:
    """指数退避重试测试。"""

    def test_exponential_backoff_basic(self):
        """基础指数退避计算。"""
        delay = exponential_backoff(0, base_delay=1.0, jitter=False)
        assert delay == 1.0

    def test_exponential_backoff_increase(self):
        """退避时间递增。"""
        delay0 = exponential_backoff(0, base_delay=1.0, jitter=False)
        delay1 = exponential_backoff(1, base_delay=1.0, jitter=False)
        delay2 = exponential_backoff(2, base_delay=1.0, jitter=False)
        assert delay0 < delay1 < delay2

    def test_exponential_backoff_max(self):
        """最大延迟限制。"""
        delay = exponential_backoff(10, base_delay=1.0, max_delay=5.0, jitter=False)
        assert delay <= 5.0

    def test_retry_decorator_success(self):
        """重试装饰器 - 成功的情况。"""
        @retry_with_backoff(max_retries=2, base_delay=0.001)
        def success_func():
            return "ok"

        result = success_func()
        assert result == "ok"

    def test_retry_decorator_fail(self):
        """重试装饰器 - 最终失败。"""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.001)
        def fail_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("test error")

        with pytest.raises(ValueError):
            fail_func()
        assert call_count == 3  # 1 次初始 + 2 次重试

    def test_retry_config_default(self):
        """RetryConfig 默认值。"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.jitter is True

    def test_retry_call_success(self):
        """命令式重试调用 - 成功。"""
        def func(x):
            return x * 2

        result = retry_call(
            func,
            5,
            config=RetryConfig(max_retries=2, base_delay=0.001),
        )
        assert result == 10


# ============================================================
#  error_log 测试
# ============================================================

class TestErrorLog:
    """结构化错误日志测试。"""

    def test_create_error_record(self):
        """创建错误记录。"""
        try:
            raise ValueError("test error")
        except ValueError as e:
            record = create_error_record(e, module="test", function="func")

        assert record.error_type == "ValueError"
        assert record.error_message == "test error"
        assert record.module == "test"
        assert record.function == "func"
        assert record.severity == "ERROR"

    def test_error_record_to_dict(self):
        """错误记录转字典。"""
        try:
            raise RuntimeError("test")
        except RuntimeError as e:
            record = create_error_record(e)

        d = record.to_dict()
        assert isinstance(d, dict)
        assert d["error_type"] == "RuntimeError"
        assert "timestamp" in d

    def test_error_record_to_json(self):
        """错误记录转 JSON。"""
        try:
            raise RuntimeError("test")
        except RuntimeError as e:
            record = create_error_record(e)

        json_str = record.to_json()
        assert isinstance(json_str, str)
        assert "RuntimeError" in json_str

    def test_log_error_json(self):
        """记录 JSON 错误日志。"""
        try:
            raise ValueError("test log")
        except ValueError as e:
            log_str = log_error_json(e, module="test")

        assert isinstance(log_str, str)
        assert "ValueError" in log_str
        assert "test log" in log_str

    def test_error_logger_context(self):
        """ErrorLogger 上下文。"""
        logger = ErrorLogger(name="test")
        logger.add_context(request_id="123", user="test_user")
        assert logger._context["request_id"] == "123"
        logger.clear_context()
        assert len(logger._context) == 0


# ============================================================
#  config_tools 测试
# ============================================================

class TestConfigTools:
    """配置工具测试。"""

    def test_get_env_var_exists(self):
        """读取存在的环境变量。"""
        os.environ["DATACORE_TEST_VAR"] = "test_value"
        try:
            value = get_env_var("TEST_VAR")
            assert value == "test_value"
        finally:
            del os.environ["DATACORE_TEST_VAR"]

    def test_get_env_var_default(self):
        """读取不存在的环境变量，返回默认值。"""
        value = get_env_var("NONEXISTENT_VAR_12345", "default_val")
        assert value == "default_val"

    def test_load_yaml_config_not_exists(self):
        """加载不存在的 YAML 文件。"""
        result = load_yaml_config("/nonexistent/path/config.yaml")
        assert result == {}

    def test_load_yaml_config_valid(self):
        """加载有效的 YAML 文件。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("key1: value1\nkey2: 123\nnested:\n  foo: bar\n")
            path = f.name

        try:
            config = load_yaml_config(path)
            assert config["key1"] == "value1"
            assert config["key2"] == 123
            assert config["nested"]["foo"] == "bar"
        finally:
            os.unlink(path)

    def test_config_loader_get(self):
        """ConfigLoader 获取配置。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("database:\n  host: localhost\n  port: 5432\n")
            path = f.name

        try:
            loader = ConfigLoader(yaml_path=path)
            assert loader.get("database.host") == "localhost"
            assert loader.get("database.port") == 5432
            assert loader.get("nonexistent", "default") == "default"
        finally:
            os.unlink(path)

    def test_config_loader_set(self):
        """ConfigLoader 设置配置。"""
        loader = ConfigLoader()
        loader.set("new.key", "new_value")
        assert loader.get("new.key") == "new_value"

    def test_config_loader_contains(self):
        """ConfigLoader __contains__。"""
        loader = ConfigLoader()
        loader.set("test.key", "value")
        assert "test.key" in loader
        assert "nonexistent" not in loader
