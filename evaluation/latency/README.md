# ULL Latency Evaluation Framework

**Version:** 2.0  
**Date:** September 2026

Deepened ultra-low latency evaluation framework with full statistical analysis, machine learning, regression detection, comparative analysis, and visualization.

## Files

| File | Description |
|------|-------------|
| `ull-latency-evaluation-framework.md` | Base framework (v1.0) — metrics, methodology, benchmarks |
| `ull-statistical-ml-framework.md` | Statistical & ML framework (v2.0) — this extension |
| `ull_latency_ml.py` | Python implementation of all statistical & ML methods |

## Quick Start

```bash
# Run demo with synthetic data
python ull_latency_ml.py --demo

# Analyze real latency data
python ull_latency_ml.py --input samples.txt --output report.json
```

## Capabilities

### Statistical Analysis
- Descriptive statistics (mean, median, std, skewness, kurtosis, CV, IQR, MAD)
- Percentile analysis with bootstrap confidence intervals (p50/p95/p99/p999/p9999)
- Distribution fitting (normal, lognormal, exponential, Weibull, gamma) with AIC/BIC
- Hypothesis testing (Welch's t-test, Mann-Whitney U, KS test)
- Effect sizes (Cohen's d, Cliff's delta)

### Throughput Analysis
- Sliding window throughput computation
- Throughput-latency relationship modeling (power law)
- Peak vs sustained throughput

### Jitter Analysis
- Time-domain: std dev, RMS, peak-to-peak, max
- Frequency-domain: FFT, dominant frequency, spectral entropy
- Autocorrelation analysis

### Determinism
- Coefficient of Variation (CV)
- Determinism Ratio (p50/p999)
- Predictability Index
- Composite determinism score

### Availability Modeling
- Uptime, MTBF, MTTR
- Availability tiers (2-6 nines)
- Downtime cost modeling

### Cost Analysis
- Cost per microsecond (absolute and marginal)
- Cost per trade
- ROI and payback period
- Total Cost of Ownership (TCO)

### Regression Detection
- Linear trend detection
- CUSUM change-point detection
- Baseline vs current comparison
- Severity classification

### Comparative Analysis
- Pairwise system comparison
- Statistical significance testing
- Weighted composite ranking

### Machine Learning
- Anomaly detection: IQR, modified Z-score, Isolation Forest
- K-means clustering for latency mode identification
- Latency prediction: linear, polynomial, exponential models
- PCA for dimensionality reduction

### Visualization
- Distribution histograms with fitted CDFs
- Time series with trend and rolling statistics
- System comparison (box plots, violin plots, CDFs)
- Heatmaps

## Python API

```python
from ull_latency_ml import (
    descriptive_statistics,
    compute_percentiles,
    fit_distributions,
    jitter_analysis,
    determinism_metrics,
    detect_trend,
    detect_change_points,
    detect_regression,
    anomaly_detection_iqr,
    anomaly_detection_zscore,
    anomaly_detection_isolation_forest,
    kmeans_clustering,
    latency_prediction,
    pca_dimensionality_reduction,
    compare_systems,
    benchmark_ranking,
    throughput_analysis,
    throughput_latency_relationship,
    cost_per_microsecond,
    cost_per_trade,
    roi_calculation,
    tco_calculation,
    availability_metrics,
    full_evaluation,
    plot_latency_distribution,
    plot_time_series,
    plot_comparison,
    plot_heatmap,
)
```

## Input Format

Latency samples: one value per line in nanoseconds.

```
# Comment lines start with #
7254.16
7102.34
6987.12
...
```

## Output Format

JSON report with all metrics:

```json
{
  "metadata": {...},
  "descriptive_statistics": {...},
  "percentiles": [...],
  "distribution_fits": [...],
  "jitter_analysis": {...},
  "determinism": {...},
  "trend": {...},
  "change_points": {...},
  "anomalies_iqr": {...},
  "anomalies_zscore": {...},
  "clustering": {...}
}
```

## Dependencies

- Python 3.9+
- numpy >= 1.20
- scipy >= 1.7
- matplotlib >= 3.5 (optional, for visualization)

## References

See the base framework document for industry benchmarks, measurement methodology, and sources.
