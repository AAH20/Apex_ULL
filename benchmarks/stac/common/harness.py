"""
STAC Benchmark Harness - Shared timing, statistics, and scoring utilities.

All benchmarks use nanosecond-resolution timing via time.perf_counter_ns()
and report latency percentiles (p50, p90, p99, p99.9, p99.99) plus
throughput and jitter metrics.

Enhanced with:
- Multi-dimensional scoring model with component breakdown
- Statistical analysis (confidence intervals, CV, skewness, kurtosis)
- Outlier detection (IQR method)
- Histogram generation
- Grade classification (A+ through F)
"""

from __future__ import annotations

import json
import math
import os
import statistics
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Any


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

def now_ns() -> int:
    """High-resolution monotonic clock in nanoseconds."""
    return time.perf_counter_ns()


def timed_ns(fn: Callable[[], Any]) -> tuple[Any, int]:
    """Run fn(), return (result, elapsed_ns)."""
    t0 = now_ns()
    result = fn()
    t1 = now_ns()
    return result, t1 - t0


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@dataclass
class LatencyStats:
    """Latency distribution summary (all values in nanoseconds)."""
    count: int = 0
    min_ns: int = 0
    max_ns: int = 0
    mean_ns: float = 0.0
    stddev_ns: float = 0.0
    p50_ns: int = 0
    p90_ns: int = 0
    p99_ns: int = 0
    p999_ns: int = 0
    p9999_ns: int = 0
    jitter_ns: float = 0.0  # mean absolute deviation between consecutive samples
    # Enhanced statistical metrics
    cv: float = 0.0  # coefficient of variation (stddev / mean)
    skewness: float = 0.0  # asymmetry of distribution
    kurtosis: float = 0.0  # tail heaviness
    ci95_low: float = 0.0  # 95% confidence interval lower bound
    ci95_high: float = 0.0  # 95% confidence interval upper bound
    ci99_low: float = 0.0  # 99% confidence interval lower bound
    ci99_high: float = 0.0  # 99% confidence interval upper bound
    outlier_count: int = 0  # number of outliers detected (IQR method)
    outlier_pct: float = 0.0  # percentage of outliers

    def to_dict(self) -> dict:
        return asdict(self)


