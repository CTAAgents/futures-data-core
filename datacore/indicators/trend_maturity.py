"""趋势成熟度评估模块。

通过多维度指标综合评估趋势的成熟度阶段，
帮助判断趋势是处于初期、中期还是末期。

评估维度:
- 趋势强度: ADX, 均线斜率
- 动量衰减: RSI 背离, MACD 柱衰减
- 波动率: ATR 变化, 布林带宽度
- 量价配合: OBV 趋势, 成交量变化
- 周期位置: 相对于历史波动的位置
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from datacore.indicators.core import (
    ma, rsi, macd, atr, dmi, obv, boll,
    linear_reg_slope,
)


@dataclass
class TrendMaturityResult:
    """趋势成熟度评估结果。

    Attributes:
        stage: 趋势阶段: "early" 初期, "mid" 中期, "late" 末期, "unknown" 未知
        score: 综合成熟度分数 0-100，越高越接近末期
        confidence: 评估置信度 0-1
        trend_direction: 趋势方向: "up", "down", "sideways"
        strength_score: 趋势强度分数 0-100
        momentum_score: 动量分数 0-100
        volatility_score: 波动率分数 0-100
        volume_score: 量能分数 0-100
        features: 详细特征字典
    """
    stage: str = "unknown"
    score: float = 0.0
    confidence: float = 0.0
    trend_direction: str = "sideways"
    strength_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    volume_score: float = 0.0
    features: dict = field(default_factory=dict)


def assess_trend_maturity(
    close: np.ndarray,
    high: Optional[np.ndarray] = None,
    low: Optional[np.ndarray] = None,
    volume: Optional[np.ndarray] = None,
    lookback: int = 60,
) -> TrendMaturityResult:
    """评估趋势成熟度。

    综合多个维度判断趋势所处的阶段。

    Args:
        close: 收盘价序列
        high: 最高价序列（可选）
        low: 最低价序列（可选）
        volume: 成交量序列（可选）
        lookback: 回溯周期数

    Returns:
        TrendMaturityResult 评估结果
    """
    n = len(close)
    if n < 20:
        return TrendMaturityResult(stage="unknown", confidence=0.0)

    high = high if high is not None else close
    low = low if low is not None else close
    volume = volume if volume is not None else np.ones_like(close)

    use_idx = min(lookback, n)
    c = close[-use_idx:]
    h = high[-use_idx:]
    low_p = low[-use_idx:]
    v = volume[-use_idx:]

    features = {}
    scores = []
    weights = []

    # 1. 趋势强度维度
    strength_score, strength_feats = _assess_strength(c, h, low_p)
    features.update(strength_feats)
    scores.append(strength_score)
    weights.append(0.30)

    # 2. 动量维度
    momentum_score, momentum_feats = _assess_momentum(c)
    features.update(momentum_feats)
    scores.append(momentum_score)
    weights.append(0.25)

    # 3. 波动率维度
    vol_score, vol_feats = _assess_volatility(c, h, low_p)
    features.update(vol_feats)
    scores.append(vol_score)
    weights.append(0.20)

    # 4. 量能维度
    volm_score, volm_feats = _assess_volume(c, v)
    features.update(volm_feats)
    scores.append(volm_score)
    weights.append(0.15)

    # 5. 周期位置维度
    pos_score, pos_feats = _assess_position(c)
    features.update(pos_feats)
    scores.append(pos_score)
    weights.append(0.10)

    total_weight = sum(weights)
    composite_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

    # 判断趋势方向
    slope = linear_reg_slope(c, min(20, len(c)))
    last_slope = slope[-1] if not np.isnan(slope[-1]) else 0.0
    mean_close = np.nanmean(c)
    slope_pct = last_slope / mean_close * 100 if mean_close != 0 else 0.0

    if slope_pct > 0.1:
        direction = "up"
    elif slope_pct < -0.1:
        direction = "down"
    else:
        direction = "sideways"

    # 判断阶段
    if composite_score < 30:
        stage = "early"
    elif composite_score < 70:
        stage = "mid"
    else:
        stage = "late"

    # 置信度
    valid_indicators = sum(1 for f in [
        "adx", "rsi", "atr_change", "obv_trend", "price_position"
    ] if f in features and not np.isnan(features.get(f, np.nan)))
    confidence = min(1.0, valid_indicators / 5.0 + 0.2)

    return TrendMaturityResult(
        stage=stage,
        score=float(composite_score),
        confidence=float(confidence),
        trend_direction=direction,
        strength_score=float(strength_score),
        momentum_score=float(momentum_score),
        volatility_score=float(vol_score),
        volume_score=float(volm_score),
        features=features,
    )


def _assess_strength(close: np.ndarray, high: np.ndarray,
                     low: np.ndarray) -> tuple[float, dict]:
    """评估趋势强度维度。

    指标:
    - ADX: 越高趋势越强，过高可能接近末期
    - 均线斜率: 斜率变化判断加速/减速
    - 多头发散度: 短中长期均线的排列状态

    Returns:
        (成熟度分数 0-100, 特征字典)
    """
    feats = {}
    n = len(close)
    score = 50.0

    # ADX
    if n >= 28:
        dmi_result = dmi(high, low, close, 14)
        adx_val = dmi_result["adx"][-1]
        if not np.isnan(adx_val):
            feats["adx"] = float(adx_val)
            if adx_val < 20:
                score = 20.0
            elif adx_val < 40:
                score = 50.0
            elif adx_val < 60:
                score = 75.0
            else:
                score = 90.0

    # 均线斜率变化
    if n >= 40:
        ma_short = ma(close, 10)
        ma_long = ma(close, 30)
        short_slope = linear_reg_slope(ma_short[-20:], 10)
        long_slope = linear_reg_slope(ma_long[-20:], 10)
        ss = short_slope[-1] if not np.isnan(short_slope[-1]) else 0.0
        ls = long_slope[-1] if not np.isnan(long_slope[-1]) else 0.0

        feats["short_ma_slope"] = float(ss)
        feats["long_ma_slope"] = float(ls)

        if ss > 0 and ls > 0:
            if ss > ls:
                feats["ma_divergence"] = "expanding"
            else:
                feats["ma_divergence"] = "converging"
                score = min(100, score + 15)
        elif ss < 0 and ls < 0:
            if abs(ss) > abs(ls):
                feats["ma_divergence"] = "expanding_down"
            else:
                feats["ma_divergence"] = "converging_down"
                score = min(100, score + 15)

    return min(100, max(0, score)), feats


def _assess_momentum(close: np.ndarray) -> tuple[float, dict]:
    """评估动量维度。

    指标:
    - RSI 位置: 超买超卖区域
    - MACD 柱变化: 柱体缩小表示动量衰减
    - 价格新高/新低数量: 动量衰竭信号

    Returns:
        (成熟度分数 0-100, 特征字典)
    """
    feats = {}
    n = len(close)
    score = 50.0

    # RSI
    if n >= 20:
        rsi_val = rsi(close, 14)
        last_rsi = rsi_val[-1]
        if not np.isnan(last_rsi):
            feats["rsi"] = float(last_rsi)
            if last_rsi > 80 or last_rsi < 20:
                score = 80.0
            elif last_rsi > 70 or last_rsi < 30:
                score = 65.0
            else:
                score = 40.0

    # MACD 柱变化
    if n >= 40:
        macd_result = macd(close, 12, 26, 9)
        hist = macd_result["histogram"]
        valid_hist = hist[~np.isnan(hist)]

        if len(valid_hist) >= 10:
            recent_hist = valid_hist[-10:]
            hist_slope = np.polyfit(np.arange(len(recent_hist)), recent_hist, 1)[0]
            feats["macd_hist_slope"] = float(hist_slope)

            max_hist = np.max(np.abs(valid_hist))
            current_hist = recent_hist[-1]
            hist_ratio = abs(current_hist) / max_hist if max_hist > 0 else 0
            feats["macd_hist_ratio"] = float(hist_ratio)

            if hist_slope < 0 and hist_ratio > 0.5:
                score = min(100, score + 20)
            elif hist_slope > 0 and hist_ratio < 0.3:
                score = max(0, score - 20)

    return min(100, max(0, score)), feats


def _assess_volatility(close: np.ndarray, high: np.ndarray,
                       low: np.ndarray) -> tuple[float, dict]:
    """评估波动率维度。

    指标:
    - ATR 变化率: 波动率放大通常出现在趋势末期
    - 布林带宽度: 带宽极值点
    - K线实体比例: 上下影线变化

    Returns:
        (成熟度分数 0-100, 特征字典)
    """
    feats = {}
    n = len(close)
    score = 50.0

    # ATR 变化
    if n >= 28:
        atr_val = atr(high, low, close, 14)
        valid_atr = atr_val[~np.isnan(atr_val)]

        if len(valid_atr) >= 10:
            current_atr = valid_atr[-1]
            avg_atr = np.mean(valid_atr[-20:]) if len(valid_atr) >= 20 else np.mean(valid_atr)
            atr_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
            feats["atr_change"] = float(atr_ratio)

            if atr_ratio > 2.0:
                score = 85.0
            elif atr_ratio > 1.5:
                score = 70.0
            elif atr_ratio < 0.7:
                score = 30.0

    # 布林带宽度
    if n >= 30:
        boll_result = boll(close, 20, 2.0)
        upper = boll_result["upper"]
        lower = boll_result["lower"]
        mid = boll_result["middle"]

        valid_idx = ~np.isnan(upper) & ~np.isnan(mid) & (mid != 0)
        if np.any(valid_idx):
            bandwidth = (upper[valid_idx] - lower[valid_idx]) / mid[valid_idx]
            current_bw = bandwidth[-1]
            avg_bw = np.mean(bandwidth[-20:]) if len(bandwidth) >= 20 else np.mean(bandwidth)
            bw_ratio = current_bw / avg_bw if avg_bw > 0 else 1.0
            feats["boll_bandwidth"] = float(current_bw)
            feats["bw_ratio"] = float(bw_ratio)

            if bw_ratio > 1.8:
                score = min(100, score + 20)
            elif bw_ratio < 0.6:
                score = max(0, score - 15)

    return min(100, max(0, score)), feats


def _assess_volume(close: np.ndarray, volume: np.ndarray) -> tuple[float, dict]:
    """评估量能维度。

    指标:
    - OBV 趋势: 量价背离信号
    - 成交量变化: 放量/缩量
    - 量价配合度: 涨跌时成交量的对称度

    Returns:
        (成熟度分数 0-100, 特征字典)
    """
    feats = {}
    n = len(close)
    score = 50.0

    # OBV
    if n >= 20:
        obv_val = obv(close, volume)
        feats["obv_latest"] = float(obv_val[-1])

        # OBV 斜率
        if n >= 30:
            obv_slope = linear_reg_slope(obv_val[-20:], 10)
            os = obv_slope[-1] if not np.isnan(obv_slope[-1]) else 0.0
            feats["obv_slope"] = float(os)

            price_slope = linear_reg_slope(close[-20:], 10)
            ps = price_slope[-1] if not np.isnan(price_slope[-1]) else 0.0

            if ps > 0 and os < 0:
                feats["obv_divergence"] = "bearish"
                score = min(100, score + 25)
            elif ps < 0 and os > 0:
                feats["obv_divergence"] = "bullish"
                score = max(0, score - 20)
            else:
                feats["obv_divergence"] = "none"

    # 成交量变化
    if n >= 20:
        recent_vol = volume[-10:]
        earlier_vol = volume[-20:-10] if n >= 20 else volume[:10]
        vol_ratio = np.mean(recent_vol) / np.mean(earlier_vol) if np.mean(earlier_vol) > 0 else 1.0
        feats["volume_ratio"] = float(vol_ratio)

        if vol_ratio > 2.0:
            score = min(100, score + 15)
        elif vol_ratio < 0.5:
            score = max(0, score - 10)

    return min(100, max(0, score)), feats


def _assess_position(close: np.ndarray) -> tuple[float, dict]:
    """评估周期位置维度。

    指标:
    - 价格在周期内的位置: 百分位
    - 回撤幅度: 从高点回撤的比例
    - 趋势持续时间: 趋势已经运行的时间

    Returns:
        (成熟度分数 0-100, 特征字典)
    """
    feats = {}
    n = len(close)
    score = 50.0

    if n >= 20:
        # 价格百分位
        period_high = np.max(close)
        period_low = np.min(close)
        price_range = period_high - period_low
        current_pos = (close[-1] - period_low) / price_range * 100 if price_range > 0 else 50.0
        feats["price_position"] = float(current_pos)

        if current_pos > 90 or current_pos < 10:
            score = 75.0
        elif current_pos > 80 or current_pos < 20:
            score = 60.0
        else:
            score = 40.0

        # 从高点回撤
        all_time_high = np.max(close)
        drawdown = (all_time_high - close[-1]) / all_time_high * 100 if all_time_high > 0 else 0.0
        feats["drawdown_pct"] = float(drawdown)

        if drawdown > 20:
            score = min(100, score + 20)

    return min(100, max(0, score)), feats
