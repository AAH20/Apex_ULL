# IOPS (Input/Output Operations Per Second)

**Definition:** The number of read or write operations a storage system can perform per second. IOPS is the primary metric for storage performance in ULL systems.

---

## 1. Measurement Methodology

### 1.1 IOPS Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Random Read IOPS** | Read from random locations | Database lookups, order book queries |
| **Random Write IOPS** | Write to random locations | Logging, order persistence |
| **Sequential Read IOPS** | Read from contiguous locations | Market data replay, backtesting |
| **Sequential Write IOPS** | Write to contiguous locations | Log streaming, tick data capture |
| **Mixed IOPS** | Combination of read/write | Realistic workloads |

### 1.2 Block Size Impact

| Block Size | Typical IOPS | Typical Bandwidth | Use Case |
|-----------|-------------|-------------------|----------|
| 4 KB | 100K–1M | 0.4–4 GB/s | Database, small records |
| 8 KB | 80K–800K | 0.6–6.4 GB/s | Database, medium records |
| 16 KB | 60K–600K | 1–10 GB/s | Database, large records |
| 32 KB | 40K–400K | 1.3–13 GB/s | File system, large I/O |
| 64 KB | 20K–200K | 1.3–13 GB/s | File system, streaming |
| 128 KB | 10K–100K | 1.3–13 GB/s | Streaming, backup |
| 1 MB | 1K–10K | 1–10 GB/s | Large file transfer |

**Key insight:** IOPS and bandwidth are related: `Bandwidth = IOPS × Block_size`. Small blocks → high IOPS, low bandwidth. Large blocks → low IOPS, high bandwidth.

### 1.3 Measurement Approaches

| Method | Description | Accuracy | Use Case |
|--------|-------------|----------|----------|
| **`fio`** | Flexible I/O tester; industry standard | Very high | General storage benchmarking |
| **`io_uring`** | Linux async I/O interface | High | Modern Linux storage |
| **`SPDK`** | User-space NVMe driver | Very high | Kernel-bypass storage |
| **`dd`** | Simple sequential I/O | Low | Quick sanity check |
| **`ioping`** | Latency-focused I/O tool | High | Latency measurement |
| **Custom NVMe testbench** | Direct NVMe register access | Very high | NVMe device validation |

### 1.4 Standard Test Configuration (fio)

```bash
# Random read test
fio --name=randread --ioengine=io_uring --iodepth=32 \
    --rw=randread --bs=4k --direct=1 --size=10G \
    --numjobs=4 --runtime=60 --group_reporting

# Random write test
fio --name=randwrite --ioengine=io_uring --iodepth=32 \
    --rw=randwrite --bs=4k --direct=1 --size=10G \
    --numjobs=4 --runtime=60 --group_reporting

# Mixed read/write (70/30)
fio --name=mixed --ioengine=io_uring --iodepth=32 \
    --rw=randrw --rwmixread=70 --bs=4k --direct=1 \
    --size=10G --numjobs=4 --runtime=60 --group_reporting
```

### 1.5 Key Formulas

```
IOPS = Total I/O operations / Measurement window (s)

Bandwidth (GB/s) = IOPS × Block_size / 1,000,000,000

IOPS per core = Total IOPS / Active CPU cores

Queue depth = IOPS × Latency (Little's Law)
  QD = 100,000 IOPS × 100 μs = 10

Effective IOPS = IOPS × (1 - error_rate)
```

---

## 2. Benchmark Standards

### 2.1 NVMe SSDs

| Device | Random Read IOPS (4K) | Random Write IOPS (4K) | Latency (read) | Source |
|--------|----------------------|------------------------|----------------|--------|
| Samsung 990 Pro | 1.4M | 1.55M | ~50 μs | Samsung specs |
| WD Black SN850X | 1.2M | 1.1M | ~55 μs | WD specs |
| Intel Optane P5800X | 1.5M | 1.5M | ~10 μs | Intel specs (discontinued) |
| Kioxia CM7 | 2.5M | 1.4M | ~40 μs | Kioxia specs |
| Samsung PM1733 | 2.5M | 1.5M | ~40 μs | Samsung specs |
| Kioxia CD8 | 2.4M | 1.2M | ~45 μs | Kioxia specs |
| Solidigm D7-P5520 | 1.9M | 1.0M | ~50 μs | Solidigm specs |

