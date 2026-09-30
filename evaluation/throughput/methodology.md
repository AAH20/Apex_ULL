# Measurement Methodology

**Cross-cutting methodology for ULL throughput evaluation.**

---

## 1. General Principles

### 1.1 Measurement Philosophy

| Principle | Description |
|-----------|-------------|
| **Measure sustained, not peak** | Peak numbers are marketing; sustained numbers are engineering |
| **Report distributions, not just means** | p50, p99, p99.9, max — the tail matters in ULL |
| **Test under contention** | Idle-system throughput is not representative |
| **Normalize by workload** | Always report message size, block size, connection count |
| **Include overhead** | Report CPU utilization, memory bandwidth, cache misses |
| **Reproducible** | Document exact configuration, versions, and environment |

### 1.2 Common Pitfalls

| Pitfall | Problem | Solution |
|---------|---------|----------|
| **Averaging over too short a window** | Misses bursts and tail behavior | Use ≥ 60s windows, report percentiles |
| **Ignoring warm-up** | JIT, cache warm, connection setup skew results | Discard first 30–60 seconds |
| **Testing with unrealistic workloads** | Results don't translate to production | Use production-like message mixes |
| **Single-threaded tests** | Don't reveal scaling bottlenecks | Test with 1, 10, 100, 1000 threads |
| **Ignoring error rates** | High throughput with 50% errors is meaningless | Always report error rate |
| **Not isolating variables** | Can't attribute performance changes | Change one variable at a time |
| **Using debug builds** | Debug overhead skews results | Use release builds with optimizations |

---

## 2. Test Environment

### 2.1 Hardware Configuration

```yaml
cpu:
  model: <CPU model>
  cores: <N>
  threads: <N>
  frequency_ghz: <N>
  numa_nodes: <N>
  l1_cache_kb: <N>
  l2_cache_kb: <N>
  l3_cache_mb: <N>

memory:
  type: <DDR4|DDR5|HBM>
  capacity_gb: <N>
  frequency_mhz: <N>
  channels: <N>
  bandwidth_gbps: <N>

network:
  nic_model: <NIC model>
  link_speed_gbps: <N>
  ports: <N>
  rdma_capable: <true|false>

storage:
  type: <NVMe Gen4|NVMe Gen5|SATA SSD>
  capacity_gb: <N>
  iops_rating: <N>

fpga:
  model: <FPGA model>  # if applicable
  serdes_rate_gbps: <N>
  lut_count: <N>
```

### 2.2 Software Configuration

```yaml
os:
  distribution: <Ubuntu|CentOS|Debian|Custom>
  kernel: <version>
  kernel_params: <isolcpus, nohz_full, etc.>

compiler:
  name: <gcc|clang|icc>
  version: <version>
  flags: <-O3, -march=native, etc.>

libraries:
  dpdk: <version>  # if applicable
  rdma_core: <version>  # if applicable
  spdk: <version>  # if applicable

application:
  name: <application name>
  version: <version>
  build_type: <release|debug>
```

### 2.3 System Tuning

| Parameter | ULL Setting | Rationale |
|-----------|------------|-----------|
| `isolcpus` | Isolate cores for app | Prevent kernel scheduling interference |
| `nohz_full` | No tick on isolated cores | Reduce timer interrupts |
| `rcu_nocbs` | Offload RCU callbacks | Reduce RCU overhead |
| `idle=poll` | CPU polls when idle | Reduce wake-up latency |
| `transparent_hugepages` | `always` or `madvise` | Reduce TLB misses |
| `vm.swappiness` | 0 | Prevent swapping |
| `net.core.busy_poll` | 50 | Reduce network latency |
| `net.core.busy_read` | 50 | Reduce network latency |
| IRQ affinity | Pin IRQs to specific cores | Cache locality |
| NUMA policy | `numactl --interleave=all` or `--membind` | Memory locality |

---

## 3. Load Generation

### 3.1 Load Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Constant rate** | Fixed messages/sec | Baseline throughput |
| **Ramp-up** | Gradually increase rate | Find breaking point |
| **Step function** | Sudden rate change | Test recovery |
| **Bursty** | Periodic bursts | Test buffering |
| **Poisson** | Random inter-arrival times | Realistic arrival pattern |
| **Trace-driven** | Replay production traffic | Most realistic |

### 3.2 Load Generation Tools

| Tool | Domain | Output |
|------|--------|--------|
| `iperf3` | Network | Bandwidth, jitter |
| `wrk` / `wrk2` | HTTP | Requests/sec, latency |
| `k6` / `locust` | HTTP | Requests/sec, latency |
| `fio` | Storage | IOPS, bandwidth, latency |
| `pktgen-DPDK` | Packet generation | Packets/sec |
| `dpdk-l2fwd` | Packet forwarding | Packets/sec |
| Custom FPGA testbench | FPGA validation | Cycle-accurate rates |

