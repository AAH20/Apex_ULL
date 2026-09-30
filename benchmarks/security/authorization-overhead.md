# ULL Security Benchmark: Authorization Overhead

**Date:** 2026-09-29  
**Scope:** Per-request authorization latency in ultra-low-latency trading infrastructure  
**Target:** <200 ns per-request authorization; <1 μs for complex policy evaluation

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

| Mechanism | Per-Request Overhead | Policy Complexity | ULL Suitability |
|---|---|---|---|
| Static ACL (bitmap) | 10–50 ns | Low (allow/deny list) | ✅ Excellent |
| RBAC (in-memory) | 50–200 ns | Medium (role → permission) | ✅ Excellent |
| ABAC (in-memory) | 100–500 ns | High (attribute-based) | ✅ Good |
| Capability-based | 20–100 ns | Low (token → resource) | ✅ Excellent |
| OPA/Rego (local) | 500–5000 ns | Very high (full policy language) | ⚠️ Moderate |
| OPA/Rego (sidecar) | 50–500 μs | Very high | ❌ Too slow |
| OPA/Rego (bundle cache) | 100–1000 ns | Very high | ⚠️ Moderate |
| Cedar (local) | 200–1000 ns | High | ⚠️ Moderate |
| Casbin (in-memory) | 100–500 ns | Medium | ✅ Good |
| Custom FPGA policy | 20–100 ns | Low–medium | ✅ Excellent |

---

## Measurement Methodology

### 1. Per-Request Authorization Overhead

**Objective:** Measure the latency added by authorizing each request on the data path.

**Setup:**
- Generate synthetic authorization requests (subject, action, resource)
- Measure baseline (no authorization) round-trip latency
- Measure authorized round-trip latency with each mechanism
- Compute delta = authorized − unauthenticated

**Procedure:**
```
For each authz_mechanism in [ACL, RBAC, ABAC, Capability, OPA_local, Cedar, Casbin]:
  For each policy_complexity in [low, medium, high]:
    For each iteration in [1..100000]:
      t0 = rdtsc()
      decision = authorize(subject, action, resource, policy)
      t1 = rdtsc()
      record(t1 - t0)
  Report: p50, p99, p99.9, p99.99, max
```

**Key metrics:**
- **p50/p99/p99.9 latency** (ns)
- **Throughput** (M requests/s) at target latency ceiling
- **CPU utilization** per core

### 2. Policy Evaluation Complexity Scaling

**Objective:** Measure how authorization latency scales with policy complexity.

**Scenarios:**
- ACL: 10, 100, 1000, 10000 entries
- RBAC: 10, 100, 1000 roles; 10, 100, 1000 permissions
- ABAC: 1, 5, 10, 20 attributes per subject/resource
- OPA/Rego: 1, 10, 100, 1000 rules

**Procedure:**
```
For each mechanism:
  For each complexity_level:
    For each iteration in [1..100000]:
      t0 = rdtsc()
      decision = authorize(request, policy)
      t1 = rdtsc()
      record(t1 - t0)
  Report: p50, p99, max
```

### 3. Distributed Authorization (Sidecar vs Inline)

**Objective:** Measure the overhead of distributed authorization architectures.

**Scenarios:**
- Inline authorization (same process)
- Sidecar authorization (localhost IPC)
- Remote authorization (network call)
- Cached authorization (TTL-based)

**Procedure:**
```
For each architecture in [inline, sidecar, remote, cached]:
  For each iteration in [1..100000]:
    t0 = rdtsc()
    decision = authorize(request)
    t1 = rdtsc()
    record(t1 - t0)
  Report: p50, p99, max
```

### 4. FPGA-Based Policy Evaluation

**Objective:** Measure authorization latency when offloaded to FPGA.

**Setup:**
- FPGA bitstream implementing ACL/RBAC policy evaluation
- Measure: request-in → decision-out latency
- Compare with software baseline

---

## Hardware Requirements

### Minimum Viable

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon Scalable (Ice Lake+) | Software authz baseline |
| NIC | Mellanox ConnectX-6 Dx | Kernel-bypass networking |
| FPGA | Xilinx Alveo U25 | Hardware policy evaluation |

