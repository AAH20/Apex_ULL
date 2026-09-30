#!/usr/bin/env python3
"""
ULL Latency Evaluation Framework — Statistical Analysis & ML Module
==================================================================

Deepens the ULL latency evaluation framework with:
  - Full percentile analysis (p50/p95/p99/p999/p9999) with confidence intervals
  - Distribution fitting and hypothesis testing
  - Throughput-latency relationship analysis
  - Jitter spectral analysis
  - Determinism scoring
  - Availability modeling
  - Cost/µs, cost/trade, ROI, TCO calculations
  - Regression and change-point detection
  - Comparative multi-system analysis
  - Machine learning: anomaly detection, clustering, prediction, PCA
  - Visualization: distributions, CDFs, time series, heatmaps

Usage:
    python ull_latency_ml.py --demo
    python ull_latency_ml.py --input samples.txt --output report.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import numpy as np
from scipy import stats
from scipy.optimize import curve_fit


# ===========================================================================
# Data Structures
# ===========================================================================

@dataclass
class PercentileResult:
    """Result for a single percentile."""
    percentile: float
    value_ns: float
    ci_lower_ns: float
    ci_upper_ns: float
    std_error_ns: float


@dataclass
class DistributionFit:
    """Result of fitting a distribution to latency data."""
    distribution: str
    params: Tuple[float, ...]
    ks_statistic: float
    ks_pvalue: float
    aic: float
    bic: float
    log_likelihood: float
    fitted: bool


@dataclass
class RegressionResult:
    """Result of regression/change-point detection."""
    method: str
    slope: float
    intercept: float
    r_squared: float
    p_value: float
    change_points: List[int] = field(default_factory=list)
    trend_direction: str = "stable"


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    method: str
    anomaly_indices: List[int]
    anomaly_scores: List[float]
    threshold: float
    anomaly_count: int
    anomaly_rate: float


@dataclass
class ComparisonResult:
    """Result of comparing two systems."""
    system_a: str
    system_b: str
    metric: str
    mean_a: float
    mean_b: float
    difference: float
    percent_difference: float
    t_statistic: float
    t_pvalue: float
    significant: bool
    effect_size: float
    winner: str


@dataclass
class MLModelResult:
    """Result of ML model training/prediction."""
    model_type: str
    train_score: float
    test_score: float
    predictions: List[float] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)


# ===========================================================================
# 1. Percentile Analysis with Confidence Intervals
# ===========================================================================

def compute_percentiles(
    samples: np.ndarray,
    percentiles: List[float] = None,
    confidence: float = 0.95,
    n_bootstrap: int = 10000,
) -> List[PercentileResult]:
    """
    Compute percentiles with bootstrap confidence intervals.

    Args:
        samples: Array of latency values in nanoseconds.
        percentiles: List of percentiles to compute (default: [50, 95, 99, 99.9, 99.99]).
        confidence: Confidence level for intervals.
        n_bootstrap: Number of bootstrap resamples.

    Returns:
        List of PercentileResult.
    """
    if percentiles is None:
        percentiles = [50, 95, 99, 99.9, 99.99]

    samples = np.asarray(samples, dtype=np.float64)
    n = len(samples)
    results = []

    alpha = 1 - confidence
    z = stats.norm.ppf(1 - alpha / 2)

    for p in percentiles:
        val = np.percentile(samples, p)

        # Bootstrap CI
        boot_vals = np.empty(n_bootstrap)
        for i in range(n_bootstrap):
            boot_sample = np.random.choice(samples, size=n, replace=True)
            boot_vals[i] = np.percentile(boot_sample, p)

        ci_lower = np.percentile(boot_vals, 100 * alpha / 2)
        ci_upper = np.percentile(boot_vals, 100 * (1 - alpha / 2))
        std_error = np.std(boot_vals, ddof=1)

        results.append(PercentileResult(
            percentile=p,
            value_ns=float(val),
            ci_lower_ns=float(ci_lower),
            ci_upper_ns=float(ci_upper),
            std_error_ns=float(std_error),
        ))

    return results


def compute_percentiles_fast(
    samples: np.ndarray,
    percentiles: List[float] = None,
) -> Dict[float, float]:
    """Fast percentile computation without CIs (for large datasets)."""
    if percentiles is None:
        percentiles = [50, 95, 99, 99.9, 99.99]
    samples = np.asarray(samples, dtype=np.float64)
    return {p: float(np.percentile(samples, p)) for p in percentiles}


# ===========================================================================
# 2. Descriptive Statistics
# ===========================================================================

def descriptive_statistics(samples: np.ndarray) -> Dict[str, float]:
    """Compute comprehensive descriptive statistics."""
    samples = np.asarray(samples, dtype=np.float64)
    n = len(samples)

    mean = float(np.mean(samples))
    median = float(np.median(samples))
    std = float(np.std(samples, ddof=1))
    var = float(np.var(samples, ddof=1))
    skewness = float(stats.skew(samples))
    kurt = float(stats.kurtosis(samples))
    cv = std / mean if mean > 0 else float('inf')
    iqr = float(np.percentile(samples, 75) - np.percentile(samples, 25))
    mad = float(np.median(np.abs(samples - median)))  # Median absolute deviation

    # Range
    min_val = float(np.min(samples))
    max_val = float(np.max(samples))
    range_val = max_val - min_val

    # Trimmed mean (10%)
    trimmed_mean = float(stats.trim_mean(samples, 0.1))

    # Geometric mean (for log-normal check)
    if np.all(samples > 0):
        geo_mean = float(np.exp(np.mean(np.log(samples))))
    else:
        geo_mean = 0.0

    return {
        "n": n,
        "mean_ns": mean,
        "median_ns": median,
        "std_ns": std,
        "variance_ns2": var,
        "min_ns": min_val,
        "max_ns": max_val,
        "range_ns": range_val,
        "iqr_ns": iqr,
        "mad_ns": mad,
        "cv": cv,
        "skewness": skewness,
        "kurtosis": kurt,
        "trimmed_mean_10_ns": trimmed_mean,
        "geometric_mean_ns": geo_mean,
    }


# ===========================================================================
# 3. Distribution Fitting
# ===========================================================================

def fit_distributions(samples: np.ndarray) -> List[DistributionFit]:
    """
    Fit multiple distributions and rank by goodness-of-fit.

    Distributions tested: normal, lognormal, exponential, weibull, gamma.
    """
    samples = np.asarray(samples, dtype=np.float64)
    n = len(samples)
    results = []

    dist_specs = [
        ("normal", stats.norm, 2),
        ("lognormal", stats.lognorm, 3),
        ("exponential", stats.expon, 2),
        ("weibull", stats.weibull_min, 3),
        ("gamma", stats.gamma, 3),
    ]

    for name, dist, n_params in dist_specs:
        try:
            params = dist.fit(samples)
            ks_stat, ks_p = stats.kstest(samples, lambda x: dist.cdf(x, *params))

            # Log-likelihood
            log_likelihood = np.sum(dist.logpdf(samples, *params))

            # AIC and BIC
            aic = 2 * n_params - 2 * log_likelihood
            bic = n_params * np.log(n) - 2 * log_likelihood

            results.append(DistributionFit(
                distribution=name,
                params=tuple(float(p) for p in params),
                ks_statistic=float(ks_stat),
                ks_pvalue=float(ks_p),
                aic=float(aic),
                bic=float(bic),
                log_likelihood=float(log_likelihood),
                fitted=True,
            ))
        except Exception:
            results.append(DistributionFit(
                distribution=name,
                params=(),
                ks_statistic=float('inf'),
                ks_pvalue=0.0,
                aic=float('inf'),
                bic=float('inf'),
                log_likelihood=float('-inf'),
                fitted=False,
            ))

    # Sort by AIC (lower is better)
    results.sort(key=lambda r: r.aic)
    return results


# ===========================================================================
# 4. Hypothesis Testing
# ===========================================================================

def compare_samples(
    samples_a: np.ndarray,
    samples_b: np.ndarray,
    name_a: str = "System A",
    name_b: str = "System B",
) -> Dict[str, Any]:
    """
    Statistical comparison of two latency sample sets.

    Performs: t-test, Mann-Whitney U, KS test, effect size.
    """
    a = np.asarray(samples_a, dtype=np.float64)
    b = np.asarray(samples_b, dtype=np.float64)

    # Welch's t-test (unequal variances)
    t_stat, t_p = stats.ttest_ind(a, b, equal_var=False)

    # Mann-Whitney U (non-parametric)
    u_stat, u_p = stats.mannwhitneyu(a, b, alternative='two-sided')

    # Kolmogorov-Smirnov test
    ks_stat, ks_p = stats.ks_2samp(a, b)

    # Effect size (Cohen's d)
    pooled_std = np.sqrt((np.std(a, ddof=1)**2 + np.std(b, ddof=1)**2) / 2)
    cohens_d = (np.mean(a) - np.mean(b)) / pooled_std if pooled_std > 0 else 0.0

    # Cliff's delta (non-parametric effect size)
    # Approximate via rank-biserial correlation
    ranks = stats.rankdata(np.concatenate([a, b]))
    rank_a = ranks[:len(a)]
    rbc = 2 * (np.mean(rank_a) - (len(a) + 1) / 2) / len(b)

    return {
        "t_test": {"statistic": float(t_stat), "pvalue": float(t_p)},
        "mann_whitney": {"statistic": float(u_stat), "pvalue": float(u_p)},
        "ks_test": {"statistic": float(ks_stat), "pvalue": float(ks_p)},
        "cohens_d": float(cohens_d),
        "cliffs_delta": float(rbc),
        "mean_a_ns": float(np.mean(a)),
        "mean_b_ns": float(np.mean(b)),
        "median_a_ns": float(np.median(a)),
        "median_b_ns": float(np.median(b)),
        "significant_05": bool(t_p < 0.05),
        "winner": name_a if np.mean(a) < np.mean(b) else name_b,
    }


# ===========================================================================
# 5. Throughput Analysis
# ===========================================================================

def throughput_analysis(
    timestamps: np.ndarray,
    window_seconds: float = 1.0,
) -> Dict[str, Any]:
    """
    Compute throughput statistics from event timestamps.

    Args:
        timestamps: Array of event timestamps (seconds).
        window_seconds: Sliding window size.

    Returns:
        Throughput statistics including percentiles, peak, sustained.
    """
    ts = np.asarray(timestamps, dtype=np.float64)
    ts.sort()

    if len(ts) < 2:
        return {"error": "Need at least 2 timestamps"}

    duration = ts[-1] - ts[0]
    n_windows = max(1, int(duration / window_seconds))

    # Count events per window
    counts = np.zeros(n_windows)
    for t in ts:
        idx = int((t - ts[0]) / window_seconds)
        if 0 <= idx < n_windows:
            counts[idx] += 1

    # Throughput = counts / window_seconds
    throughput = counts / window_seconds

    return {
        "total_events": int(len(ts)),
        "duration_s": float(duration),
        "window_s": window_seconds,
        "n_windows": n_windows,
        "throughput_mean": float(np.mean(throughput)),
        "throughput_std": float(np.std(throughput, ddof=1)),
        "throughput_p50": float(np.percentile(throughput, 50)),
        "throughput_p95": float(np.percentile(throughput, 95)),
        "throughput_p99": float(np.percentile(throughput, 99)),
        "throughput_peak": float(np.max(throughput)),
        "throughput_min": float(np.min(throughput)),
        "throughput_cv": float(np.std(throughput, ddof=1) / np.mean(throughput)) if np.mean(throughput) > 0 else 0,
    }


def throughput_latency_relationship(
    throughputs: np.ndarray,
    latencies: np.ndarray,
) -> Dict[str, Any]:
    """
    Analyze the throughput-latency relationship.

    Fits a model: latency = a * throughput^b (power law)
    and computes correlation.
    """
    t = np.asarray(throughputs, dtype=np.float64)
    l = np.asarray(latencies, dtype=np.float64)

    # Pearson correlation
    r, p = stats.pearsonr(t, l)

    # Spearman rank correlation
    rho, rho_p = stats.spearmanr(t, l)

    # Power law fit: latency = a * throughput^b
    def power_law(x, a, b):
        return a * np.power(x, b)

    try:
        popt, _ = curve_fit(power_law, t, l, p0=[l[0], 1.0], maxfev=10000)
        a_fit, b_fit = popt
        predicted = power_law(t, a_fit, b_fit)
        ss_res = np.sum((l - predicted) ** 2)
        ss_tot = np.sum((l - np.mean(l)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    except Exception:
        a_fit, b_fit, r_squared = 0.0, 0.0, 0.0

    return {
        "pearson_r": float(r),
        "pearson_p": float(p),
        "spearman_rho": float(rho),
        "spearman_p": float(rho_p),
        "power_law_a": float(a_fit),
        "power_law_b": float(b_fit),
        "power_law_r2": float(r_squared),
        "relationship": "positive" if r > 0.3 else ("negative" if r < -0.3 else "weak"),
    }


# ===========================================================================
# 6. Jitter Analysis
# ===========================================================================

def jitter_analysis(samples: np.ndarray) -> Dict[str, Any]:
    """
    Comprehensive jitter analysis.

    Computes: std dev, RMS jitter, peak-to-peak, autocorrelation, spectral analysis.
    """
    s = np.asarray(samples, dtype=np.float64)
    n = len(s)

    # First differences (jitter series)
    jitter = np.diff(s)

    # Basic jitter metrics
    jitter_mean = float(np.mean(jitter))
    jitter_std = float(np.std(jitter, ddof=1))
    jitter_rms = float(np.sqrt(np.mean(jitter**2)))
    jitter_max = float(np.max(np.abs(jitter)))
    jitter_p2p = float(np.max(s) - np.min(s))

    # Autocorrelation of jitter
    if len(jitter) > 1:
        jitter_centered = jitter - jitter_mean
        autocorr = np.correlate(jitter_centered, jitter_centered, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        autocorr = autocorr / autocorr[0] if autocorr[0] != 0 else autocorr
        # First zero-crossing
        zero_cross = -1
        for i in range(1, len(autocorr)):
            if autocorr[i] <= 0:
                zero_cross = i
                break
    else:
        autocorr = np.array([1.0])
        zero_cross = -1

    # Spectral analysis (FFT)
    if len(jitter) > 10:
        fft_vals = np.abs(np.fft.rfft(jitter))
        freqs = np.fft.rfftfreq(len(jitter))
        # Dominant frequency
        if len(fft_vals) > 1:
            dominant_idx = np.argmax(fft_vals[1:]) + 1
            dominant_freq = float(freqs[dominant_idx])
            dominant_power = float(fft_vals[dominant_idx])
        else:
            dominant_freq = 0.0
            dominant_power = 0.0
        # Spectral entropy
        psd = fft_vals**2
        psd_norm = psd / np.sum(psd) if np.sum(psd) > 0 else psd
        spectral_entropy = float(-np.sum(psd_norm * np.log2(psd_norm + 1e-12)))
    else:
        dominant_freq = 0.0
        dominant_power = 0.0
        spectral_entropy = 0.0

    return {
        "jitter_mean_ns": jitter_mean,
        "jitter_std_ns": jitter_std,
        "jitter_rms_ns": jitter_rms,
        "jitter_max_ns": jitter_max,
        "jitter_peak_to_peak_ns": jitter_p2p,
        "autocorr_lag1": float(autocorr[1]) if len(autocorr) > 1 else 0.0,
        "autocorr_first_zero_crossing": zero_cross,
        "dominant_frequency": dominant_freq,
        "dominant_power": dominant_power,
        "spectral_entropy": spectral_entropy,
    }


# ===========================================================================
# 7. Determinism Metrics
# ===========================================================================

def determinism_metrics(samples: np.ndarray) -> Dict[str, Any]:
    """Compute all determinism metrics."""
    s = np.asarray(samples, dtype=np.float64)
    n = len(s)

    mean = float(np.mean(s))
    std = float(np.std(s, ddof=1))
    cv = std / mean if mean > 0 else float('inf')

    p50 = float(np.percentile(s, 50))
    p99 = float(np.percentile(s, 99))
    p999 = float(np.percentile(s, 99.9))
    p9999 = float(np.percentile(s, 99.99))

    determinism_ratio = p50 / p999 if p999 > 0 else float('inf')
    predictability_index = 1 - (std / p999) if p999 > 0 else 0.0

    # Grade
    if cv < 0.01:
        grade = "Excellent"
    elif cv < 0.05:
        grade = "Very Good"
    elif cv < 0.10:
        grade = "Good"
    elif cv < 0.20:
        grade = "Acceptable"
    elif cv < 0.50:
        grade = "Poor"
    else:
        grade = "Unacceptable"

    return {
        "cv": cv,
        "determinism_ratio": determinism_ratio,
        "predictability_index": predictability_index,
        "p50_ns": p50,
        "p99_ns": p99,
        "p999_ns": p999,
        "p9999_ns": p9999,
        "grade": grade,
    }


# ===========================================================================
# 8. Availability Modeling
# ===========================================================================

def availability_metrics(
    uptime_seconds: float,
    downtime_seconds: float,
    n_failures: int,
) -> Dict[str, Any]:
    """Compute availability metrics."""
    total = uptime_seconds + downtime_seconds
    uptime_pct = (uptime_seconds / total * 100) if total > 0 else 100.0

    mtbf = uptime_seconds / n_failures if n_failures > 0 else float('inf')
    mttr = downtime_seconds / n_failures if n_failures > 0 else 0.0

    # Availability tier
    if uptime_pct >= 99.9999:
        tier = "6 nines"
    elif uptime_pct >= 99.999:
        tier = "5 nines"
    elif uptime_pct >= 99.99:
        tier = "4 nines"
    elif uptime_pct >= 99.9:
        tier = "3 nines"
    elif uptime_pct >= 99:
        tier = "2 nines"
    else:
        tier = "1 nine"

    # Downtime per year
    downtime_per_year = (100 - uptime_pct) / 100 * 365 * 24 * 3600

    return {
        "uptime_pct": uptime_pct,
        "tier": tier,
        "mtbf_seconds": mtbf,
        "mttr_seconds": mttr,
        "downtime_per_year_seconds": downtime_per_year,
        "downtime_per_year_human": _seconds_to_human(downtime_per_year),
    }


def _seconds_to_human(seconds: float) -> str:
    """Convert seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds*1000:.1f} ms"
    elif seconds < 60:
        return f"{seconds:.1f} s"
    elif seconds < 3600:
        return f"{seconds/60:.1f} min"
    elif seconds < 86400:
        return f"{seconds/3600:.1f} hours"
    else:
        return f"{seconds/86400:.2f} days"


