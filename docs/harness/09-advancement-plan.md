# Data-Core Advancement Plan

Version: v2.0.0 | Updated: 2026-07-20

## Milestones

| 里程碑 | 版本 | 日期 | 状态 | 说明 |
|:-------|:-----|:-----|:-----|:-----|
| **M1** | **v0.1.0** | **2026-07-18** | ✅ **COMPLETED** | 基础可用版 |
| **M2** | **v0.2.0** | **2026-07-18** | ✅ **COMPLETED** | 能力增强版（期货深度+新闻+宏观） |
| **M3** | **v0.3.0** | **2026-07-18** | ✅ **COMPLETED** | 数据加工层（情绪管线+市场制度） |
| **M4** | **v0.4.0** | **2026-07-18** | ✅ **COMPLETED** | 工程完善版（健康检查+熔断+指标+ETF/CB） |
| **M5** | **v0.5.0** | **2026-07-19** | ✅ **COMPLETED** | 数据源完善版（宏观/期货/A股扩展 + DuckDB缓存） |
| **M6** | **v0.6.0** | **2026-07-19** | ✅ **COMPLETED** | LLM 与智能加工版（情绪端到端 + 基本面LLM + Docker） |
| **M7** | **v1.0.0** | **2026-07-19** | ✅ **COMPLETED** | 生产就绪版（WebSocket + 告警 + 基准 + 安全审计） |
| **M8** | **v1.1.0** | **2026-07-19** | ✅ **COMPLETED** | 统一数据枢纽 Phase 1（异步双接口 + F10 + core） |
| **M9** | **v1.2.0** | **2026-07-19** | ✅ **COMPLETED** | FDC 模块吸收版（indicators + 3 个期货新数据源 + 7 源降级链） |
| **M10** | **v1.3.0** | **2026-07-19** | ✅ **COMPLETED** | BaseTool & 数据工具链版（23个Tool + 复权换月 + 周期转换 + 消费者反馈 + 数据清洗 + 数据校验 + 采集骨架 + 运维工具） |
| **M11** | **v2.0.0** | **2026-07-20** | ✅ **COMPLETED** | FDT 兼容层 + Qlib/RD-Agent 适配器（统一数据枢纽完整版） |
| **M12** | **v2.0.0** | **2026-07-20** | ✅ **COMPLETED** | 终验通过（1418测试 + 88%覆盖率 + ruff零错误） |

## M11 (v2.0.0) 交付清单 ✅

### FDT 兼容层
- ✅ FDT 兼容层（datacore/fdc_compat.py）
- ✅ FDC 兼容函数签名映射（get_kline/get_quote/get_fundamental/get_indicators 等）
- ✅ 数据格式适配（DataFrame/Series/native 三种输出格式）
- ✅ 字段名映射（FDC 风格 ↔ Data-Core 风格）
- ✅ 错误码兼容
- ✅ 渐进式迁移路径 + 双轨运行支持

### Qlib/RD-Agent 适配器
- ✅ Qlib/RD-Agent 适配器（datacore/qlib_adapter/，3 个文件）
- ✅ Qlib DataProvider 完整接口实现
- ✅ calendars() 交易日历接口
- ✅ instruments() 品种池接口
- ✅ features() 特征数据接口（OHLCV + 指标）
- ✅ fundamentals() 基本面数据接口
- ✅ 表达式引擎支持（Alpha158 等经典因子表达式）
- ✅ 数据格式双向转换器（Data-Core ↔ Qlib）

### 测试与质量
- ✅ 2 个新测试文件，197 个新测试用例
- ✅ 总计 39 个测试文件，1418 个测试用例
- ✅ 代码覆盖率 88%（核心模块接近 100%）
- ✅ ruff 代码审计零错误
- ✅ 统一数据枢纽完整交付

## M12 (v2.0.0) 终验通过 ✅

### 终验标准
- ✅ 1418 测试全部通过
- ✅ 88% 代码覆盖率（核心模块接近 100%）
- ✅ ruff 代码审计零错误
- ✅ pylint ≥ 9.50/10
- ✅ mypy 0 错误
- ✅ 41 个差距全部关闭（G01-G28, D01-D05）
- ✅ 7 项安全审计全部通过
- ✅ FDT 兼容层交付
- ✅ Qlib/RD-Agent 适配器交付

