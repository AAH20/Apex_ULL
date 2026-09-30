# Throughput Benchmark

> **Metric:** Data transfer rate under latency constraints  
> **Target:** 100+ Gb/s (RDMA), 40+ Gb/s (DPDK)

---

## 1. Measurement Methodology

### Definition

Throughput measures the rate at which data can be transferred between nodes. In ULL contexts, throughput must be measured while maintaining latency constraints.

### Types of Throughput

| Type | Description | Use Case |
|------|-------------|----------|
| **Bulk Throughput** | Maximum data rate, no latency constraint | File transfer |
| **Latency-Constrained Throughput** | Data rate with latency < threshold | ULL applications |
| **Sustained Throughput** | Long-term average data rate | Capacity planning |
| **Burst Throughput** | Short-term peak data rate | Burst handling |

### Procedure

1. **Setup:** Two nodes with RDMA-capable NICs
2. **Warm-up:** Transfer data for 10 seconds to stabilize
3. **Measurement:** Transfer data for specified duration (default: 60 seconds)
4. **Calculation:** `Throughput = bytes_transferred / duration`
5. **Latency constraint:** Measure latency simultaneously, report throughput at latency percentiles

### Formula

```
Throughput (Gb/s) = (bytes_transferred × 8) / (duration × 10⁹)
```

### Key Considerations

- **Message size:** Test with various sizes (64 B to 1 MB)
- **Queue depth:** Vary outstanding requests
- **CPU utilization:** Monitor to ensure not CPU-bound
- **Latency constraint:** Report throughput at p50, p99, p99.9 latency

---

## 2. Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| NIC | ConnectX-6 (200 Gb/s) | ConnectX-7 (400 Gb/s NDR) | RDMA support |
| CPU | 8 cores, 2.5 GHz | 16+ cores, 3.0 GHz+ | Sufficient processing |
| Memory | 32 GB DDR4 | 64 GB DDR5 | Large buffers |
| Switch | NDR InfiniBand | NDR IB | Non-blocking |
| Cabling | DAC (≤2.5 m) | DAC (≤2.5 m) | Minimize distance |
| PCIe | Gen4 x16 | Gen5 x16 | Sufficient bandwidth |

### PCIe Bandwidth Requirements

| NIC Speed | PCIe Gen4 | PCIe Gen5 |
|-----------|-----------|-----------|
| 100 Gb/s | x8 sufficient | x4 sufficient |
| 200 Gb/s | x16 required | x8 sufficient |
| 400 Gb/s | x16 (bottleneck) | x16 required |

---

## 3. Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| OS | Linux 6.1+ (PREEMPT_RT) | Real-time kernel |
| MLNX_OFED | 23.10+ | RDMA drivers |
| DPDK | 23.11+ | Kernel bypass |
| libibverbs | Latest | RDMA verbs API |
| perftest | Latest | RDMA benchmark |
| iperf3 | Latest | TCP/IP benchmark |

### Configuration

```bash
# Increase socket buffers
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728
sysctl -w net.core.rmem_default=134217728
sysctl -w net.core.wmem_default=134217728

# Increase RDMA resources
sysctl -w net.core.netdev_max_backlog=100000

# CPU affinity for RDMA
echo <CPU_MASK> > /proc/irq/<NIC_IRQ>/smp_affinity
```

---

## 4. Running the Benchmark

### Using perftest (RDMA)

```bash
# On Node B (server)
ib_write_bw -a -d mlx5_0 --report_gbits

# On Node A (client)
ib_write_bw -a -d mlx5_0 --report_gbits <Node_B_IP>

# With latency measurement
ib_write_bw -a -d mlx5_0 --report_gbits --latency <Node_B_IP>
```

### Using DPDK

```bash
# On Node B (server)
./l2fwd -l 2-7 -n 4 -- -p 0x1

# On Node A (client)
./l2fwd -l 2-7 -n 4 -- -p 0x1
```

### Using iperf3 (TCP/IP)

```bash
# On Node B (server)
iperf3 -s -p 5201

# On Node A (client)
iperf3 -c <Node_B_IP> -p 5201 -t 60 -P 4
```

### Custom Throughput Test

```c
// Pseudocode for throughput benchmark
uint64_t bytes_transferred = 0;
uint64_t start_time = get_time();

for (i = 0; i < num_messages; i++) {
    send_message(buffer, message_size);
    bytes_transferred += message_size;
}

uint64_t end_time = get_time();
double duration = (end_time - start_time) / 1e9;
double throughput_gbps = (bytes_transferred * 8) / (duration * 1e9);

printf("Throughput: %.2f Gb/s\n", throughput_gbps);
```

---

## 5. Expected Results

| Technology | Message Size | Throughput | Latency |
|------------|--------------|------------|---------|
| InfiniBand NDR | 64 B | 10–20 Gb/s | 1.5 µs |
| InfiniBand NDR | 1 KB | 100–200 Gb/s | 2.0 µs |
| InfiniBand NDR | 1 MB | 350–400 Gb/s | 10 µs |
| RoCE v2 | 64 B | 10–15 Gb/s | 2.5 µs |
| RoCE v2 | 1 KB | 80–150 Gb/s | 3.0 µs |
| DPDK | 64 B | 5–10 Gb/s | 5 µs |
| DPDK | 1 KB | 30–50 Gb/s | 6 µs |

---

## 6. Throughput vs. Latency Trade-off

```
Throughput (Gb/s)
    │
400 ┤                    ┌─────────
    │                 ┌──┘
300 ┤              ┌──┘
    │           ┌──┘
200 ┤        ┌──┘
    │     ┌──┘
100 ┤  ┌──┘
    │┌─┘
  0 ┼─┴─┴─┴─┴─┴─┴─┴─┴─┴──► Latency (µs)
    0  1  2  3  4  5  6  7  8  9  10
```

### Optimization Strategies

| Strategy | Throughput Impact | Latency Impact |
|----------|-------------------|----------------|
| Larger messages | Increase | Increase |
| Higher queue depth | Increase | Increase |
| Multiple streams | Increase | Minimal |
| Kernel bypass | Increase | Decrease |
| RDMA | Increase | Decrease |
| CPU pinning | Minimal | Decrease |

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Low throughput | CPU-bound | Add more cores, optimize code |
| Low throughput | PCIe bottleneck | Upgrade to PCIe Gen5 |
| Low throughput | Small messages | Increase message size |
| High latency | Queue depth too high | Reduce queue depth |
| Inconsistent throughput | Background load | Isolate cores |
| Packet loss | Buffer overflow | Increase buffer sizes |
