# ULL Determinism Benchmarks

**Project:** ultra-low-latency-infra  
**Date:** 2026-09-29  
**Scope:** Latency determinism metrics for ultra-low-latency infrastructure

---

## Overview

Determinism — the consistency and predictability of latency — is as critical as raw latency in ULL systems. A system with 200 ns average but 50 µs tail latency is often worse than one with 500 ns average and 600 ns tail. These benchmarks quantify determinism across four complementary metrics.

## Metrics

| # | Metric | What It Measures | Ideal Value |
|---|--------|------------------|-------------|
| 1 | [Coefficient of Variation (CV)](01-coefficient-of-variation.md) | Relative spread of latency distribution | → 0 |
| 2 | [p99/p50 Ratio](02-p99-p50-ratio.md) | Tail-to-median latency ratio | → 1.0 |
| 3 | [Max Latency](03-max-latency.md) | Worst-case single-sample latency | Minimize |
| 4 | [Jitter Standard Deviation](04-jitter-std-dev.md) | Consecutive-sample variability | → 0 |

## Quick Reference: Target Determinism by Deployment Tier

| Tier | CV | p99/p50 | Max Latency | Jitter σ |
|------|-----|---------|-------------|----------|
| Full FPGA tick-to-trade | < 0.01 | < 1.5 | < 1 µs | < 10 ns |
| FPGA feed handler + CPU strategy | < 0.05 | < 2.0 | < 5 µs | < 50 ns |
| Kernel bypass (DPDK/Onload) | < 0.10 | < 3.0 | < 20 µs | < 200 ns |
| Standard kernel stack | < 0.30 | < 10.0 | < 100 µs | < 1 µs |

## Measurement Principles

1. **Warm-up:** Discard first 10,000 samples (cache/TLB warm-up, frequency scaling stabilization)
2. **Isolation:** Disable hyperthreading, pin to isolated cores, disable IRQ affinity on measurement cores
3. **Duration:** Minimum 10 million samples or 60 seconds of continuous measurement (whichever is longer)
4. **Clock source:** Use `CLOCK_MONOTONIC_RAW` (TSC-based, NTP-independent) or `rdtsc` directly
5. **Record raw samples:** Never pre-aggregate; compute all percentiles from the full sample set
6. **Repeat:** Run 3+ passes; report median-of-passes for each metric

## Hardware Requirements (Common)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Intel Xeon Scalable (isolated cores) | AMD EPYC 9004 or Intel Xeon 6 |
| Clock | Invariant TSC | Invariant TSC + `tsc=reliable` kernel param |
| NIC | FPGA-based (e.g., Alveo, PAC) | Purpose-built ULL NIC (e.g., Exablaze, Metamako) |
| Memory | DDR4-3200, pinned pages | DDR5-4800, 1 GB hugepages |
| Motherboard | Isolated PCIe root complex | Dedicated PCIe slot, no shared root complex |
| Power | Performance governor, C-states disabled | BIOS-level C-state disable, locked frequency |

## Software Requirements (Common)

| Layer | Requirement |
|-------|-------------|
| Kernel | `isolcpus`, `nohz_full`, `rcu_nocbs`, `intel_pstate=disable` or `amd_pstate=disable` |
| Scheduler | `SCHED_FIFO` or `SCHED_DEADLINE` for measurement thread |
| Interrupts | IRQs excluded from measurement cores (`/proc/irq/default_smp_affinity`) |
| Memory | `mlockall(MCL_CURRENT \| MCL_FUTURE)`, pre-faulted stack |
| Clock | `CLOCK_MONOTONIC_RAW` via `clock_gettime()` or inline `rdtsc` |
| Compiler | `-O3 -march=native`, no LTO for measurement hot path |

## File Structure

```
benchmarks/determinism/
├── README.md                          ← This file
├── 01-coefficient-of-variation.md     ← CV benchmark
├── 02-p99-p50-ratio.md                ← p99/p50 ratio benchmark
├── 03-max-latency.md                  ← Max latency benchmark
├── 04-jitter-std-dev.md               ← Jitter σ benchmark
└── common/
    ├── measurement-methodology.md     ← Shared methodology details
    └── reference-implementation/      ← C/Python reference code
```

## References

- [HFT Firms Research Report](../../reports/hft-firms.md) — §1 "Tick-to-Trade Latency Hierarchy"
- [Network Technologies Report](../../reports/network-technologies.md) — §4 "Kernel Bypass"
- [FPGA Technologies Report](../../reports/fpga-technologies.md) — §3 "Latency Benchmarks"
