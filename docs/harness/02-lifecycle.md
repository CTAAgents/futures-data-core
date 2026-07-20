# Data-Core Lifecycle

Version: v2.0.0 | Updated: 2026-07-20

## Module Phases

| Phase | Version | Module | Status | Description |
|:------|:--------|:-------|:-------|:------------|
| Phase 1 | v0.1.0 | models/registry/store | COMPLETED | 数据模型、品种注册、存储层基础 |
| Phase 2 | v0.2.0 | futures providers | COMPLETED | 期货多源数据源 |
| Phase 3 | v0.2.0 | equity providers | COMPLETED | 股票多源数据源 |
| Phase 4 | v0.3.0 | processing layer | COMPLETED | 数据加工层：情绪管线 + 市场制度 |
| Phase 5 | v0.5.0 | data source expansion | COMPLETED | 数据源完善版（宏观/期货/A股扩展 + DuckDB缓存） |
| Phase 6 | v0.6.0 | LLM & intelligent processing | COMPLETED | LLM 情绪打分端到端验证 + 基本面LLM加工 |
| Phase 7 | v1.0.0 | production readiness | COMPLETED | WebSocket 实时行情 + 告警系统 + 性能基准 + 安全审计 |
| Phase 8 | v1.1.0 | unified data hub phase 1 | COMPLETED | 异步双接口 + F10 综合报告 + core 共享基础设施 |
| Phase 9 | v1.2.0 | FDC module absorption | COMPLETED | indicators 技术指标模块 + 3 个期货新数据源 + 7 源降级链 |
| Phase 10 | v1.3.0 | BaseTool & data toolchain | COMPLETED | BaseTool 接口层 + 复权换月 + 周期转换 + 消费者反馈 + 数据清洗 + 数据校验 + 采集骨架 + 运维工具 |
| Phase 11 | v2.0.0 | FDT compatibility layer | COMPLETED | FDC 兼容层（fdc_compat.py），提供 FDC 兼容的函数签名 |
| Phase 12 | v2.0.0 | Qlib/RD-Agent adapter | COMPLETED | Qlib/RD-Agent 适配器（qlib_adapter/provider.py） |
| Phase 0 (Final) | v2.0.0 | Final acceptance | COMPLETED | 1418 测试全部通过，88% 覆盖率，ruff 零错误 |

## v0.5.0 数据源完善版

v0.5.0 聚焦数据源扩展：新增 5 个数据源提供者，DuckDB 接入 api.py 作为 L2 缓存层，多源降级链全面升级。

### v0.5.0 新增模块
- `datacore/macro/providers/national_bureau.py` — 国家统计局宏观数据源 (P0)
- `datacore/macro/providers/pboc.py` — 央行宏观数据源 (P1)
- `datacore/futures/providers/exchange_api.py` — 交易所官方数据源（上期所/郑商所/大商所）
- `datacore/futures/providers/shengyishe.py` — 生意社现货/基差数据源
- `datacore/equity/providers/guosen.py` — 国信证券数据源 (P2)

### v0.5.0 增强模块
- `datacore/api.py` — DuckDB L2 缓存集成（MemoryCache → DuckDB），版本号 v0.5.0
- `datacore/macro/macro_provider.py` — 3 源降级链: 统计局→央行→东方财富
- `datacore/macro/providers/__init__.py` — 新增 national_bureau/pboc 导出
- `datacore/futures/futures_provider.py` — 4 源降级链（新增 exchange_api/shengyishe）
- `datacore/futures/providers/__init__.py` — 新增 exchange_api/shengyishe 导出
- `datacore/equity/providers/__init__.py` — 新增 GuosenProvider 导出
- `datacore/equity/equity_provider.py` — 3 源降级链: 腾讯→东方财富→国信

### v0.5.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_macro_providers.py` | 28 | 宏观数据源 mock 测试 |
| `tests/test_futures_providers.py` | 6 | 期货基本面数据源 mock 测试 |
| `tests/test_guosen.py` | 7 | 国信证券 mock 测试 |
| `tests/test_news_providers.py` | 19 | 新闻数据源 mock 测试 |
| `tests/test_api_cache.py` | 12 | 缓存层测试 |

