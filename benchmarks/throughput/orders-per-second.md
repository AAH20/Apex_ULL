# Orders/sec Throughput Benchmark

## Overview

Measures the rate at which a system can process order entry messages — new orders, cancellations, modifications — from receipt through risk check, matching engine, and acknowledgment. This is the primary throughput metric for order gateways and matching engines.

## Measurement Methodology

### What to Measure

- **Order acceptance rate**: Orders received and acknowledged per second
- **Order processing rate**: Orders fully processed (risk check + matching + ack) per second
- **Round-trip throughput**: Complete order lifecycle (send → ack) per second
- **Sustained rate**: Steady-state throughput under continuous load

### Measurement Protocol

1. **Warm-up**: 60 seconds to populate order books, caches, and connection pools
2. **Measurement window**: 120 seconds at target order rate
3. **Order mix**: Realistic distribution (60% new, 25% cancel, 15% modify)
4. **Repeat**: 5 iterations, report median

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Order size | 48–128 bytes | Typical FIX/FAST/binary order |
| Protocol | TCP (order entry) | Reliable delivery required |
| Order book depth | 100–1000 levels | Realistic market depth |
| Instruments | 100–10,000 | Diverse symbol coverage |
| Risk checks | Pre-trade + post-trade | Full risk pipeline |
| Ack latency | <10 µs target | Must not bottleneck throughput |

### Common Pitfalls

- **Measuring only order submission**: Must measure full round-trip including ack
- **Ignoring order book state**: Empty books process faster than deep books
- **Not testing order mix**: All-new-order workloads are unrealistic
- **TCP head-of-line blocking**: One slow order can block the entire stream
- **Not measuring under rejection**: Rejected orders still consume throughput

## Hardware Requirements

### Minimum (Entry ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 16 cores @ 3.5 GHz | AMD EPYC 9354 |
| NIC | 100GbE dual-port | Mellanox ConnectX-6 |
| Memory | 128 GB DDR5 | Order book storage |
| Storage | NVMe Gen4 SSD | Order persistence |
| OS | Linux 6.x RT-PREEMPT | Kernel bypass for market data |

### Recommended (Mid ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 48 cores @ 3.7 GHz | AMD EPYC 9554 |
| NIC | 400GbE dual-port | Mellanox ConnectX-7 |
| Memory | 512 GB DDR5-5600 | Full order book in memory |
| Storage | NVMe Gen5 SSD | 14 GB/s for persistence |
| FPGA | AMD Versal AI Edge | Order encoding/decoding offload |

### Extreme ULL

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 96+ cores @ 4.0 GHz | AMD EPYC 9754 |
| NIC | 800GbE or custom FPGA | Sub-100ns order processing |
| Memory | 2 TB DDR5 + HBM | All state in memory |
| Storage | CXL persistent memory | Sub-µs order persistence |
| FPGA | Intel Agilex 7 | Full matching engine in hardware |

## Software Requirements

### OS & Kernel

```bash
# Kernel parameters for order processing
echo "isolcpus=2-31 nohz_full=2-31 rcu_nocbs=2-31" >> /boot/cmdline
echo "intel_pstate=disable processor.max_cstate=1" >> /boot/cmdline
echo "default_hugepagesz=1G hugepagesz=1G hugepages=64" >> /boot/cmdline
echo "net.ipv4.tcp_low_latency=1" >> /etc/sysctl.conf
echo "net.core.busy_poll=50 net.core.busy_read=50" >> /etc/sysctl.conf
```

### Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| DPDK | 24.07+ | Kernel bypass for market data |
| Aeron | 1.40+ | Order gateway messaging |
| Boost.Beast | 1.84+ | WebSocket/HTTP order entry |
| flatbuffers | 23.5+ | Order serialization |
| hdr_histogram | 1.12+ | Latency tracking |

### Build Flags

```bash
CFLAGS="-O3 -march=native -mtune=native -flto -fno-semantic-interposition"
CFLAGS="$CFLAGS -DNDEBUG -D_FORTIFY_SOURCE=0"
CFLAGS="$CFLAGS -fomit-frame-pointer -funroll-loops -falign-loops=64"
```

## Benchmark Code

### Reference Implementation (C++)