# ===========================================================================
# 9. Cost Analysis
# ===========================================================================

def cost_per_microsecond(
    annual_cost: float,
    baseline_latency_us: float,
    achieved_latency_us: float,
) -> Dict[str, float]:
    """Compute cost per microsecond metrics."""
    improvement = baseline_latency_us - achieved_latency_us
    if improvement <= 0:
        return {
            "cost_per_us_absolute": annual_cost / achieved_latency_us if achieved_latency_us > 0 else float('inf'),
            "cost_per_us_marginal": float('inf'),
            "improvement_us": improvement,
        }
    return {
        "cost_per_us_absolute": annual_cost / achieved_latency_us,
        "cost_per_us_marginal": annual_cost / improvement,
        "improvement_us": improvement,
    }


def cost_per_trade(
    annual_cost: float,
    annual_trades: int,
) -> Dict[str, float]:
    """Compute cost per trade metrics."""
    if annual_trades <= 0:
        return {"cost_per_trade": float('inf'), "cost_per_1000_trades": float('inf')}
    cpt = annual_cost / annual_trades
    return {
        "cost_per_trade": cpt,
        "cost_per_1000_trades": cpt * 1000,
    }


def roi_calculation(
    revenue_with: float,
    revenue_without: float,
    investment_cost: float,
    time_years: float = 1.0,
) -> Dict[str, float]:
    """Compute ROI metrics."""
    revenue_uplift = revenue_with - revenue_without
    net_return = revenue_uplift * time_years - investment_cost
    roi = (net_return / investment_cost * 100) if investment_cost > 0 else 0.0
    payback = investment_cost / revenue_uplift if revenue_uplift > 0 else float('inf')

    return {
        "revenue_uplift": revenue_uplift,
        "net_return": net_return,
        "roi_pct": roi,
        "payback_years": payback,
        "roi_annualized_pct": ((1 + roi / 100) ** (1 / time_years) - 1) * 100 if time_years > 0 else roi,
    }


