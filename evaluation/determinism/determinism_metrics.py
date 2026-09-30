#!/usr/bin/env python3
"""
ULL Determinism Evaluation Framework — Metrics Implementation

Computes four determinism metrics from latency samples:
  1. Coefficient of Variation (CV)
  2. p99/p50 Ratio
  3. Max Latency
  4. Jitter Standard Deviation

Plus a composite determinism score.

Usage:
    python determinism_metrics.py --input latency_samples.txt --output report.json
    python determinism_metrics.py --demo
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MetricResult:
    """Result for a single metric."""
    name: str
    value: float
    unit: str
    grade: str
    interpretation: str


@dataclass
class DeterminismReport:
    """Full determinism evaluation report."""
    sample_count: int
    mean_latency_ns: float
    median_latency_ns: float
    cv: MetricResult
    p99_p50_ratio: MetricResult
    max_latency: MetricResult
    jitter_std_dev: MetricResult
    composite_score: float
    composite_grade: str
    top_10_max: List[float] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Metric 1: Coefficient of Variation
# ---------------------------------------------------------------------------

def compute_cv(samples: List[float]) -> MetricResult:
    """
    Compute Coefficient of Variation: CV = σ / μ

    Args:
        samples: List of latency values in nanoseconds.

    Returns:
        MetricResult with CV as a ratio (not percentage).
    """
    n = len(samples)
    if n < 2:
        raise ValueError("Need at least 2 samples to compute CV")

    mean = sum(samples) / n
    if mean == 0:
        raise ValueError("Mean latency is zero; CV undefined")

    variance = sum((x - mean) ** 2 for x in samples) / n
    std_dev = math.sqrt(variance)
    cv = std_dev / mean

    # Grade
    if cv < 0.01:
        grade = "Excellent"
        interp = "FPGA-grade determinism; hardware-level consistency"
    elif cv < 0.05:
        grade = "Very Good"
        interp = "Kernel-bypass with proper tuning (DPDK, RDMA)"
    elif cv < 0.10:
        grade = "Good"
        interp = "Well-tuned software stack, isolated cores"
    elif cv < 0.20:
        grade = "Acceptable"
        interp = "Standard kernel bypass without full isolation"
    elif cv < 0.50:
        grade = "Poor"
        interp = "Standard OS networking, shared infrastructure"
    else:
        grade = "Unacceptable"
        interp = "Unsuitable for ULL; investigate immediately"

    return MetricResult(
        name="Coefficient of Variation",
        value=cv,
        unit="ratio",
        grade=grade,
        interpretation=interp,
    )


# ---------------------------------------------------------------------------
# Metric 2: p99/p50 Ratio
# ---------------------------------------------------------------------------

def compute_percentile(sorted_samples: List[float], p: float) -> float:
    """
    Compute the p-th percentile using linear interpolation.

    Args:
        sorted_samples: Pre-sorted list of values.
        p: Percentile in [0, 100].

    Returns:
        The p-th percentile value.
    """
    n = len(sorted_samples)
    if n == 0:
        raise ValueError("Empty sample list")
    if n == 1:
        return sorted_samples[0]

    # Linear interpolation method
    k = (p / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_samples[int(k)]
    d0 = sorted_samples[int(f)] * (c - k)
    d1 = sorted_samples[int(c)] * (k - f)
    return d0 + d1


def compute_p99_p50_ratio(samples: List[float]) -> MetricResult:
    """
    Compute p99/p50 ratio.

    Args:
        samples: List of latency values in nanoseconds.

    Returns:
        MetricResult with the p99/p50 ratio.
    """
    if len(samples) < 100:
        raise ValueError("Need at least 100 samples for stable p99")

    sorted_samples = sorted(samples)
    p50 = compute_percentile(sorted_samples, 50)
    p99 = compute_percentile(sorted_samples, 99)

    if p50 == 0:
        raise ValueError("p50 is zero; ratio undefined")

    ratio = p99 / p50

    # Grade
    if ratio < 1.5:
        grade = "Excellent"
        interp = "Near-perfect determinism; tail ≈ median"
    elif ratio < 3.0:
        grade = "Very Good"
        interp = "Mild tail inflation; typical of tuned ULL systems"
    elif ratio < 5.0:
        grade = "Good"
        interp = "Moderate tail; acceptable for most ULL applications"
    elif ratio < 10.0:
        grade = "Acceptable"
        interp = "Significant tail; may violate tight SLAs"
    elif ratio < 50.0:
        grade = "Poor"
        interp = "Severe tail latency; requires optimization"
    else:
        grade = "Unacceptable"
        interp = "Catastrophic tail behavior; unsuitable for ULL"

    return MetricResult(
        name="p99/p50 Ratio",
        value=ratio,
        unit="ratio",
        grade=grade,
        interpretation=interp,
    )


# ---------------------------------------------------------------------------
# Metric 3: Max Latency
# ---------------------------------------------------------------------------

def compute_max_latency(samples: List[float]) -> MetricResult:
    """
    Compute max latency and its ratio to median.

    Args:
        samples: List of latency values in nanoseconds.

    Returns:
        MetricResult with max latency in nanoseconds.
    """
    if not samples:
        raise ValueError("Empty sample list")

    sorted_samples = sorted(samples)
    max_val = sorted_samples[-1]
    median = compute_percentile(sorted_samples, 50)

    if median == 0:
        raise ValueError("Median is zero; ratio undefined")

    ratio = max_val / median

    # Grade
    if ratio < 2.0:
        grade = "Excellent"
        interp = "No significant outliers"
    elif ratio < 5.0:
        grade = "Very Good"
        interp = "Minor outliers, well-controlled"
    elif ratio < 10.0:
        grade = "Good"
        interp = "Some outliers; acceptable for most ULL"
    elif ratio < 50.0:
        grade = "Acceptable"
        interp = "Noticeable outliers; investigate causes"
    elif ratio < 100.0:
        grade = "Poor"
        interp = "Severe outliers; likely systematic issue"
    else:
        grade = "Unacceptable"
        interp = "Catastrophic; system unsuitable for ULL"

    return MetricResult(
        name="Max Latency",
        value=max_val,
        unit="ns",
        grade=grade,
        interpretation=interp,
    )


# ---------------------------------------------------------------------------
# Metric 4: Jitter Standard Deviation
# ---------------------------------------------------------------------------

def compute_jitter_std_dev(samples: List[float]) -> MetricResult:
    """
    Compute jitter standard deviation (std dev of first differences).

    Jitter_i = x_i - x_{i-1}
    Jitter Std Dev = sqrt( (1/(N-1)) * sum( (Jitter_i - mean_jitter)^2 ) )

    Args:
        samples: List of latency values in chronological order.

    Returns:
        MetricResult with jitter std dev in nanoseconds.
    """
    n = len(samples)
    if n < 3:
        raise ValueError("Need at least 3 samples to compute jitter std dev")

    # First differences
    jitters = [samples[i] - samples[i - 1] for i in range(1, n)]
    m = len(jitters)

    mean_jitter = sum(jitters) / m
    variance = sum((j - mean_jitter) ** 2 for j in jitters) / (m - 1)
    jitter_std = math.sqrt(variance)

    # Grade (absolute thresholds in nanoseconds)
    if jitter_std < 10:
        grade = "Excellent"
        interp = "FPGA-grade; hardware-level consistency"
    elif jitter_std < 100:
        grade = "Very Good"
        interp = "Kernel bypass with proper tuning"
    elif jitter_std < 1000:
        grade = "Good"
        interp = "Well-tuned software stack"
    elif jitter_std < 10000:
        grade = "Acceptable"
        interp = "Standard kernel bypass"
    elif jitter_std < 100000:
        grade = "Poor"
        interp = "Standard OS networking"
    else:
        grade = "Unacceptable"
        interp = "Unsuitable for ULL"

    return MetricResult(
        name="Jitter Std Dev",
        value=jitter_std,
        unit="ns",
        grade=grade,
        interpretation=interp,
    )


# ---------------------------------------------------------------------------
# Composite Score
# ---------------------------------------------------------------------------

def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to [0, 1] using min-max scaling."""
    if max_val == min_val:
        return 1.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def compute_composite_score(
    cv: float,
    p99_p50: float,
    max_ratio: float,
    jitter_std_ns: float,
) -> Tuple[float, str]:
    """
    Compute composite determinism score.

    Each metric is normalized to [0, 1] where 1 = best, then combined
    with weights. Final score is in [0, 1] where 1 = perfect determinism.

    Args:
        cv: Coefficient of variation (ratio).
        p99_p50: p99/p50 ratio.
        max_ratio: max latency / median ratio.
        jitter_std_ns: Jitter standard deviation in nanoseconds.

    Returns:
        Tuple of (score, grade).
    """
    # Normalize each metric (lower = better, so we invert)
    # CV: ideal 0, unacceptable 0.5
    cv_norm = 1.0 - _normalize(cv, 0.0, 0.5)

    # p99/p50: ideal 1.0, unacceptable 50.0
    p99p50_norm = 1.0 - _normalize(p99_p50, 1.0, 50.0)

    # Max ratio: ideal 1.0, unacceptable 100.0
    max_norm = 1.0 - _normalize(max_ratio, 1.0, 100.0)

    # Jitter std dev: ideal 0 ns, unacceptable 100000 ns (100 µs)
    jitter_norm = 1.0 - _normalize(jitter_std_ns, 0.0, 100000.0)

    # Weights
    w_cv = 0.30
    w_p99 = 0.30
    w_max = 0.20
    w_jitter = 0.20

    score = (
        w_cv * cv_norm
        + w_p99 * p99p50_norm
        + w_max * max_norm
        + w_jitter * jitter_norm
    )

    # Grade
    if score >= 0.90:
        grade = "A (Excellent)"
    elif score >= 0.80:
        grade = "B (Very Good)"
    elif score >= 0.70:
        grade = "C (Good)"
    elif score >= 0.60:
        grade = "D (Acceptable)"
    else:
        grade = "F (Poor)"

    return score, grade


