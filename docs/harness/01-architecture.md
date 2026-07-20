# Data-Core Architecture

Version: v2.0.0 | Updated: 2026-07-20

## 1. System Positioning

Data-Core is an independent data infrastructure module providing unified data interfaces for FTS (Factor Trading System) and other research tools. All data sources are self-contained with zero external MCP/Skill/Agent dependencies.

Data-Core is responsible for data collection and processing (including LLM-based sentiment scoring and market regime detection), while FTS is responsible for factor evolution and strategy generation.

**v0.3.0 边界更新**: SENTIMENT/MARKET_STATE 由 Data-Core 数据加工层产出（含LLM打分+聚合），FTS 直接消费。

**v0.4.0 边界更新**: 新增 Breaker 熔断层、MetricsCollector 指标收集框架、DuckDB 持久化数据流。

**v0.5.0 边界更新**: 新增 5 个数据源（国家统计局/央行/交易所/生意社/国信），DuckDB 接入 api.py 作为 L2 缓存层，多源降级链全面扩展。

**v0.6.0 边界更新**: 新增 LLM 情绪打分端到端验证，基本面 LLM 加工模块（研报摘要 + 财报提取）。

**v1.0.0 边界更新**: 新增 WebSocket 实时行情管理、告警引擎、性能基准测试框架、安全审计清单。

**v1.1.0 边界更新**: 新增 AsyncDataProvider 异步双接口、F10 综合报告、core/ 共享基础设施模块（数据结构 + 新鲜度评估）。

**v1.2.0 边界更新**: 新增 indicators/ 技术指标模块（从 FDC 吸收）、3 个期货新数据源（QMT/TqSdk/WebFallback），期货降级链从 4 源扩展为 7 源。

**v1.3.0 边界更新**: 新增 BaseTool 接口层（23 个 Tool，兼容 LangChain 协议）、复权/换月引擎、周期转换引擎、消费者反馈通道、数据清洗模块、数据校验模块、采集模块骨架、运维工具模块。v2.0 之前最大版本，测试总数 1221 个。

**v2.0.0 边界更新**: 新增 FDT 兼容层（fdc_compat.py，提供 FDC 兼容的函数签名）、Qlib/RD-Agent 适配器（qlib_adapter/provider.py）。统一数据枢纽完整版，测试总数 1418 个，覆盖率 88%（核心模块接近 100%），ruff 代码审计零错误。

## 2. Layered Architecture

