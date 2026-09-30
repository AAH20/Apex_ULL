# ULL Security Benchmark: Audit Overhead

**Date:** 2026-09-29  
**Scope:** Per-event audit logging latency in ultra-low-latency trading infrastructure  
**Target:** <500 ns per-event audit (asynchronous); <5 μs (synchronous)

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

| Mechanism | Per-Event Overhead | Durability Guarantee | ULL Suitability |
|---|---|---|---|
| In-memory buffer (async) | 20–100 ns | None (loss on crash) | ✅ Excellent |
| Lock-free ring buffer | 50–200 ns | None (loss on crash) | ✅ Excellent |
| Write-ahead log (WAL) | 200–1000 ns | Process crash | ✅ Good |
| Append-only file (O_APPEND) | 500–2000 ns | OS crash | ✅ Good |
| fsync() per event | 10–100 μs | System crash | ❌ Too slow |
| Remote audit (sync) | 50–500 μs | System crash | ❌ Too slow |
| Remote audit (async) | 100–500 ns | None (loss on crash) | ✅ Excellent |
| FPGA-accelerated audit | 50–200 ns | Process crash | ✅ Good |
| TPM-backed audit | 1–10 ms | System crash | ❌ Too slow |
| Blockchain-based audit | 100–500 ms | Immutable | ❌ Too slow |

---

## Measurement Methodology

### 1. Per-Event Audit Logging Overhead

**Objective:** Measure the latency added by auditing each event on the data path.

**Setup:**
- Generate synthetic audit events (64–256 bytes, matching typical audit log sizes)
- Measure baseline (no audit) round-trip latency
- Measure audited round-trip latency with each mechanism
- Compute delta = audited − unaudited

**Procedure:**
```
For each audit_mechanism in [memory_buffer, ring_buffer, WAL, append_file, fsync, remote_sync, remote_async]:
  For each event_size in [64, 128, 256, 512]:
    For each iteration in [1..100000]:
      t0 = rdtsc()
      audit_log(event)
      t1 = rdtsc()
      record(t1 - t0)
  Report: p50, p99, p99.9, p99.99, max
```

**Key metrics:**
- **p50/p99/p99.9 latency** (ns)
- **Throughput** (M events/s) at target latency ceiling
- **CPU utilization** per core
- **Memory bandwidth** utilization

### 2. Synchronous vs Asynchronous Audit

**Objective:** Measure the overhead difference between synchronous and asynchronous audit logging.

**Scenarios:**
- Synchronous: audit log written before event is processed
- Asynchronous: audit log written after event is processed (fire-and-forget)
- Batched: audit logs written in batches (e.g., every 100 events or 1 ms)

**Procedure:**
```
For each mode in [sync, async, batched]:
  For each batch_size in [1, 10, 100, 1000]:
    For each iteration in [1..100000]:
      t0 = rdtsc()
      process_event(event)
      audit_log(event, mode, batch_size)
      t1 = rdtsc()
      record(t1 - t0)
  Report: p50, p99, max
```

### 3. Tamper-Evident Audit Structures

**Objective:** Measure the overhead of tamper-evident audit logging.

**Scenarios:**
- Plain append-only log
- Hash chain (each entry includes hash of previous entry)
- Merkle tree (batch verification)
- Signed log (each entry signed with HMAC)
- TPM-backed log (each entry extends PCR)

**Procedure:**
```
For each tamper_mechanism in [plain, hash_chain, merkle_tree, signed, tpm]:
  For each iteration in [1..100000]:
    t0 = rdtsc()
    audit_log_tamper_evident(event, tamper_mechanism)
    t1 = rdtsc()
    record(t1 - t0)
  Report: p50, p99, max
```

### 4. Remote Audit Shipping

**Objective:** Measure the overhead of shipping audit logs to a remote system.

**Scenarios:**
- Local file write
- Remote syslog (UDP)
- Remote syslog (TCP)
- Remote Kafka producer
- Remote gRPC call

**Procedure:**
```
For each remote_mechanism in [local, syslog_udp, syslog_tcp, kafka, grpc]:
  For each iteration in [1..100000]:
    t0 = rdtsc()
    audit_log_remote(event, remote_mechanism)
    t1 = rdtsc()
    record(t1 - t0)
  Report: p50, p99, max
```

---

## Hardware Requirements

### Minimum Viable

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon Scalable (Ice Lake+) | Software audit baseline |
| NVMe SSD | Intel Optane P5800X or equivalent | Low-latency persistent audit |
| NIC | Mellanox ConnectX-6 Dx | Kernel-bypass networking |

