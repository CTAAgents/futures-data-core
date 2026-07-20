# Data-Core Resilience

Version: v2.0.0 | Updated: 2026-07-20

## Degradation Strategy

### 通用降级原则
- 每个数据类型维护独立的降级链
- 按优先级从高到低依次尝试
- 单个源失败不影响其他源
- 所有源不可用则返回 `UNAVAILABLE` grade
- 网络超时：3s 快速失败，立即尝试下一个源

### 缓存层降级（v0.5.0 新增，L0 前置缓存）
在多层降级链之前，请求先经过缓存层：

```
请求 → MemoryCache (L1) → DuckDB (L2, 仅 OHLCV) → 熔断器 → 数据源链
  L1 命中: 直接返回 CACHED 数据，跳过后续所有步骤
  L1 未命中 → L2 命中: 从 DuckDB 加载，写回 MemoryCache
  L1/L2 均未命中: 走降级链获取 HTTP 数据，写回 L1 + L2
```

| 层级 | 存储 | 范围 | 延迟 |
|:-----|:-----|:-----|:-----|
| L1 | MemoryCache | 所有 DataType | <1ms |
| L2 | DuckDB | OHLCV 仅 | <5ms |

### 熔断器降级（v0.4.0 新增，第 0 级前置保护）

在多层降级链之前，所有数据源调用先经过 Breaker 熔断器：

```
调用方 → Breaker（CLOSED） → 数据源（P0）
         Breaker（OPEN）   → 直接快速失败 → 降级到下一源
         Breaker（HALF_OPEN）→ 允许探测请求
```

| 状态 | 说明 | 行为 |
|:-----|:-----|:-----|
| `CLOSED` | 正常工作 | 请求正常通过，统计失败次数 |
| `OPEN` | 熔断开启 | 请求直接快速失败，不调用实际源 |
| `HALF_OPEN` | 半开探测 | 允许有限请求通过，成功则恢复 CLOSED，失败则回到 OPEN |

**状态转换**: CLOSED → (连续失败 ≥ max_failures) → OPEN → (recovery_timeout 后) → HALF_OPEN → (探测成功) → CLOSED / (探测失败) → OPEN

### 期货行情降级链（v1.2.0 扩展为 7 源）
| 数据类型 | P0 | P1 | P2 | P3 | P4 | P5 | P6 |
|:---------|:---|:---|:---|:---|:---|:---|:---|
| OHLCV/QUOTE | TQ-Local | EastMoney | QMT | ExchangeApi | ShengYiShe | WebFallback | TqSdk |
| 合约链/期限结构/价差 | TQ-Local | EastMoney | QMT | ExchangeApi | ShengYiShe | WebFallback | TqSdk |

**降级说明**:
- QMT (P2): 迅投行情源，依赖 xtquant，需手动启用
- WebFallback (P5): 网页备用抓取，零额外依赖
- TqSdk (P6): 末位兜底，依赖 tqsdk，需手动启用

### 期货基本面降级链（v0.5.0 新增）
| 数据类型 | P0 | P1 |
|:---------|:---|:---|
| 基差 | 生意社（真实现货价） | 东方财富（近似算法，已修复 D01） |
| 持仓排名 | 交易所官方 | 东方财富 |
| 仓单 | 交易所官方 | 东方财富 |

### A 股降级链（v0.5.0 扩展）
| 数据类型 | P0 | P1 | P2 |
|:---------|:---|:---|:---|
| OHLCV/QUOTE | 腾讯财经 | 东方财富 | 国信证券 |

### 宏观数据降级链（v0.5.0 新增）
| 数据类型 | P0 | P1 | P2 |
|:---------|:---|:---|:---|
| 宏观指标 | 国家统计局（官方） | 央行（官方） | 东方财富（汇总） |

### 新闻资讯降级链
| 数据类型 | P0 | P1 | P2 | P3 |
|:---------|:---|:---|:---|:---|
| 快讯 | 财联社 | 华尔街见闻 | 东方财富研报 | 交易所公告 |

### 情绪数据降级链（v0.3.0 新增）
| 数据类型 | P0 (PRIMARY) | P1 (DAILY) | P2 (CACHED) |
|:---------|:-------------|:-----------|:------------|
| 情绪打分 | LLM 情绪打分 | 规则基线（词典法） | MemoryCache |

