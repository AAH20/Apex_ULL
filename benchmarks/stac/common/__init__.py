"""
STAC Benchmark Suite - Common utilities.

Provides shared timing, statistics, scoring, regression detection,
and comparative analysis for all STAC benchmarks.
"""

from common.harness import (
    now_ns,
    timed_ns,
    LatencyStats,
    compute_latency_stats,
    compute_histogram,
    BenchmarkResult,
    run_benchmark,
    ScoreBreakdown,
    classify_grade,
    compute_score_breakdown,
    score_lower_is_better,
    score_higher_is_better,
    score_composite,
    get_environment_info,
)
from common.metrics import (
    MetricDef,
    MetricRegistry,
    StatisticalSummary,
    STANDARD_LATENCY_METRICS,
    STATISTICAL_METRICS,
    STANDARD_THROUGHPUT_METRICS,
    QOS_METRICS,
    create_default_registry,
    create_full_registry,
)
from common.regression import (
    Baseline,
    PerformanceDelta,
    RegressionReport,
    compare_to_baseline,
    detect_trend,
    detect_change_points,
    save_baseline,
    load_baseline,
)
from common.comparative import (
    ComparativeMetric,
    BenchmarkRanking,
    ComparativeReport,
    compare_benchmarks,
    generate_comparison_table,
)

__all__ = [
    # Harness
    "now_ns",
    "timed_ns",
    "LatencyStats",
    "compute_latency_stats",
    "compute_histogram",
    "BenchmarkResult",
    "run_benchmark",
    "ScoreBreakdown",
    "classify_grade",
    "compute_score_breakdown",
    "score_lower_is_better",
    "score_higher_is_better",
    "score_composite",
    "get_environment_info",
    # Metrics
    "MetricDef",
    "MetricRegistry",
    "StatisticalSummary",
    "STANDARD_LATENCY_METRICS",
    "STATISTICAL_METRICS",
    "STANDARD_THROUGHPUT_METRICS",
    "QOS_METRICS",
    "create_default_registry",
    "create_full_registry",
    # Regression
    "Baseline",
    "PerformanceDelta",
    "RegressionReport",
    "compare_to_baseline",
    "detect_trend",
    "detect_change_points",
    "save_baseline",
    "load_baseline",
    # Comparative
    "ComparativeMetric",
    "BenchmarkRanking",
    "ComparativeReport",
    "compare_benchmarks",
    "generate_comparison_table",
]
