# Data-Core Code Wiki

> 版本: v1.0.0 | AI-Native 量化数据基础设施
> 更新: 2026-07-19

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [目录结构](#3-目录结构)
4. [模块详解](#4-模块详解)
   - [4.1 config — 统一配置系统](#41-config--统一配置系统)
   - [4.2 models — 数据模型层](#42-models--数据模型层)
   - [4.3 registry — 符号注册表](#43-registry--符号注册表)
   - [4.4 store — 存储层](#44-store--存储层)
   - [4.5 equity — A股数据模块](#45-equity--a股数据模块)
   - [4.6 futures — 期货数据模块](#46-futures--期货数据模块)
   - [4.7 news — 新闻资讯模块](#47-news--新闻资讯模块)
   - [4.8 macro — 宏观数据模块](#48-macro--宏观数据模块)
   - [4.9 processing — 数据加工层](#49-processing--数据加工层)
   - [4.10 breaker — 熔断层](#410-breaker--熔断层)
   - [4.11 metrics — 指标收集](#411-metrics--指标收集)
   - [4.12 api — 统一数据入口](#412-api--统一数据入口)
   - [4.13 cli — 命令行工具](#413-cli--命令行工具)
   - [4.14 stream — WebSocket 实时行情](#414-stream--websocket-实时行情)
   - [4.15 alert — 告警引擎](#415-alert--告警引擎)
5. [数据流与降级链](#5-数据流与降级链)
6. [配置说明](#6-配置说明)
7. [运行与测试](#7-运行与测试)
8. [依赖关系](#8-依赖关系)

---

## 1. 项目概述

**Data-Core** 是一个面向中国期货和证券市场的 AI-Native 量化数据基础设施。专为 LLM 驱动的量化研究场景设计，核心特色包括：

- **数据溯源 (Provenance)**: 每条数据携带 source + grade + freshness 元数据，AI Agent 可自行判断数据可靠性
- **自描述 Schema**: 数据模型使用明确的 dataclass 定义，Python 和 LLM 均可通过结构化反射消费
- **优雅降级 (Graceful Degradation)**: 多源回退链 + 熔断器 + LLM→规则降级，三层保护，永不硬失败
- **数据加工层 (Processing Layer)**: 自包含情绪打分（LLM 优先，规则降级）和市场制度检测能力
- **零外部依赖**: 自包含的 HTTP 数据源，单 `pip install` 即可使用，无需 MCP/Skill/Agent 依赖
- **多后端存储**: 支持 DuckDB（默认）、PostgreSQL、Redis 三种存储后端
- **可观测性**: 健康检查、熔断器状态、指标收集三大支柱，覆盖所有数据源调用

### 数据复权策略

Data-Core 对不同类型的 K 线数据采取不同的复权策略，设计的核心原则是：**Data-Core 统一处理，消费端只声明需求**。

所有复权/换月处理由 Data-Core 的复权引擎完成，消费方通过 `adjustment` 参数指定需求：

| 市场 | 可选 adjustment | 说明 |
|:-----|:----------------|:-----|
| A 股/ETF/可转债/REITs | `"qfq"`（前复权）、`"hfq"`（后复权）、`"none"`（不复权） | 基于除权除息日历自行计算，脱离对 API 参数依赖 |
| 期货 | `"continuous"`（主力连续）、`"continuous_qfq"`（主力连续+前复权）、`"none"`（原始合约） | 主力连续合约拼接（成交量/持仓量/固定日换月） |

**v1.0 时期采用的是"数据源提供什么就返回什么"**的被动策略——A 股的复权由 Tencent/EastMoney 的 API 参数完成，期货换月交由消费方自行处理。**v2.0 升级为 Data-Core 统一复权/换月引擎**，消费方不再感知底层计算逻辑。

```python
# ─── v2.0 用法 ───
dc.get("RB", DataType.OHLCV, adjustment="continuous")       # 期货主力连续
dc.get("600519", DataType.OHLCV, adjustment="qfq")          # A 股前复权
dc.get("600519", DataType.OHLCV, adjustment="hfq")          # A 股后复权
dc.get("600519", DataType.OHLCV, adjustment="none")         # A 股不复权
```

### 周期转换

Data-Core 支持跨周期 K 线转换。消费端只需指定 `period` 参数，Data-Core 自动从最细粒度原始数据重采样到目标周期。

```python
dc.get("RB", DataType.OHLCV, period="daily")                 # 日线（默认）
dc.get("RB", DataType.OHLCV, period="60m")                   # 60 分钟线
dc.get("RB", DataType.OHLCV, period="15m")                   # 15 分钟线
dc.get("RB", DataType.OHLCV, period="weekly")                # 周线
dc.get("RB", DataType.OHLCV, period="monthly")               # 月线
```

| period 值 | 说明 | 聚合规则 |
|:----------|:-----|:---------|
| `"1m"` ~ `"60m"` | 分钟级 | O=first, H=max, L=min, C=last, V=sum |
| `"daily"` | 日线（默认） | 当日所有分钟聚合 |
| `"weekly"` | 周线（周一为起始） | 5 根日线→1 根周线 |
| `"monthly"` | 月线 | 当月日线→1 根月线 |
| `"auto"` | 自动选择最合适周期 | 按数据量自动判断 |

**处理管线**: `原始数据 → 复权/换月引擎 → 周期转换引擎 → 消费端`

**约束**: 只能从细粒度→粗粒度（1min→5min→daily→weekly）。如果请求的周期比 Provider 能提供的最细粒度还细，返回错误+建议。

### 版本演进

| 版本 | 关键交付 |
|:-----|:---------|
| v0.1.0 | 基础架构：models/registry/store/equity/futures/cli |
| v0.2.0 | 新闻模块 + 宏观数据模块 |
| v0.3.0 | 数据加工层：情绪管线（LLM+规则）+ 市场制度检测 |
| v0.4.0 | 工程完善：熔断器、健康检查、指标收集、DuckDB 持久化、CLI 增强、ETF/CB 支持 |
| v0.5.0 | 数据源完善（宏观/期货/A股扩展 + DuckDB缓存 + 多源降级链） |
| v0.6.0 | LLM与智能加工（情绪端到端 + 基本面LLM加工 + 部署文档） |
| v1.0.0 | 生产就绪（WebSocket实时行情 + 告警引擎 + 性能基准 + 安全审计） |

---

## 2. 整体架构

### 数据流（AI-Native 视图）

```
AI Agent / 策略
      |
      | get(symbol, data_type) --> DataPayload { data + grade + source + meta }
      v
UnifiedDataProvider (api.py)
      |
      ├── Breaker (熔断层, CLOSED/OPEN/HALF_OPEN)
      ├── MetricsCollector (指标收集)
      ├── futures/          TQ-Local --> EastMoney --> ExchangeAPI --> ShengYiShe
      │     56+ 合约品种, 合约链/期限结构/价差/基差/持仓/仓单
      |
      ├── equity/           Tencent --> EastMoney --> Guosen
      │     A股/ETF/可转债/REITs, K线/行情/财务
      |
      ├── news/             财联社 --> 华尔街见闻 --> 东方财富研报
      │     新闻采集 + 关键词分类 (macro/policy/industry/company)
      |
      ├── macro/            国家统计局 --> 中国人民银行 --> 东方财富
      │     CPI/PPI/GDP/PMI/M2/LPR 等宏观指标
      |
      ├── processing/       数据加工层
      │     ├── SentimentLLM --> RuleBase (降级)
      │     ├── MarketRegimeDetector (bull/bear/sideways)
      │     └── FundamentalLLM (研报摘要 + 财报提取)
      |
      ├── alert/            告警引擎 (v1.0.0)
      |     └── AlertEngine: 规则/阈值/模式匹配
      |
      ├── stream/           WebSocket实时行情 (v1.0.0)
      |     └── StreamQuote: WebSocket --> 全双工推送
      |
      ├── store/            MemoryCache + DuckDB/PostgreSQL/Redis
      |     └── DuckDB 现已完全接入 L2 缓存层
      ├── registry/         SymbolRegistry (56+ 期货品种)
      ├── config/           DataCoreConfig (环境变量 + YAML)
      └── models/           DataType / MarketType / SourceGrade / DataPayload
```

### AI 可消费的数据契约

每个 API 响应返回 `DataPayload`，一个对 AI 友好的结构化信封：

```python
@dataclass
class DataPayload:
    symbol: str          # 查询符号
    data_type: DataType  # 数据类型
    market: MarketType   # 市场类型
    data: Any            # 实际数据 (KlineData, SentimentData 等)
    source: str          # 数据来源 ("tencent", "llm", "rule_fallback")
    grade: SourceGrade   # PRIMARY / DAILY / CACHED / STALE / UNAVAILABLE
    collected_at: float  # 采集时间
    errors: list[str]    # 遇到的错误
    warnings: list[str]  # 警告信息
```

AI Agent 据此决策：
- `PRIMARY` 数据可用于交易决策
- `DAILY`/`CACHED` 数据可用于分析
- `STALE`/`UNAVAILABLE` 应跳过或触发人工通知

### 设计原则

| 原则 | 说明 |
|------|------|
| **AI Native** | 所有数据返回携带 provenance 元数据 (source, grade, freshness)，供 LLM 决策 |
| **零外部依赖** | 自包含 HTTP 数据源，单 pip install 即可使用 |
| **优雅降级** | 多源回退 + 熔断器 + 异常捕获，三层保护，永不硬失败 |
| **市场无关** | 统一 API 覆盖期货、股票、ETF、可转债、REITs |
| **配置优先** | 禁止硬编码，所有配置通过环境变量或 YAML 文件注入 |
| **边界清晰** | 数据归 Data-Core，因子归 FTS，决策归 FDT，上下游不可逆 |

---

## 3. 目录结构

```
data-core/
├── datacore/                      # 主包
│   ├── __init__.py                # 包入口, 导出 UnifiedDataProvider
│   ├── api.py                     # UnifiedDataProvider — 统一数据入口
│   ├── cli.py                     # 命令行工具 (list/status/quote)
│   ├── config.py                  # DataCoreConfig — 统一配置系统（单例）
│   ├── breaker.py                 # Breaker — 带状态熔断器 (v0.4.0)
│   ├── health.py                  # HealthChecker — 数据源健康检查 (v0.4.0)
│   ├── metrics.py                 # MetricsCollector — 指标收集框架 (v0.4.0)
│   ├── alert.py                   # AlertEngine — 告警引擎 (v1.0.0)
│   ├── stream.py                  # StreamQuote — WebSocket 实时行情 (v1.0.0)
│   │
│   ├── models/                    # 数据模型层
│   │   ├── __init__.py
│   │   ├── enums.py               # DataType / MarketType / SourceGrade 枚举
│   │   ├── ohlcv.py               # KBar / KlineData / QuoteData 结构
│   │   ├── payload.py             # DataPayload — 统一数据载荷信封
│   │   └── futures.py             # 期货数据模型 (合约链/期限结构/价差/基差等)
│   │
│   ├── registry/                  # 符号注册表
│   │   ├── __init__.py
│   │   └── symbol_registry.py     # SymbolEntry / SymbolRegistry (56+ 品种)
│   │
│   ├── store/                     # 存储层
│   │   ├── __init__.py
│   │   ├── cache.py               # MemoryCache — TTL 内存缓存
│   │   ├── duckdb.py              # DuckDBStore — DuckDB 持久化（默认，已接入 L2 缓存）
│   │   ├── postgres.py            # PostgresStore — PostgreSQL 持久化
│   │   └── redis.py               # RedisStore — Redis 缓存
│   │
│   ├── equity/                    # A股数据模块
│   │   ├── __init__.py
│   │   ├── equity_provider.py     # EquityDataProvider — A股数据入口
│   │   ├── financial.py           # 财务评分工具
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py            # EquityDataSource 抽象基类
│   │       ├── tencent.py         # TencentProvider — 腾讯数据源 (P0)
│   │       ├── eastmoney.py       # EastMoneyEquityProvider — 东方财富 (P1)
│   │       └── guosen.py          # GuosenProvider — 国信证券 (P2, v0.5.0)
│   │
│   ├── futures/                   # 期货数据模块
│   │   ├── __init__.py
│   │   ├── futures_provider.py    # FuturesDataProvider — 期货数据入口
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py            # FuturesDataSource 抽象基类
│   │       ├── tdx_lc.py          # TdxLcProvider — 通达信本地 (P0)
│   │       ├── eastmoney.py       # EastMoneyFuturesProvider — 东方财富 (P1)
│   │       ├── exchange_api.py    # ExchangeApiProvider — 交易所官方 API (P2, v0.5.0)
│   │       └── shengyishe.py      # ShengYiSheProvider — 生意社现货/基差 (P3, v0.5.0)
│   │
│   ├── news/                      # 新闻资讯模块 (v0.2.0)
│   │   ├── __init__.py
│   │   ├── news_provider.py       # NewsDataProvider — 新闻数据入口
│   │   ├── classifier.py          # NewsClassifier — 关键词分类器
│   │   ├── models.py              # NewsItem / NewsData 模型
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py            # NewsDataSource 抽象基类
│   │       ├── cls.py             # ClsProvider — 财联社 (P0)
│   │       ├── wallstreet_cn.py   # WallStreetCnProvider — 华尔街见闻 (P1)
│   │       └── eastmoney_research.py  # EastMoneyResearchProvider — 东方财富研报 (P2)
│   │
│   ├── macro/                     # 宏观数据模块 (v0.2.0)
│   │   ├── __init__.py
│   │   ├── macro_provider.py      # MacroDataProvider — 宏观数据入口（3 源）
│   │   ├── models.py              # 宏观数据模型
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py            # MacroDataSource 抽象基类
│   │       ├── eastmoney_macro.py # EastMoneyMacroProvider — 东方财富宏观 (P2)
│   │       ├── national_bureau.py # NationalBureauProvider — 国家统计局 (P0, v0.5.0)
│   │       └── pboc.py            # PboCProvider — 中国人民银行 (P1, v0.5.0)
│   │
│   ├── processing/                # 数据加工层 (v0.3.0)
│   │   ├── __init__.py
│   │   ├── base.py                # ProcessingStage 抽象基类
│   │   ├── models.py              # SentimentItem / SentimentData / MarketStateData
│   │   ├── market_regime.py       # MarketRegimeDetector (bull/bear/sideways)
│   │   ├── fundamental/           # 基本面LLM加工 (v0.6.0)
│   │   │   ├── __init__.py
│   │   │   └── fundamental_llm.py # FundamentalLLMStage — 研报摘要 + 财报提取
│   │   └── sentiment/
│   │       ├── __init__.py
│   │       ├── sentiment_rule.py  # SentimentRuleStage — 词典法基线（零成本）
│   │       ├── sentiment_llm.py   # SentimentLLMStage — LLM 打分（含降级）
│   │       └── sentiment_aggregator.py  # SentimentAggregator — 情绪聚合器
│
├── config/
│   └── settings.yaml              # 配置文件（支持环境变量覆盖）
│
├── tests/                         # 测试目录 (26 个文件, 724+ 用例)
│   ├── conftest.py                # 共享 Fixture 和 Mock 配置
│   ├── test_api.py                # UnifiedDataProvider 路由测试
│   ├── test_alert.py              # 告警引擎测试 (v1.0.0)
│   ├── test_breaker.py            # 熔断器状态转换/超时/半开探测
│   ├── test_cli.py                # 命令行工具测试
│   ├── test_duckdb.py             # DuckDB 持久化缓存测试 (v0.5.0)
│   ├── test_equity.py             # A股 Provider 集成测试
│   ├── test_equity_mock.py        # A股 Provider Mock 测试
│   ├── test_exchange_api.py       # ExchangeAPI 提供商测试 (v0.5.0)
│   ├── test_futures.py            # 期货 Provider 集成测试
│   ├── test_futures_mock.py       # 期货 Provider Mock 测试
│   ├── test_futures_models.py     # 期货数据模型测试
│   ├── test_guosen.py             # 国信证券提供商测试 (v0.5.0)
│   ├── test_health.py             # 健康检查接口测试
│   ├── test_macro.py              # 宏观数据模型测试
│   ├── test_macro_mock.py         # 宏观数据源 Mock 测试 (v0.5.0)
│   ├── test_metrics.py            # 指标收集框架测试
│   ├── test_models.py             # 枚举/Payload/K线数据结构测试
│   ├── test_national_bureau.py    # 国家统计局提供商测试 (v0.5.0)
│   ├── test_news.py               # 新闻分类器 + 新闻模型测试
│   ├── test_pboc.py               # 中国人民银行提供商测试 (v0.5.0)
│   ├── test_processing.py         # 数据加工层（情绪管线 + 市场制度）测试
│   ├── test_fundamental.py        # 基本面LLM加工测试 (v0.6.0)
│   ├── test_registry.py           # 符号注册表测试
│   ├── test_shengyishe.py         # 生意社提供商测试 (v0.5.0)
│   ├── test_store.py              # 缓存测试
│   └── test_stream.py             # WebSocket 实时行情测试 (v1.0.0)
│
├── docs/
│   └── harness/                   # HARNESS 工程规范文档 (09 份)
│       ├── 01-architecture.md     # 架构文档
│       ├── 02-lifecycle.md        # 阶段定义
│       ├── 03-configuration.md    # 配置项
│       ├── 04-resilience.md       # 降级策略
│       ├── 05-observability.md    # 可观测性
│       ├── 06-testing.md          # 测试用例
│       ├── 07-operations.md       # 版本历史
│       ├── 08-gap-analysis.md     # 差距管理
│       └── 09-advancement-plan.md # 晋级计划
│
├── pyproject.toml                 # 项目元数据与构建配置
├── CODE_WIKI.md                   # 项目说明书 (本文件，动态文档)
├── ARCHITECTURE.md                # 架构设计文档
├── README.md                      # 项目 README
├── CLAUDE.md                      # AI 编码行为准则
├── .pylintrc                      # Pylint 配置
└── .gitignore
```

---

## 4. 模块详解

### 4.1 config — 统一配置系统

**路径**: [datacore/config.py](file:///d:/Programs/data-core/datacore/config.py)

提供统一的配置管理，支持环境变量和 YAML 文件两种配置方式，优先级从高到低：

1. **环境变量**: `DATACORE_*` 前缀
2. **YAML 文件**: `config/settings.yaml` 或 `~/.datacore/settings.yaml`
3. **代码默认值**: 硬编码的默认值（仅作为兜底）

#### DataCoreConfig 类

| 属性 | 类型 | 环境变量 | YAML 路径 | 默认值 | 说明 |
|------|------|----------|-----------|--------|------|
| `tdx_url` | str | `DATACORE_SOURCES_TDX_LC_URL` | `sources.tdx_lc.url` | `http://127.0.0.1:17709/` | 通达信本地服务地址 |
| `tdx_timeout` | int | `DATACORE_SOURCES_TDX_LC_TIMEOUT` | `sources.tdx_lc.timeout` | `3` | 通达信请求超时(秒) |
| `guosen_api_key` | Optional[str] | `DATACORE_SOURCES_GUOSEN_API_KEY` | `sources.guosen.api_key` | `None` | 国信证券 API-KEY（敏感） |
| `guosen_url` | str | `DATACORE_SOURCES_GUOSEN_URL` | `sources.guosen.url` | `https://api.guosen.com.cn/` | 国信证券 API 地址 |
| `guosen_timeout` | int | `DATACORE_SOURCES_GUOSEN_TIMEOUT` | `sources.guosen.timeout` | `5` | 国信证券请求超时(秒) |
| `cache_ttl` | int | `DATACORE_STORE_CACHE_TTL` | `store.cache_ttl` | `3600` | 缓存 TTL(秒) |
| `duckdb_path` | str | `DATACORE_STORE_DUCKDB_PATH` | `store.duckdb_path` | `~/.datacore/datacore.db` | DuckDB 数据库路径 |
| `pg_dsn` | Optional[str] | `DATACORE_STORE_POSTGRESQL_DSN` | `store.postgresql.dsn` | `None` | PostgreSQL 连接 DSN |
| `redis_url` | Optional[str] | `DATACORE_STORE_REDIS_URL` | `store.redis.url` | `None` | Redis 连接 URL |
| `store_backend` | str | `DATACORE_STORE_BACKEND` | `store.backend` | `duckdb` | 默认存储后端 |

#### get_config() 函数

获取全局配置实例（单例模式）：

```python
from datacore.config import get_config

config = get_config()
print(config.tdx_url)
print(config.store_backend)
```

#### 安全注意事项

- **禁止硬编码敏感信息**: 所有密码、密钥、API Key 必须通过环境变量注入
- **YAML 文件不应提交到版本控制**: 生产环境配置应存储在安全位置（如 `~/.datacore/settings.yaml`）
- **环境变量优先**: 敏感配置应通过环境变量覆盖，避免在 YAML 文件中明文存储

---

### 4.2 models — 数据模型层

**路径**: [datacore/models/](file:///d:/Programs/data-core/datacore/models/)

提供系统中所有核心数据类型定义，是整个项目的契约层。

#### enums.py — 枚举定义

**路径**: [datacore/models/enums.py](file:///d:/Programs/data-core/datacore/models/enums.py)

| 枚举 | 字段 | 说明 |
|------|------|------|
| `DataType` | `OHLCV`, `QUOTE`, `TECHNICAL`, `FINANCIAL`, `FUNDAMENTAL`, `MACRO`, `NEWS`, `ANNOUNCEMENT`, `SENTIMENT`, `MARKET_STATE`, `FUTURES_CONTRACT_CHAIN`, `FUTURES_TERM_STRUCTURE`, `FUTURES_SPREAD`, `FUTURES_BASIS`, `FUTURES_POSITION`, `FUTURES_WAREHOUSE_RECEIPT`, `ETF_NAV`, `ETF_PREMIUM`, `ETF_FUND_FLOW`, `CB_CONVERSION`, `CB_TERMS`, `CB_PURE_BOND` | FTS 分类法，按数据结构特征划分数据类型。SENTIMENT/MARKET_STATE 由 Data-Core 加工层产出 |
| `MarketType` | `FUTURES`, `STOCK`, `ETF`, `CB`(可转债), `REIT` | 支持的市场类型 |
| `SourceGrade` | `PRIMARY` > `DAILY` > `CACHED` > `STALE` > `UNAVAILABLE` | 数据质量等级，从高到低排列 |

`SourceGrade` 是 AI-Native 设计的核心：AI Agent 根据等级决定数据的使用策略。

| Grade | 说明 | 使用建议 |
|:------|:-----|:---------|
| `PRIMARY` | 官方数据源 / LLM 打分 | 可用于交易决策 |
| `DAILY` | 第三方数据 / 规则基线 | 可用于因子计算 |
| `CACHED` | 缓存数据 | 可用于分析，需标注 |
| `STALE` | 过期数据 | 低权重使用 |
| `UNAVAILABLE` | 所有源不可用 | 因子降级或跳过 |

#### ohlcv.py — K线与行情数据结构

**路径**: [datacore/models/ohlcv.py](file:///d:/Programs/data-core/datacore/models/ohlcv.py)

- **`KBar`**: 单根 K 线数据
  - 字段: `date`, `open`, `high`, `low`, `close`, `volume`, `amount`, `open_interest`, `settlement`
  - `open_interest`(持仓量) 和 `settlement`(结算价) 为期货特有字段，可选

- **`KlineData`**: K 线数据集
  - 字段: `symbol`, `period`, `bars: list[KBar]`, `source`, `contract`
  - 聚合多根 KBar，附带数据源和合约信息

- **`QuoteData`**: 实时行情快照
  - 字段: `symbol`, `source`, `last_price`, `open`, `high`, `low`, `pre_close`, `volume`, `amount`, `bid_price`, `ask_price`, `change_pct`, `update_time`
  - 包含五档买卖盘口

#### futures.py — 期货数据模型

**路径**: [datacore/models/futures.py](file:///d:/Programs/data-core/datacore/models/futures.py)

| 数据结构 | 字段 | 说明 |
|:---------|:-----|:-----|
| `ContractInfo` | symbol, name, expiry_date, exchange, ... | 单个合约信息 |
| `ContractChain` | symbol, contracts: list[ContractInfo] | 合约链（同一品种所有可交易合约） |
| `TermStructurePoint` | contract, price, days_to_expiry | 期限结构上的一个点 |
| `TermStructure` | symbol, points: list[TermStructurePoint] | 完整的期限结构曲线 |
| `SpreadData` | near_contract, far_contract, spread_series | 跨期价差数据 |
| `BasisData` | futures_price, spot_price, basis, basis_rate | 基差数据（现货-期货价差） |
| `PositionRankItem` | rank, broker, long_qty, short_qty, net_qty | 期货公司持仓排名条目 |
| `PositionRankData` | symbol, date, long_ranks, short_ranks | 持仓排名数据 |
| `WarehouseReceiptData` | symbol, warehouse, receipt_qty, change, total_receipts | 仓单数据 |

#### payload.py — 统一数据载荷信封

**路径**: [datacore/models/payload.py](file:///d:/Programs/data-core/datacore/models/payload.py)

- **`DataPayload`**: 所有 API 返回的统一信封
  - 字段: `symbol`, `data_type`, `market`, `data`, `source`, `grade`, `collected_at`, `meta`, `errors`, `warnings`
  - 属性: `available` — 检查数据是否可用 (`grade != UNAVAILABLE`)

```python
@dataclass
class DataPayload:
    symbol: str
    data_type: DataType
    market: MarketType
    data: Any = None          # 实际数据 (KlineData / SentimentData / dict 等)
    source: str = ""          # 数据源名称
    grade: SourceGrade = SourceGrade.UNAVAILABLE
    collected_at: float = 0.0 # 采集时间戳
    meta: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.grade != SourceGrade.UNAVAILABLE
```

---

### 4.3 registry — 符号注册表

**路径**: [datacore/registry/](file:///d:/Programs/data-core/datacore/registry/)

负责符号解析和市场路由，是 `UnifiedDataProvider` 判断"请求属于哪个市场"的依据。

#### SymbolEntry

单个符号条目的数据类：
- `symbol`: 符号代码 (如 `"RB"`, `"600519"`)
- `name`: 中文名称 (如 `"螺纹钢"`)
- `market`: 所属市场 (`MarketType`)
- `sector`: 所属板块/行业
- `is_active`: 是否活跃

#### SymbolRegistry

**路径**: [datacore/registry/symbol_registry.py](file:///d:/Programs/data-core/datacore/registry/symbol_registry.py)

核心功能：
- `__init__()`: 初始化时调用 `_init_builtin()` 注册 56 个内置期货品种
- `_init_builtin()`: 硬编码内置期货品种表，按行业板块分组：

| 板块 | 品种 |
|:-----|:-----|
| **黑色系** | RB(螺纹钢), HC(热卷), I(铁矿石), J(焦炭), JM(焦煤), SF(硅铁), SM(锰硅) |
| **能源链** | SC(原油), LU(低硫燃油), FU(燃油), BU(沥青), PG(液化气), PX(对二甲苯) |
| **聚酯链** | TA(PTA), PF(短纤), EG(乙二醇), EB(苯乙烯) |
| **塑化链** | V(PVC), PP(聚丙烯), L(聚乙烯), MA(甲醇) |
| **化工** | SA(纯碱), UR(尿素), SH(烧碱) |
| **有色金属** | CU(沪铜), AL(沪铝), ZN(沪锌), PB(沪铅), NI(沪镍), SN(沪锡), AO(氧化铝), SS(不锈钢) |
| **贵金属** | AU(黄金), AG(白银) |
| **油脂油料** | A(豆一), B(豆二), M(豆粕), Y(豆油), P(棕榈油), OI(菜油), RM(菜粕), PK(花生) |
| **农产品** | C(玉米), CS(淀粉), SR(白糖), CF(棉花), JD(鸡蛋), LH(生猪) |
| **建材化工** | FG(玻璃), RU(橡胶), NR(20号胶), BR(丁二烯胶), SP(纸浆) |
| **新能源** | LC(碳酸锂), SI(工业硅) |
| **航运** | EC(欧线集运) |

- `register(symbol, name, market, sector, is_active)`: 动态注册新符号
- `resolve(symbol)`: 解析符号，返回 `SymbolEntry` 或 `None`
- `resolve_market(symbol)`: 解析符号所属市场
- `list_by_market(market)`: 按市场列举符号
- `list_all()`: 列举所有符号

> **注意**: A 股/ETF/可转债等非期货品种未预注册到注册表中。注册表仅管理期货品种的静态列表，A股符号通过代码前缀 (`6`=沪市, `0`/`3`=深市) 在 Provider 层动态识别。

---

### 4.4 store — 存储层

**路径**: [datacore/store/](file:///d:/Programs/data-core/datacore/store/)

提供热数据内存缓存和冷数据持久化能力，支持三种后端：

| 后端 | 文件 | 默认 | 适用场景 |
|------|------|------|----------|
| MemoryCache | cache.py | 是 | 进程内热缓存，零依赖 |
| DuckDBStore | duckdb.py | 是 | 本地冷数据持久化，OLAP 优化 |
| PostgresStore | postgres.py | 否 | 分布式部署，跨进程共享 |
| RedisStore | redis.py | 否 | 热缓存共享，跨进程失效通知 |

#### MemoryCache

**路径**: [datacore/store/cache.py](file:///d:/Programs/data-core/datacore/store/cache.py)

进程内 TTL 字典缓存，用于热数据加速：

| 方法 | 说明 |
|------|------|
| `get(key)` | 获取缓存值，过期返回 None |
| `set(key, value, ttl)` | 设置缓存值，支持自定义 TTL |
| `invalidate(key)` | 使单个键失效 |
| `purge()` | 清理所有过期键，返回清理数量 |
| `clear()` | 清空整个缓存 |

- 使用 `pickle` 序列化存储值
- 默认 TTL: 从配置系统获取（默认 3600 秒）

#### DuckDBStore

**路径**: [datacore/store/duckdb.py](file:///d:/Programs/data-core/datacore/store/duckdb.py)

DuckDB 持久化存储引擎，用于冷数据持久化（默认后端）：
- `init_schema()`: 创建三张表（幂等操作）
  - `kline_cache`: K线缓存 (PK: symbol, period, date)
  - `quote_cache`: 行情快照缓存
  - `macro_cache`: 宏观数据缓存 (PK: indicator, date)
- `store_kline(symbol, period, bars)`: 批量存储 K 线数据
- `load_kline(symbol, period, days)`: 加载 K 线数据（按 date DESC）
- `store_quote(symbol, quote)`: 存储行情快照
- `load_quote(symbol)`: 加载最近行情快照
- `store_macro(indicator, date, value)`: 存储宏观指标值
- `load_macro(indicator, limit)`: 加载宏观指标数据
- `close()`: 关闭连接
- 数据库路径从配置系统获取

> **注意**: DuckDB 目前已实现 schema 和 store/load 方法，但尚未接入 UnifiedDataProvider 缓存层（列为 G10 差距，计划 v0.5.0 完成）

#### PostgresStore

**路径**: [datacore/store/postgres.py](file:///d:/Programs/data-core/datacore/store/postgres.py)

PostgreSQL 持久化存储引擎（可选后端）：
- `init_schema()`: 创建四张表（幂等操作），包含 `datacore_cache` 用于通用缓存
- 缓存接口: `cache_get`, `cache_set`, `cache_invalidate`, `cache_purge`
- 配置方式: 环境变量 `DATACORE_STORE_POSTGRESQL_DSN` 或 YAML 文件
- 可选依赖: `psycopg2-binary`

#### RedisStore

**路径**: [datacore/store/redis.py](file:///d:/Programs/data-core/datacore/store/redis.py)

Redis 缓存存储引擎（可选后端）：
- 缓存接口: `cache_get`, `cache_set`, `cache_invalidate`, `cache_purge`
- 支持跨进程失效广播（通过 Pub/Sub）
- 配置方式: 环境变量 `DATACORE_STORE_REDIS_URL` 或 YAML 文件
- 可选依赖: `redis`

#### build_*_store() 函数

`build_postgres_store()` 和 `build_redis_store()` 函数提供安全的后端构造：
- 如果依赖未安装或配置未设置，返回 `None`
- 不会抛出异常，保证主流程不会因可选后端不可用而失败

---

### 4.5 equity — A股数据模块

**路径**: [datacore/equity/](file:///d:/Programs/data-core/datacore/equity/)

提供 A股、ETF、可转债、REITs 的统一数据获取。

#### EquityDataProvider

**路径**: [datacore/equity/equity_provider.py](file:///d:/Programs/data-core/datacore/equity/equity_provider.py)

A 股数据统一入口，维护多源降级链：
- 数据源列表: `[TencentProvider(), EastMoneyEquityProvider(), GuosenProvider()]`
- `get(symbol, data_type, params, market)`: 按优先级遍历数据源，第一个成功返回的即为结果
- 所有源都失败时返回 `UNAVAILABLE` 级别的 `DataPayload`

#### EquityDataSource 抽象基类

**路径**: [datacore/equity/providers/base.py](file:///d:/Programs/data-core/datacore/equity/providers/base.py)

| 属性/方法 | 说明 |
|-----------|------|
| `name` | 数据源名称 |
| `priority` | 优先级 (0=最高) |
| `supported_types` | 支持的数据类型集合 |
| `supported_markets` | 支持的市场类型 (默认: STOCK, ETF, CB, REIT) |
| `fetch(symbol, data_type, params)` | 抽象方法 — 获取数据 |
| `check_available()` | 检查数据源是否可用 |

#### TencentProvider — P0 源

**路径**: [datacore/equity/providers/tencent.py](file:///d:/Programs/data-core/datacore/equity/providers/tencent.py)

腾讯公开 API，A股首选数据源：
- 优先级: 0 (最高)
- 支持类型: `OHLCV`, `QUOTE`
- 核心方法:
  - `_fetch_quote(symbol)`: 通过 `qt.gtimg.cn` 获取实时行情
  - `_fetch_kline(symbol, params)`: 通过 `web.ifzq.gtimg.cn` 获取 K 线（前复权）
- 辅助函数:
  - `_detect_market_code(symbol)`: 根据代码前缀 (`6`=沪, `0`/`3`=深) 判断市场
  - `_parse_tencent_quote(text, symbol)`: 解析腾讯行情文本协议
  - `_f(v)`: 安全类型转换

#### EastMoneyEquityProvider — P1 源

**路径**: [datacore/equity/providers/eastmoney.py](file:///d:/Programs/data-core/datacore/equity/providers/eastmoney.py)

东方财富公开 API，A股备用数据源：
- 优先级: 1
- 支持类型: `OHLCV`, `FINANCIAL`, `MACRO`
- 核心方法:
  - `_fetch_kline(symbol, params)`: 通过 `push2his.eastmoney.com` 获取 K 线（前复权，参数 `fqt=1`）
  - `_fetch_financial(symbol)`: 获取 PE/PB 等财务指标
  - `_fetch_macro()`: 获取 PMI 等宏观数据
- 辅助函数: `_f(v)` — 安全类型转换

#### GuosenProvider — P2 源 (v0.5.0)

**路径**: [datacore/equity/providers/guosen.py](file:///d:/Programs/data-core/datacore/equity/providers/guosen.py)

国信证券 API，A股第三方数据源：
- 优先级: 2
- 支持类型: `OHLCV`, `QUOTE`
- 需要配置 `DATACORE_SOURCES_GUOSEN_API_KEY`（敏感信息，通过环境变量注入）
- 核心方法:
  - `_fetch_kline(symbol, params)`: 通过国信证券 API 获取 K 线
  - `_fetch_quote(symbol)`: 获取实时行情
  - `check_available()`: 检查 API-KEY 是否已配置

#### financial.py — 财务评分工具

**路径**: [datacore/equity/financial.py](file:///d:/Programs/data-core/datacore/equity/financial.py)

`calc_financial_score(fin)`: 简单财务评分计算
- `value_score`: 基于 PE/PB 的估值评分
- `growth_score`: (预留)
- `quality_score`: (预留)
- `composite`: 综合评分

---

### 4.6 futures — 期货数据模块

**路径**: [datacore/futures/](file:///d:/Programs/data-core/datacore/futures/)

提供中国期货市场 56+ 个品种的统一数据获取。

#### FuturesDataProvider

**路径**: [datacore/futures/futures_provider.py](file:///d:/Programs/data-core/datacore/futures/futures_provider.py)

期货数据统一入口，维护多源降级链：
- 数据源列表: `[TdxLcProvider(), EastMoneyFuturesProvider(), ExchangeApiProvider(), ShengYiSheProvider()]`
- `get(symbol, data_type, params)`: 按数据类型路由

| 数据类型 | 内部方法 | 说明 |
|:---------|:---------|:-----|
| `OHLCV` | `_get_kline()` | K 线数据 |
| `QUOTE` | `_get_quote()` | 实时行情 |
| `FUTURES_CONTRACT_CHAIN` | `_get_contract_chain()` | 合约链 |
| `FUTURES_TERM_STRUCTURE` | `_get_term_structure()` | 期限结构 |
| `FUTURES_SPREAD` | `_get_spread()` | 跨期价差 |
| `FUTURES_BASIS` | `_get_basis()` | 基差 |
| `FUTURES_POSITION` | `_get_position_rank()` | 持仓排名 |
| `FUTURES_WAREHOUSE_RECEIPT` | `_get_warehouse_receipts()` | 仓单 |

- 降级逻辑: 按优先级遍历源，第一个成功返回的赋予 `PRIMARY` 等级，后续回退源返回 `DAILY` 等级
- 所有源都失败时返回 `UNAVAILABLE` 级别的 `DataPayload`

#### FuturesDataSource 抽象基类

**路径**: [datacore/futures/providers/base.py](file:///d:/Programs/data-core/datacore/futures/providers/base.py)

| 属性/方法 | 说明 |
|-----------|------|
| `name` | 数据源名称 |
| `priority` | 优先级 |
| `supported_types` | 支持的数据类型集合 |
| `fetch_kline(symbol, period, days)` | 抽象方法 — 获取 K 线 |
| `fetch_quote(symbol)` | 抽象方法 — 获取行情 |
| `fetch_contract_chain(symbol, ...)` | 获取合约链 |
| `fetch_term_structure(symbol)` | 获取期限结构 |
| `fetch_spread(symbol, near, far, ...)` | 获取价差 |
| `fetch_basis(symbol)` | 获取基差 |
| `fetch_position_rank(symbol)` | 获取持仓排名 |
| `fetch_warehouse_receipts(symbol)` | 获取仓单 |
| `check_available()` | 检查数据源是否可用 |

#### TdxLcProvider — P0 源

**路径**: [datacore/futures/providers/tdx_lc.py](file:///d:/Programs/data-core/datacore/futures/providers/tdx_lc.py)

通达信本地 HTTP 服务 (TQ-Local)，期货首选数据源：
- 优先级: 0 (最高)
- 支持类型: `OHLCV`, `QUOTE`, `TECHNICAL`
- 配置方式: 从统一配置系统获取 URL 和超时时间
- 通信方式: JSON-RPC over HTTP
- 合约解析: `_load_contracts()` 通过 `get_stock_list` API 获取合约列表，提取字母前缀作为品种代码
- K 线周期映射: `{"daily": "1d", "60m": "60m", "120m": "120m", "240m": "240m", "weekly": "1w"}`
- 关键方法:
  - `_post(method, params)`: JSON-RPC 调用
  - `_resolve_contract(symbol)`: 品种代码 -> 具体合约代码
  - `fetch_kline(symbol, period, days)`: 获取 K 线（含持仓量）
  - `fetch_quote(symbol)`: 获取实时行情快照

#### EastMoneyFuturesProvider — P1 源

**路径**: [datacore/futures/providers/eastmoney.py](file:///d:/Programs/data-core/datacore/futures/providers/eastmoney.py)

东方财富公开 API，期货备用数据源：
- 优先级: 1
- 支持类型: `OHLCV`
- 与 A 股 EastMoney 类似，但 secid 使用 `CF.{symbol}` 格式
- `fetch_quote()` 返回 None（不支持期货行情）

#### ExchangeApiProvider — P2 源 (v0.5.0)

**路径**: [datacore/futures/providers/exchange_api.py](file:///d:/Programs/data-core/datacore/futures/providers/exchange_api.py)

交易所官方 API，期货第三方数据源：
- 优先级: 2
- 支持类型: `OHLCV`, `FUTURES_CONTRACT_CHAIN`
- 访问交易所官方行情接口（如上期所、大商所、郑商所、中金所）
- 数据权威性高，但受限于交易所访问频率限制
- 核心方法:
  - `_fetch_kline(symbol, params)`: 获取交易所官方 K 线
  - `_fetch_contract_chain(symbol)`: 获取交易所官方合约链

#### ShengYiSheProvider — P3 源 (v0.5.0)

**路径**: [datacore/futures/providers/shengyishe.py](file:///d:/Programs/data-core/datacore/futures/providers/shengyishe.py)

生意社公开 API，现货/基差数据源：
- 优先级: 3
- 支持类型: `FUTURES_BASIS`
- 提供大宗商品的现货价格和基差数据
- 核心方法:
  - `fetch_basis(symbol)`: 获取品种基差（现货-期货价差）
  - `_fetch_spot_price(symbol)`: 获取现货价格

---

### 4.7 news — 新闻资讯模块

**路径**: [datacore/news/](file:///d:/Programs/data-core/datacore/news/)

新闻类数据（快讯、研报）的统一抽象。采集 + 分类加工，产出携带 tags 的 NEWS 数据。

#### NewsDataProvider

**路径**: [datacore/news/news_provider.py](file:///d:/Programs/data-core/datacore/news/news_provider.py)

新闻数据统一入口，维护多源降级链：
- 数据源: `[ClsProvider(), WallStreetCnProvider(), EastMoneyResearchProvider()]`
- `get(symbol, params)`: 获取新闻数据，自动分类打 tags

| 参数 | 默认值 | 说明 |
|:-----|:-------|:-----|
| `symbol` | None | 品种代码，None 表示全市场 |
| `days` | 7 | 获取最近几天的新闻 |
| `categories` | None | 分类过滤（如 ["macro", "industry"]）|
| `limit` | 50 | 返回条数上限 |

降级链: **财联社 (P0)** → **华尔街见闻 (P1)** → **东方财富研报 (P2)**

#### NewsClassifier

**路径**: [datacore/news/classifier.py](file:///d:/Programs/data-core/datacore/news/classifier.py)

基于关键词的新闻分类器，属于数据加工层（不涉及情绪打分）：

| 分类 | 关键词举例 |
|:-----|:-----------|
| `macro` | 宏观, GDP, CPI, PPI, PMI, M2, LPR, 央行, 美联储, 通胀, 衰退 |
| `policy` | 政策, 监管, 新规, 证监会, 发改委, 上调, 下调, 批准 |
| `industry` | 产业, 产能, 产量, 库存, 供需, 减产, 增产, 检修 |
| `company` | 公司, 业绩, 财报, 营收, 利润, 分红, 回购, 减持 |

```python
classifier = NewsClassifier()
tags = classifier.classify("央行下调LPR利率")
# tags = ["macro", "policy"]
```

#### 新闻数据模型

**路径**: [datacore/news/models.py](file:///d:/Programs/data-core/datacore/news/models.py)

| 数据结构 | 字段 | 说明 |
|:---------|:-----|:-----|
| `NewsItem` | title, content, source, published_at, url, tags, related_symbols | 单条新闻 |
| `NewsData` | symbol, items: list[NewsItem], total, source | 新闻数据集 |

---

### 4.8 macro — 宏观数据模块

**路径**: [datacore/macro/](file:///d:/Programs/data-core/datacore/macro/)

提供宏观经济指标的查询与缓存。

#### MacroDataProvider

**路径**: [datacore/macro/macro_provider.py](file:///d:/Programs/data-core/datacore/macro/macro_provider.py)

宏观数据统一入口，维护多源降级链：
- 数据源: `[NationalBureauProvider(), PboCProvider(), EastMoneyMacroProvider()]`
- `get(indicator, params)`: 获取宏观指标数据

| 支持指标 | 说明 |
|:---------|:-----|
| `cpi` | 居民消费价格指数 |
| `ppi` | 工业生产者出厂价格指数 |
| `gdp` | 国内生产总值 |
| `pmi` | 采购经理指数 |
| `m2` | 广义货币供应量 |
| `lpr` | 贷款市场报价利率 |

#### NationalBureauProvider — P0 源 (v0.5.0)

**路径**: [datacore/macro/providers/national_bureau.py](file:///d:/Programs/data-core/datacore/macro/providers/national_bureau.py)

国家统计局 (stats.gov.cn) 官方数据源，宏观数据首选：
- 优先级: 0（最高）
- 支持指标: `cpi`, `ppi`, `gdp`, `pmi`
- 数据来源: 国家统计局官方发布
- 核心方法:
  - `_fetch_indicator(indicator, params)`: 获取官方统计数据

#### PboCProvider — P1 源 (v0.5.0)

**路径**: [datacore/macro/providers/pboc.py](file:///d:/Programs/data-core/datacore/macro/providers/pboc.py)

中国人民银行 (pbc.gov.cn) 官方数据源：
- 优先级: 1
- 支持指标: `m2`, `lpr`
- 数据来源: 央行官方发布
- 核心方法:
  - `_fetch_indicator(indicator, params)`: 获取央行统计数据

#### EastMoneyMacroProvider — P2 源

**路径**: [datacore/macro/providers/eastmoney_macro.py](file:///d:/Programs/data-core/datacore/macro/providers/eastmoney_macro.py)

东方财富宏观数据源（降级后备）：
- 优先级: 2
- 支持指标: `cpi`, `ppi`, `gdp`, `pmi`, `m2`, `lpr`
- 数据来源: 东方财富聚合

#### 宏观数据模型

**路径**: [datacore/macro/models.py](file:///d:/Programs/data-core/datacore/macro/models.py)

| 数据结构 | 说明 |
|:---------|:-----|
| `MacroIndicator` | 宏观指标定义（code, name, unit, frequency）|
| `MacroDataPoint` | 单条数据（date, value）|
| `MacroData` | 宏观数据集（indicator, data_points）|

---

### 4.9 processing — 数据加工层

**路径**: [datacore/processing/](file:///d:/Programs/data-core/datacore/processing/)

Data-Core 的数据加工层，将原始数据加工为 AI 可直接消费的结构化数据。**v0.3.0 新增**。

#### 加工管线架构

```
原始数据         加工阶段                   输出
───────         ────────                  ────
NEWS (采集+分类) → SentimentLLM (P0)       → SENTIMENT
                  → RuleBase (P1, 降级)    → (情绪分数 + 置信度)
                  → SentimentAggregator    → (按品种/时间聚合)

OHLCV (采集)     → MarketRegimeDetector    → MARKET_STATE
                                           → (bull/bear/sideways + 置信度)

研报/财报         → FundamentalLLM (v0.6.0) → FUNDAMENTAL
                                           → (研报摘要/财报提取)
```

#### ProcessingStage 抽象基类

**路径**: [datacore/processing/base.py](file:///d:/Programs/data-core/datacore/processing/base.py)

所有加工阶段的统一接口：

| 属性/方法 | 说明 |
|-----------|------|
| `input_type` | 输入数据类型声明（如 `"NEWS"`）|
| `output_type` | 输出数据类型声明（如 `"SENTIMENT_ITEM"`）|
| `name` | 阶段名称，用于日志和降级链标识 |
| `priority` | 优先级（0=最高），用于降级链排序 |
| `process(input_data, symbol, params)` | 抽象方法 — 执行数据加工 |
| `check_available()` | 检查此加工阶段是否可用 |

#### 情绪打分管线

##### SentimentLLMStage — P0 高质量打分

**路径**: [datacore/processing/sentiment/sentiment_llm.py](file:///d:/Programs/data-core/datacore/processing/sentiment/sentiment_llm.py)

- 使用 LLM 对新闻进行情绪打分（需要配置 `DATACORE_LLM_API_KEY`）
- 输出: `SentimentItem`（score: -1.0 ~ +1.0, confidence: 0.0 ~ 1.0）
- 降级: 配置 `fallback_to_rule=True` 时，LLM 不可用自动降级到规则基线

##### SentimentRuleStage — P1 规则基线

**路径**: [datacore/processing/sentiment/sentiment_rule.py](file:///d:/Programs/data-core/datacore/processing/sentiment/sentiment_rule.py)

- 词典法情绪打分（零成本，无需外部依赖）
- 内置 100+ 正面/负面词汇 + 否定词 + 程度副词处理
- 输出: `SentimentItem`（规则打分，置信度固定 0.5）

##### SentimentAggregator — 情绪聚合器

**路径**: [datacore/processing/sentiment/sentiment_aggregator.py](file:///d:/Programs/data-core/datacore/processing/sentiment/sentiment_aggregator.py)

- 时间衰减加权（近期新闻权重更高）
- 置信度加权（高置信度打分权重更高）
- 按日聚合，产出每日情绪序列
- 输出: `SentimentData`（含 overall_score, daily, topics）

#### 市场制度检测

##### MarketRegimeDetector

**路径**: [datacore/processing/market_regime.py](file:///d:/Programs/data-core/datacore/processing/market_regime.py)

基于 OHLCV 数据的纯计算检测器（无外部依赖），识别市场处于 bull/bear/sideways：

检测逻辑:
1. **趋势强度**: MA 斜率 + 价格相对 MA 位置（权重 60%）
2. **成交量趋势**: 成交量 MA 斜率（权重 20%）
3. **波动率**: 收益率标准差（负权重，高波动在无趋势时倾向于 sideways）
4. **综合打分**: `score = trend_strength * 0.6 + volume_trend * 0.2 - volatility * 0.2`

#### FundamentalLLMStage — 基本面LLM加工 (v0.6.0)

**路径**: [datacore/processing/fundamental/fundamental_llm.py](file:///d:/Programs/data-core/datacore/processing/fundamental/fundamental_llm.py)

基于 LLM 的研报摘要和财务报表提取加工阶段：
- 研报摘要: 输入研报全文 → LLM 提取核心观点、评级、目标价
- 财报提取: 输入财报文本 → LLM 提取营收、利润、毛利率等关键指标
- 输出类型: `DataType.FUNDAMENTAL`
- 降级策略: LLM 不可用 → 返回空结果（不降级到规则，因为规则无法替代 LLM 语义理解）
- 配置: 依赖 `DATACORE_LLM_API_KEY` 环境变量

#### 数据加工层数据模型

**路径**: [datacore/processing/models.py](file:///d:/Programs/data-core/datacore/processing/models.py)

| 数据结构 | 说明 |
|:---------|:-----|
| `SentimentItem` | 单条新闻/公告的情绪打分结果（score, confidence, source, tags） |
| `SentimentData` | 品种情绪聚合数据（overall_score, daily, topics） |
| `MarketStateData` | 市场制度状态（regime, confidence, trend_strength, volatility） |
| `MarketRegime` | 枚举: BULL / BEAR / SIDEWAYS / UNKNOWN |

---

### 4.10 breaker — 熔断层

**路径**: [datacore/breaker.py](file:///d:/Programs/data-core/datacore/breaker.py)

带状态熔断器，保护外部数据源调用。**v0.4.0 新增**。

#### 状态转换

```
CLOSED → (连续失败 ≥ max_failures) → OPEN → (recovery_timeout 后) → HALF_OPEN
HALF_OPEN → (探测成功) → CLOSED
HALF_OPEN → (探测失败) → OPEN
```

#### Breaker 类

| 属性/方法 | 说明 |
|-----------|------|
| `name` | 熔断器名称 |
| `state` | 当前状态 (CLOSED/OPEN/HALF_OPEN) |
| `max_failures` | 连续失败次数阈值（默认 3）|
| `recovery_timeout` | OPEN→HALF_OPEN 等待时间（默认 30s）|
| `call(func, *args, **kwargs)` | 带熔断保护的函数调用 |
| `reset()` | 手动重置熔断器 |
| `stats` | 状态快照（调用次数/失败次数/当前状态）|

使用示例：
```python
from datacore.breaker import Breaker

breaker = Breaker("eastmoney", max_failures=3, recovery_timeout=30.0)
try:
    result = breaker.call(my_http_request, url, params)
except RuntimeError:
    # 熔断器 OPEN，使用降级源
    fallback_result = use_backup_source()
```

---

### 4.11 metrics — 指标收集

**路径**: [datacore/metrics.py](file:///d:/Programs/data-core/datacore/metrics.py)

轻量级指标收集框架，统计调用次数、成功率、延迟等。**v0.4.0 新增**。

#### MetricsCollector 类

| 方法 | 说明 |
|------|------|
| `record(key, duration, success)` | 记录一次调用（成功/失败+耗时） |
| `snapshot()` | 获取各端点详细统计（调用数/失败数/成功率/平均耗时） |
| `summary()` | 获取全局摘要（总调用数/总失败数/总成功率） |
| `reset()` | 重置所有指标 |

收集的指标：

| 指标 | 类型 | 说明 |
|:-----|:-----|:-----|
| `calls_total` | Counter | 总调用次数（按数据源/方法维度）|
| `calls_success` | Counter | 成功调用次数 |
| `calls_failed` | Counter | 失败调用次数 |
| `success_rate` | Gauge | 成功率百分比（实时）|
| `latency_p50/p95/p99` | Gauge | 响应延迟百分位（毫秒）|
| `cache_hit_rate` | Gauge | 缓存命中率 |
| `breaker_open_count` | Counter | 熔断器开启次数 |

使用示例：
```python
from datacore.metrics import get_metrics

metrics = get_metrics()
metrics.record("futures.tdx_lc.kline", duration=0.35, success=True)
metrics.record("futures.tdx_lc.kline", duration=3.2, success=False)

report = metrics.summary()
print(f"总调用: {report['total_calls']}, 成功率: {report['overall_success_rate']}%")
```

---

### 4.12 api — 统一数据入口

**路径**: [datacore/api.py](file:///d:/Programs/data-core/datacore/api.py)

`UnifiedDataProvider` 是整个系统的门面类，所有消费者通过此接口获取数据。

```python
class UnifiedDataProvider:
    def __init__(self):
        self.registry = SymbolRegistry()

    def get(self, symbol, data_type, params=None) -> DataPayload:
        # 1. 数据加工层路由 (SENTIMENT/MARKET_STATE/NEWS/MACRO)
        # 2. 通过 registry.resolve_market() 判断市场类型
        # 3. 期货 -> FuturesDataProvider
        # 4. 股票/ETF/可转债/REITs -> EquityDataProvider
        # 5. 未知符号 -> UNAVAILABLE

    def get_batch(self, symbols, data_type, params=None) -> dict[str, DataPayload]:
        # 批量获取

    def list_symbols(self, market=None) -> list[dict]:
        # 列出所有/指定市场符号

    def get_health(self) -> dict:
        # 健康检查 — 探测所有数据源可用性及延迟
```

**路由逻辑**:
```
get("RB", DataType.OHLCV)
  -> resolve_market("RB") = MarketType.FUTURES
  -> FuturesDataProvider.get("RB", OHLCV)

get("600519", DataType.QUOTE)
  -> resolve_market("600519") = None (A股未预注册)
  -> EquityDataProvider.get("600519", QUOTE)

get("RB", DataType.SENTIMENT)
  -> 数据加工层路由
  -> NEWS news → SentimentLLMStage → SentimentAggregator

get("*", DataType.MACRO)
  -> 宏观数据路由
  -> MacroDataProvider.get(indicator=None)

get("ZZZ", DataType.OHLCV)
  -> resolve_market("ZZZ") = None
  -> 返回 UNAVAILABLE (含错误信息 "Unknown symbol: ZZZ")
```

**懒加载模式**: `_get_futures()`, `_get_equity()`, `_get_news()`, `_get_macro()`, `_get_sentiment_llm()`, `_get_sentiment_aggregator()`, `_get_market_regime()` 使用模块级全局变量和懒加载，推迟 Provider 的导入和实例化。

> **DuckDB 缓存集成**: 自 v1.0.0 起，DuckDB 已完全接入 UnifiedDataProvider 的 L2 缓存层（原 G10 差距已关闭）。`get()` 和 `get_batch()` 方法自动查询 DuckDB 缓存作为第二级缓存（MemoryCache → DuckDBStore → 数据源），显著减少对外部数据源的重复调用。

---

### 4.13 cli — 命令行工具

**路径**: [datacore/cli.py](file:///d:/Programs/data-core/datacore/cli.py)

命令行入口，通过 `pyproject.toml` 注册为 `datacore` 命令：

| 命令 | 功能 |
|------|------|
| `datacore list` | 列出所有注册的标的（56+ 期货品种）|
| `datacore status` | 查看版本、注册表数、各数据源健康状态 |
| `datacore quote <symbol>` | 查询某个标的行情 |

```bash
# 示例
datacore list
datacore status      # 显示各数据源 ✅/❌ 状态 + 延迟
datacore quote RB
datacore quote 600519
```

`datacore status` 输出示例：
```
Data-Core v1.0.0
注册表: 56 个标的
  tdx_local: ✅ (12.3ms)
  eastmoney_futures: ✅ (45.6ms)
  tencent: ✅ (8.2ms)
  cls: ❌ (3000ms)
  wallstreet: ✅ (120ms)
  national_bureau: ✅ (80ms)
  pboc: ✅ (65ms)

系统状态: healthy
```

---

### 4.14 stream — WebSocket 实时行情 (v1.0.0)

**路径**: [datacore/stream.py](file:///d:/Programs/data-core/datacore/stream.py)

基于 WebSocket 的全双工实时行情推送模块，提供低延迟的市场数据流。

#### StreamQuote

实时行情流数据类：
- 字段: `symbol`, `market`, `last_price`, `volume`, `timestamp`, `source`
- 通过 WebSocket 连接持续推送，支持订阅/取消订阅

#### WebSocketManager

WebSocket 连接管理器：
- `connect()`: 建立 WebSocket 连接
- `subscribe(symbols, data_types)`: 订阅指定品种的数据类型
- `unsubscribe(symbols)`: 取消订阅
- `on_message(callback)`: 注册消息回调函数
- `close()`: 关闭连接

支持的数据类型：
- `QUOTE`: 实时行情快照（逐笔推送）
- `OHLCV`: K 线更新（分时/1分钟/5分钟聚合）
- `DEPTH`: 深度行情（五档/十档盘口）

使用示例：
```python
from datacore.stream import WebSocketManager

ws = WebSocketManager()
ws.connect()
ws.subscribe(["RB", "CU", "600519"], ["QUOTE"])

def on_quote(data):
    print(f"{data.symbol}: {data.last_price}")

ws.on_message(on_quote)
```

### 4.15 alert — 告警引擎 (v1.0.0)

**路径**: [datacore/alert.py](file:///d:/Programs/data-core/datacore/alert.py)

灵活的告警引擎，支持基于规则、阈值和模式匹配的告警触发与通知。

#### AlertEngine

告警引擎核心，管理告警规则的注册、评估和通知分发：
- `register_rule(rule)`: 注册一条告警规则
- `unregister_rule(rule_id)`: 注销告警规则
- `evaluate(data)`: 对传入数据评估所有已注册规则
- `evaluate_batch(data_list)`: 批量评估
- 支持定时评估（通过 `start_periodic_eval(interval)`）

#### AlertRule

告警规则定义：
- `rule_id`: 规则唯一标识
- `name`: 规则名称
- `condition`: 条件表达式（支持价格阈值、指标突破、模式匹配等）
- `severity`: 严重级别（INFO / WARNING / CRITICAL）
- `cooldown`: 冷却时间（防止重复告警）

#### AlertEvent

告警事件，记录触发详情：
- 字段: `rule_id`, `symbol`, `triggered_at`, `value`, `threshold`, `message`, `severity`
- 支持事件持久化（可选，依赖存储后端）

#### AlertNotifier

告警通知分发器：
- 支持多种通知渠道：控制台日志、文件、HTTP Webhook
- `send(event)`: 发送告警通知
- `register_channel(channel)`: 注册自定义通知渠道

使用示例：
```python
from datacore.alert import AlertEngine, AlertRule

engine = AlertEngine()

# 注册价格阈值规则
rule = AlertRule(
    rule_id="price_spike",
    name="价格异动",
    condition={"type": "price_change", "threshold": 5.0, "direction": "above"},
    severity="WARNING",
    cooldown=300
)
engine.register_rule(rule)

# 评估行情数据
quote_data = {"symbol": "RB", "last_price": 3800, "change_pct": 6.2}
events = engine.evaluate(quote_data)
for event in events:
    print(f"[{event.severity}] {event.message}")
```

---

## 5. 数据流与降级链

### A 股数据流

```
UnifiedDataProvider.get("600519", DataType.QUOTE)
  |
  v
EquityDataProvider.get("600519", QUOTE)
  |
  +-- [P0] TencentProvider.fetch("600519", QUOTE)
  |     |-- check_available()? --> qt.gtimg.cn 可达?
  |     |-- _fetch_quote() --> HTTP GET qt.gtimg.cn
  |     |-- 成功? --> DataPayload(grade=PRIMARY, source="tencent")
  |     |-- 失败? --> 继续
  |
  +-- [P1] EastMoneyEquityProvider.fetch("600519", QUOTE)
        |-- check_available()? --> push2.eastmoney.com 可达?
        |-- QUOTE 不在 supported_types 中 --> 跳过
        |
  --> DataPayload(grade=UNAVAILABLE, errors=["所有 A 股源不可用"])
```

### 期货数据流

```
UnifiedDataProvider.get("RB", DataType.OHLCV)
  |
  v
FuturesDataProvider.get("RB", OHLCV)
  |
  +-- [P0] TdxLcProvider.fetch_kline("RB", "daily", 120)
  |     |-- 从配置获取 URL 和超时
  |     |-- _resolve_contract("RB") --> "RB2510" (通过通达信本地API)
  |     |-- _post("get_market_data", ...) --> K线数据
  |     |-- 成功? --> DataPayload(grade=PRIMARY, source="tdx_lc")
  |     |-- 失败? --> 继续
  |
  +-- [P1] EastMoneyFuturesProvider.fetch_kline("RB", "daily", 120)
        |-- check_available()? --> push2his.eastmoney.com 可达?
        |-- HTTP GET push2his.eastmoney.com (secid="CF.RB")
        |-- 成功? --> DataPayload(grade=DAILY, source="eastmoney_futures")
        |-- 失败? -->
  --> DataPayload(grade=UNAVAILABLE, errors=["所有期货源不可用"])
```

### 情绪数据加工流（v0.3.0）

```
UnifiedDataProvider.get("RB", DataType.SENTIMENT, {"days": 30})
  |
  +-- Step 1: NewsDataProvider.get("RB", {"days": 30})
  |     |-- 新闻采集（财联社/华尔街见闻/东方财富研报）
  |     |-- 新闻分类（打 macro/policy/industry/company 标签）
  |
  +-- Step 2: SentimentLLMStage.process(news_item)
  |     |-- check_available()? --> DATACORE_LLM_API_KEY 已配置?
  |     |-- LLM 情绪打分 --> SentimentItem(score, confidence, source="llm")
  |     |-- LLM 不可用 --> 降级到 SentimentRuleStage
  |           |-- 词典法打分 --> SentimentItem(score, confidence=0.5, source="rule_fallback")
  |
  +-- Step 3: SentimentAggregator.aggregate(sentiment_items)
  |     |-- 时间衰减加权
  |     |-- 置信度加权
  |     |-- 按日聚合
  |
  --> DataPayload(grade=PRIMARY/DAILY, data=SentimentData)
```

### 市场制度检测流（v0.3.0）

```
UnifiedDataProvider.get("RB", DataType.MARKET_STATE, {"period": "daily", "days": 120})
  |
  +-- Step 1: FuturesDataProvider._get_kline("RB", "daily", 120)
  |     |-- 获取 OHLCV K 线数据
  |
  +-- Step 2: MarketRegimeDetector.process(ohlcv_data)
  |     |-- 计算趋势强度（MA斜率+价格偏离）
  |     |-- 计算波动率（收益率标准差，年化）
  |     |-- 计算成交量趋势（成交量MA斜率）
  |     |-- 综合打分: score = trend*0.6 + volume*0.2 - vol*0.2
  |     |-- score > 0.6 → BULL, score < -0.6 → BEAR, 否则 SIDEWAYS
  |
  --> DataPayload(grade=PRIMARY, data=MarketStateData)
```

### 降级链总览

#### 期货行情降级链

| 数据类型 | P0 | P1 | P2 | P3 |
|:---------|:---|:---|:---|:---|
| OHLCV/QUOTE | TQ-Local | EastMoney | ExchangeAPI | ShengYiShe/MemoryCache |
| 合约链/期限结构/价差 | TQ-Local | EastMoney | ExchangeAPI | MemoryCache |
| 基差 | TQ-Local | EastMoney | ShengYiShe | MemoryCache |

#### A 股行情降级链

| 数据类型 | P0 | P1 | P2 | P3 |
|:---------|:---|:---|:---|:---|
| OHLCV/QUOTE | Tencent | EastMoney | Guosen | MemoryCache |

#### 新闻资讯降级链

| 数据类型 | P0 | P1 | P2 | P3 |
|:---------|:---|:---|:---|:---|
| 快讯 | 财联社 | 华尔街见闻 | 东方财富研报 | 交易所公告 |

#### 情绪数据降级链

| 数据类型 | P0 (PRIMARY) | P1 (DAILY) | P2 (CACHED) |
|:---------|:-------------|:-----------|:------------|
| 情绪打分 | LLM 情绪打分 | 规则基线（词典法） | MemoryCache |

> **降级保证**: LLM 不可用时自动降级到规则基线（零成本模式），确保情绪数据始终可用。

#### 宏观数据降级链

| 数据类型 | P0 | P1 | P2 | P3 |
|:---------|:---|:---|:---|:---|
| CPI/PPI/GDP/PMI | 国家统计局 | 东方财富 | — | MemoryCache |
| M2/LPR | 中国人民银行 | 东方财富 | — | MemoryCache |

---

## 6. 配置说明

### 配置优先级

配置加载优先级（从高到低）：
1. **环境变量**: `DATACORE_*` 前缀
2. **YAML 文件**: `config/settings.yaml` 或 `~/.datacore/settings.yaml`
3. **代码默认值**: 硬编码的默认值

### 完整配置文件

**路径**: [config/settings.yaml](file:///d:/Programs/data-core/config/settings.yaml)

```yaml
sources:
  tdx_lc:
    enabled: true
    url: http://127.0.0.1:17709/
    timeout: 3
  eastmoney:
    enabled: true
  tencent:
    enabled: true
  guosen:
    enabled: false
    api_key:
    url: https://api.guosen.com.cn/
    timeout: 5

store:
  backend: duckdb
  cache_ttl: 3600
  duckdb_path: ~/.datacore/datacore.db
  postgresql:
    dsn:
  redis:
    url:
```

### 环境变量映射

| 配置项 | 环境变量 |
|--------|----------|
| 通达信 URL | `DATACORE_SOURCES_TDX_LC_URL` |
| 通达信超时 | `DATACORE_SOURCES_TDX_LC_TIMEOUT` |
| 国信 API-KEY | `DATACORE_SOURCES_GUOSEN_API_KEY` |
| 国信 URL | `DATACORE_SOURCES_GUOSEN_URL` |
| 缓存 TTL | `DATACORE_STORE_CACHE_TTL` |
| DuckDB 路径 | `DATACORE_STORE_DUCKDB_PATH` |
| PostgreSQL DSN | `DATACORE_STORE_POSTGRESQL_DSN` |
| Redis URL | `DATACORE_STORE_REDIS_URL` |
| 存储后端 | `DATACORE_STORE_BACKEND` |
| LLM API Key | `DATACORE_LLM_API_KEY` |
| LLM 模型 | `DATACORE_LLM_MODEL` |
| 熔断器超时 | `DATACORE_CB_TIMEOUT` |
| 熔断器最大失败 | `DATACORE_CB_MAX_FAILURES` |
| 熔断器恢复超时 | `DATACORE_CB_RECOVERY_TIMEOUT` |
| 指标启用 | `DATACORE_METRICS_ENABLED` |
| 新闻源 | `DATACORE_NEWS_SOURCES` |
| 宏观源 | `DATACORE_MACRO_SOURCES` |

### 配置示例

#### 开发环境

```bash
# 使用默认配置即可，无需额外设置
pip install -e ".[store]"
```

#### 生产环境（带 DuckDB）

```bash
export DATACORE_STORE_DUCKDB_PATH=/data/datacore/database.db
pip install -e ".[store]"
```

#### 生产环境（使用 PostgreSQL）

```bash
export DATACORE_STORE_BACKEND=postgres
export DATACORE_STORE_POSTGRESQL_DSN="postgresql://user:password@localhost:5432/datacore"
pip install -e ".[postgres]"
```

#### 带 LLM 情绪打分

```bash
export DATACORE_LLM_API_KEY=sk-your-api-key-here
export DATACORE_LLM_MODEL=gpt-4o-mini
pip install -e .
```

#### 生产环境（Redis + PostgreSQL）

```bash
export DATACORE_STORE_REDIS_URL="redis://localhost:6379/0"
export DATACORE_STORE_POSTGRESQL_DSN="postgresql://user:password@localhost:5432/datacore"
pip install -e ".[full]"
```

#### 通过 YAML 文件配置

```yaml
# ~/.datacore/settings.yaml
sources:
  tdx_lc:
    url: http://tdx-server:17709/
    timeout: 5

store:
  backend: postgres
  postgresql:
    dsn: postgresql://user:password@pg-server:5432/datacore
```

---

## 7. 运行与测试

### 安装

```bash
# 基础安装（仅核心功能）
pip install -e .

# 带 DuckDB 存储
pip install -e ".[store]"

# 带 PostgreSQL
pip install -e ".[postgres]"

# 带 Redis
pip install -e ".[redis]"

# 带 WebSocket 实时行情
pip install -e ".[stream]"

# 完整安装（所有依赖）
pip install -e ".[full]"
```

### Python API 使用

```python
from datacore import UnifiedDataProvider
from datacore.models.enums import DataType

dc = UnifiedDataProvider()

# 期货 K 线
rb = dc.get('RB', DataType.OHLCV, {'period': 'daily', 'days': 400})
if rb.available:
    kline = rb.data
    print(f"来源: {rb.source}, 等级: {rb.grade}")

# A股行情
kweichow = dc.get('600519', DataType.QUOTE)
if kweichow.available:
    quote = kweichow.data
    print(f"最新价: {quote.last_price}")

# A股财务
fin = dc.get('600519', DataType.FINANCIAL)

# 新闻资讯
news = dc.get('RB', DataType.NEWS, {'days': 3, 'categories': ['macro', 'industry']})

# 情绪数据
sentiment = dc.get('RB', DataType.SENTIMENT, {'days': 30})
if sentiment.available:
    print(f"情绪分数: {sentiment.data.overall_score}")

# 市场制度
regime = dc.get('RB', DataType.MARKET_STATE, {'period': 'daily', 'days': 120})
if regime.available:
    print(f"市场状态: {regime.data.regime}")

# 宏观数据
macro = dc.get('*', DataType.MACRO, {'indicator': 'cpi'})

# 批量查询
results = dc.get_batch(['RB', 'CU', 'AU'], DataType.OHLCV)
for sym, payload in results.items():
    print(f"{sym}: {payload.grade}")

# 健康检查
health = dc.get_health()
for src_name, info in health.get('sources', {}).items():
    ok = "✅" if info.get('available') else "❌"
    print(f"  {src_name}: {ok} ({info.get('latency_ms', '?')}ms)")

# 列出标的
symbols = dc.list_symbols()
for s in symbols:
    print(f"  {s['symbol']:8s} {s['name']:10s} [{s['market']}]")
```

### 配置系统使用

```python
from datacore.config import get_config

config = get_config()
print(f"通达信 URL: {config.tdx_url}")
print(f"缓存 TTL: {config.cache_ttl}")
print(f"存储后端: {config.store_backend}")

# DuckDB 存储
from datacore.store import DuckDBStore
store = DuckDBStore()
store.init_schema()
store.store_kline("RB", "daily", [{"date": "2026-01-01", "open": 3500, ...}])

# PostgreSQL 后端
from datacore.store.postgres import build_postgres_store
pg_store = build_postgres_store()
if pg_store:
    pg_store.cache_set("test_key", "test_value", 3600)

# Redis 后端
from datacore.store.redis import build_redis_store
redis_store = build_redis_store()
if redis_store:
    redis_store.cache_set("test_key", "test_value", 3600)
```

### 命令行使用

```bash
datacore list         # 列出所有标的
datacore status       # 查看版本和数据源健康状态
datacore quote RB     # 查询螺纹钢行情
datacore quote 600519 # 查询贵州茅台行情
```

### MetricsCollector 使用

```python
from datacore.metrics import get_metrics

metrics = get_metrics()
# 记录调用
metrics.record("futures.tdx_lc.kline", duration=0.35, success=True)
metrics.record("futures.tdx_lc.kline", duration=3.2, success=False)
metrics.record("equity.tencent.quote", duration=0.12, success=True)

# 获取快照
snap = metrics.snapshot()
# {'futures.tdx_lc.kline': {'calls': 2, 'failures': 1, 'success_rate': 50.0, ...}}

# 全局摘要
summary = metrics.summary()
print(f"总调用: {summary['total_calls']}, 成功率: {summary['overall_success_rate']}%")
```

### Breaker 使用

```python
from datacore.breaker import Breaker

breaker = Breaker("eastmoney", max_failures=3, recovery_timeout=30.0)

def fetch_data():
    import httpx
    resp = httpx.get("https://push2.eastmoney.com/api/qt/stock/get", timeout=3)
    return resp.json()

try:
    result = breaker.call(fetch_data)
except RuntimeError:
    # 熔断器 OPEN，使用降级源
    print("使用降级源 ...")

# 查看熔断器状态
print(breaker.stats)
# {'name': 'eastmoney', 'state': 'open', 'fail_count': 3, ...}
```

### 运行测试

```bash
cd datacore

# 运行全部测试
python -m pytest tests/ -v

# 按模块运行
python -m pytest tests/test_api.py -v
python -m pytest tests/test_breaker.py -v
python -m pytest tests/test_processing.py -v
python -m pytest tests/test_store.py -v

# 运行带标记的测试
python -m pytest tests/ -m "not slow" -v
```

### 测试覆盖

**总计: 26 个测试文件，724+ 测试用例，≥ 95% 覆盖率**

| 测试文件 | 用例数 | 覆盖模块 |
|:---------|:-------|:---------|
| `test_api.py` | 4 | UnifiedDataProvider 路由测试 |
| `test_alert.py` | 20 | 告警引擎规则评估/通知 (v1.0.0) |
| `test_breaker.py` | 30 | 熔断器状态转换/超时/半开探测 |
| `test_cli.py` | — | 命令行工具 |
| `test_duckdb.py` | 18 | DuckDB 持久化缓存 (v0.5.0) |
| `test_equity.py` | — | A 股 Provider 集成测试 |
| `test_equity_mock.py` | 4 | TencentProvider Mock 测试 |
| `test_exchange_api.py` | 8 | ExchangeAPI 提供商 (v0.5.0) |
| `test_futures.py` | — | 期货 Provider 集成测试 |
| `test_futures_mock.py` | 11 | TdxLcProvider Mock 测试 |
| `test_futures_models.py` | 18 | 期货数据模型 |
| `test_guosen.py` | 6 | 国信证券提供商 (v0.5.0) |
| `test_health.py` | 20 | 健康检查接口 |
| `test_macro.py` | 3 | 宏观数据模型 |
| `test_macro_mock.py` | 12 | 宏观数据源 Mock (v0.5.0) |
| `test_metrics.py` | 30 | 指标收集框架 |
| `test_models.py` | 7 | 枚举/Payload/K线数据结构 |
| `test_national_bureau.py` | 10 | 国家统计局提供商 (v0.5.0) |
| `test_news.py` | 11 | 新闻分类器 + 新闻模型 |
| `test_pboc.py` | 8 | 中国人民银行提供商 (v0.5.0) |
| `test_processing.py` | 36 | 情绪管线 + 市场制度 |
| `test_fundamental.py` | 10 | 基本面LLM加工 (v0.6.0) |
| `test_registry.py` | 5 | SymbolRegistry |
| `test_shengyishe.py` | 8 | 生意社提供商 (v0.5.0) |
| `test_store.py` | 5 | MemoryCache |
| `test_stream.py` | 15 | WebSocket 实时行情 (v1.0.0) |

**审计工具链**: pylint 10/10, mypy 0 错误(64 文件), ruff + flake8 0 错误

---

## 8. 依赖关系

### 核心依赖（必需）

| 包 | 最低版本 | 用途 |
|---|---------|------|
| `numpy` | 1.24 | 数值计算 |
| `pandas` | 2.0 | 数据处理 |
| `httpx` | 0.25 | HTTP 客户端（数据源通信） |
| `pyyaml` | 6.0 | YAML 配置文件解析 |

### 可选依赖

| 包 | 组 | 用途 |
|---|------|------|
| `duckdb` | store / full | OLAP 嵌入式数据库（冷数据持久化，默认后端） |
| `psycopg2-binary` | postgres / full | PostgreSQL 驱动（分布式持久化） |
| `redis` | redis / full | Redis 客户端（热缓存共享） |
| `beautifulsoup4` | full | HTML 解析（备用源数据提取） |
| `websockets>=12.0` | stream / full | WebSocket 实时行情（v1.0.0） |

### 零依赖说明

Data-Core 刻意避免依赖以下常见金融数据包：
- **akshare**: 零依赖，自实现 HTTP 数据源
- **tushare**: 同上
- **任何 MCP Server**: 自包含设计，不依赖外部 Agent 运行时
- **任何外部 Skill**: 无需 Agent 框架支持

---

## 附录：关键数据流图

### 请求生命周期

```
用户请求: dc.get("RB", DataType.OHLCV)
  |
  1. UnifiedDataProvider.get()
  |   - registry.resolve_market("RB") -> MarketType.FUTURES
  |
  2. FuturesDataProvider.get()
  |   - data_type == OHLCV -> _get_kline("RB", "daily", 120)
  |
  3. 遍历 sources: [TdxLcProvider, EastMoneyFuturesProvider]
  |   - 检查 check_available()
  |   - 检查 supported_types
  |   - 调用 fetch_kline()
  |
  4. 成功 -> DataPayload(grade=PRIMARY/DAILY, source="tdx_lc"/"eastmoney")
  |   失败 -> 尝试下一个源
  |
  5. 全部失败 -> DataPayload(grade=UNAVAILABLE, errors=["所有期货源不可用"])
```

### 情绪数据加工生命周期

```
用户请求: dc.get("RB", DataType.SENTIMENT, {"days": 30})
  |
  1. UnifiedDataProvider._get_sentiment()
  |   - 数据加工层路由，非市场路由
  |
  2. NewsDataProvider.get("RB", {"days": 30})
  |   - 财联社/华尔街见闻/东方财富研报三级降级
  |   - NewsClassifier 自动打标签
  |
  3. SentimentLLMStage.process(news_item)
  |   - LLM 打分 (如果 DATACORE_LLM_API_KEY 已配置)
  |   - 自动降级到 SentimentRuleStage (词典法)
  |
  4. SentimentAggregator.aggregate(sentiment_items)
  |   - 时间衰减加权 + 置信度加权 + 按日聚合
  |
  5. DataPayload(grade=PRIMARY/DAILY, data=SentimentData)
```

### 配置加载流程

```
get_config()
  |
  +-- _load_env()
  |     - 读取所有 DATACORE_* 环境变量
  |     - 转换为小写字典
  |
  +-- _load_yaml()
  |     - 尝试读取 config/settings.yaml
  |     - 尝试读取 ~/.datacore/settings.yaml
  |     - 使用 yaml.safe_load 安全解析
  |
  +-- _get(key, default)
        - 优先从环境变量获取
        - 其次从 YAML 配置获取
        - 最后使用默认值
```

### 健康检查流程 (v1.0.0)

```
dc.get_health()
  |
  +-- FuturesDataProvider.sources
  |     - tdx_lc: check_available() + 延迟
  |     - eastmoney_futures: check_available() + 延迟
  |     - exchange_api: check_available() + 延迟
  |     - shengyishe: check_available() + 延迟
  |
  +-- EquityDataProvider.sources
  |     - tencent: check_available() + 延迟
  |     - eastmoney_equity: check_available() + 延迟
  |     - guosen: check_available() + 延迟
  |
  +-- NewsDataProvider.sources
  |     - cls: check_available() + 延迟
  |     - wallstreet: check_available() + 延迟
  |
  +-- MacroDataProvider.sources
  |     - national_bureau: check_available() + 延迟
  |     - pboc: check_available() + 延迟
  |     - eastmoney_macro: check_available() + 延迟
  |
  +-- alert/stream (v1.0.0)
        - alert_engine: check_available()
        - websocket: check_available()

  --> {
    "status": "healthy" | "unavailable",
    "version": "1.0.0",
    "sources": { name: {available, latency_ms} },
    "timestamp": time.time()
  }
```

