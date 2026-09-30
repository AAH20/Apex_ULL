"""
STAC Benchmark Metrics - Metric definitions and aggregation.

Each benchmark reports a standard set of metrics plus benchmark-specific ones.
All latency metrics are in nanoseconds unless otherwise noted.

Enhanced with:
- Statistical summary metrics
- Sub-stage timing metrics
- Quality-of-service metrics
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class MetricDef:
    """Definition of a single metric."""
    name: str
    unit: str
    description: str
    direction: str  # "lower_is_better" or "higher_is_better"
    reference_value: float | None = None  # Reference for scoring


# Standard latency metrics reported by every benchmark
STANDARD_LATENCY_METRICS: list[MetricDef] = [
    MetricDef("min_ns", "ns", "Minimum observed latency", "lower_is_better"),
    MetricDef("max_ns", "ns", "Maximum observed latency", "lower_is_better"),
    MetricDef("mean_ns", "ns", "Mean latency", "lower_is_better"),
    MetricDef("stddev_ns", "ns", "Standard deviation of latency", "lower_is_better"),
    MetricDef("p50_ns", "ns", "Median latency (50th percentile)", "lower_is_better"),
    MetricDef("p90_ns", "ns", "90th percentile latency", "lower_is_better"),
    MetricDef("p99_ns", "ns", "99th percentile latency", "lower_is_better"),
    MetricDef("p999_ns", "ns", "99.9th percentile latency", "lower_is_better"),
    MetricDef("p9999_ns", "ns", "99.99th percentile latency", "lower_is_better"),
    MetricDef("jitter_ns", "ns", "Mean absolute deviation between consecutive samples", "lower_is_better"),
]

# Enhanced statistical metrics
STATISTICAL_METRICS: list[MetricDef] = [
    MetricDef("cv", "ratio", "Coefficient of variation (stddev/mean)", "lower_is_better", 0.5),
    MetricDef("skewness", "ratio", "Skewness of latency distribution", "lower_is_better", 0.0),
    MetricDef("kurtosis", "ratio", "Excess kurtosis of latency distribution", "lower_is_better", 0.0),
    MetricDef("ci95_low", "ns", "95% confidence interval lower bound", "lower_is_better"),
    MetricDef("ci95_high", "ns", "95% confidence interval upper bound", "lower_is_better"),
    MetricDef("ci99_low", "ns", "99% confidence interval lower bound", "lower_is_better"),
    MetricDef("ci99_high", "ns", "99% confidence interval upper bound", "lower_is_better"),
    MetricDef("outlier_count", "count", "Number of outliers detected (IQR method)", "lower_is_better"),
    MetricDef("outlier_pct", "percent", "Percentage of outliers", "lower_is_better", 1.0),
]

# Standard throughput metric
STANDARD_THROUGHPUT_METRICS: list[MetricDef] = [
    MetricDef("throughput_ops_s", "ops/s", "Operations per second", "higher_is_better"),
    MetricDef("iterations", "count", "Total number of iterations", "higher_is_better"),
    MetricDef("duration_s", "s", "Total benchmark duration", "lower_is_better"),
]

# Quality-of-service metrics
QOS_METRICS: list[MetricDef] = [
    MetricDef("availability", "percent", "Percentage of successful operations", "higher_is_better", 99.99),
    MetricDef("error_rate", "percent", "Percentage of failed operations", "lower_is_better", 0.01),
    MetricDef("saturation", "percent", "Resource saturation level", "lower_is_better", 80.0),
]


@dataclass
class StatisticalSummary:
    """Statistical summary of a benchmark run."""
    sample_count: int = 0
    mean_ns: float = 0.0
    median_ns: float = 0.0
    stddev_ns: float = 0.0
    cv: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    ci95_low: float = 0.0
    ci95_high: float = 0.0
    ci99_low: float = 0.0
    ci99_high: float = 0.0
    outlier_count: int = 0
    outlier_pct: float = 0.0
    histogram_bins: int = 20

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetricRegistry:
    """Registry of all metrics for a benchmark suite."""
    metrics: dict[str, MetricDef] = field(default_factory=dict)

    def register(self, metric: MetricDef) -> None:
        self.metrics[metric.name] = metric

    def register_standard(self) -> None:
        """Register all standard latency and throughput metrics."""
        for m in STANDARD_LATENCY_METRICS + STANDARD_THROUGHPUT_METRICS:
            self.register(m)

    def register_statistical(self) -> None:
        """Register statistical analysis metrics."""
        for m in STATISTICAL_METRICS:
            self.register(m)

    def register_qos(self) -> None:
        """Register quality-of-service metrics."""
        for m in QOS_METRICS:
            self.register(m)

    def register_all(self) -> None:
        """Register all metric categories."""
        self.register_standard()
        self.register_statistical()
        self.register_qos()

    def get(self, name: str) -> MetricDef | None:
        return self.metrics.get(name)

    def to_dict(self) -> dict:
        return {k: asdict(v) for k, v in self.metrics.items()}


def create_default_registry() -> MetricRegistry:
    """Create a registry with all standard metrics pre-registered."""
    reg = MetricRegistry()
    reg.register_standard()
    return reg


def create_full_registry() -> MetricRegistry:
    """Create a registry with all metrics (standard + statistical + QoS)."""
    reg = MetricRegistry()
    reg.register_all()
    return reg
