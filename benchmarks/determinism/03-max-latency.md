# Benchmark 3: Max Latency

**Metric:** max(samples) — the single highest latency sample observed

**What it measures:** The absolute worst-case latency over the entire measurement window. Unlike p99, which is a statistical measure, max is a single point — the one sample that represents the system's worst behavior.

**Why it matters:** In ULL systems, a single 100 µs spike can cause a missed trade, a stale quote, or a regulatory violation. Max latency is the "never exceed" bound that systems must be designed to meet. It is the most conservative determinism metric.

---

## Measurement Methodology

### 1. Sample Collection

```
For each of N passes (N ≥ 3):
  1. Warm up: send/process 10,000 samples, discard
  2. Collect 10,000,000 raw latency samples (or 60s continuous, whichever is longer)
  3. Track running maximum during collection (no post-processing needed)
  4. Record: max_latency = maximum of all samples
Report: median max across all passes (or worst-case max across all passes for certification)
```

### 2. Running Maximum (Hot Path)

```c
typedef struct {
    uint64_t max_latency;
    uint64_t max_index;      // which sample was the max
    uint64_t max_timestamp;  // when (in TSC) the max occurred
    uint64_t second_max;     // second highest (for context)
} max_tracker_t;

void max_init(max_tracker_t *t) {
    t->max_latency = 0;
    t->max_index = 0;
    t->max_timestamp = 0;
    t->second_max = 0;
}

// Called for every sample — must be branch-predictor friendly
static inline void max_update(max_tracker_t *t, uint64_t sample,
                               uint64_t index, uint64_t timestamp) {
    if (sample > t->max_latency) {
        t->second_max = t->max_latency;
        t->max_latency = sample;
        t->max_index = index;
        t->max_timestamp = timestamp;
    } else if (sample > t->second_max) {
        t->second_max = sample;
    }
}
```

### 3. Post-Hoc Analysis

```c
typedef struct {
    uint64_t max;
    uint64_t p999;       // 99.9th percentile
    uint64_t p9999;      // 99.99th percentile
    uint64_t p99999;     // 99.999th percentile
    uint64_t histogram_overflow;  // samples above histogram ceiling
} max_analysis_t;

// After collecting all samples, sort and extract tail percentiles
max_analysis_t analyze_max(const uint64_t *sorted_samples, size_t n) {
    max_analysis_t result;
    result.max = sorted_samples[n - 1];
    result.p999 = sorted_samples[(size_t)(0.999 * n)];
    result.p9999 = sorted_samples[(size_t)(0.9999 * n)];
    result.p99999 = sorted_samples[(size_t)(0.99999 * n)];
    result.histogram_overflow = 0;
    return result;
}
```

### 4. Max Latency vs. Tail Percentiles

| Metric | Sample Rank (of 10M) | What It Tells You |
|--------|---------------------|-------------------|
| p99 | 100,000th | 1% of samples exceed this |
| p999 | 10,000th | 0.1% of samples exceed this |
| p9999 | 1,000th | 0.01% of samples exceed this |
| p99999 | 100th | 0.001% of samples exceed this |
| max | 1st | The single worst sample |

### 5. Critical Measurement Rules

| Rule | Rationale |
|------|-----------|
| Track max during collection | Sorting 10M samples just to find max is wasteful |
| Record the index and timestamp of max | Enables root-cause analysis (what was happening at that moment) |
| Report second-max for context | If max >> second-max, it may be a measurement artifact |
| Use multiple passes | A single pass may miss rare events; 3+ passes give confidence |
| Consider worst-case max across passes | For certification/SLA purposes, report the worst max seen |

---

## Hardware Requirements

| Component | Minimum | Recommended | Why |
|-----------|---------|-------------|-----|
| CPU | Intel Xeon Scalable (Skylake+) | Intel Xeon 6 / AMD EPYC 9004 | Invariant TSC, large L3 |
| Cache | ≥ 32 MB L3 | ≥ 64 MB L3 | Sample storage in cache |
| Memory | DDR4-3200, `mlockall()` | DDR5-4800, 1 GB hugepages | No page faults during measurement |
| NIC | FPGA-based with hardware timestamping | Purpose-built ULL NIC | Hardware timestamps are deterministic |
| PCIe | Gen4 x16 dedicated | Gen5 x16 dedicated | No DMA contention |
| Power | `performance` governor | BIOS C-state disable | C-state exit latency can be 10–100 µs |
| Thermal | Adequate cooling | Sub-ambient for extreme | Thermal throttling causes periodic max spikes |
| Motherboard | No shared PCIe root complex | Dedicated root complex per slot | Shared root complex adds DMA latency |

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

---

## Interpretation Guide

| Max Latency | Determinism Grade | Typical Deployment |
|-------------|-------------------|-------------------|
| < 500 ns | Excellent | Full FPGA tick-to-trade |
| 500 ns – 1 µs | Very Good | FPGA feed handler + CPU strategy |
| 1 – 5 µs | Good | Kernel bypass (DPDK/Onload) |
| 5 – 20 µs | Acceptable | Tuned kernel bypass |
| 20 – 100 µs | Poor | Standard kernel stack |
| > 100 µs | Unacceptable | Untuned/virtualized environment |

### Common Pitfalls

- **Single-pass max is meaningless:** A single 10M-sample pass may not capture a 1-in-100M event. Run multiple passes and report the worst.
- **Max is not reproducible:** The exact max value will differ between runs. Focus on the order of magnitude and the tail percentiles (p999, p9999) for reproducibility.
- **Measurement artifacts:** A single outlier max (e.g., 100× the second-max) may indicate a measurement bug (e.g., TSC descheduling, interrupt during `rdtsc`). Investigate before reporting.
- **Max grows with sample count:** The more samples you collect, the higher the max will be. Always report sample count alongside max latency.
- **Warm-up contamination:** If warm-up is insufficient, the max may be a warm-up artifact (e.g., first-touch page fault, TLB miss). Always discard warm-up samples.
