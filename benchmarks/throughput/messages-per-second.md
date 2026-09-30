# Messages/sec Throughput Benchmark

## Overview

Measures the rate at which a system can process market data messages (quotes, trades, order book updates). This is the primary throughput metric for feed handlers and market data pipelines.

## Measurement Methodology

### What to Measure

- **Inbound message rate**: Messages received from network interface (packets/sec × messages/packet)
- **Processed message rate**: Messages fully decoded, normalized, and published downstream
- **Sustained rate**: Steady-state throughput after warm-up, measured over ≥60 seconds

### Measurement Protocol

1. **Warm-up**: 30 seconds of full-rate traffic (discard all measurements)
2. **Measurement window**: 60 seconds at target rate
3. **Cooldown**: 10 seconds to drain queues
4. **Repeat**: 5 iterations, report median

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Message size | 64–256 bytes | Typical market data UDP payload |
| Messages/packet | 1–8 | Depends on multicast batching |
| Protocol | UDP multicast | Standard for market data distribution |
| Ring buffer size | 1M–16M entries | Must absorb bursts without loss |
| Measurement granularity | Per-core and system-wide | Identify scaling bottlenecks |

### Common Pitfalls

- **Measuring at the NIC, not the application**: NIC counters show packets received, not messages processed
- **Ignoring queue depth effects**: Throughput may appear higher with shallow queues (messages dropped)
- **Not accounting for batching**: Hardware batching (GRO, LRO) inflates apparent message rate
- **CPU frequency scaling**: Must disable turbo boost and lock frequency for reproducible results
- **NUMA effects**: Memory allocation must be NUMA-local to the processing core

## Hardware Requirements

### Minimum (Entry ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 8 cores @ 3.0 GHz | Intel Xeon W-3400 or AMD EPYC 9004 |
| NIC | 100GbE with hardware timestamping | Mellanox ConnectX-5/6 |
| Memory | 64 GB DDR5 | NUMA-aware allocation |
| Storage | NVMe Gen4 SSD | For capture/replay |
| OS | Linux 6.x with RT-PREEMPT | Kernel bypass required |

### Recommended (Mid ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 32 cores @ 3.5 GHz | AMD EPYC 9654 |
| NIC | 400GbE with FPGA timestamping | Mellanox ConnectX-7 |
| Memory | 256 GB DDR5-5600 | 2 TB/s aggregate bandwidth |
| Storage | NVMe Gen5 SSD | 14 GB/s sequential |
| FPGA | AMD Versal AI Edge | For feed handler offload |

### Extreme ULL

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 64+ cores @ 4.0 GHz | AMD EPYC 9754/9914 |
| NIC | 800GbE or custom FPGA | Sub-100ns timestamping |
| Memory | 1 TB DDR5 + HBM | CXL 2.0 for memory expansion |
| Storage | CXL-attached persistent memory | Sub-µs access latency |
| FPGA | Intel Agilex 7 | Full feed handler in hardware |

## Software Requirements

### OS & Kernel

```bash
# Kernel parameters
echo "isolcpus=2-15 nohz_full=2-15 rcu_nocbs=2-15" >> /boot/cmdline
echo "intel_pstate=disable processor.max_cstate=1" >> /boot/cmdline
echo "default_hugepagesz=1G hugepagesz=1G hugepages=32" >> /boot/cmdline
echo "net.core.rmem_max=134217728 net.core.wmem_max=134217728" >> /etc/sysctl.conf
```

### Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| DPDK | 24.07+ | Kernel bypass networking |
| Aeron | 1.40+ | Low-latency messaging |
| Boost.Asio | 1.84+ | Async I/O (fallback) |
| libpcap | 1.10+ | Packet capture for replay |
| hdr_histogram | 1.12+ | Latency distribution tracking |

### Build Flags

```bash
# GCC flags for maximum throughput
CFLAGS="-O3 -march=native -mtune=native -flto -fno-semantic-interposition"
CFLAGS="$CFLAGS -DNDEBUG -D_FORTIFY_SOURCE=0"
CFLAGS="$CFLAGS -fomit-frame-pointer -funroll-loops"
LDFLAGS="-Wl,-O1 -Wl,--as-needed -flto"
```

## Benchmark Code

### Reference Implementation (C++ with DPDK)

