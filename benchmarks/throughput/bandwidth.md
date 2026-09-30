# Bandwidth Throughput Benchmark

## Overview

Measures network and memory bandwidth for ultra-low-latency systems. Covers network interface bandwidth (100GbE–800GbE), memory bandwidth (DDR5), and interconnect bandwidth (InfiniBand, CXL).

## Measurement Methodology

### What to Measure

- **Network bandwidth**: Sustained data transfer rate over network interface
- **Memory bandwidth**: Sustained data transfer rate to/from main memory
- **Interconnect bandwidth**: Sustained data transfer rate over high-speed interconnect
- **Bidirectional bandwidth**: Simultaneous send and receive throughput

### Measurement Protocol

1. **Warm-up**: 30 seconds to reach steady state
2. **Measurement window**: 60 seconds at target bandwidth
3. **Message sizes**: 64B, 256B, 1KB, 4KB, 64KB, 1MB (measure scaling)
4. **Repeat**: 5 iterations, report median

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Message size | 64B–1MB | Cover all realistic payload sizes |
| Protocol | TCP, UDP, RDMA | Measure all transport options |
| Queue depth | 1–128 | Measure latency vs bandwidth tradeoff |
| Direction | Unidirectional, bidirectional | Realistic traffic patterns |
| NUMA | Local, remote | Measure NUMA impact |

### Common Pitfalls

- **Measuring with small messages**: Small messages are CPU-bound, not bandwidth-bound
- **Not testing bidirectional**: Full-duplex interfaces can saturate in both directions
- **Ignoring protocol overhead**: TCP/IP overhead reduces effective bandwidth
- **Not testing at production message size**: Bandwidth varies significantly with message size
- **Ignoring NUMA effects**: Remote memory access reduces effective bandwidth

## Hardware Requirements

### Minimum (Entry ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 8 cores @ 3.0 GHz | Intel Xeon W-3400 |
| NIC | 100GbE dual-port | Mellanox ConnectX-6 |
| Memory | 64 GB DDR5-4800 | 38 GB/s per socket |
| Interconnect | 100GbE Ethernet | Standard data center fabric |
| OS | Linux 6.x | Kernel networking |

### Recommended (Mid ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 32 cores @ 3.5 GHz | AMD EPYC 9654 |
| NIC | 400GbE dual-port | Mellanox ConnectX-7 |
| Memory | 256 GB DDR5-5600 | 400+ GB/s per socket |
| Interconnect | 400GbE RoCE v2 | Low-latency RDMA fabric |
| OS | Linux 6.x with DPDK | Kernel bypass networking |

### Extreme ULL

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 64+ cores @ 4.0 GHz | AMD EPYC 9754 |
| NIC | 800GbE or custom FPGA | Sub-100ns latency |
| Memory | 2 TB DDR5-6400 + HBM | 600+ GB/s per socket |
| Interconnect | InfiniBand XDR or CXL 2.0 | 800Gb/s+ per port |
| OS | Linux 6.x with DPDK/SPDK | Full kernel bypass |

## Software Requirements

### OS & Kernel

```bash
# Kernel parameters for bandwidth
echo "isolcpus=2-31 nohz_full=2-31 rcu_nocbs=2-31" >> /boot/cmdline
echo "intel_pstate=disable processor.max_cstate=1" >> /boot/cmdline
echo "net.core.rmem_max=134217728 net.core.wmem_max=134217728" >> /etc/sysctl.conf
echo "net.core.netdev_max_backlog=65536" >> /etc/sysctl.conf
echo "net.ipv4.tcp_rmem=4096 87380 134217728" >> /etc/sysctl.conf
echo "net.ipv4.tcp_wmem=4096 65536 134217728" >> /etc/sysctl.conf
```

### Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| DPDK | 24.07+ | Kernel bypass networking |
| ibverbs | 1.16+ | RDMA/InfiniBand access |
| NCCL | 2.20+ | Collective communications |
| memtester | 4.6+ | Memory bandwidth testing |
| iperf3 | 3.16+ | Network bandwidth testing |

