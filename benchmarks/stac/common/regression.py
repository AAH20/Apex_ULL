"""
STAC Benchmark Regression Detection - Baseline comparison and trend analysis.

Provides tools to:
- Compare current results against saved baselines
- Detect performance regressions/improvements
- Analyze trends across multiple runs
- Detect change points in performance
- Generate regression reports
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from common.harness import BenchmarkResult, LatencyStats


@dataclass
class Baseline:
    """Saved baseline for a single benchmark."""
    benchmark_name: str
    version: str
    timestamp: str
    latency: dict  # LatencyStats as dict
    throughput_ops_s: float
    score: float
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_result(cls, result: BenchmarkResult, timestamp: str = "") -> Baseline:
        return cls(
            benchmark_name=result.name,
            version=result.version,
            timestamp=timestamp,
            latency=result.latency.to_dict(),
            throughput_ops_s=result.throughput_ops_s,
            score=result.score,
            metadata=result.metadata,
        )


@dataclass
class PerformanceDelta:
    """Performance change between baseline and current run."""
    benchmark_name: str
    metric_name: str
    baseline_value: float
    current_value: float
    absolute_change: float
    percent_change: float
    direction: str  # "improved", "regressed", "unchanged"
    severity: str  # "none", "minor", "moderate", "major", "critical"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RegressionReport:
    """Complete regression analysis report."""
    benchmark_name: str
    has_regression: bool
    has_improvement: bool
    overall_status: str  # "improved", "regressed", "unchanged", "mixed"
    deltas: list[PerformanceDelta] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "benchmark_name": self.benchmark_name,
            "has_regression": self.has_regression,
            "has_improvement": self.has_improvement,
            "overall_status": self.overall_status,
            "deltas": [d.to_dict() for d in self.deltas],
            "summary": self.summary,
        }


def _classify_severity(metric_name: str, percent_change: float, direction: str) -> str:
    """Classify the severity of a performance change."""
    abs_change = abs(percent_change)
    if direction == "unchanged" or abs_change < 1.0:
        return "none"
    elif abs_change < 5.0:
        return "minor"
    elif abs_change < 15.0:
        return "moderate"
    elif abs_change < 30.0:
        return "major"
    else:
        return "critical"


def _classify_direction(metric_name: str, percent_change: float, lower_is_better: bool = True) -> str:
    """Classify whether a change is an improvement or regression."""
    if abs(percent_change) < 0.5:  # Less than 0.5% change is considered unchanged
        return "unchanged"
    if lower_is_better:
        return "improved" if percent_change < 0 else "regressed"
    else:
        return "improved" if percent_change > 0 else "regressed"


def compare_to_baseline(
    current: BenchmarkResult,
    baseline: Baseline,
    latency_threshold_pct: float = 5.0,
    throughput_threshold_pct: float = 5.0,
) -> RegressionReport:
    """
    Compare current benchmark results against a baseline.

    Args:
        current: Current benchmark result
        baseline: Saved baseline to compare against
        latency_threshold_pct: Percentage change threshold for latency regression
        throughput_threshold_pct: Percentage change threshold for throughput regression

    Returns:
        RegressionReport with detailed analysis
    """
    deltas: list[PerformanceDelta] = []

    # Compare key latency metrics
    latency_metrics = [
        ("p50_ns", True),
        ("p90_ns", True),
        ("p99_ns", True),
        ("mean_ns", True),
        ("stddev_ns", True),
        ("jitter_ns", True),
        ("min_ns", True),
        ("max_ns", True),
    ]

    for metric_name, lower_is_better in latency_metrics:
        baseline_val = baseline.latency.get(metric_name, 0)
        current_val = getattr(current.latency, metric_name, 0)
        if baseline_val > 0:
            abs_change = current_val - baseline_val
            pct_change = (abs_change / baseline_val) * 100.0
            direction = _classify_direction(metric_name, pct_change, lower_is_better)
            severity = _classify_severity(metric_name, pct_change, direction)
            deltas.append(PerformanceDelta(
                benchmark_name=current.name,
                metric_name=metric_name,
                baseline_value=baseline_val,
                current_value=current_val,
                absolute_change=abs_change,
                percent_change=pct_change,
                direction=direction,
                severity=severity,
            ))

    # Compare throughput
    if baseline.throughput_ops_s > 0:
        abs_change = current.throughput_ops_s - baseline.throughput_ops_s
        pct_change = (abs_change / baseline.throughput_ops_s) * 100.0
        direction = _classify_direction("throughput", pct_change, lower_is_better=False)
        severity = _classify_severity("throughput", pct_change, direction)
        deltas.append(PerformanceDelta(
            benchmark_name=current.name,
            metric_name="throughput_ops_s",
            baseline_value=baseline.throughput_ops_s,
            current_value=current.throughput_ops_s,
            absolute_change=abs_change,
            percent_change=pct_change,
            direction=direction,
            severity=severity,
        ))

    # Compare score
    if baseline.score > 0:
        abs_change = current.score - baseline.score
        pct_change = (abs_change / baseline.score) * 100.0
        direction = _classify_direction("score", pct_change, lower_is_better=False)
        severity = _classify_severity("score", pct_change, direction)
        deltas.append(PerformanceDelta(
            benchmark_name=current.name,
            metric_name="score",
            baseline_value=baseline.score,
            current_value=current.score,
            absolute_change=abs_change,
            percent_change=pct_change,
            direction=direction,
            severity=severity,
        ))

    # Determine overall status
    has_regression = any(d.direction == "regressed" for d in deltas)
    has_improvement = any(d.direction == "improved" for d in deltas)

    if has_regression and has_improvement:
        overall_status = "mixed"
    elif has_regression:
        overall_status = "regressed"
    elif has_improvement:
        overall_status = "improved"
    else:
        overall_status = "unchanged"

    # Generate summary
    regressed = [d for d in deltas if d.direction == "regressed"]
    improved = [d for d in deltas if d.direction == "improved"]
    summary_parts = []
    if regressed:
        summary_parts.append(f"Regressed: {', '.join(d.metric_name for d in regressed)}")
    if improved:
        summary_parts.append(f"Improved: {', '.join(d.metric_name for d in improved)}")
    if not summary_parts:
        summary_parts.append("No significant changes detected")
    summary = "; ".join(summary_parts)

    return RegressionReport(
        benchmark_name=current.name,
        has_regression=has_regression,
        has_improvement=has_improvement,
        overall_status=overall_status,
        deltas=deltas,
        summary=summary,
    )


def detect_trend(results: list[BenchmarkResult]) -> dict[str, Any]:
    """
    Detect performance trends across multiple runs using linear regression.

    Args:
        results: List of benchmark results in chronological order

    Returns:
        Dictionary with trend analysis for each metric
    """
    if len(results) < 2:
        return {"error": "Need at least 2 results for trend analysis"}

    trends = {}
    metrics = ["p50_ns", "p99_ns", "mean_ns", "throughput_ops_s", "score"]

    for metric in metrics:
        values = []
        for r in results:
            if metric in ("throughput_ops_s", "score"):
                values.append(getattr(r, metric, 0))
            else:
                values.append(getattr(r.latency, metric, 0))

        if len(values) < 2:
            continue

        # Simple linear regression: y = mx + b
        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = statistics.fmean(values)

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0.0
        intercept = y_mean - slope * x_mean

        # R-squared
        ss_res = sum((v - (slope * i + intercept)) ** 2 for i, v in enumerate(values))
        ss_tot = sum((v - y_mean) ** 2 for v in values)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Trend direction
        if abs(slope) < 0.001 * abs(y_mean) if y_mean != 0 else abs(slope) < 0.001:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        trends[metric] = {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "direction": direction,
            "first_value": values[0],
            "last_value": values[-1],
            "percent_change": ((values[-1] - values[0]) / values[0] * 100.0) if values[0] != 0 else 0.0,
        }

    return trends


def detect_change_points(samples: list[float], threshold_std: float = 2.0) -> list[dict]:
    """
    Detect change points in a time series using CUSUM-like approach.

    Args:
        samples: Time series data
        threshold_std: Number of standard deviations for change detection

    Returns:
        List of change points with index and description
    """
    if len(samples) < 10:
        return []

    mean = statistics.fmean(samples)
    stddev = statistics.stdev(samples) if len(samples) > 1 else 0.0

    if stddev == 0:
        return []

    change_points = []
    cusum_pos = 0.0
    cusum_neg = 0.0
    threshold = threshold_std * stddev

    for i, val in enumerate(samples):
        normalized = val - mean
        cusum_pos = max(0, cusum_pos + normalized - 0.5 * stddev)
        cusum_neg = min(0, cusum_neg + normalized + 0.5 * stddev)

        if cusum_pos > threshold:
            change_points.append({
                "index": i,
                "value": val,
                "type": "positive_shift",
                "description": f"Performance degradation at sample {i}",
            })
            cusum_pos = 0.0
        elif abs(cusum_neg) > threshold:
            change_points.append({
                "index": i,
                "value": val,
                "type": "negative_shift",
                "description": f"Performance improvement at sample {i}",
            })
            cusum_neg = 0.0

    return change_points


def save_baseline(result: BenchmarkResult, path: str | Path, timestamp: str = "") -> None:
    """Save a benchmark result as a baseline."""
    from datetime import datetime
    if not timestamp:
        timestamp = datetime.now().isoformat()
    baseline = Baseline.from_result(result, timestamp)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(baseline.to_dict(), f, indent=2)


def load_baseline(path: str | Path) -> Baseline | None:
    """Load a baseline from file."""
    try:
        with open(path) as f:
            data = json.load(f)
        return Baseline(
            benchmark_name=data["benchmark_name"],
            version=data["version"],
            timestamp=data["timestamp"],
            latency=data["latency"],
            throughput_ops_s=data["throughput_ops_s"],
            score=data["score"],
            metadata=data.get("metadata", {}),
        )
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None
