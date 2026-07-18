"""A 股财务指标计算工具。"""
from __future__ import annotations
from typing import Any


def calc_financial_score(fin: dict[str, Any]) -> dict[str, float]:
    """计算综合财务评分（简化版）。"""
    score = {"value_score": 0.0, "growth_score": 0.0, "quality_score": 0.0, "composite": 0.0}
    pe = fin.get("pe_ttm") or fin.get("pe")
    pb = fin.get("pb")
    if pe and pe > 0:
        score["value_score"] = max(-1, min(1, (30 - pe) / 30))
    if pb and pb > 0:
        score["value_score"] += max(-1, min(1, (5 - pb) / 5))
    score["value_score"] /= 2
    score["composite"] = score["value_score"]
    return score
