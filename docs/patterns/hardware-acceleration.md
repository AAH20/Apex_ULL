# Hardware Acceleration Pattern for Ultra-Low-Latency Infrastructure

> Pattern catalog: FPGA, ASIC, GPU, DPU, SmartNIC pipelines
> Compiled: September 2026
> Source data: reports/fpga-technologies.md, reports/network-technologies.md, reports/hft-firms.md

---

## 1. Pattern Overview

Ultra-low-latency (ULL) systems require hardware acceleration when software-only approaches cannot meet the latency budget. Five primary acceleration patterns exist, each with distinct trade-offs across latency, throughput, power, cost, and programmability.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ULL Hardware Acceleration Stack                  │
├──────────┬──────────┬──────────┬──────────┬──────────────────────────┤
│  FPGA    │  ASIC    │  GPU     │  DPU     │  SmartNIC                │
│  ~ns-µs  │  ~ns     │  ~µs-ms  │  ~µs     │  ~ns-µs                  │
│  Flexible│  Fixed   │  Parallel│  Offload │  Network-first           │
└──────────┴──────────┴──────────┴──────────┴──────────────────────────┘
```

---

## 2. FPGA Pipeline Pattern

### 2.1 Architecture

```
Network → [SerDes] → [MAC] → [Pipeline Logic] → [Decision] → [TX]
                        ↓
                   [Order Book BRAM]
                        ↓
                   [Risk Check]
```

FPGAs provide reconfigurable hardware pipelines where each stage is a physical circuit. The entire tick-to-trade path can be implemented in programmable logic with deterministic, cycle-accurate timing.

### 2.2 Latency Profile

| Metric | Value | Notes |
|--------|-------|-------|
| Wire-to-wire (tick-to-trade) | 150–500 ns | Full FPGA pipeline |
| PHY+MAC round-trip | 89.6 ns | Algo-Logic CME T2T |
| Deterministic control loops | <500 ns | Lattice Nexus |
| Sub-µs pipelines | <1,000 ns | All major FPGA families |
| Jitter | Very low (ns-level) | Deterministic by design |

### 2.3 Throughput

| Device Class | Line Rate | Packet Rate | Orders/Sec |
|--------------|-----------|-------------|------------|
| Lattice Nexus (small) | 10–16 Gbps | ~15 Mpps | ~50K |
| Microchip PolarFire | 12.7 Gbps | ~18 Mpps | ~100K |
| AMD Versal AI Edge | 32 Gbps | ~47 Mpps | ~150K |
| Intel Agilex 7 | 116 Gbps | ~170 Mpps | ~200K |
| Achronix Speedster7t | 112 Gbps | ~165 Mpps | ~200K |

### 2.4 Power Consumption

| Device | Process | Power Range | Power Efficiency |
|--------|---------|-------------|------------------|
| Lattice Nexus | 28nm FD-SOI | <1–5W | Best (4× lower than peers) |
| Microchip PolarFire | 28nm NV | 3.5W typical | Excellent (50% lower than SRAM) |
| AMD Versal AI Edge | 7nm | 15–75W | Good |
| Intel Agilex 7 | 10nm SuperFin | 10–100W+ | Moderate |
| Achronix Speedster7t | 7nm | 50–150W+ | Lower (high perf) |

### 2.5 Cost

| Device | Dev Kit | Production Unit | Cost Tier |
|--------|---------|-----------------|-----------|
| Lattice Nexus | $500–$2K | $10–$100 | $ |
| Microchip PolarFire | $500–$2K | $50–$500 | $$ |
| AMD Versal AI Edge | $5K–$15K | $500–$10K+ | $$$$ |
| Intel Agilex 7 | $5K–$10K | $500–$15K+ | $$$$ |
| Achronix Speedster7t | $10K–$50K+ | $5K–$25K+ | $$$$$ |

### 2.6 Programmability

| Aspect | Rating | Details |
|--------|--------|---------|
| Reconfigurability | ★★★★★ | Full bitstream reconfiguration |
| HLS support | ★★★★ | Vitis HLS, Intel HLS, Catapult |
| HDL required | ★★★★★ | Verilog/VHDL/SystemVerilog for best results |
| Partial reconfig | ★★★★ | Dynamic function swap without downtime |
| Time-to-market | ★★★ | Weeks to months (vs. years for ASIC) |
| Team expertise | ★★★ | Specialized FPGA engineers needed |

### 2.7 Best For

- **HFT tick-to-trade**: Sub-µs deterministic pipelines (all major HFT firms use FPGAs)
- **Protocol bridging**: Custom network protocols at line rate
- **Pre-trade risk checks**: Hardware-accelerated order validation
- **Sensor fusion**: Real-time parallel processing near sensors
- **AI inference at edge**: Quantized neural networks on FPGA (Jump Trading: 1.2 µs inference)

### 2.8 Real-World Deployments

| Firm | FPGA Use | Measured Latency |
|------|----------|------------------|
| Citadel Securities | FPGA gateways, kernel bypass | Sub-100 ms execution |
| Jump Trading | Xilinx UltraScale+, ML inference | 1.2 µs median round-trip |
| HRT | AMD FPGAs, SystemVerilog | <10 ns data structure alignment |
| Optiver | Xilinx FPGAs, Verilog | <500 ns options quoting |
| IMC Trading | FPGA (Verilog/SV/VHDL) | 480 ns average latency |

---

## 3. ASIC Pipeline Pattern

### 3.1 Architecture

```
Network → [SerDes] → [Fixed-Function Pipeline] → [Decision] → [TX]
                        ↓
                   [Hardwired Logic]
                        ↓
                   [Fixed Risk Engine]