### Build Flags

```bash
CFLAGS="-O3 -march=native -mtune=native -flto -fno-semantic-interposition"
CFLAGS="$CFLAGS -DNDEBUG -D_FORTIFY_SOURCE=0"
CFLAGS="$CFLAGS -fomit-frame-pointer -funroll-loops -falign-loops=64"
```

## Benchmark Code

### Network Bandwidth (C with DPDK)

```cpp
// bandwidth_dpdk.cpp
// DPDK-based network bandwidth benchmark

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

struct alignas(64) BandwidthStats {
    std::atomic<uint64_t> bytes_sent{0};
    std::atomic<uint64_t> bytes_received{0};
    std::atomic<uint64_t> packets_sent{0};
    std::atomic<uint64_t> packets_received{0};
    std::atomic<uint64_t> errors{0};
    char pad[64 - 5 * sizeof(std::atomic<uint64_t>)];
};

static BandwidthStats g_stats[MAX_LCORE];
static volatile bool g_running = false;

// Generate test pattern
void fill_pattern(rte_mbuf *m, uint16_t size) {
    uint8_t *data = rte_pktmbuf_mtod(m, uint8_t *);
    for (uint16_t i = 0; i < size; i++) {
        data[i] = (uint8_t)(i & 0xFF);
    }
}

static int sender_loop(void *arg) {
    unsigned lcore_id = rte_lcore_id();
    unsigned port_id = *(unsigned *)arg;
    struct rte_mbuf *tx_bufs[BURST_SIZE];
    struct rte_mempool *mbuf_pool = (struct rte_mempool *)((void **)arg)[1];
    
    uint64_t local_bytes = 0;
    uint64_t local_pkts = 0;
    
    while (g_running) {
        // Allocate mbufs
        for (int i = 0; i < BURST_SIZE; i++) {
            tx_bufs[i] = rte_pktmbuf_alloc(mbuf_pool);
            if (!tx_bufs[i]) break;
            fill_pattern(tx_bufs[i], 1024); // 1KB packets
        }
        
        // Send burst
        uint16_t nb_tx = rte_eth_tx_burst(port_id, 0, tx_bufs, BURST_SIZE);
        local_pkts += nb_tx;
        local_bytes += nb_tx * 1024;
        
        // Free unsent
        for (uint16_t i = nb_tx; i < BURST_SIZE; i++) {
            rte_pktmbuf_free(tx_bufs[i]);
        }
    }
    
    g_stats[lcore_id].bytes_sent = local_bytes;
    g_stats[lcore_id].packets_sent = local_pkts;
    
    return 0;
}

static int receiver_loop(void *arg) {
    unsigned lcore_id = rte_lcore_id();
    unsigned port_id = *(unsigned *)arg;
    struct rte_mbuf *rx_bufs[BURST_SIZE];
    
    uint64_t local_bytes = 0;
    uint64_t local_pkts = 0;
    
    while (g_running) {
        uint16_t nb_rx = rte_eth_rx_burst(port_id, 0, rx_bufs, BURST_SIZE);
        if (nb_rx == 0) continue;
        
        local_pkts += nb_rx;
        for (uint16_t i = 0; i < nb_rx; i++) {
            local_bytes += rte_pktmbuf_pkt_len(rx_bufs[i]);
            rte_pktmbuf_free(rx_bufs[i]);
        }
    }
    
    g_stats[lcore_id].bytes_received = local_bytes;
    g_stats[lcore_id].packets_received = local_pkts;
    
    return 0;
}

int main(int argc, char *argv[]) {
    int ret = rte_eal_init(argc, argv);
    if (ret < 0) rte_exit(EXIT_FAILURE, "EAL init failed\n");
    
    unsigned port_id = 0;
    struct rte_eth_conf port_conf = {};
    struct rte_mempool *mbuf_pool;
    
    ret = rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    if (ret < 0) rte_exit(EXIT_FAILURE, "Dev configure failed\n");
    
    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", NUM_MBUFS,
        MBUF_CACHE_SIZE, 0, RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
    
    ret = rte_eth_rx_queue_setup(port_id, 0, RX_RING_SIZE,
        rte_eth_dev_socket_id(port_id), NULL, mbuf_pool);
    ret = rte_eth_tx_queue_setup(port_id, 0, TX_RING_SIZE,
        rte_eth_dev_socket_id(port_id), NULL);
    
    ret = rte_eth_dev_start(port_id);
    rte_eth_promiscuous_enable(port_id);
    
    // Launch sender and receiver on different cores
    void *args[2] = {&port_id, mbuf_pool};
    rte_eal_remote_launch(sender_loop, args, 1);
    rte_eal_remote_launch(receiver_loop, &port_id, 2);
    
    // Warm-up
    printf("Warming up for %d seconds...\n", WARMUP_DURATION_SEC);
    sleep(WARMUP_DURATION_SEC);
    
    // Reset stats
    for (unsigned i = 0; i < MAX_LCORE; i++) {
        g_stats[i].bytes_sent = 0;
        g_stats[i].bytes_received = 0;
        g_stats[i].packets_sent = 0;
        g_stats[i].packets_received = 0;
    }
    
    // Measurement
    printf("Measuring for %d seconds...\n", MEASURE_DURATION_SEC);
    g_running = true;
    sleep(MEASURE_DURATION_SEC);
    g_running = false;
    
    rte_eal_mp_wait_lcore();
    
    // Aggregate
    uint64_t total_sent = 0, total_recv = 0;
    uint64_t total_pkts_sent = 0, total_pkts_recv = 0;
    for (unsigned i = 0; i < MAX_LCORE; i++) {
        total_sent += g_stats[i].bytes_sent.load();
        total_recv += g_stats[i].bytes_received.load();
        total_pkts_sent += g_stats[i].packets_sent.load();
        total_pkts_recv += g_stats[i].packets_received.load();
    }
    
    double duration = MEASURE_DURATION_SEC;
    printf("\n=== Bandwidth Benchmark Results ===\n");
    printf("Duration:           %.1f seconds\n", duration);
    printf("Bytes sent:         %lu\n", total_sent);
    printf("Bytes received:     %lu\n", total_recv);
    printf("Packets sent:       %lu\n", total_pkts_sent);
    printf("Packets received:   %lu\n", total_pkts_recv);
    printf("Send bandwidth:     %.2f Gb/s\n", total_sent * 8.0 / duration / 1e9);
    printf("Receive bandwidth:  %.2f Gb/s\n", total_recv * 8.0 / duration / 1e9);
    printf("Combined bandwidth: %.2f Gb/s\n", (total_sent + total_recv) * 8.0 / duration / 1e9);
    
    rte_eth_dev_stop(port_id);
    rte_eth_dev_close(port_id);
    return 0;
}
```

