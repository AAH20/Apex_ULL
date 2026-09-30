# ULL Latency Evaluation Framework — Statistical Analysis & ML

**Version:** 2.0  
**Date:** September 2026  
**Scope:** Deepened statistical analysis, machine learning, regression detection, comparative analysis, and visualization for ultra-low latency infrastructure evaluation.

---

## Table of Contents

1. [Overview](#overview)
2. [Statistical Analysis](#statistical-analysis)
3. [Distribution Fitting](#distribution-fitting)
4. [Hypothesis Testing](#hypothesis-testing)
5. [Throughput Analysis](#throughput-analysis)
6. [Jitter Spectral Analysis](#jitter-spectral-analysis)
7. [Determinism Metrics](#determinism-metrics)
8. [Availability Modeling](#availability-modeling)
9. [Cost Analysis](#cost-analysis)
10. [Regression & Change-Point Detection](#regression--change-point-detection)
11. [Comparative Analysis](#comparative-analysis)
12. [Machine Learning](#machine-learning)
13. [Visualization](#visualization)
14. [Full Evaluation Pipeline](#full-evaluation-pipeline)
15. [Implementation](#implementation)

---

## Overview

This document extends the base ULL Latency Evaluation Framework with advanced statistical analysis, machine learning, and visualization capabilities. It provides:

- **Full percentile analysis** with bootstrap confidence intervals
- **Distribution fitting** with AIC/BIC model selection
- **Hypothesis testing** for system comparison
- **Throughput-latency relationship** modeling
- **Jitter spectral analysis** (FFT, autocorrelation)
- **Change-point detection** (CUSUM)
- **Anomaly detection** (IQR, Z-score, Isolation Forest)
- **K-means clustering** for latency mode identification
- **PCA** for dimensionality reduction
- **Latency prediction** models (linear, polynomial, exponential)
- **Comparative analysis** with effect sizes
- **Benchmark ranking** with weighted composite scores
- **Visualization** (distributions, CDFs, time series, heatmaps)

---

## Statistical Analysis

### Descriptive Statistics

Comprehensive descriptive statistics for latency samples:

| Statistic | Formula | Use |
|-----------|---------|-----|
| Mean | μ = (1/N) Σ xᵢ | Central tendency |
| Median | p50 | Robust central tendency |
| Std Dev | σ = √[(1/(N-1)) Σ (xᵢ - μ)²] | Spread |
| Variance | σ² | Spread squared |
| Skewness | E[(x-μ)³]/σ³ | Asymmetry |
| Kurtosis | E[(x-μ)⁴]/σ⁴ - 3 | Tail heaviness |
| CV | σ/μ | Normalized spread |
| IQR | p75 - p25 | Robust spread |
| MAD | median(\|x - median\|) | Robust deviation |
| Trimmed Mean | mean after removing 10% tails | Robust mean |
| Geometric Mean | exp(mean(ln(x))) | Log-normal check |

### Percentile Analysis with Confidence Intervals

Percentiles are computed with bootstrap confidence intervals:

```
p50, p95, p99, p999, p9999
```

Each percentile includes:
- Point estimate
- 95% confidence interval (bootstrap)
- Standard error

**Bootstrap Protocol:**
1. Resample N samples with replacement (10,000 iterations)
2. Compute percentile for each resample
3. Take 2.5th and 97.5th percentiles as CI

**Sample Size Requirements:**

| Percentile | Minimum Samples | Recommended |
|------------|-----------------|-------------|
| p50 | 1,000 | 10,000 |
| p95 | 10,000 | 100,000 |
| p99 | 100,000 | 1,000,000 |
| p999 | 1,000,000 | 10,000,000 |
| p9999 | 10,000,000 | 100,000,000 |

---

## Distribution Fitting

### Supported Distributions

| Distribution | Parameters | Use Case |
|--------------|------------|----------|
| Normal | μ, σ | Symmetric, light-tailed |
| Lognormal | μ, σ, shift | Right-skewed, multiplicative noise |
| Exponential | λ | Memoryless, single-mode |
| Weibull | k, λ | Flexible shape |
| Gamma | k, θ | Right-skewed, flexible |

### Model Selection

Models ranked by **AIC** (Akaike Information Criterion):

```
AIC = 2k - 2ln(L)
```

Where k = number of parameters, L = likelihood.

**Interpretation:**
- Lower AIC = better fit
- ΔAIC < 2: substantial support
- ΔAIC 4-7: considerably less support
- ΔAIC > 10: essentially no support

### Goodness-of-Fit Tests

| Test | Statistic | Use |
|------|-----------|-----|
| Kolmogorov-Smirnov | D = max\|F_emp - F_fit\| | Overall fit |
| Anderson-Darling | A² | Tail-sensitive |
| Shapiro-Wilk | W | Normality |

---

## Hypothesis Testing

### Two-Sample Comparison

For comparing two systems (A vs B):

| Test | Assumptions | Use |
|------|-------------|-----|
| Welch's t-test | Approximately normal | Mean comparison |
| Mann-Whitney U | Non-parametric | Median comparison |
| Kolmogorov-Smirnov | Non-parametric | Distribution comparison |

### Effect Sizes

| Measure | Formula | Interpretation |
|---------|---------|----------------|
| Cohen's d | (μ_A - μ_B) / σ_pooled | 0.2=small, 0.5=medium, 0.8=large |
| Cliff's delta | P(X_A > X_B) - P(X_A < X_B) | -1 to 1 |
| Rank-biserial | 2×(mean_rank_A - (N+1)/2) / N_B | Correlation-like |

### Multiple Comparison Correction

When comparing multiple systems, apply:
- **Bonferroni**: α/m (conservative)
- **Holm-Bonferroni**: Step-down (less conservative)
- **Benjamini-Hochberg**: FDR control

---

## Throughput Analysis

### Throughput Metrics

| Metric | Formula | Use |
|--------|---------|-----|
| Mean throughput | N / T | Average rate |
| Peak throughput | max(counts per window) | Burst capacity |
| Sustained throughput | p95 of windowed counts | Stable capacity |
| Throughput CV | σ/μ of windowed counts | Stability |

### Throughput-Latency Relationship

**Power Law Model:**
```
latency = a × throughput^b
```

Where:
- b > 0: latency increases with throughput (typical)
- b ≈ 0: latency independent of throughput (ideal)
- b < 0: latency decreases with throughput (unusual)

**Correlation Analysis:**
- Pearson r: linear relationship
- Spearman ρ: monotonic relationship

### Load Level Behavior

| Load | Latency Behavior | Throughput Behavior |
|------|------------------|---------------------|
| <50% | Stable | Linear increase |
| 50-80% | Slight increase | Still increasing |
| 80-95% | Sharp increase | Plateau |
| >95% | Spikes | May decrease (backpressure) |

---

## Jitter Spectral Analysis

### Time-Domain Jitter

| Metric | Formula | Use |
|--------|---------|-----|
| Jitter std dev | σ(Δx) | Overall variability |
| RMS jitter | √(mean(Δx²)) | Energy of variation |
| Peak-to-peak | max(x) - min(x) | Total range |
| Max jitter | max(\|Δx\|) | Worst single variation |

### Frequency-Domain Analysis

**FFT Analysis:**
- Dominant frequency: peak in power spectrum
- Spectral entropy: measure of frequency concentration
- Total power: sum of all frequency components

**Autocorrelation:**
- Lag-1 autocorrelation: temporal dependence
- First zero-crossing: decorrelation time

### Jitter Sources

| Source | Frequency Range | Mitigation |
|--------|-----------------|------------|
| OS scheduling | 1-100 Hz | Kernel bypass, CPU pinning |
| Network congestion | 0.1-10 Hz | Dedicated lines, QoS |
| GC pauses | 0.01-1 Hz | No GC languages |
| Cache misses | 1000+ Hz | Cache-aware structures |
| Thermal throttling | 0.001-0.1 Hz | Thermal management |

---

## Determinism Metrics

### Core Metrics

| Metric | Formula | Ideal | Grade Ranges |
|--------|---------|-------|--------------|
| CV | σ/μ | 0 | <0.01 Excellent, 0.01-0.05 Very Good, 0.05-0.10 Good, 0.10-0.20 Acceptable, 0.20-0.50 Poor, >0.50 Unacceptable |
| Determinism Ratio | p50/p999 | 1.0 | <1.5 Excellent, 1.5-3.0 Very Good, 3.0-5.0 Good, 5.0-10.0 Acceptable, 10.0-50.0 Poor, >50.0 Unacceptable |
| Predictability Index | 1 - σ/p999 | 1.0 | Similar to CV |

### Composite Determinism Score

```
Score = 0.30 × (1 - CV_norm) + 0.30 × (1 - DR_norm) + 0.20 × (1 - Max_norm) + 0.20 × (1 - Jitter_norm)
```

Where each metric is min-max normalized to [0, 1].

---

## Availability Modeling

### Metrics

| Metric | Formula | Use |
|--------|---------|-----|
| Uptime % | (Total - Downtime) / Total × 100 | Overall availability |
| MTBF | Uptime / N_failures | Reliability |
| MTTR | Downtime / N_failures | Recoverability |

### Availability Tiers

| Tier | Downtime/Year | Use Case |
|------|---------------|----------|
| 99% | 3.65 days | Non-critical |
| 99.9% | 8.76 hours | Standard production |
| 99.99% | 52.6 minutes | ULL trading |
| 99.999% | 5.26 minutes | Mission-critical HFT |
| 99.9999% | 31.5 seconds | Theoretical optimum |

### High-Availability Patterns

| Pattern | Availability | MTTR | Cost |
|---------|-------------|------|------|
| Active-passive | 99.9% | Minutes | $$ |
| Active-active | 99.99% | Seconds | $$$ |
| N+1 redundancy | 99.999% | <1 second | $$$$ |
| Geographic redundancy | 99.9999% | <100 ms | $$$$$ |

---

## Cost Analysis

### Cost per Microsecond

```
Cost per μs (absolute) = Annual cost / Achieved latency (μs)
Cost per μs (marginal) = ΔCost / ΔLatency
```

### Cost per Trade

```
Cost per trade = Annual cost / Annual trades
All-in cost per trade = (Infrastructure + Personnel + Data + Facilities) / Annual trades
```

### ROI

```
Latency ROI = (Revenue_with - Revenue_without - Cost) / Cost × 100
Payback period = Cost / Annual revenue uplift
```

### TCO

```
TCO = CapEx + OpEx + Personnel + Data + Compliance + Decommissioning
```

With optional discounting:
```
TCO = CapEx + Σ(OpEx_t / (1 + r)^t) for t = 1 to N
```

---

## Regression & Change-Point Detection

### Trend Detection

**Linear Regression:**
```
latency = slope × time + intercept
```

- slope > 2×std_err: increasing trend
- slope < -2×std_err: decreasing trend
- otherwise: stable

### Change-Point Detection (CUSUM)

**Algorithm:**
1. Normalize samples: z = (x - μ) / σ
2. Compute CUSUM: S⁺ = max(0, S⁺ + z - k), S⁻ = max(0, S⁻ - z - k)
3. Flag change point when S⁺ > h or S⁻ > h
4. Reset CUSUM after detection

**Parameters:**
- k = 0.5 (slack parameter)
- h = 3.0 (threshold, in std devs)
- min_segment_size = 100 (minimum samples between change points)

### Regression Detection

Compare baseline vs current:

| Metric | Threshold | Action |
|--------|-----------|--------|
| p50 change | >5% | Investigate |
| p50 change | >20% | Major regression |
| p50 change | >50% | Critical regression |
| p99 change | >10% | Investigate tail |
| Mann-Whitney p | <0.05 | Statistically significant |

---

## Comparative Analysis

### Pairwise Comparison

For each pair of systems, compute:
- Mean, p50, p99, p999 for each system
- Difference and percent difference
- Welch's t-test
- Mann-Whitney U test
- Effect size (Cohen's d, Cliff's delta)

### Benchmark Ranking

**Weighted Composite Score:**

```
Score = w₁ × (1 - p50_norm) + w₂ × (1 - p99_norm) + w₃ × (1 - p999_norm) + w₄ × (1 - CV_norm)
```

Default weights: p50=0.3, p99=0.3, p999=0.2, CV=0.2

### Statistical Significance

| p-value | Significance |
|---------|--------------|
| <0.001 | *** |
| <0.01 | ** |
| <0.05 | * |
| ≥0.05 | ns |

---

## Machine Learning

### Anomaly Detection

#### IQR Method
```
Lower fence = Q1 - 1.5 × IQR
Upper fence = Q3 + 1.5 × IQR
Anomaly if x < lower or x > upper
```

#### Modified Z-Score (MAD-based)
```
Mᵢ = 0.6745 × (xᵢ - median) / MAD
Anomaly if |Mᵢ| > 3.5
```

#### Isolation Forest
```
1. Build T isolation trees
2. For each tree, randomly partition data
3. Path length = number of splits to isolate point
4. Anomaly score = 2^(-E(h) / c(n))
5. c(n) = 2×(ln(n-1) + 0.5772) - 2×(n-1)/n
```

### K-Means Clustering

**Use Case:** Identify latency modes (e.g., cache hit, cache miss, outlier)

**Algorithm:**
1. Initialize centroids using k-means++
2. Assign each point to nearest centroid
3. Update centroids as mean of assigned points
4. Repeat until convergence

**Output:**
- Cluster centroids
- Cluster sizes
- Within-cluster statistics

### Latency Prediction

**Models:**

| Model | Formula | Use |
|-------|---------|-----|
| Linear | y = β₀ + β₁x₁ + ... + βₙxₙ | Linear relationships |
| Polynomial | y = Σ βᵢxᵢ^d | Non-linear |
| Exponential | y = a × exp(b×x) | Multiplicative |

**Evaluation:**
- R² (coefficient of determination)
- Train/test split (80/20)
- Feature importance

### PCA (Dimensionality Reduction)

**Use Case:** Reduce multi-feature latency data to 2-3 dimensions for visualization

**Output:**
- Transformed data (n × k)
- Explained variance ratio
- Principal components

---

## Visualization

### Distribution Plots
- Histogram with fitted distributions
- CDF with percentile markers

### Time Series Plots
- Raw latency over time
- Trend line
- Rolling mean ± 1σ

### Comparison Plots
- Box plots
- Violin plots
- CDF comparison

### Heatmaps
- Time-of-day vs system
- Latency intensity

---

## Full Evaluation Pipeline

The `full_evaluation()` function runs all analyses:

```python
report = full_evaluation(samples, metadata={
    "system": "FPGA Feed Handler",
    "date": "2026-09-30",
    "load": "100K msg/s"
})
```

**Output includes:**
1. Descriptive statistics
2. Percentiles with CIs
3. Distribution fits
4. Jitter analysis
5. Determinism metrics
6. Trend detection
7. Change points
8. Anomaly detection (IQR + Z-score)
9. K-means clustering

---

## Implementation

### File Structure

```
evaluation/latency/
├── ull-latency-evaluation-framework.md  # Base framework (v1.0)
├── ull-statistical-ml-framework.md      # This document (v2.0)
└── ull_latency_ml.py                    # Python implementation
```

### Usage

```bash
# Demo with synthetic data
python ull_latency_ml.py --demo

# Analyze real data
python ull_latency_ml.py --input samples.txt --output report.json
```

### Python API

```python
from ull_latency_ml import (
    descriptive_statistics,
    compute_percentiles,
    fit_distributions,
    jitter_analysis,
    determinism_metrics,
    detect_trend,
    detect_change_points,
    anomaly_detection_iqr,
    anomaly_detection_zscore,
    kmeans_clustering,
    compare_systems,
    benchmark_ranking,
    full_evaluation,
)

# Load samples
samples = np.loadtxt("latency_samples.txt")

# Run full evaluation
report = full_evaluation(samples)

# Or run individual analyses
stats = descriptive_statistics(samples)
pcts = compute_percentiles(samples)
fits = fit_distributions(samples)
```

### Dependencies

- numpy >= 1.20
- scipy >= 1.7
- matplotlib >= 3.5 (optional, for visualization)

---

*Framework version 2.0 — 2026-09-30*
