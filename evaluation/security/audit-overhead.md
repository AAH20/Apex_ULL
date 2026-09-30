# Audit Overhead Evaluation

## 1. Scope

Measures latency introduced by audit logging and compliance recording in ULL infrastructure:
- **Synchronous audit**: Inline audit record generation before request completion
- **Asynchronous audit**: Queue-based audit record generation (non-blocking)
- **Structured logging**: JSON/CEF/LEEF formatted log generation
- **Audit trail integrity**: Hash chaining, Merkle trees, signed log entries
- **Compliance logging**: PCI DSS, SOX, GDPR, HIPAA-specific audit requirements

---

## 2. Measurement Methodology

### 2.1 Synchronous Audit Logging

| Phase | What to Measure | How |
|-------|----------------|-----|
| Event serialization | Audit event → JSON/Protobuf | Micro-benchmark |
| Hash chaining | Previous hash + current event → new hash | Crypto timing |
| Digital signature | Sign audit entry | Ed25519/ECDSA timing |
| Synchronous write | Write to local disk / syslog | I/O timing |
| Remote ship | Send to SIEM/log aggregator | Network round-trip |

**Tooling:**
```python
# Audit event serialization micro-benchmark
import time, json, hashlib

def measure_audit_sync(event):
    start = time.perf_counter_ns()
    serialized = json.dumps(event)           # Serialization
    entry_hash = hashlib.sha256(serialized.encode()).digest()  # Hash
    # signature = sign(entry_hash)            # Optional: sign
    # write_to_disk(serialized)               # Optional: sync write
    elapsed = time.perf_counter_ns() - start
    return elapsed
```

### 2.2 Asynchronous Audit Logging

| Phase | What to Measure | How |
|-------|----------------|-----|
| Event serialization | Audit event → JSON/Protobuf | Micro-benchmark |
| Queue enqueue | Push to Kafka/Redis/NATS | Queue producer timing |
| Queue dequeue | Consumer read latency | Queue consumer timing |
| Batch write | Bulk insert to log store | DB/storage timing |
| End-to-end | Event generated → queryable in SIEM | Full pipeline timing |

**Tooling:**
```bash
# Kafka producer latency
kafka-producer-perf-test \
  --topic audit-events \
  --num-records 100000 \
  --record-size 512 \
  --throughput -1 \
  --producer-props bootstrap.servers=localhost:9092

# Redis stream enqueue latency
redis-cli --latency-history -i 1
# Then: XADD audit:stream * field value
```

### 2.3 Structured Log Generation

| Format | Serialization Size | Serialization Latency | Notes |
|--------|-------------------|----------------------|-------|
| JSON | 200–2000 bytes | 0.01–0.1 ms | Most common |
| CEF (Common Event Format) | 300–1500 bytes | 0.01–0.1 ms | SIEM-friendly |
| LEEF (Log Event Extended Format) | 300–1500 bytes | 0.01–0.1 ms | IBM QRadar |
| Protobuf | 100–800 bytes | 0.005–0.05 ms | Compact, fast |
| MessagePack | 100–800 bytes | 0.005–0.05 ms | Binary, fast |
| CSV | 200–1000 bytes | 0.01–0.05 ms | Simple, verbose |

### 2.4 Audit Trail Integrity

| Mechanism | Overhead per Entry | Verification Latency | Notes |
|-----------|-------------------|---------------------|-------|
| Hash chain (SHA-256) | 0.01–0.05 ms | 0.01–0.05 ms | Sequential dependency |
| Merkle tree | 0.05–0.2 ms | 0.1–1 ms | Batch verification |
| Digital signature (Ed25519) | 0.05–0.2 ms | 0.1–0.5 ms | Per-entry signing |
| Digital signature (ECDSA P-256) | 0.3–1.5 ms | 0.2–1 ms | Slower than Ed25519 |
| Blockchain anchoring | 10–1000 ms | N/A | Periodic batch anchor |

---

## 3. Benchmark Standards

| Standard | Relevance |
|----------|-----------|
| **RFC 5424 (Syslog)** | Syslog protocol and message format |
| **RFC 3164 (BSD Syslog)** | Legacy syslog format |
| **CEF (Common Event Format)** | ArcSight/SIEM standard |
| **LEEF (Log Event Extended Format)** | IBM QRadar format |
| **OpenTelemetry Logs** | Cloud-native observability |
| **NIST SP 800-92** | Guide to computer security log management |
| **PCI DSS v4.0** | Requirement 10: Track and monitor access |
| **SOX Section 404** | Internal controls reporting |
| **GDPR Article 30** | Records of processing activities |
| **HIPAA §164.312(b)** | Audit controls |