```cpp
// orders_per_second.cpp
// Order gateway throughput benchmark

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>
#include <memory>
#include <random>

// Order types
enum class OrderType : uint8_t {
    NEW = 0,
    CANCEL = 1,
    MODIFY = 2
};

enum class OrderSide : uint8_t {
    BUY = 0,
    SELL = 1
};

// Compact order structure (64 bytes, cache-line friendly)
struct alignas(64) Order {
    uint64_t order_id;
    uint64_t timestamp_ns;
    uint64_t symbol_id;
    int64_t price;       // fixed-point 1e-9
    uint64_t quantity;
    uint64_t account_id;
    OrderType type;
    OrderSide side;
    uint32_t flags;
    uint32_t padding;
};

// Order book level
struct PriceLevel {
    int64_t price;
    uint64_t total_quantity;
    uint32_t order_count;
};

// Matching engine shard (per-symbol)
struct OrderBook {
    static constexpr int MAX_LEVELS = 1024;
    PriceLevel bids[MAX_LEVELS];
    PriceLevel asks[MAX_LEVELS];
    int bid_count = 0;
    int ask_count = 0;
    uint64_t symbol_id;
    
    // Process order, return number of fills
    uint32_t process_order(const Order& order, uint64_t* fill_ids, int64_t* fill_prices, uint64_t* fill_qtys);
};

// Statistics
struct alignas(64) Stats {
    std::atomic<uint64_t> orders_received{0};
    std::atomic<uint64_t> orders_accepted{0};
    std::atomic<uint64_t> orders_rejected{0};
    std::atomic<uint64_t> orders_filled{0};
    std::atomic<uint64_t> orders_cancelled{0};
    std::atomic<uint64_t> total_latency_ns{0};
    std::atomic<uint64_t> max_latency_ns{0};
    char pad[64 - 7 * sizeof(std::atomic<uint64_t>)];
};

static Stats g_stats;
static volatile bool g_running = false;

// Generate realistic order mix
Order generate_order(uint64_t seq, std::mt19937_64& rng) {
    Order order{};
    order.order_id = seq;
    order.timestamp_ns = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    order.symbol_id = 1000 + (rng() % 5000);
    order.price = 1000000000LL + (rng() % 100000000LL); // $100.00 - $110.00
    order.quantity = 100 * (rng() % 1000 + 1);
    order.account_id = rng() % 10000;
    
    uint32_t r = rng() % 100;
    if (r < 60) order.type = OrderType::NEW;
    else if (r < 85) order.type = OrderType::CANCEL;
    else order.type = OrderType::MODIFY;
    
    order.side = (rng() % 2 == 0) ? OrderSide::BUY : OrderSide::SELL;
    order.flags = 0;
    return order;
}

// Simulate order processing pipeline
void process_order_pipeline(const Order& order) {
    auto start = std::chrono::high_resolution_clock::now();
    
    // Stage 1: Decode and validate (simulated)
    // In real system: parse FIX/binary, validate fields
    
    // Stage 2: Risk check (simulated)
    bool risk_pass = (order.quantity < 10000000 && order.price > 0);
    
    // Stage 3: Matching engine (simulated)
    uint32_t fills = 0;
    if (risk_pass && order.type == OrderType::NEW) {
        fills = 1 + (order.order_id % 3); // 1-3 fills per order
    }
    
    // Stage 4: Generate ack (simulated)
    auto end = std::chrono::high_resolution_clock::now();
    uint64_t latency = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    
    // Update stats
    g_stats.orders_received++;
    if (risk_pass) {
        g_stats.orders_accepted++;
        g_stats.orders_filled += fills;
    } else {
        g_stats.orders_rejected++;
    }
    g_stats.total_latency_ns += latency;
    
    uint64_t prev_max = g_stats.max_latency_ns.load();
    while (latency > prev_max && !g_stats.max_latency_ns.compare_exchange_weak(prev_max, latency));
}

// Worker thread
void worker_thread(int num_orders, int thread_id) {
    std::mt19937_64 rng(thread_id * 12345);
    
    for (int i = 0; i < num_orders && g_running; i++) {
        Order order = generate_order(thread_id * 1000000000ULL + i, rng);
        process_order_pipeline(order);
    }
}

int main(int argc, char* argv[]) {
    int num_threads = argc > 1 ? atoi(argv[1]) : 8;
    int orders_per_thread = argc > 2 ? atoi(argv[2]) : 1000000;
    
    printf("Orders/sec Benchmark\n");
    printf("Threads: %d, Orders/thread: %d\n", num_threads, orders_per_thread);
    
    g_running = true;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<std::thread> threads;
    for (int i = 0; i < num_threads; i++) {
        threads.emplace_back(worker_thread, orders_per_thread, i);
    }
    
    for (auto& t : threads) t.join();
    
    auto end = std::chrono::high_resolution_clock::now();
    double duration_sec = std::chrono::duration<double>(end - start).count();
    
    uint64_t total_orders = g_stats.orders_received.load();
    uint64_t accepted = g_stats.orders_accepted.load();
    uint64_t rejected = g_stats.orders_rejected.load();
    uint64_t fills = g_stats.orders_filled.load();
    uint64_t avg_latency = total_orders > 0 ? g_stats.total_latency_ns.load() / total_orders : 0;
    uint64_t max_latency = g_stats.max_latency_ns.load();
    
    printf("\n=== Orders/sec Benchmark Results ===\n");
    printf("Duration:           %.3f seconds\n", duration_sec);
    printf("Total orders:       %lu\n", total_orders);
    printf("Orders/sec:         %.2f M\n", total_orders / duration_sec / 1e6);
    printf("Accepted:           %lu (%.1f%%)\n", accepted, 100.0 * accepted / total_orders);
    printf("Rejected:           %lu (%.1f%%)\n", rejected, 100.0 * rejected / total_orders);
    printf("Fills generated:    %lu\n", fills);
    printf("Avg latency:        %lu ns\n", avg_latency);
    printf("Max latency:        %lu ns\n", max_latency);
    printf("Throughput/core:    %.2f K orders/s\n", total_orders / duration_sec / num_threads / 1e3);
    
    return 0;
}
```