```

ASICs implement the entire pipeline as fixed-function silicon. No programmability after fabrication, but absolute minimum latency and power per operation.

### 3.2 Latency Profile

| Metric | Value | Notes |
|--------|-------|-------|
| Wire-to-wire | <25 ns | Research benchmarks (fastest published) |
| Gate-level delay | 1–10 ns | Simple combinational paths |
| Full pipeline | 50–200 ns | Depends on complexity |
| Jitter | Lowest possible | Zero reconfiguration overhead |

### 3.3 Throughput

| Implementation | Line Rate | Packet Rate | Notes |
|----------------|-----------|-------------|-------|
| Custom HFT ASIC | 100–400 Gbps | 150–600 Mpps | Fixed protocol |
| Network processor ASIC | 400 Gbps | ~600 Mpps | Broadcom Tomahawk class |
| P4 switch ASIC | 6.5–12.8 Tbps | 4.8 Bbps | Programmable data plane |

### 3.4 Power Consumption

| Metric | Value | Notes |
|--------|-------|-------|
| Power per operation | Lowest | No configuration overhead |
| Power per port | 4.2–4.9 W | Switch ASICs |
| Total (switch ASIC) | 200–500W | Full switch |
| vs. FPGA | 3–10× lower | For equivalent function |

### 3.5 Cost

| Cost Component | Range | Notes |
|----------------|-------|-------|
| NRE (mask + design) | $5M–$50M+ | One-time, process-node dependent |
| Unit cost (at volume) | $50–$500 | High volume amortizes NRE |
| Development time | 12–36 months | Full design → tapeout → validation |
| Break-even volume | 100K+ units | vs. FPGA total cost of ownership |

### 3.6 Programmability

| Aspect | Rating | Details |
|--------|--------|---------|
| Post-fabrication change | ✗ | Fixed function |
| P4 programmability | ★★★★ | P4-capable switch ASICs (Tofino) |
| Firmware updates | ★★★ | Microcode on embedded cores |
| Time-to-market | ★★ | 12–36 months |
| Team expertise | ★★ | ASIC design + verification engineers |

### 3.7 Best For

- **Ultra-high-volume, fixed-function workloads**: Where NRE is amortized
- **Absolute lowest latency**: No reconfiguration overhead
- **Power-constrained environments**: Minimum energy per operation
- **Standard protocol processing**: Fixed network protocols at scale

### 3.8 Trade-offs

- **Pros**: Lowest latency, lowest power per op, highest throughput at volume
- **Cons**: Highest NRE, zero post-fabrication flexibility, long development cycles, high risk (spins cost $1M+)

---

## 4. GPU Pipeline Pattern

### 4.1 Architecture

```
Network → [CPU] → [PCIe] → [GPU] → [Compute] → [Result] → [PCIe] → [CPU] → [TX]
```

GPUs provide massive parallel compute but introduce PCIe and memory transfer overhead. Best for workloads where compute intensity justifies the transfer latency.

### 4.2 Latency Profile

| Metric | Value | Notes |
|--------|-------|-------|
| PCIe round-trip | 1–3 µs | Gen4/Gen5 x16 |
| Kernel launch | 5–20 µs | CUDA/OpenCL dispatch |
| End-to-end inference | 10–100 µs | Small model, PCIe-based |
| GPU-to-GPU (NVLink) | 100–200 ns | Direct GPU interconnect |
| GPUDirect RDMA | 1–2 µs | Network → GPU memory bypassing CPU |

### 4.3 Throughput

| Product | FP16 Compute | Memory Bandwidth | Notes |
|---------|-------------|-----------------|-------|
| NVIDIA H100 | ~990 TFLOPS | 3.35 TB/s HBM3 | Training + inference |
| NVIDIA RTX 5090 | ~112 TFLOPS | 1.8 TB/s GDDR7 | Gaming/prosumer |
| AMD MI300X | ~1,300 TFLOPS | 5.3 TB/s HBM3 | Training |
| AMD RX 9070 XT | ~94.7 TFLOPS | — | RDNA 4 |

### 4.4 Power Consumption

| Product | TDP | Performance/Watt |
|---------|-----|------------------|
| NVIDIA H100 SXM | 700W | High (datacenter-optimized) |
| NVIDIA RTX 5090 | 575W | Moderate |
| AMD MI300X | 750W | High |
| Intel Arc B580 | 190W | Moderate |

### 4.5 Cost

| Product | MSRP | Cost per TFLOPS |
|---------|------|-----------------|
| NVIDIA H100 | ~$30K–$40K | ~$35 |
| NVIDIA RTX 5090 | $1,999 | ~$18 |
| AMD RX 9070 XT | $549 | ~$6 |
| Intel Arc B580 | $249 | ~$12 |

### 4.6 Programmability

| Aspect | Rating | Details |
|--------|--------|---------|
| Ecosystem maturity | ★★★★★ | CUDA, ROCm, oneAPI |
| Language support | ★★★★★ | C++, Python, CUDA, OpenCL |
| ML frameworks | ★★★★★ | PyTorch, TensorFlow, JAX |
| Real-time constraints | ★★ | Not deterministic (GC, scheduling) |
| Time-to-market | ★★★★★ | Software development only |

### 4.7 Best For

- **AI/ML inference at scale**: Where compute intensity justifies transfer overhead
- **Batch processing**: Non-real-time analytics, backtesting
- **Research and prototyping**: Rapid iteration on models
- **GPUDirect RDMA**: Network-to-GPU zero-copy pipelines

### 4.8 Real-World Deployments

| Firm | GPU Use | Measured Latency |
|------|---------|------------------|
| Jump Trading | 12,000 H100 nodes, HPC | 1.7 µs CPU-GPU (vs 1.2 µs FPGA) |
| HRT | NVIDIA Vera Rubin NVL72 (research) | — |
| Tower Research | GPU/HPC clusters, foundation models | — |

---

## 5. DPU Pipeline Pattern

### 5.1 Architecture

```
Network → [DPU: ARM cores + NIC + Accelerators] → [Offloaded Processing] → [Host]
```

DPUs (Data Processing Units) integrate ARM cores, network interfaces, and hardware accelerators on a single card, offloading infrastructure tasks from the host CPU.

### 5.2 Latency Profile

| Metric | Value | Notes |
|--------|-------|-------|
| Port-to-port | 1–5 µs | On-card processing |
| IPsec encryption | <150 ns overhead | Hardware offload |
| OVS offload | 1,800% throughput improvement | vs. software |
| P99 latency reduction | 4× (48 ms → 12 ms) | Edge AI workloads |
| RDMA RTT | ~2 µs | RoCEv2 |

### 5.3 Throughput

| DPU | Network | Packet Rate | Crypto | ARM Cores |
|-----|---------|-------------|--------|-----------|
| NVIDIA BlueField-3 | 400 Gb/s | 80 Mpps | 200 Gb/s | 16× A78AE |
| NVIDIA BlueField-4 | 800 Gb/s | 117 Mpps | — | 64× Vera |
| Intel IPU E2100 | 200 Gb/s | 200 Mpps | 170 Gb/s IPsec | 16× N1 |
| AMD Pensando Salina | 400 Gb/s | 117 Mpps | Hardware | 16× N1 |

### 5.4 Power Consumption

| DPU | TDP | Notes |
|-----|-----|-------|
| NVIDIA BlueField-3 | 75–150W | Highest power |
| Intel IPU E2100 | 20–30W | Most efficient |
| AMD Pensando Salina | ~50W | Moderate |

### 5.5 Cost

| DPU | Price | Ecosystem |
|-----|-------|-----------|
| NVIDIA BlueField-3 | ~$2,200 | DOCA SDK (NVIDIA lock-in) |
| Intel IPU E2100 | ~$1,500–$2,500 | IPDK, P4 toolchain |
| AMD Pensando Salina | ~$1,800–$2,800 | P4, AMD ecosystem |

### 5.6 Programmability

| Aspect | Rating | Details |
|--------|--------|---------|
| P4 programmability | ★★★★ | Intel IPU, AMD Pensando |
| SDK ecosystem | ★★★ | DOCA (NVIDIA), IPDK (Intel) |
| ARM core flexibility | ★★★★ | General-purpose processing |
| Time-to-market | ★★★ | Medium (SDK learning curve) |
| Vendor lock-in | ★★ | High (especially NVIDIA DOCA) |

### 5.7 Best For

- **Cloud infrastructure offload**: OVS, storage, security
- **AI training clusters**: GPUDirect RDMA, SHARP collective offload
- **Storage disaggregation**: NVMe-oF, SPDK acceleration
- **Zero-trust networking**: Microsegmentation, encryption offload
- **Multi-tenant isolation**: Hardware-enforced security boundaries

---

## 6. SmartNIC Pipeline Pattern

### 6.1 Architecture

```
Network → [SmartNIC: FPGA/ASIC + CPU] → [Kernel Bypass] → [App]
```

SmartNICs sit between the network and host, providing kernel-bypass packet processing with varying degrees of programmability. The line between SmartNIC and DPU is blurring; SmartNICs typically emphasize network processing while DPUs emphasize infrastructure offload.

### 6.2 Latency Profile

| Metric | Value | Notes |
|--------|-------|-------|
| Kernel bypass (DPDK) | 1–10 µs | Application-level |
| FPGA-based NIC | 100 ns – 1 µs | Deterministic |
| RDMA (RoCE v2) | 1–3 µs | End-to-end |
| RDMA (InfiniBand) | 100–200 ns | Switch port-to-port |
| Onload (kernel bypass) | 1–5 µs | Solarflare/Xilinx |

### 6.3 Throughput

| NIC Type | Line Rate | Packet Rate | Notes |
|----------|-----------|-------------|-------|
| Standard NIC | 100–400 Gb/s | — | No offload |
| FPGA SmartNIC | 100–400 Gb/s | 100+ Mpps | Programmable |
| DPU (BlueField-3) | 400 Gb/s | 80 Mpps | Full offload |
| DPU (Salina) | 400 Gb/s | 117 Mpps | P4 programmable |

### 6.4 Power Consumption

| NIC Type | Power | Notes |
|----------|-------|-------|
| Standard NIC | 10–25W | No acceleration |
| FPGA SmartNIC | 25–75W | Depends on FPGA |
| DPU | 75–150W | Full infrastructure offload |

### 6.5 Cost

| NIC Type | Price | Notes |
|----------|-------|-------|
| Standard NIC | $100–$500 | No acceleration |
| FPGA SmartNIC | $1K–$5K | CSPi, Algo-Logic |
| DPU | $1.5K–$5K | BlueField, IPU, Pensando |

### 6.6 Programmability

| Aspect | Rating | Details |
|--------|--------|---------|
| Kernel bypass maturity | ★★★★★ | DPDK, SPDK, Onload |
| P4 programmability | ★★★★ | Select SmartNICs |
| eBPF/XDP | ★★★★ | Linux kernel native |
| Time-to-market | ★★★★ | Software-defined |
| Hardware dependency | ★★★ | Varies by NIC |

### 6.7 Best For

- **Kernel bypass networking**: DPDK/SPDK for existing applications
- **Protocol acceleration**: RDMA offload for storage/compute
- **Network function virtualization**: vRouter, vFirewall, vLB
- **5G UPF**: User plane function acceleration
- **Security**: TLS/IPsec/DPI offload

---

## 7. Comparative Matrix

### 7.1 Latency Hierarchy (Fastest to Slowest)

| Rank | Technology | Typical Latency | Jitter | Determinism |
|------|-----------|-----------------|--------|-------------|
| 1 | ASIC | <25 ns–200 ns | Lowest | Perfect |
| 2 | FPGA | 150 ns–1 µs | Very low | Excellent |
| 3 | SmartNIC (FPGA) | 100 ns–1 µs | Very low | Excellent |
| 4 | DPU | 1–5 µs | Low | Good |
| 5 | GPU (PCIe) | 10–100 µs | Moderate | Poor |
| 6 | GPU (NVLink) | 100–200 ns | Low | Good |
| 7 | Kernel bypass (DPDK) | 1–10 µs | Moderate | Good |
| 8 | Kernel TCP | 10–50 µs | High | Poor |

### 7.2 Throughput Comparison

| Technology | Max Line Rate | Packet Rate | Compute |
|-----------|---------------|-------------|---------|
| ASIC | 12.8 Tbps | 4.8 Bpps | Fixed function |
| FPGA | 116 Gbps | 170 Mpps | 61 TOPS (Speedster7t) |
| GPU | N/A | N/A | 1,300 TFLOPS (MI300X) |
| DPU | 800 Gb/s | 117 Mpps | 11.2 TIPS (BF-4) |
| SmartNIC | 400 Gb/s | 100+ Mpps | Varies |

### 7.3 Power Efficiency (Operations per Watt)

| Rank | Technology | Efficiency | Notes |
|------|-----------|------------|-------|
| 1 | ASIC | Highest | No overhead |
| 2 | FPGA (Lattice Nexus) | <1W fabric | Best FPGA efficiency |
| 3 | FPGA (PolarFire) | 3.5W typical | Non-volatile advantage |
| 4 | DPU (Intel IPU) | 20–30W | Efficient infrastructure |
| 5 | FPGA (7–10nm) | 15–150W | Performance trade-off |
| 6 | GPU | 575–750W | Compute-intensive only |

### 7.4 Cost Efficiency (Performance per Dollar)

| Rank | Technology | Cost Model | Break-even |
|------|-----------|------------|------------|
| 1 | SmartNIC (DPDK) | $0 (software) + NIC | Immediate |
| 2 | GPU (AMD) | $6/TFLOPS | Volume compute |
| 3 | FPGA (Lattice) | $10–$100/unit | Low volume |
| 4 | DPU | $1.5K–$5K/card | Infrastructure |
| 5 | FPGA (7nm) | $500–$25K/unit | Medium volume |
| 6 | ASIC | $5M+ NRE | 100K+ units |

### 7.5 Programmability vs. Performance Trade-off

```
High Performance ──────────────────────────────────► High Programmability
  │                                                        │
  │  ASIC ◄──── FPGA ◄──── DPU ◄──── SmartNIC ◄──── GPU  │
  │  (fixed)   (reconfig)  (P4/SDK)  (DPDK/P4)   (CUDA)  │
  │                                                        │
  │  Lowest latency ◄──────────────────────► Fastest dev   │
  │  Highest NRE ◄──────────────────────────► Lowest NRE  │
  └────────────────────────────────────────────────────────┘
