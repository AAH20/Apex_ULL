# ULL Determinism Evaluation Framework

**Version:** 1.0  
**Date:** 2026-09-29  
**Scope:** Ultra-low-latency infrastructure determinism metrics, measurement methodology, benchmark standards, and industry averages.

---

## Table of Contents

1. [Overview](#overview)
2. [Metric 1: Coefficient of Variation (CV)](#1-coefficient-of-variation-cv)
3. [Metric 2: p99/p50 Ratio](#2-p99p50-ratio)
4. [Metric 3: Max Latency](#3-max-latency)
5. [Metric 4: Jitter Standard Deviation](#4-jitter-standard-deviation)
6. [Composite Determinism Score](#composite-determinism-score)
7. [Measurement Protocol](#measurement-protocol)
8. [Implementation](#implementation)
9. [Sources](#sources)

---

## Overview

Determinism in ultra-low-latency (ULL) systems is the degree to which latency is predictable and repeatable. Unlike raw speed (mean latency), determinism captures the *consistency* of the system — critical for HFT, real-time control, and safety-critical applications where tail behavior matters more than averages.

This framework defines four complementary metrics, each capturing a different dimension of determinism:

| Metric | What It Measures | Ideal Value | Primary Use Case |
|--------|-----------------|-------------|------------------|
| Coefficient of Variation | Relative spread of all samples | → 0 | Overall system stability |
| p99/p50 Ratio | Tail latency severity | 1.0 | SLA/SLO compliance |
| Max Latency | Absolute worst case | As low as possible | Hard real-time guarantees |
| Jitter Std Dev | Inter-sample variability | → 0 | Network/pipeline stability |

---

## 1. Coefficient of Variation (CV)

### Definition

```
CV = σ / μ
```

Where:
- **σ** = population standard deviation of latency samples
- **μ** = mean latency

CV is dimensionless, enabling comparison across systems with different absolute latencies.

### Measurement Methodology

1. **Sample collection**: Record ≥10,000 latency measurements under steady-state load.
2. **Warm-up**: Discard first 1% of samples (JIT, cache warm-up, connection establishment).
3. **Steady-state window**: Use samples after warm-up, during constant load.
4. **Calculation**:
   - Compute mean: `μ = (1/N) Σ xᵢ`
   - Compute std dev: `σ = √[(1/N) Σ (xᵢ - μ)²]`
   - Compute CV: `CV = σ / μ`
5. **Reporting**: Report CV as a percentage (×100) and raw ratio.

### Benchmark Standards

| Grade | CV Range | Interpretation |
|-------|----------|----------------|
| **Excellent** | < 0.01 (1%) | FPGA-grade determinism; hardware-level consistency |
| **Very Good** | 0.01 – 0.05 (1–5%) | Kernel-bypass with proper tuning (DPDK, RDMA) |
| **Good** | 0.05 – 0.10 (5–10%) | Well-tuned software stack, isolated cores |
| **Acceptable** | 0.10 – 0.20 (10–20%) | Standard kernel bypass without full isolation |
| **Poor** | 0.20 – 0.50 (20–50%) | Standard OS networking, shared infrastructure |
| **Unacceptable** | > 0.50 (>50%) | Unsuitable for ULL; investigate immediately |

### Industry Averages

| System Type | Typical CV | Source |
|-------------|-----------|--------|
| FPGA tick-to-trade | 0.001 – 0.01 | IEEE 2024; Algo-Logic T2T benchmarks |
| Kernel bypass (DPDK/Onload) | 0.02 – 0.08 | DPDK perf reports; HFT firm disclosures |
| RDMA (RoCE v2) | 0.03 – 0.10 | NVIDIA ConnectX benchmarks |
| InfiniBand NDR | 0.01 – 0.05 | HPC MPI latency studies |
| Standard kernel TCP | 0.15 – 0.40 | Cloud latency studies |
| Virtualized/cloud networking | 0.20 – 0.60 | AWS/GCP latency variability reports |
| Wireless (microwave) | 0.05 – 0.15 | HFT microwave link measurements |

### Interpretation Guide

- **CV < 0.01**: Latency is essentially fixed; the system behaves like a hardware circuit. Typical of FPGA pipelines with fixed clock-cycle processing.
- **CV 0.01–0.05**: Minor variability from OS scheduling, cache misses, or interrupt handling. Achievable with kernel bypass + CPU isolation.
- **CV 0.05–0.15**: Noticeable jitter; may cause SLA violations in sub-microsecond systems. Requires investigation.
- **CV > 0.15**: High variability; unsuitable for latency-critical paths. Indicates contention, shared resources, or insufficient isolation.

---

## 2. p99/p50 Ratio

### Definition

```
p99/p50 Ratio = P99 latency / P50 latency
```

Where:
- **P50** = median latency (50th percentile)
- **P99** = 99th percentile latency (99% of samples are below this value)

This ratio measures tail latency severity — how much worse the "bad" requests are compared to the typical case.

### Measurement Methodology

1. **Sample collection**: Record ≥100,000 latency measurements (larger sample needed for stable tail percentiles).
2. **Sorting**: Sort all samples in ascending order.
3. **Percentile extraction**:
   - P50: value at index `⌊0.50 × N⌋`
   - P99: value at index `⌊0.99 × N⌋`
4. **Ratio calculation**: `ratio = P99 / P50`
5. **Confidence**: For p99 stability, N should be ≥100,000. For p99.9, N ≥ 1,000,000.

### Benchmark Standards

| Grade | p99/p50 Range | Interpretation |
|-------|---------------|----------------|
| **Excellent** | 1.0 – 1.5 | Near-perfect determinism; tail ≈ median |
| **Very Good** | 1.5 – 3.0 | Mild tail inflation; typical of tuned ULL systems |
| **Good** | 3.0 – 5.0 | Moderate tail; acceptable for most ULL applications |
| **Acceptable** | 5.0 – 10.0 | Significant tail; may violate tight SLAs |
| **Poor** | 10.0 – 50.0 | Severe tail latency; requires optimization |
| **Unacceptable** | > 50.0 | Catastrophic tail behavior; unsuitable for ULL |

### Industry Averages

| System Type | Typical p99/p50 | Source |
|-------------|-----------------|--------|
| FPGA wire-to-wire | 1.01 – 1.10 | Algo-Logic, CSPi benchmarks |
| Kernel bypass (DPDK) | 1.5 – 4.0 | DPDK RTCP benchmark (median 7.07 µs, max 12.2 µs → ratio ~1.7) |
| RDMA (RoCE v2) | 2.0 – 5.0 | NVIDIA RoCE latency studies |
| InfiniBand NDR | 1.5 – 3.0 | HPC cluster benchmarks |
| SPDK NVMe-oF | 2.0 – 4.0 | SPDK perf report (avg 28.44 µs, p99 56.7 µs → ratio ~2.0) |
| Standard kernel TCP | 5.0 – 20.0 | Cloud latency studies |
| Cloud (AWS/GCP) | 10.0 – 100.0 | Cloud provider latency reports |
| DPU (BlueField-3) | 1.2 – 2.5 | NVIDIA DPU benchmarks |

### Interpretation Guide

- **Ratio ≈ 1.0**: Every request takes the same time. Only achievable in pure hardware (FPGA/ASIC) with fixed pipeline depth.
- **Ratio 1.5–3.0**: The "gold standard" for software ULL systems. Achievable with kernel bypass, CPU isolation, and careful tuning.
- **Ratio 3.0–10.0**: Common in production systems. May be acceptable depending on SLA requirements.
- **Ratio > 10.0**: Indicates fundamental issues — buffer contention, interrupt storms, or resource sharing.

---

## 3. Max Latency

### Definition

```
Max Latency = max(x₁, x₂, ..., xₙ)
```

The single worst latency observed during the measurement window. Represents the absolute worst-case behavior.

### Measurement Methodology

1. **Sample collection**: Record all latency measurements during the test window.
2. **Window selection**: Max latency is highly sensitive to window length. Define the window explicitly:
   - **Short window** (1M samples): Captures transient spikes
   - **Long window** (1B+ samples): Captures rare events (GC pauses, page faults, thermal throttling)
3. **Reporting**: Always report max latency alongside the sample count and time window.
4. **Context**: Report the top-N max values (e.g., top 10) to distinguish single outliers from systematic issues.

### Benchmark Standards

| Grade | Max Latency (relative to median) | Interpretation |
|-------|----------------------------------|----------------|
| **Excellent** | < 2× median | No significant outliers |
| **Very Good** | 2 – 5× median | Minor outliers, well-controlled |
| **Good** | 5 – 10× median | Some outliers; acceptable for most ULL |
| **Acceptable** | 10 – 50× median | Noticeable outliers; investigate causes |
| **Poor** | 50 – 100× median | Severe outliers; likely systematic issue |
| **Unacceptable** | > 100× median | Catastrophic; system unsuitable for ULL |

### Industry Averages

| System Type | Typical Max Latency | Median | Max/Median Ratio |
|-------------|---------------------|--------|-------------------|
| FPGA tick-to-trade | 500 ns | 480 ns | ~1.04 |
| Kernel bypass (DPDK) | 12.2 µs | 7.07 µs | ~1.7 |
| RDMA (RoCE v2) | 5 µs | 2 µs | ~2.5 |
| InfiniBand NDR | 3 µs | 1.5 µs | ~2.0 |
| SPDK NVMe-oF | 165.5 µs (p99.999) | 28.44 µs | ~5.8 |
| Standard kernel TCP | 500 µs | 50 µs | ~10 |
| Cloud networking | 50 ms | 5 ms | ~10 |

### Interpretation Guide

- **Max < 2× median**: Exceptional. Indicates a tightly controlled environment with no interference.
- **Max 2–5× median**: Normal for well-tuned ULL systems. Occasional cache misses or interrupt handling.
- **Max 5–20× median**: Common in production. May indicate occasional OS interference or contention.
- **Max > 20× median**: Requires investigation. Common causes: page faults, context switches, GC pauses, thermal throttling, or interrupt storms.

### Key Consideration

Max latency is the least statistically robust metric — a single outlier can dominate. Always report it alongside:
- Sample count
- Time window
- Top-10 max values
- Whether the max is a one-off or recurring

---

## 4. Jitter Standard Deviation

### Definition

Jitter is the variation in inter-arrival or inter-departure times. Jitter standard deviation quantifies this variation.

For latency samples `x₁, x₂, ..., xₙ`:

```
Jitterᵢ = xᵢ - xᵢ₋₁   (for i = 2, ..., n)
Jitter Std Dev = σ_jitter = √[(1/(N-1)) Σ (Jitterᵢ - μ_jitter)²]
```

Where:
- **μ_jitter** = mean of jitter values (≈ 0 for stationary processes)
- **Jitter Std Dev** = standard deviation of the first differences

### Measurement Methodology

1. **Sample collection**: Record latency samples in chronological order (preserving sequence).
2. **First difference**: Compute `Jitterᵢ = xᵢ - xᵢ₋₁` for all consecutive pairs.
3. **Statistics**: Compute mean and standard deviation of the jitter series.
4. **Alternative (RJitter)**: Some frameworks use the smoothed jitter from RFC 3550 (RTP):
   ```
   Jitterᵢ = Jitterᵢ₋₁ + (|xᵢ - xᵢ₋₁| - Jitterᵢ₋₁) / 16
   ```
   This provides an exponentially-weighted moving average of jitter.

### Benchmark Standards

| Grade | Jitter Std Dev (absolute) | Interpretation |
|-------|---------------------------|----------------|
| **Excellent** | < 10 ns | FPGA-grade; hardware-level consistency |
| **Very Good** | 10 – 100 ns | Kernel bypass with proper tuning |
| **Good** | 100 ns – 1 µs | Well-tuned software stack |
| **Acceptable** | 1 – 10 µs | Standard kernel bypass |
| **Poor** | 10 – 100 µs | Standard OS networking |
| **Unacceptable** | > 100 µs | Unsuitable for ULL |

### Industry Averages

| System Type | Typical Jitter Std Dev | Source |
|-------------|----------------------|--------|
| FPGA wire-to-wire | 1 – 10 ns | Fixed clock-cycle processing |
| Kernel bypass (DPDK) | 50 – 500 ns | DPDK RTCP benchmark (jitter 52.6 µs max, but std dev much lower) |
| RDMA (RoCE v2) | 100 ns – 1 µs | NVIDIA RoCE benchmarks |
| InfiniBand NDR | 50 – 200 ns | HPC cluster studies |
| SPDK NVMe-oF | 1 – 10 µs | SPDK perf reports |
| Standard kernel TCP | 10 – 100 µs | Cloud latency studies |
| Cloud networking | 1 – 10 ms | Cloud provider reports |

### Interpretation Guide

- **Jitter Std Dev < 100 ns**: Excellent. The system produces latencies in a very tight band. Suitable for sub-microsecond ULL.
- **Jitter Std Dev 100 ns – 1 µs**: Good. Minor variability from software processing. Acceptable for most ULL applications.
- **Jitter Std Dev 1 – 10 µs**: Moderate. Noticeable variability; may cause issues in tight SLA environments.
- **Jitter Std Dev > 10 µs**: High variability. Indicates significant interference or contention.

### Relationship to CV

Jitter std dev and CV are related but distinct:
- **CV** measures total spread relative to mean (includes both random and systematic variation)
- **Jitter std dev** measures frame-to-frame variation (captures temporal correlation)

A system can have low CV but high jitter std dev (e.g., a slowly drifting latency) or high CV but low jitter std dev (e.g., a bimodal distribution with stable modes).

---

## Composite Determinism Score

For a single-number determinism rating, combine all four metrics:

```
Determinism Score = w₁ × (1 - CV_norm) + w₂ × (1 - p99p50_norm) + w₃ × (1 - Max_norm) + w₄ × (1 - Jitter_norm)
```

Where each metric is normalized to [0, 1] using min-max scaling against the benchmark ranges above, and weights sum to 1.0.

### Recommended Weights

| Weight | Value | Rationale |
|--------|-------|-----------|
| w₁ (CV) | 0.30 | Most comprehensive single metric |
| w₂ (p99/p50) | 0.30 | Critical for SLA compliance |
| w₃ (Max) | 0.20 | Important but less statistically robust |
| w₄ (Jitter) | 0.20 | Captures temporal stability |

### Score Interpretation

| Score | Grade | Action |
|-------|-------|--------|
| 0.90 – 1.00 | A (Excellent) | Production-ready for the most demanding ULL |
| 0.80 – 0.89 | B (Very Good) | Production-ready for ULL |
| 0.70 – 0.79 | C (Good) | Acceptable for most ULL; monitor closely |
| 0.60 – 0.69 | D (Acceptable) | Marginal; optimization recommended |
| 0.00 – 0.59 | F (Poor) | Not suitable for ULL; significant work needed |

---

## Measurement Protocol

### Pre-Conditions

1. **System under test**: Document hardware, OS, kernel version, driver versions, BIOS settings.
2. **Workload**: Define the traffic pattern (message size, rate, distribution).
3. **Duration**: Minimum 10 minutes steady-state per test run.
4. **Repetitions**: Minimum 3 runs; report mean and std dev across runs.
5. **Isolation**: Disable CPU frequency scaling, hyperthreading, and power management.
6. **Environment**: Record temperature, other tenants (if cloud), and background processes.

### Test Procedure

```
1. Warm-up: 60 seconds (discard all samples)
2. Baseline: 10 minutes idle measurement
3. Load test: 10 minutes under target load
4. Recovery: 10 minutes post-load measurement
5. Repeat steps 2-4 for 3 runs
```

### Data Collection

- **Timestamp**: Use `CLOCK_MONOTONIC_RAW` or `rdtsc` for nanosecond resolution
- **Sample size**: ≥100,000 samples per run for p99 stability
- **Storage**: Store raw samples (not just aggregates) for post-hoc analysis

### Reporting Template

```
=== Determinism Evaluation Report ===
Date: 2026-09-29
System: [hardware/software config]
Workload: [traffic pattern]
Samples: [N] over [duration]

--- Metric Results ---
                    Run 1    Run 2    Run 3    Mean     Std Dev
CV (ratio):         0.0xx    0.0xx    0.0xx    0.0xx    0.0xx
p99/p50 ratio:      x.xx     x.xx     x.xx     x.xx     x.xx
Max latency (ns):   xxx      xxx      xxx      xxx      xxx
Jitter std dev:     xx ns    xx ns    xx ns    xx ns    xx ns

--- Composite Score ---
Determinism Score: 0.xx (Grade: X)
```

---

## Implementation

See `determinism_metrics.py` for a Python implementation of all four metrics plus the composite score.

```bash
python determinism_metrics.py --input latency_samples.txt --output report.json
```

---

## Sources

- IEEE 2024 FPGA for HFT study (480 ns average latency benchmark)
- Algo-Logic Systems CME T2T press release (sub-µs wire-to-wire)
- CSPi Tick-to-Trade latency benchmark (1.538 µs mean)
- DPDK Performance Reports (RTCP-DPDK: avg 27.7 µs, max 75.8 µs, jitter 52.6 µs)
- SPDK NVMe-oF Performance Report 22.01 (avg 28.44 µs, p99 56.7 µs, p99.999 165.5 µs)
- NVIDIA ConnectX-7 NDR benchmarks
- NVIDIA BlueField-3 DPU benchmarks (p99 latency reduction 4×)
- HFT firm disclosures (Citadel, Jump, HRT, Optiver, IMC, Tower)
- Cloud provider latency studies (AWS, GCP)
- RFC 3550 (RTP jitter calculation)

---

*Framework version 1.0 — 2026-09-29*
