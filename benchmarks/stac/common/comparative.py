"""
STAC Benchmark Comparative Analysis - Cross-benchmark comparison and ranking.

Provides tools to:
- Compare performance across all benchmarks
- Compute relative performance ratios
- Rank benchmarks by various criteria
- Generate efficiency frontier analysis
- Produce radar chart data for visualization
- Identify bottlenecks and optimization opportunities
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field, asdict
from typing import Any

from common.harness import BenchmarkResult, ScoreBreakdown


@dataclass
class ComparativeMetric:
    """A single comparative metric across benchmarks."""
    name: str
    unit: str
    values: dict[str, float] = field(default_factory=dict)  # benchmark_name -> value
    best_benchmark: str = ""
    worst_benchmark: str = ""
    best_value: float = 0.0
    worst_value: float = 0.0
    mean_value: float = 0.0
    stddev_value: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkRanking:
    """Ranking information for a single benchmark."""
    benchmark_name: str
    overall_rank: int = 0
    latency_rank: int = 0
    throughput_rank: int = 0
    score_rank: int = 0
    efficiency_rank: int = 0  # score per unit of throughput
    composite_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ComparativeReport:
    """Complete comparative analysis report."""
    benchmarks: list[str] = field(default_factory=list)
    metrics: list[ComparativeMetric] = field(default_factory=list)
    rankings: list[BenchmarkRanking] = field(default_factory=list)
    relative_performance: dict[str, dict[str, float]] = field(default_factory=dict)
    efficiency_frontier: list[str] = field(default_factory=list)
    radar_chart_data: dict = field(default_factory=dict)
    bottleneck_analysis: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "benchmarks": self.benchmarks,
            "metrics": [m.to_dict() for m in self.metrics],
            "rankings": [r.to_dict() for r in self.rankings],
            "relative_performance": self.relative_performance,
            "efficiency_frontier": self.efficiency_frontier,
            "radar_chart_data": self.radar_chart_data,
            "bottleneck_analysis": self.bottleneck_analysis,
            "recommendations": self.recommendations,
        }


def compare_benchmarks(results: dict[str, BenchmarkResult]) -> ComparativeReport:
    """
    Generate a comprehensive comparative analysis across all benchmarks.

    Args:
        results: Dictionary mapping benchmark names to their results

    Returns:
        ComparativeReport with full analysis
    """
    if not results:
        return ComparativeReport()

    benchmark_names = list(results.keys())
    report = ComparativeReport(benchmarks=benchmark_names)

    # Build comparative metrics
    metric_definitions = [
        ("p50_ns", "ns", "Median Latency", True),
        ("p90_ns", "ns", "90th Percentile Latency", True),
        ("p99_ns", "ns", "99th Percentile Latency", True),
        ("mean_ns", "ns", "Mean Latency", True),
        ("stddev_ns", "ns", "Standard Deviation", True),
        ("jitter_ns", "ns", "Jitter", True),
        ("throughput_ops_s", "ops/s", "Throughput", False),
        ("score", "score", "Composite Score", False),
    ]

    for metric_name, unit, description, lower_is_better in metric_definitions:
        values = {}
        for name, result in results.items():
            if metric_name in ("throughput_ops_s", "score"):
                values[name] = getattr(result, metric_name, 0)
            else:
                values[name] = getattr(result.latency, metric_name, 0)

        if not values:
            continue

        sorted_items = sorted(values.items(), key=lambda x: x[1])
        if lower_is_better:
            best_name, best_val = sorted_items[0]
            worst_name, worst_val = sorted_items[-1]
        else:
            best_name, best_val = sorted_items[-1]
            worst_name, worst_val = sorted_items[0]

        report.metrics.append(ComparativeMetric(
            name=metric_name,
            unit=unit,
            values=values,
            best_benchmark=best_name,
            worst_benchmark=worst_name,
            best_value=best_val,
            worst_value=worst_val,
            mean_value=statistics.fmean(values.values()),
            stddev_value=statistics.stdev(values.values()) if len(values) > 1 else 0.0,
        ))

    # Compute rankings
    report.rankings = _compute_rankings(results)

    # Compute relative performance
    report.relative_performance = _compute_relative_performance(results)

    # Compute efficiency frontier
    report.efficiency_frontier = _compute_efficiency_frontier(results)

    # Generate radar chart data
    report.radar_chart_data = _generate_radar_data(results)

    # Bottleneck analysis
    report.bottleneck_analysis = _analyze_bottlenecks(results)

    # Recommendations
    report.recommendations = _generate_recommendations(results, report)

    return report


def _compute_rankings(results: dict[str, BenchmarkResult]) -> list[BenchmarkRanking]:
    """Compute rankings for each benchmark across multiple dimensions."""
    rankings = []

    # Sort by each metric
    by_latency = sorted(results.items(), key=lambda x: x[1].latency.p50_ns)
    by_throughput = sorted(results.items(), key=lambda x: x[1].throughput_ops_s, reverse=True)
    by_score = sorted(results.items(), key=lambda x: x[1].score, reverse=True)

    # Efficiency: score per unit throughput (higher is better)
    by_efficiency = sorted(
        results.items(),
        key=lambda x: x[1].score / x[1].throughput_ops_s if x[1].throughput_ops_s > 0 else 0,
        reverse=True,
    )

    latency_ranks = {name: i + 1 for i, (name, _) in enumerate(by_latency)}
    throughput_ranks = {name: i + 1 for i, (name, _) in enumerate(by_throughput)}
    score_ranks = {name: i + 1 for i, (name, _) in enumerate(by_score)}
    efficiency_ranks = {name: i + 1 for i, (name, _) in enumerate(by_efficiency)}

    # Overall rank: average of all ranks
    overall_ranks = {}
    for name in results:
        avg_rank = (latency_ranks[name] + throughput_ranks[name] + score_ranks[name] + efficiency_ranks[name]) / 4.0
        overall_ranks[name] = avg_rank

    sorted_overall = sorted(overall_ranks.items(), key=lambda x: x[1])
    overall_rank_map = {name: i + 1 for i, (name, _) in enumerate(sorted_overall)}

    for name, result in results.items():
        rankings.append(BenchmarkRanking(
            benchmark_name=name,
            overall_rank=overall_rank_map[name],
            latency_rank=latency_ranks[name],
            throughput_rank=throughput_ranks[name],
            score_rank=score_ranks[name],
            efficiency_rank=efficiency_ranks[name],
            composite_score=result.score,
        ))

    return sorted(rankings, key=lambda r: r.overall_rank)


def _compute_relative_performance(results: dict[str, BenchmarkResult]) -> dict[str, dict[str, float]]:
    """Compute relative performance ratios between all benchmark pairs."""
    relative = {}
    names = list(results.keys())

    for name in names:
        relative[name] = {}
        for other_name in names:
            if name == other_name:
                relative[name][other_name] = 1.0
            else:
                # Ratio of p50 latencies (how many times faster/slower)
                p50_self = results[name].latency.p50_ns
                p50_other = results[other_name].latency.p50_ns
                if p50_other > 0:
                    relative[name][other_name] = p50_self / p50_other
                else:
                    relative[name][other_name] = 1.0

    return relative


def _compute_efficiency_frontier(results: dict[str, BenchmarkResult]) -> list[str]:
    """
    Compute the efficiency frontier: benchmarks that are not dominated
    in both latency and throughput.

    A benchmark A dominates B if A has both lower latency and higher throughput.
    """
    names = list(results.keys())
    frontier = []

    for name in names:
        dominated = False
        for other_name in names:
            if name == other_name:
                continue
            other = results[other_name]
            current = results[name]
            # Other dominates current if it has lower latency AND higher throughput
            if (other.latency.p50_ns <= current.latency.p50_ns and
                other.throughput_ops_s >= current.throughput_ops_s and
                (other.latency.p50_ns < current.latency.p50_ns or
                 other.throughput_ops_s > current.throughput_ops_s)):
                dominated = True
                break
        if not dominated:
            frontier.append(name)

    return sorted(frontier)


def _generate_radar_data(results: dict[str, BenchmarkResult]) -> dict:
    """Generate data for radar/spider chart visualization."""
    # Normalize all metrics to 0-1 scale for radar chart
    names = list(results.keys())
    if not names:
        return {}

    # Collect all values for normalization
    p50_values = [r.latency.p50_ns for r in results.values()]
    p99_values = [r.latency.p99_ns for r in results.values()]
    throughput_values = [r.throughput_ops_s for r in results.values()]
    jitter_values = [r.latency.jitter_ns for r in results.values()]
    score_values = [r.score for r in results.values()]

    def normalize(values: list[float], lower_is_better: bool = True) -> list[float]:
        if not values:
            return []
        min_val = min(values)
        max_val = max(values)
        if min_val == max_val:
            return [0.5] * len(values)
        if lower_is_better:
            return [(max_val - v) / (max_val - min_val) for v in values]
        else:
            return [(v - min_val) / (max_val - min_val) for v in values]

    normalized = {
        "latency": normalize(p50_values, lower_is_better=True),
        "tail_latency": normalize(p99_values, lower_is_better=True),
        "throughput": normalize(throughput_values, lower_is_better=False),
        "jitter": normalize(jitter_values, lower_is_better=True),
        "score": normalize(score_values, lower_is_better=False),
    }

    return {
        "dimensions": list(normalized.keys()),
        "benchmarks": names,
        "normalized_values": {
            name: {dim: normalized[dim][i] for dim in normalized}
            for i, name in enumerate(names)
        },
        "raw_values": {
            name: {
                "latency": results[name].latency.p50_ns,
                "tail_latency": results[name].latency.p99_ns,
                "throughput": results[name].throughput_ops_s,
                "jitter": results[name].latency.jitter_ns,
                "score": results[name].score,
            }
            for name in names
        },
    }


def _analyze_bottlenecks(results: dict[str, BenchmarkResult]) -> dict:
    """Identify performance bottlenecks across the benchmark suite."""
    if not results:
        return {}

    # Find worst performers
    by_latency = sorted(results.items(), key=lambda x: x[1].latency.p50_ns, reverse=True)
    by_throughput = sorted(results.items(), key=lambda x: x[1].throughput_ops_s)
    by_score = sorted(results.items(), key=lambda x: x[1].score)

    # Find benchmarks with high tail latency ratio (p99/p50)
    tail_ratios = {}
    for name, result in results.items():
        if result.latency.p50_ns > 0:
            tail_ratios[name] = result.latency.p99_ns / result.latency.p50_ns
    high_tail = sorted(tail_ratios.items(), key=lambda x: x[1], reverse=True)

    # Find benchmarks with high variability (CV)
    cv_values = {}
    for name, result in results.items():
        cv_values[name] = result.latency.cv
    high_cv = sorted(cv_values.items(), key=lambda x: x[1], reverse=True)

    return {
        "highest_latency": {
            "benchmark": by_latency[0][0],
            "p50_ns": by_latency[0][1].latency.p50_ns,
        },
        "lowest_throughput": {
            "benchmark": by_throughput[0][0],
            "throughput_ops_s": by_throughput[0][1].throughput_ops_s,
        },
        "lowest_score": {
            "benchmark": by_score[0][0],
            "score": by_score[0][1].score,
        },
        "highest_tail_ratio": {
            "benchmark": high_tail[0][0] if high_tail else "",
            "ratio": high_tail[0][1] if high_tail else 0,
        },
        "highest_variability": {
            "benchmark": high_cv[0][0] if high_cv else "",
            "cv": high_cv[0][1] if high_cv else 0,
        },
    }


def _generate_recommendations(results: dict[str, BenchmarkResult], report: ComparativeReport) -> list[str]:
    """Generate optimization recommendations based on comparative analysis."""
    recommendations = []

    # Find benchmarks with low scores
    low_score = [name for name, r in results.items() if r.score < 0.5]
    if low_score:
        recommendations.append(
            f"Focus optimization on: {', '.join(low_score)} (score < 0.5)"
        )

    # Find benchmarks with high tail latency
    high_tail = [name for name, r in results.items()
                 if r.latency.p50_ns > 0 and r.latency.p99_ns / r.latency.p50_ns > 10]
    if high_tail:
        recommendations.append(
            f"High tail latency in: {', '.join(high_tail)} (p99/p50 > 10x)"
        )

    # Find benchmarks with high variability
    high_cv = [name for name, r in results.items() if r.latency.cv > 1.0]
    if high_cv:
        recommendations.append(
            f"High variability in: {', '.join(high_cv)} (CV > 1.0)"
        )

    # Find benchmarks with high outlier percentage
    high_outliers = [name for name, r in results.items() if r.latency.outlier_pct > 5.0]
    if high_outliers:
        recommendations.append(
            f"High outlier rate in: {', '.join(high_outliers)} (> 5%)"
        )

    # Efficiency frontier recommendations
    if report.efficiency_frontier:
        recommendations.append(
            f"Efficiency frontier (Pareto optimal): {', '.join(report.efficiency_frontier)}"
        )

    # Throughput vs latency trade-off
    for name, result in results.items():
        if result.throughput_ops_s < 10000 and result.latency.p50_ns > 10000:
            recommendations.append(
                f"{name}: Low throughput with high latency - consider algorithmic optimization"
            )

    return recommendations


def generate_comparison_table(results: dict[str, BenchmarkResult]) -> str:
    """Generate a formatted comparison table."""
    if not results:
        return "No results to compare"

    lines = []
    lines.append("=" * 120)
    lines.append("COMPARATIVE ANALYSIS")
    lines.append("=" * 120)
    lines.append(f"{'Benchmark':<12} {'p50 (ns)':>12} {'p99 (ns)':>12} {'Throughput':>14} "
                 f"{'Jitter':>10} {'CV':>8} {'Score':>10} {'Grade':>6}")
    lines.append("-" * 120)

    for name in sorted(results.keys()):
        r = results[name]
        grade = r.score_breakdown.grade if r.score_breakdown else "N/A"
        lines.append(
            f"{name:<12} {r.latency.p50_ns:>12,} {r.latency.p99_ns:>12,} "
            f"{r.throughput_ops_s:>14,.0f} {r.latency.jitter_ns:>10.1f} "
            f"{r.latency.cv:>8.3f} {r.score:>10.4f} {grade:>6}"
        )

    lines.append("=" * 120)

    # Rankings
    report = compare_benchmarks(results)
    lines.append("")
    lines.append("RANKINGS")
    lines.append("-" * 60)
    lines.append(f"{'Benchmark':<12} {'Overall':>8} {'Latency':>8} {'Throughput':>10} {'Score':>8}")
    lines.append("-" * 60)
    for r in report.rankings:
        lines.append(
            f"{r.benchmark_name:<12} {r.overall_rank:>8} {r.latency_rank:>8} "
            f"{r.throughput_rank:>10} {r.score_rank:>8}"
        )
    lines.append("=" * 60)

    return "\n".join(lines)