```cpp
// messages_per_second.cpp
// Compile: g++ -O3 -march=native -o mps messages_per_second.cpp -lrte_eal -lrte_ethdev

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_ring.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>

#define RX_RING_SIZE 4096
#define TX_RING_SIZE 4096
#define NUM_MBUFS 65536
#define MBUF_CACHE_SIZE 512
#define BURST_SIZE 32
#define MEASURE_DURATION_SEC 60
#define WARMUP_DURATION_SEC 30

struct alignas(64) WorkerStats {
    std::atomic<uint64_t> messages_processed{0};
    std::atomic<uint64_t> packets_received{0};
    std::atomic<uint64_t> bytes_received{0};
    std::atomic<uint64_t> drops{0};
    char pad[64 - 5 * sizeof(std::atomic<uint64_t>)];
};

static WorkerStats g_stats[MAX_LCORE];
static volatile bool g_running = false;

static int processing_loop(void *arg) {
    unsigned lcore_id = rte_lcore_id();
    unsigned port_id = *(unsigned *)arg;
    struct rte_mbuf *bufs[BURST_SIZE];
    
    // Pin to isolated CPU core
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(lcore_id, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpuset), &cpuset);
    
    uint64_t local_msgs = 0;
    uint64_t local_pkts = 0;
    uint64_t local_bytes = 0;
    uint64_t local_drops = 0;
    
    while (g_running) {
        uint16_t nb_rx = rte_eth_rx_burst(port_id, 0, bufs, BURST_SIZE);
        if (unlikely(nb_rx == 0)) continue;
        
        local_pkts += nb_rx;
        
        for (uint16_t i = 0; i < nb_rx; i++) {
            uint16_t pkt_len = rte_pktmbuf_pkt_len(bufs[i]);
            local_bytes += pkt_len;
            
            // Count messages: assume 1 message per packet for small packets
            // For batched messages, parse the payload
            if (pkt_len <= 256) {
                local_msgs++;
            } else {
                // Parse batch header for message count
                uint8_t *data = rte_pktmbuf_mtod(bufs[i], uint8_t *);
                uint16_t batch_count = *(uint16_t *)(data + 2); // offset for batch count
                local_msgs += batch_count;
            }
            
            rte_pktmbuf_free(bufs[i]);
        }
    }
    
    g_stats[lcore_id].messages_processed = local_msgs;
    g_stats[lcore_id].packets_received = local_pkts;
    g_stats[lcore_id].bytes_received = local_bytes;
    g_stats[lcore_id].drops = local_drops;
    
    return 0;
}

int main(int argc, char *argv[]) {
    // Initialize DPDK EAL
    int ret = rte_eal_init(argc, argv);
    if (ret < 0) rte_exit(EXIT_FAILURE, "EAL init failed\n");
    
    unsigned port_id = 0;
    struct rte_eth_conf port_conf = {};
    struct rte_eth_rxconf rxconf;
    struct rte_mempool *mbuf_pool;
    
    // Configure port
    uint16_t nb_rxd = RX_RING_SIZE;
    uint16_t nb_txd = TX_RING_SIZE;
    
    ret = rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    if (ret < 0) rte_exit(EXIT_FAILURE, "Dev configure failed\n");
    
    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", NUM_MBUFS,
        MBUF_CACHE_SIZE, 0, RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
    
    rxconf = rte_eth_devices[port_id].data->dev_conf.rxconf;
    rxconf.offloads = DEV_RX_OFFLOAD_CHECKSUM;
    
    ret = rte_eth_rx_queue_setup(port_id, 0, nb_rxd,
        rte_eth_dev_socket_id(port_id), &rxconf, mbuf_pool);
    if (ret < 0) rte_exit(EXIT_FAILURE, "RX queue setup failed\n");
    
    ret = rte_eth_tx_queue_setup(port_id, 0, nb_txd,
        rte_eth_dev_socket_id(port_id), NULL);
    if (ret < 0) rte_exit(EXIT_FAILURE, "TX queue setup failed\n");
    
    ret = rte_eth_dev_start(port_id);
    if (ret < 0) rte_exit(EXIT_FAILURE, "Dev start failed\n");
    
    rte_eth_promiscuous_enable(port_id);
    
    // Launch worker on each available lcore
    unsigned worker_arg = port_id;
    rte_eal_mp_remote_launch(processing_loop, &worker_arg, SKIP_MAIN);
    
    // Warm-up period
    printf("Warming up for %d seconds...\n", WARMUP_DURATION_SEC);
    sleep(WARMUP_DURATION_SEC);
    
    // Reset stats
    for (unsigned i = 0; i < MAX_LCORE; i++) {
        g_stats[i].messages_processed = 0;
        g_stats[i].packets_received = 0;
        g_stats[i].bytes_received = 0;
        g_stats[i].drops = 0;
    }
    
    // Measurement period
    printf("Measuring for %d seconds...\n", MEASURE_DURATION_SEC);
    g_running = true;
    sleep(MEASURE_DURATION_SEC);
    g_running = false;
    
    rte_eal_mp_wait_lcore();
    
    // Aggregate results
    uint64_t total_msgs = 0, total_pkts = 0, total_bytes = 0, total_drops = 0;
    for (unsigned i = 0; i < MAX_LCORE; i++) {
        total_msgs += g_stats[i].messages_processed.load();
        total_pkts += g_stats[i].packets_received.load();
        total_bytes += g_stats[i].bytes_received.load();
        total_drops += g_stats[i].drops.load();
    }
    
    double duration = MEASURE_DURATION_SEC;
    printf("\n=== Messages/sec Benchmark Results ===\n");
    printf("Duration:           %.1f seconds\n", duration);
    printf("Total messages:     %lu\n", total_msgs);
    printf("Total packets:      %lu\n", total_pkts);
    printf("Total bytes:        %lu\n", total_bytes);
    printf("Messages/sec:       %.2f M\n", total_msgs / duration / 1e6);
    printf("Packets/sec:        %.2f M\n", total_pkts / duration / 1e6);
    printf("Throughput:         %.2f Gb/s\n", total_bytes * 8.0 / duration / 1e9);
    printf("Drops:              %lu\n", total_drops);
    printf("Messages/packet:    %.2f\n", (double)total_msgs / total_pkts);
    
    rte_eth_dev_stop(port_id);
    rte_eth_dev_close(port_id);
    return 0;
}
```