### Recommended for Full Benchmark Suite

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon 8490H (Sapphire Rapids) | High-performance software audit |
| NVMe SSD | Intel Optane P5800X (1.6 TB) | Sub-μs persistent write |
| NIC | Nvidia BlueField-3 DPU | Full protocol offload |
| FPGA | Xilinx Alveo U25 | Custom audit pipeline |
| Timing | Intel I210-AT (hardware timestamping) | Sub-μs measurement |

### FPGA Audit Pipeline Requirements

| Resource | Hash Chain @ 100 Gb/s | Merkle Tree @ 100 Gb/s | Notes |
|---|---|---|---|
| LUTs | ~10,000–20,000 | ~20,000–40,000 | Pipeline stages |
| FFs | ~5,000–10,000 | ~10,000–20,000 | State storage |
| BRAM | ~50–100 KB | ~200–500 KB | Hash state + tree |
| Throughput | 100 Gb/s | 100 Gb/s | ~148.8 Mpps |
| Latency | 50–100 ns | 100–200 ns | Wire-to-wire |

---

## Software Requirements

### Operating System

| OS | Version | Kernel | Notes |
|---|---|---|---|
| Ubuntu LTS | 24.04 | 6.8+ | Primary benchmark platform |
| RHEL | 9.3+ | 5.14+ | Enterprise deployment target |

### Audit Libraries

| Library | Version | Mechanisms | Use Case |
|---|---|---|---|
| syslog (rsyslog) | 8.2024+ | Syslog protocol | Standard system audit |
| Apache Kafka | 3.7+ | Distributed log shipping | High-throughput audit |
| gRPC | 1.64+ | RPC-based audit | Low-latency remote audit |
| spdlog | 1.14+ | C++ logging library | Application audit |
| log4cplus | 2.1+ | C++ logging library | Application audit |
| Linux kernel | 6.8+ | AF_ALG (hash chain) | Kernel-bypass audit |
| tpm2-tss | 4.1+ | TPM-backed audit | Hardware-backed audit |

### Benchmark Tools

| Tool | Purpose |
|---|---|
| `rsyslogd` | Syslog audit benchmark |
| `kafka-producer-perf-test` | Kafka audit benchmark |
| `grpc_bench` | gRPC audit benchmark |
| Custom `rdtsc` harness | Sub-μs per-event measurement |
| `fio` | Persistent storage audit benchmark |

---

## Benchmark Scenarios

### Scenario A: In-Memory Buffer (Async)

