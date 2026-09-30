# Tutorial: Latency Measurement

**Domain:** System  
**Difficulty:** Beginner  
**Duration:** 1 hour

---

## Overview

In this tutorial, you'll learn how to measure latency accurately in ULL systems. We'll cover hardware timestamping, software timing, and statistical analysis.

## What You'll Build

- A high-resolution timing library
- A latency measurement tool
- Statistical analysis of results

## Prerequisites

- Linux system with `perf` access
- Basic C or Python knowledge
- `rdtsc` support (x86) or `pmccntr_el0` (ARM)

---

## Step 1: High-Resolution Timing (C)

```c
// timing.h
#ifndef TIMING_H
#define TIMING_H

#include <stdint.h>
#include <time.h>

// x86 RDTSC
static inline uint64_t rdtsc(void) {
    unsigned int lo, hi;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

// RDTSCP (serialized)
static inline uint64_t rdtscp(void) {
    unsigned int aux;
    return __rdtscp(&aux);
}

// ARM cycle counter
static inline uint64_t arm_cycle_count(void) {
    uint64_t val;
    __asm__ __volatile__("mrs %0, pmccntr_el0" : "=r"(val));
    return val;
}

// Get CPU frequency (cycles per second)
static inline double get_cpu_freq_ghz(void) {
    struct timespec ts_start, ts_end;
    uint64_t tsc_start, tsc_end;
    
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    tsc_start = rdtscp();
    
    // Busy wait for ~100ms
    for (volatile int i = 0; i < 100000000; i++);
    
    tsc_end = rdtscp();
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    
    double elapsed_sec = (ts_end.tv_sec - ts_start.tv_sec) +
                         (ts_end.tv_nsec - ts_start.tv_nsec) / 1e9;
    return (tsc_end - tsc_start) / elapsed_sec / 1e9;
}

// Convert cycles to nanoseconds
static inline double cycles_to_ns(uint64_t cycles, double freq_ghz) {
    return cycles / freq_ghz;
}

#endif
```

## Step 2: Latency Measurement Tool (C)

```c
// latency_measure.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "timing.h"

#define SAMPLES 100000

typedef struct {
    uint64_t *samples;
    int count;
    int capacity;
} latency_stats_t;

void stats_init(latency_stats_t *stats, int capacity) {
    stats->samples = malloc(capacity * sizeof(uint64_t));
    stats->count = 0;
    stats->capacity = capacity;
}

void stats_add(latency_stats_t *stats, uint64_t sample) {
    if (stats->count < stats->capacity) {
        stats->samples[stats->count++] = sample;
    }
}

int compare_uint64(const void *a, const void *b) {
    uint64_t va = *(const uint64_t *)a;
    uint64_t vb = *(const uint64_t *)b;
    return (va > vb) - (va < vb);
}

void stats_report(latency_stats_t *stats, double freq_ghz) {
    if (stats->count == 0) return;
    
    // Sort for percentiles
    qsort(stats->samples, stats->count, sizeof(uint64_t), compare_uint64);
    
    uint64_t min = stats->samples[0];
    uint64_t max = stats->samples[stats->count - 1];
    uint64_t p50 = stats->samples[stats->count * 50 / 100];
    uint64_t p99 = stats->samples[stats->count * 99 / 100];
    uint64_t p999 = stats->samples[stats->count * 999 / 1000];
    
    // Mean
    double sum = 0;
    for (int i = 0; i < stats->count; i++) sum += stats->samples[i];
    double mean = sum / stats->count;
    
    // Std dev
    double variance = 0;
    for (int i = 0; i < stats->count; i++) {
        variance += pow(stats->samples[i] - mean, 2);
    }
    variance /= stats->count;
    double stddev = sqrt(variance);
    
    printf("=== Latency Statistics (n=%d) ===\n", stats->count);
    printf("Min:    %8.1f ns\n", cycles_to_ns(min, freq_ghz));
    printf("Mean:   %8.1f ns\n", cycles_to_ns(mean, freq_ghz));
    printf("StdDev: %8.1f ns\n", cycles_to_ns(stddev, freq_ghz));
    printf("P50:    %8.1f ns\n", cycles_to_ns(p50, freq_ghz));
    printf("P99:    %8.1f ns\n", cycles_to_ns(p99, freq_ghz));
    printf("P99.9:  %8.1f ns\n", cycles_to_ns(p999, freq_ghz));
    printf("Max:    %8.1f ns\n", cycles_to_ns(max, freq_ghz));
}

// Example: measure function latency
void example_function(volatile int *data) {
    // Simulate some work
    for (int i = 0; i < 100; i++) {
        *data += i;
    }
}

int main() {
    double freq = get_cpu_freq_ghz();
    printf("CPU frequency: %.2f GHz\n\n", freq);
    
    latency_stats_t stats;
    stats_init(&stats, SAMPLES);
    
    volatile int data = 0;
    
    for (int i = 0; i < SAMPLES; i++) {
        uint64_t t0 = rdtscp();
        example_function(&data);
        uint64_t t1 = rdtscp();
        stats_add(&stats, t1 - t0);
    }
    
    stats_report(&stats, freq);
    
    free(stats.samples);
    return 0;
}
```

