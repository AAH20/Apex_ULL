# Ultra-Low Latency Infrastructure — Getting Started

**Version:** 1.0  
**Last Updated:** 2026-09-29  
**Project:** ultra-low-latency-infra

---

## What Is This Project?

Ultra-low-latency (ULL) infrastructure encompasses the hardware, software, and network technologies used to minimize the time between an event occurring and a system responding to it. This project documents the architecture, technologies, benchmarks, and best practices for building systems where every nanosecond counts.

### Domains Covered

| Domain | Typical Latency Budget | Key Technologies |
|--------|----------------------|------------------|
| High-Frequency Trading (HFT) | 150 ns – 10 µs | FPGA, kernel bypass, microwave |
| Payment Networks | 42 ms – 1 s | gRPC, cell-based architecture, multi-region |
| Gaming (PC) | 3 ms – 60 ms | NVIDIA Reflex, DLSS, GPU scheduling |
| Gaming (Mobile) | 18 ms – 100 ms | Apple Silicon, ARM Mali, 240Hz touch |
| Data Center Interconnect | 100 ns – 5 µs | InfiniBand, RoCE, DPU, optical switching |

---

## Repository Structure

```
ultra-low-latency-infra/
├── docs/                  # This documentation
│   ├── getting-started.md # You are here
│   ├── architecture.md    # System architecture guide
│   ├── api-reference.md   # Technology API reference
│   └── tutorials/         # Step-by-step tutorials
├── reports/               # Deep research reports
│   ├── hft-firms.md       # HFT firm profiles and benchmarks
│   ├── fpga-technologies.md
│   ├── network-technologies.md
│   ├── payment-networks.md
│   └── gaming.md
├── benchmarks/            # Performance benchmarks
├── evaluation/            # Evaluation frameworks
│   └── throughput/        # Throughput measurement methodology
└── security/              # Security considerations
```

---

## Quick Start

### 1. Understand the Latency Hierarchy

Before diving into any technology, internalize the fundamental latency tiers:

| Tier | Latency | Example |
|------|---------|---------|
| **On-chip** | 1–2 cycles (0.5–2 ns) | FPGA eFPGA, ASIC logic |
| **FPGA pipeline** | 100–500 ns | Feed handler, order book update |
| **Kernel bypass** | 1–5 µs | DPDK, Onload, ef_vi |
| **RDMA / InfiniBand** | 100 ns – 2 µs | RoCE v2, NDR 400G |
| **Network switch** | 100–500 ns | P4 switch, Tofino |
| **Cross-host (same DC)** | 5–20 µs | DPDK loopback, SPDK |
| **Cross-region** | 40–300 ms | Fiber, microwave, internet |

### 2. Pick Your Domain

- **Building trading systems?** → Read [Architecture Guide](architecture.md) → FPGA + kernel bypass
- **Building payment processing?** → Read [Payment Networks Report](../reports/payment-networks.md) → gRPC + multi-region
- **Building game engines?** → Read [Gaming Report](../reports/gaming.md) → Reflex + GPU scheduling
- **Building data center fabric?** → Read [Network Technologies Report](../reports/network-technologies.md) → InfiniBand + DPU

### 3. Run the Benchmarks

See the [Throughput Evaluation Framework](../evaluation/throughput/README.md) for measurement methodology and industry averages.

---

## Key Concepts

### Latency vs. Throughput

- **Latency** = time for one operation to complete (nanoseconds to milliseconds)
- **Throughput** = operations per second (messages/sec, orders/sec, IOPS)
- **ULL systems optimize both**, but latency is the primary constraint

### The Tick-to-Trade Pipeline

The canonical ULL pipeline in HFT:

```
Market Data → Feed Handler → Order Book → Strategy → Risk Check → Order Encoder → Exchange
   (wire)       (FPGA)         (FPGA)      (CPU)      (FPGA)        (FPGA)         (wire)
```

Each arrow is a latency budget. The total is the tick-to-trade latency.

### Determinism Matters

In ULL systems, **jitter** (variance in latency) is often as important as average latency. A system with 500 ns average but 2 µs jitter is less predictable than one with 800 ns average and 50 ns jitter.

---

## Technology Selection Cheat Sheet

| If you need... | Use... | Avoid... |
|---------------|--------|----------|
| Sub-microsecond processing | FPGA (Achronix, Xilinx, Intel) | Standard CPU, GPU |
| Sub-5µs network I/O | DPDK, kernel bypass | Kernel TCP stack |
| Sub-2µs cross-host | InfiniBand NDR, RoCE v2 | TCP, iWARP |
| Nanosecond switching | P4 switch, optical | Electrical hierarchy |
| Lowest jitter | FPGA determinism | Software polling |
| AI inference on FPGA | Quantized NN (8-bit), AIE-ML | Full-precision models |

---

## Prerequisites

To work with this project's content:

- **Basic:** Computer architecture, networking fundamentals, Linux
- **Intermediate:** C++, Python, TCP/IP, kernel internals
- **Advanced:** FPGA design (Verilog/SystemVerilog), DPDK, RDMA, P4

---

## Next Steps

1. **[Architecture Guide](architecture.md)** — Deep dive into ULL system design
2. **[API Reference](api-reference.md)** — Technology interfaces and configurations
3. **[Tutorials](tutorials/)** — Hands-on guides for key technologies
4. **[Reports](../reports/)** — Domain-specific research and benchmarks
