# Industry Averages: Consolidated Reference

**Quick-reference tables for ULL throughput benchmarks across all domains.**

---

## 1. Messages Per Second (msg/s)

| Domain | Low-End | Mid-Range | High-End | ULL Target |
|--------|---------|-----------|----------|------------|
| HFT market data (per feed) | 500K | 2M | 10M | 100M+ |
| HFT order entry | 100K | 500K | 2M | 10M+ |
| Payment authorization | 10K | 50K | 200K | 1M+ |
| Payment clearing | 1K | 10K | 50K | 500K+ |
| Gaming state sync | 10K | 100K | 1M | 10M+ |
| IoT telemetry | 100K | 1M | 10M | 100M+ |
| Network (DPDK, per core) | 1M | 10M | 50M | 100M+ |
| Network (RDMA NDR) | 100M | 200M | 370M | 500M+ |
| FPGA feed handler | 10M | 50M | 100M | 1B+ |

---

## 2. Orders Per Second (ord/s)

| Domain | Low-End | Mid-Range | High-End | ULL Target |
|--------|---------|-----------|----------|------------|
| Exchange matching (per venue) | 200K | 500K | 2M | 5M+ |
| FPGA trading system | 100K | 500K | 1M | 5M+ |
| C++ kernel bypass | 50K | 200K | 500K | 1M+ |
| C++ standard kernel | 10K | 50K | 100K | 500K+ |
| Java (LMAX) | 50K | 100K | 200K | 500K+ |
| Java (standard) | 10K | 30K | 50K | 100K+ |
| Rust (tokio) | 50K | 100K | 200K | 500K+ |
| Go | 20K | 50K | 100K | 200K+ |
| Python | 1K | 5K | 10K | 50K+ |

---

## 3. Trades Per Second (trd/s)

| Domain | Low-End | Mid-Range | High-End | ULL Target |
|--------|---------|-----------|----------|------------|
| US equities (all venues) | 500K | 1M | 3M | 10M+ |
| US options (all venues) | 200K | 500K | 1.5M | 5M+ |
| Futures (CME) | 300K | 500K | 1.5M | 5M+ |
| Crypto (Binance) | 500K | 1M | 2M | 5M+ |
| Clearing (DTCC) | 10K | 50K | 200K | 500K+ |
| Settlement (T+2) | 1K | 5K | 10K | 50K+ |
| Blockchain (Bitcoin) | 3 | 5 | 7 | — |
| Blockchain (Ethereum) | 15 | 20 | 30 | — |
| Blockchain (Solana) | 2K | 3K | 4K | — |

---

## 4. IOPS (4K Random)

| Storage Type | Low-End | Mid-Range | High-End | ULL Target |
|-------------|---------|-----------|----------|------------|
| SATA SSD | 50K | 100K | 200K | — |
| NVMe Gen4 | 500K | 1M | 2.5M | 5M+ |
| NVMe Gen5 | 1M | 2M | 5M | 10M+ |
| Intel Optane (3D XPoint) | 1M | 1.5M | 2.5M | 5M+ |
| NVMe-oF TCP | 35K | 100K | 500K | 1M+ |
| NVMe-oF RDMA | 500K | 1M | 2M | 6M+ |
| DRAM (persistent memory) | 10M | 50M | 100M | — |
| DRAM (volatile) | 100M | 500M | 1B | — |

---

## 5. Bandwidth (Gb/s)

| Network Type | Low-End | Mid-Range | High-End | ULL Target |
|-------------|---------|-----------|----------|------------|
| Ethernet 10GbE | 10 | — | — | — |
| Ethernet 100GbE | 100 | — | — | — |
| Ethernet 400GbE | 400 | — | — | — |
| Ethernet 800GbE | 800 | — | — | — |
| InfiniBand HDR | 200 | — | — | — |
| InfiniBand NDR | 400 | — | 800 | — |
| InfiniBand XDR | 800 | — | 1600 | — |
| RoCE v2 | 100 | 200 | 400 | 800 |
| DPU (BlueField-3) | 200 | 400 | — | — |
| DPU (BlueField-4) | 400 | 800 | — | — |
| FPGA (Achronix) | 400 | 800 | — | — |
| Microwave (CHI-NY) | 1 | 5 | 10 | — |
| Fiber (CHI-NY) | 10 | 50 | 100 | — |

---

## 6. Cross-Domain Comparison

| Domain | msg/s | ord/s | trd/s | IOPS | Bandwidth |
|--------|-------|-------|-------|------|-----------|
| HFT (per firm) | 10M | 1M | 100K | 1M | 400 Gb/s |
| Payment (Visa) | 83K | — | — | — | 100 Gb/s |
| Payment (Stripe) | 10M | — | — | — | 100 Gb/s |
| Gaming (per shard) | 1M | — | — | 100K | 10 Gb/s |
| Data center (spine) | — | — | — | — | 800 Gb/s |
| AI training (per node) | — | — | — | — | 800 Gb/s |

