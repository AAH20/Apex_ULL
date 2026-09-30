# IOPS Throughput Benchmark

## Overview

Measures storage I/O operations per second for ultra-low-latency systems. Covers NVMe SSDs, persistent memory, and CXL-attached storage. Critical for trade persistence, market data capture, and recovery.

## Measurement Methodology

### What to Measure

- **Random read IOPS**: 4KB random reads (most common workload)
- **Random write IOPS**: 4KB random writes (trade persistence)
- **Sequential read IOPS**: 1MB sequential reads (market data replay)
- **Sequential write IOPS**: 1MB sequential writes (market data capture)
- **Mixed IOPS**: 70/30 read/write mix (realistic workload)

### Measurement Protocol

1. **Warm-up**: 30 seconds to populate caches and reach steady state
2. **Measurement window**: 60 seconds at target queue depth
3. **Queue depths**: 1, 8, 32, 64, 128 (measure scaling)
4. **Repeat**: 5 iterations, report median

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Block size | 4KB (random), 1MB (sequential) | Standard storage test sizes |
| Queue depth | 1–128 | Measure latency vs throughput tradeoff |
| Access pattern | Random, sequential, mixed | Realistic workloads |
| Data pattern | Incompressible | Prevent compression artifacts |
| File system | None (raw device) or XFS | Bypass FS overhead for raw test |

### Common Pitfalls

- **Measuring cached IOPS**: Must use O_DIRECT to bypass page cache
- **Not testing at production queue depth**: QD=1 is not representative
- **Ignoring write amplification**: SSDs perform differently under sustained writes
- **Not testing steady state**: SSD performance degrades as NAND fills
- **Ignoring NUMA effects**: Storage device must be NUMA-local to CPU

## Hardware Requirements

### Minimum (Entry ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 8 cores @ 3.0 GHz | Intel Xeon W-3400 |
| Storage | NVMe Gen4 SSD | 7 GB/s sequential, 1M IOPS |
| Memory | 64 GB DDR5 | For caching and buffering |
| OS | Linux 6.x | Native NVMe driver |

### Recommended (Mid ULL)

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 32 cores @ 3.5 GHz | AMD EPYC 9654 |
| Storage | NVMe Gen5 SSD | 14 GB/s sequential, 2M+ IOPS |
| Memory | 256 GB DDR5-5600 | Large cache for write buffering |
| HBA | PCIe Gen5 x16 | Full bandwidth to NVMe |
| OS | Linux 6.x with SPDK | Kernel bypass for storage |

### Extreme ULL

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | 64+ cores @ 4.0 GHz | AMD EPYC 9754 |
| Storage | CXL-attached persistent memory | Sub-µs access latency |
| Memory | 1 TB DDR5 + HBM | All state in memory |
| HBA | CXL 2.0 switch | Memory-semantic access |
| OS | Linux 6.x with SPDK | Full kernel bypass |

## Software Requirements

### OS & Kernel

```bash
# Kernel parameters for storage performance
echo "isolcpus=2-15 nohz_full=2-15 rcu_nocbs=2-15" >> /boot/cmdline
echo "intel_pstate=disable processor.max_cstate=1" >> /boot/cmdline
echo "vm.dirty_ratio=5 vm.dirty_background_ratio=2" >> /etc/sysctl.conf
echo "vm.swappiness=1" >> /etc/sysctl.conf
```

### Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| SPDK | 24.07+ | Kernel bypass NVMe access |
| libaio | 0.3.113+ | Async I/O (fallback) |
| io_uring | Kernel 6.x+ | Async I/O (modern alternative) |
| nvme-cli | 2.x+ | NVMe management and testing |
| fio | 3.36+ | Reference benchmark tool |

### Build Flags

```bash
CFLAGS="-O3 -march=native -mtune=native -flto -fno-semantic-interposition"
CFLAGS="$CFLAGS -DNDEBUG -D_FORTIFY_SOURCE=0"
CFLAGS="$CFLAGS -fomit-frame-pointer -funroll-loops"
```

## Benchmark Code

### Reference Implementation (C with SPDK)

