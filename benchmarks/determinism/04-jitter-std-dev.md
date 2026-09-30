# Benchmark 4: Jitter Standard Deviation

**Metric:** σ_jitter = std_dev(|sample[i] - sample[i-1]|) — standard deviation of consecutive-sample differences

**What it measures:** The variability of the *change* in latency from one sample to the next. Low jitter σ means the latency is not just low on average, but also stable from sample to sample — no sudden jumps or oscillations.

**Why it matters:** Two systems can have identical mean and p99 latencies but very different jitter profiles. A system with low jitter is predictable: you can bound the latency with confidence. A system with high jitter is unpredictable — the next sample could be near the mean or far from it. Jitter σ captures this predictability.

---

## Measurement Methodology

### 1. Sample Collection

```
For each of N passes (N ≥ 3):
  1. Warm up: send/process 10,000 samples, discard
  2. Collect 10,000,000 raw latency samples (or 60s continuous, whichever is longer)
  3. Compute consecutive differences: d[i] = |sample[i] - sample[i-1]|
  4. Compute: mean(d), std_dev(d), jitter_σ = std_dev(d)
Report: median jitter_σ across all passes
```

### 2. Computation

```c
typedef struct {
    uint64_t prev_sample;
    int has_prev;
    // Welford's state for jitter
    welford_state_t welford;
} jitter_state_t;

void jitter_init(jitter_state_t *j) {
    j->has_prev = 0;
    j->prev_sample = 0;
    j->welford.count = 0;
    j->welford.mean = 0.0;
    j->welford.M2 = 0.0;
}

// Called for every sample
static inline void jitter_update(jitter_state_t *j, uint64_t sample) {
    if (j->has_prev) {
        uint64_t diff = (sample > j->prev_sample)
                        ? (sample - j->prev_sample)
                        : (j->prev_sample - sample);
        welford_update(&j->welford, (double)diff);
    }
    j->prev_sample = sample;
    j->has_prev = 1;
}

double jitter_sigma(const jitter_state_t *j) {
    if (j->welford.count < 2) return 0.0;
    double variance = j->welford.M2 / (j->welford.count - 1);
    return sqrt(variance);
}
```

### 3. Alternative: Mean Absolute Jitter (MAJ)

Some practitioners prefer mean absolute deviation over standard deviation for robustness:

```c
// Mean Absolute Jitter — more robust to outliers than σ
double compute_maj(const uint64_t *samples, size_t n) {
    if (n < 2) return 0.0;
    long double sum = 0.0;
    for (size_t i = 1; i < n; i++) {
        uint64_t diff = (samples[i] > samples[i-1])
                        ? (samples[i] - samples[i-1])
                        : (samples[i-1] - samples[i]);
        sum += (long double)diff;
    }
    return (double)(sum / (n - 1));
}
```

### 4. Jitter vs. Other Metrics

| Metric | Measures | Sensitive To |
|--------|----------|--------------|
| CV (σ/μ) | Overall spread | All samples equally |
| p99/p50 | Tail behavior | Upper tail only |
| Max | Single worst sample | One extreme outlier |
| **Jitter σ** | Consecutive variability | Sample-to-sample transitions |

### 5. Critical Measurement Rules

| Rule | Rationale |
|------|-----------|
| Use absolute differences | Signed differences would cancel out (up-down-up-down = 0) |
| Report both σ and MAJ | σ is standard but outlier-sensitive; MAJ is robust but less conventional |
| Use Welford's algorithm | Numerically stable, single pass, no storage of all differences |
| Consider jitter of jitter | σ of consecutive jitter values reveals meta-instability |
| Separate periodic from random jitter | Use FFT on the difference sequence to identify periodic components |

---

## Hardware Requirements

| Component | Minimum | Recommended | Why |
|-----------|---------|-------------|-----|
| CPU | Intel Xeon Scalable (Skylake+) | Intel Xeon 6 / AMD EPYC 9004 | Invariant TSC, consistent instruction timing |
| Cache | ≥ 32 MB L3 | ≥ 64 MB L3 | No cache misses during measurement |
| Memory | DDR4-3200, `mlockall()` | DDR5-4800, 1 GB hugepages | Memory latency consistency |
| NIC | FPGA-based with hardware timestamping | Purpose-built ULL NIC | Hardware timestamps have lower jitter than software |
| PCIe | Gen4 x16 dedicated | Gen5 x16 dedicated | DMA timing consistency |
| Power | `performance` governor | BIOS C-state disable | C-state transitions cause 10–100 µs jitter spikes |
| Clock | Invariant TSC | `tsc=reliable` | TSC must be consistent across cores |
| Interrupt controller | MSI-X with isolated affinity | No legacy INTx | Shared interrupts cause jitter |
| Motherboard | No shared PCIe root complex | Dedicated root complex | Shared DMA causes jitter |

---

## Software Requirements

| Layer | Requirement | Configuration |
|-------|-------------|---------------|
| Kernel boot | Core isolation | `isolcpus=2-7 nohz_full=2-7 rcu_nocbs=2-7` |
| Kernel boot | Disable C-states | `processor.max_cstate=1 intel_idle.max_cstate=0` |
| Kernel boot | Disable P-states | `intel_pstate=disable` or `amd_pstate=disable` |
| Kernel boot | Hugepages | `default_hugepagesz=1G hugepagesz=1G hugepages=4` |
| IRQ affinity | Exclude measurement cores | `echo 0-1 > /proc/irq/default_smp_affinity` |
| Scheduler | Real-time priority | `SCHED_FIFO` priority 99 |
| Memory | Lock pages | `mlockall(MCL_CURRENT \| MCL_FUTURE)` |
| Clock | Raw monotonic | `clock_gettime(CLOCK_MONOTONIC_RAW, ...)` |
| Compiler | Optimization | `-O3 -march=native` |
| Linker | No lazy binding | `-Wl,-z,now` |
| NUMA | Single-node | `numactl --membind=0 --cpunodebind=0` |
| Syscall | Avoid during measurement | No `malloc`, `printf`, `write` in hot path |

---

## Interpretation Guide

| Jitter σ | Determinism Grade | Typical Deployment |
|----------|-------------------|-------------------|
| < 5 ns | Excellent | Full FPGA tick-to-trade |
| 5 – 20 ns | Very Good | FPGA feed handler + CPU strategy |
| 20 – 100 ns | Good | Kernel bypass (DPDK/Onload) |
| 100 – 500 ns | Acceptable | Tuned kernel bypass |
| 500 ns – 2 µs | Poor | Standard kernel stack |
| > 2 µs | Unacceptable | Untuned/virtualized environment |

### Common Pitfalls

- **Jitter σ vs. absolute jitter:** Jitter σ is in the same units as latency (ns, µs). A jitter σ of 50 ns on a 200 ns mean is 25% — high. On a 10 µs mean, it's 0.5% — low. Always consider jitter σ relative to mean latency.
- **Periodic jitter:** If the difference sequence has a strong periodic component (e.g., from a 1 kHz timer interrupt), jitter σ will be high even if the system is otherwise stable. Use FFT to identify and eliminate periodic sources.
- **Jitter of jitter:** High jitter σ with low CV can indicate a system that is mostly stable but has occasional bursts. Compute jitter σ of the jitter sequence to detect this.
- **Measurement rate dependence:** Jitter σ depends on the sampling rate. A system sampled at 1 MHz will show different jitter than the same system sampled at 10 MHz. Always report the sampling rate.
- **Warm-up contamination:** The first few differences after warm-up may be artificially large. Discard the first 1,000 differences after warm-up.
