"""
ULL Network Stack — Python Benchmark Suite
==========================================

Measures latency, throughput, CPU overhead, and determinism for all
network stack components.

Usage:
    python3 -m applications.network_stack.benchmark [--quick] [--output results.json]
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
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))

from applications.network_stack.net_stack_py import (
    NetBufPool, NetRing, NetCQ, NetQP, NetPort, NetStack, now_ns,
)


# ================================================================== #
# Benchmark configuration                                             #
# ================================================================== #

DEFAULT_RING_CAPACITY = 4096
DEFAULT_POOL_CAPACITY = 65536
DEFAULT_BUF_SIZE = 9000
WARMUP_ITERS = 10_000
BENCH_ITERS = 1_000_000
QUICK_MODE = False


# ================================================================== #
# Latency benchmark                                                   #
# ================================================================== #

def bench_ring_latency(capacity: int, iters: int) -> Dict:
    """Measure ring buffer push/pop latency."""
    ring = NetRing(capacity)
    latencies = []

    # Warmup
    for i in range(WARMUP_ITERS):
        ring.push(i + 1)
        ring.pop()

    # Measure
    for i in range(iters):
        t0 = now_ns()
        ring.push(i + 1)
        t1 = now_ns()
        ring.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "Ring latency")


def bench_buf_pool_latency(capacity: int, buf_size: int, iters: int) -> Dict:
    """Measure buffer pool alloc/free latency."""
    pool = NetBufPool(capacity, buf_size)
    latencies = []

    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        pool.free(idx)

    for i in range(iters):
        t0 = now_ns()
        idx = pool.alloc()
        t1 = now_ns()
        pool.free(idx)
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "BufPool latency")


def bench_cq_latency(capacity: int, iters: int) -> Dict:
    """Measure completion queue push/pop latency."""
    cq = NetCQ(capacity)
    latencies = []

    for i in range(WARMUP_ITERS):
        cq.push(i + 1, 0, 64, i)
        cq.pop()

    for i in range(iters):
        t0 = now_ns()
        cq.push(i + 1, 0, 64, i)
        t1 = now_ns()
        cq.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "CQ latency")


def bench_qp_latency(capacity: int, buf_size: int, iters: int) -> Dict:
    """Measure queue pair send/recv latency."""
    pool = NetBufPool(capacity, buf_size)
    qp = NetQP(1, pool, capacity)
    latencies = []

    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        qp.send(idx)
        qp.loopback()
        qp.recv()
        pool.free(idx)

    for i in range(iters):
        idx = pool.alloc()
        t0 = now_ns()
        qp.send(idx)
        t1 = now_ns()
        qp.loopback()
        qp.recv()
        t2 = now_ns()
        pool.free(idx)
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)

    return _stats(latencies, "QP latency")


# ================================================================== #
# Throughput benchmark                                                #
# ================================================================== #

def bench_ring_throughput(capacity: int, iters: int) -> Dict:
    """Measure ring buffer throughput (ops/sec)."""
    ring = NetRing(capacity)

    for i in range(WARMUP_ITERS):
        ring.push(i + 1)
        ring.pop()

    t0 = time.perf_counter_ns()
    for i in range(iters):
        ring.push(i + 1)
        ring.pop()
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 2
    return {
        "name": "Ring throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


def bench_buf_pool_throughput(capacity: int, buf_size: int, iters: int) -> Dict:
    """Measure buffer pool throughput (ops/sec)."""
    pool = NetBufPool(capacity, buf_size)

    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        pool.free(idx)

    t0 = time.perf_counter_ns()
    for i in range(iters):
        idx = pool.alloc()
        pool.free(idx)
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 2
    return {
        "name": "BufPool throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


def bench_qp_throughput(capacity: int, buf_size: int, iters: int) -> Dict:
    """Measure queue pair throughput (ops/sec)."""
    pool = NetBufPool(capacity, buf_size)
    qp = NetQP(1, pool, capacity)

    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        qp.send(idx)
        qp.loopback()
        qp.recv()
        pool.free(idx)

    t0 = time.perf_counter_ns()
    for i in range(iters):
        idx = pool.alloc()
        qp.send(idx)
        qp.loopback()
        qp.recv()
        pool.free(idx)
    t1 = time.perf_counter_ns()

    elapsed_s = (t1 - t0) / 1e9
    ops = iters * 3
    return {
        "name": "QP throughput",
        "ops_per_sec": ops / elapsed_s,
        "elapsed_s": elapsed_s,
        "total_ops": ops,
    }


# ================================================================== #
# Determinism benchmark                                               #
# ================================================================== #

def bench_determinism(capacity: int, buf_size: int, iters: int) -> Dict:
    """Measure latency determinism (jitter) for each component."""
    results = {}

    # Ring determinism
    ring = NetRing(capacity)
    latencies = []
    for i in range(WARMUP_ITERS):
        ring.push(i + 1)
        ring.pop()
    for i in range(iters):
        t0 = now_ns()
        ring.push(i + 1)
        t1 = now_ns()
        ring.pop()
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)
    latencies.sort()
    results["Ring"] = {
        "min_ns": latencies[0],
        "p50_ns": latencies[len(latencies) // 2],
        "p99_ns": latencies[int(len(latencies) * 0.99)],
        "p999_ns": latencies[int(len(latencies) * 0.999)],
        "max_ns": latencies[-1],
        "stdev_ns": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "jitter_ratio": latencies[-1] / max(latencies[0], 1),
    }

    # Buffer pool determinism
    pool = NetBufPool(capacity, buf_size)
    latencies = []
    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        pool.free(idx)
    for i in range(iters):
        t0 = now_ns()
        idx = pool.alloc()
        t1 = now_ns()
        pool.free(idx)
        t2 = now_ns()
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)
    latencies.sort()
    results["BufPool"] = {
        "min_ns": latencies[0],
        "p50_ns": latencies[len(latencies) // 2],
        "p99_ns": latencies[int(len(latencies) * 0.99)],
        "p999_ns": latencies[int(len(latencies) * 0.999)],
        "max_ns": latencies[-1],
        "stdev_ns": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "jitter_ratio": latencies[-1] / max(latencies[0], 1),
    }

    # QP determinism
    qp = NetQP(1, pool, capacity)
    latencies = []
    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        qp.send(idx)
        qp.loopback()
        qp.recv()
        pool.free(idx)
    for i in range(iters):
        idx = pool.alloc()
        t0 = now_ns()
        qp.send(idx)
        t1 = now_ns()
        qp.loopback()
        qp.recv()
        t2 = now_ns()
        pool.free(idx)
        latencies.append(t1 - t0)
        latencies.append(t2 - t1)
    latencies.sort()
    results["QP"] = {
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

def bench_cpu_overhead(capacity: int, buf_size: int, iters: int) -> Dict:
    """Measure CPU overhead via context switches and cache misses."""
    import resource

    results = {}

    # Ring CPU overhead
    ring = NetRing(capacity)
    for i in range(WARMUP_ITERS):
        ring.push(i + 1)
        ring.pop()

    r0 = resource.getrusage(resource.RUSAGE_SELF)
    t0 = time.perf_counter_ns()
    for i in range(iters):
        ring.push(i + 1)
        ring.pop()
    t1 = time.perf_counter_ns()
    r1 = resource.getrusage(resource.RUSAGE_SELF)

    cpu_time_s = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    wall_time_s = (t1 - t0) / 1e9

    results["Ring"] = {
        "cpu_time_ms": cpu_time_s * 1000,
        "wall_time_ms": wall_time_s * 1000,
        "cpu_overhead_pct": (cpu_time_s / max(wall_time_s, 1e-9)) * 100,
        "ctx_switches": r1.ru_nvcsw - r0.ru_nvcsw,
        "involuntary_ctx_switches": r1.ru_nivcsw - r0.ru_nivcsw,
    }

    # Buffer pool CPU overhead
    pool = NetBufPool(capacity, buf_size)
    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        pool.free(idx)

    r0 = resource.getrusage(resource.RUSAGE_SELF)
    t0 = time.perf_counter_ns()
    for i in range(iters):
        idx = pool.alloc()
        pool.free(idx)
    t1 = time.perf_counter_ns()
    r1 = resource.getrusage(resource.RUSAGE_SELF)

    cpu_time_s = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    wall_time_s = (t1 - t0) / 1e9

    results["BufPool"] = {
        "cpu_time_ms": cpu_time_s * 1000,
        "wall_time_ms": wall_time_s * 1000,
        "cpu_overhead_pct": (cpu_time_s / max(wall_time_s, 1e-9)) * 100,
        "ctx_switches": r1.ru_nvcsw - r0.ru_nvcsw,
        "involuntary_ctx_switches": r1.ru_nivcsw - r0.ru_nivcsw,
    }

    # QP CPU overhead
    qp = NetQP(1, pool, capacity)
    for i in range(WARMUP_ITERS):
        idx = pool.alloc()
        qp.send(idx)
        qp.loopback()
        qp.recv()
        pool.free(idx)

    r0 = resource.getrusage(resource.RUSAGE_SELF)
    t0 = time.perf_counter_ns()
    for i in range(iters):
        idx = pool.alloc()
        qp.send(idx)
        qp.loopback()
        qp.recv()
        pool.free(idx)
    t1 = time.perf_counter_ns()
    r1 = resource.getrusage(resource.RUSAGE_SELF)

    cpu_time_s = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    wall_time_s = (t1 - t0) / 1e9

    results["QP"] = {
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

    ring_capacity = DEFAULT_RING_CAPACITY
    pool_capacity = DEFAULT_POOL_CAPACITY
    buf_size = DEFAULT_BUF_SIZE
    iters = BENCH_ITERS

    print(f"ULL Network Stack Benchmark Suite")
    print(f"=================================")
    print(f"Platform: {platform.machine()} / {platform.processor()}")
    print(f"Python: {platform.python_version()}")
    print(f"Ring capacity: {ring_capacity}")
    print(f"Pool capacity: {pool_capacity}")
    print(f"Buffer size: {buf_size}")
    print(f"Iterations: {iters:,}")
    print(f"Warmup: {WARMUP_ITERS:,}")
    print()

    results = {
        "metadata": {
            "platform": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "ring_capacity": ring_capacity,
            "pool_capacity": pool_capacity,
            "buf_size": buf_size,
            "iterations": iters,
            "warmup": WARMUP_ITERS,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
        "latency": {},
        "throughput": {},
        "determinism": {},
        "cpu_overhead": {},
    }

    # Latency benchmarks
    print("Running latency benchmarks...")
    for name, fn in [
        ("Ring", lambda: bench_ring_latency(ring_capacity, iters)),
        ("BufPool", lambda: bench_buf_pool_latency(pool_capacity, buf_size, iters)),
        ("CQ", lambda: bench_cq_latency(ring_capacity, iters)),
        ("QP", lambda: bench_qp_latency(pool_capacity, buf_size, iters)),
    ]:
        print(f"  {name}...", end=" ", flush=True)
        results["latency"][name] = fn()
        print(f"p50={results['latency'][name]['p50_ns']}ns")

    # Throughput benchmarks
    print("\nRunning throughput benchmarks...")
    for name, fn in [
        ("Ring", lambda: bench_ring_throughput(ring_capacity, iters)),
        ("BufPool", lambda: bench_buf_pool_throughput(pool_capacity, buf_size, iters)),
        ("QP", lambda: bench_qp_throughput(pool_capacity, buf_size, iters)),
    ]:
        print(f"  {name}...", end=" ", flush=True)
        results["throughput"][name] = fn()
        print(f"{results['throughput'][name]['ops_per_sec']/1e6:.1f}M ops/s")

    # Determinism benchmarks
    print("\nRunning determinism benchmarks...")
    results["determinism"] = bench_determinism(pool_capacity, buf_size, iters // 10)
    for name, stats in results["determinism"].items():
        print(f"  {name}: p99={stats['p99_ns']}ns, jitter={stats['jitter_ratio']:.1f}x")

    # CPU overhead benchmarks
    print("\nRunning CPU overhead benchmarks...")
    results["cpu_overhead"] = bench_cpu_overhead(pool_capacity, buf_size, iters)
    for name, stats in results["cpu_overhead"].items():
        print(f"  {name}: cpu={stats['cpu_overhead_pct']:.1f}%, ctx_switches={stats['ctx_switches']}")

    return results


def print_summary(results: Dict):
    """Print a formatted summary table."""
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n--- Latency (ns) ---")
    print(f"{'Component':<12} {'min':>8} {'p50':>8} {'p90':>8} {'p99':>8} {'p99.9':>8} {'max':>8}")
    print("-" * 72)
    for name, s in results["latency"].items():
        print(f"{name:<12} {s['min_ns']:>8} {s['p50_ns']:>8} {s['p90_ns']:>8} "
              f"{s['p99_ns']:>8} {s['p999_ns']:>8} {s['max_ns']:>8}")

    print("\n--- Throughput (M ops/s) ---")
    print(f"{'Component':<12} {'ops/s':>12}")
    print("-" * 28)
    for name, s in results["throughput"].items():
        print(f"{name:<12} {s['ops_per_sec']/1e6:>12.1f}")

    print("\n--- Determinism (jitter ratio) ---")
    print(f"{'Component':<12} {'p99':>8} {'p99.9':>8} {'max':>8} {'jitter':>8}")
    print("-" * 52)
    for name, s in results["determinism"].items():
        print(f"{name:<12} {s['p99_ns']:>8} {s['p999_ns']:>8} {s['max_ns']:>8} {s['jitter_ratio']:>8.1f}x")

    print("\n--- CPU Overhead ---")
    print(f"{'Component':<12} {'cpu%':>8} {'ctx_sw':>8} {'invol':>8}")
    print("-" * 44)
    for name, s in results["cpu_overhead"].items():
        print(f"{name:<12} {s['cpu_overhead_pct']:>8.1f} {s['ctx_switches']:>8} {s['involuntary_ctx_switches']:>8}")


def main():
    parser = argparse.ArgumentParser(description="ULL Network Stack Benchmark Suite")
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
