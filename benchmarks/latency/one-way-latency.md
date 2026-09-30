# One-Way Latency Benchmark

> **Metric:** Single-direction message delivery time  
> **Target:** < 1 µs (RDMA), < 5 µs (DPDK)

---

## 1. Measurement Methodology

### Definition

One-way latency measures the time for a message to travel from Node A to Node B in a single direction. This is the most challenging metric to measure accurately due to clock synchronization requirements.

### Procedure

1. **Clock synchronization:** Both nodes must have synchronized clocks (PTP/IEEE 1588)
2. **Measurement:**
   - Node A sends message at `t1` (timestamped by Node A's clock)
   - Node B receives message at `t2` (timestamped by Node B's clock)
3. **Calculation:** `One-Way Latency = t2 - t1`
4. **Clock offset correction:** Account for clock offset between nodes

### Formula

```
One-Way Latency = t_receive - t_send - clock_offset
```

Where `clock_offset` is the difference between Node A and Node B clocks, measured via PTP.

### Key Considerations

- **Clock synchronization:** Requires sub-microsecond accuracy
- **Hardware timestamping:** Essential for accurate measurement
- **PTP grandmaster:** Required for clock distribution
- **Timestamp points:** Must be consistent (NIC vs. application)

### Measurement Points

| Point | Location | Accuracy | Use Case |
|-------|----------|----------|----------|
| NIC TX | Hardware | ~10 ns | Most accurate |
| Application TX | Software | ~1 µs | Application-level |
| NIC RX | Hardware | ~10 ns | Most accurate |
| Application RX | Software | ~1 µs | Application-level |

---

## 2. Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| NIC | ConnectX-6 (200 Gb/s) | ConnectX-7 (400 Gb/s NDR) | Hardware timestamping |
| CPU | 8 cores, 2.5 GHz | 16+ cores, 3.0 GHz+ | Isolated cores |
| Memory | 32 GB DDR4 | 64 GB DDR5 | Low-latency DIMMs |
| Switch | NDR InfiniBand | NDR IB with PTP | PTP support |
| PTP GM | Hardware GM | GPS-disciplined OCXO | < 100 ns accuracy |
| Cabling | DAC (≤2.5 m) | DAC (≤2.5 m) | Minimize distance |

### PTP Grandmaster Requirements

| Feature | Requirement |
|---------|-------------|
| Accuracy | < 100 ns |
| Stability | < 10 ns over 24 hours |
| Interface | 10 Gb/s+ with hardware timestamping |
| Antenna | GPS/GNSS for absolute time |

---

## 3. Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| OS | Linux 6.1+ (PREEMPT_RT) | Real-time kernel |
| MLNX_OFED | 23.10+ | RDMA drivers with PTP |
| PTP4L | Latest | PTP protocol stack |
| phc2sys | Latest | PHC to system clock sync |
| DPDK | 23.11+ | Kernel bypass with timestamping |
| libibverbs | Latest | RDMA verbs API |

### PTP Configuration

```bash
# /etc/linuxptp/ptp4l.conf
[global]
priority1 128
clockClass 6
clockAccuracy 0x21
offsetScaledLogVariance 0xFFFF
free_running 0
freq_est_interval 1
dscp_event 46
dscp_general 46

# Hardware timestamping
ptp4l -i eth0 -m -H -f /etc/linuxptp/ptp4l.conf

# Sync system clock
phc2sys -s eth0 -m -w -O 0
```

### Verify Clock Sync

```bash
# Check PTP status
pmc -u -b 0 'GET CURRENT_DATA_SET'
pmc -u -b 0 'GET TIME_STATUS_NP'

# Check offset (should be < 100 ns)
cat /sys/class/ptp/ptp0/clock_name
ethtool -T eth0
```

---

## 4. Running the Benchmark

### Using DPDK with Hardware Timestamping

```c
// Enable hardware timestamping in DPDK
struct rte_eth_conf port_conf = {
    .rxmode = {
        .offloads = DEV_RX_OFFLOAD_TIMESTAMP,
    },
    .txmode = {
        .offloads = DEV_TX_OFFLOAD_SEND_ON_TIMESTAMP,
    },
};

// Send with timestamp
rte_eth_tx_burst(port_id, queue_id, &tx_pkts, 1);

// Receive with timestamp
rte_eth_rx_burst(port_id, queue_id, &rx_pkts, 1);
uint64_t timestamp = rx_pkts[0].timestamp;
```

### Using RDMA with Hardware Timestamping

```c
// Enable completion timestamp
struct ibv_cq_init_attr_ex cq_attr = {
    .cqe = 1024,
    .channel = NULL,
    .comp_vector = 0,
    .wc_flags = IBV_WC_WITH_TIMESTAMP,
    .comp_mask = IBV_CQ_INIT_ATTR_MASK_FLAGS,
    .flags = IBV_CREATE_CQ_ATTR_SINGLE_THREADED,
};

struct ibv_cq *cq = ibv_create_cq_ex(context, &cq_attr);

// Poll CQ with timestamp
struct ibv_wc wc;
ibv_poll_cq(cq, 1, &wc);
uint64_t timestamp = wc.timestamp;
```

### Using PTP-Enabled Tools

```bash
# Using ptp4l for one-way latency measurement
# On Node A (sender)
ptp4l -i eth0 -m -H --tx_timestamp_timeout 100

# On Node B (receiver)
ptp4l -i eth0 -m -H --tx_timestamp_timeout 100

# Measure one-way delay
pmc -u -b 0 'GET CURRENT_DATA_SET'
```

---

## 5. Expected Results

| Technology | Typical One-Way | Min One-Way | Clock Accuracy |
|------------|-----------------|-------------|----------------|
| InfiniBand NDR | 0.5–0.8 µs | 0.4 µs | < 100 ns |
| RoCE v2 | 0.8–1.5 µs | 0.6 µs | < 100 ns |
| DPDK | 1–2 µs | 0.8 µs | < 100 ns |
| Kernel TCP/IP | 5–20 µs | 3 µs | < 1 µs |

---

## 6. Clock Synchronization Details

### PTP Message Flow

```
┌─────────────┐                    ┌─────────────┐
│   Node A    │                    │   Node B    │
│  (Master)   │                    │   (Slave)   │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       │──────── Sync (t1) ──────────────►│
       │                                  │
       │◄──── Delay_Req (t2) ─────────────│
       │                                  │
       │──────── Delay_Resp (t3) ────────►│
       │                                  │
       │◄──── Delay_Resp_Follow_Up (t4) ──│
       │                                  │
       │  offset = ((t2-t1) - (t4-t3))/2  │
       │  delay  = ((t2-t1) + (t4-t3))/2  │
```

### Clock Offset Calculation

```
offset = ((t2 - t1) - (t4 - t3)) / 2
delay  = ((t2 - t1) + (t4 - t3)) / 2
```

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Negative latency | Clock offset | Improve PTP sync |
| High variance | Clock drift | Use hardware timestamping |
| Inconsistent results | Software timestamping | Enable hardware timestamping |
| Clock offset > 1 µs | PTP not working | Check PTP configuration |
| No timestamp support | Driver issue | Update MLNX_OFED |
