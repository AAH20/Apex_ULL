# ULL Throughput Evaluation Framework

**Date:** 2026-09-29  
**Scope:** Ultra-low-latency infrastructure throughput benchmarks across HFT, payments, gaming, and data center domains

---

## Overview

This framework defines measurement methodology, benchmark standards, and industry averages for five core throughput dimensions in ultra-low-latency (ULL) systems:

| # | Metric | Unit | Primary Domains |
|---|--------|------|-----------------|
| 1 | Messages/sec | msg/s | HFT market data, order routing, payment auth |
| 2 | Orders/sec | ord/s | Exchange matching engines, trading systems |
| 3 | Trades/sec | trd/s | Settlement, clearing, trade reporting |
| 4 | IOPS | IOPS | Storage, NVMe-oF, database, logging |
| 5 | Bandwidth | Gb/s | Network fabric, interconnect, WAN |

---

## File Index

| File | Content |
|------|---------|
| [messages-per-second.md](messages-per-second.md) | Market data, order flow, payment message throughput |
| [orders-per-second.md](orders-per-second.md) | Exchange matching engine and trading system order throughput |
| [trades-per-second.md](trades-per-second.md) | Trade execution, settlement, and clearing throughput |
| [iops.md](iops.md) | Storage I/O operations per second benchmarks |
| [bandwidth.md](bandwidth.md) | Network bandwidth and interconnect throughput |
| [methodology.md](methodology.md) | Cross-cutting measurement methodology and best practices |
| [industry-averages.md](industry-averages.md) | Consolidated industry average reference tables |

---

## Key Principles

1. **Measure at the bottleneck** — throughput is only as high as the slowest component in the pipeline
2. **Report sustained, not peak** — peak numbers are marketing; sustained numbers are engineering
3. **Include jitter and tail latency** — throughput without latency context is meaningless for ULL
4. **Normalize by message size** — always report bytes/op alongside ops/sec
5. **Test under contention** — idle-system throughput is not representative

---

## Quick Reference: Industry Throughput Ranges

| Metric | Low-End | Mid-Range | High-End | ULL Target |
|--------|---------|-----------|----------|------------|
| Messages/sec | 100K | 1M | 100M+ | 1B+ |
| Orders/sec | 10K | 100K | 1M+ | 10M+ |
| Trades/sec | 1K | 50K | 500K+ | 5M+ |
| IOPS (4K random) | 100K | 1M | 10M+ | 100M+ |
| Bandwidth | 10 Gb/s | 100 Gb/s | 400 Gb/s | 800 Gb/s+ |

---

*See individual metric files for detailed methodology, benchmarks, and industry data.*
