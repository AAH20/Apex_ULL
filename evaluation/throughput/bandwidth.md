# Bandwidth (Gb/s)

**Definition:** The maximum data transfer rate of a network or interconnect, measured in gigabits per second (Gb/s). Bandwidth determines how much data can flow through a system per unit time.

---

## 1. Measurement Methodology

### 1.1 Bandwidth vs. Throughput vs. Goodput

| Term | Definition | Formula |
|------|-----------|---------|
| **Bandwidth** | Theoretical maximum data rate | Link rate (e.g., 400 Gb/s) |
| **Throughput** | Actual data rate achieved | Measured data / time |
| **Goodput** | Useful data rate (excluding headers) | Throughput × (payload / total) |
| **Line rate** | Maximum rate at the physical layer | NIC/switch specification |

```
Goodput = Bandwidth × (1 - protocol_overhead) × (1 - error_rate)

Example: 400 Gb/s Ethernet with 3% overhead
  Goodput = 400 × 0.97 = 388 Gb/s
```

### 1.2 Measurement Approaches

| Method | Description | Accuracy | Use Case |
|--------|-------------|----------|----------|
| **`iperf3`** | Standard network benchmark | Very high | TCP/UDP throughput |
| **`ib_write_bw`** | InfiniBand RDMA write bandwidth | Very high | RDMA/InfiniBand |
| **`ib_send_bw`** | InfiniBand RDMA send bandwidth | Very high | RDMA/InfiniBand |
| **`nuttcp`** | Network performance test | High | TCP/UDP throughput |
| **`netperf`** | Network benchmark suite | High | Various protocols |
| **`dpdk-procinfo`** | DPDK port statistics | Very high | Kernel-bypass |
| **`ethtool -S`** | NIC statistics | Very high | Hardware counters |
| **`switch counters`** | Switch port statistics | Very high | Switch bandwidth |

### 1.3 Standard Test Configuration

```bash
# TCP bandwidth test
iperf3 -c <server_ip> -t 60 -P 4 -w 1M

# UDP bandwidth test
iperf3 -c <server_ip> -t 60 -u -b 400G

# InfiniBand RDMA write bandwidth
ib_write_bw -d <device> --report_gbits -D 60

# InfiniBand RDMA send bandwidth
ib_send_bw -d <device> --report_gbits -D 60
```

### 1.4 Key Formulas

```
Bandwidth (Gb/s) = Total bits transferred / Measurement window (s) / 1,000,000,000

Effective bandwidth = Bandwidth × (payload_bytes / total_bytes)

Bidirectional bandwidth = 2 × Unidirectional bandwidth (full-duplex)

Aggregate bandwidth = Σ(all active links)

Bandwidth per port = Total switch capacity / Number of ports
```

---

## 2. Benchmark Standards

### 2.1 Ethernet Standards

| Standard | Year | Per-lane Rate | 4x Rate | 8x Rate | Use Case |
|---------|------|--------------|---------|---------|----------|
| 10GbE | 2002 | 10 Gb/s | — | — | Legacy data center |
| 40GbE | 2010 | 10 Gb/s | 40 Gb/s | — | Spine/leaf |
| 100GbE | 2013 | 25 Gb/s | 100 Gb/s | — | Data center, HFT |
| 200GbE | 2017 | 50 Gb/s | 200 Gb/s | — | High-performance DC |
| 400GbE | 2017 | 100 Gb/s | 400 Gb/s | — | AI clusters, HFT |
| 800GbE | 2022 | 200 Gb/s | 800 Gb/s | — | Next-gen AI clusters |
| 1.6TbE | 2025+ | 400 Gb/s | 1.6 Tb/s | — | Future DC |

### 2.2 InfiniBand Standards