### Memory Bandwidth (C)

```cpp
// memory_bandwidth.cpp
// Memory bandwidth benchmark

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>
#include <immintrin.h>

#define BUFFER_SIZE (256 * 1024 * 1024)  // 256 MB per thread
#define MEASURE_DURATION_SEC 60
#define WARMUP_DURATION_SEC 10

struct alignas(64) MemStats {
    std::atomic<uint64_t> bytes_read{0};
    std::atomic<uint64_t> bytes_written{0};
    char pad[64 - 2 * sizeof(std::atomic<uint64_t>)];
};

static MemStats g_stats[32];
static volatile bool g_running = false;

// AVX-512 memory read
void avx512_read(void *buf, size_t size) {
    __m512i *ptr = (__m512i *)buf;
    size_t vec_count = size / 64;
    __m512i sum = _mm512_setzero_si512();
    
    for (size_t i = 0; i < vec_count; i++) {
        __m512i val = _mm512_load_si512(&ptr[i]);
        sum = _mm512_add_epi64(sum, val);
    }
    
    // Prevent optimization
    volatile __m512i sink = sum;
    (void)sink;
}

// AVX-512 memory write
void avx512_write(void *buf, size_t size) {
    __m512i *ptr = (__m512i *)buf;
    size_t vec_count = size / 64;
    __m512i val = _mm512_set1_epi64(0xDEADBEEFCAFEBABE);
    
    for (size_t i = 0; i < vec_count; i++) {
        _mm512_store_si512(&ptr[i], val);
    }
}

void worker_thread(int thread_id, int mode) {
    // Allocate aligned buffer
    void *buf = aligned_alloc(64, BUFFER_SIZE);
    if (!buf) {
        fprintf(stderr, "Failed to allocate buffer for thread %d\n", thread_id);
        return;
    }
    
    // Pin to CPU core
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(thread_id + 1, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpuset), &cpuset);
    
    uint64_t local_read = 0, local_written = 0;
    
    while (g_running) {
        if (mode == 0) {  // Read
            avx512_read(buf, BUFFER_SIZE);
            local_read += BUFFER_SIZE;
        } else {  // Write
            avx512_write(buf, BUFFER_SIZE);
            local_written += BUFFER_SIZE;
        }
    }
    
    g_stats[thread_id].bytes_read = local_read;
    g_stats[thread_id].bytes_written = local_written;
    
    free(buf);
}

int main(int argc, char* argv[]) {
    int num_threads = argc > 1 ? atoi(argv[1]) : 8;
    int mode = argc > 2 ? atoi(argv[2]) : 0;  // 0=read, 1=write
    
    printf("Memory Bandwidth Benchmark\n");
    printf("Threads: %d, Mode: %s\n", num_threads, mode == 0 ? "read" : "write");
    printf("Buffer size: %d MB per thread\n", BUFFER_SIZE / 1024 / 1024);
    
    g_running = true;
    
    std::vector<std::thread> threads;
    for (int i = 0; i < num_threads; i++) {
        threads.emplace_back(worker_thread, i, mode);
    }
    
    // Warm-up
    printf("Warming up for %d seconds...\n", WARMUP_DURATION_SEC);
    sleep(WARMUP_DURATION_SEC);
    
    // Reset stats
    for (int i = 0; i < 32; i++) {
        g_stats[i].bytes_read = 0;
        g_stats[i].bytes_written = 0;
    }
    
    // Measurement
    printf("Measuring for %d seconds...\n", MEASURE_DURATION_SEC);
    auto start = std::chrono::high_resolution_clock::now();
    sleep(MEASURE_DURATION_SEC);
    g_running = false;
    auto end = std::chrono::high_resolution_clock::now();
    
    for (auto& t : threads) t.join();
    
    double duration = std::chrono::duration<double>(end - start).count();
    
    uint64_t total_read = 0, total_written = 0;
    for (int i = 0; i < num_threads; i++) {
        total_read += g_stats[i].bytes_read.load();
        total_written += g_stats[i].bytes_written.load();
    }
    
    printf("\n=== Memory Bandwidth Results ===\n");
    printf("Duration:           %.1f seconds\n", duration);
    printf("Total read:         %lu bytes\n", total_read);
    printf("Total written:      %lu bytes\n", total_written);
    printf("Read bandwidth:     %.2f GB/s\n", total_read / duration / 1e9);
    printf("Write bandwidth:    %.2f GB/s\n", total_written / duration / 1e9);
    printf("Combined bandwidth: %.2f GB/s\n", (total_read + total_written) / duration / 1e9);
    
    return 0;
}
```

