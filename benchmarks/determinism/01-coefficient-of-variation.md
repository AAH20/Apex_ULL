# Benchmark 1: Coefficient of Variation (CV)

**Metric:** CV = σ / μ (standard deviation / mean)

**What it measures:** Relative spread of the latency distribution. A CV of 0 means every sample is identical (perfect determinism). Higher CV means more variability relative to the mean.

**Why it matters:** CV normalizes variability against the mean, making it comparable across systems with different absolute latencies. A 100 ns σ on a 200 ns mean (CV=0.5) is far less deterministic than 100 ns σ on a 10 µs mean (CV=0.01).

---

## Measurement Methodology

### 1. Sample Collection

```
For each of N passes (N ≥ 3):
  1. Warm up: send/process 10,000 samples, discard
  2. Collect 10,000,000 raw latency samples (or 60s continuous, whichever is longer)
  3. Store samples in a pre-allocated, cache-aligned array
  4. Record: mean (μ), standard deviation (σ), CV = σ/μ
Report: median CV across all passes
```

### 2. Computation

```c
// Two-pass algorithm (numerically stable)
double compute_cv(const uint64_t *samples, size_t n) {
    // Pass 1: mean
    long double sum = 0.0;
    for (size_t i = 0; i < n; i++)
        sum += (long double)samples[i];
    double mean = (double)(sum / n);

    // Pass 2: variance (Welford's algorithm preferred for streaming)
    long double sq_sum = 0.0;
    for (size_t i = 0; i < n; i++) {
        long double diff = (long double)samples[i] - mean;
        sq_sum += diff * diff;
    }
    double variance = (double)(sq_sum / (n - 1));  // sample variance
    double stddev = sqrt(variance);

    return stddev / mean;
}
```

### 3. Welford's Online Algorithm (Preferred for Streaming)

```c
typedef struct {
    size_t count;
    double mean;
    double M2;  // sum of squares of differences from mean
} welford_state_t;

void welford_update(welford_state_t *s, double x) {
    s->count++;
    double delta = x - s->mean;
    s->mean += delta / s->count;
    double delta2 = x - s->mean;
    s->M2 += delta * delta;
}

double welford_cv(const welford_state_t *s) {
    if (s->count < 2) return 0.0;
    double variance = s->M2 / (s->count - 1);
    return sqrt(variance) / s->mean;
}
```

### 4. Critical Measurement Rules

| Rule | Rationale |
|------|-----------|
| Use `CLOCK_MONOTONIC_RAW` | Immune to NTP frequency adjustments |
| Record in nanoseconds as `uint64_t` | Avoid floating-point in hot path |
| Pre-allocate sample array | `malloc` during measurement introduces jitter |
| Pin thread to isolated core | Migration causes 10–100 µs spikes |
| Disable CPU frequency scaling | Turbo/transition causes bimodal distribution |
| Use `rdtsc` directly if TSC invariant | `clock_gettime` adds 20–40 ns overhead |

---

## Hardware Requirements

| Component | Minimum | Recommended | Why |
|-----------|---------|-------------|-----|
| CPU | Intel Xeon Scalable (Skylake+) | Intel Xeon 6 / AMD EPYC 9004 | Invariant TSC required |
| TSC | Invariant TSC (`constant_tsc` + `nonstop_tsc`) | `tsc=reliable` kernel parameter | TSC must not vary across cores or C-states |
| Core isolation | `isolcpus=` kernel parameter | `isolcpus` + `nohz_full` + `rcu_nocbs` | Eliminates scheduler/RCU interrupts |
| Memory | DDR4-3200, `mlockall()` | DDR5-4800, 1 GB hugepages | Page faults cause multi-µs spikes |
| PCIe | Dedicated root complex for NIC | No shared root complex | DMA contention adds jitter |
| Power | `performance` governor | BIOS C-state disable, locked frequency | P-state/C-state transitions cause bimodal latency |
| Cooling | Adequate for sustained max clock | Sub-ambient (LN2 for extreme) | Thermal throttling causes periodic spikes |

---

## Software Requirements

| Layer | Requirement | Configuration |
|-------|-------------|---------------|
| Kernel boot | Core isolation | `isolcpus=2-7 nohz_full=2-7 rcu_nocbs=2-7` |
| Kernel boot | Disable P-states | `intel_pstate=disable` or `amd_pstate=disable` |
| Kernel boot | TSC reliability | `tsc=reliable` |
| Kernel boot | Hugepages | `default_hugepagesz=1G hugepagesz=1G hugepages=4` |
| IRQ affinity | Exclude measurement cores | `echo 0-1 > /proc/irq/default_smp_affinity` |
| Scheduler | Real-time priority | `SCHED_FIFO` priority 99 |
| Memory | Lock pages | `mlockall(MCL_CURRENT \| MCL_FUTURE)` |
| Memory | Pre-fault stack | Touch all stack pages before measurement |
| Clock | Raw monotonic | `clock_gettime(CLOCK_MONOTONIC_RAW, ...)` |
| Compiler | Optimization | `-O3 -march=native -fno-omit-frame-pointer` |
| Linker | No lazy binding | `-Wl,-z,now` (prevent PLT resolution during measurement) |

---

## Interpretation Guide

| CV Range | Determinism Grade | Typical Deployment |
|----------|-------------------|-------------------|
| < 0.01 | Excellent | Full FPGA tick-to-trade |
| 0.01 – 0.05 | Very Good | FPGA feed handler + CPU strategy |
| 0.05 – 0.10 | Good | Kernel bypass (DPDK/Onload) |
| 0.10 – 0.20 | Acceptable | Tuned kernel bypass |
| 0.20 – 0.50 | Poor | Standard kernel stack |
| > 0.50 | Unacceptable | Untuned/virtualized environment |

### Common Pitfalls

- **Bimodal distribution:** CV > 0.5 often indicates two distinct latency populations (e.g., cached vs. uncached, turbo vs. base clock). Investigate with a histogram before optimizing.
- **Outlier sensitivity:** CV is sensitive to outliers. A single 100 µs spike in 10M samples can dominate σ. Consider reporting CV both with and without outliers (trimmed CV).
- **Sample size:** CV estimates converge slowly. Use ≥ 10M samples for stable estimates (95% CI on CV ≈ ±0.001 for well-behaved distributions).