**新增 72 个测试用例，总计 656 个测试用例**

### v0.5.0 产出物清单

- ✅ 国家统计局宏观数据源（GDP/CPI/PPI/PMI）
- ✅ 央行宏观数据源（LPR/M2）
- ✅ 交易所官方数据源（上期所/郑商所/大商所）
- ✅ 生意社现货/基差数据源
- ✅ 国信证券数据源正式接入
- ✅ DuckDB L2 缓存集成（MemoryCache → DuckDB → HTTP）
- ✅ 宏观 3 源降级链
- ✅ 期货 4 源降级链
- ✅ A 股 3 源降级链
- ✅ 5 个新测试文件，72 个新测试用例
- ✅ D01 修复：shengyishe 提供真实基差，替换 eastmoney 近似算法
- ✅ D05 关闭：DuckDB 接入 api.py 缓存层

## v0.6.0 LLM 与智能加工版

v0.6.0 聚焦 LLM 能力完善：情绪打分端到端验证，基本面 LLM 加工模块，Docker 部署。

### v0.6.0 新增模块
- `datacore/processing/fundamental/fundamental_llm.py` — 基本面 LLM 加工（研报摘要 + 财报提取）
- `datacore/processing/fundamental/models.py` — 基本面加工数据模型
- `Dockerfile` — 应用 Dockerfile
- `docker-compose.yml` — 开发环境 Docker Compose
- `docker-compose.prod.yml` — 生产环境 Docker Compose
- `docs/DEPLOYMENT.md` — 部署文档

### v0.6.0 增强模块
- `datacore/processing/sentiment/sentiment_llm.py` — LLM 情绪打分端到端验证（15 个测试）

### v0.6.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_sentiment_llm.py` | 15 | LLM 情绪打分端到端测试 |
| `tests/test_fundamental_llm.py` | 12 | 基本面 LLM 加工测试 |

**新增 27 个测试用例，总计 683 个测试用例**

### v0.6.0 产出物清单

- ✅ LLM 情绪打分端到端验证（15 个测试）
- ✅ 基本面 LLM 加工模块（研报摘要 + 财报提取）
- ✅ 部署文档（docs/DEPLOYMENT.md）
- ✅ 2 个新测试文件，27 个新测试用例

## v1.0.0 生产就绪版

v1.0.0 聚焦生产就绪：WebSocket 实时行情、告警系统、性能基准测试、安全审计。

### v1.0.0 新增模块
- `datacore/stream.py` — WebSocket 实时行情（StreamQuote + WebSocketManager）
- `datacore/alert.py` — 告警引擎（AlertEngine + 预置规则 + 3 个通知渠道）
- `tests/benchmark_test.py` — 性能基准测试（8 个基准测试）
- `docs/SECURITY_CHECKLIST.md` — 安全审计清单（7 项检查）

### v1.0.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_stream.py` | 15 | WebSocket 连接/重连/订阅测试 |
| `tests/test_alert.py` | 18 | 告警引擎规则/渠道测试 |
| `tests/benchmark_test.py` | 8 | 性能基准测试（数据获取/缓存/加工/并发） |

**新增 41 个测试用例，总计 724 个测试用例**

### v1.0.0 产出物清单

- ✅ WebSocket 实时行情支持（StreamQuote + WebSocketManager）
- ✅ 告警系统（AlertEngine、预置规则、3 个通知渠道）
- ✅ 性能基准测试（8 个基准测试）
- ✅ 安全审计（docs/SECURITY_CHECKLIST.md，7 项检查全部通过）
- ✅ 3 个新测试文件，41 个新测试用例
- ✅ 代码覆盖率 ≥ 95%
- ✅ pylint ≥ 9.50/10, mypy: 0 错误, ruff: 0 错误

## v2.0.0 统一数据枢纽完整版