## Step 3: Python Statistical Analysis

```python
# analyze_latency.py
import numpy as np
import matplotlib.pyplot as plt

def analyze_latency(samples_ns):
    """Analyze latency samples in nanoseconds."""
    arr = np.array(samples_ns)
    
    print(f"Samples: {len(arr)}")
    print(f"Min:     {arr.min():.1f} ns")
    print(f"Mean:    {arr.mean():.1f} ns")
    print(f"StdDev:  {arr.std():.1f} ns")
    print(f"P50:     {np.percentile(arr, 50):.1f} ns")
    print(f"P99:     {np.percentile(arr, 99):.1f} ns")
    print(f"P99.9:   {np.percentile(arr, 99.9):.1f} ns")
    print(f"Max:     {arr.max():.1f} ns")
    
    # Plot histogram
    plt.figure(figsize=(10, 6))
    plt.hist(arr, bins=100, edgecolor='black')
    plt.xlabel('Latency (ns)')
    plt.ylabel('Count')
    plt.title('Latency Distribution')
    plt.savefig('latency_histogram.png')
    print("\nHistogram saved to latency_histogram.png")

# Example usage
if __name__ == '__main__':
    # Generate synthetic data
    np.random.seed(42)
    samples = np.random.lognormal(mean=6, sigma=0.5, size=10000)
    analyze_latency(samples)
```

## Step 4: Using Linux perf

```bash
# Measure CPU cycles for a command
perf stat -e cycles,instructions,cache-misses ./my_ull_app

# Record latency events
perf record -e cycles -g ./my_ull_app

# Report
perf report

# Hardware timestamping (DPDK)
# Enable in DPDK:
# rte_eth_timesync_enable(port_id);
```

## Step 5: Network Latency Measurement

```c
// network_latency.c
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include "timing.h"

#define PORT 12345
#define MSG_SIZE 64

int main() {
    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(PORT),
        .sin_addr.s_addr = INADDR_ANY,
    };
    bind(sockfd, (struct sockaddr *)&addr, sizeof(addr));
    
    char buf[MSG_SIZE];
    struct sockaddr_in client;
    socklen_t client_len = sizeof(client);
    
    double freq = get_cpu_freq_ghz();
    
    while (1) {
        uint64_t t0 = rdtscp();
        recvfrom(sockfd, buf, MSG_SIZE, 0,
                 (struct sockaddr *)&client, &client_len);
        uint64_t t1 = rdtscp();
        
        printf("RX latency: %.1f ns\n", cycles_to_ns(t1 - t0, freq));
        
        // Echo back
        sendto(sockfd, buf, MSG_SIZE, 0,
               (struct sockaddr *)&client, client_len);
    }
    
    close(sockfd);
    return 0;
}
```

## Expected Results

| Measurement Method | Resolution | Overhead |
|-------------------|------------|----------|
| `rdtsc` | ~0.3 ns | ~20 cycles |
| `rdtscp` | ~0.3 ns | ~100 cycles |
| `clock_gettime` | ~20 ns | ~25 ns |
| `perf_event` | ~1 ns | ~1000 cycles |
| Hardware timestamp | ~0.1 ns | ~0 (offloaded) |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Inconsistent TSC | Use `rdtscp` instead of `rdtsc` |
| High measurement overhead | Use hardware timestamping |
| Frequency varies | Disable frequency scaling |
| Outliers in data | Check for interrupts, CPU migration |

## Next Steps

- Apply measurement to [DPDK Packet Processing](dpdk-packet-processing.md)
- Measure [RDMA Echo Server](rdma-echo-server.md) latency
- Use measurements to validate [Kernel Tuning](kernel-tuning.md)