### Recommended for Full Benchmark Suite

| Component | Specification | Purpose |
|---|---|---|
| CPU | Intel Xeon 8490H (Sapphire Rapids) | High-performance software authz |
| NIC | Nvidia BlueField-3 DPU | Full protocol offload |
| FPGA | Xilinx Versal AI Edge / Alveo U55C | Custom authz pipeline |
| Timing | Intel I210-AT (hardware timestamping) | Sub-μs measurement |

### FPGA Authz Pipeline Requirements

| Resource | ACL @ 100 Gb/s | RBAC @ 100 Gb/s | Notes |
|---|---|---|---|
| LUTs | ~5,000–10,000 | ~15,000–30,000 | Pipeline stages |
| FFs | ~3,000–5,000 | ~10,000–20,000 | State storage |
| BRAM | ~10–50 KB | ~100–500 KB | Policy storage |
| Throughput | 100 Gb/s | 100 Gb/s | ~148.8 Mpps |
| Latency | 20–50 ns | 50–100 ns | Wire-to-wire |

---

## Software Requirements

### Operating System

| OS | Version | Kernel | Notes |
|---|---|---|---|
| Ubuntu LTS | 24.04 | 6.8+ | Primary benchmark platform |
| RHEL | 9.3+ | 5.14+ | Enterprise deployment target |

### Authorization Libraries

| Library | Version | Mechanisms | Use Case |
|---|---|---|---|
| Open Policy Agent (OPA) | 0.68+ | Rego policy language | General-purpose authz |
| Cedar | 4.0+ | Cedar policy language | AWS-optimized authz |
| Casbin | 1.26+ | RBAC, ABAC, ACL | Lightweight authz |
| Oso | 0.28+ | Polar policy language | Application authz |
| Google Zanzibar | — | Relationship-based authz | Google-scale authz |
| Custom C library | — | ACL, RBAC, ABAC | Maximum performance |

### Benchmark Tools

| Tool | Purpose |
|---|---|
| `opa bench` | OPA policy evaluation benchmark |
| `cedar-cli` | Cedar policy evaluation benchmark |
| Custom `rdtsc` harness | Sub-μs per-request measurement |
| `dpdk-crypto-perf` | DPDK-based authz benchmark |
| `wrk` / `wrk2` | HTTP-level authz benchmark |

---

## Benchmark Scenarios

### Scenario A: Static ACL (Bitmap)

```c
// Pseudocode for ACL bitmap authorization
void benchmark_acl_bitmap(void) {
    uint64_t acl_bitmap = 0xDEADBEEFCAFEBABE; // Pre-computed ACL
    
    for (int i = 0; i < ITERATIONS; i++) {
        uint64_t subject_id = generate_subject_id();
        uint64_t action = generate_action();
        
        uint64_t t0 = __rdtsc();
        int allowed = (acl_bitmap >> (subject_id * 8 + action)) & 1;
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 10–50 ns per authorization decision

### Scenario B: RBAC (In-Memory)

```c
// Pseudocode for RBAC authorization
void benchmark_rbac(void) {
    rbac_policy_t *policy = load_rbac_policy("rbac_policy.json");
    
    for (int i = 0; i < ITERATIONS; i++) {
        subject_t *subject = generate_subject();
        const char *action = generate_action();
        const char *resource = generate_resource();
        
        uint64_t t0 = __rdtsc();
        int allowed = rbac_authorize(policy, subject, action, resource);
        uint64_t t1 = __rdtsc();
        results[i] = t1 - t0;
    }
    report_percentiles(results, ITERATIONS);
}
```

**Expected:** 50–200 ns per authorization decision

### Scenario C: OPA/Rego (Local)

```bash
# Benchmark OPA policy evaluation
opa bench --benchmark-iterations 100000 --benchmark-authz \
    --policy authz.rego --input input.json --request "data.app.authz.allow"