v2.0.0 是 Data-Core 统一数据枢纽的完整版本：FDT 兼容层、Qlib/RD-Agent 适配器，实现全生态对接。终验 1418 测试全部通过，88% 覆盖率（核心模块接近 100%），ruff 代码审计零错误。

### v2.0.0 新增模块
- `datacore/fdc_compat.py` — FDT 兼容层，提供 FDC 兼容的函数签名，平滑迁移 FDT 消费者
- `datacore/qlib_adapter/provider.py` — Qlib/RD-Agent 适配器，Qlib DataProvider 接口实现
- `datacore/qlib_adapter/converter.py` — 数据格式转换器（Data-Core ↔ Qlib）
- `datacore/qlib_adapter/__init__.py` — Qlib 适配器模块导出

### v2.0.0 增强模块
- `datacore/api.py` — 版本号 1.3.0 → 2.0.0
- `datacore/__init__.py` — 版本号 1.3.0 → 2.0.0

### v2.0.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_fdc_compat.py` | 98 | FDT 兼容层测试（FDC 函数签名全覆盖 + 数据格式适配） |
| `tests/test_qlib_adapter.py` | 99 | Qlib/RD-Agent 适配器测试（Provider 接口 + 格式转换） |

**新增 197 个测试用例，总计 1418 个测试用例**

### v2.0.0 产出物清单

- ✅ FDT 兼容层（datacore/fdc_compat.py）
- ✅ FDC 兼容函数签名映射（get_kline/get_quote/get_fundamental/get_indicators 等）
- ✅ 数据格式适配（DataFrame/Series 输出 + 字段名映射 + 错误码兼容）
- ✅ 渐进式迁移路径 + 双轨运行支持
- ✅ Qlib/RD-Agent 适配器（datacore/qlib_adapter/，3 个文件）
- ✅ Qlib DataProvider 完整接口实现（calendars/instruments/features/fundamentals）
- ✅ 表达式引擎支持（Alpha158 等经典因子表达式）
- ✅ 数据格式双向转换器（Data-Core ↔ Qlib）
- ✅ 版本号从 1.3.0 升级到 2.0.0
- ✅ 2 个新测试文件，197 个新测试用例
- ✅ 测试总数 1418 个（1221 + 197）
- ✅ 代码覆盖率 88%（核心模块接近 100%）
- ✅ ruff 代码审计零错误
- ✅ 统一数据枢纽完整交付

## v1.3.0 BaseTool & 数据工具链版

v1.3.0 聚焦 BaseTool 接口层与数据工具链建设：23 个 Tool（兼容 LangChain 协议）、复权/换月引擎、周期转换引擎、消费者反馈通道、数据清洗模块、数据校验模块、采集模块骨架、运维工具模块。v2.0 之前最大版本。

### v1.3.0 新增模块
- `datacore/tools/base.py` — DataCoreBaseTool 基类（兼容 LangChain 协议）
- `datacore/tools/` — 23 个 Tool（OHLCV/Quote/Sentiment/Health/ListSymbols/Macro/Fundamental/F10/Indicators/TermStructure/Basis/MarketRegime/News/Adjustment/Period/UnitUnify/DateAlign/DuplicateMerge/OutlierFilter/CrossSourceVerify/MissingDetect/CalMathCompute/ConfigRead）
- `datacore/tools/__init__.py` — all_tools 自动发现机制
- `datacore/adjustment/stock_adjustment.py` — 股票前复权/后复权/不复权
- `datacore/adjustment/futures_rollover.py` — 期货主力连续合约（成交量加权/持仓量加权/固定日换月）
- `datacore/adjustment/spread_adjustment.py` — 期货换月价差调整（前复权/后复权/等权）
- `datacore/adjustment/__init__.py` — 复权/换月模块导出
- `datacore/resampler/resampler.py` — 周期转换主入口（1m→5m→15m→30m→60m→daily→weekly→monthly）
- `datacore/resampler/ohlcv_aggregator.py` — OHLCV 正确聚合
- `datacore/resampler/auto_detector.py` — auto 模式自动选择
- `datacore/resampler/__init__.py` — 周期转换模块导出
- `datacore/issue.py` — 消费者反馈通道（IssueRegistry + DataIssue + IssueType + report_issue() API）
- `datacore/cleaning/unit_unify.py` — 单位统一
- `datacore/cleaning/date_align.py` — 日期对齐
- `datacore/cleaning/duplicate_merge.py` — 去重合并
- `datacore/cleaning/outlier_filter.py` — 异常值过滤
- `datacore/cleaning/__init__.py` — 数据清洗模块导出
- `datacore/validation/weight_score.py` — 权重评分
- `datacore/validation/cross_source.py` — 跨源校验
- `datacore/validation/missing_detect.py` — 缺失检测
- `datacore/validation/cal_math.py` — 计算校验
- `datacore/validation/__init__.py` — 数据校验模块导出
- `datacore/collectors/web_crawl.py` — 网页爬虫采集骨架
- `datacore/collectors/open_source.py` — 开源数据采集骨架
- `datacore/collectors/local_doc.py` — 本地文档采集骨架
- `datacore/collectors/search.py` — 搜索采集骨架
- `datacore/collectors/__init__.py` — 采集模块导出
- `datacore/operations/crawl_retry.py` — 爬取重试
- `datacore/operations/error_log.py` — 错误日志
- `datacore/operations/config_tools.py` — 配置工具
- `datacore/operations/__init__.py` — 运维工具导出