def tco_calculation(
    capex: float,
    annual_opex: float,
    annual_personnel: float,
    annual_data: float,
    annual_compliance: float,
    years: int = 3,
    discount_rate: float = 0.0,
) -> Dict[str, float]:
    """Compute Total Cost of Ownership."""
    total_opex = annual_opex + annual_personnel + annual_data + annual_compliance

    if discount_rate > 0:
        # Discounted cash flow
        npv_opex = sum(total_opex / (1 + discount_rate) ** t for t in range(1, years + 1))
        tco = capex + npv_opex
    else:
        tco = capex + total_opex * years

    return {
        "capex": capex,
        "annual_opex": annual_opex,
        "annual_personnel": annual_personnel,
        "annual_data": annual_data,
        "annual_compliance": annual_compliance,
        "total_annual_operating": total_opex,
        "tco": tco,
        "tco_per_year": tco / years,
        "capex_pct": capex / tco * 100 if tco > 0 else 0,
        "opex_pct": total_opex * years / tco * 100 if tco > 0 else 0,
    }


# ===========================================================================
# 10. Regression & Change-Point Detection
# ===========================================================================

def detect_trend(samples: np.ndarray) -> RegressionResult:
    """
    Detect trend in latency time series using linear regression.
    """
    s = np.asarray(samples, dtype=np.float64)
    n = len(s)
    x = np.arange(n, dtype=np.float64)

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, s)

    if slope > std_err * 2:
        direction = "increasing"
    elif slope < -std_err * 2:
        direction = "decreasing"
    else:
        direction = "stable"

    return RegressionResult(
        method="linear_regression",
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_value**2),
        p_value=float(p_value),
        trend_direction=direction,
    )