| Generation | Year | Per-lane Rate | 4x Rate | 8x Rate | Modulation |
|-----------|------|--------------|---------|---------|------------|
| EDR | 2014 | 25.78 Gb/s | 100 Gb/s | — | NRZ |
| HDR | 2018 | 53.125 Gb/s | 200 Gb/s | — | PAM4 |
| NDR | 2021 | 106.25 Gb/s | 400 Gb/s | — | PAM4 |
| XDR | 2024 | 200 Gb/s | 800 Gb/s | — | PAM4 + FEC |
| GDR | 2027+ | ~400 Gb/s | 1.6 Tb/s | — | PAM4 + FEC |

### 2.3 InfiniBand Switch Capacity

| Switch | Capacity | Ports | Latency | Source |
|--------|----------|-------|---------|--------|
| QM8700 (HDR) | 40 Tb/s | 40×200G | 100–200 ns | NVIDIA specs |
| QM9700 (NDR) | 51.2 Tb/s | 64×400G | 100–200 ns | NVIDIA specs |
| QM9790 (NDR) | 51.2 Tb/s | 64×400G | 100–200 ns | NVIDIA specs |
| Modular NDR | 1.64 Pb/s | — | — | NVIDIA specs |

### 2.4 DPU / SmartNIC Bandwidth

| Device | Network Bandwidth | Packet Rate | Source |
|--------|------------------|-------------|--------|
| NVIDIA BlueField-3 | 400 Gb/s | 80 Mpps | NVIDIA specs |
| NVIDIA BlueField-4 | 800 Gb/s | 117 Mpps | NVIDIA specs |
| Intel IPU E2100 | 200 Gb/s | 200 Mpps | Intel specs |
| AMD Pensando Salina | 400 Gb/s | 117 Mpps | AMD specs |
| AMD Pollara 400 | 400 Gb/s | — | AMD specs |

### 2.5 FPGA Network Bandwidth

| Device | SerDes Rate | Ethernet | Source |
|--------|------------|----------|--------|
| AMD Versal AI Edge | 32G | — | AMD specs |
| Intel Agilex 7 I-Series | 116G PAM4 | 400G | Intel specs |
| Achronix Speedster7t | 112G | 2×400G | Achronix specs |
| Lattice Nexus 2 | 16G | — | Lattice specs |

---

## 3. Industry Averages

### 3.1 By Network Type

| Network Type | Bandwidth | Latency | Jitter | Use Case |
|-------------|-----------|---------|--------|----------|
| Standard Ethernet (10GbE) | 10 Gb/s | 10–100 μs | High | General purpose |
| Data Center Ethernet (100GbE) | 100 Gb/s | 5–50 μs | Medium | DC spine |
| HFT Ethernet (100GbE) | 100 Gb/s | 1–10 μs | Low | Trading |
| RoCE v2 | 100–400 Gb/s | 1–3 μs | Low–moderate | DC, storage |
| InfiniBand NDR | 400–800 Gb/s | 100–200 ns | Very low | HPC, AI |
| Microwave (Chicago-NY) | 1–10 Gb/s | 4.7 ms | Low | HFT WAN |
| Fiber (Chicago-NY) | 10–100 Gb/s | 7.2 ms | Low | HFT WAN |

### 3.2 By Application

| Application | Bandwidth Required | Latency Target | Notes |
|-------------|-------------------|----------------|-------|
| HFT market data (per feed) | 1–10 Gb/s | <10 μs | Multicast UDP |
| HFT order entry | 1–10 Gb/s | <10 μs | TCP or UDP |
| Payment authorization | 1–10 Gb/s | <100 ms | TCP |
| Payment clearing | 10–100 Gb/s | Minutes | Batch |
| Gaming state sync | 1–10 Gb/s | <50 ms | UDP |
| Video streaming | 10–100 Gb/s | <1 s | TCP/UDP |
| AI training (per node) | 400–800 Gb/s | <1 μs | RDMA |
| Storage (NVMe-oF) | 100–400 Gb/s | <100 μs | RDMA/TCP |

### 3.3 By Domain

