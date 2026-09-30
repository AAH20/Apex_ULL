# ULL Scalability Benchmark Suite

**Project:** ultra-low-latency-infra  
**Date:** September 2026  
**Scope:** Horizontal scaling, vertical scaling, linear speedup, Amdahl's law, Gustafson's law

---

## Table of Contents

1. [Horizontal Scaling](#horizontal-scaling)
2. [Vertical Scaling](#vertical-scaling)
3. [Linear Speedup](#linear-speedup)
4. [Amdahl's Law](#amdahls-law)
5. [Gustafson's Law](#gustafsons-law)
6. [Cross-Benchmark Comparison](#cross-benchmark-comparison)
7. [Unified Test Harness](#unified-test-harness)

---

## 1. Horizontal Scaling

### Definition

Horizontal scaling (scale-out) adds more nodes to a distributed system to increase aggregate throughput while maintaining or reducing per-request latency. In ULL infrastructure, this means deploying additional FPGA feed handlers, matching engine replicas, or strategy nodes across co-location sites.

### Measurement Methodology

#### 1.1 Test Topology

```
                    ┌─────────────┐
                    │  Load Gen   │
                    │  (Spirent/  │
                    │   Ixia)     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼──────┐ ┌──▼────────┐
        │  Node 1   │ │  Node 2  │ │  Node N   │
        │  FPGA +   │ │  FPGA +  │ │  FPGA +   │
        │  CPU      │ │  CPU     │ │  CPU      │
        └─────┬─────┘ └───┬──────┘ └──┬────────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │  Aggregator │
                    │  (Latency   │
                    │   + Tput)   │
                    └─────────────┘
```

#### 1.2 Scaling Dimensions

| Dimension | Variable | Range | Step |
|-----------|----------|-------|------|
| Node count | N | 1–64 | 1, 2, 4, 8, 16, 32, 64 |
| Message rate | R | 100K–100M msg/s | 10× increments |
| Payload size | S | 64B–4KB | 64, 256, 1024, 4096 |
| Fan-out pattern | F | unicast, multicast, broadcast | — |

#### 1.3 Metrics

| Metric | Symbol | Unit | Target |
|--------|--------|------|--------|
| Aggregate throughput | T(N) | msg/s | Linear: T(N) = N × T(1) |
| Per-node throughput | t(N) | msg/s | Constant: t(N) ≈ T(1) |
| End-to-end latency (p50) | L₅₀(N) | μs | Flat or sub-linear growth |
| End-to-end latency (p99) | L₉₉(N) | μs | < 2× L₅₀ |
| Latency jitter (σ) | σ(N) | μs | < 0.1 × L₅₀ |
| Efficiency | E(N) | % | E(N) = T(N)/(N×T(1)) × 100 |
| Cost per msg | C(N) | $/msg | Sub-linear decrease |

#### 1.4 Procedure

1. **Baseline (N=1):** Measure single-node throughput T(1) and latency L(1) at target message rate.
2. **Scale-out sweep:** For each N ∈ {2, 4, 8, 16, 32, 64}:
   a. Deploy N identical nodes with identical configuration.
   b. Distribute load evenly across all nodes.
   c. Run warm-up: 60 seconds at 50% target rate.
   d. Run measurement: 300 seconds at 100% target rate.
   e. Collect per-node and aggregate metrics.
3. **Contention test:** Repeat with shared resources (network switch, memory bus) to identify bottlenecks.
4. **Failure resilience:** Kill one node mid-run; measure recovery time and throughput degradation.

#### 1.5 Pass Criteria

- **Linear scaling:** E(N) ≥ 90% for N ≤ 16
- **Sub-linear acceptable:** E(N) ≥ 70% for N ≤ 64
- **Latency stability:** L₅₀(N) ≤ 1.2 × L₅₀(1) for N ≤ 16
- **No head-of-line blocking:** p99/p50 < 3.0

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| Compute nodes | 8 | 32 | Identical CPU, RAM, NIC |
| FPGA NICs | 8 × 10GbE | 32 × 100GbE | Solarflare/Mellanox with kernel bypass |
| Top-of-rack switch | 40GbE | 100GbE, cut-through | < 1μs port-to-port |
| Spine switches | 2 (HA) | 4+ | Non-blocking fabric |
| Load generator | 1 | 2 (HA) | Spirent/Ixia or custom FPGA |
| Timing source | GPS/PTP | GPS + PTP (IEEE 1588) | < 100ns sync accuracy |
| Cabling | DAC | DAC + fiber for spine | Matched lengths for sync |

### Software Requirements

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Kernel bypass | DPDK / Onload / ef_vi | Latest stable | Sub-μs packet I/O |
| Messaging | Nanomsg / ZeroMQ / custom | — | Inter-node communication |
| Serialization | FlatBuffers / Cap'n Proto / SBE | — | Zero-copy deserialization |
| Load balancer | Custom (consistent hashing) | — | Even distribution |
| Orchestration | Kubernetes / Slurm / custom | — | Node lifecycle |
| Monitoring | Prometheus + Grafana | — | Real-time metrics |
| Clock sync | PTP daemon (ptp4l) | — | Sub-μs time alignment |
| OS tuning | Linux kernel 6.x | — | IRQ affinity, isolcpu, hugepages |

---

## 2. Vertical Scaling

### Definition

Vertical scaling (scale-up) increases the resources of a single node — more CPU cores, faster memory, additional FPGA fabric, or upgraded NICs — to improve throughput and latency without adding nodes.

### Measurement Methodology

#### 2.1 Scaling Dimensions

| Dimension | Variable | Range | Step |
|-----------|----------|-------|------|
| CPU cores | C | 1–128 | 1, 2, 4, 8, 16, 32, 64, 128 |
| CPU frequency | f | 2.0–5.0 GHz | 0.2 GHz |
| Memory channels | M | 1–8 | 1, 2, 4, 8 |
| Memory speed | DDR | 3200–8000 MT/s | Generation steps |
| FPGA LUTs | L | 100K–3M | Device tier |
| NIC speed | S | 1–400 GbE | 1, 10, 25, 100, 400 |
| PCIe lanes | P | x4–x16 | x4, x8, x16 |

#### 2.2 Metrics

| Metric | Symbol | Unit | Target |
|--------|--------|------|--------|
| Single-thread throughput | T₁ | msg/s | Baseline |
| Multi-thread throughput | T(C) | msg/s | Near-linear with cores |
| Latency (p50) | L₅₀ | μs | Decreases with resources |
| Latency (p99) | L₉₉ | μs | Decreases with resources |
| IPC (instructions/cycle) | IPC | — | > 2.0 for optimized code |
| Cache hit rate | H | % | > 95% L1, > 90% L2 |
| Memory bandwidth utilization | BW | % | < 80% of peak |
| Power efficiency | P | msg/J | Increases with scale |

#### 2.3 Procedure

1. **Baseline:** Measure single-core, single-thread performance with minimal resources.
2. **Core scaling:** Pin threads to physical cores (1, 2, 4, 8, ...). Measure throughput and latency at each level.
3. **Frequency scaling:** Lock CPU at each frequency step; measure latency-sensitive workload performance.
4. **Memory scaling:** Vary memory channels and speed; measure bandwidth-bound workload.
5. **FPGA scaling:** Deploy workloads of increasing complexity on FPGA; measure throughput vs. LUT utilization.
6. **NIC scaling:** Upgrade NIC speed; measure packet processing throughput.
7. **Thermal/power monitoring:** Log power draw at each configuration; compute energy per message.

#### 2.4 Pass Criteria

- **Core scaling efficiency:** T(C)/T(1) ≥ 0.85 × C for C ≤ 16
- **Latency improvement:** L₅₀(C) ≤ L₅₀(1) / √C for C ≤ 16
- **Memory bandwidth:** Achieve > 80% of theoretical peak
- **FPGA utilization:** > 70% LUTs at target throughput
- **Power efficiency:** P(C) ≥ 1.5 × P(1) for C = 4

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| CPU | 16-core x86_64 | 64-core x86_64 or ARM | High single-thread perf + many cores |
| RAM | 64 GB DDR4 | 512 GB DDR5 | 8 channels, ECC |
| FPGA | Xilinx Alveo U25 | Xilinx Versal HBM | On-board HBM for buffering |
| NIC | 10GbE | 100GbE with FPGA | Kernel bypass capable |
| Storage | NVMe SSD | NVMe SSD (gen4/5) | For logging and replay |
| Cooling | Air | Liquid | Sustained boost clocks |
| PSU | 800W | 1600W+ | Headroom for peak draw |
| Timing | PTP | GPS + PTP | Sub-μs accuracy |

### Software Requirements

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Compiler | GCC 13+ / Clang 17+ | — | -O3, -march=native, LTO |
| Profiling | perf, Intel VTune | — | Hotspot analysis |
| Memory allocator | jemalloc / mimalloc / tcmalloc | — | Low-fragmentation |
| Threading | C++20 std::thread / TBB | — | Work-stealing scheduler |
| FPGA toolchain | Vitis / Quartus | — | Synthesis, place-and-route |
| Kernel | Linux 6.x (PREEMPT_RT) | — | Real-time scheduling |
| NUMA | numactl, libnuma | — | Memory locality |
| Hugepages | 1GB/2MB | — | TLB miss reduction |

---

## 3. Linear Speedup

### Definition

Linear speedup is the ideal scaling scenario where performance increases proportionally with added resources. For ULL systems, this means doubling nodes or cores exactly doubles throughput with no latency penalty.

### Measurement Methodology

#### 3.1 Speedup Definition

```
S(N) = T(1) / T(N)
```

Where:
- S(N) = speedup with N resources
- T(1) = execution time with 1 resource
- T(N) = execution time with N resources

**Linear speedup:** S(N) = N

#### 3.2 Test Workloads

| Workload | Description | Parallelizable Fraction |
|----------|-------------|------------------------|
| Market data processing | Parse and normalize market data feeds | ~99% |
| Order book reconstruction | Build L2/L3 order books from increments | ~95% |
| Risk checks | Pre-trade risk validation | ~98% |
| Signal computation | Alpha signal calculation across instruments | ~99% |
| Backtesting | Historical strategy simulation | ~99% |
| Log analysis | Post-trade analysis and reporting | ~90% |

#### 3.3 Metrics

| Metric | Symbol | Unit | Target |
|--------|--------|------|--------|
| Speedup | S(N) | × | S(N) = N (ideal) |
| Efficiency | E(N) | % | E(N) = S(N)/N × 100 = 100% |
| Scalability | Sc(N) | — | Sc(N) = S(N)/N |
| Overhead | O(N) | μs | O(N) < 0.05 × T(1) |
| Communication ratio | CR | % | CR < 5% of total time |

#### 3.4 Procedure

1. **Identify parallelizable fraction (p):** Profile the workload to determine the fraction that can be parallelized.
2. **Baseline (N=1):** Measure T(1) for the complete workload.
3. **Speedup sweep:** For each N ∈ {2, 4, 8, 16, 32, 64, 128}:
   a. Partition the workload into N independent tasks.
   b. Execute on N resources with minimal communication.
   c. Measure T(N) and compute S(N) = T(1)/T(N).
   d. Record efficiency E(N) = S(N)/N.
4. **Communication overhead test:** Introduce inter-node communication; measure overhead growth.
5. **Amdahl prediction:** Compare measured S(N) against Amdahl's law prediction (see §4).
6. **Gustafson prediction:** Compare against Gustafson's law prediction (see §5).

#### 3.5 Pass Criteria

- **Near-linear:** S(N) ≥ 0.95 × N for N ≤ 8
- **Acceptable:** S(N) ≥ 0.80 × N for N ≤ 32
- **Efficiency floor:** E(N) ≥ 60% for N ≤ 64
- **Overhead bound:** O(N) < 10% of T(N) for N ≤ 16

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| Compute nodes | 8 | 64 | Homogeneous cluster |
| Interconnect | 40GbE | 200GbE InfiniBand / RoCE | < 1μs latency, > 90% bisection BW |
| Shared storage | NFS | Lustre / GPFS | Parallel filesystem |
| Load generator | 1 | 4 | Distributed load generation |
| Timing | PTP | GPS + PTP | < 100ns sync |
| Switch fabric | Fat-tree | Fat-tree / dragonfly | Non-blocking |

### Software Requirements

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| MPI | OpenMPI / MPICH | — | Message passing |
| Shared memory | OpenMP / TBB | — | Intra-node parallelism |
| Task scheduler | Ray / Dask / custom | — | Work distribution |
| Data partitioning | Consistent hashing | — | Even load split |
| Communication | UCX / libfabric | — | Low-latency messaging |
| Profiling | Extrae / Score-P | — | Trace analysis |
| Verification | Custom checksum | — | Result correctness |

---

## 4. Amdahl's Law

### Definition

Amdahl's law models the theoretical speedup of a fixed-size workload when adding resources. It captures the diminishing returns imposed by the serial (non-parallelizable) fraction of the workload.

### Formula

```
S(N) = 1 / ((1 - p) + p/N)
```

Where:
- S(N) = maximum speedup with N processors
- p = parallelizable fraction (0 ≤ p ≤ 1)
- N = number of processors/resources
- (1 - p) = serial fraction

### Key Insights

| Serial Fraction (1-p) | Max Speedup (N→∞) | Speedup at N=64 | Speedup at N=128 |
|-----------------------|-------------------|-----------------|------------------|
| 0% | ∞ | 64× | 128× |
| 1% | 100× | 39.4× | 56.7× |
| 5% | 20× | 14.2× | 17.9× |
| 10% | 10× | 7.8× | 9.2× |
| 20% | 5× | 3.8× | 4.4× |
| 50% | 2× | 1.9× | 2.0× |

### Measurement Methodology

#### 4.1 Procedure

1. **Profile for serial fraction:** Use `perf`, VTune, or custom instrumentation to identify the serial fraction (1-p) of the target workload.
2. **Baseline measurement:** Measure T(1) — total execution time on a single resource.
3. **Parallel sweep:** For each N ∈ {2, 4, 8, 16, 32, 64, 128, 256}:
   a. Execute the workload on N resources.
   b. Measure T(N).
   c. Compute measured speedup: S_measured(N) = T(1)/T(N).
   d. Compute Amdahl prediction: S_amdahl(N) = 1/((1-p) + p/N).
   e. Compute deviation: Δ(N) = |S_measured(N) - S_amdahl(N)| / S_amdahl(N).
4. **Serial fraction sensitivity:** Repeat for p ∈ {0.5, 0.8, 0.9, 0.95, 0.99, 0.999}.
5. **Bottleneck identification:** If measured speedup deviates significantly from Amdahl prediction, identify the new bottleneck (memory bandwidth, synchronization, I/O).

#### 4.2 Metrics

| Metric | Symbol | Unit | Target |
|--------|--------|------|--------|
| Measured speedup | S_m(N) | × | — |
| Amdahl speedup | S_a(N) | × | — |
| Deviation | Δ(N) | % | < 10% |
| Serial fraction | 1-p | % | Minimize |
| Asymptotic limit | S(∞) | × | 1/(1-p) |
| Resource efficiency | E(N) | % | E(N) = S(N)/N |

#### 4.3 Pass Criteria

- **Model accuracy:** Δ(N) < 15% for all tested N
- **Serial fraction:** (1-p) < 5% for target workloads
- **Practical speedup:** S(16) ≥ 0.5 × S(∞)
- **Diminishing returns point:** Identify N* where S(N*) ≥ 0.8 × S(∞)

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| Compute nodes | 16 | 128 | Homogeneous |
| Profiling hardware | perf counters | Intel PT / AMD IBS | Precise tracing |
| Interconnect | 40GbE | 200GbE InfiniBand | Low latency |
| Shared memory | NUMA-aware | NUMA-optimized | For shared-memory tests |
| Storage | NVMe | NVMe + RAM disk | Eliminate I/O bottleneck |

### Software Requirements

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Profiling | perf, VTune, AMD uProf | — | Serial fraction analysis |
| Tracing | LTTng / BPF | — | Kernel-level tracing |
| Synchronization | C++20 atomics / TBB | — | Minimal lock contention |
| Task decomposition | OpenMP / TBB / Ray | — | Parallel execution |
| Modeling | Python (numpy/matplotlib) | — | Amdahl curve fitting |
| Visualization | Grafana / matplotlib | — | Speedup plots |

---

## 5. Gustafson's Law

### Definition

Gustafson's law models speedup when the problem size scales with the number of processors. Unlike Amdahl's law (fixed problem size), Gustafson assumes the workload grows to fill available resources — the realistic scenario for ULL systems processing increasing market data volumes.

### Formula

```
S(N) = N - α × (N - 1)
```

Or equivalently:

```
S(N) = (1 - p) + p × N
```

Where:
- S(N) = speedup with N processors
- p = parallelizable fraction
- N = number of processors
- α = serial fraction (α = 1 - p)

### Key Insights

| Serial Fraction (α) | Speedup at N=64 | Speedup at N=128 | Speedup at N=256 |
|---------------------|-----------------|------------------|------------------|
| 0% | 64× | 128× | 256× |
| 1% | 63.4× | 126.7× | 253.4× |
| 5% | 60.8× | 121.6× | 243.2× |
| 10% | 57.6× | 115.2× | 230.4× |
| 20% | 51.2× | 102.4× | 204.8× |
| 50% | 32.0× | 64.0× | 128.0× |

### Measurement Methodology

#### 5.1 Procedure

1. **Define workload scaling function:** W(N) = W(1) × N^β where β ∈ [0, 1]:
   - β = 1: Perfect scaling (workload grows linearly with N)
   - β = 0: Fixed workload (reduces to Amdahl's law)
   - β = 0.5: Sub-linear workload growth
2. **Baseline (N=1):** Measure T(1) for the unit workload W(1).
3. **Scaled sweep:** For each N ∈ {2, 4, 8, 16, 32, 64, 128, 256}:
   a. Scale workload: W(N) = W(1) × N^β.
   b. Execute on N resources.
   c. Measure T(N).
   d. Compute speedup: S(N) = T(1) × N^β / T(N) (normalized to unit work).
   e. Compute Gustafson prediction: S_gustafson(N) = N - α×(N-1).
4. **Sensitivity analysis:** Repeat for β ∈ {0.5, 0.75, 1.0} and α ∈ {0.01, 0.05, 0.10}.
5. **Throughput scaling:** Measure aggregate throughput T(N)/W(N) — should remain constant for perfect scaling.

#### 5.2 Metrics

| Metric | Symbol | Unit | Target |
|--------|--------|------|--------|
| Scaled speedup | S(N) | × | — |
| Gustafson speedup | S_g(N) | × | — |
| Deviation | Δ(N) | % | < 10% |
| Throughput per node | t(N) | msg/s | Constant |
| Workload scaling exponent | β | — | ≥ 0.9 |
| Latency at scale | L(N) | μs | Flat or decreasing |

#### 5.3 Pass Criteria

- **Model accuracy:** Δ(N) < 15% for all tested N
- **Throughput per node:** t(N) ≥ 0.9 × t(1) for N ≤ 64
- **Latency stability:** L₅₀(N) ≤ 1.1 × L₅₀(1) for N ≤ 64
- **Scaled efficiency:** E(N) ≥ 80% for N ≤ 128

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| Compute nodes | 16 | 256 | Homogeneous cluster |
| Interconnect | 40GbE | 400GbE InfiniBand | Low latency, high BW |
| Shared storage | Parallel FS | Lustre / GPFS / WEKA | Scalable throughput |
| Load generator | 4 | 16 | Distributed, scalable |
| Timing | PTP | GPS + PTP | < 100ns sync |
| Network topology | Fat-tree | Dragonfly / slimfly | Scalable bisection BW |

### Software Requirements

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| MPI | OpenMPI / MPICH | — | Scalable message passing |
| Distributed computing | Ray / Dask / Spark | — | Workload distribution |
| Data partitioning | Consistent hashing / range | — | Even distribution |
| Communication | UCX / libfabric / NCCL | — | Low-latency collective ops |
| Profiling | Extrae / Score-P / TAU | — | Scalability analysis |
| Modeling | Python (numpy/scipy) | — | Gustafson curve fitting |
| Visualization | Grafana / matplotlib | — | Scaled speedup plots |

---

## 6. Cross-Benchmark Comparison

| Aspect | Horizontal Scaling | Vertical Scaling | Linear Speedup | Amdahl's Law | Gustafson's Law |
|--------|-------------------|-----------------|----------------|--------------|-----------------|
| **Resource change** | Add nodes | Add resources per node | Add nodes/cores | Add nodes | Add nodes + grow workload |
| **Problem size** | Fixed | Fixed | Fixed | Fixed | Scales with N |
| **Key metric** | Aggregate throughput | Per-node throughput | S(N) = N | S(N) = 1/((1-p)+p/N) | S(N) = N-α(N-1) |
| **Bottleneck** | Network, synchronization | Memory bandwidth, thermals | Communication overhead | Serial fraction | Serial fraction + scaling |
| **ULL relevance** | Multi-site deployment | Single-node optimization | Ideal target | Realistic limit | Realistic growth |
| **Cost model** | $ per node | $ per upgrade | $ per node | $ per node | $ per node + $ per workload |

---

## 7. Unified Test Harness

### 7.1 Directory Structure

```
benchmarks/scalability/
├── README.md                    # This file
├── horizontal-scaling.md        # §1 detailed spec
├── vertical-scaling.md         # §2 detailed spec
├── linear-speedup.md            # §3 detailed spec
├── amdahls-law.md               # §4 detailed spec
├── gustafsons-law.md            # §5 detailed spec
├── scripts/
│   ├── run_horizontal.sh        # Horizontal scaling test
│   ├── run_vertical.sh          # Vertical scaling test
│   ├── run_speedup.sh           # Linear speedup test
│   ├── run_amdahl.sh          # Amdahl's law test
│   ├── run_gustafson.sh         # Gustafson's law test
│   └── common/
│       ├── metrics.sh           # Metric collection functions
│       ├── plot.sh              # Gnuplot/matplotlib plotting
│       └── report.sh            # Report generation
├── results/
│   ├── horizontal/
│   ├── vertical/
│   ├── speedup/
│   ├── amdahl/
│   └── gustafson/
└── config/
    ├── cluster.yaml             # Cluster topology
    ├── workloads.yaml            # Workload definitions
    └── thresholds.yaml           # Pass/fail thresholds
```

### 7.2 Common Configuration

```yaml
# config/cluster.yaml
cluster:
  name: ull-scalability-test
  nodes:
    - id: node-01
      role: compute
      cpu: "64-core x86_64"
      ram: "512GB DDR5"
      nic: "100GbE FPGA"
      fpga: "Xilinx Versal HBM"
    # ... additional nodes
  network:
    fabric: "InfiniBand NDR"
    topology: "fat-tree"
    latency_target: "< 1μs"
  timing:
    source: "GPS + PTP"
    accuracy: "< 100ns"

# config/workloads.yaml
workloads:
  market_data:
    type: "streaming"
    rate: "10M msg/s"
    payload: "256B"
    parallelizable: 0.99
  order_book:
    type: "stateful"
    rate: "1M updates/s"
    payload: "128B"
    parallelizable: 0.95
  risk_check:
    type: "request-response"
    rate: "100K req/s"
    payload: "1KB"
    parallelizable: 0.98

# config/thresholds.yaml
thresholds:
  horizontal:
    efficiency_min: 0.90
    latency_growth_max: 1.2
  vertical:
    core_scaling_min: 0.85
    memory_bw_min: 0.80
  speedup:
    linear_min: 0.95
    efficiency_floor: 0.60
  amdahl:
    deviation_max: 0.15
    serial_fraction_max: 0.05
  gustafson:
    deviation_max: 0.15
    throughput_per_node_min: 0.90
```

### 7.3 Execution Order

1. **Vertical scaling** first — establish single-node baseline.
2. **Horizontal scaling** second — measure multi-node behavior.
3. **Linear speedup** third — verify ideal scaling.
4. **Amdahl's law** fourth — model fixed-workload limits.
5. **Gustafson's law** fifth — model scaled-workload behavior.

### 7.4 Reporting

Each benchmark produces:
- Raw metrics (CSV/JSON)
- Plots (PNG/PDF): throughput vs. N, latency vs. N, speedup vs. N
- Summary report (Markdown): pass/fail, key findings, recommendations
- Comparison against theoretical models (Amdahl/Gustafson curves)

---

## References

1. Amdahl, G. M. (1967). "Validity of the single processor approach to achieving large scale computing capabilities." *AFIPS Conference Proceedings*.
2. Gustafson, J. L. (1988). "Reevaluating Amdahl's law." *Communications of the ACM*, 31(5), 532–533.
3. Hennessy, J. L., & Patterson, D. A. (2019). *Computer Architecture: A Quantitative Approach* (6th ed.). Morgan Kaufmann.
4. IEEE 2024 Study on FPGA-based ULL Systems.
5. CME Group Latency Statistics (2025).
6. Nasdaq INET Performance Benchmarks (2025).