def detect_change_points(
    samples: np.ndarray,
    min_segment_size: int = 100,
    threshold: float = 3.0,
) -> RegressionResult:
    """
    Detect change points using a simple CUSUM-based approach.

    Args:
        samples: Latency time series.
        min_segment_size: Minimum samples between change points.
        threshold: Detection threshold (in std devs).

    Returns:
        RegressionResult with change point indices.
    """
    s = np.asarray(samples, dtype=np.float64)
    n = len(s)

    if n < min_segment_size * 2:
        return RegressionResult(
            method="cusum",
            slope=0, intercept=0, r_squared=0, p_value=1,
            change_points=[],
            trend_direction="insufficient_data",
        )

    # Normalize
    mean = np.mean(s)
    std = np.std(s, ddof=1)
    if std == 0:
        return RegressionResult(
            method="cusum",
            slope=0, intercept=mean, r_squared=0, p_value=1,
            change_points=[],
            trend_direction="stable",
        )

    normalized = (s - mean) / std

    # CUSUM
    cusum_pos = np.zeros(n)
    cusum_neg = np.zeros(n)
    change_points = []

    for i in range(1, n):
        cusum_pos[i] = max(0, cusum_pos[i-1] + normalized[i] - 0.5)
        cusum_neg[i] = max(0, cusum_neg[i-1] - normalized[i] - 0.5)

        if cusum_pos[i] > threshold or cusum_neg[i] > threshold:
            # Check minimum distance from last change point
            if not change_points or (i - change_points[-1]) >= min_segment_size:
                change_points.append(i)
            cusum_pos[i] = 0
            cusum_neg[i] = 0

    return RegressionResult(
        method="cusum",
        slope=0, intercept=mean, r_squared=0, p_value=0,
        change_points=change_points,
        trend_direction=f"{len(change_points)} change_points_detected",
    )


def detect_regression(
    baseline_samples: np.ndarray,
    current_samples: np.ndarray,
) -> Dict[str, Any]:
    """
    Detect performance regression between baseline and current.

    Uses multiple tests and effect sizes.
    """
    baseline = np.asarray(baseline_samples, dtype=np.float64)
    current = np.asarray(current_samples, dtype=np.float64)

    # Mann-Whitney U (non-parametric, robust to outliers)
    u_stat, u_p = stats.mannwhitneyu(current, baseline, alternative='greater')

    # t-test
    t_stat, t_p = stats.ttest_ind(current, baseline, equal_var=False)

    # Percentile comparison
    p50_base = np.percentile(baseline, 50)
    p50_curr = np.percentile(current, 50)
    p99_base = np.percentile(baseline, 99)
    p99_curr = np.percentile(current, 99)

    p50_change = (p50_curr - p50_base) / p50_base * 100 if p50_base > 0 else 0
    p99_change = (p99_curr - p99_base) / p99_base * 100 if p99_base > 0 else 0

    # Regression detected if p50 increased by >5% with statistical significance
    regression_detected = p50_change > 5 and u_p < 0.05

    return {
        "regression_detected": regression_detected,
        "p50_baseline_ns": float(p50_base),
        "p50_current_ns": float(p50_curr),
        "p50_change_pct": float(p50_change),
        "p99_baseline_ns": float(p99_base),
        "p99_current_ns": float(p99_curr),
        "p99_change_pct": float(p99_change),
        "mann_whitney_p": float(u_p),
        "t_test_p": float(t_p),
        "severity": "critical" if p50_change > 50 else ("major" if p50_change > 20 else ("minor" if p50_change > 5 else "none")),
    }


# ===========================================================================
# 11. Comparative Analysis
# ===========================================================================

def compare_systems(
    systems: Dict[str, np.ndarray],
    metrics: List[str] = None,
) -> List[ComparisonResult]:
    """
    Pairwise comparison of multiple systems.

    Args:
        systems: Dict mapping system name to latency samples.
        metrics: List of metrics to compare (default: ["mean", "p50", "p99"]).

    Returns:
        List of ComparisonResult for each pair.
    """
    if metrics is None:
        metrics = ["mean", "p50", "p99"]

    names = list(systems.keys())
    results = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            name_a, name_b = names[i], names[j]
            a = np.asarray(systems[name_a], dtype=np.float64)
            b = np.asarray(systems[name_b], dtype=np.float64)

            for metric in metrics:
                if metric == "mean":
                    val_a, val_b = np.mean(a), np.mean(b)
                elif metric == "p50":
                    val_a, val_b = np.percentile(a, 50), np.percentile(b, 50)
                elif metric == "p99":
                    val_a, val_b = np.percentile(a, 99), np.percentile(b, 99)
                elif metric == "p999":
                    val_a, val_b = np.percentile(a, 99.9), np.percentile(b, 99.9)
                else:
                    continue

                # Welch's t-test
                t_stat, t_p = stats.ttest_ind(a, b, equal_var=False)

                # Effect size (Cohen's d)
                pooled_std = np.sqrt((np.std(a, ddof=1)**2 + np.std(b, ddof=1)**2) / 2)
                cohens_d = (val_a - val_b) / pooled_std if pooled_std > 0 else 0

                diff = val_a - val_b
                pct_diff = diff / val_b * 100 if val_b > 0 else 0

                results.append(ComparisonResult(
                    system_a=name_a,
                    system_b=name_b,
                    metric=metric,
                    mean_a=float(val_a),
                    mean_b=float(val_b),
                    difference=float(diff),
                    percent_difference=float(pct_diff),
                    t_statistic=float(t_stat),
                    t_pvalue=float(t_p),
                    significant=bool(t_p < 0.05),
                    effect_size=float(cohens_d),
                    winner=name_a if val_a < val_b else name_b,
                ))

    return results


