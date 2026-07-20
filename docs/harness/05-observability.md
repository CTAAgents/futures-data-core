# Data-Core Observability

Version: v2.0.0 | Updated: 2026-07-20

## Data Quality Grades

每个 `DataPayload` 都携带 `grade` 字段：

| Grade | 说明 | 使用建议 |
|:------|:-----|:---------|
| `PRIMARY` | 官方数据源/LLM打分 | 可用于交易决策 |
| `DAILY` | 第三方数据/规则基线 | 可用于因子计算 |
| `CACHED` | 缓存数据 | 可用于分析，需标注 |
| `STALE` | 过期数据 | 低权重使用 |
| `UNAVAILABLE` | 所有源不可用 | 因子降级或跳过 |

## 数据加工层可观测性（v0.3.0 新增）

### 情绪数据元数据
每个 `SentimentItem` 携带完整的可观测信息：

| 字段 | 说明 |
|:-----|:-----|
| `score` | 情绪分数 (-1.0 ~ +1.0) |
| `confidence` | 置信度 (0.0 ~ 1.0) |
| `source` | 打分来源 (llm / rule / rule_fallback) |
| `tags` | 新闻分类标签 |
| `published_at` | 新闻发布时间 |
| `collected_at` | 打分时间 |

### 市场制度元数据
`MarketStateData` 携带检测特征：

| 字段 | 说明 |
|:-----|:-----|
| `regime` | 市场制度 (bull/bear/sideways/unknown) |
| `confidence` | 检测置信度 |
| `trend_strength` | 趋势强度 |
| `volatility` | 波动率（年化） |
| `volume_trend` | 成交量趋势 |
| `features` | 原始特征字典 |

## 健康检查接口（v0.4.0 新增）

`UnifiedDataProvider.get_health()` 返回各数据源实时可用状态：

| 返回字段 | 类型 | 说明 |
|:---------|:-----|:-----|
| `status` | str | 整体状态：healthy / degraded / unavailable |
| `sources` | dict | 各数据源状态详情 |
| `sources.{name}.available` | bool | 该源是否可用 |
| `sources.{name}.latency_ms` | float | 健康检查延迟（毫秒） |
| `sources.{name}.grade` | str | 数据质量等级 |
| `sources.{name}.last_error` | str | 最近错误信息（如有） |
| `sources.{name}.breaker_state` | str | 熔断器状态（CLOSED/OPEN/HALF_OPEN） |
| `timestamp` | str | 检查时间戳 |

健康检查覆盖的数据源列表：
- `tdx_local` — TQ-Local 通达信本地服务
- `eastmoney` — 东方财富 HTTP
- `tencent` — 腾讯财经
- `cls` — 财联社新闻
- `wallstreet` — 华尔街见闻
- `llm` — LLM 情绪打分服务
- `guosen` — 国信证券（v0.5.0 新增）
- `national_bureau` — 国家统计局（v0.5.0 新增）
- `pboc` — 央行（v0.5.0 新增）
- `exchange_api` — 交易所官方（v0.5.0 新增）
- `shengyishe` — 生意社（v0.5.0 新增）
- `memory_cache` — 内存缓存状态（v0.5.0 新增）
- `duckdb_cache` — DuckDB 缓存状态（v0.5.0 新增）
- `websocket` — WebSocket 连接状态（v1.0.0 新增）
- `alert_engine` — 告警引擎状态（v1.0.0 新增）
- `data_freshness` — 数据新鲜度评估器（v1.1.0 新增）
- `f10_report` — F10 综合报告（v1.1.0 新增）
- `async_provider` — 异步接口状态（v1.1.0 新增）
- `indicators` — 技术指标模块（v1.2.0 新增）
- `qmt` — QMT 迅投资讯源（v1.2.0 新增）
- `web_fallback` — 网页备用数据源（v1.2.0 新增）
- `tqsdk` — TqSdk 兜底数据源（v1.2.0 新增）
- `base_tools` — BaseTool 接口层（v1.3.0 新增）
- `adjustment` — 复权/换月引擎（v1.3.0 新增）
- `resampler` — 周期转换引擎（v1.3.0 新增）
- `consumer_issues` — 消费者反馈通道（v1.3.0 新增）
- `cleaning` — 数据清洗模块（v1.3.0 新增）
- `validation` — 数据校验模块（v1.3.0 新增）
- `collectors` — 采集模块骨架（v1.3.0 新增）
- `operations` — 运维工具模块（v1.3.0 新增）
- `fdc_compat` — FDT 兼容层（v2.0.0 新增）
- `qlib_adapter` — Qlib/RD-Agent 适配器（v2.0.0 新增）

