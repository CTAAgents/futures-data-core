# Data-Core

AI-Native 量化数据基础设施 — 面向中国期货与证券市场的统一数据接口。

## 安装

```bash
# 基础安装（仅核心功能）
pip install -e .

# 带 DuckDB 存储
pip install -e ".[store]"

# 带 PostgreSQL
pip install -e ".[postgres]"

# 带 Redis
pip install -e ".[redis]"

# 完整安装（所有依赖）
pip install -e ".[full]"
```

## 快速开始

```python
from datacore import UnifiedDataProvider
from datacore.models.enums import DataType

dc = UnifiedDataProvider()

# 期货 K 线
rb = dc.get('RB', DataType.OHLCV, {'period': 'daily', 'days': 400})

# A股行情
kweichow = dc.get('600519', DataType.QUOTE)
fin = dc.get('600519', DataType.FINANCIAL)

# 宏观数据
macro = dc.get('*', DataType.MACRO)

# 情绪数据
sentiment = dc.get('RB', DataType.SENTIMENT, {'days': 30})

# 市场制度检测
regime = dc.get('RB', DataType.MARKET_STATE, {'period': 'daily', 'days': 120})
```

## 设计原则

- **AI Native**: 所有数据返回携带溯源元数据（source, grade, freshness），供 LLM 决策
- **数据加工层**: Data-Core 负责从原始数据到可消费结构化数据的转换（含 LLM 情绪打分+市场制度检测）
- **零外部依赖**: 自包含 HTTP 数据源，单 pip install 即可使用
- **优雅降级**: 多源回退链 + 熔断器 + LLM→规则降级，三层保护，永不硬失败
- **市场无关**: 统一 API 覆盖期货、股票、ETF、可转债、REITs
- **三层缓存**: MemoryCache (L1) → DuckDB (L2) → HTTP 源 (L3)

## 架构

```
UnifiedDataProvider
  +-- futures/    TQ-Local -> EastMoney -> ExchangeAPI -> ShengYiShe
  +-- equity/     Tencent -> EastMoney -> Guosen
  +-- macro/      NationalBureau -> PboC -> EastMoney
  +-- news/       Cls -> WallStreetCn -> EastMoneyResearch
  +-- processing/ SentimentLLM -> RuleBase + MarketRegimeDetector
  +-- store/      MemoryCache + DuckDB/PostgreSQL/Redis
  +-- registry/   SymbolRegistry (56+ 期货品种)
  +-- config/     DataCoreConfig (环境变量 + YAML)
  +-- models/     DataType / MarketType / SourceGrade / DataPayload
  +-- breaker/    CLOSED/OPEN/HALF_OPEN 熔断器
  +-- metrics/    MetricsCollector 指标收集
```

## 数据源列表

| 数据源 | 市场 | 优先级 | 是否需要配置 |
|:-------|:-----|:-------|:-------------|
| 腾讯财经 | A股 | P0 | 否 |
| 东方财富 | A股/期货/宏观 | P1 | 否 |
| 财联社 | 新闻 | P0 | 否 |
| 华尔街见闻 | 新闻 | P1 | 否 |
| 东方财富研报 | 新闻 | P2 | 否 |
| 国家统计局 | 宏观 | P0 | 否 |
| 央行 | 宏观 | P1 | 否 |
| 通达信 TQ-Local | 全市场 | P0 | 需要安装客户端 |
| 交易所官方 | 期货基本面 | P0 | 否 |
| 生意社 | 期货基差 | P1 | 否 |
| 国信证券 | A股 | P2 | 需要 API-KEY |

## 数据源配置

### 通达信 TQ-Local（需要安装客户端）

```yaml
# config/settings.yaml
sources:
  tdx_lc:
    enabled: true
    url: http://127.0.0.1:17709/
    timeout: 3
```

### 国信证券（需要 API-KEY）

```bash
export DATACORE_SOURCES_GUOSEN_API_KEY=YOUR_API_KEY
```

## 配置说明

### 配置优先级（从高到低）

1. **环境变量**: `DATACORE_*` 前缀
2. **YAML 文件**: `config/settings.yaml` 或 `~/.datacore/settings.yaml`
3. **代码默认值**: 硬编码的默认值

### 完整配置示例

```yaml
# config/settings.yaml
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

## 测试

```bash
cd datacore
python -m pytest tests/ -v   # 724+ 个测试用例
```

## 文档

- [ARCHITECTURE.md](ARCHITECTURE.md) - 架构设计文档
- [CODE_WIKI.md](CODE_WIKI.md) - 项目说明书（动态文档）
- [PRODUCTION_PLAN.md](docs/PRODUCTION_PLAN.md) - 生产就绪路线图（v0.5.0 → v1.0.0）
- [UNIFIED_DATA_HUB_PLAN.md](docs/UNIFIED_DATA_HUB_PLAN.md) - 统一数据中枢升级方案（v1.0 → v2.0）
- [docs/harness/](docs/harness/) - HARNESS 工程规范文档 (09 份)
- [CLAUDE.md](CLAUDE.md) - AI 编码行为准则

## 版本

v2.0.0 (2026-07-19) - 统一数据中枢版：BaseTool 接口层 + 指标体系 + 复权/换月引擎 + 周期转换 + FDT 兼容 + Qlib 适配器 + 清洗/校验/采集/运维工具链
v1.3.0 (2026-07-19) - 扩展能力版：复权/换月引擎 + 周期转换 + 消费者反馈通道 + 清洗/校验/运维工具
v1.2.0 (2026-07-19) - FDC 吸收版：40+ 技术指标 + 3 个期货新数据源 + 趋势成熟度评估
v1.1.0 (2026-07-19) - 基础设施+双接口版：AsyncDataProvider 异步接口 + F10 综合报告 + core 共享模块
v1.0.0 (2026-07-19) - 生产就绪版：WebSocket 实时行情 + 告警系统 + 性能基准 + 安全加固
