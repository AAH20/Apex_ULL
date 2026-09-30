# Ultra-Low Latency Architecture Guide

**Version:** 1.0  
**Last Updated:** 2026-09-29

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture Patterns](#system-architecture-patterns)
3. [Hardware Layer](#hardware-layer)
4. [Network Layer](#network-layer)
5. [Software Layer](#software-layer)
6. [Data Flow Architecture](#data-flow-architecture)
7. [Latency Budgeting](#latency-budgeting)
8. [Fault Tolerance & Redundancy](#fault-tolerance--redundancy)
9. [Security Architecture](#security-architecture)
10. [Design Checklist](#design-checklist)

---

## Overview

Ultra-low-latency systems are designed around a single principle: **minimize the time from input to output at every layer of the stack**. This requires co-design across hardware, networking, and software — optimizing one layer in isolation yields diminishing returns.

### Design Principles

1. **Determinism over average latency** — predictable performance beats fast-but-variable
2. **Eliminate the kernel** — bypass the OS network stack on the hot path
3. **Co-locate compute and data** — every millimeter of wire adds nanoseconds
4. **Pipeline everything** — serialize only where absolutely necessary
5. **Measure at the bottleneck** — throughput is gated by the slowest stage

---

## System Architecture Patterns

### Pattern 1: FPGA-First (HFT Trading)

```
┌─────────────────────────────────────────────────────────┐
│                    Exchange Gateway                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  PHY/MAC │→ │  Feed    │→ │  Order   │→ │  Order  │ │
│  │  (FPGA)  │  │  Handler │  │  Book    │  │ Encoder │ │
│  └──────────┘  │  (FPGA)  │  │  (FPGA)  │  │  (FPGA) │ │
│                └──────────┘  └──────────┘  └─────────┘ │
│                      ↓                                    │
│                ┌──────────┐                               │
│                │ Strategy │  ← CPU (complex logic)        │
│                │  (CPU)   │                               │
│                └──────────┘                               │
└─────────────────────────────────────────────────────────┘
```

**When to use:** Market making, arbitrage, exchange matching  
**Latency:** 150–500 ns (FPGA path), 1–5 µs (CPU strategy path)  
**Key insight:** FPGAs provide determinism — same work in same cycles every time

### Pattern 2: Kernel Bypass (Network-Intensive)

```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│  NIC     │ ←→  │  User Space  │ ←→  │  App     │
│ (DPDK/   │ DMA │  PMD Driver  │     │  Logic   │
│  Onload) │     │  (no kernel) │     │          │
└──────────┘     └──────────────┘     └──────────┘
```

**When to use:** Packet processing, NFV, 5G UPF, security appliances  
**Latency:** 1–10 µs application-level  
**Key insight:** Eliminates context switches, interrupts, and kernel overhead

### Pattern 3: RDMA Fabric (Cross-Host)

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Host A  │ ←→  │ InfiniBand│ ←→  │  Host B  │
│  (ConnectX-7)  │  Switch   │     │  (ConnectX-7) │
│  400 Gb/s│     │  ~100 ns  │     │  400 Gb/s│
└──────────┘     └──────────┘     └──────────┘
```

**When to use:** HPC clusters, AI training, distributed storage  
**Latency:** 1–2 µs end-to-end  
**Key insight:** Full transport offload, zero-copy, kernel bypass built into hardware

### Pattern 4: DPU Offload (Cloud Infrastructure)

```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│  Host CPU│ ←→  │  DPU/SmartNIC│ ←→  │  Network │
│  (x86)   │ PCIe│  (BlueField) │     │  400G    │
│          │     │  OVS/Storage │     │          │
│          │     │  Crypto offload     │          │
└──────────┘     └──────────────┘     └──────────┘
```

**When to use:** Cloud virtualization, storage disaggregation, security  
**Latency:** 1–5 µs on-card processing  
**Key insight:** Frees host CPU for application logic; hardware offload for common operations

### Pattern 5: Cell-Based Architecture (Payments)

```
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Cell 1 │ │ Cell 2 │ │ Cell 3 │ │ Cell N │
│ 0.08%  │ │ 0.08% │ │ 0.08% │ │ 0.08%  │
│ traffic│ │ traffic│ │ traffic│ │ traffic│
└────────┘ └────────┘ └────────┘ └────────┘
     ↑           ↑           ↑          ↑
     └───────────┴───────────┴──────────┘
              Global Load Balancer
```

**When to use:** Payment processing, high-availability services  
**Latency:** 42 ms mean (Stripe), 89 ms p99  
**Key insight:** Failure in one cell affects ≤0.08% of traffic; independent scaling

---

## Hardware Layer

### FPGA Selection Guide

| Use Case | Recommended FPGA | Process | Key Feature |
|----------|-----------------|---------|-------------|
| HFT feed handling | Achronix Speedster7t | 7nm | 112G SerDes, 2D NoC |
| AI inference on edge | AMD Versal AI Edge | 7nm | AIE-ML engines, ASIL D |
| High-bandwidth networking | Intel Agilex 7 I-Series | 10nm | 116G SerDes, CXL |
| Ultra-low power | Lattice Nexus | 28nm FD-SOI | <1W, <500ns |
| Defense/aerospace | Microchip PolarFire | 28nm NV | SEU-immune, DPA-protected |
| SoC-integrated | Flex Logix eFPGA | 12–40nm | 1–2 cycle latency |

### NIC Selection

| NIC | Network | Use Case | Latency |
|-----|---------|----------|---------|
| NVIDIA ConnectX-7 | NDR 400G IB | HPC, AI training | ~100 ns switch |
| NVIDIA ConnectX-6 | RoCE v2 200G | Data center, storage | 1–3 µs |
| Intel E810 | iWARP 100G | WAN, legacy DC | 5–10 µs |
| Solarflare X2522 | Onload 10G | HFT kernel bypass | 1–2 µs |
| AMD Pollara 400 | Ultra Ethernet 400G | Hyperscale cloud | Sub-200 ns |

### CPU Considerations

- **Core isolation:** `isolcpus`, `nohz_full`, `rcu_nocbs` kernel parameters
- **Hugepages:** 1 GB pages for DPDK/SPDK memory pools
- **NUMA awareness:** Pin threads to cores near the NIC
- **Frequency scaling:** Disable for deterministic performance
- **Hyperthreading:** Disable on latency-critical cores

---

## Network Layer

### Interconnect Comparison

| Technology | Latency | Throughput | Cost | Best For |
|-----------|---------|------------|------|----------|
| InfiniBand NDR | 100–200 ns | 400–800 Gb/s | $$$$ | HPC, AI training |
| RoCE v2 | 1–3 µs | 100–400 Gb/s | $$ | Data center, storage |
| iWARP | 5–10 µs | 10–100 Gb/s | $$ | WAN, legacy DC |
| DPDK | 1–10 µs | 100+ Mpps | $ | Packet processing |
| P4 Switch | 100–500 ns | 6.5–12.8 Tb/s | $$$ | Programmable fabric |
| Optical Switch | 40 ns – 1 µs | 25–100 Gb/s/port | $$$$ | Future DCN |

### Network Topology Patterns

**HFT: Point-to-Point**
```
Exchange ←── Microwave/Fiber ──→ Trading Engine
         (4.7 ms Chicago-NY microwave)
```

**Data Center: Fat-Tree (Clos)**
```
  ┌─────┐ ┌─────┐ ┌─────┐
  │Leaf │ │Leaf │ │Leaf │  ← Top-of-Rack
  └──┬──┘ └──┬──┘ └──┬──┘
     │       │       │
  ┌──┴──┐ ┌──┴──┐ ┌──┴──┐
  │Spine│ │Spine│ │Spine│  ← Aggregation
  └─────┘ └─────┘ └─────┘
```

**Future: Optical Flat Network**
```
  ┌─────────────────────────┐
  │  High-Radix Optical     │
  │  Switch (1000+ ports)   │
  │  40 ns switching        │
  └──┬───┬───┬───┬───┬───┬──┘
     │   │   │   │   │   │
    N1  N2  N3  N4  N5  N6  ← All nodes equal distance
```

---

## Software Layer

### Kernel Bypass Stacks

**DPDK (Data Plane Development Kit)**
```c
// Minimal DPDK initialization pattern
#include <rte_eal.h>
#include <rte_ethdev.h>

int main(int argc, char *argv[]) {
    rte_eal_init(argc, argv);
    
    // Configure port
    struct rte_eth_conf port_conf = {
        .rxmode = { .max_rx_pkt_len = RTE_ETHER_MAX_LEN },
    };
    rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    
    // Setup memory pool with hugepages
    struct rte_mempool *mbuf_pool = rte_pktmbuf_pool_create(
        "MBUF_POOL", NUM_MBUFS, MBUF_CACHE_SIZE, 0,
        RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
    
    // RX/TX loop (polling, no interrupts)
    while (1) {
        rte_eth_rx_burst(port_id, 0, pkts, BURST_SIZE);
        // Process packets...
        rte_eth_tx_burst(port_id, 0, pkts, nb_pkts);
    }
}
```

**Onload (Solarflare ef_vi)**
```c
// Onload: kernel bypass with standard socket API
#include <onload/extensions.h>

int fd = socket(AF_INET, SOCK_STREAM, 0);
// Onload intercepts and bypasses kernel automatically
connect(fd, ...);  // Runs in user space
```

### RDMA Programming

**Verbs API (libibverbs)**
```c
// RDMA read/write with zero-copy
struct ibv_context *ctx = ibv_open_device(dev);
struct ibv_pd *pd = ibv_alloc_pd(ctx);
struct ibv_mr *mr = ibv_reg_mr(pd, buf, size, 
    IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_READ);

// Queue Pair setup
struct ibv_qp_init_attr qp_attr = {
    .send_cq = cq, .recv_cq = cq,
    .cap = { .max_send_wr = 16, .max_recv_wr = 16,
             .max_send_sge = 1, .max_recv_sge = 1 }
};
struct ibv_qp *qp = ibv_create_qp(pd, &qp_attr);

// RDMA READ: remote memory → local memory (no remote CPU involvement)
struct ibv_sge sge = { .addr = (uintptr_t)local_buf,
                       .length = 4096, .lkey = mr->lkey };
struct ibv_send_wr wr = {
    .wr_id = 1, .sg_list = &sge, .num_sge = 1,
    .opcode = IBV_WR_RDMA_READ,
    .wr.rdma = { .remote_addr = remote_addr, .rkey = remote_rkey }
};
ibv_post_send(qp, &wr, &bad_wr);
```

### P4 Program Structure

```p4
// P4 packet processing pipeline
parser MyParser(packet_in pkt, out headers hdr) {
    state start {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            0x0800: parse_ipv4;
            default: accept;
        }
    }
    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition accept;
    }
}

control MyControl(inout headers hdr) {
    action forward(bit<9> port) {
        standard_metadata.egress_spec = port;
    }
    
    table forwarding_table {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { forward; drop; }
        default_action = drop();
    }
    
    apply {
        forwarding_table.apply();
    }
}
```

---

## Data Flow Architecture

### HFT Market Data Pipeline

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Exchange │───→│  FPGA    │───→│  FPGA    │───→│  CPU     │
│  Wire    │    │  Feed    │    │  Order   │    │ Strategy │
│  (UDP)   │    │  Handler │    │  Book    │    │ Engine   │
└─────────┘    └──────────┘    └──────────┘    └──────────┘
     │              │                │               │
   ~0 ns         ~200 ns          ~100 ns          ~1 µs
                  (decode)        (update)        (decide)
```

### Payment Authorization Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Merchant │───→│  API     │───→│  Auth    │───→│  Card    │
│  Client  │    │  Gateway │    │  Engine  │    │  Network │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │              │                │               │
   ~1 ms          ~5 ms            ~10 ms          ~30 ms
                  (routing)       (fraud check)   (issuer auth)
```

---

## Latency Budgeting

### How to Allocate Your Budget

Every ULL system has a total latency budget. Allocate it across stages:

**Example: HFT tick-to-trade (500 ns budget)**

| Stage | Budget | Technology |
|-------|--------|------------|
| Wire propagation | 100 ns | Microwave |
| PHY/MAC | 50 ns | FPGA |
| Feed decode | 100 ns | FPGA |
| Order book update | 100 ns | FPGA |
| Strategy decision | 100 ns | CPU (cache-hot) |
| Order encode | 30 ns | FPGA |
| Wire propagation | 20 ns | Microwave |
| **Total** | **500 ns** | |

**Example: Payment authorization (100 ms budget)**

| Stage | Budget | Technology |
|-------|--------|------------|
| Client → API GW | 20 ms | Internet |
| API GW → Auth | 5 ms | gRPC (internal) |
| Fraud check | 30 ms | ML inference |
| Card network | 35 ms | Visa/Mastercard |
| Response | 10 ms | Internet |
| **Total** | **100 ms** | |

### Measuring Latency

```c
// High-resolution timestamping (x86)
#include <x86intrin.h>

static inline uint64_t rdtsc(void) {
    return __rdtsc();
}

// Usage: measure stage latency
uint64_t t0 = rdtsc();
process_market_data();
uint64_t t1 = rdtsc();
uint64_t cycles = t1 - t0;
double nanoseconds = cycles / cpu_freq_ghz;
```

---

## Fault Tolerance & Redundancy

### HFT Redundancy Pattern

```
┌──────────────┐     ┌──────────────┐
│  Primary     │     │  Secondary   │
│  FPGA Card   │←───→│  FPGA Card   │
│  (Active)    │     │  (Hot Standby)│
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                │
         ┌──────┴───────┐
         │   Exchange   │
         └──────────────┘
```

- **Failover time:** <1 µs (FPGA-based) or <1 ms (software-based)
- **State sync:** Continuous mirroring of order book state
- **Split-brain prevention:** Consensus protocol or hardware arbiter

### Payment Cell-Based Redundancy

- Each cell operates independently (≤0.08% traffic per cell)
- Automated remediation for 82+ common failure scenarios
- Multi-region active-active deployment
- Zero-downtime migrations via canary routing

---

## Security Architecture

### FPGA Security

| Threat | Mitigation |
|--------|-----------|
| Bitstream tampering | DPA-protected bitstream (PolarFire) |
| Side-channel attacks | Constant-time logic, power balancing |
| Fault injection | SEU-immune fabric (non-volatile) |
| Physical tampering | Tamper detection, secure boot |

### Network Security

| Layer | Technology | Latency Impact |
|-------|-----------|----------------|
| Encryption | IPsec offload (DPU) | <150 ns overhead |
| TLS | Hardware TLS offload | ~30–50% improvement |
| DDoS | P4 switch (line-rate) | 2.1–4.6 µs detection |
| Microsegmentation | DPU policy engine | <1 µs per packet |

### Payment Security

- Zero-trust architecture (NIST SP 800-207)
- AI-powered real-time fraud detection
- Tokenization (card numbers never touch merchant systems)
- Multi-region canary routing for zero-downtime security updates

---

## Design Checklist

Use this checklist when designing a ULL system:

- [ ] **Define latency budget** — total and per-stage
- [ ] **Choose hardware** — FPGA, NIC, CPU, DPU
- [ ] **Select interconnect** — InfiniBand, RoCE, DPDK, P4
- [ ] **Design data flow** — pipeline stages, serialization points
- [ ] **Plan redundancy** — failover strategy, state sync
- [ ] **Security review** — encryption, access control, tamper resistance
- [ ] **Measurement plan** — how will you verify latency?
- [ ] **Jitter analysis** — p50, p99, p99.9, max
- [ ] **Failure modes** — what happens when each component fails?
- [ ] **Operational runbook** — monitoring, alerting, recovery

---

## Further Reading

- [FPGA Technologies Report](../reports/fpga-technologies.md) — Detailed FPGA comparison
- [Network Technologies Report](../reports/network-technologies.md) — RDMA, DPU, P4, optical
- [HFT Firms Report](../reports/hft-firms.md) — Industry practices and benchmarks
- [Payment Networks Report](../reports/payment-networks.md) — Payment system architecture
- [Gaming Report](../reports/gaming.md) — Gaming latency technologies
- [API Reference](api-reference.md) — Technology interfaces and configurations
- [Tutorials](tutorials/) — Hands-on implementation guides