## 缓存层可观测性（v0.5.0 新增）

### 缓存命中流
```
请求 → MemoryCache 检查 → DuckDB 检查 → HTTP 源
        ↓ 命中           ↓ 命中
    返回 CACHED      返回 CACHED
```

### 缓存状态字段
每个 DataPayload 的 `source` 字段标识数据来源：
- `memory_cache`: 来自 L1 内存缓存
- `duckdb_cache`: 来自 L2 DuckDB 持久化缓存
- `tdx_lc`, `eastmoney`, etc.: 来自 HTTP 实时数据源

### 健康检查中的缓存状态
`get_health()` 新增缓存层状态：
- `memory_cache.available`: 始终 true
- `memory_cache.grade`: "active"
- `duckdb_cache.available`: DuckDB 是否可用
- `duckdb_cache.grade`: "active" / "unavailable"

## WebSocket 可观测性（v1.0.0 新增）

### WebSocket 状态
| 指标 | 说明 |
|:-----|:-----|
| `ws_connected` | 连接状态 (bool) |
| `ws_reconnect_count` | 累计重连次数 |
| `ws_last_heartbeat` | 最后一次心跳时间 |
| `ws_subscribed_symbols` | 当前订阅品种数 |

### 健康检查中的 WebSocket 状态
`get_health()` 新增：
- `websocket.available`: WebSocket 是否连接
- `websocket.grade`: "active" / "disconnected"
- `websocket.reconnect_count`: 重连次数

## 告警系统可观测性（v1.0.0 新增）

### 告警指标
| 指标名称 | 类型 | 说明 |
|:---------|:-----|:-----|
| `alerts_triggered_total` | Counter | 告警触发总数 |
| `alerts_by_rule` | Counter | 按规则分类的告警数（price_breakout/volatility_anomaly/data_stale/breaker_trip） |
| `alerts_by_channel` | Counter | 按渠道分类的告警数（webhook/file/log） |
| `alerts_channel_fallback` | Counter | 渠道降级次数 |
| `alerts_success_rate` | Gauge | 告警通知成功率 |

### 健康检查中的告警状态
`get_health()` 新增：
- `alert_engine.available`: 告警引擎是否运行
- `alert_engine.grade`: "active" / "degraded"

## 技术指标可观测性（v1.2.0 新增）

### 指标计算元数据
每个指标计算结果携带完整的可观测信息：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `indicator_name` | str | 指标名称 |
| `computed_at` | datetime | 计算时间戳 |
| `implementation` | str | 实际使用的实现层（tdx_compat / numpy_core / talib_fallback） |
| `period` | int | 计算周期 |
| `input_length` | int | 输入数据长度 |
| `output_length` | int | 输出结果长度 |
| `compute_time_ms` | float | 计算耗时（毫秒） |

### 三层路由统计
| 指标 | 说明 |
|:-----|:-----|
| `indicators_tdx_compat_used` | TDX 对齐层使用次数 |
| `indicators_numpy_core_used` | numpy 核心层使用次数 |
| `indicators_talib_fallback_used` | TA-Lib 兜底层使用次数 |
| `indicators_fallback_total` | 降级触发总次数 |

