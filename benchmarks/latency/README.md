# Ultra-Low Latency Benchmark Suite

> **Project:** ultra-low-latency-infra  
> **Scope:** End-to-end latency measurement methodology for ULL infrastructure  
> **Metrics:** Ping-pong, Round-trip, One-way, Jitter, Throughput, Message Rate

---

## Overview

This benchmark suite defines standardized measurement methodologies for ultra-low-latency (ULL) infrastructure. Each metric includes measurement methodology, hardware requirements, and software requirements.

### Metrics

| # | Metric | Description | Typical ULL Target |
|---|--------|-------------|-------------------|
| 1 | [Ping-Pong Latency](ping-pong-latency.md) | Request-response round-trip between two nodes | < 2 µs |
| 2 | [Round-Trip Latency](round-trip-latency.md) | Full RTT of a message (A→B→A) | < 2 µs |
| 3 | [One-Way Latency](one-way-latency.md) | Single-direction message delivery time | < 1 µs |
| 4 | [Jitter](jitter.md) | Variation in latency over time | < 100 ns |
| 5 | [Throughput](throughput.md) | Data transfer rate under latency constraints | 100+ Gb/s |
| 6 | [Message Rate](message-rate.md) | Messages processed per second | 100+ Mmsg/s |

---

## Quick Start

### Prerequisites

- Two or more ULL-capable nodes (see individual metric docs for hardware specs)
- RDMA-capable NICs (NVIDIA ConnectX-7 or equivalent) or DPDK-compatible NICs
- PTP grandmaster clock (for one-way latency)
- Isolated CPU cores and kernel bypass configured

### Running Benchmarks

Each metric directory contains detailed instructions. General pattern:

```bash
# On Node B (server)
<benchmark-tool> -a <ip> -p <port> --server

# On Node A (client)
<benchmark-tool> -a <ip> -p <port> --client --duration 60
```

---

## Common Infrastructure

### Network Topology

```
┌─────────────┐          ┌─────────────┐
│   Node A    │◄────────►│   Node B    │
│  (Client)   │  RDMA /  │  (Server)   │
│             │  DPDK    │             │
└─────────────┘          └─────────────┘
       │                        │
       └──────────┬─────────────┘
                  │
          ┌───────▼───────┐
          │  PTP GM Clock │
          │  (IEEE 1588)  │
          └───────────────┘
```

### Shared Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| NIC | ConnectX-6 (200 Gb/s) | ConnectX-7 (400 Gb/s NDR) |
| CPU | 8 cores, 2.5 GHz | 16+ cores, 3.0 GHz+ |
| Memory | 32 GB DDR4 | 64 GB DDR5 |
| OS | Linux 5.15+ | Linux 6.1+ (PREEMPT_RT) |
| Switch | NDR InfiniBand | NDR IB + PTP support |

### Shared Software Requirements

| Component | Purpose |
|-----------|---------|
| MLNX_OFED / DOCA | RDMA drivers and libraries |
| DPDK 23.11+ | Kernel bypass networking |
| libibverbs | RDMA verbs API |
| PTP4L / PHC2SYS | Clock synchronization |
| perf / ftrace | Kernel tracing |
| numactl | NUMA affinity control |

---

## Results Template

Each benchmark should record:

```yaml
benchmark: <metric-name>
date: <ISO-8601>
topology: <network-topology>
hardware:
  nic: <model>
  cpu: <model>
  memory: <size>
software:
  os: <kernel-version>
  driver: <driver-version>
  tool: <tool-version>
results:
  min: <value>
  avg: <value>
  max: <value>
  p50: <value>
  p99: <value>
  p99.9: <value>
  stddev: <value>
```

---

## References

- [OSU Micro-Benchmarks](https://mvapich.cse.ohio-state.edu/benchmarks/)
- [DPDK Performance Reports](https://core.dpdk.org/perf-report/)
- [InfiniBand perftest](https://github.com/linux-rdma/perftest)
- [IEEE 1588 PTP](https://ieee1588.nist.gov/)
- [lmbench](https://sourceforge.net/projects/lmbench/)
