# Data-Core Configuration

Version: v2.0.0 | Updated: 2026-07-20

## Config Sources (priority high to low)

- P0: Environment variables (`DATACORE_*` prefix)
- P1: `config/settings.yaml`
- P2: Code defaults

## Key Config Items

### 通用配置
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_LOG_LEVEL` | `INFO` | 日志级别 |
| `DATACORE_TIMEOUT` | `3` | HTTP 请求超时时间（秒） |
| `DATACORE_CACHE_TTL` | `3600` | 内存缓存 TTL（秒） |

### TQ-Local 配置
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_TDX_URL` | `http://127.0.0.1:17709/` | TQ-Local 服务地址 |
| `DATACORE_TDX_TIMEOUT` | `3` | TQ-Local 请求超时 |

### 存储配置
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_DB_PATH` | `~/.datacore/datacore.db` | DuckDB 数据库路径 |
| `DATACORE_REDIS_URL` | `redis://localhost:6379/0` | Redis 连接地址（可选） |
| `DATACORE_PG_URL` | 空 | PostgreSQL 连接地址（可选） |

### 熔断器配置（v0.4.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_CB_TIMEOUT` | `5` | 熔断器调用超时（秒） |
| `DATACORE_CB_MAX_FAILURES` | `5` | 连续失败次数触发 OPEN |
| `DATACORE_CB_RECOVERY_TIMEOUT` | `30` | HALF_OPEN 探测间隔（秒） |

### 指标收集配置（v0.4.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_METRICS_ENABLED` | `true` | 是否启用指标收集 |
| `DATACORE_METRICS_MAX_ENTRIES` | `10000` | 指标最大记录条数 |

### 国信证券配置
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_GUOSEN_API_KEY` | 空 | 国信证券 API Key |

### LLM 配置（v0.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_LLM_API_KEY` | 空 | LLM API Key（用于情绪打分） |
| `DATACORE_LLM_MODEL` | `gpt-4o-mini` | LLM 模型名称 |

> **降级策略**: 未配置 LLM API Key 时，情绪打分自动降级到规则基线（词典法）。

### 新闻/宏观模块配置
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_NEWS_SOURCES` | `cls,wallstreet,eastmoney` | 启用的新闻源 |
| `DATACORE_NEWS_CACHE_TTL` | `1800` | 新闻缓存 TTL（秒） |
| `DATACORE_MACRO_SOURCES` | `national_bureau,pboc,eastmoney` | 启用的宏观数据源（v0.5.0 更新） |
| `DATACORE_MACRO_CACHE_TTL` | `86400` | 宏观数据缓存 TTL（秒） |

### WebSocket 配置（v1.0.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_WS_URL` | `wss://example.com/market` | WebSocket 服务地址 |
| `DATACORE_WS_RECONNECT_INTERVAL` | `5` | 重连间隔（秒） |
| `DATACORE_WS_MAX_RECONNECT` | `10` | 最大重连次数 |
| `DATACORE_WS_HEARTBEAT_INTERVAL` | `30` | 心跳间隔（秒） |
| `DATACORE_WS_SUBSCRIBE_SYMBOLS` | 空 | 默认订阅品种列表（逗号分隔） |

### 告警配置（v1.0.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_ALERT_FILE_PATH` | `~/.datacore/alerts.log` | 告警日志文件路径 |
| `DATACORE_ALERT_WEBHOOK_URL` | 空 | 告警 Webhook 回调地址 |
| `DATACORE_ALERT_PRICE_THRESHOLD` | `0.05` | 价格突破阈值（5%） |
| `DATACORE_ALERT_VOLATILITY_THRESHOLD` | `0.03` | 波动率异常阈值（3%） |
| `DATACORE_ALERT_STALE_SECONDS` | `300` | 数据延迟告警阈值（秒） |