```

---

## 8. Selection Guide by Use Case

### 8.1 By Latency Budget

| Latency Budget | Recommended Pattern | Example |
|----------------|-------------------|---------|
| <100 ns | ASIC | Custom HFT chip |
| 100–500 ns | FPGA | Tick-to-trade pipeline |
| 500 ns–1 µs | FPGA / SmartNIC | Feed handler + risk |
| 1–5 µs | DPU / SmartNIC | OVS offload, storage |
| 5–20 µs | DPDK / GPU (NVLink) | Inference, analytics |
| 20–100 µs | GPU (PCIe) | Batch inference |
| >100 µs | CPU + software | General purpose |

### 8.2 By Workload Type

| Workload | Recommended Pattern | Rationale |
|----------|-------------------|-----------|
| HFT market data | FPGA | Deterministic, sub-µs |
| HFT ML inference | FPGA (quantized) | 1.2 µs vs 1.7 µs GPU |
| AI training | GPU (H100/MI300X) | Massive parallel compute |
| AI inference (edge) | FPGA / GPU | Depends on model size |
| Network security | DPU / SmartNIC | Line-rate inspection |
| Storage offload | DPU (NVMe-oF) | Kernel bypass + RDMA |
| Cloud virtualization | DPU | OVS, storage, security |
| Protocol bridging | FPGA | Custom protocol support |
| 5G UPF | SmartNIC / DPU | Line-rate packet processing |

### 8.3 By Budget

| Budget | Recommended Stack | Total Cost |
|--------|-------------------|------------|
| **$** | DPDK/SPDK + standard NICs | <$1K |
| **$$** | RoCE v2 + ConnectX NICs | $1K–$5K |
| **$$$** | FPGA dev kit + DPDK | $5K–$15K |
| **$$$$** | DPU (BlueField/IPU) | $2K–$5K/card |
| **$$$$$** | Full FPGA deployment | $10K–$50K+ |
| **$$$$$$** | ASIC tapeout | $5M+ NRE |

### 8.4 By Team Expertise

| Team Skill | Recommended Pattern | Learning Curve |
|-----------|-------------------|----------------|
| Software only | DPDK/SPDK + SmartNIC | Low |
| FPGA/HDL | FPGA pipeline | Medium–High |
| ASIC design | ASIC | Very High |
| CUDA/GPU | GPU pipeline | Medium |
| P4 networking | DPU / SmartNIC | Medium |
| Systems/C++ | Any (integration) | Varies |

---

## 9. Hybrid Patterns

### 9.1 FPGA + CPU (Most Common in HFT)

```
Market Data → [FPGA: decode + order book + risk] → [CPU: strategy] → [FPGA: encode] → Exchange
```

- FPGA handles: Market data decoding, order book updates, pre-trade risk, order encoding
- CPU handles: Strategy logic, parameter updates, position tracking, P&L
- **Key insight**: FPGAs provide determinism, not just speed — same work in same cycles every time

### 9.2 DPU + GPU (AI Training Clusters)

```
GPU ← [NVLink] → GPU ← [NVLink] → GPU
  ↓                              ↑