```
UnifiedDataProvider (api.py)
  ├── AsyncDataProvider (api_async.py, v1.1.0 新增)
  │   └── 异步双接口，基于 run_in_executor 线程池桥接同步代码
  ├── F10 综合报告 (api_f10.py, v1.1.0 新增)
  │   └── get_f10() — 聚合期限结构/价差/基差/仓单/持仓排名
  ├── Breaker (熔断层, v0.4.0 新增)
  │   └── 包裹所有数据源调用（CLOSED/OPEN/HALF_OPEN）
  ├── MetricsCollector (指标收集, v0.4.0 新增)
  │   └── 统计调用次数/成功率/延迟/缓存命中率
  ├── Cache Layer (v0.5.0: MemoryCache → DuckDB)
  │   ├── L1: MemoryCache（内存缓存）
  │   └── L2: DuckDB（持久化缓存，仅 OHLCV）
  ├── core/             # 共享基础设施（v1.1.0 新增）
  │   ├── types.py               # KlineBar / QuoteData / FreshnessStatus
  │   ├── data_freshness.py      # DataFreshnessAssessor 数据新鲜度评估
  │   └── __init__.py            # 导出核心类型
  ├── indicators/       # 技术指标模块（v1.2.0 新增，FDC 吸收）
  │   ├── core.py                # 37+ 基础指标纯 numpy 实现
  │   ├── tdx_compat.py          # TDX 通达信对齐指标
  │   ├── legacy_numpy.py        # 旧版兼容实现
  │   ├── trend_maturity.py      # 趋势成熟度评估
  │   ├── talib_wrapper.py       # TA-Lib 封装兜底
  │   └── __init__.py            # 导出 compute_indicators / INDICATOR_NAMES / assess_trend_maturity
  ├── tools/            # BaseTool 接口层（v1.3.0 新增，核心交付）
  │   ├── base.py                # DataCoreBaseTool 基类（兼容 LangChain 协议）
  │   ├── ohlcv.py               # OHLCV 数据工具
  │   ├── quote.py               # Quote 行情工具
  │   ├── sentiment.py           # Sentiment 情绪工具
  │   ├── health.py              # Health 健康检查工具
  │   ├── list_symbols.py        # ListSymbols 品种列表工具
  │   ├── macro.py               # Macro 宏观工具
  │   ├── fundamental.py         # Fundamental 基本面工具
  │   ├── f10.py                 # F10 综合报告工具
  │   ├── indicators.py          # Indicators 技术指标工具
  │   ├── term_structure.py      # TermStructure 期限结构工具
  │   ├── basis.py               # Basis 基差工具
  │   ├── market_regime.py       # MarketRegime 市场制度工具
  │   ├── news.py                # News 新闻工具
  │   ├── adjustment.py          # Adjustment 复权工具
  │   ├── period.py              # Period 周期转换工具
  │   ├── unit_unify.py          # UnitUnify 单位统一（清洗）
  │   ├── date_align.py          # DateAlign 日期对齐（清洗）
  │   ├── duplicate_merge.py     # DuplicateMerge 去重合并（清洗）
  │   ├── outlier_filter.py      # OutlierFilter 异常值过滤（清洗）
  │   ├── cross_source_verify.py # CrossSourceVerify 跨源校验
  │   ├── missing_detect.py      # MissingDetect 缺失检测
  │   ├── cal_math_compute.py    # CalMathCompute 计算校验
  │   ├── config_read.py         # ConfigRead 配置读取（运维）
  │   └── __init__.py            # all_tools 自动发现机制
  ├── adjustment/       # 复权/换月引擎（v1.3.0 新增）
  │   ├── stock_adjustment.py    # 股票前复权/后复权/不复权
  │   ├── futures_rollover.py    # 期货主力连续合约（成交量/持仓量/固定日换月）
  │   ├── spread_adjustment.py   # 期货换月价差调整（前复权/后复权/等权）
  │   └── __init__.py            # 导出调整接口
  ├── resampler/        # 周期转换引擎（v1.3.0 新增）
  │   ├── resampler.py           # 1m→5m→15m→30m→60m→daily→weekly→monthly
  │   ├── ohlcv_aggregator.py    # OHLCV 正确聚合
  │   ├── auto_detector.py       # auto 模式自动选择
  │   └── __init__.py            # 导出 resample 接口
  ├── issue.py          # 消费者反馈通道（v1.3.0 新增）
  │   └── IssueRegistry + DataIssue + IssueType + report_issue() API
  ├── cleaning/         # 数据清洗模块（v1.3.0 新增）
  │   ├── unit_unify.py          # 单位统一
  │   ├── date_align.py          # 日期对齐
  │   ├── duplicate_merge.py     # 去重合并
  │   ├── outlier_filter.py      # 异常值过滤
  │   └── __init__.py            # 导出清洗工具
  ├── validation/       # 数据校验模块（v1.3.0 新增）
  │   ├── weight_score.py        # 权重评分
  │   ├── cross_source.py        # 跨源校验
  │   ├── missing_detect.py      # 缺失检测
  │   ├── cal_math.py            # 计算校验
  │   └── __init__.py            # 导出校验工具
  ├── collectors/       # 新增采集模块骨架（v1.3.0 新增）
  │   ├── web_crawl.py           # 网页爬虫采集
  │   ├── open_source.py         # 开源数据采集
  │   ├── local_doc.py           # 本地文档采集
  │   ├── search.py              # 搜索采集
  │   └── __init__.py            # 导出采集器
  ├── operations/       # 运维工具模块（v1.3.0 新增）
  │   ├── crawl_retry.py         # 爬取重试
  │   ├── error_log.py           # 错误日志
  │   ├── config_tools.py        # 配置工具
  │   └── __init__.py            # 导出运维工具
  ├── fdc_compat.py     # FDT 兼容层（v2.0.0 新增）
  │   └── 提供 FDC 兼容的函数签名，平滑迁移 FDT 消费者
  ├── qlib_adapter/     # Qlib/RD-Agent 适配器（v2.0.0 新增）
  │   ├── provider.py            # Qlib 数据提供者接口
  │   └── __init__.py            # 导出适配器
  ├── futures/          # 期货数据模块
  │   ├── futures_provider.py    # 期货统一入口（7 源降级链, v1.2.0 扩展）
  │   └── providers/             # 多源降级链
  │       ├── tdx_lc.py          # TQ-Local (P0)
  │       ├── eastmoney.py       # 东方财富 (P1)
  │       ├── qmt.py             # QMT 迅投 (P2, v1.2.0)
  │       ├── exchange_api.py    # 交易所官方（上期所/郑商所/大商所）(P3, v0.5.0)
  │       ├── shengyishe.py      # 生意社现货/基差 (P4, v0.5.0)
  │       ├── web_fallback.py    # 网页备用 (P5, v1.2.0)
  │       └── tqsdk.py           # TqSdk 兜底 (P6, v1.2.0)
  ├── equity/           # 股票数据模块
  │   ├── equity_provider.py     # 股票统一入口（3 源降级链）
  │   ├── financial.py           # 财务数据
  │   └── providers/             # 多源降级链
  │       ├── tencent.py         # 腾讯财经 (P0)
  │       ├── eastmoney.py       # 东方财富 (P1)
  │       └── guosen.py          # 国信证券 (P2, v0.5.0)
  ├── news/             # 新闻资讯模块（v0.2.0）
  │   ├── news_provider.py       # 新闻统一入口
  │   ├── classifier.py          # 新闻分类器
  │   └── providers/             # 多源降级链
  ├── macro/            # 宏观数据模块（v0.2.0）
  │   ├── macro_provider.py      # 宏观统一入口（3 源降级链, v0.5.0 新增）
  │   └── providers/             # 多源降级链
  │       ├── eastmoney_macro.py # 东方财富宏观 (P2)
  │       ├── national_bureau.py # 国家统计局 (P0, v0.5.0)
  │       └── pboc.py            # 央行 (P1, v0.5.0)
  ├── processing/       # 数据加工层（v0.3.0 新增）
  │   ├── base.py                # ProcessingStage 抽象基类
  │   ├── models.py              # SentimentItem/SentimentData/MarketStateData
  │   ├── sentiment/             # 情绪加工管线
  │   │   ├── sentiment_rule.py  # 规则情绪基线（词典法，零成本）
  │   │   ├── sentiment_llm.py   # LLM 情绪打分（高质量，v0.6.0 端到端验证）
  │   │   └── sentiment_aggregator.py  # 情绪聚合器
  │   ├── market_regime.py       # 市场制度检测（bull/bear/sideways）
  │   └── fundamental/           # 基本面 LLM 加工（v0.6.0 新增）
  │       ├── fundamental_llm.py # 研报摘要 + 财报提取
  │       └── models.py          # 基本面加工数据模型
  ├── stream/           # WebSocket 实时行情（v1.0.0 新增）
  │   └── stream.py             # StreamQuote + WebSocketManager
  ├── alert/            # 告警引擎（v1.0.0 新增）
  │   └── alert.py              # AlertEngine + 预置规则 + 3 通知渠道
  ├── store/            # 存储层（缓存+持久化）
  │   ├── cache.py               # MemoryCache 内存缓存
  │   └── duckdb.py              # DuckDB 持久化（v0.4.0 新增加密存读，v0.5.0 接入缓存层）
  ├── models/           # 数据模型与枚举
  │   └── enums.py               # DataType/MarketType/SourceGrade
  ├── registry/         # 品种注册表
  └── config.py         # 统一配置系统

# 数据持久化流（v0.4.0）
api.py → store/duckdb.py → DuckDB 数据库
  - store(key, value): 加密持久化写入
  - load(key): 加密持久化读取
  - 按类型（kline/quote/macro 等）提供具体存读方法

# 缓存层数据流（v0.5.0）
请求 → MemoryCache (L1) → DuckDB (L2, 仅 OHLCV) → HTTP 数据源
  - L1 命中: 直接返回 CACHED 数据，无网络开销
  - L1 未命中 L2 命中: 从 DuckDB 加载 K 线，写回 MemoryCache
  - L1/L2 均未命中: 走降级链获取 HTTP 数据，写回 L1 + L2

# WebSocket 实时数据流（v1.0.0）
WebSocketManager → 行情订阅 → 数据回调 → 告警引擎
  - 连接管理：自动重连 + 心跳保活
  - 订阅管理：按品种/类型分发行情
  - 告警触发：预置规则检测 → 渠道通知（日志/文件/Webhook）

# 告警引擎数据流（v1.0.0）
AlertEngine → 规则匹配 → 渠道分发
  - 预置规则：价格突破/波动率异常/数据延迟/熔断触发
  - 通知渠道：日志记录 / 文件写入 / Webhook 回调
```