### 基准测试配置（v1.0.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_BENCHMARK_ITERATIONS` | `100` | 基准测试迭代次数 |
| `DATACORE_BENCHMARK_WARMUP` | `10` | 预热迭代次数 |

### 数据新鲜度配置（v1.1.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_FRESHNESS_STALE_SECONDS` | `300` | 数据过期为 STALE 的阈值（秒） |
| `DATACORE_FRESHNESS_EXPIRED_SECONDS` | `3600` | 数据过期为 EXPIRED 的阈值（秒） |
| `DATACORE_FRESHNESS_ENABLED` | `true` | 是否启用新鲜度评估 |

### QMT 迅投配置（v1.2.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_QMT_ENABLED` | `false` | 是否启用 QMT 数据源（需安装 xtquant） |
| `DATACORE_QMT_PATH` | 空 | QMT 客户端安装路径（用于 xtquant 初始化） |
| `DATACORE_QMT_TIMEOUT` | `5` | QMT 请求超时时间（秒） |

### TqSdk 配置（v1.2.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_TQSDK_ENABLED` | `false` | 是否启用 TqSdk 兜底数据源（需安装 tqsdk） |
| `DATACORE_TQSDK_ACCOUNT` | 空 | TqSdk 账户（可选，模拟盘可留空） |
| `DATACORE_TQSDK_TIMEOUT` | `10` | TqSdk 请求超时时间（秒） |

### WebFallback 配置（v1.2.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_WEB_FALLBACK_ENABLED` | `true` | 是否启用网页备用数据源 |
| `DATACORE_WEB_FALLBACK_TIMEOUT` | `8` | 网页抓取超时时间（秒） |

### 技术指标配置（v1.2.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_INDICATORS_TDX_PRIORITY` | `true` | 是否优先使用 TDX 对齐指标 |
| `DATACORE_INDICATORS_TALIB_ENABLED` | `true` | 是否启用 TA-Lib 兜底层（需安装 TA-Lib） |
| `DATACORE_INDICATORS_DEFAULT_PERIOD` | `14` | 默认指标计算周期 |

### 期货数据源配置（v1.2.0 更新）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_FUTURES_SOURCES` | `tdx_lc,eastmoney,qmt,exchange_api,shengyishe,web_fallback,tqsdk` | 启用的期货数据源（7 源，按优先级排序） |

### BaseTool 配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_TOOLS_ENABLED` | `true` | 是否启用 BaseTool 接口层 |
| `DATACORE_TOOLS_AUTO_DISCOVERY` | `true` | 是否启用 all_tools 自动发现机制 |
| `DATACORE_TOOLS_LANGCHAIN_COMPAT` | `true` | 是否启用 LangChain 协议兼容模式 |

### 复权/换月配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_ADJUST_STOCK_DEFAULT` | `front` | 股票默认复权方式（front/back/none） |
| `DATACORE_ADJUST_FUTURES_ROLLOVER` | `volume` | 期货主力换月方式（volume/interest/fixed_day） |
| `DATACORE_ADJUST_FUTURES_SPREAD` | `front` | 期货换月价差调整方式（front/back/equal） |
| `DATACORE_ADJUST_FIXED_ROLLOVER_DAY` | `1` | 固定日换月日期（1-31） |

### 周期转换配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_RESAMPLE_DEFAULT_PERIOD` | `auto` | 默认周期转换目标（auto/1m/5m/15m/30m/60m/daily/weekly/monthly） |
| `DATACORE_RESAMPLE_ENABLE_AUTO` | `true` | 是否启用 auto 自动检测模式 |
| `DATACORE_RESAMPLE_VOLUME_SUM` | `true` | 成交量是否求和聚合 |

### 消费者反馈配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_ISSUE_ENABLED` | `true` | 是否启用消费者反馈通道 |
| `DATACORE_ISSUE_AUTO_DEGRADE` | `true` | 问题触发时是否自动降级 |
| `DATACORE_ISSUE_MAX_QUEUE_SIZE` | `1000` | 问题注册表最大队列大小 |
| `DATACORE_ISSUE_RETENTION_HOURS` | `24` | 问题记录保留时间（小时） |