---

## 4. Industry Averages

### 4.1 Audit Event Serialization

| Format | Latency (per event) | Throughput (events/s) | Notes |
|--------|---------------------|----------------------|-------|
| JSON | 0.01–0.1 ms | 10,000–100,000 | Most common |
| Protobuf | 0.005–0.05 ms | 20,000–200,000 | Fastest structured |
| MessagePack | 0.005–0.05 ms | 20,000–200,000 | Binary JSON |
| CEF | 0.01–0.1 ms | 10,000–100,000 | SIEM-optimized |
| Plain text | 0.005–0.05 ms | 20,000–200,000 | Simplest |

### 4.2 Audit Write Latency

| Destination | Typical Latency | Notes |
|-------------|----------------|-------|
| Local disk (buffered) | 0.01–0.1 ms | Page cache |
| Local disk (O_SYNC) | 0.5–5 ms | Forced flush |
| Syslog (UDP) | 0.05–0.2 ms | Fire-and-forget |
| Syslog (TCP) | 0.1–1 ms | Reliable delivery |
| Kafka produce | 0.1–2 ms | Async, batched |
| Redis stream | 0.05–0.2 ms | In-memory |
| SIEM API (HTTP) | 1–10 ms | Network round-trip |
| CloudWatch Logs | 1–5 ms | AWS API |
| Stackdriver/Cloud Logging | 1–5 ms | GCP API |

### 4.3 Hash Chain & Integrity Overhead

| Operation | Latency (per entry) | Notes |
|-----------|---------------------|-------|
| SHA-256 hash | 0.005–0.02 ms | Fast, hardware accel |
| SHA-384 hash | 0.005–0.02 ms | Slightly slower |
| HMAC-SHA256 | 0.01–0.05 ms | Keyed hash |
| Ed25519 sign | 0.05–0.2 ms | Per-entry signature |
| Ed25519 verify | 0.1–0.5 ms | Verification |
| ECDSA P-256 sign | 0.3–1.5 ms | Slower signing |
| ECDSA P-256 verify | 0.2–1 ms | Verification |
| Merkle tree build (batch) | 0.01–0.05 ms/entry | Amortized |

### 4.4 End-to-End Audit Pipeline Latency

| Pipeline Stage | Typical Latency | Notes |
|----------------|----------------|-------|
| Event generation | 0.01–0.1 ms | Application |
| Serialization | 0.01–0.1 ms | Format-dependent |
| Enqueue (async) | 0.1–2 ms | Kafka/Redis |
| Consumer processing | 0.5–5 ms | Deserialize + enrich |
| Storage write | 1–10 ms | DB/Elasticsearch |
| SIEM indexing | 1–10 s | Searchable latency |
| **Total (async)** | **2–10 ms** | Event → stored |
| **Total (sync)** | **0.5–5 ms** | Event → committed |

---

## 5. ULL Optimization Strategies

| Strategy | Applicability | Expected Savings |
|----------|--------------|-----------------|
| Async audit logging | All non-critical audit | Eliminates from request path |
| Protobuf/MessagePack serialization | High-volume audit | 2–5x faster than JSON |
| Batched log shipping | Kafka/remote SIEM | Amortize network cost |
| Ed25519 for log signing | Integrity-critical | 5–10x faster than ECDSA |
| Hash chain batching | Sequential integrity | Amortize hash computation |
| Pre-allocated log buffers | All audit | Reduce allocation overhead |
| Ring buffer + background flush | Local audit | Non-blocking writes |
| Sampling (non-critical events) | High-volume audit | Reduce volume by 90%+ |
| Edge aggregation | Distributed audit | Batch before shipping |
| Separate audit thread/core | All audit | Isolate from request path |

---

## 6. Measurement Checklist

- [ ] Audit event serialization latency (JSON, Protobuf, CEF)
- [ ] Synchronous audit write latency (local disk, O_SYNC)
- [ ] Asynchronous audit enqueue latency (Kafka, Redis)
- [ ] End-to-end audit pipeline latency (event → queryable)
- [ ] Hash chain computation latency (SHA-256, HMAC)
- [ ] Digital signature latency (Ed25519, ECDSA)
- [ ] Merkle tree build and verification latency
- [ ] Audit log shipping latency (syslog, SIEM API)
- [ ] Audit middleware overhead (p50, p99, p999)
- [ ] Audit volume impact on request latency
- [ ] Cold vs. warm audit buffer comparison
- [ ] Concurrent audit throughput
- [ ] Audit log storage I/O overhead
- [ ] Compliance-specific format overhead (PCI, HIPAA)