```

**Expected:** 500–5000 ns per policy evaluation

### Scenario D: FPGA-Based Policy Evaluation

```
[Request] → [FPGA: ACL/RBAC evaluation] → [Decision]
                ↑ 20-100 ns
```

**Expected:** 20–100 ns per authorization decision

---

## Expected Results & Baselines

### Per-Request Authorization (Intel Sapphire Rapids)

| Mechanism | Policy Complexity | p50 (ns) | p99 (ns) | p99.9 (ns) | Throughput (M/s) |
|---|---|---|---|---|---|
| Static ACL (bitmap) | Low | 15 | 25 | 50 | ~66 |
| Capability-based | Low | 30 | 50 | 100 | ~33 |
| RBAC (in-memory) | Medium | 80 | 150 | 300 | ~12.5 |
| ABAC (in-memory) | High | 200 | 400 | 800 | ~5 |
| Casbin (in-memory) | Medium | 120 | 250 | 500 | ~8.3 |
| Cedar (local) | High | 300 | 600 | 1200 | ~3.3 |
| OPA/Rego (local) | Very high | 800 | 2000 | 5000 | ~1.25 |
| OPA/Rego (bundle cache) | Very high | 400 | 1000 | 2500 | ~2.5 |

### Policy Complexity Scaling

| Mechanism | Low (ns) | Medium (ns) | High (ns) | Very High (ns) |
|---|---|---|---|---|
| ACL | 15 | 30 | 60 | 120 |
| RBAC | 50 | 100 | 200 | 400 |
| ABAC | 100 | 250 | 500 | 1000 |
| OPA/Rego | 500 | 1500 | 4000 | 10000 |

### Distributed Authorization Architecture

| Architecture | p50 (ns) | p99 (ns) | Notes |
|---|---|---|---|
| Inline (same process) | 80 | 150 | Baseline |
| Sidecar (localhost IPC) | 5000 | 15000 | Unix socket |
| Remote (network call) | 50000 | 200000 | TCP round-trip |
| Cached (TTL=1s) | 20 | 50 | Cache hit |

### FPGA-Based Authorization

| Mechanism | p50 (ns) | p99 (ns) | Throughput (Mpps) |
|---|---|---|---|
| ACL (bitmap) | 20 | 40 | ~50 |
| RBAC (hash table) | 50 | 100 | ~20 |
| ABAC (multi-attribute) | 80 | 150 | ~12.5 |

---

## Optimization Strategies

### 1. Use Simple Mechanisms on the Fast Path
- **Static ACL (bitmap)** is the fastest authorization mechanism — O(1) lookup
- **Capability-based auth** is nearly as fast — token contains permissions
- **Avoid OPA/Rego on the fast path** — use it for complex, infrequent decisions

### 2. Pre-Compute and Cache
- **Pre-compute RBAC role assignments** — map subject → permissions at session start
- **Cache authorization decisions** — TTL-based caching for repeated requests
- **Use Bloom filters** for fast negative checks (definitely not authorized)

### 3. Hardware Offload
- **FPGA for ACL/RBAC** — sub-100 ns per authorization decision
- **SmartNIC for policy enforcement** — offload authz to NIC

### 4. Policy Simplification
- **Flatten ABAC to RBAC** — pre-compute attribute combinations into roles
- **Use hierarchical RBAC** — reduce policy size through role inheritance
- **Partition policies** — only load relevant policy subset per service

### 5. Distributed Architecture
- **Inline authorization** for latency-critical paths
- **Sidecar authorization** for complex, infrequent decisions
- **Cached authorization** for repeated requests

---

## References

1. Open Policy Agent. *OPA Documentation*, 2024.
2. Amazon Web Services. *Cedar Policy Language*, 2024.
3. Casbin. *Casbin Documentation*, 2024.
4. Google. *Zanzibar: Google's Consistent, Global Authorization System*, 2019.
5. NIST. *SP 800-162: Guide to Attribute Based Access Control (ABAC) Definition and Considerations*, 2014.
6. NIST. *SP 800-178: Guide to Role-Based Access Control (RBAC)*, 2024.
7. Xilinx. *Alveo U25N Data Center Accelerator Card*, 2024.