## 3. DataType 体系（v0.4.0 更新）

### 通用类型（全市场）
- `OHLCV`, `QUOTE`, `TECHNICAL`, `FINANCIAL`, `FUNDAMENTAL`
- `MACRO`, `NEWS`, `ANNOUNCEMENT`
- `SENTIMENT` (v0.3.0): 情绪数据，Data-Core 数据加工层产出
- `MARKET_STATE` (v0.3.0): 市场制度，Data-Core 数据加工层产出

### 期货特异类型
- `FUTURES_CONTRACT_CHAIN`, `FUTURES_TERM_STRUCTURE`, `FUTURES_SPREAD`
- `FUTURES_BASIS`, `FUTURES_POSITION`, `FUTURES_WAREHOUSE_RECEIPT`
- `F10_REPORT` (v1.1.0): F10 综合报告，聚合期限结构/价差/基差/仓单/持仓排名

### ETF/可转债/REIT 特异类型（v0.4.0 已实现基础获取）
- `ETF_NAV`, `ETF_PREMIUM`, `ETF_FUND_FLOW`
- `CB_CONVERSION`, `CB_TERMS`, `CB_PURE_BOND`

## 4. v2.0.0 新增组件

| 组件 | 文件 | 说明 |
|:-----|:-----|:-----|
| FDT 兼容层 | datacore/fdc_compat.py | 提供 FDC 兼容的函数签名，平滑迁移 FDT 消费者 |
| Qlib/RD-Agent 适配器 | datacore/qlib_adapter/ | Qlib 数据提供者接口，支持 RD-Agent 因子研究框架 |
| FDT 兼容层测试 | tests/test_fdc_compat.py | 98 个测试用例（FDC 兼容函数签名全覆盖） |
| Qlib 适配器测试 | tests/test_qlib_adapter.py | 99 个测试用例（Qlib Provider 接口全覆盖） |