[BlueField DPU] ←── InfiniBand ──→ [BlueField DPU]
```

- DPU handles: Network, storage, security offload
- GPU handles: Compute-intensive training
- GPUDirect RDMA: Network → GPU memory zero-copy

### 9.3 SmartNIC + FPGA (Network Function Acceleration)

```
Network → [SmartNIC: kernel bypass] → [FPGA: custom processing] → [Host]
```

- SmartNIC handles: Kernel bypass, basic packet processing
- FPGA handles: Custom protocol, deep packet inspection, encryption

### 9.4 Full Hardware Pipeline (Fastest)

```
Network → [FPGA: feed handler] → [FPGA: strategy] → [FPGA: order encoder] → Exchange
                ↓
         [CPU: monitoring only]
```

- Entire tick-to-trade in FPGA
- CPU only for monitoring, logging, parameter updates
- Achieves 150–500 ns wire-to-wire

---

## 10. Decision Flowchart

```
START: What is your latency budget?
│
├─ <1 µs ──► FPGA or ASIC
│             │
│             ├─ Need reconfigurability? ──► FPGA
│             └─ Fixed function, high volume? ──► ASIC
│
├─ 1–10 µs ──► DPU or SmartNIC
│              │
│              ├─ Infrastructure offload? ──► DPU
│              └─ Network processing only? ──► SmartNIC
│
├─ 10–100 µs ──► GPU (PCIe) or DPDK
│                │
│                ├─ Compute-intensive? ──► GPU
│                └─ Network-intensive? ──► DPDK
│
└─ >100 µs ──► CPU + software optimization
```

---

## 11. Key Takeaways

1. **For absolute lowest latency**: ASIC (<25 ns) or FPGA (150–500 ns)
2. **For best latency-power tradeoff**: Lattice Nexus FPGA (<1W, <500 ns)
3. **For highest bandwidth + latency**: Achronix Speedster7t (2D NoC, 112G SerDes)
4. **For AI + latency + safety**: AMD Versal AI Edge (ASIL D, AI Engines + PL)
5. **For data center + host coherence**: Intel Agilex 7 (CXL, PCIe Gen5)
6. **For cost-sensitive high-volume**: Lattice Nexus ($10–$100) or ASIC at scale
7. **For infrastructure offload**: DPU (BlueField, IPU, Pensando)
8. **For kernel bypass**: DPDK/SPDK on SmartNICs
9. **For compute-intensive workloads**: GPU (H100, MI300X)
10. **For HFT**: FPGA is the industry standard (all major firms use it)

---

## 12. References

- reports/fpga-technologies.md — FPGA vendor deep-dive
- reports/network-technologies.md — DPU/SmartNIC/RDMA comparison
- reports/hft-firms.md — HFT firm technology patterns
- reports/gaming.md — GPU latency/throughput data
- reports/payment-networks.md — Payment network latency benchmarks

---

*Pattern compiled: 2026-09-29*
