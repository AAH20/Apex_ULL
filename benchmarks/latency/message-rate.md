# Message Rate Benchmark

> **Metric:** Messages processed per second  
> **Target:** 100+ Mmsg/s (RDMA), 10+ Mmsg/s (DPDK)

---

## 1. Measurement Methodology

### Definition

Message rate measures the number of messages that can be processed per second. This is critical for ULL applications that rely on small, frequent messages.

### Types of Message Rate

| Type | Description | Use Case |
|------|-------------|----------|
| **Send Rate** | Messages sent per second | Producer throughput |
| **Receive Rate** | Messages received per second | Consumer throughput |
| **Round-Trip Rate** | Complete request-response cycles per second | End-to-end throughput |
| **Sustained Rate** | Long-term average message rate | Capacity planning |

### Procedure

1. **Setup:** Two nodes with RDMA-capable NICs
2. **Warm-up:** Process 10,000 messages to stabilize
3. **Measurement:** Process messages for specified duration (default: 60 seconds)
4. **Calculation:** `Message Rate = messages_processed / duration`
5. **Latency correlation:** Measure latency simultaneously

### Formula

```
Message Rate (Mmsg/s) = messages_processed / (duration × 10⁶)
```

### Key Considerations

- **Message size:** Small messages (64–256 B) are most challenging
- **Queue depth:** Affects pipelining and throughput
- **CPU utilization:** High rates require efficient processing
- **Batch processing:** Can improve rate but increases latency

---

## 2. Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| NIC | ConnectX-6 (200 Gb/s) | ConnectX-7 (400 Gb/s NDR) | High message rate support |
| CPU | 8 cores, 2.5 GHz | 16+ cores, 3.0 GHz+ | High single-thread perf |
| Memory | 32 GB DDR4 | 64 GB DDR5 | Low-latency DIMMs |
| Switch | NDR InfiniBand | NDR IB | Low latency |
| Cabling | DAC (≤2.5 m) | DAC (≤2.5 m) | Minimize distance |

### CPU Requirements

Message rate is often CPU-bound:

| Message Size | CPU Cores Needed | Single-Core Rate |
|--------------|------------------|------------------|
| 64 B | 4–8 | 5–10 Mmsg/s |
| 256 B | 2–4 | 10–20 Mmsg/s |
| 1 KB | 1–2 | 20–40 Mmsg/s |

---

## 3. Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| OS | Linux 6.1+ (PREEMPT_RT) | Real-time kernel |
| MLNX_OFED | 23.10+ | RDMA drivers |
| DPDK | 23.11+ | Kernel bypass |
| libibverbs | Latest | RDMA verbs API |
| perftest | Latest | RDMA benchmark |

### Configuration for High Message Rate

```bash
# CPU isolation
GRUB_CMDLINE_LINUX="isolcpus=2-15 nohz_full=2-15 rcu_nocbs=2-15"

# Disable CPU frequency scaling
cpupower frequency-set -g performance

# Increase RDMA resources
sysctl -w net.core.netdev_max_backlog=100000
sysctl -w net.core.somaxconn=65535

# Huge pages for DPDK
echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Disable IRQ balancing
systemctl stop irqbalance
systemctl disable irqbalance
```

---

## 4. Running the Benchmark

### Using perftest (RDMA)

```bash
# On Node B (server)
ib_write_lat -a -d mlx5_0 --report_gbits

# On Node A (client) - measures message rate
ib_write_lat -a -d mlx5_0 --report_gbits <Node_B_IP>
```

### Using DPDK

```bash
# On Node B (server)
./l2fwd -l 2-7 -n 4 -- -p 0x1

# On Node A (client)
./l2fwd -l 2-7 -n 4 -- -p 0x1
```

### Custom Message Rate Test

```c
// Pseudocode for message rate benchmark
uint64_t message_count = 0;
uint64_t start_time = get_time();

for (i = 0; i < num_messages; i++) {
    send_message(buffer, message_size);
    message_count++;
}

uint64_t end_time = get_time();
double duration = (end_time - start_time) / 1e9;
double message_rate_mmsg_s = message_count / (duration * 1e6);

printf("Message Rate: %.2f Mmsg/s\n", message_rate_mmsg_s);
```

### Using DPDK TestPMD

```bash
# Run testpmd for message rate measurement
./testpmd -l 2-7 -n 4 -- -i --portmask=0x1 \
  --txd=128 --rxd=128 \
  --burst=32 \
  --txq=1 --rxq=1 \
  --stats-period=1
```

---

## 5. Expected Results

| Technology | Message Size | Message Rate | Latency |
|------------|--------------|--------------|---------|
| InfiniBand NDR | 64 B | 100–200 Mmsg/s | 1.5 µs |
| InfiniBand NDR | 256 B | 50–100 Mmsg/s | 1.5 µs |
| InfiniBand NDR | 1 KB | 20–50 Mmsg/s | 2.0 µs |
| RoCE v2 | 64 B | 50–100 Mmsg/s | 2.5 µs |
| RoCE v2 | 256 B | 30–60 Mmsg/s | 2.5 µs |
| DPDK | 64 B | 10–20 Mmsg/s | 5 µs |
| DPDK | 256 B | 5–10 Mmsg/s | 5 µs |

---

## 6. Message Rate vs. Message Size

```
Message Rate (Mmsg/s)
    │
200 ┤┌─┐
    ││ │
150 ┤│ └─┐
    ││   │
100 ┤│   └─┐
    ││     │
 50 ┤│     └─┐
    ││       │
  0 ┼┴─┴─┴─┴─┴──► Message Size (B)
    0 64 256 1K 4K 16K 64K
```

### Optimization Strategies

| Strategy | Rate Impact | Latency Impact |
|----------|-------------|----------------|
| Smaller messages | Decrease | Decrease |
| Batch processing | Increase | Increase |
| Multiple queues | Increase | Minimal |
| Kernel bypass | Increase | Decrease |
| RDMA | Increase | Decrease |
| CPU pinning | Minimal | Decrease |

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Low message rate | CPU-bound | Add more cores, optimize code |
| Low message rate | Small messages | Use batch processing |
| High latency | Queue depth too high | Reduce queue depth |
| Inconsistent rate | Background load | Isolate cores |
| Message loss | Buffer overflow | Increase buffer sizes |
| Rate drops over time | Thermal throttling | Improve cooling |
