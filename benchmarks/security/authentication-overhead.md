# ULL Security Benchmark: Authentication Overhead

**Date:** 2026-09-29  
**Scope:** Per-message and per-session authentication latency in ultra-low-latency trading infrastructure  
**Target:** <500 ns per-message authentication; <5 μs session authentication

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

| Mechanism | Per-Message Overhead | Per-Session Overhead | ULL Suitability |
|---|---|---|---|
| HMAC-SHA-256 | 100–300 ns | N/A (stateless) | ✅ Excellent |
| HMAC-SHA-512 | 150–400 ns | N/A (stateless) | ✅ Excellent |
| AES-CMAC | 150–350 ns | N/A (stateless) | ✅ Good |
| ECDSA P-256 sign | 50–150 μs | N/A | ❌ Sign only, verify is fast |
| ECDSA P-256 verify | 100–300 μs | N/A | ❌ Too slow for fast path |
| Ed25519 sign | 30–80 μs | N/A | ❌ Sign only |
| Ed25519 verify | 50–120 μs | N/A | ❌ Too slow for fast path |
| mTLS (mutual auth) | N/A | 10–50 μs | ⚠️ Session setup only |
| JWT (RS256) verify | 50–150 μs | N/A | ❌ Too slow |
| JWT (HS256) verify | 100–300 ns | N/A | ✅ Excellent |
| WireGuard handshake | N/A | 500–2000 μs | ⚠️ Session setup |
| MACsec MKA | N/A | 100–500 μs | ⚠️ Session setup |
| TPM 2.0 quote | N/A | 1–10 ms | ❌ Not for fast path |
| SGX attestation | N/A | 10–100 ms | ❌ Not for fast path |

---

## Measurement Methodology

### 1. Per-Message Authentication Overhead

**Objective:** Measure the latency added by authenticating each message on the data path.

**Setup:**
- Generate synthetic market-data packets (64–256 bytes)
- Measure baseline (unauthenticated) round-trip latency
- Measure authenticated round-trip latency with each mechanism
- Compute delta = authenticated − unauthenticated

**Procedure:**
```
For each auth_mechanism in [HMAC-SHA-256, HMAC-SHA-512, AES-CMAC, JWT-HS256]:
  For each packet_size in [64, 128, 256, 512]:
    For each iteration in [1..100000]:
      t0 = rdtsc()
      tag = authenticate(packet, key)
      t1 = rdtsc()
      record(t1 - t0)
  Report: p50, p99, p99.9, p99.99, max
```

**Key metrics:**
- **p50/p99/p99.9 latency** (ns)
- **Throughput** (Mpps) at target latency ceiling
- **CPU utilization** per core

### 2. Session Authentication Overhead

**Objective:** Measure the latency of establishing an authenticated session.

**Scenarios:**
- mTLS mutual authentication (full handshake)
- mTLS with session resumption
- WireGuard handshake
- MACsec MKA (802.1X)
- Custom UDP-based authentication

**Procedure:**
```
For each session_type:
  For each iteration in [1..10000]:
    t0 = rdtsc()
    session = authenticate_session(session_type)
    t1 = rdtsc()
    record(t1 - t0)
  Report: p50, p99, max
```

### 3. Certificate Chain Validation

**Objective:** Measure the latency of validating X.509 certificate chains.

**Scenarios:**
- Single-level CA (root → leaf)
- Two-level CA (root → intermediate → leaf)
- Certificate revocation check (OCSP stapling)
- Certificate revocation check (OCSP online)
- Certificate revocation check (CRL)

**Procedure:**
```
For each chain_depth in [1, 2, 3]:
  For each revocation_method in [none, OCSP_stapled, OCSP_online, CRL]:
    For each iteration in [1..10000]:
      t0 = rdtsc()
      valid = validate_certificate(chain, revocation_method)
      t1 = rdtsc()
      record(t1 - t0)
  Report: p50, p99, max
```

### 4. Hardware-Backed Attestation

**Objective:** Measure the latency of hardware-based attestation mechanisms.

**Scenarios:**
- TPM 2.0 quote (SHA-256 PCR)
- TPM 2.0 quote (SHA-1 PCR)
- Intel SGX remote attestation
- AMD SEV-SNP attestation
- ARM TrustZone attestation

---

## Hardware Requirements