### 健康检查中的指标模块状态
`get_health()` 新增：
- `indicators.available`: 指标模块是否可用（始终 true，纯计算）
- `indicators.tdx_compat_available`: TDX 对齐层是否可用
- `indicators.talib_available`: TA-Lib 兜底层是否可用
- `indicators.total_computed`: 累计计算次数
- `indicators.avg_compute_time_ms`: 平均计算耗时

### 趋势成熟度评估元数据
`assess_trend_maturity()` 返回结果携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `trend_direction` | str | 趋势方向（up / down / sideways） |
| `maturity_level` | int | 成熟度等级（1-5） |
| `confidence` | float | 评估置信度（0.0 ~ 1.0） |
| `duration_bars` | int | 趋势持续 K 线数 |
| `strength_score` | float | 趋势强度得分 |
| `features` | dict | 原始特征字典 |

## BaseTool 接口层可观测性（v1.3.0 新增）

### Tool 调用元数据
每个 Tool 调用结果携带完整的可观测信息：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `tool_name` | str | Tool 名称 |
| `invoked_at` | datetime | 调用时间戳 |
| `execution_time_ms` | float | 执行耗时（毫秒） |
| `success` | bool | 是否成功 |
| `error_message` | str | 错误信息（如有） |
| `input_params` | dict | 输入参数摘要 |
| `output_rows` | int | 输出数据行数 |

### all_tools 自动发现统计
| 指标 | 说明 |
|:-----|:-----|
| `tools_total_count` | 已注册 Tool 总数 |
| `tools_by_category` | 按分类统计 Tool 数量 |
| `tools_discovered` | 自动发现的 Tool 数量 |
| `tools_failed_load` | 加载失败的 Tool 数量 |

### 健康检查中的 BaseTool 状态
`get_health()` 新增：
- `base_tools.available`: BaseTool 接口层是否可用
- `base_tools.total_count`: 已注册 Tool 总数
- `base_tools.success_rate`: Tool 调用成功率
- `base_tools.avg_execution_time_ms`: 平均执行耗时

## 复权/换月可观测性（v1.3.0 新增）

### 复权元数据
每次复权/换月结果携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `adjustment_type` | str | 调整类型（front/back/none） |
| `adjustment_method` | str | 换月方式（volume/interest/fixed_day） |
| `rollover_count` | int | 换月次数 |
| `spread_adjusted` | bool | 是否已做价差调整 |
| `original_length` | int | 原始数据长度 |
| `adjusted_length` | int | 调整后数据长度 |

### 健康检查中的复权状态
`get_health()` 新增：
- `adjustment.available`: 复权/换月引擎是否可用（始终 true，纯计算）
- `adjustment.total_adjustments`: 累计调整次数
- `adjustment.stock_adjustments`: 股票复权次数
- `adjustment.futures_rollovers`: 期货换月次数

## 周期转换可观测性（v1.3.0 新增）

### 周期转换元数据
每次 resample 结果携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `source_period` | str | 源周期（1m/5m/15m/...） |
| `target_period` | str | 目标周期 |
| `auto_detected` | bool | 是否 auto 自动检测 |
| `source_bars` | int | 源数据 K 线数 |
| `target_bars` | int | 目标数据 K 线数 |
| `resample_time_ms` | float | 转换耗时（毫秒） |

### 健康检查中的周期转换状态
`get_health()` 新增：
- `resampler.available`: 周期转换引擎是否可用（始终 true，纯计算）
- `resampler.total_resamples`: 累计转换次数
- `resampler.auto_used_count`: auto 模式使用次数
- `resampler.avg_resample_time_ms`: 平均转换耗时

## 消费者反馈可观测性（v1.3.0 新增）