### fdc_compat.py FDT 兼容层（v2.0.0）

```
fdc_compat.py
  ├── 兼容函数签名映射
  │   ├── get_kline() → UnifiedDataProvider.get_kline()
  │   ├── get_quote() → UnifiedDataProvider.get_quote()
  │   ├── get_fundamental() → UnifiedDataProvider.get_fundamental()
  │   ├── get_indicators() → indicators.compute_indicators()
  │   └── ... 其他 FDC 兼容接口
  ├── 数据格式适配
  │   ├── DataFrame / Series 输出格式
  │   ├── 字段名映射（FDC 风格 → Data-Core 风格）
  │   └── 错误码兼容
  └── 迁移指南
      ├── 渐进式迁移路径
      └── 双轨运行支持
```

### qlib_adapter/ Qlib/RD-Agent 适配器（v2.0.0）

```
qlib_adapter/
  ├── provider.py              # Qlib DataProvider 接口实现
  │   ├── calendars()          # 交易日历
  │   ├── instruments()        # 股票池/品种池
  │   ├── features()           # 特征数据（OHLCV + 指标）
  │   ├── fundamentals()       # 基本面数据
  │   └── expression_engine    # 表达式引擎支持
  ├── converter.py             # 数据格式转换器
  │   ├── Data-Core → Qlib 格式
  │   └── Qlib → Data-Core 格式
  └── __init__.py              # 导出 QlibDataProvider
```

