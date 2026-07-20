# Data-Core — AI-Native 量化数据基础设施

> 版本: v1.0.0 | AI-Native 量化研究数据基础设施
> 领域: 期货与证券 AI 驱动量化分析

## 核心理念

Data-Core 是一个 AI-Native 数据基础设施，专为 LLM 驱动的量化研究场景设计。
与传统面向人类分析师的量化数据系统不同，Data-Core 提供：

1. **AI 可溯源**: 每个数据点都携带 source + grade + freshness 元数据，
   AI Agent 可以在决策前评估数据可靠性。
2. **自描述 Schema**: 数据模型使用明确的 dataclass 定义，
   Python 和 LLM 均可通过结构化反射消费。
3. **优雅降级**: 多源回退链 + 熔断器 + LLM→规则降级，三层保护，
   永不硬失败，而是返回 UNAVAILABLE 等级而非抛出异常。
4. **零外部依赖**: 自包含的 HTTP 数据源，无需 MCP/Skill/Agent 依赖。
   单 pip install 即可在任何研究环境中使用。
5. **可观测性**: 健康检查、熔断器状态、指标收集、告警引擎四大支柱，
   覆盖所有数据源调用。

## 架构

### 数据流（AI-Native 视图）

```
AI Agent / 策略
      |
      | get(symbol, data_type) -> DataPayload { data + grade + source + meta }
      v
UnifiedDataProvider (api.py)
      |
      +-- futures/      TQ-Local -> EastMoney -> ExchangeAPI -> ShengYiShe
      |    56+ 合约品种, 合约链/期限结构/价差/基差/持仓/仓单
      |
      +-- equity/       Tencent -> EastMoney -> Guosen
      |    A股, ETF, 可转债, REITs, 财务数据
      |
      +-- macro/        国家统计局 -> 央行 -> 东方财富
      |    CPI/PPI/GDP/PMI/M2/LPR
      |
      +-- news/         财联社 -> 华尔街见闻 -> 东方财富研报
      |    新闻采集 + 关键词分类
      |
      +-- processing/   数据加工层
      |    情绪打分 (LLM优先, 规则降级)
      |    市场制度检测 (bull/bear/sideways)
      |    基本面LLM加工 (研报摘要 + 财报提取)
      |
      +-- stream/       WebSocket 实时行情 (v1.0.0)
      +-- alert/        告警引擎 (价格/波动率/数据延迟/熔断)
      +-- store/        MemoryCache(L1) -> DuckDB(L2) -> HTTP源(L3)
      +-- breaker/      熔断器 CLOSED/OPEN/HALF_OPEN
      +-- metrics/      MetricsCollector 指标收集
      +-- registry/     SymbolRegistry (市场路由, 56+ 品种)
      +-- config/       DataCoreConfig (环境变量 + YAML)
      +-- models/       DataType/MarketType/SourceGrade/DataPayload
```

### AI 可消费的数据契约

每个 API 响应都返回 DataPayload，一个对 AI 友好的结构化信封：

```python
@dataclass
class DataPayload:
    symbol: str          # 查询符号
    data_type: DataType  # 数据类型
    market: MarketType   # 市场类型
    data: Any            # 实际数据 (KlineData, SentimentData 等)
    source: str          # 数据来源
    grade: SourceGrade   # PRIMARY / DAILY / CACHED / STALE / UNAVAILABLE
    collected_at: float  # 采集时间
    errors: list[str]    # 遇到的错误
    warnings: list[str]  # 警告信息
```

AI Agent 可以据此决策：
- `PRIMARY` 数据可用于交易决策
- `DAILY`/`CACHED` 数据可用于分析
- `STALE`/`UNAVAILABLE` 应跳过或触发告警

### 数据源降级链

| 市场 | P0 | P1 | P2 | P3 |
|------|----|----|----|----|
| 期货 | TQ-Local (私有) | EastMoney (公开 API) | 交易所官方 (公开 API) | 生意社 (公开 API) |
| A股 | Tencent (公开 API) | EastMoney (公开 API) | 国信证券 (需 API-KEY) | — |
| 宏观 | 国家统计局 (公开) | 央行 (公开) | 东方财富 (公开 API) | — |
| 新闻 | 财联社 (公开) | 华尔街见闻 (公开) | 东方财富研报 (公开) | — |

