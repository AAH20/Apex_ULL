# ULL Reliability Benchmark

**Project:** ultra-low-latency-infra  
**Scope:** Fault tolerance, error rate, data loss, RPO, RTO  
**Date:** September 2026

---

## Overview

This benchmark defines how to measure, validate, and enforce reliability in ultra-low-latency (ULL) infrastructure. ULL systems operate at nanosecond-to-microsecond timescales where traditional reliability mechanisms (retries, consensus, checkpointing) introduce unacceptable latency. This document specifies measurement methodologies, hardware requirements, and software requirements for each reliability dimension.

---

## Benchmark Dimensions

| # | Dimension | Target | Unit |
|---|-----------|--------|------|
| 1 | Fault Tolerance | 99.999% (five-nines) | Availability |
| 2 | Error Rate | <1 error per 10⁹ operations | Errors/op |
| 3 | Data Loss | Zero (synchronous) / <1s (async) | Seconds of data |
| 4 | Recovery Point Objective (RPO) | 0 (sync) / <1s (async) | Seconds |
| 5 | Recovery Time Objective (RTO) | <100 ms (hot standby) / <5 s (cold) | Seconds |

---

## 1. Fault Tolerance

### Definition
The system's ability to continue operating correctly despite component failures (network, compute, storage, power).

### Measurement Methodology

#### 1.1 Chaos Engineering for ULL
- **Tool:** Custom fault-injection framework (FPGA-based for sub-microsecond precision)
- **Method:** Inject faults at deterministic points in the data path; measure detection + recovery time
- **Fault types:**
  - Network link failure (fiber cut, switch port down)
  - Compute node failure (CPU crash, FPGA bitstream corruption)
  - Storage failure (NVMe SSD failure, RAID controller failure)
  - Power failure (PSU failure, facility power loss)
  - Clock drift (PTP grandmaster failure, oscillator degradation)

#### 1.2 Availability Calculation
```
Availability = (Total Time - Downtime) / Total Time × 100%
```
- Measure over rolling 30-day windows
- Downtime = sum of all unplanned outages >1 second
- Planned maintenance excluded (max 4 hours/month)

#### 1.3 Fault Detection Latency
- **Metric:** Time from fault occurrence to detection
- **Target:** <10 ms for network faults, <1 ms for FPGA-internal faults
- **Measurement:** Hardware timestamped event logs (PTP-synchronized)

#### 1.4 Failover Latency
- **Metric:** Time from detection to traffic rerouted
- **Target:** <100 ms (hot standby), <5 s (cold standby)
- **Measurement:** Packet capture at ingress/egress with hardware timestamps

### Hardware Requirements

| Component | Redundancy | Failover Mechanism | Latency Impact |
|-----------|-----------|-------------------|----------------|
| Network links | 2× diverse paths | BFD + ECMP | <50 ms detection |
| FPGA feed handlers | Active-active | Heartbeat + state sync | <1 ms |
| Compute nodes | N+1 | Kubernetes + custom scheduler | <100 ms |
| Storage (NVMe) | RAID-10 + replica | NVMe-oF multipath | <10 ms |
| Power | 2N UPS + generator | ATS switchover | 0 ms (UPS ride-through) |
| Clock (PTP) | 3× grandmasters | BMCA algorithm | <1 μs drift |

### Software Requirements

| Layer | Mechanism | Target |
|-------|-----------|--------|
| Network | BFD (Bidirectional Forwarding Detection) | <3 ms detection |
| Network | BGP/OSPF fast convergence | <50 ms reroute |
| Compute | Health checks (gRPC + custom) | <10 ms interval |
| Compute | Hot standby with shared state | <100 ms failover |
| Storage | NVMe-oF multipath | <10 ms path switch |
| Application | Circuit breaker pattern | <1 ms trip |
| Application | Retry with exponential backoff | Configurable |

---

## 2. Error Rate

### Definition
The frequency of incorrect operations (wrong output, dropped message, corrupted data) per unit of work.

### Measurement Methodology

#### 2.1 End-to-End Error Rate
```
Error Rate = (Failed Operations / Total Operations) × 100%
```
- **Operation definition:** One complete tick-to-trade cycle (market data in → order out)
- **Measurement window:** Rolling 1-hour and 24-hour
- **Error classification:**
  - **Critical:** Wrong order sent, order lost, duplicate order
  - **Major:** Delayed order (>100 μs SLA breach), partial fill
  - **Minor:** Logging error, metrics gap, non-critical warning

#### 2.2 Bit Error Rate (BER) — Network Layer
- **Target:** <10⁻¹² (fiber), <10⁻⁹ (wireless/microwave)
- **Measurement:** RFC 2544 test frames + hardware BER testers
- **Method:** Inject test frames during low-traffic periods; count errored bits

#### 2.3 FPGA Logic Error Rate
- **Target:** <1 error per 10¹² clock cycles (SEU rate)
- **Measurement:** CRC/ECC error counters on FPGA config memory
- **Method:** Monitor SEM (Soft Error Mitigation) IP error logs

