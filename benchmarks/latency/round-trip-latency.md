# Round-Trip Latency Benchmark

> **Metric:** Full round-trip time of a message (A→B→A)  
> **Target:** < 2 µs (RDMA), < 10 µs (DPDK)

---

## 1. Measurement Methodology

### Definition

Round-trip latency (RTT) measures the total time for a message to travel from Node A to Node B, be processed, and return to Node A. Unlike ping-pong, RTT may include processing time at the destination.

### Procedure

1. **Setup:** Two nodes with synchronized clocks (PTP) or single-node timing
2. **Message flow:**
   - Node A sends message at `t1`
   - Node B receives at `t2`, processes, sends response at `t3`
   - Node A receives response at `t4`
3. **Calculation:** `RTT = t4 - t1`
4. **Variants:**
   - **Pure RTT:** No processing at Node B (immediate response)
   - **Processing RTT:** Include fixed processing delay at Node B
   - **Application RTT:** Include application-level processing

### Formula

```
RTT = t_response_received - t_request_sent
    = (t4 - t1)
```

### Key Differences from Ping-Pong

| Aspect | Ping-Pong | Round-Trip |
|--------|-----------|------------|
| Processing | None at responder | May include processing |
| Protocol | Lock-step | Can be pipelined |
| Measurement | Single node | Can use both nodes |
| Use case | Network path | End-to-end application |

---

## 2. Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| NIC | ConnectX-6 (200 Gb/s) | ConnectX-7 (400 Gb/s NDR) | RDMA support mandatory |
| CPU | 8 cores, 2.5 GHz | 16+ cores, 3.0 GHz+ | Isolated cores |
| Memory | 32 GB DDR4 | 64 GB DDR5 | Low-latency DIMMs |
| Switch | NDR InfiniBand | NDR IB with PTP | Cut-through switching |
| Clock sync | PTP (IEEE 1588) | PTP + hardware timestamp | For distributed timing |

### Clock Synchronization

For accurate RTT measurement across nodes:

```bash
# Install PTP
apt install linuxptp

# Configure PTP grandmaster
ptp4l -i eth0 -m -H  # Hardware timestamping

# Sync system clock to PHC
phc2sys -s eth0 -m -w
```

---

## 3. Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| OS | Linux 6.1+ (PREEMPT_RT) | Real-time kernel |
| MLNX_OFED | 23.10+ | RDMA drivers |
| libibverbs | Latest | RDMA verbs API |
| DPDK | 23.11+ | Kernel bypass |
| PTP4L | Latest | Clock synchronization |
| phc2sys | Latest | PHC to system clock sync |

### Configuration

```bash
# Enable hardware timestamping
ethtool -T eth0  # Verify support
ethtool --set-time eth0 rx on tx on

# CPU isolation
GRUB_CMDLINE_LINUX="isolcpus=2-15 nohz_full=2-15 rcu_nocbs=2-15"

# Disable NTP (use PTP only)
systemctl stop systemd-timesyncd
systemctl disable systemd-timesyncd
```

---

## 4. Running the Benchmark

### Using perftest (RDMA)

```bash
# On Node B (server)
ib_send_lat -a -d mlx5_0 --report_gbits

# On Node A (client)
ib_send_lat -a -d mlx5_0 --report_gbits <Node_B_IP>
```

### Using DPDK

```bash
# On Node B (server)
./l2fwd -l 2-7 -n 4 -- -p 0x1

# On Node A (client) with latency measurement
./l2fwd-latency -l 2-7 -n 4 -- -p 0x1 --latency
```

### Custom Implementation

```c
// Pseudocode for RTT benchmark
for (i = 0; i < iterations; i++) {
    t1 = get_time();  // Hardware timestamp
    send_message(msg);
    response = wait_for_response();
    t4 = get_time();
    rtt[i] = t4 - t1;
}
```

---

## 5. Expected Results

| Technology | Typical RTT | Min RTT | Max RTT |
|------------|-------------|---------|---------|
| InfiniBand NDR | 1.0–1.5 µs | 0.8 µs | 2.0 µs |
| RoCE v2 | 1.5–3.0 µs | 1.2 µs | 5.0 µs |
| DPDK | 2–5 µs | 1.5 µs | 10 µs |
| Kernel TCP/IP | 10–50 µs | 5 µs | 100 µs |

---

## 6. Analysis

### Latency Breakdown

```
Total RTT = NIC TX + Switch + NIC RX + Processing + NIC TX + Switch + NIC RX
          = 2 × (NIC latency) + 2 × (Switch latency) + Processing
```

### Optimization Targets

| Component | Typical Latency | Optimization |
|-----------|-----------------|--------------|
| NIC TX | 200–400 ns | Use RDMA, avoid copies |
| Switch | 100–200 ns | Cut-through, NDR |
| NIC RX | 200–400 ns | Polling mode, no interrupts |
| Processing | 0–1000 ns | Optimize application code |
| Kernel | 1000–5000 ns | Use kernel bypass |

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| RTT > 5 µs | Kernel involvement | Use RDMA or DPDK |
| High variance | Clock drift | Enable PTP hardware timestamping |
| Out-of-order results | Multiple queues | Use single queue pair |
| Buffer overflow | High message rate | Increase CQ size |
