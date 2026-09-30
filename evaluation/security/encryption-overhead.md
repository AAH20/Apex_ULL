# Encryption Overhead Evaluation

## 1. Scope

Measures latency introduced by cryptographic operations in ULL infrastructure:
- **Data-in-transit**: TLS handshake, record-layer encryption, key exchange
- **Data-at-rest**: Disk encryption, database field-level encryption, backup encryption
- **Application-layer**: Message-level encryption, envelope encryption, digital signatures

---

## 2. Measurement Methodology

### 2.1 TLS / Data-in-Transit

| Phase | What to Measure | How |
|-------|----------------|-----|
| Handshake (full) | ClientHello → Finished | `openssl s_time` or `curl -w '%{time_appconnect}'` |
| Handshake (resumed) | Session ticket / PSK resumption | `openssl s_time -reconnect` |
| Key exchange | ECDHE P-256 / X25519 operation | `openssl speed ecdhp256` / micro-benchmark |
| Record encryption | AES-256-GCM / ChaCha20-Poly1305 | `openssl speed -evp aes-256-gcm` |
| Certificate verification | Chain validation + OCSP stapling | `openssl verify` timing |

**Tooling:**
```bash
# TLS handshake timing
openssl s_time -connect host:443 -new -time 30

# Cipher throughput
openssl speed -evp aes-256-gcm -bytes 1024 -seconds 10
openssl speed -evp chacha20-poly1305 -bytes 1024 -seconds 10

# ECDH key exchange
openssl speed ecdhp256 ecdhx25519
```

### 2.2 Data-at-Rest

| Phase | What to Measure | How |
|-------|----------------|-----|
| Disk encryption | dm-crypt / LUKS overhead | `fio` with/without encrypted volume |
| Field-level encryption | AES-GCM per-field encrypt/decrypt | Application micro-benchmark |
| Envelope encryption | KMS unwrap + data key decrypt | Cloud KMS client timing |
| Backup encryption | Streaming encrypt during backup | `openssl enc` pipe throughput |

**Tooling:**
```bash
# Disk encryption overhead
fio --name=randread --ioengine=libaio --iodepth=32 \
    --rw=randread --bs=4k --direct=1 --size=1G \
    --filename=/dev/mapper/encrypted --output-format=json

# Field-level encryption micro-benchmark
# (language-specific: e.g., Python cryptography, Rust ring, Go crypto/aes)
```

### 2.3 Application-Layer

| Phase | What to Measure | How |
|-------|----------------|-----|
| Message encryption | NaCl box / AES-GCM per message | Micro-benchmark with message size sweep |
| Digital signatures | Ed25519 sign/verify, ECDSA P-256 | `openssl speed ed25519 ecdsap256` |
| Envelope encryption | GenerateDataKey + Decrypt | KMS API timing |

---

## 3. Benchmark Standards

| Standard | Relevance |
|----------|-----------|
| **NIST SP 800-90B** | Entropy source validation for key generation |
| **NIST SP 800-57** | Key management lifecycle, algorithm selection |
| **RFC 8446 (TLS 1.3)** | Handshake protocol, 1-RTT resumption |
| **RFC 9180 (HPKE)** | Hybrid public key encryption standard |
| **FIPS 140-3** | Cryptographic module validation |
| **PCI DSS v4.0** | Encryption requirements for cardholder data |

---

## 4. Industry Averages

### 4.1 TLS Handshake Latency

| Scenario | Typical Latency | Notes |
|----------|----------------|-------|
| TLS 1.3 full handshake (same region) | 1–3 ms | 1-RTT, ECDHE P-256 |
| TLS 1.3 full handshake (cross-region) | 50–200 ms | Dominated by network RTT |
| TLS 1.3 session resumption (PSK) | 0.3–1 ms | 0-RTT optional |
| TLS 1.2 full handshake | 2–5 ms | 2-RTT, more round trips |
| mTLS (mutual TLS) | +0.5–2 ms | Client cert verification |

### 4.2 Symmetric Encryption Throughput

| Algorithm | Throughput (per core, AES-NI) | Throughput (software-only) |
|-----------|-------------------------------|---------------------------|
| AES-256-GCM | 3–5 GB/s | 200–500 MB/s |
| AES-128-GCM | 3.5–6 GB/s | 250–600 MB/s |
| ChaCha20-Poly1305 | 2–4 GB/s | 1.5–3 GB/s |
| AES-256-CTR + HMAC-SHA256 | 2–4 GB/s | 150–400 MB/s |

### 4.3 Asymmetric Operations

| Operation | Latency (typical) | Throughput |
|-----------|-------------------|------------|
| ECDHE P-256 key exchange | 0.3–1 ms | 1,000–3,000 ops/s |
| X25519 key exchange | 0.1–0.5 ms | 3,000–10,000 ops/s |
| Ed25519 sign | 0.05–0.2 ms | 5,000–20,000 ops/s |
| Ed25519 verify | 0.1–0.5 ms | 2,000–8,000 ops/s |
| RSA-2048 sign | 1–5 ms | 500–2,000 ops/s |
| RSA-2048 verify | 0.1–0.5 ms | 5,000–20,000 ops/s |
| RSA-2048 key generation | 50–500 ms | 2–20 ops/s |

### 4.4 Data-at-Rest Overhead

| Scenario | Overhead | Notes |
|----------|----------|-------|
| dm-crypt AES-XTS (AES-NI) | 5–15% I/O overhead | Negligible with hardware accel |
| dm-crypt AES-XTS (software) | 30–60% I/O overhead | Significant without AES-NI |
| Field-level AES-GCM per record | 0.1–1 ms | Depends on record size |
| KMS envelope encryption (unwrap) | 0.5–5 ms | Network call to KMS |
| Local key cache hit | 0.01–0.1 ms | In-memory decrypt |

---

## 5. ULL Optimization Strategies

| Strategy | Applicability | Expected Savings |
|----------|--------------|-----------------|
| TLS 1.3 + PSK resumption | All data-in-transit | 50–80% handshake latency |
| 0-RTT early data | Idempotent requests | Eliminates handshake RTT |
| AES-NI / hardware crypto | All symmetric ops | 5–10x throughput |
| Intel QAT / async crypto | High-throughput TLS | Offload from CPU |
| Session ticket caching | Repeated connections | Avoid full handshake |
| Pre-shared keys (PSK) | Internal service mesh | Skip key exchange |
| Ed25519 over RSA | Signatures | 10–50x faster sign/verify |
| Key derivation caching | Envelope encryption | Avoid repeated KMS calls |

---

## 6. Measurement Checklist

- [ ] TLS 1.3 full handshake latency (p50, p99, p999)
- [ ] TLS 1.3 resumption latency
- [ ] Symmetric cipher throughput (AES-GCM, ChaCha20-Poly1305)
- [ ] ECDH key exchange latency (P-256, X25519)
- [ ] Digital signature sign/verify latency (Ed25519, ECDSA)
- [ ] Certificate chain validation latency
- [ ] OCSP stapling check latency
- [ ] Disk encryption I/O overhead (% delta)
- [ ] Field-level encryption per-record latency
- [ ] KMS envelope encryption unwrap latency
- [ ] Cold vs. warm key cache comparison
- [ ] Network RTT contribution to handshake