## M10 (v1.3.0) 交付清单 ✅

### BaseTool 接口层
- ✅ DataCoreBaseTool 基类（兼容 LangChain 协议）
- ✅ 23 个 Tool：OHLCV/Quote/Sentiment/Health/ListSymbols/Macro/Fundamental/F10/Indicators/TermStructure/Basis/MarketRegime/News/Adjustment/Period/UnitUnify/DateAlign/DuplicateMerge/OutlierFilter/CrossSourceVerify/MissingDetect/CalMathCompute/ConfigRead
- ✅ all_tools 自动发现机制
- ✅ 5 大分类：数据获取(13) / 数据处理(2) / 数据清洗(4) / 数据校验(3) / 运维工具(1)

### 复权/换月引擎
- ✅ 股票前复权/后复权/不复权
- ✅ 期货主力连续合约（成交量加权/持仓量加权/固定日换月）
- ✅ 期货换月价差调整（前复权/后复权/等权）
- ✅ datacore/adjustment/ 模块（4 个文件）

### 周期转换引擎
- ✅ 1m→5m→15m→30m→60m→daily→weekly→monthly 全周期支持
- ✅ OHLCV 正确聚合（Open首/High最高/Low最低/Close尾/Volume求和）
- ✅ auto 模式自动检测
- ✅ datacore/resampler/ 模块（4 个文件）

### 消费者反馈通道
- ✅ IssueRegistry + DataIssue + IssueType
- ✅ report_issue() API
- ✅ 四级自动降级应对（LOW/MEDIUM/HIGH/CRITICAL）
- ✅ get_health() 新增 consumer_issues 字段
- ✅ datacore/issue.py

### 数据清洗模块
- ✅ unit_unify 单位统一
- ✅ date_align 日期对齐
- ✅ duplicate_merge 去重合并
- ✅ outlier_filter 异常值过滤（3σ / IQR）
- ✅ datacore/cleaning/ 模块（5 个文件）

### 数据校验模块
- ✅ weight_score 权重评分
- ✅ cross_source 跨源校验
- ✅ missing_detect 缺失检测
- ✅ cal_math 计算校验
- ✅ datacore/validation/ 模块（5 个文件）

### 采集模块骨架
- ✅ web_crawl 网页爬虫采集骨架
- ✅ open_source 开源数据采集骨架
- ✅ local_doc 本地文档采集骨架
- ✅ search 搜索采集骨架
- ✅ datacore/collectors/ 模块（5 个文件）

### 运维工具模块
- ✅ crawl_retry 爬取重试
- ✅ error_log 错误日志
- ✅ config_tools 配置工具
- ✅ datacore/operations/ 模块（4 个文件）

### 测试与质量
- ✅ 8 个新测试文件，365 个新测试用例
- ✅ 总计 37 个测试文件，1221 个测试用例
- ✅ 代码覆盖率保持 96%
- ✅ pylint ≥ 9.50/10, mypy: 0 错误, ruff: 0 错误
- ✅ v2.0 之前最大版本

## M9 (v1.2.0) 交付清单 ✅

### 技术指标模块
- ✅ indicators/ 技术指标模块（从 FDC 吸收，5 个文件）
- ✅ 37+ 基础指标纯 numpy 实现
- ✅ TDX 通达信对齐指标层
- ✅ TA-Lib 封装兜底层
- ✅ 三层路由体系：TDX → numpy core → TA-Lib
- ✅ 趋势成熟度评估（assess_trend_maturity）
- ✅ 公开 API：compute_indicators, INDICATOR_NAMES, assess_trend_maturity

### 期货数据源扩展
- ✅ QMTProvider 迅投资讯源（P2，依赖 xtquant）
- ✅ WebFallbackProvider 网页备用源（P5，零依赖）
- ✅ TqSdkProvider 兜底源（P6，依赖 tqsdk）
- ✅ 期货降级链从 4 源扩展为 7 源

### 测试与质量
- ✅ 2 个新测试文件，110 个新测试用例
- ✅ 总计 29 个测试文件，856 个测试用例
- ✅ 代码覆盖率保持 96%