# ---------------------------------------------------------------------------
# Full evaluation
# ---------------------------------------------------------------------------

def evaluate_determinism(samples: List[float], metadata: Optional[dict] = None) -> DeterminismReport:
    """
    Run full determinism evaluation on latency samples.

    Args:
        samples: List of latency values in nanoseconds (chronological order).
        metadata: Optional dict of system/test metadata.

    Returns:
        DeterminismReport with all metrics and composite score.
    """
    if len(samples) < 100:
        raise ValueError(f"Need at least 100 samples, got {len(samples)}")

    sorted_samples = sorted(samples)
    n = len(samples)

    mean_lat = sum(samples) / n
    median_lat = compute_percentile(sorted_samples, 50)

    # Compute all metrics
    cv_result = compute_cv(samples)
    p99_p50_result = compute_p99_p50_ratio(samples)
    max_result = compute_max_latency(samples)
    jitter_result = compute_jitter_std_dev(samples)

    # Max ratio for composite
    max_ratio = max_result.value / median_lat if median_lat > 0 else float("inf")

    # Composite score
    score, grade = compute_composite_score(
        cv=cv_result.value,
        p99_p50=p99_p50_result.value,
        max_ratio=max_ratio,
        jitter_std_ns=jitter_result.value,
    )

    # Top 10 max values
    top_10 = sorted_samples[-10:][::-1]  # descending

    return DeterminismReport(
        sample_count=n,
        mean_latency_ns=mean_lat,
        median_latency_ns=median_lat,
        cv=cv_result,
        p99_p50_ratio=p99_p50_result,
        max_latency=max_result,
        jitter_std_dev=jitter_result,
        composite_score=score,
        composite_grade=grade,
        top_10_max=top_10,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_samples(filepath: str) -> List[float]:
    """
    Load latency samples from a text file.

    Format: one latency value per line (nanoseconds).
    Lines starting with '#' are ignored.
    """
    samples = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            samples.append(float(line))
    return samples


def report_to_dict(report: DeterminismReport) -> dict:
    """Convert report to a JSON-serializable dict."""
    return {
        "sample_count": report.sample_count,
        "mean_latency_ns": round(report.mean_latency_ns, 2),
        "median_latency_ns": round(report.median_latency_ns, 2),
        "metrics": {
            "cv": {
                "name": report.cv.name,
                "value": round(report.cv.value, 6),
                "unit": report.cv.unit,
                "grade": report.cv.grade,
                "interpretation": report.cv.interpretation,
            },
            "p99_p50_ratio": {
                "name": report.p99_p50_ratio.name,
                "value": round(report.p99_p50_ratio.value, 4),
                "unit": report.p99_p50_ratio.unit,
                "grade": report.p99_p50_ratio.grade,
                "interpretation": report.p99_p50_ratio.interpretation,
            },
            "max_latency": {
                "name": report.max_latency.name,
                "value": round(report.max_latency.value, 2),
                "unit": report.max_latency.unit,
                "grade": report.max_latency.grade,
                "interpretation": report.max_latency.interpretation,
            },
            "jitter_std_dev": {
                "name": report.jitter_std_dev.name,
                "value": round(report.jitter_std_dev.value, 2),
                "unit": report.jitter_std_dev.unit,
                "grade": report.jitter_std_dev.grade,
                "interpretation": report.jitter_std_dev.interpretation,
            },
        },
        "composite_score": round(report.composite_score, 4),
        "composite_grade": report.composite_grade,
        "top_10_max_ns": [round(x, 2) for x in report.top_10_max],
        "metadata": report.metadata,
    }


def print_report(report: DeterminismReport) -> None:
    """Print a human-readable report to stdout."""
    print("=" * 70)
    print("  ULL DETERMINISM EVALUATION REPORT")
    print("=" * 70)
    print(f"  Samples:     {report.sample_count:,}")
    print(f"  Mean:        {report.mean_latency_ns:,.2f} ns")
    print(f"  Median:      {report.median_latency_ns:,.2f} ns")
    print()

    for metric in [report.cv, report.p99_p50_ratio, report.max_latency, report.jitter_std_dev]:
        print(f"  {metric.name}")
        print(f"    Value:    {metric.value:,.6f} {metric.unit}")
        print(f"    Grade:    {metric.grade}")
        print(f"    Detail:   {metric.interpretation}")
        print()

    print(f"  Composite Score: {report.composite_score:.4f} — Grade: {report.composite_grade}")
    print()

    if report.top_10_max:
        print("  Top 10 Max Latencies (ns):")
        for i, val in enumerate(report.top_10_max, 1):
            print(f"    {i:2d}. {val:,.2f}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

def _generate_demo_samples() -> List[float]:
    """Generate synthetic latency samples simulating a kernel-bypass system."""
    import random
    random.seed(42)

    # Base latency ~7 µs (7000 ns) with Gaussian noise
    base = 7000.0
    noise_std = 300.0  # ~4.3% CV
    n = 100_000

    samples = []
    for _ in range(n):
        # Gaussian noise
        val = random.gauss(base, noise_std)
        # Occasional spikes (1% of samples, +5-15 µs)
        if random.random() < 0.01:
            val += random.uniform(5000, 15000)
        # Rare outliers (0.01% of samples, +50-200 µs)
        if random.random() < 0.0001:
            val += random.uniform(50000, 200000)
        samples.append(max(val, 100.0))  # clamp to positive

    return samples


def run_demo() -> None:
    """Run a demonstration with synthetic data."""
    print("Generating synthetic latency samples (kernel-bypass simulation)...")
    samples = _generate_demo_samples()
    print(f"Generated {len(samples):,} samples\n")

    report = evaluate_determinism(
        samples,
        metadata={
            "source": "synthetic",
            "description": "Kernel-bypass simulation: base 7µs, noise 300ns, 1% spikes, 0.01% outliers",
        },
    )
    print_report(report)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ULL Determinism Evaluation Framework",
    )
    parser.add_argument(
        "--input", "-i",
        help="Input file with latency samples (one value per line, nanoseconds)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file for JSON report",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with synthetic demo data",
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.input:
        parser.error("Either --input or --demo must be specified")

    # Load samples
    samples = load_samples(args.input)
    print(f"Loaded {len(samples):,} samples from {args.input}")

    # Evaluate
    report = evaluate_determinism(samples, metadata={"source_file": args.input})
    print_report(report)

    # Save JSON if requested
    if args.output:
        report_dict = report_to_dict(report)
        with open(args.output, "w") as f:
            json.dump(report_dict, f, indent=2)
        print(f"\nJSON report saved to {args.output}")


if __name__ == "__main__":
    main()