### Issue 数据结构
每个 DataIssue 携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `issue_id` | str | 问题唯一标识 |
| `issue_type` | IssueType | 问题类型枚举 |
| `severity` | str | 严重级别（LOW/MEDIUM/HIGH/CRITICAL） |
| `symbol` | str | 相关品种代码 |
| `data_type` | str | 数据类型 |
| `source` | str | 问题来源 |
| `description` | str | 问题描述 |
| `reported_at` | datetime | 上报时间 |
| `degrade_action` | str | 触发的降级动作 |
| `resolved` | bool | 是否已解决 |

### 消费者反馈指标
| 指标 | 类型 | 说明 |
|:-----|:-----|:-----|
| `issues_reported_total` | Counter | 问题上报总数 |
| `issues_by_severity` | Counter | 按严重级别分类的问题数 |
| `issues_by_type` | Counter | 按类型分类的问题数 |
| `issues_auto_degraded` | Counter | 自动降级触发次数 |
| `issues_resolved_total` | Counter | 已解决问题数 |
| `active_issues_count` | Gauge | 当前活跃问题数 |

### 健康检查中的消费者反馈状态
`get_health()` 新增：
- `consumer_issues.available`: 消费者反馈通道是否启用
- `consumer_issues.active_count`: 当前活跃问题数
- `consumer_issues.total_reported`: 累计上报问题数
- `consumer_issues.auto_degrade_count`: 自动降级触发次数
- `consumer_issues.most_common_type`: 最常见问题类型

## 数据清洗可观测性（v1.3.0 新增）

### 清洗结果元数据
每次清洗结果在 metadata.cleaning 中携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `pipeline_used` | str | 使用的清洗链路（full/basic/passthrough） |
| `unit_unified` | bool | 是否已做单位统一 |
| `date_aligned` | bool | 是否已做日期对齐 |
| `duplicates_removed` | int | 移除的重复数据条数 |
| `outliers_removed` | int | 过滤的异常值条数 |
| `cleaning_time_ms` | float | 清洗耗时（毫秒） |

### 健康检查中的清洗状态
`get_health()` 新增：
- `cleaning.available`: 数据清洗模块是否可用
- `cleaning.total_cleaned`: 累计清洗次数
- `cleaning.duplicates_removed_total`: 累计去重数量
- `cleaning.outliers_removed_total`: 累计异常值过滤数量

## 数据校验可观测性（v1.3.0 新增）

### 校验结果元数据
每次校验结果在 metadata.validation 中携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `validation_level` | str | 校验级别（full/basic/mark_only） |
| `cross_source_passed` | bool | 跨源校验是否通过 |
| `cross_source_deviation` | float | 跨源偏差率 |
| `missing_detected` | bool | 是否检测到缺失值 |
| `missing_ratio` | float | 缺失值比例 |
| `cal_math_passed` | bool | 计算校验是否通过 |
| `weight_score` | float | 综合权重评分 |

### 健康检查中的校验状态
`get_health()` 新增：
- `validation.available`: 数据校验模块是否可用
- `validation.total_validated`: 累计校验次数
- `validation.pass_rate`: 校验通过率
- `validation.avg_weight_score`: 平均权重评分

## FDT 兼容层可观测性（v2.0.0 新增）

### FDT 兼容层元数据
每次 FDC 兼容调用结果携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `compat_mode` | str | 兼容模式（full_compat/signature_only/passthrough） |
| `output_format` | str | 输出格式（native/dataframe/series） |
| `field_style` | str | 字段命名风格（datacore/fdc） |
| `error_compat` | bool | 是否启用错误码兼容 |
| `compat_time_ms` | float | 兼容层转换耗时（毫秒） |

### 健康检查中的 FDT 兼容层状态
`get_health()` 新增：
- `fdc_compat.available`: FDT 兼容层是否可用
- `fdc_compat.total_calls`: 累计兼容调用次数
- `fdc_compat.full_compat_count`: 完整兼容模式次数
- `fdc_compat.degradation_count`: 降级触发次数

## Qlib/RD-Agent 适配器可观测性（v2.0.0 新增）