### iperf3 Commands (Reference)

```bash
# Network bandwidth test
# Server
iperf3 -s -p 5201

# Client - 100GbE test
iperf3 -c <server_ip> -p 5201 -t 60 -P 8 -w 256K

# Client - RDMA test (requires ib_write_bw)
ib_write_bw -d <device> -a --report_gbits

# Client - bidirectional
iperf3 -c <server_ip> -p 5201 -t 60 -P 8 --bidir
```

## Expected Results

### Network Bandwidth Reference Numbers

| Network Type | Per-Port BW | Bidirectional BW | Latency | CPU Usage |
|-------------|-------------|------------------|---------|-----------|
| 100GbE | 94 Gb/s | 188 Gb/s | 1–5 µs | 2–4 cores |
| 200GbE | 188 Gb/s | 376 Gb/s | 1–3 µs | 4–8 cores |
| 400GbE | 376 Gb/s | 752 Gb/s | 0.5–2 µs | 8–16 cores |
| 800GbE | 752 Gb/s | 1.5 Tb/s | 0.5–1 µs | 16–32 cores |
| InfiniBand NDR | 400 Gb/s | 800 Gb/s | 100–200 ns | Near-zero (offload) |
| InfiniBand XDR | 800 Gb/s | 1.6 Tb/s | 100–200 ns | Near-zero (offload) |