## M8 (v1.1.0) 交付清单 ✅

### 异步双接口
- ✅ AsyncDataProvider 异步双接口（api_async.py）
- ✅ 基于 run_in_executor 线程池桥接同步代码
- ✅ get_kline_async / get_quote_async / get_f10_async
- ✅ 与同步 UnifiedDataProvider 接口完全对齐

### F10 综合报告
- ✅ F10 综合报告模块（api_f10.py）
- ✅ UnifiedDataProvider.get_f10() 方法
- ✅ 聚合期限结构/价差/基差/仓单/持仓排名
- ✅ DataType.F10_REPORT 枚举值

### core 共享基础设施
- ✅ datacore/core/ 模块（types.py + data_freshness.py + __init__.py）
- ✅ KlineBar / QuoteData 核心数据结构
- ✅ FreshnessStatus 枚举（FRESH/STALE/EXPIRED）
- ✅ DataFreshnessAssessor 数据新鲜度评估器

### 测试与质量
- ✅ 1 个新测试文件，28 个新测试用例
- ✅ 总计 27 个测试文件，746 个测试用例
- ✅ 代码覆盖率从 95% 提升到 96%
- ✅ pylint ≥ 9.50/10, mypy: 0 错误, ruff: 0 错误

## M7 (v1.0.0) 交付清单 ✅

### WebSocket 实时行情
- ✅ StreamQuote 数据模型（symbol/price/volume/timestamp/exchange）
- ✅ WebSocketManager 连接管理（connect/subscribe/on_quote）
- ✅ 自动重连策略（指数退避）
- ✅ 心跳保活机制

### 告警引擎
- ✅ AlertEngine 告警引擎
- ✅ 预置告警规则（price_breakout/volatility_anomaly/data_stale/breaker_trip）
- ✅ 3 个通知渠道（日志/文件/Webhook）
- ✅ 渠道降级策略（Webhook → 文件 → 日志）

### 性能基准
- ✅ 数据获取性能基准
- ✅ 缓存层性能基准
- ✅ 数据加工性能基准
- ✅ 并发处理性能基准
- ✅ 8 个基准测试

### 安全审计
- ✅ 认证安全（API Key 环境变量）
- ✅ 数据加密（DuckDB 加密存储）
- ✅ 注入防护（SQL 参数化）
- ✅ 配置安全（默认值安全）
- ✅ 依赖安全（版本锁定）
- ✅ 日志安全（无敏感信息）
- ✅ 通信安全（HTTPS/WS 加密）
- ✅ docs/SECURITY_CHECKLIST.md

### 测试与质量
- ✅ 3 个新测试文件，41 个新测试用例
- ✅ 总计 26 个测试文件，724+ 个测试用例
- ✅ 代码覆盖率 ≥ 95%
- ✅ pylint ≥ 9.50/10, mypy: 0 错误, ruff: 0 错误

## M6 (v0.6.0) 交付清单 ✅

### LLM 情绪打分
- ✅ LLM 情绪打分端到端验证（15 个测试）
- ✅ 真实 API 调用路径验证

### 基本面 LLM 加工
- ✅ fundamental_llm.py 研报摘要提取
- ✅ fundamental_llm.py 财报提取
- ✅ 基本面加工数据模型

### Docker 部署
- ✅ Dockerfile（应用容器化）
- ✅ docker-compose.yml（开发环境）
- ✅ docker-compose.prod.yml（生产环境）
- ✅ docs/DEPLOYMENT.md（部署文档）

### 测试
- ✅ 2 个新测试文件，27 个新测试用例

## M5 (v0.5.0) 交付清单 ✅

### 数据源完善（P1→P2）
- ✅ 国信 HTTP 数据源正式接入（GuosenProvider，7 个 mock 测试）
- ✅ 新闻数据源实际 HTTP 抓取（财联社/华尔街见闻/东方财富研报，19 个 mock 测试）
- ✅ 国家统计局/央行宏观源接入（3 源降级链，28 个 mock 测试）
- ✅ 期货基本面数据实际抓取（交易所官方/生意社，6 个 mock 测试）