### Minimum Viable

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon Scalable (Ice Lake+) with SHA-NI | Hardware SHA acceleration |
| TPM | TPM 2.0 (discrete or firmware) | Hardware-backed attestation |
| NIC | Mellanox ConnectX-6 Dx with TLS/MACsec offload | Hardware auth offload |
| HSM | YubiHSM 2 or Thales Luna 7 | Key storage and signing |

### Recommended for Full Benchmark Suite

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon 8490H (Sapphire Rapids) with QAT | QAT-accelerated TLS |
| QAT Card | Intel QAT 8970 | TLS handshake offload |
| NIC | Nvidia BlueField-3 DPU | Full protocol offload |
| FPGA | Xilinx Alveo U25 | Custom auth pipeline |
| HSM | Thales Luna 7 (network HSM) | FIPS 140-3 Level 3 key storage |
| Timing | Intel I210-AT (hardware timestamping) | Sub-μs measurement |

### FPGA Auth Pipeline Requirements

| Resource | HMAC-SHA-256 @ 100 Gb/s | Notes |
|---|---|---|
| LUTs | ~8,000–15,000 | Pipeline stages |
| FFs | ~5,000–10,000 | State and key storage |
| BRAM | ~20–50 KB | Key lookup |
| Throughput | 100 Gb/s | ~148.8 Mpps |
| Latency | 30–80 ns | Wire-to-wire |

---

## Software Requirements

### Operating System

| OS | Version | Kernel | Notes |
|---|---|---|---|
| Ubuntu LTS | 24.04 | 6.8+ | Primary benchmark platform |
| RHEL | 9.3+ | 5.14+ | Enterprise deployment target |

### Authentication Libraries

| Library | Version | Mechanisms | Use Case |
|---|---|---|---|
| OpenSSL | 3.2+ | TLS 1.3, mTLS, ECDSA, Ed25519 | Baseline TLS |
| BoringSSL | latest | TLS 1.3, mTLS, ECDSA, Ed25519 | Google-optimized TLS |
| wolfSSL | 5.7+ | TLS 1.3, mTLS, ECDSA, Ed25519 | Embedded/FPGA-friendly |
| libjwt | 1.17+ | JWT (HS256, RS256, ES256) | Token-based auth |
| tpm2-tss | 4.1+ | TPM 2.0 quote, key operations | Hardware attestation |
| Intel SGX SDK | 2.23+ | SGX attestation | Enclave attestation |
| Linux kernel | 6.8+ | AF_ALG (HMAC, CMAC) | Kernel-bypass auth |

### Benchmark Tools

| Tool | Purpose |
|---|---|
| `openssl speed` | Primitive auth throughput |
| `openssl s_time` | TLS handshake latency |
| `tpm2_quote` | TPM attestation latency |
| `sgx_sign` | SGX attestation latency |
| Custom `rdtsc` harness | Sub-μs per-message measurement |
| `dpdk-crypto-perf` | DPDK auth benchmark |

---

## Benchmark Scenarios

### Scenario A: HMAC-SHA-256 Per-Message Authentication

```c
// Pseudocode for per-message HMAC-SHA-256 measurement
void benchmark_hmac_sha256(void) {
    uint8_t key[32], message[256], tag[32];
    HMAC_CTX *ctx = HMAC_CTX_new();
    HMAC_Init_ex(ctx, key, 32, EVP_sha256(), NULL);
    
    for (int i = 0; i < ITERATIONS; i++) {
        uint64_t t0 = __rdtsc();
        HMAC_Update(ctx, message, sizeof(message));
        HMAC_Final(ctx, tag, NULL);
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 100–300 ns per 256-byte message on modern x86 with SHA-NI

### Scenario B: mTLS Mutual Authentication

```bash
# Server
openssl s_server -accept 443 -tls1_3 -cert server.pem -key server.key \
    -Verify 2 -CAfile ca.pem -www

# Client (measure mutual handshake time)
for i in $(seq 1 10000); do
    /usr/bin/time -f "%e" openssl s_client -connect localhost:443 -tls1_3 \
        -cert client.pem -key client.key -CAfile ca.pem -brief
