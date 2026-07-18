# Data-Core — AI-Native 量化数据基础设施

> 版本: v0.1.0 | AI-Native 量化研究数据基础设施
> 领域: 期货与证券 AI 驱动量化分析

## 核心理念

Data-Core 是一个 AI-Native 数据基础设施，专为 LLM 驱动的量化研究场景设计。
与传统面向人类分析师的量化数据系统不同，Data-Core 提供：

1. **AI 可溯源**: 每个数据点都携带 source + grade + freshness 元数据，
   AI Agent 可以在决策前评估数据可靠性。
2. **自描述 Schema**: 数据模型使用明确的 TypedDict/dataclass 定义，
   Python 和 LLM 均可通过结构化反射消费。
3. **优雅降级**: 多源回退链保证 AI Pipeline 不会因数据问题硬失败，
   而是返回 UNAVAILABLE 等级而非抛出异常。
4. **零外部依赖**: 自包含的 HTTP 数据源，无需 MCP/Skill/Agent 依赖。
   单 pip install 即可在任何研究环境中使用。

## 架构

### 数据流（AI-Native 视图）

```
AI Agent / 策略
      |
      | get(symbol, data_type) -> DataPayload { data + grade + source + meta }
      v
UnifiedDataProvider
      |
      +-- futures/      TQ-Local -> EastMoney
      |    56 个合约品种, 仓单, 基差, 宏观
      |
      +-- equity/       Tencent -> EastMoney -> Guosen
      |    A股, ETF, 可转债, REITs
      |
      +-- store/        MemoryCache + DuckDB 持久化
      +-- registry/     SymbolRegistry (市场路由)
      +-- config/       DataCoreConfig (环境变量 + YAML)
      +-- models/       DataType/MarketType/SourceGrade/DataPayload
```

### AI 可消费的数据契约

每个 API 响应都返回 DataPayload，一个对 AI 友好的结构化信封：

```python
@dataclass
class DataPayload:
    symbol: str          # 查询符号
    data: Any            # 实际数据 (KlineData, dict 等)
    source: str          # 数据来源
    grade: SourceGrade   # PRIMARY / DAILY / CACHED / STALE / UNAVAILABLE
    collected_at: float  # 采集时间
    errors: list[str]    # 遇到的错误
```

AI Agent 可以据此决策：
- 使用 PRIMARY 数据进行交易决策
- 使用 DAILY/CACHED 数据进行分析
- 跳过 STALE/UNAVAILABLE 或触发人工通知

### 数据源降级链

| 市场 | P0 | P1 | P2 |
|------|----|----|----|
| 期货 | TQ-Local (私有) | EastMoney (公开 API) | TQSDK (可选) |
| A股 | Tencent (公开 API) | EastMoney (公开 API) | Guosen (公开 API) |

所有数据源都是自包含的 HTTP 实现 —— 无需外部 MCP，无需 Skill 依赖。
系统可以完全离线运行（通过 DuckDB 缓存）或在线运行（通过 HTTP 数据源）。

### AI Pipeline 集成

```python
from datacore import UnifiedDataProvider
from datacore.models.enums import DataType, SourceGrade

dc = UnifiedDataProvider()

# AI Agent 在交易前检查数据质量
payload = dc.get('RB', DataType.OHLCV, {'period': 'daily', 'days': 400})
if payload.grade >= SourceGrade.DAILY:
    # 使用数据进行分析
    kline = payload.data
else:
    # 触发数据刷新或跳过
    print(f'数据质量不足: {payload.grade}')
```

### 依赖关系（最小化）

必需: numpy, pandas, httpx, pyyaml
可选: duckdb, psycopg2-binary, redis, beautifulsoup4

零依赖: akshare, tushare, 任何 MCP Server, 任何外部 Skill。