def benchmark_ranking(
    systems: Dict[str, np.ndarray],
    weights: Dict[str, float] = None,
) -> List[Dict[str, Any]]:
    """
    Rank systems by weighted composite score.

    Args:
        systems: Dict mapping system name to latency samples.
        weights: Weights for each metric (default: equal weights).

    Returns:
        Ranked list of systems with scores.
    """
    if weights is None:
        weights = {"p50": 0.3, "p99": 0.3, "p999": 0.2, "cv": 0.2}

    # Map weight keys to score keys
    key_map = {"p50": "p50_ns", "p99": "p99_ns", "p999": "p999_ns", "cv": "cv"}

    scores = []
    for name, samples in systems.items():
        s = np.asarray(samples, dtype=np.float64)
        p50 = np.percentile(s, 50)
        p99 = np.percentile(s, 99)
        p999 = np.percentile(s, 99.9)
        cv = np.std(s, ddof=1) / np.mean(s) if np.mean(s) > 0 else float('inf')

        scores.append({
            "system": name,
            "p50_ns": float(p50),
            "p99_ns": float(p99),
            "p999_ns": float(p999),
            "cv": float(cv),
        })

    # Normalize
    for metric in weights:
        score_key = key_map.get(metric, metric)
        vals = [s[score_key] for s in scores]
        min_val, max_val = min(vals), max(vals)
        for s in scores:
            if max_val > min_val:
                s[f"{metric}_norm"] = (s[score_key] - min_val) / (max_val - min_val)
            else:
                s[f"{metric}_norm"] = 0.0

    # Compute composite score
    for s in scores:
        composite = 0.0
        for metric, weight in weights.items():
            composite += weight * (1 - s[f"{metric}_norm"])  # Invert so lower = better
        s["composite_score"] = composite

    # Sort by composite score (higher = better)
    scores.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, s in enumerate(scores):
        s["rank"] = i + 1

    return scores


# ===========================================================================
# 12. Machine Learning
# ===========================================================================

def anomaly_detection_iqr(samples: np.ndarray, k: float = 1.5) -> AnomalyResult:
    """
    Detect anomalies using the IQR method.

    Args:
        samples: Latency samples.
        k: IQR multiplier (default 1.5 for outliers, 3.0 for extreme outliers).
    """
    s = np.asarray(samples, dtype=np.float64)
    q1 = np.percentile(s, 25)
    q3 = np.percentile(s, 75)
    iqr = q3 - q1

    lower = q1 - k * iqr
    upper = q3 + k * iqr

    anomaly_mask = (s < lower) | (s > upper)
    anomaly_indices = np.where(anomaly_mask)[0].tolist()

    # Anomaly scores (distance from nearest fence, normalized by IQR)
    scores = np.zeros(len(s))
    for i in range(len(s)):
        if s[i] < lower:
            scores[i] = (lower - s[i]) / iqr if iqr > 0 else 0
        elif s[i] > upper:
            scores[i] = (s[i] - upper) / iqr if iqr > 0 else 0

    return AnomalyResult(
        method="iqr",
        anomaly_indices=anomaly_indices,
        anomaly_scores=scores.tolist(),
        threshold=float(upper - lower),
        anomaly_count=len(anomaly_indices),
        anomaly_rate=len(anomaly_indices) / len(s) if len(s) > 0 else 0,
    )


def anomaly_detection_zscore(
    samples: np.ndarray,
    threshold: float = 3.0,
) -> AnomalyResult:
    """Detect anomalies using modified Z-score (MAD-based)."""
    s = np.asarray(samples, dtype=np.float64)
    median = np.median(s)
    mad = np.median(np.abs(s - median))

    if mad == 0:
        mad = np.std(s, ddof=1) * 0.6745  # Fallback

    modified_z = 0.6745 * (s - median) / mad if mad > 0 else np.zeros(len(s))

    anomaly_mask = np.abs(modified_z) > threshold
    anomaly_indices = np.where(anomaly_mask)[0].tolist()

    return AnomalyResult(
        method="modified_zscore",
        anomaly_indices=anomaly_indices,
        anomaly_scores=np.abs(modified_z).tolist(),
        threshold=threshold,
        anomaly_count=len(anomaly_indices),
        anomaly_rate=len(anomaly_indices) / len(s) if len(s) > 0 else 0,
    )


def anomaly_detection_isolation_forest(
    samples: np.ndarray,
    n_trees: int = 100,
    sample_size: int = 256,
    contamination: float = 0.01,
) -> AnomalyResult:
    """
    Simplified isolation forest implementation using random partitioning.

    This is a pure-numpy implementation suitable for 1D data.
    """
    s = np.asarray(samples, dtype=np.float64)
    n = len(s)

    if n < sample_size:
        sample_size = n

    # Build isolation trees
    path_lengths = np.zeros(n)

    for _ in range(n_trees):
        # Random subsample
        idx = np.random.choice(n, size=min(sample_size, n), replace=False)
        subsample = s[idx]

        # Build tree and compute path lengths
        for i in range(n):
            path_lengths[i] += _isolation_path_length(s[i], subsample)

    # Average path length
    avg_path_lengths = path_lengths / n_trees

    # Anomaly score: 2^(-avg_path / c(n))
    c_n = 2 * (np.log(sample_size - 1) + 0.5772156649) - 2 * (sample_size - 1) / sample_size
    scores = 2 ** (-avg_path_lengths / c_n) if c_n > 0 else np.zeros(n)

    # Threshold based on contamination
    threshold = np.percentile(scores, 100 * (1 - contamination))
    anomaly_mask = scores >= threshold
    anomaly_indices = np.where(anomaly_mask)[0].tolist()

    return AnomalyResult(
        method="isolation_forest",
        anomaly_indices=anomaly_indices,
        anomaly_scores=scores.tolist(),
        threshold=float(threshold),
        anomaly_count=len(anomaly_indices),
        anomaly_rate=len(anomaly_indices) / n if n > 0 else 0,
    )


def _isolation_path_length(value: float, data: np.ndarray, depth: int = 0, max_depth: int = 50) -> float:
    """Compute isolation path length for a single value."""
    if len(data) <= 1 or depth >= max_depth:
        return depth + _c_factor(len(data))

    min_val = np.min(data)
    max_val = np.max(data)

    if min_val == max_val:
        return depth + _c_factor(len(data))

    # Random split point
    split = random.uniform(min_val, max_val)

    if value < split:
        return _isolation_path_length(value, data[data < split], depth + 1, max_depth)
    else:
        return _isolation_path_length(value, data[data >= split], depth + 1, max_depth)


