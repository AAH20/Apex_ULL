# ULL Security Benchmark: Encryption Overhead

**Date:** 2026-09-29  
**Scope:** Wire-to-wire encryption latency in ultra-low-latency trading infrastructure  
**Target:** Sub-μs overhead on the fast path; <10 μs on session setup

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Measurement Methodology](#measurement-methodology)
3. [Hardware Requirements](#hardware-requirements)
4. [Software Requirements](#software-requirements)
5. [Benchmark Scenarios](#benchmark-scenarios)
6. [Expected Results & Baselines](#expected-results--baselines)
7. [Optimization Strategies](#optimization-strategies)
8. [References](#references)

---

## Executive Summary

| Algorithm / Mode | Per-Packet Overhead | Hardware Acceleration | ULL Suitability |
|---|---|---|---|
| AES-256-GCM | 200–500 ns | AES-NI, QAT, FPGA | ✅ Excellent |
| ChaCha20-Poly1305 | 300–700 ns | AVX-512, ARMv8 crypto | ✅ Excellent |
| AES-128-GCM | 150–400 ns | AES-NI, QAT, FPGA | ✅ Excellent |
| MACsec (802.1AE) | 50–150 ns | MACsec offload NIC | ✅ Excellent |
| IPsec (ESP tunnel) | 500 ns – 2 μs | QAT, FPGA, SmartNIC | ⚠️ Moderate |
| TLS 1.3 (1-RTT) | 5–20 μs (handshake) | TLS offload NIC | ⚠️ Session setup only |
| TLS 1.3 (0-RTT resumption) | 1–3 μs | TLS offload NIC | ✅ Good |
| Kyber-1024 (PQ KEM) | 50–200 μs | FPGA, ASIC | ❌ Not for fast path |
| Dilithium-5 (PQ sign) | 100–500 μs | FPGA, ASIC | ❌ Not for fast path |

---

## Measurement Methodology

### 1. Per-Packet Encryption Overhead

**Objective:** Measure the incremental latency added by encrypting/decrypting each packet on the data path.

**Setup:**
- Generate synthetic market-data packets (64–256 bytes, matching FIX/FAST/ITCH sizes)
- Measure baseline (plaintext) round-trip latency
- Measure encrypted round-trip latency with each algorithm
- Compute delta = encrypted − plaintext

**Procedure:**
```
For each algorithm in [AES-128-GCM, AES-256-GCM, ChaCha20-Poly1305]:
  For each packet_size in [64, 128, 256, 512, 1024]:
    For each iteration in [1..100000]:
      t0 = rdtsc()
      ciphertext = encrypt(plaintext, key, nonce)
      t1 = rdtsc()
      record(t1 - t0)
  Report: p50, p99, p99.9, p99.99, max
```

**Key metrics:**
- **p50/p99/p99.9 latency** (ns)
- **Throughput** (Mpps) at target latency ceiling
- **Jitter** (σ of latency distribution)
- **CPU utilization** per core during encryption

**Timing source:** `rdtsc` / `rdtscp` (invariant TSC, ~0.3 ns resolution on modern x86)

### 2. Handshake / Key-Exchange Overhead

**Objective:** Measure session establishment latency for TLS 1.3 and custom key-exchange protocols.

**Scenarios:**
- Full TLS 1.3 handshake (1-RTT, ECDHE P-256)
- TLS 1.3 with pre-shared key (0-RTT resumption)
- TLS 1.3 with post-quantum key exchange (X25519 + Kyber-1024 hybrid)
- Custom UDP-based key exchange (e.g., WireGuard-style)
- MACsec SAK establishment (802.1X with MKA)

**Procedure:**
```
For each handshake_type:
  For each iteration in [1..10000]:
    t0 = rdtsc()
    session = establish_session(handshake_type)
    t1 = rdtsc()
    record(t1 - t0)
  Report: p50, p99, max
```

### 3. Wire-to-Wire Encryption Overhead (End-to-End)

**Objective:** Measure the total added latency across a network path with encryption at each hop.

**Topology:**
```
[Sender] → [MACsec NIC] → [Switch] → [MACsec NIC] → [Receiver]
[Sender] → [IPsec Gateway] → [IPsec Gateway] → [Receiver]
[Sender] → [TLS Proxy] → [TLS Proxy] → [Receiver]
```

**Measurement points:**
- NIC wire timestamp (hardware timestamping, PTP-synchronized)
- Pre-encryption timestamp
- Post-decryption timestamp
- End-to-end application-visible latency

### 4. FPGA-Based Encryption Benchmark

**Objective:** Measure encryption latency when offloaded to FPGA.

**Setup:**
- FPGA bitstream implementing AES-256-GCM at line rate
- Measure: wire-in → wire-out latency through FPGA crypto pipeline
- Compare with software AES-NI baseline

---

## Hardware Requirements

### Minimum Viable

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon Scalable (Ice Lake+) or AMD EPYC (Genoa+) with AES-NI, VAES, VPCLMULQDQ | Software crypto baseline |
| NIC | Mellanox ConnectX-6 Dx (or equivalent) with MACsec/IPsec offload | Hardware crypto offload |
| FPGA | Xilinx Alveo U25 or Intel Stratix 10 (for FPGA crypto path) | Sub-100ns crypto |
| Switch | MACsec-capable L2 switch (e.g., Arista 7050X) | Wire-rate MACsec |
| Timing | Intel I210-AT (hardware timestamping) or NIC with PTP | Sub-μs measurement |

### Recommended for Full Benchmark Suite

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon 8490H (Sapphire Rapids) with QAT | QAT-accelerated crypto |
| QAT Card | Intel QAT 8970 (400 Gb/s crypto throughput) | IPsec/TLS offload |
| NIC | Nvidia BlueField-3 DPU | Full protocol offload |
| FPGA | Xilinx Versal AI Edge / Alveo U55C | Custom crypto pipeline |
| Oscilloscope | Keysight UXR0592A (59 GHz) + time-domain reflectometer | Sub-ns wire latency |
| PTP Grandmaster | Meinberg LANTIME M1000 | <100 ns clock synchronization |

### FPGA Crypto Pipeline Requirements

| Resource | AES-256-GCM @ 100 Gb/s | Notes |
|---|---|---|
| LUTs | ~15,000–25,000 | Pipeline stages |
| FFs | ~10,000–20,000 | Key schedule + state |
| BRAM | ~50–100 KB | Key/IV lookup |
| DSP | 0 | AES uses LUTs, not DSPs |
| Throughput | 100 Gb/s (single core) | ~148.8 Mpps |
| Latency | 50–100 ns | Wire-to-wire |

---

## Software Requirements

### Operating System

| OS | Version | Kernel | Notes |
|---|---|---|---|
| Ubuntu LTS | 24.04 | 6.8+ (PREEMPT_RT optional) | Primary benchmark platform |
| RHEL | 9.3+ | 5.14+ | Enterprise deployment target |
| Custom RT kernel | 6.6+ | PREEMPT_RT patch | For jitter-sensitive measurements |

### Crypto Libraries

| Library | Version | Algorithms | Use Case |
|---|---|---|---|
| OpenSSL | 3.2+ | AES-GCM, ChaCha20, TLS 1.3 | Baseline TLS benchmark |
| BoringSSL | latest | AES-GCM, ChaCha20, TLS 1.3 | Google-optimized TLS |
| wolfSSL | 5.7+ | AES-GCM, ChaCha20, TLS 1.3 | Embedded/FPGA-friendly |
| Intel IPP Crypto | 2021+ | AES-GCM, RSA, ECDSA | Intel-optimized primitives |
| Linux kernel crypto API | 6.8+ | AF_ALG (AES-GCM, ChaCha20) | Kernel-bypass crypto |
| DPDK cryptodev | 24.07+ | AES-GCM, ChaCha20 | Kernel-bypass data path |

### Benchmark Tools

| Tool | Purpose |
|---|---|
| `openssl speed` | Primitive crypto throughput |
| `openssl s_time` | TLS handshake latency |
| `iperf3 -Z` | TLS-encrypted throughput |
| `dpdk-crypto-perf` | DPDK crypto benchmark |
| `pktgen-dpdk` | Packet generation with crypto |
| Custom `rdtsc` harness | Sub-μs per-packet measurement |
| `wireshark` + hardware timestamps | Wire-level verification |

### FPGA Toolchain

| Tool | Version | Purpose |
|---|---|---|
| Xilinx Vivado | 2024.1+ | FPGA synthesis and bitstream |
| Intel Quartus Prime | 23.1+ | Intel FPGA alternative |
| P4 Compiler | p4c | Programmable switch crypto |

---

## Benchmark Scenarios

### Scenario A: Software AES-NI Baseline

```c
// Pseudocode for per-packet AES-256-GCM measurement
void benchmark_aes_gcm(void) {
    uint8_t key[32], iv[12], aad[16];
    uint8_t plaintext[256], ciphertext[300], tag[16];
    
    for (int i = 0; i < ITERATIONS; i++) {
        uint64_t t0 = __rdtsc();
        AES_GCM_encrypt(key, iv, plaintext, sizeof(plaintext),
                        aad, sizeof(aad), ciphertext, tag);
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 200–500 ns per 256-byte packet on modern x86 with AES-NI

### Scenario B: QAT-Accelerated IPsec

```bash
# Configure QAT for IPsec offload
qat_service start
ip link add ipsec0 type xfrm dev eth0 offload dev qat
# Measure with pktgen
./pktgen -l 0-3 -n 4 -- -P -m "[1:2].0" -f ipsec_benchmark.lua
```

**Expected:** 500 ns – 2 μs per packet, 400 Gb/s aggregate throughput

### Scenario C: FPGA Wire-to-Wire

```
[Generator] → [FPGA: AES-256-GCM encrypt] → [FPGA: AES-256-GCM decrypt] → [Analyzer]
                    ↑ 50-100 ns                          ↑ 50-100 ns
```

**Expected:** 100–200 ns total crypto overhead (encrypt + decrypt)

### Scenario D: TLS 1.3 Handshake

```bash
# Server
openssl s_server -accept 443 -tls1_3 -cert server.pem -key server.key -www

# Client (measure handshake time)
for i in $(seq 1 10000); do
    /usr/bin/time -f "%e" openssl s_client -connect localhost:443 -tls1_3 -brief
done
```

**Expected:** 5–20 μs for full handshake, 1–3 μs for 0-RTT resumption

---

## Expected Results & Baselines

### Software Crypto (per 256-byte packet, Intel Sapphire Rapids)

| Algorithm | p50 (ns) | p99 (ns) | p99.9 (ns) | Throughput (Mpps) |
|---|---|---|---|---|
| AES-128-GCM | 180 | 250 | 400 | ~5.5 |
| AES-256-GCM | 220 | 300 | 500 | ~4.5 |
| ChaCha20-Poly1305 | 350 | 500 | 800 | ~2.8 |
| AES-128-GCM (VAES-512) | 90 | 130 | 200 | ~11 |
| AES-256-GCM (VAES-512) | 110 | 160 | 250 | ~9 |

### Hardware Crypto (per 256-byte packet)

| Platform | p50 (ns) | p99 (ns) | Throughput (Mpps) |
|---|---|---|---|
| MACsec offload NIC | 50 | 100 | ~20 |
| QAT IPsec offload | 500 | 1000 | ~2 (per core) |
| FPGA (Alveo U25) | 50 | 80 | ~20 |
| FPGA (Versal AI Edge) | 30 | 50 | ~33 |

### TLS 1.3 Handshake Latency

| Scenario | p50 (μs) | p99 (μs) | Notes |
|---|---|---|---|
| Full handshake (P-256) | 8 | 15 | Software, no offload |
| Full handshake (P-256, QAT) | 5 | 10 | QAT offload |
| 0-RTT resumption | 1.5 | 3 | Software |
| 0-RTT resumption (QAT) | 0.8 | 1.5 | QAT offload |
| Hybrid PQ (X25519+Kyber) | 120 | 250 | Software, not ULL-suitable |

---

## Optimization Strategies

### 1. Algorithm Selection
- **Use AES-128-GCM over AES-256-GCM** when regulatory requirements permit — ~20% faster
- **Use ChaCha20-Poly1305** on platforms without AES-NI (ARM, RISC-V)
- **Avoid post-quantum algorithms on the fast path** — use them only for initial key exchange

### 2. Hardware Offload
- **MACsec for L2 encryption** — lowest overhead, wire-rate on modern switches
- **QAT for IPsec/TLS** — best for L3/L4 encryption with session management
- **FPGA for custom protocols** — lowest latency, highest flexibility

### 3. Session Management
- **Pre-establish sessions** — amortize handshake cost over many packets
- **Use 0-RTT resumption** — skip full handshake on reconnect
- **Session tickets** — stateless server-side resumption

### 4. Kernel Bypass
- **DPDK cryptodev** — avoid kernel context switches
- **AF_ALG with no_copy** — zero-copy kernel crypto
- **io_uring with fixed buffers** — reduced syscall overhead

### 5. FPGA Pipeline Optimization
- **Pipeline AES rounds** — 10-stage pipeline for 100+ Gb/s
- **Inline key schedule** — pre-compute round keys, store in BRAM
- **Batched authentication** — amortize GHASH across packets

---

## References

1. Intel. *Intel QuickAssist Technology (QAT) Developer Guide*, 2025.
2. Nvidia. *BlueField-3 DPU Architecture and Performance*, 2024.
3. Xilinx. *Alveo U25N Data Center Accelerator Card*, 2024.
4. Cloudflare. *Post-quantum TLS performance*, 2024.
5. IEEE. *FPGA-Based AES-GCM Implementation for 100GbE*, 2024.
6. IETF. *RFC 8446: TLS 1.3*, 2018.
7. NIST. *FIPS 197: Advanced Encryption Standard*, 2001.
8. DPDK. *DPDK Cryptodev Performance Guide*, 2024.