### 缓存层
- ✅ DuckDB 接入 api.py 作为 L2 缓存（MemoryCache → DuckDB → HTTP）
- ✅ 12 个缓存层测试用例

### 降级链
- ✅ 宏观 3 源降级链: 统计局→央行→东方财富
- ✅ 期货 4 源降级链: TQ-Local→东方财富→交易所→生意社
- ✅ A 股 3 源降级链: 腾讯→东方财富→国信

### 技术债修复
- ✅ D01: 基差近似算法通过生意社真实数据源修复
- ✅ D03: news provider 异常处理通过 mock 覆盖
- ✅ D05: DuckDB 接入 api.py 缓存层

### 测试
- ✅ 新增 5 个测试文件，72 个测试用例
- ✅ 总计 20 个测试文件，656 个测试用例

## M4 (v0.4.0) 交付清单 ✅

### 熔断器
- ✅ Breaker 类（CLOSED/OPEN/HALF_OPEN 三种状态）
- ✅ 超时触发熔断
- ✅ 半开探测恢复
- ✅ 可配置 max_failures / recovery_timeout
- ✅ 30 个测试用例

### 健康检查
- ✅ UnifiedDataProvider.get_health() 方法
- ✅ 各数据源实时可用状态探测
- ✅ 整体 healthy/degraded/unavailable 状态汇总
- ✅ 20 个测试用例

### 指标收集
- ✅ MetricsCollector 框架
- ✅ 调用次数/成功率/延迟（P50/P95/P99）/缓存命中率
- ✅ MetricsCollector.report() 快照
- ✅ 30 个测试用例

### DuckDB 持久化
- ✅ store/duckdb.py 加密持久化
- ✅ store(key, value) / load(key)
- ✅ 按类型（kline/quote/macro 等）具体存读方法

### CLI 增强
- ✅ status 命令显示真实数据源状态

### ETF/CB/REIT
- ✅ DataType 已定义
- ✅ 基础数据获取

### 测试
- ✅ 80 个新增测试用例（总计 184 个）
- ✅ test_breaker.py / test_health.py / test_metrics.py

## 晋级标准

### M2 → M3 晋级标准 ✅
- [x] SENTIMENT/MARKET_STATE DataType 定义
- [x] 情绪加工管线可用（规则基线+LLM骨架）
- [x] 市场制度检测可用
- [x] 接入 UnifiedDataProvider
- [x] 测试用例覆盖新增功能

### M3 → M4 晋级标准 ✅
- [x] 健康检查接口可用
- [x] 熔断器实现并测试
- [x] 指标收集框架就绪
- [x] ETF/CB 基础功能可用
- [x] 所有 P1 差距关闭
- [x] 80 个新增测试用例

### M4 → M5 晋级标准 ✅
- [x] 国信 HTTP 数据源正式接入
- [x] 新闻数据源实际 HTTP 抓取
- [x] 国家统计局/央行宏观源接入
- [x] 期货基本面数据实际抓取
- [x] DuckDB 集成到 api.py 缓存层
- [x] 72 个新增测试用例

### M5 → M6 晋级标准 ✅
- [x] LLM 情绪打分端到端验证（15 个测试）
- [x] 基本面 LLM 加工模块（研报摘要 + 财报提取）
- [x] 部署文档
- [x] 27 个新增测试用例

### M6 → M7 晋级标准 ✅
- [x] WebSocket 实时行情支持
- [x] 告警系统（预置规则 + 3 通知渠道）
- [x] 性能基准测试（8 个基准测试）
- [x] 安全审计（7 项检查全部通过）
- [x] 全链路 trace_id 贯穿
- [x] P0/P1 级差距全部关闭
- [x] 整体测试覆盖率 ≥ 95%
- [x] pylint ≥ 9.50/10, mypy: 0 错误, ruff: 0 错误
- [x] 41 个新增测试用例

### M7 → M8 晋级标准 ✅
- [x] AsyncDataProvider 异步双接口
- [x] F10 综合报告（聚合期限结构/价差/基差/仓单/持仓排名）
- [x] core/ 共享基础设施模块（types.py + data_freshness.py）
- [x] DataType.F10_REPORT 枚举值
- [x] 数据新鲜度评估器（FreshnessStatus 三级状态）
- [x] G13-G16 差距全部关闭
- [x] 整体测试覆盖率 ≥ 96%
- [x] pylint ≥ 9.50/10, mypy: 0 错误, ruff: 0 错误
- [x] 28 个新增测试用例