### Python Load Generator

```python
#!/usr/bin/env python3
"""Order entry load generator for orders/sec benchmark."""

import socket
import struct
import time
import multiprocessing
import random
from dataclasses import dataclass

@dataclass
class Order:
    order_id: int
    timestamp_ns: int
    symbol_id: int
    price: int
    quantity: int
    account_id: int
    order_type: int  # 0=new, 1=cancel, 2=modify
    side: int        # 0=buy, 1=sell

def encode_order(order: Order) -> bytes:
    """Encode order to binary format (48 bytes)."""
    return struct.pack('!QQQqQQBBH',
        order.order_id, order.timestamp_ns, order.symbol_id,
        order.price, order.quantity, order.account_id,
        order.order_type, order.side, 0)

def generate_order_batch(batch_size: int, base_id: int) -> bytes:
    """Generate a batch of orders with realistic mix."""
    orders = b''
    for i in range(batch_size):
        r = random.random()
        if r < 0.60:
            otype = 0  # NEW
        elif r < 0.85:
            otype = 1  # CANCEL
        else:
            otype = 2  # MODIFY
        
        order = Order(
            order_id=base_id + i,
            timestamp_ns=time.time_ns(),
            symbol_id=1000 + random.randint(0, 4999),
            price=1000000000 + random.randint(0, 100000000),
            quantity=100 * random.randint(1, 1000),
            account_id=random.randint(0, 9999),
            order_type=otype,
            side=random.randint(0, 1)
        )
        orders += encode_order(order)
    return orders

def order_load_generator(target_rate_ops: float, host: str, port: int, duration_sec: int):
    """Generate order entry traffic at target rate."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    batch_size = 16
    interval = batch_size / (target_rate_ops * 1e6)
    base_id = 0
    
    print(f"Generating {target_rate_ops} M orders/s to {host}:{port}")
    
    start = time.perf_counter()
    while time.perf_counter() - start < duration_sec:
        loop_start = time.perf_counter()
        batch = generate_order_batch(batch_size, base_id)
        sock.sendall(batch)
        base_id += batch_size
        
        elapsed = time.perf_counter() - loop_start
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    sock.close()

if __name__ == '__main__':
    import sys
    rate = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0  # 1M orders/s
    host = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8080
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    order_load_generator(rate, host, port, duration)
```

## Expected Results

### Production ULL System Reference Numbers

| System Tier | Orders/sec | Latency (p99) | Hardware |
|------------|-----------|---------------|----------|
| Entry ULL | 500K–1M | 5–10 µs | 100GbE + DPDK |
| Mid ULL | 2–5M | 2–5 µs | 400GbE + DPDK |
| Extreme ULL | 10–50M | 0.5–2 µs | FPGA order gateway |
| Custom FPGA | 100M+ | <500 ns | Full hardware pipeline |

### Scaling Characteristics

| Cores | Expected Throughput | Efficiency |
|-------|-------------------|------------|
| 1 | 100–200K orders/s | Baseline |
| 4 | 400–800K orders/s | 90–95% |
| 8 | 800K–1.6M orders/s | 85–90% |
| 16 | 1.5–3M orders/s | 80–85% |
| 32 | 3–6M orders/s | 75–80% |

## Analysis

### Identifying Bottlenecks

| Symptom | Likely Cause | Remedy |
|---------|-------------|--------|
| Throughput plateaus at low core count | Lock contention in matching engine | Shard by symbol, use per-symbol locks |
| High rejection rate under load | Risk check bottleneck | Parallelize risk checks, pre-compute limits |
| Latency spikes during cancel-heavy periods | Order book traversal | Use hash map for order lookup, not tree |
| Throughput drops with more symbols | Cache misses | Partition by symbol, NUMA-local books |
| TCP head-of-line blocking | Single connection bottleneck | Use multiple connections, connection pooling |

### Optimization Checklist

- [ ] Order book sharded by symbol (no cross-symbol locks)
- [ ] Per-symbol order ID hash map for O(1) cancel/modify lookup
- [ ] Risk checks parallelized across cores
- [ ] Order encoding uses zero-copy where possible
- [ ] Ack generation is asynchronous (don't block matching)
- [ ] Connection pooling for order entry clients
- [ ] NUMA-local order book allocation
- [ ] Cache-line alignment for order structures
- [ ] Batch order processing (16+ orders per iteration)
- [ ] Hardware timestamping on order receipt
