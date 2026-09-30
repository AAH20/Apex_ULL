# Benchmark 2: p99/p50 Ratio

**Metric:** p99 / p50 (99th percentile latency / median latency)

**What it measures:** The ratio of near-worst-case latency to typical latency. A ratio of 1.0 means the 99th percentile equals the median — every sample is nearly identical. Higher ratios indicate a heavy tail.

**Why it matters:** In ULL systems, the tail is what kills profitability. A strategy that works at 500 ns median but fails at 5 µs p99 will lose money on exactly the trades that matter most. The p99/p50 ratio captures tail behavior in a single, interpretable number.

---

## Measurement Methodology

### 1. Sample Collection

```
For each of N passes (N ≥ 3):
  1. Warm up: send/process 10,000 samples, discard
  2. Collect 10,000,000 raw latency samples (or 60s continuous, whichever is longer)
  3. Sort samples in ascending order (or use histogram/selection algorithm)
  4. Extract: p50 = samples[n/2], p99 = samples[0.99*n]
  5. Compute: ratio = p99 / p50
Report: median ratio across all passes
```

### 2. Percentile Extraction

```c
// After sorting (or using quickselect for single percentile)
double compute_p99_p50_ratio(const uint64_t *sorted_samples, size_t n) {
    size_t p50_idx = n / 2;
    size_t p99_idx = (size_t)(0.99 * (double)n);

    double p50 = (double)sorted_samples[p50_idx];
    double p99 = (double)sorted_samples[p99_idx];

    return p99 / p50;
}
```

### 3. Efficient Percentile Computation (No Full Sort)

For large sample sets, use a histogram or the P² algorithm:

```c
// P² Algorithm for dynamic percentile estimation
// (Jain & Chlamtac, 1985) — O(1) per sample, O(1) memory
typedef struct {
    double q[5];      // marker heights (min, p/2, p, (1+p)/2, max)
    double n[5];      // marker positions
    double dn[5];     // desired marker positions
    double np[5];     // desired positions increment
    size_t count;
} p2_state_t;

void p2_init(p2_state_t *s, double p) {
    s->q[0] = s->q[1] = s->q[2] = s->q[3] = s->q[4] = 0.0;
    s->n[0] = 1; s->n[1] = 2; s->n[2] = 3; s->n[3] = 4; s->n[4] = 5;
    s->dn[0] = 0; s->dn[1] = p/2; s->dn[2] = p; s->dn[3] = (1+p)/2; s->dn[4] = 1;
    s->np[0] = 1; s->np[1] = 1 + 2*p; s->np[2] = 1 + 4*p;
    s->np[3] = 3 + 2*p; s->np[4] = 5;
    s->count = 0;
}

// Update with new sample, return current p-th percentile estimate
double p2_update(p2_state_t *s, double x);
```

### 4. Histogram-Based Approach (Recommended for Post-Processing)

```c
#define HISTOGRAM_BUCKETS 4096
#define HISTOGRAM_MIN_NS 0
#define HISTOGRAM_MAX_NS 100000  // 100 µs ceiling

typedef struct {
    uint64_t buckets[HISTOGRAM_BUCKETS];
    uint64_t total;
    uint64_t min;
    uint64_t max;
} latency_histogram_t;

void hist_update(latency_histogram_t *h, uint64_t sample) {
    if (sample < HISTOGRAM_MIN_NS || sample > HISTOGRAM_MAX_NS) return;
    size_t idx = (size_t)((double)(sample - HISTOGRAM_MIN_NS) /
                          (HISTOGRAM_MAX_NS - HISTOGRAM_MIN_NS) * HISTOGRAM_BUCKETS);
    if (idx >= HISTOGRAM_BUCKETS) idx = HISTOGRAM_BUCKETS - 1;
    h->buckets[idx]++;
    h->total++;
    if (sample < h->min) h->min = sample;
    if (sample > h->max) h->max = sample;
}

double hist_percentile(const latency_histogram_t *h, double p) {
    uint64_t target = (uint64_t)(p * h->total);
    uint64_t cumulative = 0;
    for (size_t i = 0; i < HISTOGRAM_BUCKETS; i++) {
        cumulative += h->buckets[i];
        if (cumulative >= target) {
            return (double)HISTOGRAM_MIN_NS +
                   ((double)i / HISTOGRAM_BUCKETS) * (HISTOGRAM_MAX_NS - HISTOGRAM_MIN_NS);
        }
    }
    return (double)HISTOGRAM_MAX_NS;
}
```

