# Trades Per Second (trd/s)

**Definition:** The number of executed trades (fills) processed per second by a trading system, exchange, or clearing system. A trade represents a completed transaction between two parties.

---

## 1. Measurement Methodology

### 1.1 Trade vs. Order vs. Message

| Concept | Definition | Relationship |
|---------|-----------|--------------|
| **Message** | Any data unit in the system | 1 order → 1+ messages |
| **Order** | Instruction to buy/sell | 1 order → 0 or 1+ trades |
| **Trade** | Executed transaction | 1 trade = 2 sides (buy + sell) |

```
Order-to-Trade Ratio = Orders submitted / Trades executed
  Market making:  3:1 to 10:1 (many orders, few fills)
  Aggressive:     1:1 (marketable orders fill immediately)
  Execution algo: 1:1 to 2:1 (patient execution)
```

### 1.2 Measurement Approaches

| Method | Description | Accuracy | Use Case |
|--------|-------------|----------|----------|
| **Matching engine fill counter** | Atomic increment on each match | Very high | Exchange systems |
| **Trade reporting system** | Count trade reports (FIX 35=8, FIX 35=AE) | High | Post-trade systems |
| **Clearing system entry** | Count clearing instructions | High | Clearing houses |
| **Blockchain/ledger** | Count committed transactions | Very high | Crypto/DeFi |
| **Trade tape parser** | Parse consolidated tape (CTS/UTP) | High | Market data analysis |

### 1.3 Standard Test Configuration

```
Test Duration:     ≥ 120 seconds sustained
Warm-up:           ≥ 60 seconds (order book population)
Load Pattern:      Realistic mix of market orders, limit orders, IOC, FOK
Trade Sizes:       Test at 1, 10, 100, 1000, 10000 shares/contracts
Price Distribution: Uniform, normal, and fat-tailed price distributions
Concurrency:       1, 10, 100, 1000 simultaneous trading sessions
Symbol Count:      1, 10, 100, 1000 symbols
```

### 1.4 Key Formulas

```
Trade throughput (trd/s) = Total trades executed / Measurement window (s)

Trade rate per symbol = Total trades / Active symbols / Time window

Average trade size = Total volume traded / Total trades executed

Notional throughput = Trade throughput × Average trade size × Price
  (reported in $/s or notional currency/s)

Fill rate = Trades executed / Orders submitted × 100%
```

---

## 2. Benchmark Standards

### 2.1 Exchange Trade Throughput

| Exchange | Trades/sec (sustained) | Trades/sec (peak) | Avg Trade Size | Source |
|---------|----------------------|-------------------|----------------|--------|
| CME Globex | 500K–1M | 2M+ | 5–50 contracts | CME reports |
| NYSE (all venues) | 300K–800K | 2M+ | 100–500 shares | NYSE reports |
| Nasdaq (all venues) | 500K–1.5M | 3M+ | 100–500 shares | Nasdaq reports |
| CBOE (all venues) | 200K–500K | 1.5M+ | 1–10 contracts | CBOE reports |
| Eurex | 300K–800K | 2M+ | 1–20 contracts | Eurex reports |
| LSE | 100K–300K | 1M+ | 100–1000 shares | LSE reports |
| Binance (crypto) | 500K–2M | 5M+ | Varies | Binance reports |
| OKX (crypto) | 200K–1M | 3M+ | Varies | OKX reports |

### 2.2 Clearing & Settlement Systems

| System | Trades/sec | Latency | Source |
|--------|-----------|---------|--------|
| DTCC (US equities) | ~50K–200K | Minutes (batch) | DTCC reports |
| OCC (US options) | ~20K–100K | Minutes (batch) | OCC reports |
| CLS (FX settlement) | ~10K–50K | Minutes (batch) | CLS reports |
| Euroclear | ~5K–20K | Minutes (batch) | Euroclear reports |
| Blockchain (Bitcoin) | ~3–7 trd/s | 10 min (block) | Bitcoin protocol |
| Blockchain (Ethereum) | ~15–30 trd/s | 12 sec (block) | Ethereum protocol |
| Blockchain (Solana) | ~2K–4K trd/s | 400 ms (block) | Solana reports |

### 2.3 Trading Firm Internal Systems

| Firm Type | Trades/sec | Notes | Source |
|-----------|-----------|-------|--------|
| HFT market maker | 10K–100K | Per firm, all venues | Industry estimates |
| Prop trading firm | 1K–10K | Per firm | Industry estimates |
| Institutional broker | 100–1K | Per firm | Industry estimates |
| Retail broker | 10–100 | Per firm | Industry estimates |

---

## 3. Industry Averages

### 3.1 By Market Session

| Session | Trades/sec (US equities) | Trades/sec (US options) | Notes |
|---------|------------------------|------------------------|-------|
| Pre-market (4:00–9:30 AM) | 10K–50K | 5K–20K | Lower volume |
| Opening cross (9:30–10:00 AM) | 200K–500K | 100K–300K | High volume |
| Regular (10:00–3:30 PM) | 100K–300K | 50K–150K | Steady state |
| Closing cross (3:30–4:00 PM) | 300K–800K | 150K–400K | High volume |
| After-hours (4:00–8:00 PM) | 5K–20K | 2K–10K | Lower volume |