**适配器特性**:
- 完整实现 Qlib DataProvider 接口协议
- 支持 RD-Agent 因子研究框架无缝接入
- 自动数据格式转换（Data-Core 内部格式 ↔ Qlib 标准格式）
- 交易日历、品种池、特征数据、基本面数据全覆盖
- 表达式引擎兼容（支持 Qlib Alpha158 等经典因子表达式）

## 5. v1.3.0 新增组件

| 组件 | 文件 | 说明 |
|:-----|:-----|:-----|
| BaseTool 接口层 | datacore/tools/ | DataCoreBaseTool 基类（兼容 LangChain 协议），23 个 Tool，all_tools 自动发现 |
| 复权/换月引擎 | datacore/adjustment/ | 股票复权 + 期货主力连续合约 + 换月价差调整 |
| 周期转换引擎 | datacore/resampler/ | 1m→5m→15m→30m→60m→daily→weekly→monthly，OHLCV 正确聚合 |
| 消费者反馈通道 | datacore/issue.py | IssueRegistry + DataIssue + IssueType + report_issue() API |
| 数据清洗模块 | datacore/cleaning/ | unit_unify / date_align / duplicate_merge / outlier_filter |
| 数据校验模块 | datacore/validation/ | weight_score / cross_source / missing_detect / cal_math |
| 采集模块骨架 | datacore/collectors/ | web_crawl / open_source / local_doc / search |
| 运维工具模块 | datacore/operations/ | crawl_retry / error_log / config_tools |
| BaseTool 测试 | tests/test_tools.py | 89 个测试用例（23 个 Tool 全覆盖） |
| 复权换月测试 | tests/test_adjustment.py | 80 个测试用例（股票复权 + 期货换月） |
| 周期转换测试 | tests/test_resampler.py | 69 个测试用例（全周期聚合 + auto 模式） |
| 消费者反馈测试 | tests/test_issue.py | 34 个测试用例（IssueRegistry + 自动降级） |
| 数据清洗测试 | tests/test_cleaning.py | 31 个测试用例（4 种清洗工具） |
| 数据校验测试 | tests/test_validation.py | 27 个测试用例（4 种校验工具） |
| 采集模块测试 | tests/test_collectors.py | 18 个测试用例（4 种采集器骨架） |
| 运维工具测试 | tests/test_operations.py | 19 个测试用例（3 种运维工具） |

### tools/ BaseTool 接口层（v1.3.0，核心交付）

```
tools/
  ├── base.py                        # DataCoreBaseTool 基类（兼容 LangChain 协议）
  ├── ohlcv.py / quote.py            # 行情数据工具
  ├── sentiment.py / health.py       # 情绪 & 健康检查工具
  ├── list_symbols.py                # 品种列表工具
  ├── macro.py / fundamental.py      # 宏观 & 基本面工具
  ├── f10.py / indicators.py         # F10 & 技术指标工具
  ├── term_structure.py / basis.py   # 期限结构 & 基差工具
  ├── market_regime.py / news.py     # 市场制度 & 新闻工具
  ├── adjustment.py / period.py      # 复权 & 周期转换工具
  ├── unit_unify.py / date_align.py  # 数据清洗工具（2个）
  ├── duplicate_merge.py / outlier_filter.py  # 数据清洗工具（2个）
  ├── cross_source_verify.py         # 跨源校验工具
  ├── missing_detect.py              # 缺失检测工具
  ├── cal_math_compute.py            # 计算校验工具
  ├── config_read.py                 # 配置读取工具（运维）
  └── __init__.py                    # all_tools 自动发现机制
```