---

## 4. Data Collection

### 4.1 Metrics to Collect

| Category | Metrics | Collection Method |
|----------|---------|-------------------|
| **Throughput** | msg/s, ord/s, trd/s, IOPS, Gb/s | Application counters |
| **Latency** | p50, p99, p99.9, max, jitter | Application timestamps |
| **CPU** | Utilization, cycles, instructions, cache misses | `perf stat` |
| **Memory** | Bandwidth, NUMA hits/misses | `perf stat`, `numastat` |
| **Network** | Packets/sec, bytes/sec, errors, drops | `ethtool -S`, `ip -s link` |
| **Storage** | IOPS, bandwidth, latency, queue depth | `iostat`, `fio` |
| **Errors** | Error rate, retransmits, drops | Application + system counters |

### 4.2 Collection Frequency

| Metric Type | Frequency | Rationale |
|-------------|-----------|-----------|
| Throughput | 1 second | Track sustained rate |
| Latency | Per-operation | Full distribution |
| CPU | 1 second | Track utilization |
| Memory | 1 second | Track bandwidth |
| Network | 1 second | Track packet rates |
| Storage | 1 second | Track IOPS |

### 4.3 Data Storage Format

```json
{
  "timestamp": "messages_per_second",
  "timestamp": "2026-09-29T12:00:00Z",
  "configuration": {
    "message_size_bytes": 100,
    "connections": 10,
    "cpu_cores": 4,
    "network_stack": "dpdk"
  },
  "results": {
    "sustained": 1250000,
    "peak": 1500000,
    "p50": 1200000,
    "p99": 1400000,
    "p999": 1450000,
    "error_rate": 0.0001
  },
  "system": {
    "cpu_utilization_pct": 75,
    "memory_bandwidth_gbps": 45,
    "cache_misses_per_sec": 100000
  }
}
```

---

## 5. Analysis

### 5.1 Throughput Analysis

```
1. Plot throughput over time → identify steady state
2. Calculate sustained throughput (mean of steady state)
3. Identify peak throughput (max in any 1s window)
4. Calculate coefficient of variation (CV) → measure stability
5. Plot throughput vs. load → find linear scaling region
6. Identify bottleneck (where throughput plateaus)
```

### 5.2 Latency Analysis

```
1. Plot latency histogram → identify distribution shape
2. Calculate percentiles (p50, p99, p99.9, max)
3. Calculate jitter (p99 - p50)
4. Plot latency vs. throughput → find knee point
5. Identify tail latency sources (GC, scheduling, I/O)
```

### 5.3 Bottleneck Identification

| Symptom | Likely Bottleneck | Investigation |
|---------|------------------|---------------|
| Throughput plateaus, CPU at 100% | CPU-bound | Profile hot path |
| Throughput plateaus, CPU low | I/O-bound | Check network/storage |
| Throughput drops periodically | GC or scheduling | Check GC logs, `perf sched` |
| Throughput varies with NUMA node | NUMA imbalance | Check `numastat` |
| Throughput drops with small packets | CPU-bound (per-packet) | Check cycles/packet |

---

## 6. Reporting

### 6.1 Minimum Report Contents

1. **System configuration** — hardware, software, tuning
2. **Workload description** — message sizes, mix, connection count
3. **Throughput results** — sustained, peak, percentiles
4. **Latency results** — p50, p99, p99.9, max, jitter
5. **Resource utilization** — CPU, memory, network, storage
6. **Error rates** — application and system level
7. **Bottleneck analysis** — what limited throughput
8. **Scaling characteristics** — how throughput scales with load

### 6.2 Comparison Methodology

```
1. Same hardware configuration
2. Same software versions
3. Same workload characteristics
4. Same measurement duration
5. Same system tuning parameters
6. Run each test ≥ 3 times, report median
```

---

## 7. Reproducibility Checklist

- [ ] Document exact hardware configuration
- [ ] Document exact software versions
- [ ] Document kernel parameters and system tuning
- [ ] Document workload characteristics
- [ ] Document measurement duration and warm-up
- [ ] Document number of test runs
- [ ] Document environment (temperature, load, other tenants)
- [ ] Provide raw data (not just summaries)
- [ ] Provide analysis scripts
- [ ] Document any anomalies or deviations

---

*This methodology applies to all throughput metrics: messages/sec, orders/sec, trades/sec, IOPS, and bandwidth.*