### Python Harness for Traffic Generation

```python
#!/usr/bin/env python3
"""Generate market data traffic for messages/sec benchmark."""

import socket
import struct
import time
import multiprocessing
from dataclasses import dataclass

@dataclass
class MarketMessage:
    timestamp: int  # nanoseconds
    symbol_id: int
    price: int      # fixed-point
    quantity: int
    side: int       # 0=bid, 1=ask
    msg_type: int   # 0=quote, 1=trade, 2=book_update

def generate_message_batch(batch_size: int, base_ts: int) -> bytes:
    """Generate a batch of market data messages."""
    header = struct.pack('!IH', base_ts & 0xFFFFFFFF, batch_size)
    payload = b''
    for i in range(batch_size):
        msg = MarketMessage(
            timestamp=base_ts + i * 100,
            symbol_id=1000 + (i % 500),
            price=1000000 + (i % 10000),
            quantity=100 * (i % 100 + 1),
            side=i % 2,
            msg_type=i % 3
        )
        payload += struct.pack('!QIIQBB', msg.timestamp, msg.symbol_id,
                               msg.price, msg.quantity, msg.side, msg.msg_type)
    return header + payload

def traffic_generator(target_rate_mps: float, port: int, group: str):
    """Generate UDP multicast traffic at target rate."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    
    batch_size = 4
    interval = batch_size / (target_rate_mps * 1e6)  # seconds per batch
    base_ts = time.time_ns()
    
    print(f"Generating {target_rate_mps} M msg/s to {group}:{port}")
    
    while True:
        start = time.perf_counter()
        batch = generate_message_batch(batch_size, base_ts)
        sock.sendto(batch, (group, port))
        base_ts += batch_size * 100
        
        elapsed = time.perf_counter() - start
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

if __name__ == '__main__':
    import sys
    rate = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0  # 10M msg/s default
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 50000
    group = sys.argv[3] if len(sys.argv) > 3 else '239.1.1.1'
    traffic_generator(rate, port, group)
```

## Expected Results

### Production ULL System Reference Numbers

| System Tier | Messages/sec | Packet Rate | Latency (p99) | Hardware |
|------------|-------------|-------------|---------------|----------|
| Entry ULL | 5–10 M | 1–2 Mpps | 5–10 µs | 100GbE + DPDK |
| Mid ULL | 20–50 M | 5–10 Mpps | 2–5 µs | 400GbE + DPDK |
| Extreme ULL | 100–500 M | 20–50 Mpps | 0.5–2 µs | FPGA feed handler |
| Custom FPGA | 1 B+ | 100+ Mpps | <500 ns | Full hardware pipeline |

### Scaling Characteristics

| Cores | Expected Throughput | Efficiency |
|-------|-------------------|------------|
| 1 | 2–5 M msg/s | Baseline |
| 4 | 8–20 M msg/s | 80–90% |
| 8 | 15–40 M msg/s | 75–85% |
| 16 | 30–80 M msg/s | 70–80% |
| 32 | 60–150 M msg/s | 65–75% |

## Analysis

### Identifying Bottlenecks

| Symptom | Likely Cause | Remedy |
|---------|-------------|--------|
| Throughput plateaus at ~5M msg/s/core | Memory bandwidth | Use hugepages, NUMA-local allocation |
| Throughput drops with larger messages | PCIe bandwidth | Enable SR-IOV, use Gen5 NIC |
| High variance in throughput | CPU contention | Isolate cores, disable IRQ on worker cores |
| Drops at high rates | Ring buffer overflow | Increase ring size, add backpressure |
| Throughput doesn't scale with cores | Lock contention | Use per-core rings, avoid shared state |

### Optimization Checklist

- [ ] CPU cores isolated (`isolcpus`, `nohz_full`)
- [ ] Hugepages configured (1GB pages)
- [ ] NUMA-local memory allocation
- [ ] NIC IRQ affinity set to non-worker cores
- [ ] Ring buffer sized for 10ms of burst
- [ ] Message parsing is branch-predictor friendly
- [ ] Cache-line alignment for all hot data structures
- [ ] Batch processing (32+ messages per iteration)
- [ ] Zero-copy from NIC to application
- [ ] Hardware timestamping enabled