**23 个 Tool 分类**:
- 数据获取（13个）: OHLCV / Quote / Sentiment / Health / ListSymbols / Macro / Fundamental / F10 / Indicators / TermStructure / Basis / MarketRegime / News
- 数据处理（2个）: Adjustment / Period
- 数据清洗（4个）: UnitUnify / DateAlign / DuplicateMerge / OutlierFilter
- 数据校验（3个）: CrossSourceVerify / MissingDetect / CalMathCompute
- 运维工具（1个）: ConfigRead

### adjustment/ 复权/换月引擎（v1.3.0）

```
adjustment/
  ├── stock_adjustment.py       # 股票前复权/后复权/不复权
  ├── futures_rollover.py       # 期货主力连续合约
  │   ├── 成交量加权换月
  │   ├── 持仓量加权换月
  │   └── 固定日换月
  ├── spread_adjustment.py      # 期货换月价差调整
  │   ├── 前复权调整
  │   ├── 后复权调整
  │   └── 等权调整
  └── __init__.py
```

### resampler/ 周期转换引擎（v1.3.0）

```
resampler/
  ├── resampler.py              # 周期转换主入口
  │   ├── 1m → 5m → 15m → 30m → 60m
  │   ├── 60m → daily → weekly → monthly
  │   └── auto 模式自动选择
  ├── ohlcv_aggregator.py       # OHLCV 正确聚合
  │   ├── Open: 第一个值
  │   ├── High: 最大值
  │   ├── Low: 最小值
  │   ├── Close: 最后一个值
  │   └── Volume: 求和
  ├── auto_detector.py          # auto 模式自动检测
  └── __init__.py
```

### 消费者反馈通道（v1.3.0）

```
issue.py
  ├── IssueType 枚举             # 问题类型枚举
  ├── DataIssue 数据类           # 问题记录
  ├── IssueRegistry 注册表       # 全局问题注册表
  ├── report_issue() API         # 上报问题 API
  ├── 自动降级应对              # 问题触发自动降级
  └── get_health() 集成          # consumer_issues 健康检查字段
```

### cleaning/ 数据清洗模块（v1.3.0）

```
cleaning/
  ├── unit_unify.py             # 单位统一（股/手/万等）
  ├── date_align.py             # 日期对齐（多源时间轴对齐）
  ├── duplicate_merge.py        # 去重合并（重复数据合并）
  ├── outlier_filter.py         # 异常值过滤（3σ / IQR）
  └── __init__.py
```

### validation/ 数据校验模块（v1.3.0）

```
validation/
  ├── weight_score.py           # 权重评分（多源数据加权）
  ├── cross_source.py           # 跨源校验（多源一致性检查）
  ├── missing_detect.py         # 缺失检测（缺失值识别与标记）
  ├── cal_math.py               # 计算校验（数学一致性验证）
  └── __init__.py
```

### collectors/ 采集模块骨架（v1.3.0）

```
collectors/
  ├── web_crawl.py              # 网页爬虫采集骨架
  ├── open_source.py            # 开源数据采集骨架
  ├── local_doc.py              # 本地文档采集骨架
  ├── search.py                 # 搜索采集骨架
  └── __init__.py
```

### operations/ 运维工具模块（v1.3.0）

```
operations/
  ├── crawl_retry.py            # 爬取重试机制
  ├── error_log.py              # 错误日志收集
  ├── config_tools.py           # 配置管理工具
  └── __init__.py
```

## 6. v1.2.0 新增组件

| 组件 | 文件 | 说明 |
|:-----|:-----|:-----|
| indicators/ 技术指标模块 | datacore/indicators/ | FDC 吸收，37+ 基础指标，三层路由体系 |
| QMTProvider | datacore/futures/providers/qmt.py | QMT 迅投数据源（P2，依赖 xtquant） |
| TqSdkProvider | datacore/futures/providers/tqsdk.py | TqSdk 数据源（P6 末位兜底，依赖 tqsdk） |
| WebFallbackProvider | datacore/futures/providers/web_fallback.py | 网页备用数据源（P5） |
| 指标测试 | tests/test_indicators.py | 90 个测试用例（核心指标/TDX 对齐/趋势成熟度） |
| 新期货数据源测试 | tests/test_futures_new_providers.py | 20 个测试用例（QMT/TqSdk/WebFallback） |