### 2.2 NVMe-oF (Network Storage)

| Transport | IOPS (4K random read) | Latency | Source |
|-----------|----------------------|---------|--------|
| NVMe-oF TCP | 34,543 (QD=1) | 28.44 μs | SPDK 22.01 report |
| NVMe-oF TCP | 100K–500K (QD=32) | 50–100 μs | SPDK benchmarks |
| NVMe-oF RDMA | 500K–2M (QD=32) | 10–30 μs | SPDK benchmarks |
| NVMe-oF RDMA (Intel IPU) | Up to 6M (4K) | ~20 μs | Intel IPU specs |

### 2.3 Storage Comparison by Technology

| Technology | IOPS (4K random) | Latency | Cost/GB | Use Case |
|-----------|-----------------|---------|---------|----------|
| SATA SSD | 100K–200K | 50–100 μs | $0.05–0.10 | Budget storage |
| NVMe SSD (Gen4) | 1M–2.5M | 20–50 μs | $0.08–0.15 | High-performance |
| NVMe SSD (Gen5) | 2M–5M | 10–30 μs | $0.15–0.30 | Cutting-edge |
| Intel Optane (3D XPoint) | 1.5M–2.5M | 5–10 μs | $0.50–1.00 | ULL (discontinued) |
| DRAM (persistent memory) | 10M–100M | 100–300 ns | $5–10 | Persistent memory |
| DRAM (volatile) | 100M–1B | 50–100 ns | $10–20 | Main memory |

### 2.4 SPDK vs. Linux Kernel NVMe-oF

| Metric | SPDK | Linux Kernel | Improvement |
|--------|------|-------------|-------------|
| Avg. latency (target) | — | — | Up to 5% lower |
| Avg. latency (initiator) | — | — | Up to 15% lower |
| IOPS/core | — | — | Up to 1.47× |
| p99 latency | 56.7 μs | — | — |
| p99.999 latency | 165.5 μs | — | — |

---

## 3. Industry Averages

### 3.1 By Workload Type

| Workload | IOPS | Block Size | Latency Target | Notes |
|----------|------|-----------|----------------|-------|
| Database (OLTP) | 100K–1M | 8–16 KB | <1 ms | Random read/write |
| Database (OLAP) | 10K–100K | 64–128 KB | <10 ms | Sequential scan |
| Log streaming | 50K–500K | 4–64 KB | <10 ms | Sequential write |
| Tick data capture | 100K–1M | 4–16 KB | <1 ms | Sequential write |
| Order persistence | 50K–500K | 4–8 KB | <1 ms | Random write |
| Market data replay | 10K–100K | 64–128 KB | <10 ms | Sequential read |
| Checkpointing | 10K–100K | 1–4 MB | <100 ms | Large sequential write |

### 3.2 By Storage Tier

| Tier | IOPS | Latency | Cost/GB/month | Use Case |
|------|------|---------|---------------|----------|
| Tier 0 (DRAM) | 100M–1B | 50–100 ns | $10–20 | Hot data, order books |
| Tier 1 (Optane/PM) | 10M–100M | 100–300 ns | $5–10 | Warm data, persistent |
| Tier 2 (NVMe Gen5) | 2M–5M | 10–30 μs | $0.15–0.30 | Hot storage |
| Tier 3 (NVMe Gen4) | 1M–2.5M | 20–50 μs | $0.08–0.15 | Warm storage |
| Tier 4 (SATA SSD) | 100K–200K | 50–100 μs | $0.05–0.10 | Cold storage |
| Tier 5 (HDD) | 100–200 | 5–10 ms | $0.02–0.04 | Archive |

### 3.3 Scaling by Queue Depth

```
QD=1:    10K–50K IOPS (latency-bound)
QD=8:    50K–200K IOPS
QD=32:   200K–1M IOPS
QD=128:  500K–2M IOPS
QD=512:  1M–5M IOPS (hardware limit)
```