#### 2.4 Software Error Rate
- **Target:** <1 unhandled exception per 10⁹ function calls
- **Measurement:** Structured logging + error aggregation (ELK/Loki)
- **Method:** Tag every operation with unique ID; trace through pipeline

### Hardware Requirements

| Component | Error Detection | Correction | Target BER |
|-----------|----------------|------------|------------|
| Network (fiber) | FEC (RS-FEC) | Automatic | <10⁻¹² |
| Network (wireless) | LDPC FEC | Automatic | <10⁻⁹ |
| FPGA config | ECC + scrubbing | Auto-reconfig | <10⁻¹² |
| DRAM | ECC (SECDED) | Automatic | <10⁻¹⁵ |
| NVMe SSD | End-to-end CRC | Automatic | <10⁻¹⁵ |
| CPU | Machine Check Arch. | N/A (detect only) | N/A |

### Software Requirements

| Layer | Mechanism | Target |
|-------|-----------|--------|
| Messaging | Sequence numbers + ACKs | Zero loss |
| Messaging | CRC-32C per packet | <10⁻⁹ undetected |
| State machine | Invariant checks | <10⁻⁶ violation |
| Order path | Idempotency keys | Zero duplicates |
| Logging | Async + ring buffer | Zero logging loss |
| Monitoring | Heartbeat + watchdog | <10 ms detection |

---

## 3. Data Loss

### Definition
The amount of data (market data, order state, trade history) that becomes permanently unavailable due to a failure.

### Measurement Methodology

#### 3.1 Data Loss Window
```
Data Loss = Time between last confirmed durable write and failure point
```
- **Synchronous replication:** Zero data loss (write confirmed only after replica ACK)
- **Asynchronous replication:** Bounded by replication lag (target <1 second)

#### 3.2 Recovery Point Verification
- **Method:** After recovery, compare recovered state against known-good checkpoint
- **Metric:** Number of records/operations lost
- **Target:** Zero for synchronous, <1000 records for asynchronous

#### 3.3 Data Integrity Verification
- **Method:** Periodic checksum verification of all persisted state
- **Frequency:** Continuous (background scrubbing)
- **Metric:** Time to detect corruption, time to repair

#### 3.4 Transaction Log Completeness
- **Method:** Verify WAL (Write-Ahead Log) continuity via sequence numbers
- **Metric:** Number of gaps in WAL sequence
- **Target:** Zero gaps

### Hardware Requirements

| Component | Redundancy | Data Protection | Loss Window |
|-----------|-----------|-----------------|-------------|
| Primary storage | RAID-10 | Mirroring | 0 (sync) |
| Replica storage | Cross-site | Sync replication | 0 (sync) |
| WAL | 3× distributed | Raft consensus | 0 (majority) |
| Market data | 2× capture | FPGA tap + software | <1 μs |
| Order state | In-memory + NVMe | Checkpoint + WAL | <100 ms |

### Software Requirements

| Layer | Mechanism | Target |
|-------|-----------|--------|
| Replication | Synchronous (Raft/Paxos) | Zero loss |
| Replication | Asynchronous (log shipping) | <1s lag |
| Checkpointing | Incremental + full | <100 ms interval |
| WAL | Group commit + fsync | <1 ms durability |
| Backup | Continuous + point-in-time | <1s RPO |
| Integrity | Merkle tree verification | <1 min detection |

---

## 4. Recovery Point Objective (RPO)

### Definition
The maximum acceptable amount of data loss measured in time. RPO = the point in time to which data must be recovered.

### Measurement Methodology

#### 4.1 RPO Verification
```
RPO = Time of failure - Time of last recoverable state
```
- **Method:** Simulate failure; measure time between last durable write and failure
- **Frequency:** Monthly chaos test
- **Target:** 0 seconds (synchronous), <1 second (asynchronous)

#### 4.2 Replication Lag Measurement
- **Metric:** Time between primary write and replica acknowledgment
- **Measurement:** Hardware-timestamped heartbeat messages
- **Target:** <1 ms (sync), <1 s (async)

#### 4.3 Checkpoint Interval
- **Metric:** Time between consistent state snapshots
- **Measurement:** Checkpoint timestamp logs
- **Target:** <100 ms (incremental), <1 min (full)

#### 4.4 WAL Archival Lag
- **Metric:** Time between WAL entry creation and archival to durable storage
- **Measurement:** WAL sequence number vs. archived sequence number
- **Target:** <1 second

### Hardware Requirements

| Component | Mechanism | RPO Target |
|-----------|-----------|------------|
| NVMe storage | NVMe-oF sync replication | 0 |
| DRAM | Persistent memory (Intel Optane) | 0 |
| FPGA state | Dual-bitstream + state mirror | 0 |
| Network | Dual-path + tap | 0 |
| Cross-site | Dark fiber + sync replication | 0 |
| Backup | Continuous archival | <1s |

### Software Requirements

