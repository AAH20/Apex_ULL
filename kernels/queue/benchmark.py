"""
ULL Queue Benchmark Suite
==========================

Measures latency, throughput, CPU overhead, and determinism for all
queue implementations in the ULL queue kernel.

Usage:
    python3 -m kernels.queue.benchmark [--quick] [--output results.json]
"""

import argparse
import json
import os
import statistics
import sys
import time
import threading
import platform
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

from kernels.queue.queue_py import (
    SPSCQueue, MPSCQueue, MPMCQueue, SPMCQueue,
    ULLQueue, Disruptor, now_ns,
)


# ================================================================== #
# Benchmark configuration                                             #
# ================================================================== #

DEFAULT_CAPACITY = 4096
WARMUP_ITERS = 10_000
BENCH_ITERS = 1_000_000
QUICK_MODE = False


# ================================================================== #
# Latency benchmark                                                   #
# ================================================================== #

def bench_spsc_latency(capacity: int, iters: int) -> Dict:
    """Measure SPSC single-item push/pop latency."""
    q = SPSCQueue(capacity)
    latencies = []

    # Warmup
    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    # Measure
    for i in range(iters):
        t0 = now_ns()
        q.push(i)
        t1 = now_ns()
        q.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)  # push latency
        latencies.append(t2 - t1)  # pop latency

    return _stats(latencies, "SPSC latency")


def bench_mpsc_latency(capacity: int, iters: int) -> Dict:
    """Measure MPSC single-item push/pop latency."""
    q = MPSCQueue(capacity)
    latencies = []

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    for i in range(iters):
        t0 = now_ns()
        q.push(i)
        t1 = now_ns()
        q.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "MPSC latency")


def bench_mpmc_latency(capacity: int, iters: int) -> Dict:
    """Measure MPMC single-item push/pop latency."""
    q = MPMCQueue(capacity)
    latencies = []

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    for i in range(iters):
        t0 = now_ns()
        q.push(i)
        t1 = now_ns()
        q.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "MPMC latency")


def bench_spmc_latency(capacity: int, iters: int) -> Dict:
    """Measure SPMC single-item push/pop latency."""
    q = SPMCQueue(capacity)
    latencies = []

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    for i in range(iters):
        t0 = now_ns()
        q.push(i)
        t1 = now_ns()
        q.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "SPMC latency")


def bench_ull_queue_latency(capacity: int, iters: int) -> Dict:
    """Measure hybrid ULL queue latency."""
    q = ULLQueue(capacity)
    latencies = []

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    for i in range(iters):
        t0 = now_ns()
        q.push(i)
        t1 = now_ns()
        q.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "ULL Queue latency")


def bench_disruptor_latency(capacity: int, iters: int) -> Dict:
    """Measure Disruptor publish latency."""
    d = Disruptor(capacity)
    latencies = []

    for i in range(WARMUP_ITERS):
        d.publish(i)

    for i in range(iters):
        t0 = now_ns()
        d.publish(i)
        t1 = now_ns()
        latencies.append(t1 - t0)

    return _stats(latencies, "Disruptor latency")


# ================================================================== #
# Throughput benchmark                                                #
# ================================================================== #

