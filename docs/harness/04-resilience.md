# Data-Core Resilience

Version: v0.1.0 | Updated: 2026-07-18

## Degradation Strategy
- TQ-Local unavailable -> auto degrade to EastMoney HTTP
- Tencent API unavailable -> auto degrade to EastMoney HTTP
- All sources unavailable -> return UNAVAILABLE grade
- Network timeout -> 3s fast fail, try next source