| Domain | Typical Bandwidth | Peak Bandwidth | Notes |
|--------|------------------|----------------|-------|
| HFT (per firm) | 10–100 Gb/s | 400 Gb/s | Multiple venues |
| Payment network | 10–100 Gb/s | 400 Gb/s | Global backbone |
| Gaming (per shard) | 1–10 Gb/s | 100 Gb/s | State sync |
| Data center (spine) | 400 Gb/s | 800 Gb/s | AI clusters |
| Cloud (per VM) | 10–100 Gb/s | 400 Gb/s | Virtualized |
| IoT (per gateway) | 1–10 Gb/s | 100 Gb/s | Aggregated |

---

## 4. Bandwidth in ULL Systems

### 4.1 HFT Network Architecture

```
Exchange ←→ FPGA Feed Handler ←→ Strategy Server ←→ Order Gateway ←→ Exchange
  100GbE        100GbE                100GbE           100GbE         100GbE
  (market data) (decode)              (decision)       (encode)       (order entry)

Total bandwidth: 400 Gb/s (4×100GbE)
Latency budget: <10 μs end-to-end
```

### 4.2 Payment Network Architecture

```
Merchant ←→ Acquirer ←→ Network ←→ Issuer ←→ Authorization
  1GbE      10GbE       100GbE     100GbE    10GbE
  (POS)     (gateway)   (backbone) (gateway) (auth)

Total bandwidth: 221 Gb/s (aggregate)
Latency budget: <1 second end-to-end
```

### 4.3 Data Center Fabric

```
Server ←→ Leaf Switch ←→ Spine Switch ←→ Core Switch ←→ WAN
  400GbE    400GbE         800GbE         800GbE        100GbE
  (NIC)     (ToR)          (Spine)        (Core)        (WAN)

Total bandwidth: 2.1 Tb/s (aggregate)
Latency budget: <1 μs (intra-DC), <100 μs (inter-DC)
```

---

## 5. Factors Affecting Bandwidth

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Protocol overhead | TCP/IP: ~3%, UDP/IP: ~1%, RDMA: <0.5% | Use RDMA for ULL |
| Packet size | Smaller packets → more overhead | Use jumbo frames (9000 MTU) |
| Encryption | TLS: 10–30% overhead | Hardware TLS offload |
| Compression | Can increase goodput | Use hardware compression |
| Network congestion | Drops effective bandwidth | QoS, traffic shaping |
| Cable quality | Signal degradation → retransmits | Use high-quality DAC/AOC |
| Switch capacity | Shared bandwidth across ports | Use non-blocking switches |
| NIC capabilities | Hardware offload vs software | Use SmartNICs, DPUs |

---

## 6. Bandwidth Measurement Tools

| Tool | Domain | Output |
|------|--------|--------|
| `iperf3` | TCP/UDP | Bandwidth, jitter, loss |
| `ib_write_bw` | RDMA write | Bandwidth, message rate |
| `ib_send_bw` | RDMA send | Bandwidth, message rate |
| `nuttcp` | TCP/UDP | Bandwidth, latency |
| `netperf` | Various | Bandwidth, latency |
| `dpdk-procinfo` | DPDK | Per-port statistics |
| `ethtool -S` | NIC | Hardware counters |
| `switch counters` | Switch | Per-port bandwidth |

---

## 7. Reporting Template

```yaml
metric: bandwidth
system: <system_name>
date: <ISO 8601>
configuration:
  link_speed_gbps: <N>
  protocol: <tcp|udp|rdma|roce|infiniband>
  packet_size_bytes: <N>
  num_streams: <N>
  duration_seconds: <N>
  network_type: <ethernet|infiniband|roce|fpga>
results:
  unidirectional_gbps: <N>
  bidirectional_gbps: <N>
  goodput_gbps: <N>
  packet_rate_mpps: <N>
  p50_latency_us: <N>
  p99_latency_us: <N>
  packet_loss_pct: <N>
  cpu_utilization_pct: <N>
notes: <any anomalies or observations>
```

---

*Sources: IEEE 802.3 Ethernet standards, NVIDIA InfiniBand product specifications, AMD/Intel DPU product briefs, Achronix/AMD/Intel FPGA product briefs, iperf3/ib_write_bw documentation.*