def bench_spsc_throughput(capacity: int, iters: int) -> Dict:
    """Measure SPSC throughput (ops/sec)."""
    q = SPSCQueue(capacity)

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    t0 = time.perf_counter_ns()
    for i in range(iters):
        q.push(i)
        q.pop()
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 2  # push + pop
    return {
        "name": "SPSC throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


def bench_mpsc_throughput(capacity: int, iters: int) -> Dict:
    """Measure MPSC throughput (ops/sec)."""
    q = MPSCQueue(capacity)

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    t0 = time.perf_counter_ns()
    for i in range(iters):
        q.push(i)
        q.pop()
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 2
    return {
        "name": "MPSC throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


def bench_mpmc_throughput(capacity: int, iters: int) -> Dict:
    """Measure MPMC throughput (ops/sec)."""
    q = MPMCQueue(capacity)

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    t0 = time.perf_counter_ns()
    for i in range(iters):
        q.push(i)
        q.pop()
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 2
    return {
        "name": "MPMC throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


def bench_spmc_throughput(capacity: int, iters: int) -> Dict:
    """Measure SPMC throughput (ops/sec)."""
    q = SPMCQueue(capacity)

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    t0 = time.perf_counter_ns()
    for i in range(iters):
        q.push(i)
        q.pop()
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 2
    return {
        "name": "SPMC throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


def bench_ull_queue_throughput(capacity: int, iters: int) -> Dict:
    """Measure hybrid ULL queue throughput."""
    q = ULLQueue(capacity)

    for i in range(WARMUP_ITERS):
        q.push(i)
        q.pop()

    t0 = time.perf_counter_ns()
    for i in range(iters):
        q.push(i)
        q.pop()
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 2
    return {
        "name": "ULL Queue throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


def bench_disruptor_throughput(capacity: int, iters: int) -> Dict:
    """Measure Disruptor throughput."""
    d = Disruptor(capacity)

    for i in range(WARMUP_ITERS):
        d.publish(i)

    t0 = time.perf_counter_ns()
    for i in range(iters):
        d.publish(i)
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    return {
        "name": "Disruptor throughput",
        "ops_per_sec": iters / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": iters,
    }


# ================================================================== #
# Multi-threaded contention benchmark                                 #
# ================================================================== #

def bench_mpmc_contention(capacity: int, iters: int, n_producers: int = 2, n_consumers: int = 2) -> Dict:
    """Measure MPMC under multi-producer/multi-consumer contention."""
    q = MPMCQueue(capacity)
    total_ops = iters * (n_producers + n_consumers)
    errors = []

    def producer(pid: int):
        for i in range(iters):
            val = (pid << 32) | (i + 1)
            while not q.push(val):
                pass

    def consumer(cid: int):
        count = 0
        while count < iters:
            item = q.pop()
            if item is not None:
                count += 1

    threads = []
    t0 = time.perf_counter_ns()

    for i in range(n_producers):
        t = threading.Thread(target=producer, args=(i,))
        threads.append(t)
    for i in range(n_consumers):
        t = threading.Thread(target=consumer, args=(i,))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    t1 = time.perf_counter_ns()
    elapsed_s = (t1 - t0) / 1e9

    return {
        "name": f"MPMC contention ({n_producers}P/{n_consumers}C)",
        "ops_per_sec": total_ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": total_ops,
        "n_producers": n_producers,
        "n_consumers": n_consumers,
    }


def bench_mpsc_contention(capacity: int, iters: int, n_producers: int = 4) -> Dict:
    """Measure MPSC under multi-producer contention."""
    q = MPSCQueue(capacity)
    total_ops = iters * (n_producers + 1)

    def producer(pid: int):
        for i in range(iters):
            val = (pid << 32) | (i + 1)
            while not q.push(val):
                pass

    def consumer():
        count = 0
        while count < iters * n_producers:
            item = q.pop()
            if item is not None:
                count += 1

    threads = []
    t0 = time.perf_counter_ns()

    for i in range(n_producers):
        t = threading.Thread(target=producer, args=(i,))
        threads.append(t)
    ct = threading.Thread(target=consumer)
    threads.append(ct)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    t1 = time.perf_counter_ns()
    elapsed_s = (t1 - t0) / 1e9

    return {
        "name": f"MPSC contention ({n_producers}P/1C)",
        "ops_per_sec": total_ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": total_ops,
        "n_producers": n_producers,
    }


# ================================================================== #
# Determinism benchmark                                               #
# ================================================================== #

def bench_determinism(capacity: int, iters: int) -> Dict:
    """Measure latency determinism (jitter) for each queue type."""
    results = {}

    for name, factory in [
        ("SPSC", SPSCQueue),
        ("MPSC", MPSCQueue),
        ("MPMC", MPMCQueue),
        ("SPMC", SPMCQueue),
        ("ULL", ULLQueue),
    ]:
        q = factory(capacity)
        latencies = []

        for i in range(WARMUP_ITERS):
            q.push(i)
            q.pop()

        for i in range(iters):
            t0 = now_ns()
            q.push(i)
            t1 = now_ns()
            q.pop()
            t2 = now_ns()
            latencies.append(t1 - t0)
            latencies.append(t2 - t1)

        latencies.sort()
        results[name] = {
            "min_ns": latencies[0],
            "p50_ns": latencies[len(latencies) // 2],
            "p99_ns": latencies[int(len(latencies) * 0.99)],
            "p999_ns": latencies[int(len(latencies) * 0.999)],
            "max_ns": latencies[-1],
            "stdev_ns": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "jitter_ratio": latencies[-1] / max(latencies[0], 1),
        }

    return results


# ================================================================== #
# CPU overhead benchmark                                              #
# ================================================================== #

def bench_cpu_overhead(capacity: int, iters: int) -> Dict:
    """Measure CPU overhead via context switches and cache misses."""
    import resource

    results = {}

    for name, factory in [
        ("SPSC", SPSCQueue),
        ("MPSC", MPSCQueue),
        ("MPMC", MPMCQueue),
        ("SPMC", SPMCQueue),
        ("ULL", ULLQueue),
    ]:
        q = factory(capacity)

        # Warmup
        for i in range(WARMUP_ITERS):
            q.push(i)
            q.pop()

        # Measure CPU time
        r0 = resource.getrusage(resource.RUSAGE_SELF)
        t0 = time.perf_counter_ns()

        for i in range(iters):
            q.push(i)
            q.pop()

        t1 = time.perf_counter_ns()
        r1 = resource.getrusage(resource.RUSAGE_SELF)

        cpu_time_s = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        wall_time_s = (t1 - t0) / 1e9

        results[name] = {
            "cpu_time_ms": cpu_time_s * 1000,
            "wall_time_ms": wall_time_s * 1000,
            "cpu_overhead_pct": (cpu_time_s / max(wall_time_s, 1e-9)) * 100,
            "ctx_switches": r1.ru_nvcsw - r0.ru_nvcsw,
            "involuntary_ctx_switches": r1.ru_nivcsw - r0.ru_nivcsw,
        }

    return results


# ================================================================== #
# Helper functions                                                    #
# ================================================================== #

def _stats(latencies: List[int], name: str) -> Dict:
    """Compute latency statistics."""
    latencies.sort()
    n = len(latencies)
    return {
        "name": name,
        "min_ns": latencies[0],
        "p50_ns": latencies[n // 2],
        "p90_ns": latencies[int(n * 0.90)],
        "p99_ns": latencies[int(n * 0.99)],
        "p999_ns": latencies[int(n * 0.999)],
        "max_ns": latencies[-1],
        "mean_ns": statistics.mean(latencies),
        "stdev_ns": statistics.stdev(latencies) if n > 1 else 0,
        "samples": n,
    }


# ================================================================== #
# Main benchmark runner                                               #
# ================================================================== #

def run_benchmarks(quick: bool = False) -> Dict:
    """Run all benchmarks and return results."""
    global WARMUP_ITERS, BENCH_ITERS

    if quick:
        WARMUP_ITERS = 1_000
        BENCH_ITERS = 100_000

    capacity = DEFAULT_CAPACITY
    iters = BENCH_ITERS

    print(f"ULL Queue Benchmark Suite")
    print(f"========================")
    print(f"Platform: {platform.machine()} / {platform.processor()}")
    print(f"Python: {platform.python_version()}")
    print(f"Capacity: {capacity}")
    print(f"Iterations: {iters:,}")
    print(f"Warmup: {WARMUP_ITERS:,}")
    print()

    results = {
        "metadata": {
            "platform": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "capacity": capacity,
            "iterations": iters,
            "warmup": WARMUP_ITERS,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
        "latency": {},
        "throughput": {},
        "contention": {},
        "determinism": {},
        "cpu_overhead": {},
    }

    # Latency benchmarks
    print("Running latency benchmarks...")
    for name, fn in [
        ("SPSC", bench_spsc_latency),
        ("MPSC", bench_mpsc_latency),
        ("MPMC", bench_mpmc_latency),
        ("SPMC", bench_spmc_latency),
        ("ULL", bench_ull_queue_latency),
        ("Disruptor", bench_disruptor_latency),
    ]:
        print(f"  {name}...", end=" ", flush=True)
        results["latency"][name] = fn(capacity, iters)
        print(f"p50={results['latency'][name]['p50_ns']}ns")

    # Throughput benchmarks
    print("\nRunning throughput benchmarks...")
    for name, fn in [
        ("SPSC", bench_spsc_throughput),
        ("MPSC", bench_mpsc_throughput),
        ("MPMC", bench_mpmc_throughput),
        ("SPMC", bench_spmc_throughput),
        ("ULL", bench_ull_queue_throughput),
        ("Disruptor", bench_disruptor_throughput),
    ]:
        print(f"  {name}...", end=" ", flush=True)
        results["throughput"][name] = fn(capacity, iters)
        print(f"{results['throughput'][name]['ops_per_sec']/1e6:.1f}M ops/s")

    # Contention benchmarks
    print("\nRunning contention benchmarks...")
    print("  MPMC 2P/2C...", end=" ", flush=True)
    results["contention"]["MPMC_2P2C"] = bench_mpmc_contention(capacity, iters // 10, 2, 2)
    print(f"{results['contention']['MPMC_2P2C']['ops_per_sec']/1e6:.1f}M ops/s")

    print("  MPMC 4P/4C...", end=" ", flush=True)
    results["contention"]["MPMC_4P4C"] = bench_mpmc_contention(capacity, iters // 10, 4, 4)
    print(f"{results['contention']['MPMC_4P4C']['ops_per_sec']/1e6:.1f}M ops/s")

    print("  MPSC 4P/1C...", end=" ", flush=True)
    results["contention"]["MPSC_4P1C"] = bench_mpsc_contention(capacity, iters // 10, 4)
    print(f"{results['contention']['MPSC_4P1C']['ops_per_sec']/1e6:.1f}M ops/s")

    # Determinism benchmarks
    print("\nRunning determinism benchmarks...")
    results["determinism"] = bench_determinism(capacity, iters // 10)
    for name, stats in results["determinism"].items():
        print(f"  {name}: p99={stats['p99_ns']}ns, jitter={stats['jitter_ratio']:.1f}x")

    # CPU overhead benchmarks
    print("\nRunning CPU overhead benchmarks...")
    results["cpu_overhead"] = bench_cpu_overhead(capacity, iters)
    for name, stats in results["cpu_overhead"].items():
        print(f"  {name}: cpu={stats['cpu_overhead_pct']:.1f}%, ctx_switches={stats['ctx_switches']}")

    return results


def print_summary(results: Dict):
    """Print a formatted summary table."""
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n--- Latency (ns) ---")
    print(f"{'Queue':<12} {'min':>8} {'p50':>8} {'p90':>8} {'p99':>8} {'p99.9':>8} {'max':>8}")
    print("-" * 72)
    for name, s in results["latency"].items():
        print(f"{name:<12} {s['min_ns']:>8} {s['p50_ns']:>8} {s['p90_ns']:>8} "
              f"{s['p99_ns']:>8} {s['p999_ns']:>8} {s['max_ns']:>8}")

    print("\n--- Throughput (M ops/s) ---")
    print(f"{'Queue':<12} {'ops/s':>12}")
    print("-" * 28)
    for name, s in results["throughput"].items():
        print(f"{name:<12} {s['ops_per_sec']/1e6:>12.1f}")

    print("\n--- Determinism (jitter ratio) ---")
    print(f"{'Queue':<12} {'p99':>8} {'p99.9':>8} {'max':>8} {'jitter':>8}")
    print("-" * 52)
    for name, s in results["determinism"].items():
        print(f"{name:<12} {s['p99_ns']:>8} {s['p999_ns']:>8} {s['max_ns']:>8} {s['jitter_ratio']:>8.1f}x")

    print("\n--- CPU Overhead ---")
    print(f"{'Queue':<12} {'cpu%':>8} {'ctx_sw':>8} {'invol':>8}")
    print("-" * 44)
    for name, s in results["cpu_overhead"].items():
        print(f"{name:<12} {s['cpu_overhead_pct']:>8.1f} {s['ctx_switches']:>8} {s['involuntary_ctx_switches']:>8}")


def main():
    parser = argparse.ArgumentParser(description="ULL Queue Benchmark Suite")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()

    results = run_benchmarks(quick=args.quick)
    print_summary(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