**Little's Law:** `IOPS = Queue_Depth / Latency`
- At QD=32 and 100 μs latency: IOPS = 32 / 0.0001 = 320,000
- At QD=32 and 10 μs latency: IOPS = 32 / 0.00001 = 3,200,000

---

## 4. Factors Affecting IOPS

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Block size | Smaller blocks → higher IOPS, lower bandwidth | Match block size to workload |
| Queue depth | Higher QD → higher IOPS (up to hardware limit) | Use io_uring, SPDK |
| Read/write mix | Writes typically slower than reads | Use write-back cache, battery-backed |
| Random vs sequential | Sequential → much higher IOPS | Use SSDs for random, HDDs for sequential |
| PCIe generation | Gen5 = 2× Gen4 bandwidth | Use Gen5 NVMe |
| Kernel overhead | Kernel stack adds 5–15 μs | Use SPDK, io_uring |
| Device controller | NVMe controller quality matters | Use enterprise-grade SSDs |
| Over-provisioning | More spare area → better performance | Reserve 10–20% spare area |
| Write amplification | Higher writes → lower effective IOPS | Use large blocks, sequential writes |

---

## 5. IOPS in ULL Systems

### 5.1 HFT Storage Requirements

| Component | IOPS Required | Block Size | Latency Target | Notes |
|-----------|-------------|-----------|----------------|-------|
| Tick database (Kdb+) | 100K–1M | 4–16 KB | <1 ms | Write-heavy |
| Order log | 50K–500K | 4–8 KB | <1 ms | Sequential write |
| Position store | 10K–100K | 4–8 KB | <1 ms | Random read/write |
| Risk checkpoint | 10K–100K | 1–4 MB | <100 ms | Periodic large write |
| Market data replay | 10K–100K | 64–128 KB | <10 ms | Sequential read |

### 5.2 Payment System Storage Requirements

| Component | IOPS Required | Block Size | Latency Target | Notes |
|-----------|-------------|-----------|----------------|-------|
| Transaction log | 50K–500K | 4–8 KB | <10 ms | Sequential write |
| Account balance | 100K–1M | 4–8 KB | <1 ms | Random read/write |
| Fraud detection | 10K–100K | 4–16 KB | <10 ms | Random read |
| Settlement batch | 1K–10K | 64–128 KB | <100 ms | Sequential write |

---

## 6. Measurement Tools

| Tool | Domain | Output |
|------|--------|--------|
| `fio` | General storage | IOPS, bandwidth, latency percentiles |
| `io_uring` | Linux async IOPS | IOPS, latency |
| `SPDK` | Kernel-bypass NVMe | IOPS, latency, CPU utilization |
| `ioping` | Latency measurement | Latency percentiles |
| `nvme-cli` | NVMe management | Device info, SMART data |
| `perf` | System profiling | I/O syscalls, block layer stats |
| `iostat` | System I/O stats | IOPS, bandwidth, utilization |
| `blktrace` | Block layer tracing | Detailed I/O trace |

---

## 7. Reporting Template

```yaml
metric: iops
system: <system_name>
date: <ISO 8601>
configuration:
  block_size_bytes: <N>
  read_write_mix: <read|write|mixed>
  queue_depth: <N>
  num_jobs: <N>
  duration_seconds: <N>
  storage_type: <sata_ssd|nvme_gen4|nvme_gen5|optane|dram>
  interface: <sata|pcie|nvme_of_tcp|nvme_of_rdma>
results:
  random_read_iops: <N>
  random_write_iops: <N>
  sequential_read_iops: <N>
  sequential_write_iops: <N>
  bandwidth_gbps: <N>
  p50_latency_us: <N>
  p99_latency_us: <N>
  p999_latency_us: <N>
  cpu_utilization_pct: <N>
notes: <any anomalies or observations>
```

---

*Sources: Samsung/WD/Intel/Kioxia/Solidigm product specifications, SPDK 22.01 performance report, Intel IPU E2100 product brief, fio documentation.*