done
```

**Expected:** 10–50 μs for full mutual handshake

### Scenario C: JWT (HS256) Verification

```c
// Pseudocode for JWT-HS256 verification
void benchmark_jwt_hs256(void) {
    const char *jwt = "eyJhbGciOiJIUzI1NiJ9...";
    uint8_t key[32];
    
    for (int i = 0; i < ITERATIONS; i++) {
        uint64_t t0 = __rdtsc();
        int valid = jwt_verify_hs256(jwt, key, sizeof(key));
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 100–300 ns per JWT verification

### Scenario D: TPM 2.0 Attestation

```bash
# Measure TPM quote latency
for i in $(seq 1 1000); do
    /usr/bin/time -f "%e" tpm2_quote -c 0x81010001 -l sha256:0,1,2,3 \
        -q "nonce" -m quote.msg -s quote.sig
done
```

**Expected:** 1–10 ms per TPM quote

---

## Expected Results & Baselines

### Per-Message Authentication (per 256-byte message, Intel Sapphire Rapids)

| Mechanism | p50 (ns) | p99 (ns) | p99.9 (ns) | Throughput (Mpps) |
|---|---|---|---|---|
| HMAC-SHA-256 | 120 | 180 | 300 | ~8.3 |
| HMAC-SHA-512 | 160 | 240 | 400 | ~6.2 |
| AES-CMAC | 180 | 260 | 400 | ~5.5 |
| HMAC-SHA-256 (SHA-NI) | 80 | 120 | 200 | ~12.5 |
| JWT-HS256 verify | 150 | 220 | 350 | ~6.7 |

### Session Authentication Latency

| Mechanism | p50 (μs) | p99 (μs) | Notes |
|---|---|---|---|
| mTLS full handshake | 15 | 30 | Software, no offload |
| mTLS full handshake (QAT) | 8 | 15 | QAT offload |
| mTLS session resumption | 3 | 6 | Software |
| mTLS session resumption (QAT) | 1.5 | 3 | QAT offload |
| WireGuard handshake | 800 | 1500 | Software |
| MACsec MKA | 200 | 400 | Hardware-assisted |

### Certificate Chain Validation

| Chain Depth | Revocation | p50 (μs) | p99 (μs) |
|---|---|---|---|
| 1 (root → leaf) | None | 50 | 100 |
| 2 (root → inter → leaf) | None | 100 | 200 |
| 3 (root → inter1 → inter2 → leaf) | None | 150 | 300 |
| 2 | OCSP stapled | 120 | 250 |
| 2 | OCSP online | 500 | 2000 |
| 2 | CRL | 200 | 500 |

### Hardware Attestation

| Mechanism | p50 (ms) | p99 (ms) | Notes |
|---|---|---|---|
| TPM 2.0 quote (SHA-256) | 2 | 5 | Discrete TPM |
| TPM 2.0 quote (SHA-1) | 1 | 3 | Discrete TPM |
| Intel SGX attestation | 20 | 50 | Remote attestation |
| AMD SEV-SNP attestation | 15 | 30 | Remote attestation |

---

## Optimization Strategies

### 1. Use Symmetric Authentication on the Fast Path
- **HMAC-SHA-256** is the fastest per-message authentication mechanism
- **Avoid asymmetric signatures** (ECDSA, Ed25519) on the fast path — they are 100–1000× slower
- **Use asymmetric auth only for session establishment**, then switch to symmetric

### 2. Pre-Compute and Cache
- **Pre-compute HMAC keys** for each session
- **Cache certificate chain validation** results (with TTL)
- **Cache JWT validation** results (with TTL)

### 3. Hardware Offload
- **QAT for TLS handshake** — offload ECDSA/RSA operations
- **FPGA for HMAC** — sub-100 ns per-message authentication
- **SHA-NI for HMAC** — hardware SHA acceleration on modern x86

### 4. Session Resumption
- **Use TLS 1.3 0-RTT resumption** — skip full handshake on reconnect
- **Use session tickets** — stateless server-side resumption
- **Pre-establish sessions** — amortize auth cost over many messages

### 5. Batch Authentication
- **Amortize authentication** across multiple messages (e.g., authenticate a batch of 10 messages with one HMAC)
- **Use Merkle trees** for batch verification

---

## References

1. Intel. *Intel QuickAssist Technology (QAT) Developer Guide*, 2025.
2. Trusted Computing Group. *TPM 2.0 Library Specification*, 2023.
3. IETF. *RFC 8446: TLS 1.3*, 2018.
4. IETF. *RFC 7519: JSON Web Token (JWT)*, 2015.
5. IETF. *RFC 6960: Online Certificate Status Protocol (OCSP)*, 2013.
6. NIST. *FIPS 180-4: Secure Hash Standard (SHS)*, 2015.
7. NIST. *FIPS 198-1: The Keyed-Hash Message Authentication Code (HMAC)*, 2008.
8. Intel. *Intel Software Guard Extensions (SGX) SDK*, 2024.