### Qlib 适配器元数据
每次 Qlib 适配器调用结果携带：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `adapter_mode` | str | 适配器模式（full_compat/basic_provider/passthrough） |
| `frequency` | str | 数据频率（daily/1m/5m/...） |
| `expression_used` | bool | 是否使用了表达式引擎 |
| `data_converted` | bool | 是否进行了格式转换 |
| `conversion_time_ms` | float | 格式转换耗时（毫秒） |

### 健康检查中的 Qlib 适配器状态
`get_health()` 新增：
- `qlib_adapter.available`: Qlib 适配器是否可用
- `qlib_adapter.total_calls`: 累计适配器调用次数
- `qlib_adapter.expression_used_count`: 表达式引擎使用次数
- `qlib_adapter.avg_conversion_time_ms`: 平均格式转换耗时

## 数据新鲜度可观测性（v1.1.0 新增）

### FreshnessStatus 状态
| 状态 | 说明 | 阈值（默认） |
|:-----|:-----|:------------|
| `FRESH` | 数据新鲜，可正常使用 | < 300s |
| `STALE` | 数据过期，低权重使用 | 300s ~ 3600s |
| `EXPIRED` | 数据严重过期，建议刷新 | > 3600s |

### 新鲜度元数据
每个 DataPayload.metadata 携带新鲜度信息：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `freshness.status` | FreshnessStatus | 新鲜度状态（FRESH/STALE/EXPIRED） |
| `freshness.data_age_seconds` | float | 数据年龄（秒） |
| `freshness.assessed_at` | datetime | 评估时间戳 |
| `freshness.data_timestamp` | datetime | 数据原始时间戳 |

### 健康检查中的新鲜度状态
`get_health()` 新增：
- `freshness.available`: 新鲜度评估器是否启用
- `freshness.stale_count`: 当前 STALE 状态数据计数
- `freshness.expired_count`: 当前 EXPIRED 状态数据计数
- `freshness.fresh_ratio`: 新鲜数据占比（0.0 ~ 1.0）

## 指标收集（v0.4.0 已实现，v1.0.0 扩展）

已关闭差距: G05 [P2]

MetricsCollector 统计以下指标：

