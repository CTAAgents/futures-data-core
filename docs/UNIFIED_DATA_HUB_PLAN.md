# Data-Core 统一数据中枢升级方案

> 版本: v1.0.0 → v2.0.0（规划中）
> 本方案取代 `docs/UPGRADE_V2_PLAN.md`
> 创建: 2026-07-19

---

## 目录

1. [战略目标](#1-战略目标)
2. [现状差距分析](#2-现状差距分析)
3. [目标架构](#3-目标架构)
4. [模块吸收清单](#4-模块吸收清单)
5. [API 设计](#5-api-设计)
6. [Qlib/RD-Agent 适配器](#6-qlibrd-agent-适配器)
7. [实施路线图](#7-实施路线图)
8. [FDT 迁移策略](#8-fdt-迁移策略)
9. [验收标准](#9-验收标准)

---

## 1. 战略目标

### 一句话定位

> **Data-Core v2.0 = 统一数据引擎 + LangChain BaseTool 接口层。所有数据能力通过 Tool 暴露给 AI Agent，Agent 框架（LangGraph/CrewAI/AutoGen）零适配、一键接入。**

### 当前痛点 vs 目标

| 维度 | 当前 (v1.0) | 目标 (v2.0) |
|:-----|:------------|:------------|
| **FDT 数据层** | 独立 `futures_data_core` 模块，代码重复维护 | 零数据采集代码，全部走 Data-Core |
| **期货能力** | 有基础，缺指标/QMT/TqSDK | 全市场覆盖（指标/TDX 公式/QMT/TqSDK/F10） |
| **A 股能力** | 3 源降级链，基础可用 | ✅ **增强为亮点：更多源、更稳定、更快** |
| **ETF/可转债/REITs** | 基础支持 | ✅ **增强为亮点：全品类覆盖，数据更丰富** |
| **宏观数据** | 3 源降级链 | ✅ **增强为亮点：更多指标、更高频、自动补缺** |
| **新闻采集** | 3 源降级链 | ✅ **增强为亮点：新增搜索/爬虫/文档源，覆盖面翻倍** |
| **情绪打分** | LLM+规则降级 | ✅ **增强为亮点：准确率提升、多模型支持、实时情绪** |
| **市场制度检测** | 基础版 | ✅ **增强为亮点：更多制度类型、多周期并行** |
| **基本面 LLM 加工** | 研报摘要+财报提取 | ✅ **增强为亮点：F10 综合报告、LLM 增强可选、多数据源交叉验证** |
| **调用方式** | 仅同步 API，无法接入 Agent 框架 | **同步+异步+BaseTool 三种入口，Agent 零适配** |
| **Agent 接入** | 无 BaseTool | **核心亮点：全部能力通过 LangChain BaseTool 暴露，自动发现注册** |
| **Qlib/RD-Agent** | 无 | **适配器层：DataCoreQLibProvider 实现 Qlib Provider 接口，RD-Agent 自动兼容** |
| **技术指标** | 无 | 40+ 个技术指标（FDC numpy + TDX 公式 + TA-Lib 兜底） |
| **综合报告** | 无 F10 | F10 综合报告（一次调用 5 类数据） |

### v2.0 核心亮点

升级后 Data-Core 相比 FDC 的最大优势，正是 Data-Core v1.0 已有的能力在 v2.0 中得到进一步增强：

| 亮点 | v1.0 已有 | v2.0 增强方向 |
|:-----|:----------|:--------------|
| **A 股全品类** | K线/行情/财务，3 源降级 | 更多数据源接入、复权策略文档化、提高降级链健壮性 |
| **ETF/可转债/REITs** | 基础数据获取 | 扩展至净值/折溢价/资金流等 ETF 特异 DataType |
| **宏观指标库** | CPI/PPI/GDP/PMI/M2/LPR 6 项，3 源降级 | 扩充指标至 20+，自动补全历史缺失、AI Agent 可查询 |
| **新闻资讯** | 3 源文本采集+分类 | 新增 Web 爬虫/Tavily 搜索/本地研报文档，覆盖倍增至 6 源 |
| **情绪打分管线** | LLM→规则降级，置信度加权聚合 | 准确率跟踪回馈、多 LLM 模型支持、实时情绪推流 |
| **市场制度检测** | bull/bear/sideways 三态 | 新增极端波动/低流动性/趋势转变识别，多周期并行检测 |
| **基本面 LLM 加工** | 研报摘要+财报提取 | 纳入 F10 综合报告，与期限结构/价差/基差/仓单合并呈现 |
| **复权/换月引擎** | 消费方自行处理 | **统一处理：期货主力连续（多种换月算法）+ 股票前/后/不复权，消费端声明即可** |
| **周期转换引擎** | 各 Provider 自行映射 | **统一重采样：任意原始周期→任意目标周期，消费端指定 `period` 即可，不感知底层** |

> **v2.0 的定位**: 吸收 FDC 的期货深度能力填补短板，同时把 Data-Core 原有的 A 股/宏观/新闻/情绪优势做成更强的亮点——而所有这些能力，最终都通过 BaseTool 接口层统一暴露给 AI Agent，这才是 v2.0 升级的核心。

### 边界定义

| 负责 | 不负责 |
|:-----|:-------|
| 所有金融数据采集/清洗/缓存/存储 | 策略信号计算（归 FTS） |
| **统一复权/换月处理（期货主力连续、股票前/后/不复权）** | 交易决策（归 FDT） |
| **周期转换/重采样（任意原始周期→任意目标周期）** | LLM Agent 编排（归各 Agent 框架） |
| 技术指标计算（纯函数） | 因子演化（归 FTS） |
| 数据校验/可信度打分 | |
| 数据加工（情绪/市场制度/衍生因子/复权/周期转换） | |
| **BaseTool 接口层（核心交付）** | |

---

## 2. 现状差距分析

### 2.1 功能覆盖矩阵

```
能力                    Data-Core v1.0      FDC (futures_data_core)     v2.0 目标
────────────────────    ───────────────     ────────────────────────    ─────────
期货 OHLCV              ✅ TdxLc-EastMoney  ✅ TDX-WebFallback-QMT-TqSDK  ✅ 全部
期货行情 QUOTE          ✅                  ✅                           ✅
合约链                  ✅                  ─                           ✅
期限结构                ✅ TdxLc            ✅ TdxLc+WebFallback         ✅ 全部
价差                    ✅ TdxLc            ✅ TdxLc+WebFallback         ✅ 全部
基差                    ✅ EastMoney+ShengYiShe ✅ TdxLc+WebFallback     ✅ 全部
持仓排名                ✅ EastMoney        ✅ WebFallback               ✅ 全部
仓单/仓单               ✅ ExchangeAPI      ✅ WebFallback+交易所官网抓取  ✅ 全部
────────────────────    ───────────────     ────────────────────────    ─────────
A股 K 线/行情           ✅ 3源降级链         ❌ 不支持                    ✅ 保留
股票财务                ✅                  ❌                           ✅ 保留
ETF/可转债/REITs       ✅                  ❌                           ✅ 保留
────────────────────    ───────────────     ────────────────────────    ─────────
宏观数据                ✅ 3源降级链         ❌ 仅东方财富                 ✅ 保留
新闻采集                ✅ 3源降级链         ❌ 不支持                    ✅ 保留
────────────────────    ───────────────     ────────────────────────    ─────────
情绪打分                ✅ LLM+规则         ❌ 基础版本                   ✅ 保留
市场制度检测            ✅                  ❌                           ✅ 保留
基本面 LLM 加工         ✅                  ❌ 仅有 F10 LLM 增强          ✅ 合并
────────────────────    ───────────────     ────────────────────────    ─────────
Qlib/RD-Agent 适配      ❌ 不支持           ❌ 无 Qlib Provider            ✅ DataCoreQLibProvider
────────────────────    ───────────────     ────────────────────────    ─────────
技术指标                ❌ 不支持           ✅ 40+ (TDX + numpy + TA-Lib)    ✅ 三层体系
TDX 公式指标            ❌ 不支持           ✅ ADX/PDI/MDI               ✅ 新增
F10 综合报告            ❌ 不支持           ✅ 聚合 5 类数据              ✅ 新增
────────────────────    ───────────────     ────────────────────────    ─────────
额外采集源              ❌                  ✅ QMT/xtquant               ✅ 新增
                                        ✅ TqSDK                      ✅ 新增
                                        ✅ WebFallback(新浪)           ✅ 新增
────────────────────    ───────────────     ────────────────────────    ─────────
缓存层                  MemoryCache+DuckDB  ✅ PostgreSQL+Redis          ✅ 全部支持
持久化                  DuckDB/PostgreSQL    ✅ PostgreSQL                ✅ 全部
────────────────────    ───────────────     ────────────────────────    ─────────
告警引擎                ✅ AlertEngine       ❌                           ✅ 保留
WebSocket 行情          ✅                  ❌                           ✅ 保留
────────────────────    ───────────────     ────────────────────────    ─────────
API 风格                同步(sync)          异步(async)                   ✅ 双接口
Agent 接口              ❌                  ❌                           ✅ BaseTool
```

### 2.2 需要从 FDC 吸收的能力

按模块整理，标注吸收优先级：

| 优先级 | 模块 | 文件 | 说明 |
|:-------|:-----|:-----|:-----|
| **P0** | 技术指标 | `indicators/core.py` | 40+ 指标纯 numpy 计算，零依赖 |
| **P0** | TA-Lib 封装 | `indicators/talib_wrapper.py` | 行业标准指标库兜底，覆盖 200+ 函数 |
| **P0** | TDX 公式 | `indicators/tdx_compat.py` | 通达信对齐的指标计算 |
| **P0** | QMT 采集器 | `collectors/qmt.py` | FDT 依赖的本地数据源 |
| **P1** | TqSDK 采集器 | `collectors/tqsdk.py` | FDT 末位兜底源 |
| **P1** | Web Fallback | `collectors/web_fallback.py` | 新浪+东方财富备用 |
| **P1** | 趋势成熟度 | `indicators/trend_maturity.py` | quant-daily 策略依赖 |
| **P1** | F10 综合报告 | `f10/`（全部） | 期限结构+价差+基差+仓单+基本面聚合 |
| **P1** | A2A 信封 | `_a2a.py` | 数据结构（考虑是否适配） |
| **P1** | 数据新鲜度 | `core/data_freshness.py` | 数据质量评估 |
| **P2** | 交易所爬虫 | `f10/exchange_scraper.py` | 直接从交易所官网抓取仓单 |
| **P2** | 旧版 numpy 指标 | `indicators/legacy_numpy.py` | 历史兼容 |
| **P2** | 缓存层 | `core/cache_store.py` | PostgreSQL+Redis 集成 |

### 2.3 FDT 中调用了 FDC 的地方（需要迁移）

从 FDC 的 `__init__.py` 导出的公开 API：

```python
# FDT 中所有 import futures_data_core 的地方都需要改为 import datacore
# 当前 FDC 公开 API 清单:
get_kline()              → datacore.api.get() 或 datacore.aget()
get_quote()              → datacore.api.get()
batch_get_quotes()       → 新增批量接口
compute_indicators()     → datacore.indicators.compute()
assess_trend_maturity()  → datacore.indicators.trend_maturity()
get_term_structure()     → datacore.api.get()
get_spread()             → datacore.api.get()
get_basis()              → datacore.api.get()
get_warrant()            → datacore.api.get()
get_fundamental()        → datacore.api.get()
get_f10()                → datacore.api.get() 或 datacore.get_f10()
get_position_ranking()   → datacore.api.get()
get_sentiment()          → datacore.api.get()
```

---

## 3. 目标架构

### 3.1 系统架构

```
┌────────────────────────────────────────────────────────────────────┐
│                         AI Agent 层                                 │
│   LangGraph / CrewAI / AutoGen / Claude Desktop / Cursor            │
│          │  ToolNode(all_tools)  │  MCP 协议  │  BaseTool invoke()  │
└──────────┴──────────────────────┴────────────┴────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────────┐
│                       Data-Core v2.0 (统一数据中枢)                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │ ① BaseTool 接口层 ★ 核心交付 ★                              │     │
│  │  ┌─────────────────────────────────────────────────────┐   │     │
│  │  │ 自动发现: from datacore.tools import all_tools       │   │     │
│  │  │ 30+ Tool, 每个继承 BaseTool, 带 args/description    │   │     │
│  │  │ 直接传入 ToolNode: graph.add_node(ToolNode(all_tools))│   │     │
│  │  │ 可选 MCP Server: 将全部 Tool 暴露为 MCP 协议         │   │     │
│  │  └─────────────────────────────────────────────────────┘   │     │
│  │                                                              │     │
│  │ ② Python API 层（底层引擎）                                   │     │
│  │  ┌──────────┐  ┌──────────┐                                  │     │
│  │  │ sync API │  │ async API│                                  │     │
│  │  │ get()    │  │ aget()   │                                  │     │
│  │  └────┬─────┘  └────┬─────┘                                  │     │
│  └───────┴──────────────┴──────────────────────────────────────┘     │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────────────────┐  │
│  │              路由 / 数据加工层                                │  │
│  │  API 路由 → 缓存查询(L1+L2) → 数据源降级 → 加工管线         │  │
│  └───────────────────────┬────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────────────────┐  │
│  │              采集层 (12 个数据源)                             │  │
│  │                                                              │  │
│  │  ┌────────期货──────────┐  ┌────────股票──────────┐        │  │
│  │  │ TdxLcProvider (P0)   │  │ TencentProvider (P0) │        │  │
│  │  │ EastMoneyFutures(P1) │  │ EastMoneyEquity(P1)  │        │  │
│  │  │ QMTCollector (P2)    │  │ GuosenProvider (P2)  │        │  │
│  │  │ ExchangeApi (P3)     │  └──────────────────────┘        │  │
│  │  │ ShengYiShe (P4)      │                                    │  │
│  │  │ WebFallback (P5)     │  ┌────────宏观/新闻──────┐        │  │
│  │  │ TqSdkCollector (P98) │  │ NationalBureau (P0)   │        │  │
│  │  └──────────────────────┘  │ PboCProvider (P1)     │        │  │
│  │                            │ EastMoneyMacro (P2)   │        │  │
│  │  ┌───本地采集(新增)───┐    │ ClsNews (P0)          │        │  │
│  │  │ WebCollector       │    │ WallStreetCn (P1)     │        │  │
│  │  │ Firecrawl          │    │ EastMoneyResearch(P2) │        │  │
│  │  │ AKShare            │    └──────────────────────┘        │  │
│  │  │ OpenBB             │                                    │  │
│  │  │ LocalDoc           │  ┌───Web 搜索(新增)───┐            │  │
│  │  │ Tavily             │  │ TavilySearch       │            │  │
│  │  └────────────────────┘  └────────────────────┘            │  │
│  └───────────────────────┬────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────────────────┐  │
│  │         加工层                                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │  │
│  │  │ 情绪打分      │  │ 市场制度检测  │  │ 技术指标三层     │ │  │
│  │  │ LLM→规则降级  │  │ bull/bear/   │  │ TDX formula_zb(主)│ │  │
│  │  │              │  │ sideways     │  │ FDC numpy(次)     │ │  │
│  │  │              │  │              │  │ TA-Lib(兜底)      │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘ │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │  │
│  │  │ F10 综合报告  │  │ 衍生因子计算  │  │ ★复权/换月引擎★  │ │  │
│  │  │ 期限结构+价差  │  │ 库存同比/    │  │ 主力连续(多种    │ │  │
│  │  │ +基差+仓单+   │  │ 基差率/      │  │ 换月算法) +      │ │  │
│  │  │ 基本面       │  │ 季节性/加工  │  │ 前/后/不复权     │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ★周期转换引擎★                                        │  │  │
│  │  │ 从最小原始周期 → 任意目标周期自动重采样                  │  │  │
│  │  │ 1min→5min→15min→30min→60min→daily→weekly→monthly     │  │  │
│  │  │ OHLCV 聚合规则: O=first, H=max, L=min, C=last, V=sum │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ 基本面 LLM                                          │  │  │
│  │  │ 研报摘要+财报提取                                    │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────────────────┐  │
│  │              基础设施层                                      │  │
│  │  熔断器 / 指标收集 / 告警引擎 / WebSocket / 数据校验          │  │
│  └───────────────────────┬────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────────────────┐  │
│  │              存储层                                          │  │
│  │  MemoryCache(L1) → DuckDB, PostgreSQL(L2) → Redis(L3)     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                      │
└────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    v                               v
             FDT (零数据采集代码)           其它分析系统
             ┌──────────────────┐         ┌──────────────────┐
             │ 全部通过          │         │ 全部通过          │
             │ datacore.get()    │         │ datacore.get()    │
             │ 获取数据          │         │ 获取数据          │
             │ futures_data_core │         │ 无需自己的        │
             │ 模块删除          │         │ 数据采集层        │
             └──────────────────┘         └──────────────────┘
```

### 3.2 核心设计决策

#### 决策 1：API 双接口（同步 + 异步）

```python
# 同步（简单脚本、策略代码）
from datacore import UnifiedDataProvider
dc = UnifiedDataProvider()
data = dc.get("RB", DataType.OHLCV)

# 异步（FDT LangGraph、高并发）
from datacore import AsyncDataProvider
adc = AsyncDataProvider()
data = await adc.get("RB", DataType.OHLCV)
```

两个接口共享同一引擎（同一套数据源/缓存/熔断器），底层通过 `asyncio.to_thread()` 或内部协程桥接。

#### 决策 2：FDC 指标吸收不重写

FDC 的 `indicators/` 已经是独立模块（纯 numpy 函数，零外部依赖），直接整体搬入 Data-Core，不改一行代码。同时新增 `indicators/talib_wrapper.py`，将 TA-Lib 作为兜底。

**指标路由优先级：通达信 formula_zb(真实盘一致) → FDC numpy(常用指标) → TA-Lib(兜底补缺)**。通达信是事实标准，FDC numpy 的指标算法也通过 `tdx_compat.py` 与通达信对齐，TA-Lib 只覆盖前两层没有的非常见指标。

```python
# v2.0 用法 — 完全兼容 FDC 的 compute_indicators 接口
from datacore.indicators import compute_indicators
result = compute_indicators({"close": [...], "high": [...], ...}, "all")
```

#### 决策 3：数据源顺序重新编排

```
期货 7 源降级链:
  TDX-Local (P0) → Data-Core 东方财富 (P1)
  → 吸收自 FDC: QMT/xtquant (P2)
  → Data-Core 交易所官方 (P3)
  → Data-Core 生意社 (P4)
  → 吸收自 FDC: WebFallback 新浪 (P5)
  → 吸收自 FDC: TqSDK (P98)
```

#### 决策 4：统一复权/换月处理 ★ 架构级变更

**原则**: 所有复权/换月处理由 Data-Core 统一完成，消费端只声明需求（品种 + 复权参数），不感知计算逻辑。

**前情**: 
- v1.0 原则是"数据源提供什么就返回什么，不做二次加工"，A 股的复权由 API 源侧参数（qfq/fqt=1）完成，期货换月交由消费方自行处理。
- v2.0 升级为 Data-Core 统一处理层，提供：
  - **期货主力连续合约拼接**：多种换月算法（成交量加权/持仓量加权/固定日换月/前复权/后复权）
  - **股票/ETF/可转债/REITs 复权**：前复权(qfq)、后复权(hfq)、不复权(none)，脱离对单一 API 参数的依赖
  - **消费端声明式调用**：在 `get()` 调用中通过 `adjustment` 参数指定

```python
# 消费端用法 — 声明式，不感知底层计算
dc.get("RB", DataType.OHLCV, adjustment="continuous")     # 期货主力连续（默认成交量加权）
dc.get("RB", DataType.OHLCV, adjustment="continuous_qfq")  # 期货主力连续 + 前复权
dc.get("600519", DataType.OHLCV, adjustment="qfq")         # A 股前复权
dc.get("600519", DataType.OHLCV, adjustment="hfq")         # A 股后复权
dc.get("600519", DataType.OHLCV, adjustment="none")        # A 股不复权（原始数据）
dc.get("RB9999", DataType.OHLCV)                           # 兼容模式：特定合约代码，不复权
```

**调整参数定义**:

| adjustment 值 | 适用市场 | 行为 |
|:--------------|:---------|:-----|
| `"none"` | 全部 | 不处理，返回原始数据（期货不拼接，股票不除权） |
| `"qfq"` | 股票/ETF/可转债/REITs | 前复权（调整除权除息前的价格） |
| `"hfq"` | 股票/ETF/可转债/REITs | 后复权（调整除权除息后的价格） |
| `"continuous"` | 期货 | 主力连续合约拼接，默认成交量加权换月，价格不调整 |
| `"continuous_qfq"` | 期货 | 主力连续 + 前复权（换月后价格对齐前段） |
| `"continuous_hfq"` | 期货 | 主力连续 + 后复权（换月前价格对齐后段） |
| `"continuous_fixed_nth"` | 期货 | 固定第 N 个交易日换月（如 `continuous_fixed_5`=每月第5日换月） |

**消费方变化**:
- 以前：期货消费方需要自己写换月/连续逻辑；股票消费方需要了解 API 参数
- 以后：消费方只需要传一个 `adjustment` 参数，Data-Core 返回已处理好的数据

> **例外/兼容**：如果消费方需要原始不处理的合约 K 线（如做价差计算需要特定合约），可以传 `adjustment="none"` 或直接用原始合约代码。

#### 决策 5：统一周期转换

**原则**: 所有 K 线数据的周期转换由 Data-Core 统一完成。Provider 只需提供其能提供的最原始周期数据，Data-Core 负责重采样到消费端指定的目标周期。

**前情**:
- v1.0 的 `period` 参数直接透传给各 Provider，每个 Provider 有自己的周期映射表（`{"daily":"1d","60m":"60m"}`）。
- 如果 Provider 不支持某个周期（如 Tencent 只提供日线，不支持分钟线），消费方得到空数据。
- v2.0 改为：以 Provider 能提供的最细粒度数据为基础，由 Data-Core 的重采样引擎统一转换为目标周期。

**重采样处理管线**:

```
消费端请求: dc.get("RB", DataType.OHLCV, period="weekly")
                      │
                      ▼
① 获取原始数据: adc.get("RB", DataType.OHLCV, period="daily")  ← 取大于目标周期的最近粒度
   └→ 如果已有 5min 缓存，取 5min；如果只有 daily 缓存，取 daily
   └→ 如果目标周期比原始周期更细（如请求 5min 但只有 daily），返回错误 + 建议
                      │
                      ▼
② 复权/换月处理: 如果指定了 adjustment，先处理
                      │
                      ▼
③ 周期转换引擎:
   ┌─────────────────┬──────────────┬──────────────────────┐
   │ 目标周期         │ 原始周期示例  │ 聚合规则              │
   ├─────────────────┼──────────────┼──────────────────────┤
   │ 5min            │ 1min         │ 5 条 1min → 1 根 5min │
   │ 15min           │ 1min / 5min  │ 15/3 条 → 1 根 15min │
   │ 30min           │ 1min / 5min  │ 30/6 条 → 1 根 30min │
   │ 60min           │ 1min / 5min  │ 60/12 条 → 1 根 60min │
   │ daily           │ 60min / 5min │ 当日分钟 → 1 根日线   │
   │ weekly          │ daily        │ 5 根日线 → 1 根周线   │
   │ monthly         │ daily        │ 当月日线 → 1 根月线   │
   └─────────────────┴──────────────┴──────────────────────┘
   聚合规则: open=first, high=max, low=min, close=last, volume=sum
                      │
                      ▼
④ 返回消费端
```

**支持的周期取值**:

| period 值 | 说明 | 需要的最细原始周期 |
|:----------|:-----|:------------------|
| `"1m"` | 1 分钟 | 1 分钟 |
| `"5m"` | 5 分钟 | ≤5 分钟 |
| `"15m"` | 15 分钟 | ≤15 分钟 |
| `"30m"` | 30 分钟 | ≤30 分钟 |
| `"60m"` | 60 分钟 | ≤60 分钟 |
| `"daily"` | 日线（默认） | ≤日线 |
| `"weekly"` | 周线（周一为起始） | ≤日线 |
| `"monthly"` | 月线 | ≤日线 |
| `"auto"` | 自动选择最合适的周期 | 任意 |

**消费方变化**:
- 以前：消费方需要知道 Provider 支持哪些周期，否则返回空
- 以后：消费方直接指定想要的周期，Data-Core 自动重采样

> **注意**: 周期转换只能从细粒度→粗粒度（1min→5min→daily→weekly）。如果请求的周期比 Provider 能提供的最细粒度还细（如请求 1min 但只有 daily 数据），Data-Core 会返回错误 + 建议可用周期。这是数据源能力上限，无法通过重采样突破。

---

## 4. 模块吸收清单

### 4.1 直接从 FDC 搬入（不改代码）

| FDC 文件 | 搬入 Data-Core 目标 | 行数 | 工作方式 |
|:---------|:-------------------|:-----|:---------|
| `indicators/core.py` | `datacore/indicators/core.py` | ~200 | 纯 numpy 函数，零依赖 |
| `indicators/tdx_compat.py` | `datacore/indicators/tdx_compat.py` | ~500 | 纯 numpy 函数 |
| `indicators/legacy_numpy.py` | `datacore/indicators/legacy_numpy.py` | ~300 | 纯 numpy 函数 |
| `indicators/trend_maturity.py` | `datacore/indicators/trend_maturity.py` | ~150 | 纯 numpy 函数 |
| `core/data_freshness.py` | `datacore/core/data_freshness.py` | ~100 | 独立逻辑 |
| `core/types.py` (KlineBar等) | `datacore/core/types.py` | ~80 | 数据结构 |

**小计：6 个文件，~1330 行，估算 1 人日**（copy-paste + 改 import）

### 4.2 适配后吸收（改动代码）

| FDC 文件 | Data-Core 目标 | 改动内容 |
|:---------|:--------------|:---------|
| `collectors/qmt.py` | `datacore/futures/providers/qmt.py` | 适配为 `FuturesDataSource` 子类 |
| `collectors/tqsdk.py` | `datacore/futures/providers/tqsdk.py` | 同上 + 配置项对齐 |
| `collectors/web_fallback.py` | `datacore/futures/providers/web_fallback.py` | 同上 |
| `f10/` 全目录 | `datacore/f10/` | 保持独立，通过统一入口暴露 |

**小计：4 个工作包，估算 2 人日**

### 4.3 新增实现

| 模块 | 说明 | 工作量 |
|:-----|:-----|:-------|
| `datacore/api_async.py` — `AsyncDataProvider` | async 双接口，共享底层引擎 | 2 人日 |
| `datacore/api_f10.py` — `get_f10()` | F10 综合报告组装 | 1 人日 |
| `datacore/core/__init__.py` | 共享基础设施 | 0.5 人日 |
| `datacore/tools/` — BaseTool 封装 | 30+ 个 Tool（沿用原 v2.0 计划） | 5 人日 |
| 数据源采集器新增 | Web 爬虫/开源库/本地文档（沿用原 v2.0 计划） | 5 人日 |

**小计：5 个工作包，估算 13.5 人日**

### 4.4 FDT 迁移

| 工作 | 说明 | 工作量 |
|:-----|:-----|:-------|
| 替换全部 import | `futures_data_core.*` → `datacore.*` | 1 人日 |
| 适配 async API | `await get_kline()` → `await adc.get()` | 1 人日 |
| F10 调用迁移 | `get_f10()` → `dc.get_f10()` | 0.5 人日 |
| 指标调用迁移 | `compute_indicators()` → `dc.indicators.compute()` | 0.5 人日 |
| 测试验证 | 跑通 FDT 全部测试 | 1 人日 |
| 删除 `futures_data_core/` | 清理旧模块 | 0.5 人日 |

**小计：6 个工作包，估算 4.5 人日**

### 4.5 总量估算

```
Phase 1: 基础设施+API双接口       ~3.5 人日
Phase 2: 吸收 FDC 核心模块        ~3 人日
Phase 3: 新增采集 + BaseTool + 复权引擎    ~18 人日（含消费者反馈通道 1 人日、复权引擎 7 人日）
Phase 4: FDT 迁移                 ~4.5 人日
Phase 5: Qlib/RD-Agent 适配器     ~4 人日
                               ─────────
                                总计 ~37 人日
```

---

## 5. API 设计

### 5.1 统一入口

```python
# ═══════════════════════════════════════════════════════════════
# sync API — 保持 v1.0 完全兼容
# ═══════════════════════════════════════════════════════════════
from datacore import UnifiedDataProvider
dc = UnifiedDataProvider()

# 2 个通用方法（全部数据类型） + N 个快捷方法
dc.get("RB", DataType.OHLCV)                                  # 通用接口（默认期货不复权）
dc.get("RB", DataType.OHLCV, period="daily")                   # 日线（默认，等价于不传）
dc.get("RB", DataType.OHLCV, period="60m")                     # 60 分钟线
dc.get("RB", DataType.OHLCV, period="15m")                     # 15 分钟线
dc.get("RB", DataType.OHLCV, period="weekly")                  # 周线
dc.get("RB", DataType.OHLCV, period="monthly")                 # 月线
dc.get("RB", DataType.OHLCV, adjustment="continuous_qfq", period="daily")  # 期货主力连续+前复权+日线
dc.get("600519", DataType.OHLCV, adjustment="qfq", period="daily")          # A 股前复权+日线
dc.get("600519", DataType.OHLCV, adjustment="hfq", period="60m")            # A 股后复权+60分钟线
dc.get("600519", DataType.OHLCV, adjustment="none")           # A 股不复权
dc.get("RB", DataType.SENTIMENT)                              # 加工层数据走同一入口
dc.get("600519", DataType.QUOTE)                              # A 股行情
dc.get_health()                                               # 健康检查
dc.get_f10("RB")                                              # F10 综合报告（快捷方法）

# ═══════════════════════════════════════════════════════════════
# async API — FDT 及高并发场景
# ═══════════════════════════════════════════════════════════════
from datacore import AsyncDataProvider
adc = AsyncDataProvider()

await adc.get("RB", DataType.OHLCV, adjustment="continuous", period="daily")  # async 版本
await adc.get("RB", DataType.SENTIMENT)
await adc.get_f10("RB")
await adc.get_health()
await adc.batch_get_quotes(["RB", "CU", "AU"])                # 批量（新增）
```

### 5.2 技术指标 API

```python
# 完全兼容 FDC 原有接口
from datacore.indicators import compute_indicators, INDICATOR_NAMES
from datacore.indicators import assess_trend_maturity

# 三层指标体系（优先级: TDX formula_zb(实盘一致) → FDC numpy → TA-Lib 兜底）

# 用法 1: 独立计算（纯函数，和数据获取解耦）
data = {"close": [3700, 3720, 3750, ...], "high": [...], "low": [...], "volume": [...]}
result = compute_indicators(data, "all")
# 内部路由: TDX formula_zb 有 → 用它；没有 → FDC numpy；再没有 → TA-Lib

# 用法 2: 指定指标源（需要交叉验证或强制走特定实现）
result = compute_indicators(data, "RSI", source="talib")  # 强制用 TA-Lib 交叉验证
result = compute_indicators(data, "RSI", source="tdx")    # 强制用通达信公式
result = compute_indicators(data, "RSI", source="fdc")    # 强制用 FDC numpy

# 用法 3: 从 Data-Core 获取 K 线后自动计算
payload = adc.get("RB", DataType.OHLCV)
indicators = payload.meta.get("indicators")  # 可选：get 时同时计算
```

### 5.3 F10 综合报告 API

```python
# 一次调用返回 5 类数据的聚合
from datacore import UnifiedDataProvider
dc = UnifiedDataProvider()
f10 = dc.get_f10("RB")
# f10.data = {
#   "term_structure": [...],   # 期限结构
#   "spread": {...},           # 跨期价差
#   "basis": {...},            # 基差
#   "warrant": {...},          # 仓单
#   "fundamental": {...},      # 基本面（可选 LLM 增强）
# }
```

### 5.4 BaseTool 层 — ★ 核心交付

BaseTool 是 v2.0 的核心——Data-Core 的所有数据能力最终通过这个层暴露给 AI Agent。Agent 框架不需要 import datacore，不需要了解数据类型枚举，只需要 `ToolNode(all_tools)` 即可获得全部金融数据能力。

| Tool | 对应的 API |
|:-----|:-----------|
| `DataCoreOHLCVTool` | `adc.get(symbol, OHLCV)` |
| `DataCoreQuoteTool` | `adc.get(symbol, QUOTE)` |
| `DataCoreSentimentTool` | `adc.get(symbol, SENTIMENT)` |
| `DataCoreHealthTool` | `adc.get_health()` |
| `DataCoreIndicatorsTool` | `compute_indicators(data)` |
| `DataCoreF10Tool` | `adc.get_f10(symbol)` |
| `DataCoreAdjustmentTool` | `apply_adjustment(kline, adjustment="qfq")` |
| `DataCorePeriodTool` | `resample_kline(kline, target_period="daily")` |
| `DataCoreMacroTool` | `adc.get("*", MACRO)` |
| ... | ... |

---

## 6. Qlib/RD-Agent 适配器

### 6.1 背景

[Qlib](https://github.com/microsoft/qlib) 是微软开源的 AI 量化平台，提供从数据获取、因子工程、模型训练到回测执行的完整管线。[RD-Agent](https://github.com/microsoft/RD-Agent) 构建在 Qlib 之上，是一个自动化研究开发的 AI Agent 系统。两者都需要可靠、统一的数据后端。

**核心结论**：不能无感替换。Qlib 和 RD-Agent 使用自定义的 `DataProvider` 接口，必须写适配器 `DataCoreQLibProvider` 才能接入 Data-Core。

### 6.2 适配方案

Qlib 的数据接口由以下 Provider 组成，需要逐一实现适配：

```
Qlib DataProvider 接口体系:
┌─────────────────────────────────────────────────────┐
│  Qlib / RD-Agent (消费方)                            │
│                                                     │
│  DataProvider ──get_features()──→ pd.DataFrame       │
│  CalendarProvider ──get_calendar()──→ pd.DatetimeIndex│
│  InstrumentProvider ──get_instruments()──→ pd.DataFrame│
│  FeatureProvider ──get_feature_config()──→ dict       │
└──────────┬────────────────────────────────────────┘
           │
┌──────────▼────────────────────────────────────────┐
│  DataCoreQLibProvider (适配器层, 新增)              │
│                                                     │
│  DataProvider.get_features():                       │
│    symbol, start_time, end_time, freq               │
│    └→ adc.get(symbol, OHLCV) 或 adc.get(symbol, QUOTE) │
│    └→ 将结果组织为 Qlib 期望的 MultiIndex DataFrame     │
│                                                     │
│  CalendarProvider.get_calendar():                   │
│    └→ 交易日历缓存，从 Data-Core 获取                │
│                                                     │
│  InstrumentProvider.get_instruments():               │
│    └→ dc.get("*", MARKET_STATE) 或预配置本地列表      │
│                                                     │
│  FeatureProvider: 指向 Data-Core indicators 模块     │
└──────────┬────────────────────────────────────────┘
           │
┌──────────▼────────────────────────────────────────┐
│  Data-Core v2.0 (统一数据中枢)                       │
│  adc.get() / dc.get() / compute_indicators()        │
│  全部数据源 / 缓存 / 熔断器 / 降级链                  │
└────────────────────────────────────────────────────┘
```

### 6.3 DataCoreQLibProvider 接口设计

```python
# datacore/qlib_adapter/provider.py — 新增
from qlib.data import DataProvider, CalendarProvider, InstrumentProvider

class DataCoreQLibProvider(DataProvider):
    """Qlib DataProvider 的 Data-Core 实现。"""

    def __init__(self, freq: str = "day"):
        from datacore import AsyncDataProvider
        self._adc = AsyncDataProvider()
        self._freq = freq

    def get_features(
        self,
        instruments: list[str],
        fields: list[str],
        start_time: str,
        end_time: str,
        freq: str = "day",
    ) -> pd.DataFrame:
        """
        内部调用 adc.get() 获取数据，按 Qlib MultiIndex 格式组织。
        实现方式：
          1. 先确定 data_type（OHLCV / QUOTE / 指标等）
          2. adc.get(symbol, data_type, params)
          3. 转成 Qlib 期望的 MultiIndex (datetime, instrument) × field 格式
        """
        ...


class DataCoreCalendarProvider(CalendarProvider):
    def get_calendar(
        self, start_time: str, end_time: str, freq: str = "day"
    ) -> pd.DatetimeIndex:
        """从 Data-Core 获取交易日历并缓存。"""
        ...


class DataCoreInstrumentProvider(InstrumentProvider):
    def get_instruments(
        self, market: str = "ALL", names: list[str] | None = None
    ) -> pd.DataFrame:
        """从 Data-Core 获取合约/股票列表。"""
        ...
```

### 6.4 RD-Agent 兼容

RD-Agent 构建在 Qlib 的 DataProvider 之上，因此 `DataCoreQLibProvider` 对 RD-Agent 自动兼容——不需要为 RD-Agent 单独写适配器。

```
RD-Agent 依赖链:
  RD-Agent → Qlib DataLayer → DataProvider (接口) 
                              └→ DataCoreQLibProvider (实现) ← Data-Core

RD-Agent 所需的全部数据（K 线/行情/因子/回测数据）都通过 DataCoreQLibProvider
从 Data-Core 获取，RD-Agent 自身代码无需修改。
```

### 6.5 适配器注册方式

```python
# 方式 1: Qlib 启动时注入自定义 Provider
import qlib
from datacore.qlib_adapter import DataCoreQLibProvider

qlib.init(provider_uri="ignore", 
          provider_class_map={
              "data": DataCoreQLibProvider,
              "calendar": DataCoreCalendarProvider,
              "instrument": DataCoreInstrumentProvider,
          })

# 方式 2: 通过 Data-Core tools 间接暴露
from datacore.tools import DataCoreQLibDataTool
# 该 Tool 封装 DataCoreQLibProvider.get_features() 供 Agent 调用
```

### 6.6 工作量估算

| 工作 | 说明 | 工作量 |
|:-----|:-----|:-------|
| `DataCoreQLibProvider` | Qlib DataProvider 实现 | 1.5 人日 |
| `DataCoreCalendarProvider` | 交易日历提供 | 0.5 人日 |
| `DataCoreInstrumentProvider` | 合约/股票列表 | 0.5 人日 |
| RD-Agent 验证 | 跑通 RD-Agent 的端到端管线 | 0.5 人日 |
| 适配器注册 + 测试 | 单元测试 + Qlib 集成测试 | 1 人日 |

**小计：4 人日**

### 6.7 验证标准

```
✅ DataCoreQLibProvider.get_features() 返回 Qlib 可识别的 MultiIndex DataFrame
✅ Qlib 端到端管线: init → get_features → 模型训练 使用 Data-Core 数据
✅ RD-Agent 端到端管线: 研究 → 生成信号 使用 Data-Core 数据
✅ 适配器自动处理交易日历（排除非交易日）
✅ 新增 ≥ 20 个测试用例
✅ 不影响 Data-Core 现有 718 测试
```

---

## 7. 实施路线图

### 路线图总览

```
Phase 1 (v1.1)          Phase 2 (v1.2)          Phase 3 (v1.3)          Phase 4 (v2.0)          Phase 5 (v2.0)
  基础设施 + 双接口       吸收 FDC 模块          新增采集+Tool+复权      FDT 迁移               Qlib/RD-Agent 适配
────────────────        ──────────────        ──────────────          ──────────────          ──────────────────
AsyncDataProvider       技术指标 40+            Web 爬虫                替换全部 import          DataCoreQLibProvider
双引擎架构               TDX 公式              开源库/文档              适配 async               CalendarProvider
F10 综合报告             趋势成熟度             搜索                    指标/F10 迁移             InstrumentProvider
共享缓存/熔断器           QMT/TqSDK 采集         BaseTool 30+           删除 FDC 模块            RD-Agent 兼容验证
                            WebFallback           清洗/校验/衍生           全面测试
                            数据新鲜度             复权/换月引擎（新增）
                                                 周期转换引擎（新增）
                                                 运维工具
```

### Phase 1 — 基础设施 + 双接口（v1.1, ~3.5 人日）

**目标**: Data-Core 基础架构升级为双引擎，不新增数据源。

```python
# 新增文件
datacore/
├── api_async.py          # AsyncDataProvider — async 接口
├── api_f10.py            # get_f10() — F10 综合报告
└── core/                 # 共享基础设施
    ├── __init__.py
    ├── types.py           # KlineBar/QuoteData （从 FDC 搬入）
    └── data_freshness.py  # 数据新鲜度评估

# 关键逻辑: AsyncDataProvider 内部复用 UnifiedDataProvider
class AsyncDataProvider:
    def __init__(self):
        self._sync = UnifiedDataProvider()  # 复用同步引擎

    async def get(self, symbol, data_type, params=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync.get, symbol, data_type, params
        )
```

**验证标准**:
- [ ] `await adc.get("RB", DataType.OHLCV)` 返回和 `dc.get()` 一致的结果
- [ ] 同步 API 100% 向后兼容，全部 718 测试通过
- [ ] F10 综合报告返回 5 个子模块数据
- [ ] 异步性能同步的 2 个并发 `get()` 可并行执行

### Phase 2 — 吸收 FDC 模块（v1.2, ~3 人日）

**目标**: FDC 的核心模块搬入 Data-Core，指标计算可用。

```python
# 新增/修改文件
datacore/
├── indicators/              # 新增 — 从 FDC 整体搬入 + TA-Lib 兜底
│   ├── __init__.py          # 导出 compute_indicators
│   ├── core.py              # 40+ 基础指标（FDC numpy）
│   ├── tdx_compat.py        # TDX 对齐指标
│   ├── legacy_numpy.py      # 旧版兼容
│   ├── trend_maturity.py    # 趋势成熟度
│   └── talib_wrapper.py     # TA-Lib 封装兜底（新增）
│
├── futures/providers/
│   ├── qmt.py               # 新增 — QMTCollector (适配)
│   ├── tqsdk.py             # 新增 — TqSdkCollector (适配)
│   └── web_fallback.py      # 新增 — WebFallback (适配)

# 修改文件
datacore/futures/futures_provider.py  # 降级链新增 3 个源
datacore/api.py                       # F10 注册到统一接口
```

**验证标准**:
- [ ] `compute_indicators({"close": [...], "high": [...]}, "all")` 返回 40+ 指标，与 FDC 结果一致
- [ ] 指标路由优先级正确：TDX formula_zb(主) → FDC numpy(次) → TA-Lib(兜底)
- [ ] TA-Lib 兜底自动生效：前两层未覆盖的指标名自动路由到 TA-Lib
- [ ] `assess_trend_maturity(kline)` 返回和 FDC 一致的结果
- [ ] 新增 3 个期货币源接入降级链
- [ ] 期货降级链优先级: TDX → EastMoney → QMT → ExchangeAPI → ShengYiShe → WebFallback → TqSDK
- [ ] 全部测试保持 ≥ 718 pass

### Phase 3 — ★ 核心：新增采集 + BaseTool + 复权引擎 + 周期转换（v1.3, ~22 人日）

**目标**: 这是 v2.0 的心脏——把 Data-Core 全部数据能力包装为 AI Agent 可直接调用的 BaseTool，同时补齐复权/换月引擎、周期转换引擎、清洗/校验/衍生计算等配套工具链。

**架构关系**: BaseTool 包装 sync API 和 async API。Agent 框架通过 ToolNode 直接调用，无需接触底层 Python API。

#### 3.1 新增采集源

```
datacore/collectors/              # 新建采集模块
├── __init__.py
├── web_crawl/
│   ├── __init__.py
│   ├── web_collector_client.py   # 封装 Java WebCollector
│   └── firecrawl_client.py       # 封装 Firecrawl API
├── open_source/
│   ├── __init__.py
│   ├── akshare_client.py         # 封装 akshare
│   └── openbb_client.py          # 封装 openbb
├── local_doc/
│   ├── __init__.py
│   └── pdf_excel_reader.py       # PDF/Excel → DataFrame
└── search/
    ├── __init__.py
    └── tavily_client.py          # 封装 Tavily API
```

| 工具 | 来源类型 | 工作量 |
|:-----|:---------|:-------|
| `WebCollectorHttpCrawlTool` | Web 爬虫 | 1 人日 |
| `FirecrawlScrapeTool` | Web 爬虫 | 0.5 人日 |
| `TavilySearchTool` | Web 搜索 | 0.5 人日 |
| `AKShareDataTool` | 开源库 | 1 人日 |
| `OpenBBFinancialTool` | 开源库 | 1 人日 |
| `LocalReportRetrieveTool` | 本地文档 | 1 人日 |

**小计: 6 个工具, 5 人日**

#### 3.2 清洗工具链

```
datacore/cleaning/
├── unit_unify.py       # 单位标准化（吨/万吨/元/美元映射）
├── date_align.py       # 时间对齐（交易日历）
├── duplicate_merge.py  # 多源去重（按权重覆盖）
├── table_struct.py     # HTML/PDF 表格 → JSON
└── outlier_filter.py   # 异常过滤（3σ/IQR）
```

| 工具 | 工作量 |
|:-----|:-------|
| `UnitUnifyTool` | 1 人日 |
| `DateAlignTool` | 1 人日 |
| `DuplicateMergeTool` | 1 人日 |
| `TableStructTool` | 1.5 人日 |
| `OutlierFilterTool` | 1 人日 |

**小计: 5 个工具, 5.5 人日**

#### 3.3 校验与衍生计算

```
datacore/validation/
├── weight_score.py     # 数据源可信度权重表
├── cross_source.py     # 多源交叉验证
├── missing_detect.py   # 缺失检测
└── cal_math.py         # 衍生因子（库存同比/基差/季节性/加工利润）
```

| 工具 | 工作量 |
|:-----|:-------|
| `DataSourceWeightScoreTool` | 0.5 人日 |
| `CrossSourceVerifyTool` | 2 人日 |
| `DataMissingDetectTool` | 1 人日 |
| `CalMathComputeTool` | 2 人日 |

**小计: 4 个工具, 5.5 人日**

#### 3.4 运维工具

| 工具 | 工作量 |
|:-----|:-------|
| `CrawlRetryTool`（指数退避重试）| 0.5 人日 |
| `ErrorLogWriteTool`（结构化审计日志）| 0.5 人日 |
| `AlertNoticeTool`（钉钉/企微通知，包装 alert.py）| 1 人日 |
| `ConfigReadTool`（动态配置加载）| 0.5 人日 |

**小计: 4 个工具, 2.5 人日**

#### 3.5 复权/换月引擎 ★ 新增

将所有复权/换月处理集中到 Data-Core，消费端通过 `adjustment` 参数声明需求。

```
datacore/adjustment/              # 新增 — 复权/换月处理模块
├── __init__.py                   # 导出 apply_adjustment()
├── equity/                      # 股票/ETF/可转债/REITs 复权
│   ├── forward_adjust.py        # 前复权算法
│   ├── backward_adjust.py       # 后复权算法
│   └── dividend_calendar.py     # 除权除息日历缓存
├── futures/                     # 期货主力连续合约
│   ├── dominant_contract.py     # 主力合约识别（成交量/持仓量/规则）
│   ├── rollover.py              # 换月算法（成交量加权/持仓量加权/固定日）
│   ├── continuous.py            # 连续合约拼接
│   └── adjust_methods.py        # 换月时的价差调整方式（前复权/后复权/等权）
├── registry.py                  # adjustment 参数 → 处理管线映射
└── engine.py                    # 统一入口，被 UnifiedDataProvider.get() 调用
```

| 子模块 | 工作量 |
|:-------|:-------|
| `equity/` — 股票复权（前/后/不复权） | 1 人日 |
| `futures/dominant_contract.py` — 主力合约识别 | 1 人日 |
| `futures/rollover.py` — 换月算法 | 1.5 人日 |
| `futures/continuous.py` — 连续拼接 | 1 人日 |
| `engine.py + registry.py` — 统一入口 | 0.5 人日 |
| BaseTool `DataCoreAdjustmentTool` | 0.5 人日 |
| 测试 | 1.5 人日 |

**小计: 7 人日**

#### 3.6 周期转换引擎 ★ 新增

所有 K 线数据的周期转换由 Data-Core 统一完成。消费端只需指定 `period` 参数，不感知底层 Provider 支持的周期。

```
datacore/resampler/               # 新增 — 周期转换模块
├── __init__.py                   # 导出 resample_kline()
├── registry.py                   # period 取值 → 目标粒度映射
├── ohlcv.py                     # OHLCV 重采样核心（first/max/min/last/sum）
├── volume.py                     # 成交量/持仓量聚合
├── calendar.py                   # 交易日历（周线周一起始、月线自然月）
└── auto.py                       # auto 模式：按数据量自动选择
```

**处理管线位置**: 先做复权/换月（adjustment），再做周期转换（resample）。

```
原始数据 → 复权/换月引擎 → 周期转换引擎 → 消费端
                              ↑
                         period 参数控制
```

| 子模块 | 工作量 |
|:-------|:-------|
| `ohlcv.py` — OHLCV 重采样核心 | 1 人日 |
| `volume.py` — 成交量聚合 | 0.5 人日 |
| `calendar.py` — 交易日历对齐 | 0.5 人日 |
| `registry.py + auto.py` — 映射与自动选择 | 0.5 人日 |
| BaseTool `DataCorePeriodTool` | 0.5 人日 |
| 测试 | 1 人日 |

**小计: 4 人日**

#### 3.7 BaseTool 接口层 ★ 核心交付

将 Data-Core 全部能力包装为 LangChain BaseTool，自动发现注册。这是 v2.0 的心脏——Agent 开发者只需要

```python
from datacore.tools import all_tools

# LangGraph: 一行代码接入全部金融数据能力
graph.add_node(ToolNode(all_tools))
```

无需 import UnifiedDataProvider，无需了解 DataType 枚举，Agent 通过 Tool 名和参数描述自动调用。

```
datacore/tools/
├── __init__.py           # all_tools = discover_tools("datacore.tools")
├── base.py               # DataCoreBaseTool
├── ohlcv.py              │
├── quote.py              │
├── sentiment.py          │ A 组：包装现有 dc.get() API
├── health.py             │ 10 个 Tool，每个 ~30 行 adapter
├── list_symbols.py       │
├── macro.py              │
├── fundamental.py        │
├── contract_chain.py     │
├── term_structure.py     │
├── basis.py              │
├── indicators.py         │
├── f10.py                │ B 组：包装 FDC 吸收后的新能力
├── tdx_formula.py        │ 6 个 Tool
├── trend_maturity.py     │
├── market_regime.py      │
├── news.py               │
└── cleaning/ validation/ operations/   C-E 组：清洗/校验/运维 Tool
```

**小计: 16+ 个 Tool, 5 人日**

#### 3.8 可选 MCP Server

列为可选模块，暂不实现。当前 BaseTool 已能被 Claude/Cursor 通过 MCP 适配器调用。

#### 3.9 验证标准

```
✅ Agent 一行代码接入: graph.add_node(ToolNode(from datacore.tools import all_tools))
✅ 16+ BaseTool 自动发现，每个带完整 args/description/schema
✅ 6 个新增采集器（爬虫/开源/文档/搜索）
✅ 5 清洗 + 4 校验 + 4 运维工具
✅ 衍生因子计算 ≥ 5 种
✅ 全链路 trace_id 贯穿
✅ 可选 MCP Server
✅ 新增 ≥ 100 个测试用例
```

**v2.0 的成功标准**: 一个不熟悉 Data-Core 的开发者，只需要知道 `from datacore.tools import all_tools`，就能在自己的 Agent 中调用 Data-Core 的全部数据能力。**不需要看文档，不需要读源码。**

#### 3.10 消费者反馈通道（新增）

**问题**: Data-Core 当前是单向管道——任何消费方（FDT、FTS、量化策略、回测引擎、AI Agent 等）发现数据问题（空数据、陈旧、异常）没有结构化渠道通知 Data-Core，只能人工告知开发者。

**方案**: 在 `UnifiedDataProvider` 中新增通用消费者反馈机制，任何调用 Data-Core 的消费方发现问题后调用同一套 `report_issue()` API，Data-Core 自动记录、降级应对、并在健康检查中暴露。消费方只需标注自己的身份（consumer 字段），无需额外配置。

```python
# datacore/issue.py — 新增
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IssueType(str, Enum):
    DATA_EMPTY = "data_empty"           # 返回空数据
    DATA_STALE = "data_stale"           # 数据停留太久未更新
    DATA_ANOMALY = "data_anomaly"       # 数据值异常（跳变/负价格等）
    SOURCE_UNAVAILABLE = "source_unavailable"  # 数据源不可用
    TYPE_UNSUPPORTED = "type_unsupported"      # 请求的 DataType 无数据源支持
    SLOW_RESPONSE = "slow_response"     # 响应过慢


@dataclass
class DataIssue:
    symbol: str
    data_type: str
    issue_type: IssueType
    detail: str
    source: str               # 产生问题的数据源名称
    consumer: str             # 报告者（"FDT.quant-daily" / "FTS"）
    timestamp: float = 0.0
    resolved: bool = False
    resolution: str = ""


class IssueRegistry:
    """数据问题注册表 — 聚合消费者反馈。"""

    def __init__(self):
        self._issues: list[DataIssue] = []

    def report(self, issue: DataIssue) -> dict:
        """记录问题并自动降级应对。"""
        self._issues.append(issue)
        return self._auto_mitigate(issue)

    def _auto_mitigate(self, issue: DataIssue) -> dict:
        """根据问题类型自动触发应对。"""
        mitigations = []
        if issue.issue_type in (IssueType.DATA_EMPTY, IssueType.SOURCE_UNAVAILABLE):
            mitigations.append(f"触发 {issue.source} 熔断器")
            # 实际调用 circuit_breaker
        if issue.issue_type == IssueType.DATA_STALE:
            mitigations.append(f"强制刷新 {issue.symbol} 缓存")
        return {"mitigated": len(mitigations) > 0, "actions": mitigations}

    def unresolved(self, symbol: Optional[str] = None) -> list[DataIssue]:
        return [i for i in self._issues if not i.resolved
                and (symbol is None or i.symbol == symbol)]

    def resolve(self, symbol: str, data_type: str, resolution: str = "") -> int:
        count = 0
        for i in self._issues:
            if i.symbol == symbol and i.data_type == data_type and not i.resolved:
                i.resolved = True
                i.resolution = resolution
                count += 1
        return count

    def stats(self) -> dict:
        """聚合统计，供 get_health() 展示。"""
        all_issues = self._issues
        unresolved_count = len([i for i in all_issues if not i.resolved])
        by_type = {}
        for i in all_issues:
            by_type.setdefault(i.issue_type.value, 0)
            by_type[i.issue_type.value] += 1
        return {
            "total_reported": len(all_issues),
            "unresolved": unresolved_count,
            "by_type": by_type,
        }
```

```python
# UnifiedDataProvider 新增方法
class UnifiedDataProvider:
    def __init__(self):
        ...
        self._issues = IssueRegistry()

    def report_issue(self, symbol: str, data_type: str, issue_type: str,
                     detail: str, source: str = "",
                     consumer: str = "unknown") -> dict:
        """消费者报告数据问题。"""
        issue = DataIssue(
            symbol=symbol, data_type=data_type,
            issue_type=IssueType(issue_type),
            detail=detail, source=source, consumer=consumer,
        )
        return self._issues.report(issue)

    def get_health(self):
        """健康检查中暴露未解决的消费者反馈。"""
        health = ...  # 原有健康检查
        health["consumer_issues"] = self._issues.stats()
        return health
```

**使用示例（任何消费方）**:

```python
# 策略/Agent/FDT 发现数据问题，立即报告
from datacore import UnifiedDataProvider
dc = UnifiedDataProvider()

payload = dc.get("RB", DataType.FUTURES_POSITION)
if not payload.available:
    dc.report_issue(
        symbol="RB",
        data_type="FUTURES_POSITION",
        issue_type="data_empty",
        detail=f"所有数据源均返回空，最后尝试: {payload.meta.get('tried_sources', [])}",
        source=payload.source,
        consumer="my_trading_strategy",  # 谁报告的，自己命名
    )
```

**集成价值**:

| 场景 | 以前 | 以后 |
|:-----|:-----|:-----|
| 数据源挂了 | 消费方默默拿到空数据，策略算错 | 消费方报告 → Data-Core 降级 + 记录在案 |
| 数据陈旧 | 没人知道，直到分析时发现 | 任一消费方上报 → 触发缓存刷新 |
| 某 DataType 频繁失败 | 靠开发者手动排查 | 多消费方聚合 → 开发者直接看热点 |
| 跨项目质量对比 | 无从得知 | 按 consumer 字段区分统计 |

**工作量: 1 人日（含测试）**

### Phase 4 — FDT 迁移（v2.0, ~4.5 人日）

**目标**: FDT 完全移除 `futures_data_core`，全部走 Data-Core。

**迁移步骤**:

```
Step 1: import 替换（~1 人日）
  FDT 中 62 个文件引用了 FDC
  全局替换:
    from futures_data_core import get_kline  →  from datacore import AsyncDataProvider
    from futures_data_core.indicators import ...  →  from datacore.indicators import ...

Step 2: async API 适配（~1 人日）
  await get_kline("RB", "daily", 120)  →  await adc.get("RB", DataType.OHLCV)

Step 3: 指标/F10 调用适配（~0.5 人日）
  compute_indicators(data, "all")  →  不变（保持函数签名兼容）
  get_f10("RB")  →  adc.get_f10("RB")

Step 4: 测试验证（~1 人日）
  跑通 FDT 全部测试: pytest tests/ -q

Step 5: 清理（~0.5 人日）
  删除 futeres_data_core/ 整个目录
  更新 FDT 的 pyproject.toml（移除 fdc 依赖，添加 datacore 依赖）
```

**FDT 迁移后的依赖关系**:

```
迁移前:                   迁移后:
FDT                      FDT
 ├── futures_data_core    └── datacore (统一数据中枢)
 ├── fdt_langgraph              ├── futures (含 TDX/QMT/TqSDK)
 └── quant-daily               ├── equity
                               ├── macro
                               ├── indicators
                               ├── processing
                               ├── stream
                               └── tools
```

---

## 8. FDT 迁移策略

### 8.1 迁移顺序

不要大爆炸式迁移，按依赖链从底层开始：

```
┌─────────────────────────────────────────────────────────────────┐
│  迁移顺序 (自底向上)                                             │
│                                                                  │
│  ① indicators (纯函数，零风险)                                    │
│     from futures_data_core.indicators → from datacore.indicators  │
│                                                                  │
│  ② K 线/行情 (核心数据)                                          │
│     await get_kline() → await adc.get(symbol, OHLCV)              │
│                                                                  │
│  ③ F10/期限结构/价差/基差/仓单                                    │
│     await get_f10() → await adc.get_f10()                         │
│                                                                  │
│  ④ multi_source_adapter (降级链)                                 │
│     删除整个模块，改用 adc.get()                                   │
│                                                                  │
│  ⑤ collector 目录删除                                            │
│     futures_data_core/ 整目录移除                                  │
│                                                                  │
│  ⑥ pyproject.toml 依赖更新                                       │
│     futures-data-core → datacore                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 兼容层（可选，降低迁移风险）

在 Data-Core 中提供一个 FDC 兼容模块，让 FDT 原有代码无需大量修改：

```python
# datacore/fdc_compat.py — 兼容层（迁移过渡期使用）
from datacore import AsyncDataProvider

_adc = AsyncDataProvider()

# 保持和 FDC 相同的函数签名
async def get_kline(symbol, period="daily", days=120, source="auto"):
    """兼容 FDC 的 get_kline 接口。"""
    data_type = _period_to_datatype(period)  # "daily" → DataType.OHLCV
    payload = await _adc.get(symbol, data_type, {"period": period, "days": days})
    return _to_fdc_payload(payload)

async def compute_indicators(data, names="all"):
    """兼容 FDC 的 compute_indicators 接口。"""
    from datacore.indicators import compute_indicators as ci
    return ci(data, names)
```

这样 FDT 只需要改 import 路径，函数签名不变：

```python
# 改前: from futures_data_core import get_kline
# 改后: from datacore.fdc_compat import get_kline
# 调用代码: await get_kline("RB", "daily", 120)  — 不用改
```

### 8.3 风险控制

| 风险 | 概率 | 应对 |
|:-----|:-----|:-----|
| 数据不一致（DC vs FDC 同品种不同价） | 中 | Phase 2 后运行对照期，双写双读验证 |
| 异步性能下降（sync bridge） | 低 | `run_in_executor` 走线程池，实测验证 |
| FDT 迁移期间回归 | 中 | 兼容层逐步替换，每个子模块切换后跑对应测试 |
| FDC 特有功能遗漏 | 低 | FDC 公开 API 清单逐一对照（`__init__.py` 的 `__all__`） |

---

## 9. 验收标准

### v1.1 — 基础设施 + 双接口

```
✅ AsyncDataProvider 可用，await adc.get() 返回和 dc.get() 一致
✅ get_f10("RB") 返回 5 子模块聚合数据（期限结构/价差/基差/仓单/基本面）
✅ 同步 API 100% 向后兼容
✅ 全部 718 测试通过
✅ docs/UPGRADE_V2_PLAN.md 由本文档取代
```

### v1.2 — FDC 模块吸收

```
✅ compute_indicators() 返回 40+ 指标，与 FDC 结果一致
✅ assess_trend_maturity() 可用
✅ QMT/TqSDK/WebFallback 3 个期货新源接入降级链
✅ 期货降级链完整: TDX → EastMoney → QMT → ExchangeAPI → ShengYiShe → WebFallback → TqSDK
✅ 全部测试 ≥ 758 pass（新增 ≥ 40 个）
```

### v1.3 — 新增采集 + BaseTool + 复权引擎 + 周期转换

```
✅ 6 个新增采集器（爬虫/开源/文档/搜索）
✅ 5 清洗 + 4 校验 + 4 运维工具
✅ 复权/换月引擎可用：
   ✅ 股票前复权/后复权/不复权
   ✅ 期货主力连续合约拼接（成交量加权/持仓量加权/固定日）
   ✅ 期货主力连续 + 前复权 / 后复权
   ✅ 消费端只需传 adjustment 参数
✅ 周期转换引擎可用：
   ✅ 1min→5min→15min→30min→60min→daily→weekly→monthly
   ✅ OHLCV 正确聚合（O=first, H=max, L=min, C=last, V=sum）
   ✅ 消费端只需传 period 参数，不感知底层 Provider
   ✅ auto 模式自动选择合适周期
✅ 30+ BaseTool 自动发现
✅ 可选 MCP Server
✅ 新增 ≥ 140 个测试用例
✅ 不影响 Data-Core 现有 718 测试

### v2.0 — FDT 迁移完成

```
✅ FDT 全部 62 个文件不再 import futures_data_core
✅ FDT 全部测试通过
✅ futures_data_core/ 目录删除
✅ FDT pyproject.toml 依赖变更为 datacore
✅ FDC 兼容层（如存在）标记为 deprecated
✅ docs/harness/ 全部 12 份文档同步更新
```

### Phase 5 — Qlib/RD-Agent 适配

```
✅ DataCoreQLibProvider.get_features() 返回 Qlib 可识别的 MultiIndex DataFrame
✅ DataCoreCalendarProvider 返回正确的交易日历
✅ DataCoreInstrumentProvider 返回正确的合约/股票列表
✅ Qlib 端到端管线: init → get_features → 模型训练 使用 Data-Core 数据
✅ RD-Agent 端到端管线: 研究 → 生成信号 使用 Data-Core 数据
✅ 适配器自动处理交易日历（排除非交易日）
✅ 新增 ≥ 20 个测试用例
✅ 不影响 Data-Core 现有 718 测试
```

---

## 附录：文件产出清单

| Phase | 新增文件 | 新增行数（估） | 修改文件 |
|:------|:---------|:---------------|:---------|
| P1 | `api_async.py`, `api_f10.py`, `core/` (3 个) | ~400 | `api.py`, `config.py`, `pyproject.toml` |
| P2 | `indicators/` (5 个), `futures/providers/qmt.py/tqsdk.py/web_fallback.py` (3 个) | ~1800 | `futures_provider.py` |
| P3 | `tools/` (30+), `collectors/` (6), `cleaning/` (5), `validation/` (5), `adjustment/` (8+), `resampler/` (6), `mcp_server.py` | ~3700 | `pyproject.toml`, `README.md` |
| P4 | 兼容层 `fdc_compat.py`（可选） | ~200 | FDT 全部 62 个引用文件 |
| P5 | `qlib_adapter/provider.py`, `qlib_adapter/calendar.py`, `qlib_adapter/instrument.py` | ~400 | — |
| 文档 | `docs/TOOLS_GUIDE.md` | ~500 | `docs/harness/` 全部 9 份 |