def compute_latency_stats(samples_ns: list[int]) -> LatencyStats:
    """Compute latency statistics from a list of nanosecond samples."""
    if not samples_ns:
        return LatencyStats()

    sorted_s = sorted(samples_ns)
    n = len(sorted_s)

    def percentile(p: float) -> int:
        idx = int(math.ceil(p / 100.0 * n)) - 1
        return sorted_s[max(0, min(idx, n - 1))]

    mean = statistics.fmean(sorted_s)
    stddev = statistics.stdev(sorted_s) if n > 1 else 0.0

    # Jitter: mean absolute difference between consecutive samples
    jitter = 0.0
    if n > 1:
        diffs = [abs(samples_ns[i] - samples_ns[i - 1]) for i in range(1, n)]
        jitter = statistics.fmean(diffs)

    # Coefficient of variation
    cv = stddev / mean if mean > 0 else 0.0

    # Skewness (Fisher-Pearson standardized moment)
    skewness = 0.0
    if n > 2 and stddev > 0:
        m3 = sum((x - mean) ** 3 for x in sorted_s) / n
        skewness = m3 / (stddev ** 3)

    # Kurtosis (excess kurtosis, Fisher definition)
    kurtosis = 0.0
    if n > 3 and stddev > 0:
        m4 = sum((x - mean) ** 4 for x in sorted_s) / n
        kurtosis = m4 / (stddev ** 4) - 3.0

    # Confidence intervals (using t-distribution approximation)
    # For large n, t-value ≈ 1.96 (95%) and 2.576 (99%)
    ci95_low, ci95_high = _confidence_interval(mean, stddev, n, 1.96)
    ci99_low, ci99_high = _confidence_interval(mean, stddev, n, 2.576)

    # Outlier detection using IQR method
    q1 = percentile(25)
    q3 = percentile(75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers = [x for x in sorted_s if x < lower_fence or x > upper_fence]
    outlier_count = len(outliers)
    outlier_pct = (outlier_count / n) * 100.0 if n > 0 else 0.0

    return LatencyStats(
        count=n,
        min_ns=sorted_s[0],
        max_ns=sorted_s[-1],
        mean_ns=mean,
        stddev_ns=stddev,
        p50_ns=percentile(50),
        p90_ns=percentile(90),
        p99_ns=percentile(99),
        p999_ns=percentile(99.9),
        p9999_ns=percentile(99.99),
        jitter_ns=jitter,
        cv=cv,
        skewness=skewness,
        kurtosis=kurtosis,
        ci95_low=ci95_low,
        ci95_high=ci95_high,
        ci99_low=ci99_low,
        ci99_high=ci99_high,
        outlier_count=outlier_count,
        outlier_pct=outlier_pct,
    )


def _confidence_interval(mean: float, stddev: float, n: int, z: float) -> tuple[float, float]:
    """Compute confidence interval for the mean."""
    if n <= 1 or stddev <= 0:
        return mean, mean
    margin = z * stddev / math.sqrt(n)
    return mean - margin, mean + margin


def compute_histogram(samples_ns: list[int], bins: int = 20) -> list[dict]:
    """Compute histogram data for visualization."""
    if not samples_ns:
        return []
    sorted_s = sorted(samples_ns)
    min_val = sorted_s[0]
    max_val = sorted_s[-1]
    if min_val == max_val:
        return [{"bin_start": min_val, "bin_end": max_val, "count": len(sorted_s)}]
    bin_width = (max_val - min_val) / bins
    histogram = []
    for i in range(bins):
        bin_start = min_val + i * bin_width
        bin_end = bin_start + bin_width
        count = sum(1 for x in sorted_s if bin_start <= x < bin_end)
        # Include max value in last bin
        if i == bins - 1:
            count = sum(1 for x in sorted_s if bin_start <= x <= bin_end)
        histogram.append({
            "bin_start": int(bin_start),
            "bin_end": int(bin_end),
            "count": count,
        })
    return histogram


# ---------------------------------------------------------------------------
# Scoring Model
# ---------------------------------------------------------------------------

@dataclass
class ScoreBreakdown:
    """Detailed breakdown of benchmark score components."""
    latency_score: float = 0.0
    throughput_score: float = 0.0
    jitter_score: float = 0.0
    tail_latency_score: float = 0.0
    consistency_score: float = 0.0
    composite_score: float = 0.0
    grade: str = "F"
    grade_label: str = "Failing"

    def to_dict(self) -> dict:
        return asdict(self)


def classify_grade(score: float) -> tuple[str, str]:
    """
    Classify a composite score into a letter grade.

    Grading scale:
        A+ : score >= 2.0  (exceptional, 2x+ better than reference)
        A  : score >= 1.5  (excellent, 1.5x+ better than reference)
        A- : score >= 1.2  (very good, 1.2x+ better than reference)
        B+ : score >= 1.0  (good, meets reference)
        B  : score >= 0.8  (acceptable, within 20% of reference)
        B- : score >= 0.6  (below average, within 40% of reference)
        C+ : score >= 0.4  (poor, within 60% of reference)
        C  : score >= 0.2  (very poor, within 80% of reference)
        D  : score >= 0.1  (bad, within 90% of reference)
        F  : score < 0.1   (failing)
    """
    if score >= 2.0:
        return "A+", "Exceptional"
    elif score >= 1.5:
        return "A", "Excellent"
    elif score >= 1.2:
        return "A-", "Very Good"
    elif score >= 1.0:
        return "B+", "Good"
    elif score >= 0.8:
        return "B", "Acceptable"
    elif score >= 0.6:
        return "B-", "Below Average"
    elif score >= 0.4:
        return "C+", "Poor"
    elif score >= 0.2:
        return "C", "Very Poor"
    elif score >= 0.1:
        return "D", "Bad"
    else:
        return "F", "Failing"


def compute_score_breakdown(
    stats: LatencyStats,
    iterations: int,
    duration_s: float,
    latency_weight: float = 0.5,
    throughput_weight: float = 0.2,
    jitter_weight: float = 0.1,
    tail_latency_weight: float = 0.1,
    consistency_weight: float = 0.1,
    reference_p50_ns: float = 1000.0,
    reference_throughput: float = 1_000_000.0,
    reference_jitter_ns: float = 100.0,
    reference_p99_ns: float = 5000.0,
    reference_cv: float = 0.5,
) -> ScoreBreakdown:
    """
    Compute detailed score breakdown with multiple dimensions.

    Components:
    - Latency score: reference_p50 / p50 (higher is better)
    - Throughput score: throughput / reference_throughput (higher is better)
    - Jitter score: reference_jitter / jitter (higher is better)
    - Tail latency score: reference_p99 / p99 (higher is better)
    - Consistency score: reference_cv / cv (higher is better, capped at 2.0)
    """
    # Latency score
    latency_score = reference_p50_ns / stats.p50_ns if stats.p50_ns > 0 else 0.0

    # Throughput score
    throughput = iterations / duration_s if duration_s > 0 else 0.0
    throughput_score = throughput / reference_throughput if reference_throughput > 0 else 0.0

    # Jitter score
    jitter_score = reference_jitter_ns / stats.jitter_ns if stats.jitter_ns > 0 else 0.0

    # Tail latency score
    tail_latency_score = reference_p99_ns / stats.p99_ns if stats.p99_ns > 0 else 0.0

    # Consistency score (CV-based, capped)
    consistency_score = min(reference_cv / stats.cv, 2.0) if stats.cv > 0 else 2.0

    # Composite score (weighted sum)
    composite = (
        latency_weight * latency_score +
        throughput_weight * throughput_score +
        jitter_weight * jitter_score +
        tail_latency_weight * tail_latency_score +
        consistency_weight * consistency_score
    )

    grade, grade_label = classify_grade(composite)

    return ScoreBreakdown(
        latency_score=latency_score,
        throughput_score=throughput_score,
        jitter_score=jitter_score,
        tail_latency_score=tail_latency_score,
        consistency_score=consistency_score,
        composite_score=composite,
        grade=grade,
        grade_label=grade_label,
    )


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    """Complete result of a benchmark run."""
    name: str
    version: str
    description: str
    duration_s: float
    iterations: int
    throughput_ops_s: float
    latency: LatencyStats
    score: float = 0.0
    score_breakdown: ScoreBreakdown | None = None
    metadata: dict = field(default_factory=dict)
    histogram: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["latency"] = self.latency.to_dict()
        if self.score_breakdown:
            d["score_breakdown"] = self.score_breakdown.to_dict()
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def run_benchmark(
    name: str,
    version: str,
    description: str,
    fn: Callable[[], Any],
    iterations: int = 100_000,
    warmup_iterations: int = 10_000,
    scoring_fn: Callable[[LatencyStats, int, float], float] | None = None,
    detailed_scoring_fn: Callable[[LatencyStats, int, float], ScoreBreakdown] | None = None,
    metadata: dict | None = None,
    compute_hist: bool = True,
    hist_bins: int = 20,
) -> BenchmarkResult:
    """
    Run a benchmark: warmup, then timed iterations, then compute stats and score.

    Args:
        name: Benchmark identifier (e.g. "STAC-M1")
        version: Benchmark version string
        description: Human-readable description
        fn: The operation to benchmark (called once per iteration)
        iterations: Number of timed iterations
        warmup_iterations: Number of warmup iterations (not timed)
        scoring_fn: Optional custom scoring function (stats, iterations, duration_s) -> score
        detailed_scoring_fn: Optional detailed scoring function returning ScoreBreakdown
        metadata: Extra key-value pairs to include in result
        compute_hist: Whether to compute histogram data
        hist_bins: Number of histogram bins

    Returns:
        BenchmarkResult with latency stats, throughput, and score
    """
    if iterations <= 0 or warmup_iterations < 0:
        raise ValueError("iterations must be positive and warmup nonnegative")
    # Warmup
    for _ in range(warmup_iterations):
        fn()

    # Timed run
    samples: list[int] = []
    t_start = now_ns()
    for _ in range(iterations):
        _, elapsed = timed_ns(fn)
        samples.append(elapsed)
    t_end = now_ns()

    duration_s = (t_end - t_start) / 1e9
    stats = compute_latency_stats(samples)
    throughput = iterations / duration_s if duration_s > 0 else 0.0

    # Compute histogram
    histogram = compute_histogram(samples, bins=hist_bins) if compute_hist else []

    # Scoring
    score = 0.0
    score_breakdown = None
    if detailed_scoring_fn:
        score_breakdown = detailed_scoring_fn(stats, iterations, duration_s)
        score = score_breakdown.composite_score
    elif scoring_fn:
        score = scoring_fn(stats, iterations, duration_s)

    return BenchmarkResult(
        name="APEX-SYNTHETIC-" + name.removeprefix("STAC-") if name.startswith("STAC-") else name,
        version=version,
        description=description,
        duration_s=duration_s,
        iterations=iterations,
        throughput_ops_s=throughput,
        latency=stats,
        score=score,
        score_breakdown=score_breakdown,
        metadata={**(metadata or {}), "benchmark_authority": "unofficial_synthetic", "official_stac_result": False},
        histogram=histogram,
    )


# ---------------------------------------------------------------------------
# Legacy scoring functions (kept for backward compatibility)
# ---------------------------------------------------------------------------

def score_lower_is_better(stats: LatencyStats, iterations: int, duration_s: float,
                          reference_ns: float) -> float:
    """
    Score where lower latency is better.
    score = reference_ns / p50_ns  (higher is better, 1.0 = meets reference)
    """
    if stats.p50_ns <= 0:
        return 0.0
    return reference_ns / stats.p50_ns


def score_higher_is_better(stats: LatencyStats, iterations: int, duration_s: float,
                           reference: float) -> float:
    """
    Score where higher throughput is better.
    score = throughput / reference  (higher is better, 1.0 = meets reference)
    """
    throughput = iterations / duration_s if duration_s > 0 else 0.0
    if reference <= 0:
        return 0.0
    return throughput / reference


def score_composite(stats: LatencyStats, iterations: int, duration_s: float,
                   latency_weight: float = 0.6,
                   throughput_weight: float = 0.3,
                   jitter_weight: float = 0.1,
                   reference_p50_ns: float = 1000.0,
                   reference_throughput: float = 1_000_000.0,
                   reference_jitter_ns: float = 100.0) -> float:
    """
    Composite score combining latency, throughput, and jitter.
    Each component is normalized to 1.0 = meets reference.
    """
    latency_score = reference_p50_ns / stats.p50_ns if stats.p50_ns > 0 else 0.0
    throughput = iterations / duration_s if duration_s > 0 else 0.0
    throughput_score = throughput / reference_throughput if reference_throughput > 0 else 0.0
    jitter_score = reference_jitter_ns / stats.jitter_ns if stats.jitter_ns > 0 else 0.0

    return (latency_weight * latency_score +
            throughput_weight * throughput_score +
            jitter_weight * jitter_score)


# ---------------------------------------------------------------------------
# Environment info
# ---------------------------------------------------------------------------

def get_environment_info() -> dict:
    """Collect system information for benchmark reproducibility."""
    info = {
        "python_version": os.sys.version,
        "platform": os.sys.platform,
        "cpu_count": os.cpu_count(),
    }
    # Try to get CPU info on Linux
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    info["cpu_model"] = line.split(":")[1].strip()
                    break
    except (FileNotFoundError, OSError):
        pass
    # Try to get CPU info on macOS
    try:
        import subprocess
        result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info["cpu_model"] = result.stdout.strip()
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass
    return info
