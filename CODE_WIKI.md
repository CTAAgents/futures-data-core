# Data-Core Code Wiki

> 版本: v0.1.0 | AI-Native 量化数据基础设施

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
   - [4.7 api — 统一数据入口](#47-api--统一数据入口)
   - [4.8 cli — 命令行工具](#48-cli--命令行工具)
5. [数据流与降级链](#5-数据流与降级链)
6. [配置说明](#6-配置说明)
7. [运行与测试](#7-运行与测试)
8. [依赖关系](#8-依赖关系)

---

## 1. 项目概述

**Data-Core** 是一个面向中国期货和证券市场的 AI-Native 量化数据基础设施。专为 LLM 驱动的量化研究场景设计，核心特色包括：

- **数据溯源 (Provenance)**: 每条数据携带 source + grade + freshness 元数据，AI Agent 可自行判断数据可靠性
- **自描述 Schema**: 数据模型使用明确的 dataclass 定义，Python 和 LLM 均可通过结构化反射消费
- **优雅降级 (Graceful Degradation)**: 多源回退链保证 AI Pipeline 不会因数据问题硬失败
- **零外部依赖**: 自包含的 HTTP 数据源，单 `pip install` 即可使用，无需 MCP/Skill/Agent 依赖
- **多后端存储**: 支持 DuckDB（默认）、PostgreSQL、Redis 三种存储后端，灵活适应不同部署场景

---

## 2. 整体架构

```
AI Agent / Strategy
      |
      | get(symbol, data_type) --> DataPayload { data + grade + source + meta }
      v
UnifiedDataProvider
      |
      +-- futures/      TQ-Local --> EastMoney
      |    56 个合约品种, 支持 K线/行情/技术指标
      |
      +-- equity/       Tencent --> EastMoney
      |    A股/ETF/可转债/REITs, 支持 K线/行情/财务/宏观
      |
      +-- store/        MemoryCache + DuckDB/PostgreSQL/Redis
      +-- registry/     SymbolRegistry (市场路由)
      +-- config/       DataCoreConfig (环境变量 + YAML)
      +-- models/       DataType / MarketType / SourceGrade / DataPayload
```

### 设计原则

| 原则 | 说明 |
|------|------|
| **AI Native** | 所有数据返回携带 provenance 元数据 (source, grade, freshness)，供 LLM 决策 |
| **零外部依赖** | 自包含 HTTP 数据源，单 pip install 即可使用 |
| **优雅降级** | 多源回退，永不硬失败 |
| **市场无关** | 统一 API 覆盖期货、股票、ETF、可转债、REITs |
| **配置优先** | 禁止硬编码，所有配置通过环境变量或 YAML 文件注入 |

---

## 3. 目录结构

```
data-core/
├── datacore/                    # 主包
│   ├── __init__.py              # 包入口, 导出 UnifiedDataProvider
│   ├── api.py                   # UnifiedDataProvider — 统一数据入口
│   ├── cli.py                   # 命令行工具
│   ├── config.py                # DataCoreConfig — 统一配置系统
│   ├── models/                  # 数据模型层
│   │   ├── __init__.py
│   │   ├── enums.py             # DataType / MarketType / SourceGrade 枚举
│   │   ├── ohlcv.py             # KBar / KlineData / QuoteData 结构
│   │   └── payload.py           # DataPayload — 统一数据载荷信封
│   ├── registry/                # 符号注册表
│   │   ├── __init__.py
│   │   └── symbol_registry.py   # SymbolEntry / SymbolRegistry
│   ├── store/                   # 存储层
│   │   ├── __init__.py
│   │   ├── cache.py             # MemoryCache — TTL 内存缓存
│   │   ├── duckdb.py            # DuckDBStore — DuckDB 持久化（默认）
│   │   ├── postgres.py          # PostgresStore — PostgreSQL 持久化
│   │   └── redis.py             # RedisStore — Redis 缓存
│   ├── equity/                  # A股数据模块
│   │   ├── __init__.py
│   │   ├── equity_provider.py   # EquityDataProvider — A股数据入口
│   │   ├── financial.py         # 财务评分工具
│   │   └── providers/           # A股数据源
│   │       ├── __init__.py
│   │       ├── base.py          # EquityDataSource 抽象基类
│   │       ├── tencent.py       # TencentProvider — 腾讯数据源 (P0)
│   │       └── eastmoney.py     # EastMoneyEquityProvider — 东方财富 (P1)
│   └── futures/                 # 期货数据模块
│       ├── __init__.py
│       ├── futures_provider.py  # FuturesDataProvider — 期货数据入口
│       └── providers/           # 期货数据源
│           ├── __init__.py
│           ├── base.py          # FuturesDataSource 抽象基类
│           ├── tdx_lc.py        # TdxLcProvider — 通达信本地 (P0)
│           └── eastmoney.py     # EastMoneyFuturesProvider — 东方财富 (P1)
├── config/
│   └── settings.yaml            # 配置文件（支持环境变量覆盖）
├── tests/                       # 测试目录
│   ├── conftest.py
│   ├── test_api.py              # UnifiedDataProvider 测试
│   ├── test_models.py           # 数据模型测试
│   ├── test_registry.py         # 注册表测试
│   ├── test_store.py            # 缓存测试
│   ├── test_equity_mock.py      # A股 Provider Mock 测试
│   └── test_futures_mock.py     # 期货 Provider Mock 测试
├── docs/
│   └── harness/                 # HARNESS 工程规范文档 (09 份)
├── pyproject.toml               # 项目元数据与构建配置
├── README.md                    # 项目 README
└── ARCHITECTURE.md              # 架构设计文档
```

---

## 4. 模块详解

### 4.1 config — 统一配置系统

**路径**: `datacore/config.py`

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

**路径**: `datacore/models/`

提供系统中所有核心数据类型定义，是整个项目的契约层。

#### enums.py — 枚举定义

| 枚举 | 字段 | 说明 |
|------|------|------|
| `DataType` | `OHLCV`, `QUOTE`, `TECHNICAL`, `FINANCIAL`, `FUNDAMENTAL`, `MACRO`, `NEWS`, `ANNOUNCEMENT`, `SENTIMENT`, `MARKET_STATE` | FTS 分类法，按数据结构特征划分数据类型 |
| `MarketType` | `FUTURES`, `STOCK`, `ETF`, `CB`(可转债), `REIT` | 支持的市场类型 |
| `SourceGrade` | `PRIMARY` > `DAILY` > `CACHED` > `STALE` > `UNAVAILABLE` | 数据质量等级，从高到低排列 |

`SourceGrade` 是 AI-Native 设计的核心：AI Agent 根据等级决定数据的使用策略（PRIMARY 可用于交易决策，DAILY/CACHED 可用于分析，STALE/UNAVAILABLE 应跳过或触发通知）。

#### ohlcv.py — K线与行情数据结构

- **`KBar`**: 单根 K 线数据
  - 字段: `date`, `open`, `high`, `low`, `close`, `volume`, `amount`, `open_interest`, `settlement`
  - `open_interest`(持仓量) 和 `settlement`(结算价) 为期货特有字段，可选

- **`KlineData`**: K 线数据集
  - 字段: `symbol`, `period`, `bars: list[KBar]`, `source`, `contract`
  - 聚合多根 KBar，附带数据源和合约信息

- **`QuoteData`**: 实时行情快照
  - 字段: `symbol`, `source`, `last_price`, `open`, `high`, `low`, `pre_close`, `volume`, `amount`, `bid_price`, `ask_price`, `change_pct`, `update_time`
  - 包含五档买卖盘口

#### payload.py — 统一数据载荷信封

- **`DataPayload`**: 所有 API 返回的统一信封
  - 字段: `symbol`, `data_type`, `market`, `data`, `source`, `grade`, `collected_at`, `meta`, `errors`, `warnings`
  - 属性: `available` — 检查数据是否可用 (`grade != UNAVAILABLE`)

```python
@dataclass
class DataPayload:
    symbol: str
    data_type: DataType
    market: MarketType
    data: Any = None          # 实际数据 (KlineData / QuoteData / dict 等)
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

**路径**: `datacore/registry/`

负责符号解析和市场路由，是 `UnifiedDataProvider` 判断"请求属于哪个市场"的依据。

#### SymbolEntry

单个符号条目的数据类：
- `symbol`: 符号代码 (如 `"RB"`, `"600519"`)
- `name`: 中文名称 (如 `"螺纹钢"`)
- `market`: 所属市场 (`MarketType`)
- `sector`: 所属板块/行业
- `is_active`: 是否活跃

#### SymbolRegistry

核心功能：
- `__init__()`: 初始化时调用 `_init_builtin()` 注册 56 个内置期货品种
- `_init_builtin()`: 硬编码内置期货品种表，按行业板块分组：
  - **黑色系**: RB(螺纹钢), HC(热卷), I(铁矿石), J(焦炭), JM(焦煤), SF(硅铁), SM(锰硅)
  - **能源链**: SC(原油), LU(低硫燃油), FU(燃油), BU(沥青), PG(液化气), PX(对二甲苯)
  - **聚酯链**: TA(PTA), PF(短纤), EG(乙二醇), EB(苯乙烯)
  - **塑化链**: V(PVC), PP(聚丙烯), L(聚乙烯), MA(甲醇)
  - **化工**: SA(纯碱), UR(尿素), SH(烧碱)
  - **有色金属**: CU(沪铜), AL(沪铝), ZN(沪锌), PB(沪铅), NI(沪镍), SN(沪锡), AO(氧化铝), SS(不锈钢)
  - **贵金属**: AU(黄金), AG(白银)
  - **油脂油料**: A(豆一), B(豆二), M(豆粕), Y(豆油), P(棕榈油), OI(菜油), RM(菜粕), PK(花生)
  - **农产品**: C(玉米), CS(淀粉), SR(白糖), CF(棉花), JD(鸡蛋), LH(生猪)
  - **建材化工**: FG(玻璃), RU(橡胶), NR(20号胶), BR(丁二烯胶), SP(纸浆)
  - **新能源**: LC(碳酸锂), SI(工业硅)
  - **航运**: EC(欧线集运)
- `register(symbol, name, market, sector, is_active)`: 动态注册新符号
- `resolve(symbol)`: 解析符号，返回 `SymbolEntry` 或 `None`
- `resolve_market(symbol)`: 解析符号所属市场
- `list_by_market(market)`: 按市场列举符号
- `list_all()`: 列举所有符号

> **注意**: A股/ETF/可转债等非期货品种未预注册到注册表中。注册表仅管理期货品种的静态列表，A股符号通过代码前缀 (`6`=沪市, `0`=`3`=深市) 在 Provider 层动态识别。

---

### 4.4 store — 存储层

**路径**: `datacore/store/`

提供热数据内存缓存和冷数据持久化能力，支持三种后端：

| 后端 | 文件 | 默认 | 适用场景 |
|------|------|------|----------|
| MemoryCache | `cache.py` | 是 | 进程内热缓存，零依赖 |
| DuckDBStore | `duckdb.py` | 是 | 本地冷数据持久化，OLAP 优化 |
| PostgresStore | `postgres.py` | 否 | 分布式部署，跨进程共享 |
| RedisStore | `redis.py` | 否 | 热缓存共享，跨进程失效通知 |

#### MemoryCache (`cache.py`)

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

#### DuckDBStore (`duckdb.py`)

DuckDB 持久化存储引擎，用于冷数据持久化（默认后端）：
- `init_schema()`: 创建三张表（幂等操作）
  - `kline_cache`: K线缓存 (PK: symbol, period, date)
  - `quote_cache`: 行情快照缓存
  - `macro_cache`: 宏观数据缓存 (PK: indicator, date)
- `close()`: 关闭连接
- 数据库路径从配置系统获取

#### PostgresStore (`postgres.py`)

PostgreSQL 持久化存储引擎（可选后端）：
- `init_schema()`: 创建四张表（幂等操作），包含 `datacore_cache` 用于通用缓存
- 缓存接口: `cache_get`, `cache_set`, `cache_invalidate`, `cache_purge`
- 配置方式: 环境变量 `DATACORE_STORE_POSTGRESQL_DSN` 或 YAML 文件
- 可选依赖: `psycopg2-binary`

#### RedisStore (`redis.py`)

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

**路径**: `datacore/equity/`

提供 A股、ETF、可转债、REITs 的统一数据获取。

#### EquityDataProvider (`equity_provider.py`)

A股数据统一入口，维护多源降级链：
- 数据源列表: `[TencentProvider(), EastMoneyEquityProvider()]`
- `get(symbol, data_type, params)`: 按优先级遍历数据源，第一个成功返回的即为结果
- 所有源都失败时返回 `UNAVAILABLE` 级别的 `DataPayload`

#### EquityDataSource 抽象基类 (`providers/base.py`)

| 属性/方法 | 说明 |
|-----------|------|
| `name` | 数据源名称 |
| `priority` | 优先级 (0=最高) |
| `supported_types` | 支持的数据类型集合 |
| `supported_markets` | 支持的市场类型 (默认: STOCK, ETF, CB, REIT) |
| `fetch(symbol, data_type, params)` | 抽象方法 — 获取数据 |
| `check_available()` | 检查数据源是否可用 |

#### TencentProvider (`providers/tencent.py`) — P0 源

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

#### EastMoneyEquityProvider (`providers/eastmoney.py`) — P1 源

东方财富公开 API，A股备用数据源：
- 优先级: 1
- 支持类型: `OHLCV`, `FINANCIAL`, `MACRO`
- 核心方法:
  - `_fetch_kline(symbol, params)`: 通过 `push2his.eastmoney.com` 获取 K 线
  - `_fetch_financial(symbol)`: 获取 PE/PB 等财务指标
  - `_fetch_macro()`: 获取 PMI 等宏观数据
- 辅助函数: `_f(v)` — 安全类型转换

#### financial.py — 财务评分工具

`calc_financial_score(fin)`: 简单财务评分计算
- `value_score`: 基于 PE/PB 的估值评分
- `growth_score`: (预留)
- `quality_score`: (预留)
- `composite`: 综合评分

---

### 4.6 futures — 期货数据模块

**路径**: `datacore/futures/`

提供中国期货市场 56+ 个品种的统一数据获取。

#### FuturesDataProvider (`futures_provider.py`)

期货数据统一入口，维护多源降级链：
- 数据源列表: `[TdxLcProvider(), EastMoneyFuturesProvider()]`
- `get(symbol, data_type, params)`: 按数据类型路由
  - `OHLCV` -> `_get_kline()`
  - `QUOTE` -> `_get_quote()`
  - 其他类型返回 None
- 降级逻辑: 按优先级遍历源，第一个成功返回的赋予 `PRIMARY` 等级，后续回退源返回 `DAILY` 等级

#### FuturesDataSource 抽象基类 (`providers/base.py`)

| 属性/方法 | 说明 |
|-----------|------|
| `name` | 数据源名称 |
| `priority` | 优先级 |
| `supported_types` | 支持的数据类型集合 |
| `fetch_kline(symbol, period, days)` | 抽象方法 — 获取 K 线 |
| `fetch_quote(symbol)` | 抽象方法 — 获取行情 |
| `check_available()` | 检查数据源是否可用 |

#### TdxLcProvider (`providers/tdx_lc.py`) — P0 源

通达信本地 HTTP 服务 (TQ-Local)，期货首选数据源：
- 优先级: 0 (最高)
- 支持类型: `OHLCV`, `QUOTE`, `TECHNICAL`
- 配置方式: 从统一配置系统获取 URL 和超时时间
- 通信方式: JSON-RPC over HTTP
- 合约解析: `_load_contracts()` 通过 `get_stock_list` API 获取合约列表，提取字母前缀作为品种代码
- K线周期映射: `{"daily": "1d", "60m": "60m", "120m": "120m", "240m": "240m", "weekly": "1w"}`
- 关键方法:
  - `_post(method, params)`: JSON-RPC 调用
  - `_resolve_contract(symbol)`: 品种代码 -> 具体合约代码
  - `fetch_kline(symbol, period, days)`: 获取 K 线（含持仓量）
  - `fetch_quote(symbol)`: 获取实时行情快照

#### EastMoneyFuturesProvider (`providers/eastmoney.py`) — P1 源

东方财富公开 API，期货备用数据源：
- 优先级: 1
- 支持类型: `OHLCV`
- 与 A股 EastMoney 类似，但 secid 使用 `CF.{symbol}` 格式
- `fetch_quote()` 返回 None（不支持期货行情）

---

### 4.7 api — 统一数据入口

**路径**: `datacore/api.py`

`UnifiedDataProvider` 是整个系统的门面类，所有消费者通过此接口获取数据。

```python
class UnifiedDataProvider:
    def __init__(self):
        self.registry = SymbolRegistry()

    def get(self, symbol, data_type, params=None) -> DataPayload:
        # 1. 通过 registry.resolve_market() 判断市场类型
        # 2. 期货 -> FuturesDataProvider
        # 3. 股票/ETF/可转债/REITs -> EquityDataProvider
        # 4. 未知符号 -> UNAVAILABLE

    def get_batch(self, symbols, data_type, params=None) -> dict[str, DataPayload]:
        # 批量获取

    def list_symbols(self, market=None) -> list[dict]:
        # 列出所有/指定市场符号
```

**路由逻辑**:
```
get("RB", DataType.OHLCV)
  -> resolve_market("RB") = MarketType.FUTURES
  -> FuturesDataProvider.get("RB", OHLCV)

get("600519", DataType.QUOTE)
  -> resolve_market("600519") = None (A股未预注册)
  -> equity provider handles it

get("ZZZ", DataType.OHLCV)
  -> resolve_market("ZZZ") = None
  -> 返回 UNAVAILABLE (含错误信息 "Unknown symbol: ZZZ")
```

**懒加载模式**: `_get_futures()` 和 `_get_equity()` 使用模块级全局变量和懒加载，推迟 Provider 的导入和实例化。

---

### 4.8 cli — 命令行工具

**路径**: `datacore/cli.py`

命令行入口，通过 `pyproject.toml` 注册为 `datacore` 命令：

| 命令 | 功能 |
|------|------|
| `datacore list` | 列出所有注册的标的 |
| `datacore status` | 查看版本和状态 |
| `datacore quote <symbol>` | 查询某个标的行情 |

```bash
# 示例
datacore list
datacore status
datacore quote RB
datacore quote 600519
```

---

## 5. 数据流与降级链

### A股数据流

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

### 降级链总览

| 市场 | P0 (PRIMARY) | P1 (DAILY) | P2 (备用) |
|------|-------------|------------|-----------|
| 期货 | TQ-Local (通达信本地, JSON-RPC) | 东方财富 (公开 HTTP API) | — |
| A股 | 腾讯 (HTTP API, qt.gtimg.cn) | 东方财富 (公开 HTTP API) | — |

---

## 6. 配置说明

### 配置优先级

配置加载优先级（从高到低）：
1. **环境变量**: `DATACORE_*` 前缀
2. **YAML 文件**: `config/settings.yaml` 或 `~/.datacore/settings.yaml`
3. **代码默认值**: 硬编码的默认值

### 配置文件

**路径**: `config/settings.yaml`

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
| 缓存 TTL | `DATACORE_STORE_CACHE_TTL` |
| DuckDB 路径 | `DATACORE_STORE_DUCKDB_PATH` |
| PostgreSQL DSN | `DATACORE_STORE_POSTGRESQL_DSN` |
| Redis URL | `DATACORE_STORE_REDIS_URL` |
| 存储后端 | `DATACORE_STORE_BACKEND` |

### 配置示例

#### 开发环境

```bash
# 使用默认配置即可，无需额外设置
pip install -e "datacore[store]"
```

#### 生产环境（使用 PostgreSQL）

```bash
# 设置环境变量
export DATACORE_STORE_BACKEND=postgres
export DATACORE_STORE_POSTGRESQL_DSN="postgresql://user:password@localhost:5432/datacore"

# 安装 PostgreSQL 依赖
pip install -e "datacore[postgres]"
```

#### 生产环境（使用 Redis + PostgreSQL）

```bash
export DATACORE_STORE_REDIS_URL="redis://localhost:6379/0"
export DATACORE_STORE_POSTGRESQL_DSN="postgresql://user:password@localhost:5432/datacore"

pip install -e "datacore[full]"
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
pip install -e datacore

# 带 DuckDB 存储
pip install -e "datacore[store]"

# 带 PostgreSQL
pip install -e "datacore[postgres]"

# 带 Redis
pip install -e "datacore[redis]"

# 完整安装（所有依赖）
pip install -e "datacore[full]"
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

# 批量查询
results = dc.get_batch(['RB', 'CU', 'AU'], DataType.OHLCV)
for sym, payload in results.items():
    print(f"{sym}: {payload.grade}")

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

# 使用 PostgreSQL 后端
from datacore.store.postgres import build_postgres_store

pg_store = build_postgres_store()
if pg_store:
    pg_store.cache_set("test_key", "test_value", 3600)
    value = pg_store.cache_get("test_key")
    print(f"PostgreSQL 缓存值: {value}")

# 使用 Redis 后端
from datacore.store.redis import build_redis_store

redis_store = build_redis_store()
if redis_store:
    redis_store.cache_set("test_key", "test_value", 3600)
```

### 命令行使用

```bash
datacore list        # 列出所有标的
datacore status      # 查看状态信息
datacore quote RB    # 查询螺纹钢行情
```

### 测试

```bash
cd datacore
python -m pytest tests/ -v

# 运行指定测试
python -m pytest tests/test_api.py -v
python -m pytest tests/test_store.py -v
python -m pytest tests/test_models.py -v
python -m pytest tests/test_registry.py -v
python -m pytest tests/test_equity_mock.py -v
python -m pytest tests/test_futures_mock.py -v
```

**测试覆盖** (共 29 个测试用例):

| 测试文件 | 测试内容 | 用例数 |
|----------|---------|--------|
| `test_api.py` | UnifiedDataProvider 基本功能 | 4 |
| `test_models.py` | 枚举、Payload、K线数据结构 | 5 |
| `test_registry.py` | 符号注册表解析与路由 | 5 |
| `test_store.py` | 内存缓存 (TTL/过期/清理) | 5 |
| `test_equity_mock.py` | TencentProvider Mock 测试 | 4 |
| `test_futures_mock.py` | TdxLcProvider Mock 测试 | 4 |
| `conftest.py` | 测试路径配置 | — |

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

### 零依赖说明

Data-Core 刻意避免依赖以下常见金融数据包：
- **akshare**: 零依赖，自实现 HTTP 数据源
- **tushare**: 同上
- **任何 MCP Server**: 自包含设计
- **任何外部 Skill**: 无需 Agent 运行时支持

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
  |   - TdxLcProvider 从配置系统获取 URL 和超时
  |   - 检查 check_available()
  |   - 检查 supported_types
  |   - 调用 fetch_kline()
  |
  4. 成功 -> 包装为 DataPayload (含 source/grade/collected_at)
  |   失败 -> 尝试下一个源
  |
  5. 全部失败 -> DataPayload(grade=UNAVAILABLE)
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