### 数据清洗配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_CLEANING_UNIT_UNIFY_ENABLED` | `true` | 是否启用单位统一 |
| `DATACORE_CLEANING_DATE_ALIGN_ENABLED` | `true` | 是否启用日期对齐 |
| `DATACORE_CLEANING_DUPLICATE_MERGE_ENABLED` | `true` | 是否启用去重合并 |
| `DATACORE_CLEANING_OUTLIER_FILTER_ENABLED` | `true` | 是否启用异常值过滤 |
| `DATACORE_CLEANING_OUTLIER_METHOD` | `3sigma` | 异常值检测方法（3sigma/iqr） |
| `DATACORE_CLEANING_OUTLIER_THRESHOLD` | `3.0` | 异常值检测阈值 |

### 数据校验配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_VALIDATION_WEIGHT_SCORE_ENABLED` | `true` | 是否启用权重评分 |
| `DATACORE_VALIDATION_CROSS_SOURCE_ENABLED` | `true` | 是否启用跨源校验 |
| `DATACORE_VALIDATION_MISSING_DETECT_ENABLED` | `true` | 是否启用缺失检测 |
| `DATACORE_VALIDATION_CAL_MATH_ENABLED` | `true` | 是否启用计算校验 |
| `DATACORE_VALIDATION_CROSS_SOURCE_THRESHOLD` | `0.05` | 跨源校验偏差阈值（5%） |

### 采集模块配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_COLLECTORS_ENABLED` | `false` | 是否启用采集模块（骨架阶段，默认关闭） |
| `DATACORE_COLLECTORS_WEB_CRAWL_RATE_LIMIT` | `1` | 网页爬虫请求频率限制（次/秒） |
| `DATACORE_COLLECTORS_USER_AGENT` | `DataCore/1.3.0` | 采集器 User-Agent |

### 运维工具配置（v1.3.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_OPS_CRAWL_RETRY_MAX` | `3` | 爬取最大重试次数 |
| `DATACORE_OPS_CRAWL_RETRY_BACKOFF` | `2` | 重试退避因子（指数退避） |
| `DATACORE_OPS_ERROR_LOG_ENABLED` | `true` | 是否启用错误日志收集 |
| `DATACORE_OPS_ERROR_LOG_PATH` | `~/.datacore/error.log` | 错误日志文件路径 |

### FDT 兼容层配置（v2.0.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_FDC_COMPAT_ENABLED` | `true` | 是否启用 FDT 兼容层 |
| `DATACORE_FDC_COMPAT_OUTPUT_FORMAT` | `native` | 输出格式（native/dataframe/series） |
| `DATACORE_FDC_COMPAT_FIELD_STYLE` | `datacore` | 字段命名风格（datacore/fdc） |
| `DATACORE_FDC_COMPAT_ERROR_COMPAT` | `true` | 是否启用 FDC 错误码兼容 |

### Qlib/RD-Agent 适配器配置（v2.0.0 新增）
| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:-----|
| `DATACORE_QLIB_ADAPTER_ENABLED` | `true` | 是否启用 Qlib 适配器 |
| `DATACORE_QLIB_FREQUENCY` | `daily` | 默认数据频率（daily/1m/5m/...） |
| `DATACORE_QLIB_INSTRUMENT_TYPE` | `all` | 默认品种池类型（all/stock/futures/...） |
| `DATACORE_QLIB_EXPRESSION_ENGINE` | `true` | 是否启用表达式引擎 |
| `DATACORE_QLIB_CACHE_ENABLED` | `true` | 是否启用 Qlib 格式缓存 |

> **安全提示**: API Key 等敏感信息请通过环境变量配置，**禁止硬编码到代码中**。