| Layer | Mechanism | RPO Target |
|-------|-----------|------------|
| Database | Synchronous replication | 0 |
| Messaging | Replicated log (Kafka/Raft) | 0 |
| State store | Raft consensus | 0 |
| File system | Distributed (Ceph/Gluster) | 0 |
| Object storage | Cross-region replication | <1s |
| Cache | Write-through + replication | 0 |

---

## 5. Recovery Time Objective (RTO)

### Definition
The maximum acceptable time to restore service after a failure. RTO = time from failure detection to full service restoration.

### Measurement Methodology

#### 5.1 RTO Verification
```
RTO = Time of service restoration - Time of failure detection
```
- **Method:** Inject fault; measure time until service passes health check
- **Frequency:** Weekly automated test, monthly full drill
- **Target:** <100 ms (hot standby), <5 s (cold standby)

#### 5.2 Component Recovery Times

| Component | Detection | Failover | Total RTO |
|-----------|-----------|----------|-----------|
| Network link | <3 ms (BFD) | <50 ms (ECMP) | <53 ms |
| FPGA feed handler | <1 ms (heartbeat) | <10 ms (state sync) | <11 ms |
| Compute node | <10 ms (health check) | <100 ms (K8s) | <110 ms |
| Storage path | <10 ms (NVMe-oF) | <10 ms (multipath) | <20 ms |
| Full node | <10 ms | <500 ms (VM restart) | <510 ms |
| Cross-site | <100 ms | <5 s (DNS + warm) | <5.1 s |

#### 5.3 State Reconstruction Time
- **Metric:** Time to rebuild in-memory state from checkpoint + WAL
- **Measurement:** Timestamp at recovery start vs. first successful operation
- **Target:** <50 ms (incremental), <5 s (full rebuild)

#### 5.4 Service Readiness Verification
- **Method:** Automated health check (synthetic transaction)
- **Target:** Pass within RTO window
- **Frequency:** Every 1 second during recovery

### Hardware Requirements

| Component | Redundancy | Recovery Mechanism | RTO Target |
|-----------|-----------|-------------------|------------|
| Network | 2× diverse | BFD + ECMP | <50 ms |
| FPGA | Active-active | State sync | <10 ms |
| Compute | N+1 hot standby | Pre-warmed VM/container | <100 ms |
| Storage | NVMe-oF multipath | Path failover | <10 ms |
| Cross-site | Warm standby | DNS + state transfer | <5 s |
| Power | 2N + generator | ATS + UPS | 0 ms |

### Software Requirements

| Layer | Mechanism | RTO Target |
|-------|-----------|------------|
| Load balancer | Health-based routing | <10 ms |
| Service mesh | Automatic failover | <50 ms |
| Database | Replica promotion | <100 ms |
| Cache | Pre-warmed replica | <10 ms |
| Queue | Replicated partition | <50 ms |
| DNS | Health-checked records | <5 s |

---

## Benchmark Execution Plan

### Phase 1: Baseline Measurement (Week 1-2)
1. Deploy monitoring stack (Prometheus + Grafana + custom exporters)
2. Instrument all components with hardware timestamping
3. Run baseline measurements for all 5 dimensions
4. Document current-state metrics

### Phase 2: Fault Injection Testing (Week 3-4)
1. Deploy chaos engineering framework
2. Execute fault scenarios for each dimension
3. Measure detection, failover, and recovery times
4. Identify gaps and bottlenecks

### Phase 3: Optimization (Week 5-6)
1. Address gaps identified in Phase 2
2. Tune detection intervals and failover thresholds
3. Re-run fault injection tests
4. Validate all targets met

### Phase 4: Continuous Validation (Ongoing)
1. Weekly automated chaos tests
2. Monthly full disaster recovery drills
3. Quarterly benchmark review and target adjustment

---

## Tooling Requirements

| Category | Tool | Purpose |
|----------|------|---------|
| Monitoring | Prometheus + Grafana | Metrics collection and visualization |
| Logging | Loki / ELK | Centralized log aggregation |
| Tracing | Jaeger / Tempo | Distributed request tracing |
| Chaos | Custom FPGA framework | Sub-microsecond fault injection |
| Testing | RFC 2544 / Ixia | Network BER and latency testing |
| Health | Custom synthetic transactions | Service readiness verification |
| Time | PTP (linuxptp) | Sub-microsecond clock synchronization |

---

## Success Criteria

| Dimension | Target | Measurement |
|-----------|--------|-------------|
| Fault Tolerance | 99.999% availability | 30-day rolling |
| Error Rate | <1 error per 10⁹ ops | 24-hour rolling |
| Data Loss | Zero (sync) / <1s (async) | Per-fault test |
| RPO | 0s (sync) / <1s (async) | Monthly test |
| RTO | <100ms (hot) / <5s (cold) | Weekly test |

---

## References

- [FPGA Technologies Report](../../reports/fpga-technologies.md)
- [Network Technologies Report](../../reports/network-technologies.md)
- [HFT Firms Report](../../reports/hft-firms.md)
- IEEE 1588-2019 (PTP)
- RFC 2544 (Network Benchmarking)
- NIST SP 800-34 (Contingency Planning)