### 3.2 By Asset Class

| Asset Class | Trades/sec (global) | Peak Trades/sec | Notes |
|-------------|-------------------|-----------------|-------|
| US Equities | 1M–3M | 10M+ | Most active market |
| US Options | 500K–1.5M | 5M+ | High contract count |
| Futures (CME) | 500K–1.5M | 5M+ | Concentrated in few products |
| FX Spot | 200K–500M | 2M+ | Decentralized, OTC |
| Crypto | 1M–5M | 20M+ | 24/7, global |
| Fixed Income | 10K–50K | 200K | Lower frequency |
| Commodities | 50K–200K | 1M+ | Seasonal variation |

### 3.3 By Technology Stack

| Stack | Trades/sec | Latency | Source |
|-------|-----------|---------|--------|
| FPGA matching engine | 1M–10M+ | <1 μs | IEEE 2024, Algo-Logic |
| C++ kernel bypass | 100K–1M | 1–10 μs | Typical ULL C++ |
| C++ standard kernel | 10K–100K | 10–50 μs | Typical low-latency C++ |
| Java (LMAX) | 50K–200K | 5–20 μs | LMAX documentation |
| Java (standard) | 10K–50K | 50–200 μs | Typical Java |
| Rust (tokio) | 50K–200K | 5–20 μs | Typical Rust async |
| Go | 20K–100K | 10–100 μs | Typical Go |
| Python | 1K–10K | 100–1000 μs | Typical Python |

---

## 4. Trade Lifecycle Throughput

```
Order Entry → Risk Check → Matching → Trade Report → Clearing → Settlement
  100K/s        50K/s       20K/s     20K/s          10K/s     1K/s
  (accept)      (pass)      (match)   (report)       (net)     (settle)
```

### Pipeline Bottleneck Analysis

```
System trade throughput = min(
  order_entry_rate,
  risk_check_rate,
  matching_rate,
  trade_report_rate,
  clearing_rate,
  settlement_rate
)
```

**Typical bottleneck:** Matching engine (20K/s) and clearing (10K/s) are the most common bottlenecks.

### Trade Processing Stages

| Stage | Typical Latency | Typical Throughput | Bottleneck Risk |
|-------|----------------|-------------------|-----------------|
| Order entry | 1–10 μs | 100K–1M/s | Low |
| Risk check | 1–100 μs | 50K–500K/s | Medium |
| Matching | 0.1–10 μs | 1M–10M/s | Low (FPGA) |
| Trade report | 1–10 μs | 100K–1M/s | Low |
| Clearing | 1 ms–1 min | 1K–100K/s | High (batch) |
| Settlement | 1 min–2 days | 100–10K/s | Very high (batch) |

---

## 5. Factors Affecting Trade Throughput

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Matching algorithm complexity | O(n) vs O(log n) per match | Use efficient data structures |
| Order book depth | Deeper books → slower matching | Optimize for common case |
| Trade reporting overhead | Serialization + network I/O | Batch reports, FPGA encoding |
| Clearing netting | Bilateral vs multilateral netting | Real-time gross settlement |
| Settlement batching | T+0 vs T+1 vs T+2 | Real-time settlement (RTGS) |
| Regulatory reporting | MiFID II, CAT, etc. | Automated reporting pipelines |
| Market volatility | Higher volatility → more trades | Auto-scaling infrastructure |

---

## 6. Measurement Tools

| Tool | Domain | Output |
|------|--------|--------|
| `exchange-mock` | Exchange simulation | Trades/sec, fill rate |
| `fix-engine` | FIX protocol testing | FIX execution report rate |
| `dpdk-l2fwd` | Packet forwarding | Packets/sec (upper bound) |
| Custom FPGA testbench | FPGA validation | Cycle-accurate trade rate |
| `perf record` | CPU profiling | Hot path identification |
| Blockchain explorers | Crypto | On-chain transaction rate |

---

## 7. Reporting Template

```yaml
metric: trades_per_second
system: <system_name>
date: <ISO 8601>
configuration:
  asset_class: <equities|options|futures|fx|crypto|...>
  trade_size_distribution: <uniform|normal|fat-tailed>
  order_book_depth: <N>
  symbol_count: <N>
  sessions: <N>
  network_stack: <kernel|dpdk|rdma|fpga>
results:
  sustained_trd_s: <N>
  peak_trd_s: <N>
  p50_trd_s: <N>
  p99_trd_s: <N>
  avg_trade_size: <N>
  notional_per_second: <N>
  fill_rate_pct: <N>
  end_to_end_latency_us: <N>
  cpu_utilization_pct: <N>
notes: <any anomalies or observations>
```

---

*Sources: CME/NYSE/Nasdaq/CBOE/Eurex exchange reports, DTCC/OCC/CLS clearing reports, IEEE 2024 FPGA study, Algo-Logic/CSPi published benchmarks, Bitcoin/Ethereum/Solana protocol specifications.*