所有数据源都是自包含的 HTTP 实现 —— 无需外部 MCP，无需 Skill 依赖。
系统可以完全离线运行（通过 DuckDB 缓存）或在线运行（通过 HTTP 数据源）。

### 数据复权说明

| 市场 | adjustment 参数 | 说明 |
|:-----|:----------------|:-----|
| A 股/ETF/可转债/REITs | `"qfq"` / `"hfq"` / `"none"` | **Data-Core 复权引擎计算**，基于除权除息日历 |
| 期货 | `"continuous"` / `"continuous_qfq"` / `"none"` | **Data-Core 复权引擎计算**，主力连续拼接+多种换月算法 |

**v1.0**: 复权由数据源 API 参数处理（前复权），期货换月由消费方自行处理。
**v2.0+**: Data-Core 统一复权/换月引擎，消费端通过 `adjustment` 参数声明需求。

### 周期转换

Data-Core 支持跨周期 K 线转换，处理管线为：`原始数据 → 复权/换月引擎 → 周期转换引擎 → 消费端`。

| period 值 | 说明 | 聚合规则 |
|:----------|:-----|:---------|
| `"1m"` ~ `"60m"` | 分钟级 | O=first, H=max, L=min, C=last, V=sum |
| `"daily"` | 日线（默认） | 当日所有分钟聚合 |
| `"weekly"` | 周线（周一为起始） | 5 根日线→1 根周线 |
| `"monthly"` | 月线 | 当月日线→1 根月线 |
| `"auto"` | 自动选择最合适周期 | 按数据量自动判断 |

**约束**: 只能从细粒度→粗粒度。请求比 Provider 最细粒度还细的周期时，返回错误+建议。

### 三层缓存架构

```
请求: dc.get("RB", DataType.OHLCV)
  |
  1. MemoryCache (L1, 进程内热缓存)
  |   TTL: 3600s, 命中即返回
  |   未命中 → 继续
  |
  2. DuckDB (L2, 本地持久化)
  |   查询 kline_cache 表
  |   命中且新鲜 → 返回 CACHED 等级
  |   未命中/过期 → 继续
  |
  3. HTTP 数据源 (L3, 多源降级链)
       TQ-Local → EastMoney → ...
       成功 → 写回 L1 + L2
```

### 情绪数据加工管线

```
NEWS (采集+分类)
  |
  +-- [P0] LLM 情绪打分 (需 API Key)
  |     → SentimentItem(score, confidence, source="llm")
  |
  +-- [P1] 规则基线 (词典法, 零成本)
  |     → SentimentItem(score, confidence=0.5, source="rule_fallback")
  |
  +-- SentimentAggregator
        → 时间衰减加权 + 置信度加权 + 按日聚合
        → SentimentData(overall_score, daily_series, topics)
```

### AI Pipeline 集成

```python
from datacore import UnifiedDataProvider
from datacore.models.enums import DataType, SourceGrade

dc = UnifiedDataProvider()

# AI Agent 在交易前检查数据质量
payload = dc.get('RB', DataType.OHLCV, {'period': 'daily', 'days': 400})
if payload.grade >= SourceGrade.DAILY:
    kline = payload.data
else:
    print(f'数据质量不足: {payload.grade}')

# 情绪数据
sentiment = dc.get('RB', DataType.SENTIMENT, {'days': 30})
if sentiment.available:
    print(f"情绪: {sentiment.data.overall_score} (来源: {sentiment.source})")

# 健康检查
health = dc.get_health()
if health['status'] == 'healthy':
    print("所有数据源正常")
```

### 依赖关系（最小化）

必需: numpy, pandas, httpx, pyyaml
可选: duckdb, psycopg2-binary, redis, beautifulsoup4, websockets

零依赖: akshare, tushare, 任何 MCP Server, 任何外部 Skill。