```c
// Pseudocode for in-memory audit buffer
void benchmark_memory_buffer(void) {
    audit_buffer_t *buf = audit_buffer_create(1024 * 1024); // 1 MB
    
    for (int i = 0; i < ITERATIONS; i++) {
        audit_event_t *event = generate_audit_event();
        
        uint64_t t0 = __rdtsc();
        audit_buffer_append(buf, event);
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 20–100 ns per audit event

### Scenario B: Write-Ahead Log (WAL)

```c
// Pseudocode for WAL audit
void benchmark_wal(void) {
    wal_t *wal = wal_open("audit.wal", O_WRONLY | O_APPEND | O_CREAT);
    
    for (int i = 0; i < ITERATIONS; i++) {
        audit_event_t *event = generate_audit_event();
        
        uint64_t t0 = __rdtsc();
        wal_append(wal, event, sizeof(*event));
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 200–1000 ns per audit event

### Scenario C: Hash Chain (Tamper-Evident)

```c
// Pseudocode for hash chain audit
void benchmark_hash_chain(void) {
    hash_chain_t *chain = hash_chain_create();
    uint8_t prev_hash[32] = {0};
    
    for (int i = 0; i < ITERATIONS; i++) {
        audit_event_t *event = generate_audit_event();
        
        uint64_t t0 = __rdtsc();
        hash_chain_append(chain, event, prev_hash);
        memcpy(prev_hash, hash_chain_last(chain), 32);
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 300–1500 ns per audit event (includes SHA-256 hash)

### Scenario D: Remote Audit (Async)

```c
// Pseudocode for remote async audit
void benchmark_remote_async(void) {
    kafka_producer_t *producer = kafka_producer_create("audit-topic");
    
    for (int i = 0; i < ITERATIONS; i++) {
        audit_event_t *event = generate_audit_event();
        
        uint64_t t0 = __rdtsc();
        kafka_producer_send_async(producer, event, sizeof(*event));
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 100–500 ns per audit event (async send)

---

## Expected Results & Baselines

### Per-Event Audit Logging (Intel Sapphire Rapids)

| Mechanism | p50 (ns) | p99 (ns) | p99.9 (ns) | Throughput (M/s) |
|---|---|---|---|---|
| In-memory buffer | 30 | 60 | 120 | ~33 |
| Lock-free ring buffer | 80 | 150 | 300 | ~12.5 |
| WAL (O_APPEND) | 400 | 800 | 1500 | ~2.5 |
| Append-only file | 800 | 1500 | 3000 | ~1.25 |
| fsync() per event | 20000 | 50000 | 100000 | ~0.05 |
| Remote syslog (UDP) | 200 | 500 | 1000 | ~5 |
| Remote syslog (TCP) | 500 | 1500 | 3000 | ~2 |
| Remote Kafka (async) | 150 | 400 | 800 | ~6.7 |
| Remote gRPC (sync) | 50000 | 200000 | 500000 | ~0.02 |

### Synchronous vs Asynchronous

| Mode | Batch Size | p50 (ns) | p99 (ns) | Notes |
|---|---|---|---|---|
| Sync | 1 | 800 | 1500 | Per-event fsync |
| Async | 1 | 30 | 60 | Fire-and-forget |
| Batched | 10 | 50 | 100 | Amortized |
| Batched | 100 | 30 | 60 | Amortized |
| Batched | 1000 | 25 | 50 | Amortized |

### Tamper-Evident Audit Structures

| Mechanism | p50 (ns) | p99 (ns) | Notes |
|---|---|---|---|
| Plain append-only | 400 | 800 | Baseline |
| Hash chain (SHA-256) | 600 | 1200 | Per-entry hash |
| Merkle tree (batch=100) | 500 | 1000 | Amortized hash |
| Signed (HMAC-SHA-256) | 700 | 1400 | Per-entry HMAC |
| TPM-backed | 2000000 | 5000000 | TPM PCR extend |

### Remote Audit Shipping

| Mechanism | p50 (ns) | p99 (ns) | Notes |
|---|---|---|---|
| Local file | 400 | 800 | Baseline |
| Syslog (UDP) | 200 | 500 | Fire-and-forget |
| Syslog (TCP) | 500 | 1500 | Reliable delivery |
| Kafka (async) | 150 | 400 | Buffered |
| Kafka (sync) | 50000 | 200000 | Per-event ack |
| gRPC (sync) | 50000 | 200000 | RPC round-trip |

---

## Optimization Strategies

### 1. Use Asynchronous Audit on the Fast Path
- **In-memory buffer** is the fastest audit mechanism — sub-100 ns
- **Lock-free ring buffer** for multi-producer scenarios
- **Avoid synchronous audit** on the fast path — it adds 10–100 μs per event

### 2. Batch Audit Events
- **Amortize audit overhead** across multiple events
- **Batch size 100–1000** events per audit write
- **Time-based flushing** (e.g., every 1 ms) for durability

### 3. Hardware Acceleration
- **FPGA for hash chain** — sub-100 ns per-entry hashing
- **NVMe SSD for WAL** — sub-μs persistent write
- **SmartNIC for remote audit** — offload network stack

### 4. Tamper-Evidence Optimization
- **Use Merkle trees** for batch verification — amortize hash cost
- **Use hash chains** for per-entry integrity — simple and fast
- **Avoid TPM-backed audit** on the fast path — 1–10 ms per event

### 5. Remote Audit Optimization
- **Use async Kafka producer** for remote audit — sub-μs per event
- **Use UDP syslog** for fire-and-forget audit — sub-μs per event
- **Avoid synchronous remote audit** on the fast path — 50–500 μs per event

### 6. Storage Optimization
- **Use Intel Optane NVMe** for WAL — sub-μs persistent write
- **Use O_APPEND** for atomic appends — no locking needed
- **Use fallocate()** to pre-allocate disk space — avoid metadata updates

---

## References

1. NIST. *SP 800-92: Guide to Computer Security Log Management*, 2006.
2. NIST. *SP 800-184: Guide for Cybersecurity Event Recovery*, 2016.
3. Apache Kafka. *Kafka Documentation*, 2024.
4. gRPC. *gRPC Documentation*, 2024.
5. Intel. *Intel Optane SSD P5800X Product Brief*, 2024.
6. Trusted Computing Group. *TPM 2.0 Library Specification*, 2023.
7. Linux kernel. *Documentation/filesystems/ext4.txt*, 2024.
8. Xilinx. *Alveo U25N Data Center Accelerator Card*, 2024.
