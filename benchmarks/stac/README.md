# STAC Benchmark Suite

Ultra-low-latency infrastructure benchmark suite based on STAC (Securities Technology Analysis Center) methodology.

## Benchmarks

| ID | Name | Description | Reference p50 |
|----|------|-------------|---------------|
| **STAC-M1** | Feed Handling | Parse, normalize, and update order book for a single market data tick | 500 ns |
| **STAC-M2** | Messaging Middleware | Round-trip message latency through messaging middleware | 2,000 ns |
| **STAC-M3** | Tick Analytics | VWAP, SMA, and volatility computation on tick stream | 1,200 ns |
| **STAC-A2** | Risk Computation | Pre-trade risk checks (position, notional, Greeks) | 500 ns |
| **STAC-T0** | Network I/O | Packet send/receive latency | 1,000 ns |
| **STAC-T1** | Tick-to-Trade | End-to-end latency from tick reception to order send | 500 ns |

## Quick Start

```bash
# Run all benchmarks
python benchmarks/stac/run_all.py

# Quick mode (fewer iterations)
python benchmarks/stac/run_all.py --quick

# Run single benchmark
python benchmarks/stac/run_all.py --benchmark STAC-M1

# Save results to JSON
python benchmarks/stac/run_all.py --output results.json

# Save current results as baselines for future regression detection
python benchmarks/stac/run_all.py --save-baseline

# Compare against saved baselines
python benchmarks/stac/run_all.py --baseline-dir baselines/
```

## Running Individual Benchmarks

```bash
cd benchmarks/stac
python stac_m1_feed_handling/benchmark.py
python stac_m2_messaging_middleware/benchmark.py
python stac_m3_tick_analytics/benchmark.py
python stac_a2_risk_computation/benchmark.py
python stac_t0_network_io/benchmark.py
python stac_t1_tick_to_trade/benchmark.py
```

## Scoring Model

Each benchmark produces a multi-dimensional composite score with five components:

| Component | Weight Range | Description |
|-----------|-------------|-------------|
| **Latency (p50)** | 30-40% | Median latency vs. reference |
| **Throughput** | 15-30% | Operations per second vs. reference |
| **Jitter** | 5-10% | Mean absolute deviation between consecutive samples |
| **Tail Latency (p99)** | 15-20% | 99th percentile latency vs. reference |
| **Consistency (CV)** | 15-20% | Coefficient of variation (stddev/mean) |

### Grade Classification

| Grade | Score Range | Label |
|-------|-------------|-------|
| A+ | ≥ 2.0 | Exceptional |
| A | ≥ 1.5 | Excellent |
| A- | ≥ 1.2 | Very Good |
| B+ | ≥ 1.0 | Good |
| B | ≥ 0.8 | Acceptable |
| B- | ≥ 0.6 | Below Average |
| C+ | ≥ 0.4 | Poor |
| C | ≥ 0.2 | Very Poor |
| D | ≥ 0.1 | Bad |
| F | < 0.1 | Failing |

Score interpretation:
- `1.0` = meets reference latency (FPGA-class performance)
- `>1.0` = exceeds reference (faster than reference)
- `<1.0` = below reference (slower than reference)

## Statistical Analysis

All benchmarks report comprehensive statistical metrics:

### Latency Distribution
- min, max, mean, stddev
- Percentiles: p50, p90, p99, p99.9, p99.99
- Jitter: mean absolute deviation between consecutive samples

### Statistical Measures
- **CV (Coefficient of Variation)**: stddev/mean, measures relative variability
- **Skewness**: asymmetry of the latency distribution
- **Kurtosis**: tail heaviness (excess kurtosis, Fisher definition)
- **Confidence Intervals**: 95% and 99% CI for the mean
- **Outlier Detection**: IQR method (1.5 × IQR beyond Q1/Q3)

### Histogram
Each benchmark generates histogram data (20 bins by default) for visualization.

## Sub-Stage Timing

Each benchmark measures per-stage latency breakdown:

| Benchmark | Stages |
|-----------|--------|
| STAC-M1 | parse → normalize → book_update |
| STAC-M2 | send → receive |
| STAC-M3 | window_update → return_calc → analytics |
| STAC-A2 | position_check → notional_check → fat_finger → greeks |
| STAC-T0 | send → receive |
| STAC-T1 | tick_processing → signal_generation → order_encoding → risk_check → order_send |

## Regression Detection

The suite supports baseline comparison and regression detection:

```bash
# Save current results as baselines
python run_all.py --save-baseline

# Compare against baselines
python run_all.py --baseline-dir baselines/
```

Regression analysis reports:
- Per-metric percentage change (p50, p99, mean, stddev, jitter, throughput, score)
- Direction classification: improved / regressed / unchanged
- Severity classification: none / minor / moderate / major / critical
- Overall status: improved / regressed / unchanged / mixed

## Comparative Analysis

When running all benchmarks, the suite automatically generates:
- Cross-benchmark comparison table
- Rankings by latency, throughput, score, and efficiency
- Relative performance ratios
- Efficiency frontier (Pareto optimal benchmarks)
- Radar chart data for visualization
- Bottleneck analysis
- Optimization recommendations

## Metrics

All benchmarks report:
- Latency: min, max, mean, stddev, p50, p90, p99, p99.9, p99.99 (nanoseconds)
- Throughput: operations per second
- Jitter: mean absolute deviation between consecutive samples
- CV, skewness, kurtosis
- 95% and 99% confidence intervals
- Outlier count and percentage
- Histogram data (20 bins)

## Reference Values

Reference latencies are derived from published research on ultra-low-latency trading systems:

| Technology | Typical Latency | Source |
|------------|-----------------|--------|
| FPGA feed handler | 200-500 ns | IEEE 2024 study |
| Kernel bypass (DPDK) | 1-5 μs | DPDK benchmarks |
| RDMA round-trip | 1-3 μs | ConnectX-3/7 benchmarks |
| Standard kernel stack | 10-50 μs | Typical measurements |
| Full FPGA tick-to-trade | 150-500 ns | Algo-Logic, CSPi |

## Project Structure

```
benchmarks/stac/
├── common/
│   ├── __init__.py
│   ├── harness.py          # Timing, statistics, scoring, histogram
│   ├── metrics.py          # Metric definitions, statistical summary
│   ├── regression.py       # Baseline comparison, trend analysis
│   └── comparative.py      # Cross-benchmark comparison, ranking
├── stac_m1_feed_handling/
│   └── benchmark.py
├── stac_m2_messaging_middleware/
│   └── benchmark.py
├── stac_m3_tick_analytics/
│   └── benchmark.py
├── stac_a2_risk_computation/
│   └── benchmark.py
├── stac_t0_network_io/
│   └── benchmark.py
├── stac_t1_tick_to_trade/
│   └── benchmark.py
├── run_all.py              # Unified runner with regression & comparison
└── README.md
```

## Environment

Benchmarks report system information (CPU, platform, Python version) for reproducibility. For production benchmarking, use:
- CPU core isolation (`isolcpus`, `nohz_full`)
- Hugepages configuration
- Real-time kernel (optional)
- Kernel bypass networking (DPDK/Onload)