> **降级保证**: LLM 不可用时自动降级到规则基线（零成本模式），确保情绪数据始终可用。

### 技术指标计算降级链（v1.2.0 新增）

indicators 模块采用三层路由降级体系：

| 层级 | 实现 | 优先级 | 说明 |
|:-----|:-----|:-------|:-----|
| P0 | tdx_compat.py | TDX 对齐 | 通达信指标对齐实现，精度最高 |
| P1 | core.py | numpy core | 37+ 基础指标纯 numpy 实现，零额外依赖 |
| P2 | talib_wrapper.py | TA-Lib 兜底 | TA-Lib 封装，需安装 TA-Lib 库 |

```
指标计算请求 → TDX 对齐层 (P0)
  → 成功: 返回 TDX 对齐结果
  → 失败/不可用 → numpy core 层 (P1)
       → 成功: 返回 numpy 实现结果
       → 失败/不可用 → TA-Lib 兜底层 (P2)
            → 成功: 返回 TA-Lib 计算结果
            → 失败: 抛出指标计算异常
```

**降级保证**: numpy core 层为纯 Python/numpy 实现，无外部依赖，始终可用，确保指标计算基本能力不中断。

### 复权/换月降级链（v1.3.0 新增）

| 层级 | 实现 | 优先级 | 说明 |
|:-----|:-----|:-------|:-----|
| P0 | stock_adjustment / futures_rollover | 原生实现 | 纯计算实现，无外部依赖 |

**降级保证**: 复权/换月引擎为纯计算实现，始终可用，降级影响仅为精度差异。

### 周期转换降级链（v1.3.0 新增）

| 层级 | 实现 | 优先级 | 说明 |
|:-----|:-----|:-------|:-----|
| P0 | resampler + ohlcv_aggregator | 原生实现 | OHLCV 正确聚合，纯计算实现 |
| P1 | auto_detector | auto 模式 | 自动检测输入周期，可选降级到手动指定 |

**降级保证**: 周期转换为纯计算实现，始终可用，auto 模式失败时降级到手动指定周期。

### 消费者反馈降级（v1.3.0 新增）

IssueRegistry 触发自动降级应对策略：

| 问题级别 | 降级行为 |
|:---------|:---------|
| `LOW` | 记录问题，不触发降级 |
| `MEDIUM` | 标记 grade 为 STALE，触发告警 |
| `HIGH` | 触发数据源降级链切换到下一优先级源 |
| `CRITICAL` | 熔断该数据源，切换到备用源 |

```
消费者上报问题 → IssueRegistry 评估级别
  → LOW: 记录 + 返回
  → MEDIUM: 标记 STALE + 告警
  → HIGH: 触发降级链切换
  → CRITICAL: 熔断 + 切换备用源
```

### 数据清洗降级链（v1.3.0 新增）

| 层级 | 工具 | 说明 |
|:-----|:-----|:-----|
| P0 | 完整清洗链路 | UnitUnify → DateAlign → DuplicateMerge → OutlierFilter |
| P1 | 基础清洗 | UnitUnify + DateAlign（跳过高级清洗） |
| P2 | 透传模式 | 不做清洗，直接返回原始数据 |

**降级保证**: 清洗工具为纯计算实现，单个工具失败时自动跳过，确保数据可用性优先。

### 数据校验降级链（v1.3.0 新增）

| 层级 | 工具 | 说明 |
|:-----|:-----|:-----|
| P0 | 完整校验 | CrossSourceVerify + MissingDetect + CalMathCompute |
| P1 | 基础校验 | MissingDetect + CalMathCompute（跳过跨源校验） |
| P2 | 仅标记 | 不阻断数据返回，仅在 metadata 中标记校验结果 |

**降级保证**: 校验工具不阻断数据流程，仅在 metadata 中标记问题，确保数据可用性。

### FDT 兼容层降级（v2.0.0 新增）

fdc_compat.py 兼容层采用三级降级策略：

| 层级 | 模式 | 说明 |
|:-----|:-----|:-----|
| P0 | 完整兼容模式 | FDC 函数签名 + 数据格式 + 错误码完全兼容 |
| P1 | 函数签名兼容 | 保留函数签名，数据格式回退到 native 格式 |
| P2 | 透传模式 | 直接调用 Data-Core 原生接口，不做兼容转换 |

