# ULL Security Benchmarks

**Date:** 2026-09-29  
**Scope:** Security overhead benchmarks for ultra-low-latency trading infrastructure

---

## Overview

This directory contains benchmarks for measuring the latency overhead of security mechanisms in ultra-low-latency (ULL) trading infrastructure. Each benchmark covers measurement methodology, hardware requirements, software requirements, and expected baseline results.

## Benchmarks

| Benchmark | Target Overhead | Document |
|---|---|---|
| **Encryption Overhead** | <500 ns per packet (fast path) | [encryption-overhead.md](./encryption-overhead.md) |
| **Authentication Overhead** | <500 ns per message (fast path) | [authentication-overhead.md](./authentication-overhead.md) |
| **Authorization Overhead** | <200 ns per request (fast path) | [authorization-overhead.md](./authorization-overhead.md) |
| **Audit Overhead** | <500 ns per event (async) | [audit-overhead.md](./audit-overhead.md) |

## Summary Table

| Security Function | Fast-Path Mechanism | Expected p50 | Expected p99 | ULL Suitability |
|---|---|---|---|---|
| Encryption | AES-128-GCM (AES-NI) | 180 ns | 250 ns | ✅ Excellent |
| Encryption | MACsec offload | 50 ns | 100 ns | ✅ Excellent |
| Encryption | FPGA AES-256-GCM | 50 ns | 80 ns | ✅ Excellent |
| Authentication | HMAC-SHA-256 (SHA-NI) | 80 ns | 120 ns | ✅ Excellent |
| Authentication | JWT-HS256 verify | 150 ns | 220 ns | ✅ Excellent |
| Authorization | Static ACL (bitmap) | 15 ns | 25 ns | ✅ Excellent |
| Authorization | RBAC (in-memory) | 80 ns | 150 ns | ✅ Excellent |
| Audit | In-memory buffer (async) | 30 ns | 60 ns | ✅ Excellent |
| Audit | Lock-free ring buffer | 80 ns | 150 ns | ✅ Excellent |

## Key Principles

1. **Use symmetric mechanisms on the fast path** — asymmetric crypto is 100–1000× slower
2. **Pre-establish sessions** — amortize handshake cost over many messages
3. **Use hardware offload** — AES-NI, SHA-NI, QAT, FPGA for sub-100 ns overhead
4. **Use asynchronous audit** — synchronous audit adds 10–100 μs per event
5. **Cache authorization decisions** — TTL-based caching for repeated requests
6. **Use simple authorization mechanisms** — ACL/RBAC over OPA/Rego on the fast path

## Measurement Methodology

All benchmarks use:
- **`rdtsc` / `rdtscp`** for sub-μs timing (invariant TSC, ~0.3 ns resolution)
- **Hardware timestamping** (Intel I210-AT or NIC with PTP) for wire-level verification
- **Percentile reporting** (p50, p99, p99.9, p99.99, max) for latency distribution
- **100,000 iterations** per measurement point for statistical significance

## Hardware Platform

| Component | Specification |
|---|---|
| CPU | Intel Xeon 8490H (Sapphire Rapids) |
| NIC | Nvidia BlueField-3 DPU |
| FPGA | Xilinx Alveo U25 / Versal AI Edge |
| NVMe SSD | Intel Optane P5800X |
| Timing | Intel I210-AT (hardware timestamping) |

## Software Platform

| Component | Version |
|---|---|
| OS | Ubuntu 24.04 LTS |
| Kernel | 6.8+ |
| OpenSSL | 3.2+ |
| DPDK | 24.07+ |
| OPA | 0.68+ |

## References

See individual benchmark documents for detailed references.
