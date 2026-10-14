"""Latency summaries for evaluation reports."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any


def percentile(sorted_values: list[float], q: float) -> float:
    """Nearest-rank percentile of already sorted values (q in 0..100)."""
    rank = max(1, math.ceil(q / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def summarize(values: Iterable[float]) -> dict[str, Any]:
    data = sorted(values)
    if not data:
        return {"count": 0, "p50": None, "p95": None, "max": None, "mean": None}
    return {
        "count": len(data),
        "p50": round(percentile(data, 50), 3),
        "p95": round(percentile(data, 95), 3),
        "max": round(data[-1], 3),
        "mean": round(sum(data) / len(data), 3),
    }


def by_quality(durations: dict[str, list[float]]) -> dict[str, dict[str, Any]]:
    """Per-document latency for each quality and for all documents together."""
    every = [d for values in durations.values() for d in values]
    return {**{q: summarize(v) for q, v in sorted(durations.items())}, "all": summarize(every)}