```
FDC 兼容调用 → 完整兼容模式 (P0)
  → 成功: 返回 FDC 格式结果
  → 失败/格式不兼容 → 函数签名兼容 (P1)
       → 成功: 返回 native 格式 + FDC 函数签名
       → 失败 → 透传模式 (P2)
            → 成功: 返回原生 Data-Core 结果
            → 失败: 抛出原生异常
```

**降级保证**: FDT 兼容层为纯封装实现，不影响核心数据获取能力，最坏情况回退到原生接口。

### Qlib/RD-Agent 适配器降级（v2.0.0 新增）

qlib_adapter 采用三级降级策略：

| 层级 | 模式 | 说明 |
|:-----|:-----|:-----|
| P0 | 完整 Qlib 兼容 | Qlib DataProvider 完整接口 + 表达式引擎 |
| P1 | 基础数据提供 | 提供 calendars/instruments/features 基础接口，关闭表达式引擎 |
| P2 | 原生数据访问 | 直接访问 Data-Core 原生接口，跳过 Qlib 格式转换 |

```
Qlib 适配器调用 → 完整兼容模式 (P0)
  → 成功: 返回 Qlib 标准格式
  → 表达式引擎失败 → 基础数据提供 (P1)
       → 成功: 返回基础数据（无表达式）
       → 格式转换失败 → 原生数据访问 (P2)
            → 成功: 返回 Data-Core 原生格式
            → 失败: 抛出原生异常
```

**降级保证**: Qlib 适配器为格式转换层，核心数据获取能力不受影响，最坏情况回退到原生接口。

### 市场制度检测
| 数据类型 | P0 | 说明 |
|:---------|:---|:-----|
| MARKET_STATE | MarketRegimeDetector | 纯计算，无外部依赖，始终可用 |

### WebSocket 行情降级链（v1.0.0 新增）
| 数据类型 | P0 | P1 | P2 |
|:---------|:---|:---|:---|
| 实时行情 | WebSocket 连接 | HTTP 轮询（降级到对应数据源 P0） | 缓存行情 |

#### WebSocket 重连策略（v1.0.0 新增）
| 参数 | 默认值 | 说明 |
|:-----|:-------|:-----|
| 重连间隔 | 5s | 断开后等待时间后重连 |
| 最大重连次数 | 10 | 超过后不再自动重连 |
| 心跳间隔 | 30s | 保活心跳包发送频率 |
| 重连退避策略 | 指数退避 | 每次重连间隔翻倍（5s → 10s → 20s → ...） |

```
WebSocket 连接断开 → 等待 5s → 重连
  → 成功: 恢复订阅 → 继续心跳保活
  → 失败: 等待 10s → 重连
    → 失败: 等待 20s → 重连
    → ... 直到 max_reconnect 或成功
```

### 告警引擎降级链（v1.0.0 新增）
| 通知渠道 | 优先级 | 说明 |
|:---------|:-------|:-----|
| Webhook | P0 | HTTP 回调通知，失败自动降级到文件 |
| 文件写入 | P1 | 本地文件持久化告警记录，失败降级到日志 |
| 日志记录 | P2 | 兜底渠道，始终可用 |

```
告警触发 → Webhook 发送
  → 成功: 完成
  → 失败: 降级到文件写入
    → 成功: 完成
    → 失败: 降级到日志记录（兜底）
```

### 数据新鲜度降级（v1.1.0 新增）

DataFreshnessAssessor 根据数据时间戳评估新鲜度，三级状态降级：

| 状态 | 阈值 | 降级行为 |
|:-----|:-----|:---------|
| `FRESH` | < stale_seconds（默认 300s） | 正常使用，grade 保持 PRIMARY/DAILY |
| `STALE` | stale_seconds ~ expired_seconds | 标记 grade 为 STALE，触发数据延迟告警 |
| `EXPIRED` | > expired_seconds（默认 3600s） | 标记 grade 为 STALE，尝试从更高优先级源刷新 |

```
数据返回 → DataFreshnessAssessor 评估
  → FRESH: 正常返回
  → STALE: 返回数据 + 标记 STALE grade + 触发告警
  → EXPIRED: 尝试刷新（降级链重试）→ 失败则返回 STALE 数据
```

**新鲜度评估维度**:
- 按数据类型独立配置阈值（K线/行情/宏观/F10）
- F10 报告默认阈值更长（stale=1800s, expired=7200s）
- 新鲜度状态写入 DataPayload.metadata.freshness

## 超时与重试