### indicators/ 技术指标模块（v1.2.0，FDC 吸收）

```
indicators/
  ├── core.py                # 37+ 基础指标纯 numpy 实现
  ├── tdx_compat.py          # TDX 通达信对齐指标
  ├── legacy_numpy.py        # 旧版兼容实现
  ├── trend_maturity.py      # 趋势成熟度评估
  ├── talib_wrapper.py       # TA-Lib 封装兜底
  └── __init__.py            # 导出 compute_indicators / INDICATOR_NAMES / assess_trend_maturity
```

**三层路由体系**: TDX 对齐 → numpy core → TA-Lib 兜底

**公开 API**:
```python
from datacore.indicators import compute_indicators, INDICATOR_NAMES, assess_trend_maturity
```

### 期货 7 源降级链（v1.2.0 扩展）

```
TdxLc (P0) → EastMoney (P1) → QMT (P2) → ExchangeApi (P3) → ShengYiShe (P4) → WebFallback (P5) → TqSdk (P6)
```

## 7. v1.1.0 新增组件

| 组件 | 文件 | 说明 |
|:-----|:-----|:-----|
| AsyncDataProvider | datacore/api_async.py | 异步双接口，基于 run_in_executor 线程池桥接同步代码 |
| F10 综合报告 | datacore/api_f10.py | get_f10() 聚合期限结构/价差/基差/仓单/持仓排名 |
| core 共享基础设施 | datacore/core/ | types.py + data_freshness.py + __init__.py |
| Phase 1 测试 | tests/test_phase1.py | 28 个测试用例（async/F10/core 全覆盖） |

### AsyncDataProvider（v1.1.0）

```
AsyncDataProvider (异步双接口)
  ├── get_kline_async(symbol, period)    # 异步 K 线获取
  ├── get_quote_async(symbol)            # 异步行情获取
  ├── get_f10_async(symbol)              # 异步 F10 报告
  └── run_in_executor 线程池桥接
       └── 内部调用同步 UnifiedDataProvider 方法
```

### F10 综合报告（v1.1.0）

```
F10Report (数据模型)
  ├── symbol: str                        # 品种代码
  ├── term_structure: TermStructureData  # 期限结构
  ├── spread: SpreadData                 # 跨期价差
  ├── basis: BasisData                   # 基差
  ├── warehouse_receipt: WarehouseReceiptData  # 仓单
  ├── position_ranking: PositionRankingData    # 持仓排名
  └── timestamp: datetime                # 生成时间
```

### core/ 共享基础设施（v1.1.0）

```
core/
  ├── types.py
  │   ├── KlineBar       # K线数据结构（open/high/low/close/volume）
  │   ├── QuoteData      # 行情数据结构（price/volume/bid/ask）
  │   └── FreshnessStatus # 新鲜度状态枚举（FRESH/STALE/EXPIRED）
  ├── data_freshness.py
  │   └── DataFreshnessAssessor  # 数据新鲜度评估器
  └── __init__.py        # 导出核心类型
```

## 8. v1.0.0 新增组件

| 组件 | 文件 | 说明 |
|:-----|:-----|:-----|
| WebSocket 实时行情 | datacore/stream.py | WebSocket 连接管理、自动重连、心跳保活、行情订阅分发 |
| 告警引擎 | datacore/alert.py | AlertEngine + 预置规则 + 3 个通知渠道（日志/文件/Webhook） |
| 性能基准测试 | tests/benchmark_test.py | 8 个基准测试（数据获取/缓存/加工/并发） |
| 安全审计清单 | docs/SECURITY_CHECKLIST.md | 7 项安全检查全部通过（认证/加密/注入/配置/依赖/日志/通信） |

### WebSocket 实时行情（v1.0.0）