---

## 7. Technology Stack Comparison

| Stack | msg/s | ord/s | trd/s | IOPS | Bandwidth | Latency |
|-------|-------|-------|-------|------|-----------|---------|
| FPGA (full pipeline) | 100M+ | 1M+ | 1M+ | — | 400 Gb/s | <1 μs |
| FPGA + CPU hybrid | 10M | 500K | 100K | 1M | 100 Gb/s | 1–5 μs |
| C++ kernel bypass | 10M | 500K | 100K | 1M | 100 Gb/s | 1–10 μs |
| C++ standard kernel | 500K | 100K | 50K | 500K | 10 Gb/s | 10–50 μs |
| Java (LMAX) | 1M | 200K | 100K | 500K | 10 Gb/s | 5–20 μs |
| Java (standard) | 100K | 50K | 25K | 100K | 1 Gb/s | 50–200 μs |
| Rust (tokio) | 1M | 200K | 100K | 500K | 10 Gb/s | 5–20 μs |
| Go | 500K | 100K | 50K | 200K | 1 Gb/s | 10–100 μs |
| Python | 10K | 5K | 1K | 50K | 1 Gb/s | 100–1000 μs |

---

## 8. Scaling Reference

### 8.1 By Connection Count

| Connections | msg/s | ord/s | trd/s | IOPS | Bandwidth |
|-------------|-------|-------|-------|------|-----------|
| 1 | 100K | 50K | 10K | 100K | 1 Gb/s |
| 10 | 500K | 200K | 50K | 500K | 5 Gb/s |
| 100 | 2M | 500K | 100K | 1M | 10 Gb/s |
| 1K | 5M | 1M | 200K | 2M | 50 Gb/s |
| 10K | 10M | 2M | 500K | 5M | 100 Gb/s |
| 100K | 50M | 5M | 1M | 10M | 400 Gb/s |
| 1M | 100M | 10M | 2M | 20M | 800 Gb/s |

### 8.2 By CPU Cores

| Cores | msg/s | ord/s | trd/s | IOPS | Bandwidth |
|-------|-------|-------|-------|------|-----------|
| 1 | 1M | 100K | 20K | 100K | 10 Gb/s |
| 4 | 4M | 400K | 80K | 400K | 40 Gb/s |
| 8 | 8M | 800K | 160K | 800K | 80 Gb/s |
| 16 | 16M | 1.5M | 300K | 1.5M | 100 Gb/s |
| 32 | 32M | 3M | 600K | 3M | 200 Gb/s |
| 64 | 64M | 6M | 1.2M | 6M | 400 Gb/s |
| 128 | 128M | 12M | 2.4M | 12M | 800 Gb/s |

---

## 9. Cost Efficiency

| Metric | $/msg/s | $/ord/s | $/trd/s | $/IOPS | $/Gb/s |
|--------|---------|---------|---------|--------|--------|
| FPGA | $0.01–0.10 | $0.10–1.00 | $1.00–10.00 | $0.001–0.01 | $10–100 |
| C++ kernel bypass | $0.001–0.01 | $0.01–0.10 | $0.10–1.00 | $0.0001–0.001 | $1–10 |
| C++ standard kernel | $0.0001–0.001 | $0.001–0.01 | $0.01–0.10 | $0.00001–0.0001 | $0.10–1.00 |
| Java (LMAX) | $0.001–0.01 | $0.01–0.10 | $0.10–1.00 | $0.0001–0.001 | $1–10 |
| Java (standard) | $0.0001–0.001 | $0.001–0.01 | $0.01–0.10 | $0.00001–0.0001 | $0.10–1.00 |
| Rust (tokio) | $0.001–0.01 | $0.01–0.10 | $0.10–1.00 | $0.0001–0.001 | $1–10 |
| Go | $0.0001–0.001 | $0.001–0.01 | $0.01–0.10 | $0.00001–0.0001 | $0.10–1.00 |
| Python | $0.00001–0.0001 | $0.0001–0.001 | $0.001–0.01 | $0.000001–0.00001 | $0.01–0.10 |

---

## 10. ULL Targets Summary

| Metric | Good | Better | Best | State-of-the-Art |
|--------|------|--------|------|-----------------|
| msg/s | 1M | 10M | 100M | 1B+ |
| ord/s | 100K | 500K | 1M | 10M+ |
| trd/s | 50K | 200K | 500K | 5M+ |
| IOPS (4K) | 1M | 5M | 10M | 100M+ |
| Bandwidth | 100 Gb/s | 400 Gb/s | 800 Gb/s | 1.6 Tb/s+ |
| Latency (p99) | <100 μs | <10 μs | <1 μs | <100 ns |

---

*Sources: CME/NYSE/Nasdaq/Eurex exchange specifications, NVIDIA/AMD/Intel product briefs, IEEE 2024 FPGA study, Visa/Stripe corporate disclosures, SPDK performance reports, Bitcoin/Ethereum/Solana protocol specifications.*