### 5. Critical Measurement Rules

| Rule | Rationale |
|------|-----------|
| Use exact percentiles, not approximations | P² and t-digest introduce error; for benchmarking, use exact sorted percentiles |
| Report p50 alongside the ratio | A ratio of 2.0 means very different things at 200 ns vs 20 µs |
| Use linear interpolation between samples | For small sample sets, nearest-rank is too coarse |
| Record the full distribution | A single ratio hides bimodal/multimodal behavior |
| Separate warm-up from measurement | First 10K samples skew p99 upward |

---

## Hardware Requirements

| Component | Minimum | Recommended | Why |
|-----------|---------|-------------|-----|
| CPU | Intel Xeon Scalable (Skylake+) | Intel Xeon 6 / AMD EPYC 9004 | Invariant TSC, large L3 for sample storage |
| Cache | ≥ 32 MB L3 | ≥ 64 MB L3 | Sample array should fit in L3 to avoid DRAM latency |
| Memory | DDR4-3200, `mlockall()` | DDR5-4800, 1 GB hugepages | Sorting 10M samples requires fast memory |
| Storage | N/A (in-memory only) | N/A | Disk I/O during measurement is catastrophic |
| NIC | FPGA-based with hardware timestamping | Purpose-built ULL NIC | Hardware timestamps eliminate software jitter |
| PCIe | Gen4 x16 dedicated | Gen5 x16 dedicated | DMA contention adds tail latency |

---

## Software Requirements

| Layer | Requirement | Configuration |
|-------|-------------|---------------|
| Kernel boot | Core isolation | `isolcpus=2-7 nohz_full=2-7 rcu_nocbs=2-7` |
| Kernel boot | Hugepages | `default_hugepagesz=1G hugepagesz=1G hugepages=4` |
| IRQ affinity | Exclude measurement cores | `echo 0-1 > /proc/irq/default_smp_affinity` |
| Scheduler | Real-time priority | `SCHED_FIFO` priority 99 |
| Memory | Lock pages | `mlockall(MCL_CURRENT \| MCL_FUTURE)` |
| Sorting | Use `qsort_r` or radix sort | Radix sort for `uint64_t` is O(n), 5–10× faster than quicksort |
| Clock | Raw monotonic | `clock_gettime(CLOCK_MONOTONIC_RAW, ...)` |
| Compiler | Optimization | `-O3 -march=native` |
| NUMA | Single-node allocation | `numactl --membind=0 --cpunodebind=0` |

---

## Interpretation Guide

| p99/p50 Ratio | Determinism Grade | Typical Deployment |
|---------------|-------------------|-------------------|
| < 1.2 | Excellent | Full FPGA tick-to-trade |
| 1.2 – 1.5 | Very Good | FPGA feed handler + CPU strategy |
| 1.5 – 2.0 | Good | Kernel bypass (DPDK/Onload) |
| 2.0 – 3.0 | Acceptable | Tuned kernel bypass |
| 3.0 – 5.0 | Poor | Standard kernel stack |
| > 5.0 | Unacceptable | Untuned/virtualized environment |

### Common Pitfalls

- **Ratio without context:** p99/p50 = 1.5 at 200 ns median (300 ns p99) is excellent; at 20 µs median (30 µs p99) is terrible. Always report absolute values alongside the ratio.
- **Tail truncation:** If your measurement loop has a timeout, you may silently drop the true p99. Ensure the measurement window is long enough to capture the full tail.
- **Bimodal distributions:** A ratio of 3.0 could mean a smooth distribution or two distinct populations. Always plot a histogram before drawing conclusions.
- **Sample size for p99:** With 10M samples, p99 is the 100,000th sample — well-converged. With 100K samples, p99 is the 1,000th sample — noisy. Use ≥ 10M samples for reliable p99.
