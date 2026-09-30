# Orders Per Second (ord/s)

**Definition:** The number of order operations (new orders, cancels, modifies, replacements) processed per second by a trading system or exchange matching engine.

---

## 1. Measurement Methodology

### 1.1 Order Operation Types

| Operation | Description | Typical Size | Frequency |
|-----------|-------------|-------------|-----------|
| New Order Single (NOS) | Submit a new order | 30–80 bytes | 60% of flow |
| Cancel Request | Cancel an existing order | 20–50 bytes | 25% of flow |
| Cancel/Replace | Modify an existing order | 40–100 bytes | 10% of flow |
| Mass Cancel | Cancel all orders for a symbol | 30–60 bytes | <1% of flow |
| Order Status | Query order status | 20–40 bytes | 4% of flow |

### 1.2 Measurement Approaches

| Method | Description | Accuracy | Use Case |
|--------|-------------|----------|----------|
| **Gateway counter** | Atomic increment at order gateway entry point | Very high | Exchange systems |
| **Matching engine counter** | Count at match engine ingress | Very high | Matching engine validation |
| **FIX session layer** | Count FIX messages (35=D, 35=F, 35=G) | High | FIX-based systems |
| **OUCH / ITCH protocol** | Count native protocol order entries | High | Proprietary protocols |
| **Binary protocol decoder** | FPGA-based order message counter | Very high | ULL FPGA systems |

### 1.3 Standard Test Configuration

```
Test Duration:     ≥ 120 seconds sustained
Warm-up:           ≥ 60 seconds (order book population, connection setup)
Load Pattern:      Realistic mix (60% new, 25% cancel, 10% replace, 5% status)
Order Book Depth:  Test at 10, 100, 1000, 10000 open orders per symbol
Symbol Count:      1, 10, 100, 1000 symbols
Price Levels:      Test at 10, 100, 1000 price levels per side
Concurrency:       1, 10, 100, 1000 simultaneous sessions
```

### 1.4 Key Formulas

```
Order throughput (ord/s) = Total order operations / Measurement window (s)

Order-to-trade ratio = Orders submitted / Trades executed
  (Typical: 2:1 to 10:1 for market making; 1:1 for aggressive takers)

Cancel ratio = Cancels / New orders
  (Typical: 0.3–0.8 for HFT; 0.01–0.1 for retail)

Order book update rate = (New orders + Cancels + Modifies) / Time window
```

---

## 2. Benchmark Standards

### 2.1 Exchange Matching Engines

| Exchange | Orders/sec | Trades/sec | Order:Trade Ratio | Source |
|---------|-----------|-----------|-------------------|--------|
| CME Globex | ~1M–5M peak | ~500K–2M | 2:1 to 3:1 | CME performance reports |
| NYSE Pillar | ~500K–2M peak | ~300K–1M | 2:1 to 3:1 | NYSE specifications |
| Nasdaq INET | ~1M–3M peak | ~500K–1.5M | 2:1 to 3:1 | Nasdaq specifications |
| Eurex T7 | ~500K–1.5M peak | ~300K–800K | 2:1 to 3:1 | Eurex documentation |
| LSE Millennium | ~200K–500K peak | ~100K–300K | 2:1 to 3:1 | LSE specifications |
| Japan Exchange (J-GATE) | ~300K–800K peak | ~200K–500K | 2:1 to 3:1 | JPX documentation |

### 2.2 FPGA-Based Trading Systems

| System | Orders/sec | Latency | Source |
|--------|-----------|---------|--------|
| IEEE 2024 FPGA study | 150,000 ord/s | 480 ns avg | IEEE publication |
| Algo-Logic CME T2T | ~500K–1M ord/s | Sub-μs wire-to-wire | Algo-Logic press release |
| CSPi ARC E-Class | ~200K–500K ord/s | 1.538 μs mean T2T | CSPi benchmark |
| Optiver quoting engine | ~100K–500K ord/s | <500 ns reaction | Optiver tech blog |
| Jump Trading FPGA | ~1M+ ord/s | 1.2 μs median RTT | Jump tech publications |

### 2.3 Software-Based Trading Systems

| Stack | Orders/sec | Latency | Source |
|-------|-----------|---------|--------|
| C++ kernel bypass (DPDK) | 100K–500K ord/s | 1–5 μs | Typical ULL C++ |
| C++ standard kernel | 10K–100K ord/s | 10–50 μs | Typical low-latency C++ |
| Java (LMAX Disruptor) | 50K–200K ord/s | 5–20 μs | LMAX documentation |
| Java (standard) | 10K–50K ord/s | 50–200 μs | Typical Java |
| Go | 20K–100K ord/s | 10–100 μs | Typical Go |
| Rust (tokio) | 50K–200K ord/s | 5–20 μs | Typical Rust async |
| Python | 1K–10K ord/s | 100–1000 μs | Typical Python |

