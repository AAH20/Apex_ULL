# ULL Power Evaluation Framework

**Version:** 1.0  
**Date:** 2026-09-29  
**Scope:** Ultra-low-latency infrastructure power evaluation — watts per operation, watts per message, energy efficiency, carbon footprint

---

## Table of Contents

1. [Overview](#overview)
2. [Metrics & Definitions](#metrics--definitions)
3. [Measurement Methodology](#measurement-methodology)
4. [Benchmark Standards](#benchmark-standards)
5. [Industry Averages](#industry-averages)
6. [Carbon Footprint](#carbon-footprint)
7. [Usage](#usage)
8. [Data Sources](#data-sources)

---

## Overview

This framework standardises power evaluation for ultra-low-latency (ULL) infrastructure across four dimensions:

| Dimension | Unit | Question Answered |
|-----------|------|-------------------|
| **Energy per Operation** | J/op | How much power per computational operation? |
| **Watts per Message** | W/msg | How much power per network message? |
| **Energy Efficiency** | ops/J or msg/J | How many operations per joule? |
| **Carbon Footprint** | gCO₂e/op | What is the carbon cost per operation? |

### Target Workloads

- **HFT/Trading:** FPGA tick-to-trade, order book updates, market data processing
- **Network:** RDMA/RoCE, DPDK packet processing, P4 switching
- **AI Inference:** FPGA-based ML inference, GPU inference
- **Payment Processing:** Transaction authorization, fraud detection
- **Gaming:** Render frames, physics simulation, network sync

---

## Metrics & Definitions

### Energy per Operation (J/op)

```
J/op = Total System Power (W) / Operations per Second (ops/s)
```

**Operation types:**
- **FPGA LUT operation:** One 6-input LUT evaluation
- **CPU instruction:** One retired instruction (IPC basis)
- **GPU FLOP:** One floating-point operation
- **Network operation:** One packet forwarded / routed
- **Storage operation:** One I/O operation (IOPS)

### Watts per Message (W/msg)

```
W/msg = Total System Power (W) / Messages per Second (msg/s)
```

**Message types:**
- **Network packet:** One Ethernet frame processed
- **RDMA message:** One RDMA send/receive
- **Order message:** One order entry/cancel/modify
- **Market data tick:** One price update processed

### Energy Efficiency

```
ops/J = Operations per Second (ops/s) / Total System Power (W)
msg/J = Messages per Second (msg/s) / Total System Power (W)
```

### Carbon Footprint

```
gCO₂e/op = (Total System Power (W) × PUE × Carbon Intensity (gCO₂e/kWh) × 3600) / ops/s
gCO₂e/msg = (Total System Power (W) × PUE × Carbon Intensity (gCO₂e/kWh) × 3600) / msg/s
```

Where:
- **PUE** (Power Usage Effectiveness): 1.0 (ideal) to 2.0 (typical data center)
- **Carbon Intensity:** Grid carbon intensity (gCO₂e/kWh)

---

## Measurement Methodology

### 1. Power Measurement

#### Hardware-Level Measurement

| Method | Accuracy | Cost | Use Case |
|--------|----------|------|----------|
| **INA219/INA260 I²C sensor** | ±1% | $5-20 | Board-level, FPGA/SoC |
| **Power analyzer (Yokogawa WT310)** | ±0.1% | $10K+ | Lab-grade system measurement |
| **Kill-A-Watt / smart PDU** | ±1-2% | $50-500 | Rack-level measurement |
| **BMC/IPMI power reporting** | ±5% | Free (built-in) | Server-level monitoring |
| **RAPL (Running Average Power Limit)** | ±5% | Free (Intel/AMD) | CPU package power |
| **NVIDIA DCGM / nvml** | ±5% | Free | GPU power monitoring |
| **Xilinx XPE / Intel Power Analyzer** | ±10% | Free (pre-silicon) | FPGA design estimation |

#### Software-Level Measurement

```python
# Intel RAPL
cat /sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj

# NVIDIA GPU
nvidia-smi --query-gpu=power.draw --format=csv

# AMD GPU
cat /sys/class/drm/card0/device/hwmon/hwmon*/power1_average

# IPMI
ipmitool sensor list | grep -i watts
```

### 2. Operation Counting

| Platform | Method | Overhead |
|----------|--------|----------|
| **CPU** | `perf stat -e instructions` | <1% |
| **FPGA** | Simulation + post-place-and-route | 0% (pre-silicon) |
| **GPU** | `ncu --metrics inst_executed` | 2-5% |
| **Network NIC** | ethtool -S / NIC registers | 0% |
| **DPDK** | rte_eth_stats | 0% |

### 3. Benchmark Standards

#### SPLASH-3 / SPECpower
- **SPECpower_ssj2008:** Server power/performance benchmark
- **SPLASH-3:** HPC benchmark suite
- **MLPerf Inference:** AI inference power benchmark

#### Network-Specific
- **RFC 2544:** Network device benchmark methodology
- **RFC 2889:** LAN switching benchmark
- **iperf3 / pkt-dpkt:** Throughput and latency benchmarking

#### FPGA-Specific
- **Xilinx XPE (Power Estimator):** Pre-implementation power estimation
- **Intel Power Analyzer:** Post-fit power analysis
- **Vivado Power Report:** Post-place-and-route power

### 4. Measurement Protocol

```
1. Idle baseline: Measure system power at idle for 5 minutes
2. Warm-up: Run workload for 10 minutes to reach thermal steady-state
3. Measurement: Record power + operations for 30 minutes
4. Repeat: 3 runs, report mean ± standard deviation
5. Environmental: Record ambient temperature, humidity
6. PUE adjustment: Multiply by facility PUE for total facility power
```

---

## Benchmark Standards

### FPGA Power Benchmarks

| Device | Process | Power Range | Typical Use | Source |
|--------|---------|-------------|-------------|--------|
| **AMD Versal AI Edge** | 7nm | 15-75W | AI inference + PL | AMD product brief |
| **Intel Agilex 7** | 10nm SuperFin | 10-100W+ | Networking, HPC | Intel datasheet |
| **Lattice Nexus** | 28nm FD-SOI | <1W-5W | Edge, sensor fusion | Lattice whitepaper |
| **Microchip PolarFire** | 28nm NV | 3.5W typical | Power-constrained | Microchip datasheet |
| **Achronix Speedster7t** | 7nm | 50-150W+ | HFT, AI inference | Achronix datasheet |
| **Flex Logix eFPGA** | 12-40nm | 5-10× lower than discrete | SoC integration | Flex Logix brief |

### Network Power Benchmarks

| Technology | Power | Latency | Throughput | Source |
|------------|-------|---------|------------|--------|
| **InfiniBand NDR switch** | 4.2 W/port | 100-200 ns | 400-800 Gb/s | NVIDIA |
| **P4 Switch (Tofino)** | 4.2 W/port | 100-500 ns | 6.5-12.8 Tb/s | Intel |
| **Optical Switch** | Lower (passive) | 40 ns-1 µs | 25-100 Gb/s/port | Research |
| **BlueField-3 DPU** | 75-150W | 1-5 µs | 400 Gb/s | NVIDIA |
| **Intel IPU E2100** | 20-30W | ~2 µs RTT | 200 Gb/s | Intel |
| **AMD Pensando Salina** | ~50W | — | 400 Gb/s | AMD |

### Server/CPU Power Benchmarks

| Platform | TDP | Cores | Memory | Use Case |
|----------|-----|-------|--------|----------|
| **Intel Xeon 8480+** | 350W | 56 cores | 8-channel DDR5 | General purpose |
| **AMD EPYC 9654** | 360W | 96 cores | 12-channel DDR5 | High core count |
| **NVIDIA H100 SXM** | 700W | — | 80GB HBM3 | AI training |
| **NVIDIA L40S** | 300W | — | 48GB GDDR6 | AI inference |

---

## Industry Averages

### Energy per Operation by Platform

| Platform | ops/s | Power (W) | J/op | ops/J | Source |
|----------|-------|-----------|------|-------|--------|
| **FPGA (Lattice Nexus)** | 100M LUT ops/s | 2W | 20 pJ/op | 50 G ops/J | Lattice |
| **FPGA (PolarFire)** | 50M LUT ops/s | 3.5W | 70 pJ/op | 14 G ops/J | Microchip |
| **FPGA (Versal AI Edge)** | 1T ops/s | 40W | 40 pJ/op | 25 G ops/J | AMD |
| **FPGA (Agilex 7)** | 2T ops/s | 60W | 30 pJ/op | 33 G ops/J | Intel |
| **CPU (Xeon 8480+)** | 500G inst/s | 350W | 700 pJ/inst | 1.4 G inst/J | Intel |
| **GPU (H100)** | 1P FP16 FLOP/s | 700W | 700 pJ/FLOP | 1.4 P FLOP/J | NVIDIA |
| **GPU (L40S)** | 360T FP16 FLOP/s | 300W | 833 pJ/FLOP | 1.2 P FLOP/J | NVIDIA |

### Watts per Message by Platform

| Platform | msg/s | Power (W) | W/msg | msg/J | Source |
|----------|-------|-----------|-------|-------|--------|
| **P4 Switch** | 4.8B pkt/s | 270W (64-port) | 56 pJ/pkt | 17.8 G pkt/J | Intel |
| **InfiniBand NDR** | 330M msg/s | 150W (switch) | 455 pJ/msg | 2.2 G msg/J | NVIDIA |
| **DPDK (100G NIC)** | 100M pkt/s | 25W (NIC) | 250 pJ/pkt | 4 G pkt/J | DPDK |
| **RoCE v2 (ConnectX-7)** | 370M msg/s | 30W (NIC) | 81 pJ/msg | 12.3 G msg/J | NVIDIA |
| **FPGA order processing** | 150K orders/s | 50W | 333 µJ/order | 3K orders/J | IEEE 2024 |
| **BlueField-3 DPU** | 80M pkt/s | 100W | 1.25 nJ/pkt | 800 M pkt/J | NVIDIA |

### Energy Efficiency Leaders

| Rank | Platform | Efficiency | Workload |
|------|----------|------------|----------|
| 1 | Lattice Nexus FPGA | 50 G ops/joule | Edge AI, sensor fusion |
| 2 | Intel Agilex 7 FPGA | 33 G ops/joule | Networking, HPC |
| 3 | AMD Versal AI Edge | 25 G ops/joule | AI inference |
| 4 | Microchip PolarFire | 14 G ops/joule | Power-constrained |
| 5 | NVIDIA H100 GPU | 1.4 P FLOP/joule | AI training |
| 6 | Intel Xeon CPU | 1.4 G inst/joule | General purpose |

---

## Carbon Footprint

### Carbon Intensity by Region

| Region | gCO₂e/kWh | Source |
|--------|-----------|--------|
| **Norway** | 20 | IEA 2024 |
| **France** | 50 | IEA 2024 |
| **Quebec (Canada)** | 30 | IEA 2024 |
| **California (US)** | 200 | EPA 2024 |
| **New York (US)** | 250 | EPA 2024 |
| **Texas (US)** | 400 | EPA 2024 |
| **Singapore** | 450 | EMA 2024 |
| **Hong Kong** | 500 | CLP 2024 |
| **Japan** | 450 | IEA 2024 |
| **Germany** | 350 | IEA 2024 |
| **India** | 600 | IEA 2024 |
| **China** | 550 | IEA 2024 |
| **Global Average** | 450 | IEA 2024 |

### PUE by Facility Type

| Facility Type | PUE Range | Typical |
|---------------|-----------|---------|
| **Hyperscale data center** | 1.1-1.3 | 1.15 |
| **Colocation (Equinix)** | 1.3-1.6 | 1.45 |
| **Enterprise data center** | 1.5-2.0 | 1.7 |
| **Edge / on-prem** | 1.0-1.2 | 1.1 |
| **HFT colocation** | 1.2-1.5 | 1.3 |

### Carbon Footprint Examples

#### Example 1: FPGA Tick-to-Trade (HFT)

```
Device: AMD Versal AI Edge (40W)
PUE: 1.3 (HFT colocation)
Carbon Intensity: 450 gCO₂e/kWh (Singapore)
Throughput: 150,000 orders/s

Total Power = 40W × 1.3 = 52W
Energy per order = 52W / 150,000 orders/s = 347 µJ/order
Carbon per order = 347 µJ × 450 gCO₂e/kWh / 3.6e9 = 43.4 ngCO₂e/order
```

#### Example 2: DPDK Packet Processing

```
NIC: 100GbE (25W)
PUE: 1.15 (hyperscale)
Carbon Intensity: 200 gCO₂e/kWh (California)
Throughput: 100M packets/s

Total Power = 25W × 1.15 = 28.75W
Energy per packet = 28.75W / 100M pkt/s = 287.5 pJ/pkt
Carbon per packet = 287.5 pJ × 200 gCO₂e/kWh / 3.6e9 = 15.97 ngCO₂e/pkt
```

#### Example 3: AI Inference (GPU)

```
GPU: NVIDIA L40S (300W)
PUE: 1.15 (hyperscale)
Carbon Intensity: 450 gCO₂e/kWh (global average)
Throughput: 360T FP16 FLOP/s

Total Power = 300W × 1.15 = 345W
Energy per FLOP = 345W / 360T FLOP/s = 958 pJ/FLOP
Carbon per FLOP = 958 pJ × 450 gCO₂e/kWh / 3.6e9 = 119.8 ngCO₂e/FLOP
```

---

## Usage

### Quick Start

```python
from power_eval import PowerEvaluator

# Initialize evaluator
eval = PowerEvaluator()

# Calculate watts per operation
result = eval.watts_per_operation(
    power_watts=40,
    operations_per_second=150_000,
    pue=1.3,
    carbon_intensity=450
)
print(f"J/op: {result['watts_per_operation']:.2e} J/op")
print(f"Carbon/op: {result['carbon_per_operation']:.2e} gCO₂e/op")

# Calculate watts per message
result = eval.watts_per_message(
    power_watts=25,
    messages_per_second=100_000_000,
    pue=1.15,
    carbon_intensity=200
)
print(f"W/msg: {result['watts_per_message']:.2e} W/msg")
```

### Batch Evaluation

```python
from power_eval import PowerEvaluator

eval = PowerEvaluator()

platforms = [
    {"name": "FPGA Versal", "power": 40, "ops_s": 150_000},
    {"name": "FPGA Agilex", "power": 60, "ops_s": 2_000_000_000},
    {"name": "CPU Xeon", "power": 350, "ops_s": 500_000_000_000},
    {"name": "GPU H100", "power": 700, "ops_s": 1_000_000_000_000_000},
]

results = eval.compare_platforms(platforms, pue=1.3, carbon_intensity=450)
eval.print_comparison(results)
```

---

## Data Sources

- AMD Versal AI Edge Product Briefs (Gen 1 & Gen 2)
- Intel Agilex 7 Product Specifications & Power Management User Guide
- Lattice Nexus Platform White Paper & CertusPro-NX Datasheet
- Microchip PolarFire Product Overview & Brochure
- Achronix Speedster7t Product Brief & Datasheet
- Flex Logix EFLX4K Gen 2 Product Brief & eFPGA Overview
- NVIDIA ConnectX-7 NDR 400G InfiniBand Adapter Datasheet
- NVIDIA BlueField-3 DPU Product Brief
- Intel IPU Adapter E2100 Product Brief
- AMD Pensando DPU Technology Brief
- DPDK Vhost/Virtio Performance Report 18.02
- SPDK NVMe-oF TCP Performance Report 22.01
- IEEE 2024 FPGA for HFT Study
- IEA 2024 Carbon Intensity Data
- EPA 2024 US Grid Carbon Intensity

---

*Framework version 1.0 — 2026-09-29*