### M8 → M9 晋级标准 ✅
- [x] indicators/ 技术指标模块（从 FDC 吸收）
- [x] 37+ 基础指标纯 numpy 实现
- [x] TDX 通达信对齐指标层
- [x] TA-Lib 封装兜底层
- [x] 三层路由体系：TDX → numpy core → TA-Lib
- [x] 趋势成熟度评估（assess_trend_maturity）
- [x] QMTProvider 迅投资讯源（P2）
- [x] WebFallbackProvider 网页备用源（P5）
- [x] TqSdkProvider 兜底源（P6）
- [x] 期货降级链从 4 源扩展为 7 源
- [x] G17-G18 差距全部关闭
- [x] 整体测试覆盖率 ≥ 96%
- [x] 110 个新增测试用例

### M9 → M10 晋级标准 ✅
- [x] BaseTool 接口层（DataCoreBaseTool 基类，兼容 LangChain 协议）
- [x] 23 个 Tool 全覆盖（数据获取/处理/清洗/校验/运维）
- [x] all_tools 自动发现机制
- [x] 复权/换月引擎（股票复权 + 期货主力连续 + 价差调整）
- [x] 周期转换引擎（全周期 + OHLCV 正确聚合 + auto 模式）
- [x] 消费者反馈通道（IssueRegistry + report_issue() + 自动降级）
- [x] 数据清洗模块（4 种清洗工具）
- [x] 数据校验模块（4 种校验工具）
- [x] 采集模块骨架（4 种采集器）
- [x] 运维工具模块（3 种运维工具）
- [x] get_health() 新增 consumer_issues
- [x] G19-G26 差距全部关闭
- [x] 整体测试覆盖率 ≥ 96%
- [x] pylint ≥ 9.50/10, mypy: 0 错误, ruff: 0 错误
- [x] 365 个新增测试用例，测试总数 1221 个

### M10 → M11 晋级标准 ✅
- [x] FDT 兼容层（fdc_compat.py）
- [x] FDC 兼容函数签名映射（get_kline/get_quote/get_fundamental/get_indicators 等）
- [x] 数据格式适配（DataFrame/Series/native 三种输出格式）
- [x] 字段名映射（FDC 风格 ↔ Data-Core 风格）
- [x] 错误码兼容
- [x] 渐进式迁移路径 + 双轨运行支持
- [x] Qlib/RD-Agent 适配器（qlib_adapter/）
- [x] Qlib DataProvider 完整接口（calendars/instruments/features/fundamentals）
- [x] 表达式引擎支持（Alpha158 等经典因子表达式）
- [x] 数据格式双向转换器（Data-Core ↔ Qlib）
- [x] G27-G28 差距全部关闭
- [x] 197 个新增测试用例，测试总数 1418 个

### M11 → M12 晋级标准 ✅
- [x] 1418 测试全部通过
- [x] 88% 代码覆盖率（核心模块接近 100%）
- [x] ruff 代码审计零错误
- [x] pylint ≥ 9.50/10
- [x] mypy 0 错误
- [x] 41 个差距全部关闭（G01-G28, D01-D05）
- [x] 7 项安全审计全部通过
- [x] FDT 兼容层交付
- [x] Qlib/RD-Agent 适配器交付
- [x] 统一数据枢纽完整交付

## 项目最终状态

| 维度 | v2.0.0 |
|:-----|:-------|
| 版本 | v2.0.0 统一数据枢纽完整版 |
| 源文件 | 100+ 个 .py |
| 测试文件 | 39 个 |
| 测试用例 | 1418 个 |
| 代码覆盖率 | 88%（核心模块接近 100%） |
| pylint | ≥ 9.50/10 |
| mypy | 0 错误 |
| ruff | 0 错误 |
| 差距关闭 | 41 个全部关闭 |
| 安全审计 | 7 项全部通过 |
| 部署 | 裸机部署（推荐），可选容器化 |
| 定位 | 统一数据枢纽完整交付 |