| 指标名称 | 类型 | 说明 |
|:---------|:-----|:-----|
| `calls_total` | Counter | 总调用次数（按数据源/方法维度） |
| `calls_success` | Counter | 成功调用次数 |
| `calls_failed` | Counter | 失败调用次数 |
| `success_rate` | Gauge | 成功率百分比（实时） |
| `latency_p50` | Gauge | 响应延迟 P50（毫秒） |
| `latency_p95` | Gauge | 响应延迟 P95（毫秒） |
| `latency_p99` | Gauge | 响应延迟 P99（毫秒） |
| `cache_hit_rate` | Gauge | 缓存命中率 |
| `cache_hits` | Counter | 缓存命中次数 |
| `cache_misses` | Counter | 缓存未命中次数 |
| `breaker_open_count` | Counter | 熔断器开启次数 |
| `breaker_half_open_count` | Counter | 熔断器半开探测次数 |
| `ws_reconnect_count` | Counter | WebSocket 重连次数（v1.0.0 新增） |
| `alerts_triggered_total` | Counter | 告警触发总数（v1.0.0 新增） |
| `freshness_stale_total` | Counter | 数据新鲜度 STALE 触发次数（v1.1.0 新增） |
| `freshness_expired_total` | Counter | 数据新鲜度 EXPIRED 触发次数（v1.1.0 新增） |
| `freshness_fresh_ratio` | Gauge | 新鲜数据占比（v1.1.0 新增） |
| `indicators_computed_total` | Counter | 技术指标计算总次数（v1.2.0 新增） |
| `indicators_tdx_compat_used` | Counter | TDX 对齐层使用次数（v1.2.0 新增） |
| `indicators_numpy_core_used` | Counter | numpy 核心层使用次数（v1.2.0 新增） |
| `indicators_talib_fallback_used` | Counter | TA-Lib 兜底层使用次数（v1.2.0 新增） |
| `indicators_avg_compute_time_ms` | Gauge | 平均计算耗时（毫秒）（v1.2.0 新增） |
| `indicators_trend_maturity_total` | Counter | 趋势成熟度评估次数（v1.2.0 新增） |
| `tools_calls_total` | Counter | BaseTool 调用总次数（v1.3.0 新增） |
| `tools_success_rate` | Gauge | BaseTool 调用成功率（v1.3.0 新增） |
| `tools_avg_execution_time_ms` | Gauge | BaseTool 平均执行耗时（v1.3.0 新增） |
| `adjustment_total_count` | Counter | 复权/换月总次数（v1.3.0 新增） |
| `adjustment_stock_count` | Counter | 股票复权次数（v1.3.0 新增） |
| `adjustment_futures_rollover_count` | Counter | 期货换月次数（v1.3.0 新增） |
| `resampler_total_count` | Counter | 周期转换总次数（v1.3.0 新增） |
| `resampler_auto_used_count` | Counter | auto 模式使用次数（v1.3.0 新增） |
| `resampler_avg_time_ms` | Gauge | 周期转换平均耗时（v1.3.0 新增） |
| `issues_reported_total` | Counter | 问题上报总数（v1.3.0 新增） |
| `issues_auto_degraded` | Counter | 自动降级触发次数（v1.3.0 新增） |
| `active_issues_count` | Gauge | 当前活跃问题数（v1.3.0 新增） |
| `cleaning_total_count` | Counter | 数据清洗总次数（v1.3.0 新增） |
| `cleaning_duplicates_removed` | Counter | 累计去重数量（v1.3.0 新增） |
| `cleaning_outliers_removed` | Counter | 累计异常值过滤数量（v1.3.0 新增） |
| `validation_total_count` | Counter | 数据校验总次数（v1.3.0 新增） |
| `validation_pass_rate` | Gauge | 数据校验通过率（v1.3.0 新增） |
| `validation_avg_weight_score` | Gauge | 平均权重评分（v1.3.0 新增） |
| `fdc_compat_total_calls` | Counter | FDT 兼容层总调用次数（v2.0.0 新增） |
| `fdc_compat_full_compat_count` | Counter | FDT 完整兼容模式次数（v2.0.0 新增） |
| `fdc_compat_degradation_count` | Counter | FDT 兼容层降级次数（v2.0.0 新增） |
| `fdc_compat_avg_time_ms` | Gauge | FDT 兼容层平均耗时（毫秒）（v2.0.0 新增） |
| `qlib_adapter_total_calls` | Counter | Qlib 适配器总调用次数（v2.0.0 新增） |
| `qlib_adapter_expression_used_count` | Counter | Qlib 表达式引擎使用次数（v2.0.0 新增） |
| `qlib_adapter_degradation_count` | Counter | Qlib 适配器降级次数（v2.0.0 新增） |
| `qlib_adapter_avg_conversion_time_ms` | Gauge | Qlib 平均格式转换耗时（毫秒）（v2.0.0 新增） |

> 指标数据可通过 `MetricsCollector.report()` 获取完整快照。

## 安全审计可观测性（v1.0.0 新增）

已通过的安全审计检查（docs/SECURITY_CHECKLIST.md）：
| 检查项 | 说明 | 状态 |
|:-------|:-----|:-----|
| 认证安全 | API Key 通过环境变量传输，不硬编码 | ✅ |
| 数据加密 | DuckDB 存储加密，敏感字段脱敏 | ✅ |
| 注入防护 | SQL 参数化查询，HTTP 输入校验 | ✅ |
| 配置安全 | 敏感配置仅环境变量，默认值安全 | ✅ |
| 依赖安全 | 依赖版本锁定，无已知漏洞 | ✅ |
| 日志安全 | 不记录敏感信息（API Key/密码） | ✅ |
| 通信安全 | HTTPS/WS 加密传输 | ✅ |