### v1.3.0 增强模块
- `datacore/api.py` — get_health() 新增 consumer_issues 字段
- `datacore/__init__.py` — 版本号 1.2.0 → 1.3.0

### v1.3.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_tools.py` | 89 | BaseTool 接口层测试（23 个 Tool 全覆盖） |
| `tests/test_adjustment.py` | 80 | 复权/换月引擎测试（股票复权 + 期货换月） |
| `tests/test_resampler.py` | 69 | 周期转换引擎测试（全周期 + auto 模式） |
| `tests/test_issue.py` | 34 | 消费者反馈通道测试（IssueRegistry + 自动降级） |
| `tests/test_cleaning.py` | 31 | 数据清洗模块测试（4 种清洗工具） |
| `tests/test_validation.py` | 27 | 数据校验模块测试（4 种校验工具） |
| `tests/test_collectors.py` | 18 | 采集模块骨架测试（4 种采集器） |
| `tests/test_operations.py` | 19 | 运维工具模块测试（3 种运维工具） |

**新增 365 个测试用例，总计 1221 个测试用例**

### v1.3.0 产出物清单

- ✅ BaseTool 接口层（datacore/tools/，24 个文件）
- ✅ DataCoreBaseTool 基类（兼容 LangChain 协议）
- ✅ 23 个 Tool：OHLCV/Quote/Sentiment/Health/ListSymbols/Macro/Fundamental/F10/Indicators/TermStructure/Basis/MarketRegime/News/Adjustment/Period/UnitUnify/DateAlign/DuplicateMerge/OutlierFilter/CrossSourceVerify/MissingDetect/CalMathCompute/ConfigRead
- ✅ all_tools 自动发现机制
- ✅ 复权/换月引擎（datacore/adjustment/，4 个文件）
- ✅ 股票前复权/后复权/不复权
- ✅ 期货主力连续合约（成交量加权/持仓量加权/固定日换月）
- ✅ 期货换月价差调整（前复权/后复权/等权）
- ✅ 周期转换引擎（datacore/resampler/，4 个文件）
- ✅ 1m→5m→15m→30m→60m→daily→weekly→monthly 全周期支持
- ✅ OHLCV 正确聚合（Open首/High最高/Low最低/Close尾/Volume求和）
- ✅ auto 模式自动选择
- ✅ 消费者反馈通道（datacore/issue.py）
- ✅ IssueRegistry + DataIssue + IssueType
- ✅ report_issue() API
- ✅ 自动降级应对
- ✅ get_health() 新增 consumer_issues
- ✅ 数据清洗模块（datacore/cleaning/，5 个文件）
- ✅ unit_unify / date_align / duplicate_merge / outlier_filter
- ✅ 数据校验模块（datacore/validation/，5 个文件）
- ✅ weight_score / cross_source / missing_detect / cal_math
- ✅ 采集模块骨架（datacore/collectors/，5 个文件）
- ✅ web_crawl / open_source / local_doc / search
- ✅ 运维工具模块（datacore/operations/，4 个文件）
- ✅ crawl_retry / error_log / config_tools
- ✅ 版本号从 1.2.0 升级到 1.3.0
- ✅ 8 个新测试文件，365 个新测试用例
- ✅ 测试总数 1221 个（856 + 365）
- ✅ v2.0 之前最大版本

