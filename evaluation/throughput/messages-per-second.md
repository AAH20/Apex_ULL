# Messages Per Second (msg/s)

**Definition:** The number of discrete messages processed per second by a system, where a message is a self-contained unit of data (market data update, order request, payment authorization, etc.).

---

## 1. Measurement Methodology

### 1.1 What Constitutes a Message

| Domain | Message Type | Typical Size |
|--------|-------------|--------------|
| HFT Market Data | Incremental order book update | 50–200 bytes |
| HFT Order Entry | New order / cancel / modify | 30–100 bytes |
| Payment Auth | ISO 8583 authorization request | 500–2000 bytes |
| Payment Clearing | ISO 20022 payment instruction | 1–5 KB |
| Gaming | Player state update / input | 100–500 bytes |
| Telemetry | Metrics / log batch | 1–10 KB |

### 1.2 Measurement Approaches

| Method | Description | Accuracy | Use Case |
|--------|-------------|----------|----------|
| **Application-level counter** | Increment atomic counter per message processed; sample every second | High | Production systems |
| **Network tap / SPAN** | Capture packets on wire; count at capture point | Very high | Infrastructure validation |
| **Kernel tracepoint** | `perf` / `eBPF` / `DPDK` eth_stats | High | Kernel-bypass systems |
| **Hardware counter** | NIC register reads (e.g., ConnectX-7 per-port counters) | Very high | RDMA / kernel bypass |
| **Log-based** | Parse application logs; count entries per time window | Medium | Post-hoc analysis |

### 1.3 Standard Test Configuration

```
Test Duration:     ≥ 60 seconds sustained (≥ 5 minutes for production validation)
Warm-up:           ≥ 30 seconds (JIT, cache warm, connection establishment)
Sample Interval:   1 second (report p50, p99, p99.9, max)
Load Pattern:      Constant rate (open-loop) with gradual ramp
Message Sizes:     Test at 64B, 256B, 1KB, 4KB, 16KB
Concurrency:       1, 10, 100, 1000 parallel connections/streams
```

### 1.4 Key Formulas

```
Throughput (msg/s) = Total messages processed / Measurement window (s)

Effective throughput = Throughput × (1 - error_rate)

Goodput = Throughput × (useful_messages / total_messages)

Message rate per core = Total throughput / Active CPU cores
```

---

## 2. Benchmark Standards

### 2.1 HFT Market Data Feed Handlers

| System | Messages/sec | Message Size | Latency | Source |
|--------|-------------|-------------|---------|--------|
| CME Globex MDP 3.0 | 500K–2M msg/s per instrument | ~100 bytes | <10 μs | CME documentation |
| Nasdaq INET | 1M–5M msg/s per feed | ~80 bytes | <10 μs | Nasdaq specs |
| FPGA feed handler (typical) | 10M–100M msg/s | 50–200 bytes | 100–500 ns | IEEE 2024 study |
| FPGA feed handler (high-end) | 100M+ msg/s | 50–200 bytes | <200 ns | Algo-Logic, CSPi |
| Kernel bypass (DPDK) | 1M–10M msg/s | 64–1518 bytes | 1–10 μs | DPDK benchmarks |
| Standard kernel stack | 100K–500K msg/s | 64–1518 bytes | 10–50 μs | Typical measurements |

### 2.2 Payment Networks

| Network | Messages/sec | Message Type | Source |
|---------|-------------|-------------|--------|
| Visa | 83,000 peak msg/s | Authorization + clearing | Visa corporate (2025) |
| Visa (stress test) | 65,000+ msg/s sustained | NOC stress test | VisaNet booklet |
| Stripe | 10,342,117 TPS (peak) | Payment requests | Black Friday 2024 |
| Stripe (sustained) | ~100K–500K msg/s | Payment requests | Estimated from annual volume |
| PayPal | ~333 TPS (1.2M/hour) | P2P payments | Service 83908 |
| Square | 47,000 TPS (peak) | Payment transactions | Black Friday 2025 |
| Fiserv | 25,000+ TPS | Core banking | Fiserv corporate |
| Worldpay | 100–500 TPS per merchant | Payment API | API documentation |

### 2.3 Network Interconnect Message Rates