### Memory Bandwidth Reference Numbers

| Memory Type | Per-Socket BW | Per-Channel BW | Latency | Notes |
|-------------|---------------|----------------|---------|-------|
| DDR5-4800 | 307 GB/s | 38.4 GB/s | 80–100 ns | 8 channels |
| DDR5-5600 | 358 GB/s | 44.8 GB/s | 70–90 ns | 8 channels |
| DDR5-6400 | 409 GB/s | 51.2 GB/s | 60–80 ns | 8 channels |
| HBM2e | 460 GB/s | — | 30–50 ns | On-package |
| HBM3 | 600+ GB/s | — | 20–40 ns | On-package |
| CXL Memory | 25–50 GB/s | — | 100–200 ns | Attached memory |

### Message Size Scaling (400GbE)

| Message Size | Effective BW | Packets/sec | CPU Usage |
|-------------|-------------|-------------|-----------|
| 64 B | 10–20 Gb/s | 20–40 Mpps | 100% (CPU-bound) |
| 256 B | 50–80 Gb/s | 25–40 Mpps | 80–100% |
| 1 KB | 150–250 Gb/s | 15–25 Mpps | 50–70% |
| 4 KB | 300–370 Gb/s | 7–9 Mpps | 30–50% |
| 64 KB | 370–390 Gb/s | 0.5–0.6 Mpps | 10–20% |
| 1 MB | 390–400 Gb/s | 350–400 Kpps | 5–10% |

## Analysis

### Identifying Bottlenecks

| Symptom | Likely Cause | Remedy |
|---------|-------------|--------|
| Bandwidth plateaus below line rate | CPU-bound (small messages) | Use larger messages, enable hardware offload |
| High CPU usage at line rate | Kernel overhead | Use DPDK or RDMA |
| Bidirectional lower than unidirectional | PCIe bandwidth limit | Use Gen5, check PCIe lane allocation |
| NUMA-related performance drop | Remote memory access | Pin to NUMA-local socket |
| Bandwidth drops with more threads | Memory controller saturation | Reduce threads, use NUMA-aware allocation |

### Optimization Checklist

- [ ] Use DPDK or RDMA to bypass kernel networking
- [ ] Message size matched to workload (larger = more efficient)
- [ ] NUMA-local memory and NIC allocation
- [ ] PCIe Gen5 x16 for 400GbE+ NICs
- [ ] Hardware offload enabled (TSO, LRO, checksum)
- [ ] Multiple queues for parallel processing
- [ ] CPU core isolation and pinning
- [ ] Hugepages for all memory buffers
- [ ] Zero-copy data path (no memcpy in hot path)
- [ ] Batch processing (32+ packets per iteration)
