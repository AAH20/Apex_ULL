# Jitter Benchmark

> **Metric:** Variation in latency over time  
> **Target:** < 100 ns (RDMA), < 500 ns (DPDK)

---

## 1. Measurement Methodology

### Definition

Jitter measures the variation in latency over time. It is critical for ULL applications where consistent timing is more important than absolute latency.

### Types of Jitter

| Type | Description | Use Case |
|------|-------------|----------|
| **Packet Jitter** | Variation in packet arrival times | Network analysis |
| **Latency Jitter** | Variation in round-trip latency | Application performance |
| **Phase Jitter** | Variation in clock phase | Clock synchronization |
| **Cycle Jitter** | Variation in cycle time | Real-time systems |

### Procedure

1. **Collect latency samples:** Measure N consecutive latencies (default: 1,000,000)
2. **Calculate statistics:**
   - Mean (μ)
   - Standard deviation (σ)
   - Peak-to-peak (max - min)
   - Percentiles (p50, p99, p99.9)
3. **Compute jitter metrics:**
   - **Absolute jitter:** `|latency[i] - mean|`
   - **Relative jitter:** `|latency[i] - mean| / mean`
   - **Peak-to-peak jitter:** `max(latency) - min(latency)`

### Formulas

```
Mean:     μ = (Σ latency[i]) / N
Variance: σ² = Σ (latency[i] - μ)² / N
Jitter:   J = σ (standard deviation)
P2P Jitter: J_p2p = max(latency) - min(latency)
```

### Key Considerations

- **Sample size:** Minimum 100,000 samples for statistical significance
- **Warm-up:** Discard first 1,000 samples
- **Time window:** Measure over extended period (minutes to hours)
- **Environmental:** Control temperature, load, and other variables

---

## 2. Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| NIC | ConnectX-6 (200 Gb/s) | ConnectX-7 (400 Gb/s NDR) | Low jitter design |
| CPU | 8 cores, 2.5 GHz | 16+ cores, 3.0 GHz+ | Isolated cores |
| Memory | 32 GB DDR4 | 64 GB DDR5 | Low-latency DIMMs |
| Switch | NDR InfiniBand | NDR IB with PTP | Cut-through switching |
| Clock | TCXO | OCXO | Stable reference clock |
| Cooling | Adequate | Active cooling | Temperature stability |

### Temperature Control

Temperature affects clock stability and signal integrity:

```bash
# Monitor temperature
sensors

# Set fan curve for stability
ipmitool raw 0x30 0x70 0x66 0x01 0x00 0x32  # 50% fan speed
```

---

## 3. Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| OS | Linux 6.1+ (PREEMPT_RT) | Real-time kernel |
| MLNX_OFED | 23.10+ | RDMA drivers |
| DPDK | 23.11+ | Kernel bypass |
| perf | Latest | Kernel tracing |
| ftrace | Latest | Function tracing |
| sysstat | Latest | System monitoring |

### Configuration for Low Jitter

```bash
# Disable CPU frequency scaling
cpupower frequency-set -g performance

# Disable C-states (prevent CPU sleep)
GRUB_CMDLINE_LINUX="intel_idle.max_cstate=0 processor.max_cstate=0"

# Disable IRQ balancing
systemctl stop irqbalance
systemctl disable irqbalance

# Set IRQ affinity to non-benchmark cores
echo 1 > /proc/irq/<IRQ_NUM>/smp_affinity

# Disable NMI watchdog
echo 0 > /proc/sys/kernel/nmi_watchdog

# Disable transparent huge pages
echo never > /sys/kernel/mm/transparent_hugepage/enabled
```

---

## 4. Running the Benchmark

### Using perftest with Jitter Analysis

```bash
# Run latency benchmark
ib_write_lat -a -d mlx5_0 --report_gbits <Node_B_IP> > latency.txt

# Analyze jitter
awk '{print $2}' latency.txt | \
  awk '{sum+=$1; sumsq+=$1*$1} END {mean=sum/NR; print "Mean:", mean; print "Stddev:", sqrt(sumsq/NR - mean*mean)}'
```

### Custom Jitter Measurement

```c
// Pseudocode for jitter measurement
uint64_t latencies[N];
for (i = 0; i < N; i++) {
    t_start = rdtsc();
    send_and_receive();
    t_end = rdtsc();
    latencies[i] = t_end - t_start;
}

// Calculate statistics
double mean = calculate_mean(latencies, N);
double stddev = calculate_stddev(latencies, N, mean);
double p2p = max(latencies) - min(latencies);
double p99 = percentile(latencies, N, 0.99);

printf("Mean: %.2f ns\n", mean);
printf("Stddev (Jitter): %.2f ns\n", stddev);
printf("P2P Jitter: %.2f ns\n", p2p);
printf("P99: %.2f ns\n", p99);
```

### Using DPDK

```bash
# Run DPDK latency benchmark
./l2fwd-latency -l 2-7 -n 4 -- -p 0x1 --latency --stats 1

# Collect and analyze
# DPDK provides min, max, avg, and jitter statistics
```

---

## 5. Expected Results

| Technology | Typical Jitter | P2P Jitter | P99 Latency |
|------------|----------------|------------|-------------|
| InfiniBand NDR | 20–50 ns | 100–200 ns | 1.5 µs |
| RoCE v2 | 50–100 ns | 200–500 ns | 2.5 µs |
| DPDK | 100–200 ns | 500–1000 ns | 5 µs |
| Kernel TCP/IP | 500–2000 ns | 2000–10000 ns | 50 µs |

---

## 6. Jitter Analysis

### Jitter Distribution

```
Latency Distribution (Histogram)
│
│    ┌───┐
│    │   │
│  ┌─┤   ├─┐
│  │ │   │ │
│ ┌┤ │   │ ├┐
│ ││ │   │ ││
│ ││ │   │ ││
└─┴─┴───┴─┴─┴──► Latency
  Min  Mean  Max
```

### Jitter Sources

| Source | Typical Jitter | Mitigation |
|--------|----------------|------------|
| Clock drift | 10–100 ns | PTP synchronization |
| Temperature | 50–200 ns | Active cooling |
| CPU scheduling | 100–1000 ns | Core isolation |
| Interrupt handling | 200–2000 ns | Polling mode |
| Network congestion | 500–5000 ns | Dedicated network |
| Kernel overhead | 1000–10000 ns | Kernel bypass |

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| High jitter (>500 ns) | CPU frequency scaling | Set governor to performance |
| Periodic spikes | IRQ handling | Move IRQs to non-isolated cores |
| Increasing jitter over time | Thermal throttling | Improve cooling |
| Random spikes | Background processes | Isolate cores, disable services |
| High P2P jitter | Network congestion | Use dedicated network |