def _c_factor(n: int) -> float:
    """Average path length of unsuccessful search in BST."""
    if n <= 1:
        return 0
    return 2 * (np.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n


def kmeans_clustering(
    samples: np.ndarray,
    k: int = 3,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """
    K-means clustering of latency samples.

    Useful for identifying modes in latency distribution (e.g., cache hit vs miss).
    """
    s = np.asarray(samples, dtype=np.float64)
    n = len(s)

    # Initialize centroids using k-means++
    centroids = _kmeans_plus_plus(s, k)

    for _ in range(max_iter):
        # Assign to nearest centroid
        distances = np.abs(s[:, np.newaxis] - centroids[np.newaxis, :])
        labels = np.argmin(distances, axis=1)

        # Update centroids
        new_centroids = np.array([s[labels == j].mean() if np.sum(labels == j) > 0 else centroids[j]
                                  for j in range(k)])

        if np.allclose(centroids, new_centroids):
            break
        centroids = new_centroids

    # Compute cluster statistics
    clusters = []
    for j in range(k):
        cluster_samples = s[labels == j]
        clusters.append({
            "cluster": j,
            "centroid_ns": float(centroids[j]),
            "count": int(len(cluster_samples)),
            "mean_ns": float(np.mean(cluster_samples)),
            "std_ns": float(np.std(cluster_samples, ddof=1)) if len(cluster_samples) > 1 else 0,
            "min_ns": float(np.min(cluster_samples)),
            "max_ns": float(np.max(cluster_samples)),
        })

    # Sort by centroid
    clusters.sort(key=lambda c: c["centroid_ns"])

    # Inertia (within-cluster sum of squares)
    inertia = np.sum((s - centroids[labels]) ** 2)

    return {
        "k": k,
        "inertia": float(inertia),
        "clusters": clusters,
        "labels": labels.tolist(),
    }


def _kmeans_plus_plus(data: np.ndarray, k: int) -> np.ndarray:
    """K-means++ initialization."""
    n = len(data)
    centroids = [data[random.randint(0, n - 1)]]

    for _ in range(1, k):
        dists = np.min(np.abs(data[:, np.newaxis] - np.array(centroids)[np.newaxis, :]), axis=1)
        probs = dists**2 / np.sum(dists**2) if np.sum(dists**2) > 0 else np.ones(n) / n
        centroids.append(data[np.random.choice(n, p=probs)])

    return np.array(centroids)


def latency_prediction(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str = "linear",
    test_size: float = 0.2,
) -> MLModelResult:
    """
    Train a latency prediction model.

    Args:
        X: Feature matrix (n_samples, n_features).
        y: Target latencies.
        model_type: "linear", "polynomial", or "exponential".
        test_size: Fraction for test set.

    Returns:
        MLModelResult with model performance.
    """
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = len(y)

    # Train/test split
    n_test = max(1, int(n * test_size))
    indices = np.random.permutation(n)
    train_idx, test_idx = indices[n_test:], indices[:n_test]

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    if model_type == "linear":
        # Multiple linear regression via least ones
        X_train_aug = np.column_stack([X_train, np.ones(len(X_train))])
        X_test_aug = np.column_stack([X_test, np.ones(len(X_test))])

        # Normal equation
        try:
            coeffs = np.linalg.lstsq(X_train_aug, y_train, rcond=None)[0]
            y_pred_train = X_train_aug @ coeffs
            y_pred_test = X_test_aug @ coeffs
        except np.linalg.LinAlgError:
            y_pred_train = np.full(len(y_train), np.mean(y_train))
            y_pred_test = np.full(len(y_test), np.mean(y_train))

        feature_importance = {f"feature_{i}": float(abs(coeffs[i])) for i in range(X.shape[1])}

    elif model_type == "polynomial":
        # Polynomial features (degree 2)
        X_train_poly = _polynomial_features(X_train, degree=2)
        X_test_poly = _polynomial_features(X_test, degree=2)

        X_train_aug = np.column_stack([X_train_poly, np.ones(len(X_train_poly))])
        X_test_aug = np.column_stack([X_test_poly, np.ones(len(X_test_poly))])

        try:
            coeffs = np.linalg.lstsq(X_train_aug, y_train, rcond=None)[0]
            y_pred_train = X_train_aug @ coeffs
            y_pred_test = X_test_aug @ coeffs
        except np.linalg.LinAlgError:
            y_pred_train = np.full(len(y_train), np.mean(y_train))
            y_pred_test = np.full(len(y_test), np.mean(y_train))

        feature_importance = {f"poly_feature_{i}": float(abs(coeffs[i])) for i in range(X_train_aug.shape[1] - 1)}

    elif model_type == "exponential":
        # Fit: y = a * exp(b * x) -> log(y) = log(a) + b * x
        log_y_train = np.log(np.maximum(y_train, 1e-12))
        X_train_aug = np.column_stack([X_train, np.ones(len(X_train))])
        X_test_aug = np.column_stack([X_test, np.ones(len(X_test))])

        try:
            coeffs = np.linalg.lstsq(X_train_aug, log_y_train, rcond=None)[0]
            y_pred_train = np.exp(X_train_aug @ coeffs)
            y_pred_test = np.exp(X_test_aug @ coeffs)
        except np.linalg.LinAlgError:
            y_pred_train = np.full(len(y_train), np.mean(y_train))
            y_pred_test = np.full(len(y_test), np.mean(y_train))

        feature_importance = {f"exp_feature_{i}": float(abs(coeffs[i])) for i in range(X.shape[1])}

    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    # R-squared
    ss_res_train = np.sum((y_train - y_pred_train) ** 2)
    ss_tot_train = np.sum((y_train - np.mean(y_train)) ** 2)
    train_r2 = 1 - ss_res_train / ss_tot_train if ss_tot_train > 0 else 0

    ss_res_test = np.sum((y_test - y_pred_test) ** 2)
    ss_tot_test = np.sum((y_test - np.mean(y_test)) ** 2)
    test_r2 = 1 - ss_res_test / ss_tot_test if ss_tot_test > 0 else 0

    return MLModelResult(
        model_type=model_type,
        train_score=float(train_r2),
        test_score=float(test_r2),
        predictions=y_pred_test.tolist(),
        feature_importance=feature_importance,
    )


def _polynomial_features(X: np.ndarray, degree: int = 2) -> np.ndarray:
    """Generate polynomial features."""
    n, d = X.shape
    features = [X]
    for deg in range(2, degree + 1):
        for i in range(d):
            features.append((X[:, i] ** deg).reshape(-1, 1))
    return np.hstack(features)


def pca_dimensionality_reduction(
    X: np.ndarray,
    n_components: int = 2,
) -> Dict[str, Any]:
    """
    PCA for dimensionality reduction of multi-feature latency data.

    Args:
        X: Feature matrix (n_samples, n_features).
        n_components: Number of principal components.

    Returns:
        Dict with transformed data, explained variance, and components.
    """
    X = np.asarray(X, dtype=np.float64)

    # Center
    mean = np.mean(X, axis=0)
    X_centered = X - mean

    # SVD
    U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)

    # Explained variance
    explained_variance = S**2 / (len(X) - 1)
    total_var = np.sum(explained_variance)
    explained_variance_ratio = explained_variance / total_var if total_var > 0 else np.zeros_like(explained_variance)

    # Transform
    n_components = min(n_components, X.shape[1])
    X_transformed = U[:, :n_components] * S[:n_components]

    return {
        "transformed": X_transformed.tolist(),
        "explained_variance": explained_variance[:n_components].tolist(),
        "explained_variance_ratio": explained_variance_ratio[:n_components].tolist(),
        "cumulative_variance_ratio": float(np.sum(explained_variance_ratio[:n_components])),
        "components": Vt[:n_components].tolist(),
        "mean": mean.tolist(),
    }


# ===========================================================================
# 13. Visualization
# ===========================================================================

def _import_matplotlib():
    """Import matplotlib, returning (plt, error) tuple."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        return plt, None
    except Exception as e:
        return None, str(e)


def plot_latency_distribution(
    samples: np.ndarray,
    title: str = "Latency Distribution",
    save_path: Optional[str] = None,
) -> None:
    """Plot latency distribution histogram with fitted distributions."""
    plt, err = _import_matplotlib()
    if plt is None:
        print(f"    [SKIP] Visualization unavailable: {err}")
        return

    s = np.asarray(samples, dtype=np.float64)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    ax = axes[0]
    ax.hist(s, bins=100, density=True, alpha=0.7, color='steelblue', edgecolor='white')
    ax.set_xlabel("Latency (ns)")
    ax.set_ylabel("Density")
    ax.set_title(f"{title} — Histogram")
    ax.axvline(np.median(s), color='red', linestyle='--', label=f"Median: {np.median(s):.1f} ns")
    ax.axvline(np.mean(s), color='green', linestyle='--', label=f"Mean: {np.mean(s):.1f} ns")
    ax.legend()

    # CDF
    ax = axes[1]
    sorted_s = np.sort(s)
    cdf = np.arange(1, len(sorted_s) + 1) / len(sorted_s)
    ax.plot(sorted_s, cdf, color='steelblue', linewidth=1)
    ax.set_xlabel("Latency (ns)")
    ax.set_ylabel("CDF")
    ax.set_title(f"{title} — CDF")
    ax.grid(True, alpha=0.3)

    # Mark percentiles
    for p in [50, 95, 99, 99.9]:
        val = np.percentile(s, p)
        ax.axvline(val, color='red', linestyle=':', alpha=0.5)
        ax.text(val, 0.5, f"p{p}", rotation=90, va='center', fontsize=8)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    plt.close()


def plot_time_series(
    samples: np.ndarray,
    title: str = "Latency Time Series",
    save_path: Optional[str] = None,
) -> None:
    """Plot latency time series with trend and change points."""
    plt, err = _import_matplotlib()
    if plt is None:
        print(f"    [SKIP] Visualization unavailable: {err}")
        return

    s = np.asarray(samples, dtype=np.float64)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # Time series
    ax = axes[0]
    ax.plot(s, color='steelblue', linewidth=0.5, alpha=0.7)
    ax.set_xlabel("Sample Index")
    ax.set_ylabel("Latency (ns)")
    ax.set_title(f"{title} — Time Series")

    # Trend line
    trend = detect_trend(s)
    x = np.arange(len(s))
    ax.plot(x, trend.intercept + trend.slope * x, 'r--', linewidth=2,
            label=f"Trend: {trend.trend_direction} (slope={trend.slope:.4f})")
    ax.legend()

    # Rolling statistics
    ax = axes[1]
    window = min(1000, len(s) // 10)
    if window > 1:
        rolling_mean = np.convolve(s, np.ones(window)/window, mode='valid')
        rolling_std = np.array([np.std(s[i:i+window]) for i in range(len(s) - window + 1)])
        ax.plot(rolling_mean, color='steelblue', linewidth=1, label=f"Rolling Mean (w={window})")
        ax.fill_between(range(len(rolling_mean)),
                        rolling_mean - rolling_std, rolling_mean + rolling_std,
                        alpha=0.3, color='steelblue', label=f"±1σ")
        ax.set_xlabel("Sample Index")
        ax.set_ylabel("Latency (ns)")
        ax.set_title(f"{title} — Rolling Statistics")
        ax.legend()

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    plt.close()


def plot_comparison(
    systems: Dict[str, np.ndarray],
    title: str = "System Comparison",
    save_path: Optional[str] = None,
) -> None:
    """Plot comparison of multiple systems."""
    plt, err = _import_matplotlib()
    if plt is None:
        print(f"    [SKIP] Visualization unavailable: {err}")
        return

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    names = list(systems.keys())
    colors = plt.cm.Set2(np.linspace(0, 1, len(names)))

    # Box plot
    ax = axes[0]
    data = [systems[n] for n in names]
    bp = ax.boxplot(data, labels=names, patch_artist=True)
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    ax.set_ylabel("Latency (ns)")
    ax.set_title(f"{title} — Box Plot")
    ax.tick_params(axis='x', rotation=45)

    # Violin plot
    ax = axes[1]
    parts = ax.violinplot(data, positions=range(len(names)), showmeans=True, showmedians=True)
    for pc, color in zip(parts['bodies'], colors):
        pc.set_facecolor(color)
        pc.set_alpha(0.7)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45)
    ax.set_ylabel("Latency (ns)")
    ax.set_title(f"{title} — Violin Plot")

    # CDF comparison
    ax = axes[2]
    for i, name in enumerate(names):
        sorted_s = np.sort(systems[name])
        cdf = np.arange(1, len(sorted_s) + 1) / len(sorted_s)
        ax.plot(sorted_s, cdf, label=name, color=colors[i], linewidth=1.5)
    ax.set_xlabel("Latency (ns)")
    ax.set_ylabel("CDF")
    ax.set_title(f"{title} — CDF Comparison")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    plt.close()


def plot_heatmap(
    data: np.ndarray,
    x_labels: List[str],
    y_labels: List[str],
    title: str = "Latency Heatmap",
    save_path: Optional[str] = None,
) -> None:
    """Plot heatmap of latency data (e.g., time-of-day vs system)."""
    plt, err = _import_matplotlib()
    if plt is None:
        print(f"    [SKIP] Visualization unavailable: {err}")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(data, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=45)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_title(title)
    plt.colorbar(im, ax=ax, label="Latency (ns)")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    plt.close()


# ===========================================================================
# 14. Full Evaluation Pipeline
# ===========================================================================

def full_evaluation(samples: np.ndarray, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Run the complete evaluation pipeline on latency samples.

    Args:
        samples: Latency samples in nanoseconds.
        metadata: Optional metadata dict.

    Returns:
        Complete evaluation report.
    """
    s = np.asarray(samples, dtype=np.float64)

    report = {
        "metadata": metadata or {},
        "descriptive_statistics": descriptive_statistics(s),
        "percentiles": [asdict(p) for p in compute_percentiles(s)],
        "distribution_fits": [asdict(d) for d in fit_distributions(s)],
        "jitter_analysis": jitter_analysis(s),
        "determinism": determinism_metrics(s),
        "trend": asdict(detect_trend(s)),
        "change_points": asdict(detect_change_points(s)),
        "anomalies_iqr": asdict(anomaly_detection_iqr(s)),
        "anomalies_zscore": asdict(anomaly_detection_zscore(s)),
        "clustering": kmeans_clustering(s, k=3),
    }

    return report


# ===========================================================================
# Demo / CLI
# ===========================================================================

def _generate_demo_samples(
    n: int = 100_000,
    base_latency_ns: float = 7000,
    noise_std_ns: float = 300,
    spike_prob: float = 0.01,
    outlier_prob: float = 0.0001,
) -> np.ndarray:
    """Generate synthetic latency samples."""
    np.random.seed(42)
    samples = np.random.normal(base_latency_ns, noise_std_ns, n)

    # Spikes
    spike_mask = np.random.random(n) < spike_prob
    samples[spike_mask] += np.random.uniform(5000, 15000, np.sum(spike_mask))

    # Outliers
    outlier_mask = np.random.random(n) < outlier_prob
    samples[outlier_mask] += np.random.uniform(50000, 200000, np.sum(outlier_mask))

    # Add a trend (simulating degradation)
    trend = np.linspace(0, 500, n)
    samples += trend

    return np.maximum(samples, 100.0)


def run_demo() -> None:
    """Run demonstration with synthetic data."""
    print("=" * 80)
    print("  ULL LATENCY EVALUATION FRAMEWORK — STATISTICAL & ML DEMO")
    print("=" * 80)

    # Generate samples
    print("\n[1] Generating synthetic latency samples...")
    samples = _generate_demo_samples(n=50_000)
    print(f"    Generated {len(samples):,} samples")

    # Descriptive statistics
    print("\n[2] Descriptive Statistics:")
    desc = descriptive_statistics(samples)
    for k, v in desc.items():
        if isinstance(v, float):
            print(f"    {k:30s}: {v:>15.4f}")
        else:
            print(f"    {k:30s}: {v:>15}")

    # Percentiles
    print("\n[3] Percentiles with 95% CI:")
    pcts = compute_percentiles(samples, n_bootstrap=5000)
    for p in pcts:
        print(f"    p{p.percentile:>6.2f}: {p.value_ns:>12.2f} ns "
              f"[{p.ci_lower_ns:.2f}, {p.ci_upper_ns:.2f}] ±{p.std_error_ns:.2f}")

    # Distribution fitting
    print("\n[4] Distribution Fitting (ranked by AIC):")
    fits = fit_distributions(samples)
    for f in fits[:3]:
        print(f"    {f.distribution:15s}: AIC={f.aic:.0f}, KS={f.ks_statistic:.4f}, p={f.ks_pvalue:.4f}")

    # Jitter
    print("\n[5] Jitter Analysis:")
    jitter = jitter_analysis(samples)
    for k, v in jitter.items():
        if isinstance(v, float):
            print(f"    {k:30s}: {v:>15.4f}")

    # Determinism
    print("\n[6] Determinism Metrics:")
    det = determinism_metrics(samples)
    for k, v in det.items():
        if isinstance(v, float):
            print(f"    {k:30s}: {v:>15.6f}")
        else:
            print(f"    {k:30s}: {v}")

    # Trend
    print("\n[7] Trend Detection:")
    trend = detect_trend(samples)
    print(f"    Direction: {trend.trend_direction}")
    print(f"    Slope: {trend.slope:.6f} ns/sample")
    print(f"    R²: {trend.r_squared:.4f}")

    # Change points
    print("\n[8] Change-Point Detection:")
    cp = detect_change_points(samples)
    print(f"    Change points: {len(cp.change_points)}")
    if cp.change_points:
        print(f"    At indices: {cp.change_points[:10]}")

    # Anomaly detection
    print("\n[9] Anomaly Detection:")
    a_iqr = anomaly_detection_iqr(samples)
    print(f"    IQR method: {a_iqr.anomaly_count} anomalies ({a_iqr.anomaly_rate*100:.3f}%)")
    a_z = anomaly_detection_zscore(samples)
    print(f"    Z-score method: {a_z.anomaly_count} anomalies ({a_z.anomaly_rate*100:.3f}%)")

    # Clustering
    print("\n[10] K-Means Clustering (k=3):")
    km = kmeans_clustering(samples, k=3)
    for c in km["clusters"]:
        print(f"    Cluster {c['cluster']}: centroid={c['centroid_ns']:.1f} ns, "
              f"count={c['count']:,}, std={c['std_ns']:.1f} ns")

    # Comparative analysis
    print("\n[11] Comparative Analysis:")
    systems = {
        "FPGA": np.random.normal(500, 50, 10000),
        "Kernel Bypass": np.random.normal(5000, 500, 10000),
        "Standard Kernel": np.random.normal(50000, 5000, 10000),
    }
    comparisons = compare_systems(systems)
    for c in comparisons[:3]:
        sig = "*" if c.significant else " "
        print(f"    {c.system_a} vs {c.system_b} ({c.metric}): "
              f"{c.difference:.1f} ns ({c.percent_difference:+.1f}%) {sig}")

    # Ranking
    print("\n[12] Benchmark Ranking:")
    ranking = benchmark_ranking(systems)
    for r in ranking:
        print(f"    #{r['rank']}: {r['system']:20s} score={r['composite_score']:.4f}")

    # Visualization
    print("\n[13] Generating visualizations...")
    plot_latency_distribution(samples, save_path="latency_distribution.png")
    plot_time_series(samples, save_path="latency_time_series.png")
    plot_comparison(systems, save_path="system_comparison.png")

    print("\n" + "=" * 80)
    print("  Demo complete. Check generated PNG files.")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="ULL Latency Evaluation Framework — Statistical & ML")
    parser.add_argument("--demo", action="store_true", help="Run demo with synthetic data")
    parser.add_argument("--input", "-i", help="Input file with latency samples (one per line, ns)")
    parser.add_argument("--output", "-o", help="Output JSON report file")
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.input:
        parser.error("Either --demo or --input must be specified")

    # Load samples
    samples = []
    with open(args.input) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                samples.append(float(line))

    print(f"Loaded {len(samples):,} samples from {args.input}")
    report = full_evaluation(np.array(samples), metadata={"source": args.input})

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to {args.output}")
    else:
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
