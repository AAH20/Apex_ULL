# ULL Throughput Benchmarks

Throughput benchmarks for ultra-low-latency infrastructure, covering the five core metrics: messages/sec, orders/sec, trades/sec, IOPS, and bandwidth.

## Metrics

| Metric | File | Description |
|--------|------|-------------|
| Messages/sec | [messages-per-second.md](messages-per-second.md) | Market data message processing rate |
| Orders/sec | [orders-per-second.md](orders-per-second.md) | Order entry and matching engine throughput |
| Trades/sec | [trades-per-second.md](trades-per-second.md) | Trade execution and reporting throughput |
| IOPS | [iops.md](iops.md) | Storage I/O operations per second |
| Bandwidth | [bandwidth.md](bandwidth.md) | Network and memory bandwidth |

## Benchmark Philosophy

Throughput benchmarks in ULL systems must measure **sustained** throughput under realistic load, not just peak burst rates. Key principles:

- **Measure at steady state**: Discard warm-up period; report sustained rate over ≥60 seconds
- **Report distribution**: Mean, p50, p99, p99.9, max — not just averages
- **Isolate the bottleneck**: Identify whether throughput is limited by CPU, memory, network, or storage
- **Realistic message sizes**: Use production-representative payloads (64B–1500B for network, 4KB–1MB for storage)
- **Multi-queue scaling**: Measure how throughput scales with queue depth and core count

## Hardware Targets

| Component | Entry ULL | Mid ULL | Extreme ULL |
|-----------|-----------|---------|-------------|
| CPU | AMD EPYC 9654 (96c) | AMD EPYC 9754 (128c) | AMD EPYC 9914 (192c) |
| NIC | Mellanox ConnectX-6 (100G) | Mellanox ConnectX-7 (400G) | Custom FPGA NIC |
| Network | 100GbE RoCE v2 | 400GbE RoCE v2 | 800GbE / InfiniBand XDR |
| Storage | NVMe Gen4 (7 GB/s) | NVMe Gen5 (14 GB/s) | CXL-attached memory |
| FPGA | Lattice Nexus | AMD Versal AI Edge | Intel Agilex 7 |
| Memory | 512 GB DDR5-4800 | 1 TB DDR5-5600 | 2 TB DDR5-6400 + HBM |

## Software Stack

| Layer | Technology |
|-------|-----------|
| Kernel | Linux 6.x RT-PREEMPT or custom kernel |
| Kernel bypass | DPDK 24.x / Onload / ef_vi |
| Messaging | Aeron, Disruptor, or custom ring buffer |
| Protocol | UDP multicast (market data), TCP/UDP (orders) |
| Storage | SPDK for NVMe, direct I/O |
| Build | GCC 14 -O3 -march=native, LTO, PGO |

## Running the Benchmarks

Each benchmark file contains:
1. **Measurement methodology** — how to measure, what to measure, common pitfalls
2. **Hardware requirements** — minimum and recommended configurations
3. **Software requirements** — OS, drivers, libraries, kernel parameters
4. **Benchmark code** — compilable C/C++ or Python reference implementation
5. **Expected results** — reference numbers from production ULL systems
6. **Analysis** — how to interpret results and identify bottlenecks

---

*Last updated: 2026-09-29*