```
StreamQuote (数据模型)
  ├── symbol: str              # 品种代码
  ├── price: float             # 最新价
  ├── volume: float            # 成交量
  ├── timestamp: datetime      # 时间戳
  └── exchange: str            # 交易所

WebSocketManager (连接管理)
  ├── connect(url)             # 建立 WebSocket 连接
  ├── subscribe(symbols)       # 订阅品种行情
  ├── on_quote(callback)       # 行情回调注册
  ├── auto_reconnect           # 自动重连（指数退避）
  └── heartbeat                # 心跳保活
```

### 告警引擎（v1.0.0）

```
AlertEngine (告警引擎)
  ├── 预置规则
  │   ├── price_breakout       # 价格突破（涨跌幅超阈值）
  │   ├── volatility_anomaly   # 波动率异常
  │   ├── data_stale           # 数据延迟告警
  │   └── breaker_trip         # 熔断触发告警
  ├── 通知渠道
  │   ├── log_channel          # 日志记录
  │   ├── file_channel         # 文件写入
  │   └── webhook_channel      # Webhook 回调
  └── 规则可配置（阈值/渠道/启用状态）
```

## 9. 数据加工层（v0.3.0 新增，v0.6.0 扩展）

### 情绪加工管线
```
NEWS (Data-Core 采集+分类)
  → SentimentLLMStage (P0, LLM打分, v0.6.0 端到端验证)
  → SentimentRuleStage (P1, 词典法降级)
  → SentimentAggregator (按品种/时间聚合)
  → SENTIMENT (FTS 直接消费)
```

### 基本面 LLM 加工管线（v0.6.0 新增）
```
研报/财报 (Data-Core 采集)
  → FundamentalLLMStage (LLM 摘要提取)
  → 结构化输出
  → FUNDAMENTAL (FTS 直接消费)
```

### 市场制度检测
```
OHLCV (Data-Core 采集)
  → MarketRegimeDetector (趋势/波动率/成交量综合判断)
  → MARKET_STATE (bull/bear/sideways, FTS 直接消费)
```

## 10. Data Source Fallback Chain

### 期货行情降级链（v1.2.0 扩展为 7 源）
- TQ-Local (P0) → 东方财富 (P1) → QMT (P2) → 交易所官方 (P3) → 生意社 (P4) → WebFallback (P5) → TqSdk (P6)

### 期货基本面降级链（v0.5.0 新增）
| 数据类型 | P0 | P1 |
|:---------|:---|:---|
| 基差 | 生意社 | 东方财富（近似算法） |
| 持仓排名 | 交易所官方 | 东方财富 |
| 仓单 | 交易所官方 | 东方财富 |

### A 股降级链（v0.5.0 扩展）
- 腾讯财经 (P0) → 东方财富 (P1) → 国信证券 (P2)

### 宏观数据降级链（v0.5.0 新增）
- 国家统计局 (P0) → 央行 (P1) → 东方财富 (P2)

### 新闻资讯降级链
- 财联社 (P0) → 华尔街见闻 (P1) → 东方财富研报 (P2)

### 情绪数据降级链（v0.3.0 新增，v0.6.0 验证）
- LLM 情绪打分 (P0, PRIMARY) → 规则基线 (P1, DAILY) → Cached (P2)

### WebSocket 降级链（v1.0.0 新增）
- WebSocket 实时行情 (P0) → HTTP 轮询行情 (P1) → 缓存行情 (P2)

### 告警降级链（v1.0.0 新增）
- Webhook 通知 (P0) → 文件写入 (P1) → 日志记录 (P2)

## 11. 核心边界原则

| 原则 | 说明 |
|:-----|:-----|
| **能力导向** | LLM 是 AI 原生项目的基本工具，边界按"能力与职责"划分 |
| **数据归 Data-Core** | 采集 + 加工（含LLM） + 存储 + 服务 + 实时行情 + 告警 |
| **因子归 FTS** | 因子发现 + 评估 + 组合 + 演化 |
| **决策归 FDT** | 辩论 + 风控 + 信号 + 执行 |
| **上下游不可逆** | Data-Core ← FTS ← FDT |