| 配置项 | 默认值 | 说明 |
|:-------|:-------|:-----|
| HTTP timeout | 3s | 单次请求超时 |
| LLM timeout | 30s | LLM 调用超时（隐含在 SDK 中） |
| 熔断器超时 | 5s | Breaker 包裹的调用超时（v0.4.0） |
| 熔断器恢复超时 | 30s | OPEN → HALF_OPEN 等待时间（v0.4.0） |
| Retry count | 0 | 不重试，直接降级 |
| WebSocket 重连超时 | 5s 起（指数退避） | WebSocket 重连间隔（v1.0.0 新增） |
| 新鲜度 STALE 阈值 | 300s | 数据标记为 STALE 的时间阈值（v1.1.0 新增） |
| 新鲜度 EXPIRED 阈值 | 3600s | 数据标记为 EXPIRED 的时间阈值（v1.1.0 新增） |
| QMT 超时 | 5s | QMT 迅投请求超时（v1.2.0 新增） |
| WebFallback 超时 | 8s | 网页备用抓取超时（v1.2.0 新增） |
| TqSdk 超时 | 10s | TqSdk 请求超时（v1.2.0 新增） |
| 指标计算超时 | 无 | 纯 numpy 计算，无网络超时，仅受 CPU 限制（v1.2.0 新增） |
| 复权/换月超时 | 无 | 纯计算，无网络超时（v1.3.0 新增） |
| 周期转换超时 | 无 | 纯计算，无网络超时（v1.3.0 新增） |
| 数据清洗超时 | 无 | 纯计算，无网络超时（v1.3.0 新增） |
| 数据校验超时 | 无 | 纯计算，无网络超时（v1.3.0 新增） |
| 采集爬取超时 | 无 | 骨架阶段，暂不实际调用（v1.3.0 新增） |
| FDT 兼容层超时 | 无 | 纯封装，无额外超时，透传内部超时（v2.0.0 新增） |
| Qlib 适配器超时 | 无 | 格式转换层，无额外超时，透传内部超时（v2.0.0 新增） |

## 降级日志

每次降级触发时，在 DataPayload 的 `errors` 字段中记录失败原因。
情绪打分的 source 字段标识实际使用的打分方式：
- `llm`: LLM 打分成功
- `rule_fallback`: LLM 不可用，降级到规则基线
- `rule`: 直接使用规则基线

告警引擎每次降级时，在告警记录中标记实际使用的通知渠道：
- `webhook`: Webhook 通知成功
- `file_fallback`: Webhook 不可用，降级到文件
- `log_fallback`: 所有高级渠道不可用，兜底到日志

数据新鲜度评估时，在 DataPayload.metadata.freshness 中标记：
- `fresh`: 数据新鲜，正常使用
- `stale`: 数据过期，低权重使用
- `expired`: 数据严重过期，已尝试刷新失败

技术指标计算降级时，在指标结果 metadata 中标记实际使用的实现层：
- `tdx_compat`: TDX 对齐实现
- `numpy_core`: numpy 核心实现
- `talib_fallback`: TA-Lib 兜底实现

消费者反馈降级时，在 IssueRegistry 中标记问题级别和降级行为：
- `low`: 仅记录，不触发降级
- `medium_degrade`: 标记 STALE grade
- `high_degrade`: 切换到下一优先级源
- `critical_breaker`: 熔断数据源

数据清洗降级时，在 DataPayload.metadata.cleaning 中标记：
- `full_pipeline`: 完整清洗链路
- `basic_pipeline`: 基础清洗（跳过高级清洗）
- `passthrough`: 透传模式（未清洗）

数据校验降级时，在 DataPayload.metadata.validation 中标记：
- `full_validation`: 完整校验
- `basic_validation`: 基础校验（跳过跨源校验）
- `mark_only`: 仅标记模式（不阻断返回）

FDT 兼容层降级时，在结果 metadata 中标记：
- `fdc_full_compat`: 完整兼容模式
- `fdc_signature_only`: 仅函数签名兼容，数据格式 native
- `fdc_passthrough`: 透传模式，直接调用原生接口

Qlib 适配器降级时，在结果 metadata 中标记：
- `qlib_full_compat`: 完整 Qlib 兼容
- `qlib_basic_provider`: 基础数据提供（无表达式引擎）
- `qlib_passthrough`: 原生数据访问（无格式转换）