```c
// iops_spdk.c
// SPDK-based NVMe IOPS benchmark

#include <spdk/stdinc.h>
#include <spdk/nvme.h>
#include <spdk/env.h>
#include <spdk/thread.h>
#include <spdk/log.h>
#include <spdk/string.h>
#include <spdk/util.h>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>

#define BLOCK_SIZE 4096
#define QUEUE_DEPTH 32
#define MEASURE_DURATION_SEC 60
#define WARMUP_DURATION_SEC 30

struct ns_entry {
    struct spdk_nvme_ctrlr *ctrlr;
    struct spdk_nvme_ns *ns;
    struct spdk_nvme_qpair *qpair;
    uint32_t block_size;
    uint64_t num_blocks;
};

struct worker_ctx {
    struct ns_entry *ns;
    std::atomic<uint64_t> ops_completed{0};
    std::atomic<uint64_t> ops_submitted{0};
    std::atomic<uint64_t> errors{0};
    volatile bool running = false;
};

static struct ns_entry g_ns;
static struct worker_ctx g_workers[32];
static volatile bool g_running = false;

static void io_complete(void *arg, const struct spdk_nvme_cpl *cpl) {
    worker_ctx *ctx = (worker_ctx *)arg;
    if (spdk_nvme_cpl_is_error(cpl)) {
        ctx->errors++;
    }
    ctx->ops_completed++;
}

static void *worker_thread(void *arg) {
    worker_ctx *ctx = (worker_ctx *)arg;
    uint64_t lba = 0;
    uint64_t max_lba = ctx->ns->num_blocks;
    
    // Pin to CPU core
    // (CPU pinning code omitted for brevity)
    
    while (ctx->running) {
        // Submit batch of I/Os
        for (int i = 0; i < QUEUE_DEPTH; i++) {
            uint64_t offset = (lba % max_lba) * BLOCK_SIZE;
            
            int rc = spdk_nvme_ns_cmd_read(
                ctx->ns->ns, ctx->ns->qpair,
                ctx->ns->ctrlr,  // buffer
                lba, 1,  // LBA, count
                io_complete, ctx, 0);
            
            if (rc == 0) {
                ctx->ops_submitted++;
                lba += BLOCK_SIZE / ctx->ns->block_size;
            } else {
                ctx->errors++;
            }
        }
        
        // Poll for completions
        while (ctx->ops_completed < ctx->ops_submitted) {
            spdk_nvme_qpair_process_completions(ctx->ns->qpair, 0);
        }
    }
    
    return NULL;
}

int main(int argc, char **argv) {
    // Initialize SPDK environment
    struct spdk_env_opts opts;
    spdk_env_opts_init(&opts);
    opts.name = "iops_benchmark";
    opts.core_mask = "0xFFFFFFFE";  // Use cores 1-31
    spdk_env_init(&opts);
    
    // Probe and attach NVMe controller
    // (Controller probe code omitted for brevity)
    
    // Create I/O queue pair
    struct spdk_nvme_io_qpair_opts qpair_opts;
    spdk_nvme_ctrlr_get_default_io_qpair_opts(g_ns.ctrlr, &qpair_opts, sizeof(qpair_opts));
    qpair_opts.io_queue_requests = QUEUE_DEPTH;
    g_ns.qpair = spdk_nvme_ctrlr_alloc_io_qpair(g_ns.ctrlr, &qpair_opts, sizeof(qpair_opts));
    
    // Get namespace info
    g_ns.block_size = spdk_nvme_ns_get_sector_size(g_ns.ns);
    g_ns.num_blocks = spdk_nvme_ns_get_size(g_ns.ns);
    
    printf("NVMe IOPS Benchmark\n");
    printf("Block size: %u, Num blocks: %lu\n", g_ns.block_size, g_ns.num_blocks);
    printf("Queue depth: %d\n", QUEUE_DEPTH);
    
    // Warm-up
    printf("Warming up for %d seconds...\n", WARMUP_DURATION_SEC);
    g_running = true;
    sleep(WARMUP_DURATION_SEC);
    
    // Reset stats
    for (int i = 0; i < 32; i++) {
        g_workers[i].ops_completed = 0;
        g_workers[i].ops_submitted = 0;
        g_workers[i].errors = 0;
    }
    
    // Measurement
    printf("Measuring for %d seconds...\n", MEASURE_DURATION_SEC);
    auto start = std::chrono::high_resolution_clock::now();
    sleep(MEASURE_DURATION_SEC);
    g_running = false;
    auto end = std::chrono::high_resolution_clock::now();
    
    double duration = std::chrono::duration<double>(end - start).count();
    
    // Aggregate results
    uint64_t total_ops = 0, total_errors = 0;
    for (int i = 0; i < 32; i++) {
        total_ops += g_workers[i].ops_completed.load();
        total_errors += g_workers[i].errors.load();
    }
    
    printf("\n=== IOPS Benchmark Results ===\n");
    printf("Duration:           %.1f seconds\n", duration);
    printf("Total I/O ops:      %lu\n", total_ops);
    printf("IOPS:               %.2f M\n", total_ops / duration / 1e6);
    printf("Throughput:         %.2f GB/s\n", total_ops * BLOCK_SIZE / duration / 1e9);
    printf("Errors:             %lu\n", total_errors);
    
    // Cleanup
    spdk_nvme_ctrlr_free_io_qpair(g_ns.qpair);
    spdk_env_cleanup();
    
    return 0;
}
```