| Technology | Messages/sec | Message Size | Source |
|-----------|-------------|-------------|--------|
| InfiniBand NDR (ConnectX-7) | 330–370M msg/s | 64B–2KB | NVIDIA datasheet |
| RoCE v2 (ConnectX-6) | 100–200M msg/s | 64B–2KB | NVIDIA benchmarks |
| iWARP (Intel E810) | 50–100M msg/s | 64B–2KB | Intel specifications |
| DPDK (single core) | 10–100M msg/s | 64B–1518B | DPDK performance reports |
| AMD Pensando Salina | 117M pkt/s | Variable | AMD product brief |
| Intel IPU E2100 | 200M pkt/s | Variable | Intel product brief |

---

## 3. Industry Averages

### 3.1 By Domain

| Domain | Median msg/s | p99 msg/s | Notes |
|--------|-------------|-----------|-------|
| HFT market data (per feed) | 2M | 5M | During peak trading hours |
| HFT order entry | 500K | 2M | Per trading session |
| Payment authorization | 50K | 200K | Global average |
| Payment clearing | 10K | 50K | Batch + real-time |
| Gaming state sync | 100K | 1M | Per game shard |
| IoT telemetry | 1M | 10M | Aggregated across devices |

### 3.2 By Technology Stack

| Stack | Typical msg/s | Ceiling msg/s | Bottleneck |
|-------|-------------|--------------|------------|
| Standard kernel TCP | 100K–500K | 1M | Context switches, interrupts |
| Kernel bypass (DPDK/Onload) | 1M–10M | 50M | Memory bandwidth, PCIe |
| RDMA (InfiniBand NDR) | 100M–370M | 500M | NIC hardware limits |
| FPGA (feed handler) | 10M–100M | 1B+ | SerDes bandwidth, logic |
| ASIC (fixed function) | 100M–1B | 10B+ | Silicon limits |

### 3.3 Scaling Characteristics

```
Single connection:     10K–100K msg/s (latency-bound)
10 connections:        100K–1M msg/s (linear scaling)
100 connections:       1M–10M msg/s (near-linear)
1000 connections:      10M–100M msg/s (sub-linear, contention)
10K+ connections:      100M+ msg/s (requires sharding/partitioning)
```

---

## 4. Factors Affecting Message Throughput

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Message size | Larger messages → fewer msg/s but higher goodput | Batch small messages |
| Connection count | More connections → higher aggregate but more overhead | Connection pooling |
| CPU core count | Linear scaling up to memory bandwidth limit | NUMA-aware allocation |
| Memory bandwidth | ~120 GB/s (DDR5) per socket limits rate | HBM, FPGA on-chip memory |
| PCIe bandwidth | Gen5 x16 = 64 GB/s; Gen4 x16 = 32 GB/s | Use Gen5, reduce copies |
| Kernel overhead | 10–50 μs per syscall | Kernel bypass (DPDK, RDMA) |
| Serialization | JSON/Protobuf parsing overhead | Binary protocols, FPGA decode |
| GC pauses | 1–100 ms stalls (Java/Go) | Native code, GC tuning, off-heap |

---

## 5. Measurement Tools

| Tool | Domain | Output |
|------|--------|--------|
| `perf stat` | System-wide | Cycles, instructions, cache misses |
| `dpdk-procinfo` | DPDK apps | Per-port packet rates |
| `ib_write_bw` / `ib_send_bw` | RDMA/InfiniBand | Bandwidth and message rate |
| `rdma-core` perftest | RoCE/IB | msg/s, latency percentiles |
| `pktgen-DPDK` | Packet generation | Line-rate packet rates |
| `wrk` / `wrk2` | HTTP APIs | Requests/sec |
| `k6` / `locust` | Load testing | Requests/sec, latency |
| Custom FPGA testbench | FPGA validation | Cycle-accurate msg/s |

---

## 6. Reporting Template

```yaml
metric: messages_per_second
system: <system_name>
date: <ISO 8601>
configuration:
  message_size_bytes: <N>
  connections: <N>
  cpu_cores: <N>
  network_stack: <kernel|dpdk|rdma|fpga>
results:
  sustained_msg_s: <N>
  peak_msg_s: <N>
  p50_msg_s: <N>
  p99_msg_s: <N>
  p999_msg_s: <N>
  error_rate: <float>
  cpu_utilization_pct: <N>
  memory_bandwidth_gbps: <N>
notes: <any anomalies or observations>
```

---

*Sources: CME/Nasdaq exchange specifications, NVIDIA ConnectX-7 datasheet, DPDK performance reports, Visa/Stripe corporate disclosures, IEEE 2024 FPGA study, AMD/Intel product briefs.*