## v1.2.0 FDC 模块吸收版

v1.2.0 聚焦 FDC 模块吸收与期货数据源扩展：indicators 技术指标模块、3 个期货新数据源、期货降级链从 4 源扩展为 7 源。

### v1.2.0 新增模块
- `datacore/indicators/core.py` — 37+ 基础指标纯 numpy 实现
- `datacore/indicators/tdx_compat.py` — TDX 通达信对齐指标
- `datacore/indicators/legacy_numpy.py` — 旧版兼容实现
- `datacore/indicators/trend_maturity.py` — 趋势成熟度评估
- `datacore/indicators/talib_wrapper.py` — TA-Lib 封装兜底
- `datacore/indicators/__init__.py` — 导出 compute_indicators / INDICATOR_NAMES / assess_trend_maturity
- `datacore/futures/providers/qmt.py` — QMT 迅投数据源（P2，依赖 xtquant）
- `datacore/futures/providers/web_fallback.py` — 网页备用数据源（P5）
- `datacore/futures/providers/tqsdk.py` — TqSdk 数据源（P6 末位兜底，依赖 tqsdk）

### v1.2.0 增强模块
- `datacore/futures/futures_provider.py` — 期货降级链从 4 源扩展为 7 源（TdxLc → EastMoney → QMT → ExchangeApi → ShengYiShe → WebFallback → TqSdk）

### v1.2.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_indicators.py` | 90 | 技术指标模块测试（核心指标/TDX 对齐/趋势成熟度/TA-Lib 兜底） |
| `tests/test_futures_new_providers.py` | 20 | 新期货数据源 mock 测试（QMT/TqSdk/WebFallback） |

**新增 110 个测试用例，总计 856 个测试用例**

### v1.2.0 产出物清单

- ✅ indicators/ 技术指标模块（FDC 吸收，5 个文件）
- ✅ 37+ 基础指标纯 numpy 实现
- ✅ TDX 通达信对齐指标层
- ✅ TA-Lib 封装兜底层
- ✅ 趋势成熟度评估（assess_trend_maturity）
- ✅ 三层路由体系：TDX → numpy core → TA-Lib
- ✅ 公开 API：compute_indicators, INDICATOR_NAMES, assess_trend_maturity
- ✅ QMTProvider 迅投资讯源（P2，依赖 xtquant）
- ✅ WebFallbackProvider 网页备用源（P5）
- ✅ TqSdkProvider 兜底源（P6，依赖 tqsdk）
- ✅ 期货降级链从 4 源扩展为 7 源
- ✅ 版本号从 1.1.0 升级到 1.2.0
- ✅ 2 个新测试文件，110 个新测试用例
- ✅ 代码覆盖率保持 96%

## v1.1.0 统一数据枢纽 Phase 1

v1.1.0 聚焦统一数据枢纽建设：异步双接口、F10 综合报告、core 共享基础设施模块。

### v1.1.0 新增模块
- `datacore/api_async.py` — AsyncDataProvider 异步双接口（基于 run_in_executor 线程池桥接同步代码）
- `datacore/api_f10.py` — F10 综合报告（聚合期限结构/价差/基差/仓单/持仓排名）
- `datacore/core/types.py` — KlineBar / QuoteData / FreshnessStatus 数据结构
- `datacore/core/data_freshness.py` — DataFreshnessAssessor 数据新鲜度评估
- `datacore/core/__init__.py` — 导出核心类型