### fio Configuration (Reference)

```ini
; iops_benchmark.fio
; Run: fio iops_benchmark.fio

[global]
ioengine=io_uring
direct=1
buffered=0
size=100%
group_reporting=1
runtime=60
time_based=1
ramp_time=30
filename=/dev/nvme0n1

[random-read-4k]
stonewall
rw=randread
bs=4k
iodepth=32
numjobs=8

[random-write-4k]
stonewall
rw=randwrite
bs=4k
iodepth=32
numjobs=8

[sequential-read-1m]
stonewall
rw=read
bs=1m
iodepth=8
numjobs=4

[sequential-write-1m]
stonewall
rw=write
bs=1m
iodepth=8
numjobs=4

[mixed-70-30]
stonewall
rw=randrw
rwmixread=70
bs=4k
iodepth=32
numjobs=8
```

## Expected Results

### Production ULL System Reference Numbers

| Storage Type | Random Read IOPS | Random Write IOPS | Sequential BW | Latency (p99) |
|-------------|-----------------|-------------------|---------------|---------------|
| NVMe Gen4 SSD | 1.0–1.5M | 500K–1M | 7 GB/s | 50–100 µs |
| NVMe Gen5 SSD | 2.0–3.0M | 1.0–2.0M | 14 GB/s | 20–50 µs |
| CXL Persistent Memory | 5.0M+ | 3.0M+ | 30+ GB/s | 1–5 µs |
| Optane PMem | 2.0M+ | 1.5M+ | 10 GB/s | 1–3 µs |

### Queue Depth Scaling

| Queue Depth | Expected IOPS (Gen5) | Latency (p99) |
|-------------|---------------------|---------------|
| 1 | 50K–100K | 10–20 µs |
| 8 | 400K–800K | 20–40 µs |
| 32 | 1.5M–2.5M | 30–60 µs |
| 64 | 2.0M–3.0M | 50–100 µs |
| 128 | 2.5M–3.5M | 80–150 µs |

## Analysis

### Identifying Bottlenecks

| Symptom | Likely Cause | Remedy |
|---------|-------------|--------|
| IOPS plateaus at low QD | CPU-bound (not storage-bound) | Use SPDK, reduce per-I/O overhead |
| Write IOPS much lower than read | Write amplification | Enable TRIM, use larger blocks |
| IOPS degrades over time | SSD thermal throttling | Improve cooling, use enterprise SSDs |
| High latency at low QD | Kernel overhead | Use SPDK or io_uring |
| NUMA-related performance drop | Remote memory access | Pin to NUMA-local socket |

### Optimization Checklist

- [ ] Use O_DIRECT or SPDK to bypass kernel
- [ ] Queue depth matched to workload (32+ for throughput)
- [ ] NUMA-local storage device and CPU
- [ ] Pre-allocated I/O buffers (no malloc in hot path)
- [ ] Batch I/O submissions (16+ per syscall)
- [ ] Use io_uring or SPDK instead of libaio
- [ ] Disable CPU frequency scaling
- [ ] Enable NVMe APST ( Autonomous Power State Transition)
- [ ] Use multiple namespaces for parallel access
- [ ] Pre-allocate and pre-touch all memory buffers