---

## 3. Industry Averages

### 3.1 By Trading Style

| Style | Orders/sec | Cancel Ratio | Order:Trade | Notes |
|-------|-----------|-------------|-------------|-------|
| Market making (HFT) | 100K–1M | 0.5–0.8 | 3:1 to 10:1 | High cancel, rapid updates |
| Statistical arbitrage | 10K–100K | 0.2–0.5 | 2:1 to 5:1 | Moderate frequency |
| Execution algo (TWAP/VWAP) | 1K–10K | 0.05–0.2 | 1:1 to 2:1 | Patient, low cancel |
| Discretionary trading | 1–100 | 0.01–0.1 | 1:1 | Human-driven |

### 3.2 By Asset Class

| Asset Class | Orders/sec (per venue) | Peak Orders/sec | Notes |
|-------------|----------------------|-----------------|-------|
| US Equities | 500K–2M | 5M+ | Most liquid market |
| US Options | 200K–1M | 3M+ | Complex order types |
| Futures (CME) | 300K–1M | 3M+ | High leverage, fast |
| FX (EBS/Reuters) | 100K–500K | 2M+ | 24-hour market |
| Crypto (Binance) | 500K–2M | 5M+ | High retail participation |
| Fixed Income | 10K–100K | 500K | Lower frequency |

### 3.3 Scaling by Order Book Depth

```
Depth = 10 orders:    500K–1M ord/s (simple matching)
Depth = 100 orders:   200K–500K ord/s (moderate complexity)
Depth = 1000 orders:  50K–200K ord/s (complex book management)
Depth = 10000 orders: 10K–50K ord/s (deep book, cache pressure)
Depth = 100000 orders: 1K–10K ord/s (extreme depth, memory-bound)
```

---

## 4. Factors Affecting Order Throughput

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Order book data structure | O(log n) vs O(1) for insert/cancel | Use hash map + sorted array |
| Cache locality | L1/L2 miss adds 4–100 cycles | Align data to cache lines (64B) |
| Memory allocation | malloc/free adds 100ns–1μs | Object pools, arena allocators |
| Lock contention | Mutex adds 10–100μs under contention | Lock-free queues, sharded locks |
| Network I/O | Kernel stack adds 10–50μs | Kernel bypass, FPGA |
| Serialization | Protocol decode adds 1–10μs | Binary protocols, FPGA decode |
| Risk checks | Pre-trade risk adds 1–100μs | FPGA hardware risk checks |
| GC pauses | 1–100ms stalls | Native code, ZGC, Shenandoah |

---

## 5. Order Lifecycle Throughput

```
Client → Gateway → Risk Check → Matching Engine → Market Data → Client
         100K/s      50K/s         20K/s            500K/s      100K/s
         (accept)    (pass)        (match)          (broadcast) (ack)
```

**Bottleneck analysis:** The matching engine is typically the bottleneck. A system accepting 100K orders/s but only matching 20K/s will queue orders, increasing latency.

### Pipeline Throughput Formula

```
System throughput = min(gateway_rate, risk_rate, match_rate, md_rate)

End-to-end latency = Σ(stage_latencies) + queueing_delay
```

---

## 6. Measurement Tools

| Tool | Domain | Output |
|------|--------|--------|
| `exchange-mock` | Exchange simulation | Orders/sec, match rate |
| `fix-engine` | FIX protocol testing | FIX message rate |
| `dpdk-l2fwd` / `dpdk-l3fwd` | Packet forwarding | Packets/sec (upper bound) |
| Custom FPGA testbench | FPGA validation | Cycle-accurate order rate |
| `perf record` | CPU profiling | Hot path identification |
| `eBPF` / `bpftrace` | Kernel tracing | Syscall rate, scheduling |

---

## 7. Reporting Template

```yaml
metric: orders_per_second
system: <system_name>
date: <ISO 8601>
configuration:
  order_mix:
    new_order_pct: <N>
    cancel_pct: <N>
    replace_pct: <N>
    status_pct: <N>
  order_book_depth: <N>
  symbol_count: <N>
  price_levels: <N>
  sessions: <N>
  network_stack: <kernel|dpdk|rdma|fpga>
results:
  sustained_ord_s: <N>
  peak_ord_s: <N>
  p50_ord_s: <N>
  p99_ord_s: <N>
  cancel_ratio: <float>
  order_to_trade_ratio: <float>
  end_to_end_latency_us: <N>
  cpu_utilization_pct: <N>
notes: <any anomalies or observations>
```

---

*Sources: CME/NYSE/Nasdaq/Eurex exchange specifications, IEEE 2024 FPGA study, Algo-Logic/CSPi/Optiver/Jump Trading published benchmarks, LMAX Disruptor documentation.*