### v1.1.0 增强模块
- `datacore/api.py` — UnifiedDataProvider 新增 get_f10() 方法
- `datacore/models/enums.py` — 新增 DataType.F10_REPORT 枚举值

### v1.1.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_phase1.py` | 28 | Phase 1 综合测试（async/F10/core 全覆盖） |

**新增 28 个测试用例，总计 746 个测试用例**

### v1.1.0 产出物清单

- ✅ AsyncDataProvider 异步双接口（api_async.py）
- ✅ F10 综合报告（api_f10.py + UnifiedDataProvider.get_f10）
- ✅ core/ 共享基础设施模块（types.py + data_freshness.py + __init__.py）
- ✅ DataType.F10_REPORT 枚举值
- ✅ 版本号从 1.0.0 升级到 1.1.0
- ✅ 1 个新测试文件，28 个新测试用例
- ✅ 代码覆盖率从 95% 提升到 96%

## v0.4.0 工程完善版

v0.4.0 聚焦工程化完善：熔断器、健康检查、指标收集、DuckDB 持久化、CLI 增强、ETF/CB 基础支持。

### v0.4.0 新增模块
- `datacore/breaker.py` — 带状态熔断器（CLOSED/OPEN/HALF_OPEN）
- `datacore/metrics.py` — 指标收集框架（调用次数/成功率/延迟/缓存命中率）
- `datacore/store/duckdb.py` — DuckDB 加密持久化（store/load 方法，按类型存取）

### v0.4.0 增强模块
- `datacore/api.py` — 新增 get_health() 健康检查接口
- `datacore/cli.py` — status 命令显示真实数据源状态（替代"待探测"占位符）
- `datacore/models/enums.py` — ETF/CB/REIT 基础数据获取支持

### v0.4.0 新增测试
| 测试文件 | 用例数 | 说明 |
|:---------|:-------|:-----|
| `tests/test_breaker.py` | 30 | 熔断器状态转换/超时/半开探测 |
| `tests/test_health.py` | 20 | 健康检查接口及各数据源状态 |
| `tests/test_metrics.py` | 30 | 指标收集/成功率/延迟/缓存命中率 |

**新增 80 个测试用例，总计 184 个测试用例**

### v0.4.0 产出物清单

- ✅ Breaker 熔断器（CLOSED/OPEN/HALF_OPEN 三种状态）
- ✅ MetricsCollector 指标收集框架
- ✅ DuckDB 加密持久化（store/load + 按类型存取）
- ✅ get_health() 健康检查接口
- ✅ CLI status 命令真实数据源状态
- ✅ ETF/CB/REIT 基础数据获取
- ✅ 80 个新增测试用例

## v0.3.0 产出物清单

### 新增模块
- `datacore/processing/` — 数据加工层（7个文件）
  - `base.py` — ProcessingStage 抽象基类
  - `models.py` — SentimentItem/SentimentData/MarketStateData/MarketRegime
  - `sentiment/sentiment_rule.py` — 规则情绪基线（词典法）
  - `sentiment/sentiment_llm.py` — LLM 情绪打分（含降级）
  - `sentiment/sentiment_aggregator.py` — 情绪聚合器（时间衰减+置信度加权）
  - `market_regime.py` — 市场制度检测（bull/bear/sideways）

### 增强模块
- `datacore/models/enums.py` — 新增 SENTIMENT/MARKET_STATE DataType
- `datacore/api.py` — 接入 SENTIMENT/MARKET_STATE/NEWS/MACRO 路由

### 新增测试
- `tests/test_processing.py` — 36 个用例

### 数据加工层能力
- ✅ 规则情绪基线（词典法，零成本，含否定词和程度副词处理）
- ✅ LLM 情绪打分骨架（含降级到规则基线）
- ✅ 情绪聚合器（时间衰减加权 + 置信度加权 + 按日聚合）
- ✅ 市场制度检测（趋势强度 + 波动率 + 成交量趋势综合判断）
- ✅ SENTIMENT/MARKET_STATE 接入 UnifiedDataProvider
