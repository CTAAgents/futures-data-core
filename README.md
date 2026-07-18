# Data-Core

AI-Native 量化数据基础设施 — 面向中国期货与证券市场的统一数据接口。

## 安装

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
```

## 设计原则

- **AI Native**: 所有数据返回携带溯源元数据（source, grade, freshness），供 LLM 决策
- **零外部依赖**: 自包含 HTTP 数据源，单 pip install 即可使用
- **优雅降级**: 多源回退链，永不硬失败
- **市场无关**: 统一 API 覆盖期货、股票、ETF、可转债、REITs

## 架构

```
UnifiedDataProvider
  +-- futures/    TQ-Local -> EastMoney
  +-- equity/     Tencent -> EastMoney -> Guosen
  +-- store/      MemoryCache + DuckDB/PostgreSQL/Redis
  +-- registry/   SymbolRegistry (56+ 期货品种)
  +-- config/     DataCoreConfig (环境变量 + YAML)
  +-- models/     DataType / MarketType / SourceGrade / DataPayload
```

## 数据源部署指南

### 1. 腾讯自选股数据源（默认启用，无需 API-KEY）

**特点**: 公开 HTTP API，无需注册，无需安装客户端

**配置**: 无需额外配置，系统自动使用

**API 地址**:
- 行情: `http://qt.gtimg.cn/q={market}{symbol}`
- K线: `http://web.ifzq.gtimg.cn/appstock/app/fqkline/get`

**数据范围**: A股、ETF、可转债实时行情和 K线数据

---

### 2. 通达信 TQ-Local 数据源（需要安装客户端）

**特点**: 本地 HTTP 服务，需要安装通达信客户端并启动 TQ-Local 服务

**安装步骤**:

1. **安装通达信客户端**:
   - 下载地址: https://www.tdx.com.cn/
   - 安装完成后，确保可以正常登录行情

2. **安装 TQ-Local 插件**:
   - TQ-Local 是通达信的 HTTP API 插件
   - 安装后会在本地启动 HTTP 服务，默认端口 `17709`

3. **启动服务**:
   - 打开通达信客户端
   - 确保 TQ-Local 插件已启用
   - 服务启动后访问: `http://127.0.0.1:17709/` 应返回 JSON-RPC 响应

**配置**:

```yaml
# config/settings.yaml
sources:
  tdx_lc:
    enabled: true
    url: http://127.0.0.1:17709/
    timeout: 3
```

或通过环境变量：

```bash
export DATACORE_SOURCES_TDX_LC_URL=http://127.0.0.1:17709/
export DATACORE_SOURCES_TDX_LC_TIMEOUT=3
```

**API 地址**: `http://127.0.0.1:17709/`（默认）

**数据范围**: 期货、股票、ETF 全市场行情和 K线数据

---

### 3. 东方财富数据源（默认启用，无需 API-KEY）

**特点**: 公开 HTTP API，无需注册，无需安装客户端

**配置**: 无需额外配置，系统自动使用

**API 地址**:
- A股 K线: `https://push2his.eastmoney.com/api/qt/stock/kline/get`
- A股行情: `https://push2.eastmoney.com/api/qt/stock/get`
- 期货 K线: `https://push2his.eastmoney.com/api/qt/stock/kline/get` (secid=CF.{symbol})

**数据范围**: A股、ETF、期货 K线数据，财务指标，宏观数据

---

### 4. 国信证券数据源（需要 API-KEY，开发中）

**特点**: 需要国信证券金工技能平台的 API-KEY，仅需单个 KEY

**安装步骤**:

1. **注册国信开发者账号**:
   - 访问国信证券金工技能平台: https://www.guosen.com.cn/gs/xxskills/index.html
   - 完成注册并创建应用

2. **获取 API-KEY**:
   - 在金工技能平台创建应用后，获取唯一的 API-KEY

3. **配置 API-KEY**:

```yaml
# config/settings.yaml
sources:
  guosen:
    enabled: true
    api_key: YOUR_API_KEY
    url: https://api.guosen.com.cn/
    timeout: 5
```

或通过环境变量（推荐）：

```bash
export DATACORE_SOURCES_GUOSEN_API_KEY=YOUR_API_KEY
```

> **安全警告**: API-KEY 是敏感信息，**禁止**写入代码或提交到版本控制。生产环境应通过环境变量注入。

**数据范围**: A股、ETF、可转债、REITs 全量数据（开发中）

---

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
    app_key:
    app_secret:
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

## 测试

```bash
cd datacore
python -m pytest tests/ -v   # 29 个测试用例
```

## 文档

- [CODE_WIKI.md](CODE_WIKI.md) - 完整的代码 Wiki 文档
- [ARCHITECTURE.md](ARCHITECTURE.md) - 架构设计文档
- [docs/harness/](docs/harness/) - HARNESS 工程规范文档 (09 份)
- [docs/harness/08-gap-analysis.md](docs/harness/08-gap-analysis.md) - 已知差距与路线图

## 版本

v0.1.0 (2026-07-18) - Initial AI-Native Quant Data Infrastructure
