"""Reusable metric utilities for the evaluator."""

from __future__ import annotations

import json
import math
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from ..models import EventSpec


def accuracy(rows: List[Dict[str, Any]]) -> float:
    """Fraction of predictions whose rounded probability matches the outcome."""
    if not rows:
        return 0.0
    correct = sum(1 for row in rows if round(row["probability"]) == row["outcome"])
    return correct / len(rows)


def brier_score(rows: List[Dict[str, Any]]) -> float:
    """Mean squared error between probabilities and outcomes."""
    if not rows:
        return 0.0
    return sum((row["probability"] - row["outcome"]) ** 2 for row in rows) / len(rows)


def els_information_ratio(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute Excess Log Score and Information Ratio vs market baseline."""
    values: List[float] = []
    for row in rows:
        market_prob = row.get("market_probability")
        if market_prob is None or market_prob <= 0 or market_prob >= 1:
            continue
        prob = min(max(row["probability"], 1e-6), 1 - 1e-6)
        market_prob = min(max(market_prob, 1e-6), 1 - 1e-6)
        if row["outcome"] == 1:
            score = math.log(prob) - math.log(market_prob)
        else:
            score = math.log(1 - prob) - math.log(1 - market_prob)
        values.append(score)
    if not values:
        return {"els": 0.0, "information_ratio": 0.0}
    mean_val = mean(values)
    std_val = pstdev(values) if len(values) > 1 else 0.0
    info_ratio = mean_val / std_val if std_val else 0.0
    return {"els": mean_val, "information_ratio": info_ratio}


def kelly_metrics(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Simulate Kelly-type PnL by comparing predictions to market baselines."""
    pnl_values: List[float] = []
    for row in rows:
        market_prob = row.get("market_probability")
        if market_prob is None:
            continue
        stake = max(min(row["probability"] - market_prob, 1.0), -1.0)
        pnl = stake * (row["outcome"] - market_prob)
        pnl_values.append(pnl)
    if not pnl_values:
        return {"kelly_pnl": 0.0, "kelly_sharpe": 0.0}
    avg = mean(pnl_values)
    std_val = pstdev(pnl_values) if len(pnl_values) > 1 else 0.0
    sharpe = avg / std_val if std_val else 0.0
    return {"kelly_pnl": avg, "kelly_sharpe": sharpe}


def calibration_bins(rows: List[Dict[str, Any]], bins: int = 10) -> List[Dict[str, float]]:
    """Reliability diagram bins mapping probability to empirical accuracy."""
    bucket_totals = [0] * bins
    bucket_hits = [0] * bins
    for row in rows:
        idx = min(int(row["probability"] * bins), bins - 1)
        bucket_totals[idx] += 1
        bucket_hits[idx] += row["outcome"]
    calibration = []
    for i in range(bins):
        total = bucket_totals[i]
        hit_rate = bucket_hits[i] / total if total else 0.0
        calibration.append({
            "bin_start": i / bins,
            "bin_end": (i + 1) / bins,
            "count": total,
            "hit_rate": hit_rate,
        })
    return calibration
