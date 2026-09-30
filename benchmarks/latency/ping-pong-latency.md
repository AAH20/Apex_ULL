# Ping-Pong Latency Benchmark

> **Metric:** Request-response round-trip between two nodes  
> **Target:** < 2 µs (RDMA), < 10 µs (DPDK)

---

## 1. Measurement Methodology

### Definition

Ping-pong latency measures the time for a message to travel from Node A to Node B and back to Node A. It is the most fundamental ULL metric.

### Procedure

1. **Setup:** Two nodes connected via RDMA-capable NICs (InfiniBand or RoCE v2)
2. **Warm-up:** Exchange 1,000 messages to warm caches and paths
3. **Measurement:** Exchange N messages (default: 100,000) in lock-step
4. **Timing:** Record `t_send` before send and `t_recv` after receive on Node A
5. **Calculation:** `latency = t_recv - t_send` for each iteration
6. **Statistics:** Compute min, max, avg, p50, p99, p99.9, stddev

### Formula

```
Ping-Pong Latency = t_response_received - t_request_sent
```

### Key Considerations

- **Lock-step protocol:** Node A sends, waits for response, then sends next
- **No pipelining:** Each request must complete before next is sent
- **CPU affinity:** Pin to isolated cores to avoid scheduler interference
- **NUMA locality:** NIC and CPU must be on same NUMA node
- **Cache effects:** Warm-up phase is critical for stable results

---

## 2. Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| NIC | ConnectX-6 (200 Gb/s) | ConnectX-7 (400 Gb/s NDR) | RDMA support mandatory |
| CPU | 8 cores, 2.5 GHz | 16+ cores, 3.0 GHz+ | Isolated cores (nohz_full) |
| Memory | 32 GB DDR4 | 64 GB DDR5 | Low-latency DIMMs |
| Switch | NDR InfiniBand | NDR IB with PTP | Cut-through switching |
| Cabling | DAC (≤2.5 m) | DAC (≤2.5 m) | Minimize physical distance |
| PCIe | Gen4 x16 | Gen5 x16 | Sufficient bandwidth |

### CPU Isolation

```bash
# Isolate cores 2-15 for benchmarking
GRUB_CMDLINE_LINUX="isolcpus=2-15 nohz_full=2-15 rcu_nocbs=2-15"
```

---

## 3. Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| OS | Linux 6.1+ (PREEMPT_RT) | Real-time kernel |
| MLNX_OFED | 23.10+ | RDMA drivers |
| libibverbs | Latest | RDMA verbs API |
| perftest | Latest | RDMA benchmark tool |
| DPDK | 23.11+ | Alternative: kernel bypass |
| numactl | Latest | NUMA affinity |
| taskset | Latest | CPU affinity |

### Configuration

```bash
# Disable CPU frequency scaling
cpupower frequency-set -g performance

# Disable IRQ balancing on isolated cores
echo 0 > /proc/irq/<IRQ_NUM>/smp_affinity

# Set NIC interrupt affinity
echo <CPU_MASK> > /proc/irq/<NIC_IRQ>/smp_affinity

# Huge pages for DPDK
echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
```

---

## 4. Running the Benchmark

### Using perftest (RDMA)

```bash
# On Node B (server)
ib_write_lat -a -d mlx5_0 --report_gbits

# On Node A (client)
ib_write_lat -a -d mlx5_0 --report_gbits <Node_B_IP>
```

### Using DPDK l2fwd-latency

```bash
# On Node B (server)
./l2fwd-latency -l 2-7 -n 4 -- -p 0x1 --latency

# On Node A (client)
./l2fwd-latency -l 2-7 -n 4 -- -p 0x1 --latency <Node_B_MAC>
```

### Custom Implementation

```c
// Pseudocode for custom ping-pong benchmark
for (i = 0; i < iterations; i++) {
    t_start = rdtsc();
    ibv_post_send(qp, &wr, &bad_wr);  // Send request
    ibv_poll_cq(cq, 1, &wc);           // Wait for response
    t_end = rdtsc();
    latency[i] = t_end - t_start;
}
```

---

## 5. Expected Results

| Technology | Typical Latency | Min Latency |
|------------|-----------------|-------------|
| InfiniBand NDR | 1.0–1.5 µs | 0.8 µs |
| RoCE v2 | 1.5–3.0 µs | 1.2 µs |
| DPDK (kernel bypass) | 2–5 µs | 1.5 µs |
| Kernel TCP/IP | 10–50 µs | 5 µs |

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| High latency (>10 µs) | CPU frequency scaling | Set governor to performance |
| High jitter | IRQ on same core | Move IRQs to non-isolated cores |
| Inconsistent results | NUMA mismatch | Pin to same NUMA node as NIC |
| Packet loss | Buffer overflow | Increase CQ/QP sizes |
