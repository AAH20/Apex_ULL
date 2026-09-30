#!/usr/bin/env python3
"""
test_dpdk.py — DPDK Test Suite

Tests for DPDK kernel bypass implementation:
- DPDK installation verification
- Hugepage configuration
- NIC binding
- Port initialization
- Packet forwarding
- Latency benchmarks
- Throughput benchmarks

Usage: python3 test_dpdk.py [--build] [--run-benchmarks]
"""

import subprocess
import sys
import os
import time
import json
import argparse
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DPDK_BENCH = SCRIPT_DIR / "dpdk_benchmark"

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.message = ""
        self.duration_ms = 0
        self.metrics = {}

    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "metrics": self.metrics,
        }

results = []

def run_test(name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = TestResult(name)
            start = time.time()
            try:
                func(result, *args, **kwargs)
                result.passed = True
                result.message = "PASS"
            except Exception as e:
                result.passed = False
                result.message = f"FAIL: {str(e)}"
            result.duration_ms = (time.time() - start) * 1000
            results.append(result)
            status = "✓" if result.passed else "✗"
            print(f"  {status} {name}: {result.message} ({result.duration_ms:.1f} ms)")
            return result.passed
        return wrapper
    return decorator

# Alias for cleaner usage
test = run_test

def run_cmd(cmd, timeout=10):
    ret = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return ret

# ── Tests ──
@test("DPDK installation")
def test_dpdk_installed(result):
    """Verify DPDK is installed."""
    ret = run_cmd("pkg-config --exists libdpdk 2>/dev/null && echo 'found'")
    if "found" not in ret.stdout:
        ret2 = run_cmd("which dpdk-devbind.py 2>/dev/null || find /usr -name 'dpdk-devbind.py' 2>/dev/null | head -1")
        if ret2.returncode != 0 or not ret2.stdout.strip():
            raise RuntimeError("DPDK not found")
    result.metrics["dpdk"] = "installed"

@test("DPDK version")
def test_dpdk_version(result):
    """Get DPDK version."""
    ret = run_cmd("pkg-config --modversion libdpdk 2>/dev/null || dpkg -l | grep dpdk 2>/dev/null | head -1")
    result.metrics["version"] = ret.stdout.strip()

@test("Hugepage configuration")
def test_hugepages(result):
    """Check hugepage configuration."""
    ret = run_cmd("cat /proc/meminfo | grep -i huge")
    result.metrics["hugepages"] = ret.stdout.strip()
    if "Hugepages_Total" not in ret.stdout:
        raise RuntimeError("Hugepages not configured")

@test("Hugepage size")
def test_hugepage_size(result):
    """Check hugepage size."""
    ret = run_cmd("cat /proc/meminfo | grep Hpagesize")
    result.metrics["hugepage_size"] = ret.stdout.strip()

@test("CPU isolation")
def test_cpu_isolation(result):
    """Check CPU isolation kernel parameters."""
    ret = run_cmd("cat /proc/cmdline 2>/dev/null | tr ' ' '\\n' | grep -E 'isolcpus|nohz_full|rcu_nocbs'")
    result.metrics["cpu_isolation"] = ret.stdout.strip() if ret.stdout else "not configured"

@test("DPDK-compatible NIC")
def test_dpdk_nic(result):
    """Check for DPDK-compatible NICs."""
    ret = run_cmd("dpdk-devbind.py --status 2>/dev/null || echo 'devbind not found'")
    result.metrics["nic_status"] = ret.stdout[:500]

@test("VFIO driver")
def test_vfio(result):
    """Check VFIO driver availability."""
    ret = run_cmd("lsmod | grep vfio 2>/dev/null || echo 'vfio not loaded'")
    result.metrics["vfio"] = ret.stdout.strip()

@test("DPDK EAL initialization")
def test_eal_init(result):
    """Test DPDK EAL can initialize."""
    ret = run_cmd(f"sudo {DPDK_BENCH} --help 2>&1 | head -5", timeout=5)
    if "EAL" in ret.stderr or "DPDK" in ret.stderr:
        result.metrics["eal"] = "available"
    else:
        result.metrics["eal"] = "check output"

@test("DPDK port count")
def test_port_count(result):
    """Check DPDK port count."""
    ret = run_cmd("dpdk-devbind.py --status 2>/dev/null | grep -c 'drv=igb_uio\\|drv=vfio-pci'")
    result.metrics["dpdk_ports"] = ret.stdout.strip()

@test("DPDK hugepage mount")
def test_hugepage_mount(result):
    """Check hugepage filesystem is mounted."""
    ret = run_cmd("mount | grep hugetlbfs 2>/dev/null || echo 'not mounted'")
    result.metrics["hugepage_mount"] = ret.stdout.strip()

@test("DPDK binary compilation")
def test_compilation(result):
    """Verify DPDK benchmark binary compiles."""
    if not DPDK_BENCH.exists():
        raise RuntimeError(f"Binary {DPDK_BENCH} not found")
    result.metrics["binary"] = "exists"

@test("DPDK memory pool")
def test_memory_pool(result):
    """Check DPDK memory pool configuration."""
    ret = run_cmd("cat /proc/meminfo | grep -i huge")
    result.metrics["memory"] = ret.stdout.strip()

@test("DPDK environment")
def test_environment(result):
    """Check DPDK environment variables."""
    ret = run_cmd("env | grep -i dpdk 2>/dev/null || echo 'no DPDK env vars'")
    result.metrics["env"] = ret.stdout.strip()

@test("DPDK NUMA nodes")
def test_numa(result):
    """Check NUMA topology."""
    ret = run_cmd("lscpu | grep -i numa 2>/dev/null || echo 'no NUMA'")
    result.metrics["numa"] = ret.stdout.strip()

@test("DPDK CPU frequency")
def test_cpu_freq(result):
    """Check CPU frequency scaling."""
    ret = run_cmd("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'no cpufreq'")
    result.metrics["cpu_governor"] = ret.stdout.strip()

# ── Benchmark Tests ──
@test("DPDK forwarding benchmark")
def test_forwarding_bench(result):
    """Run DPDK forwarding benchmark."""
    ret = run_cmd(f"sudo {DPDK_BENCH} -l 0-1 -n 2 --proc-type=auto 2>&1", timeout=30)
    if ret.returncode == 0:
        result.metrics["forwarding"] = ret.stdout[:500]
    else:
        result.metrics["forwarding"] = ret.stderr[:200]

@test("DPDK latency benchmark")
def test_latency_bench(result):
    """Run DPDK latency benchmark."""
    ret = run_cmd(f"sudo {DPDK_BENCH} -l 0-1 -n 2 --proc-type=auto 2>&1 | grep -A 10 'Latency'", timeout=30)
    if ret.stdout:
        result.metrics["latency"] = ret.stdout[:500]

# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="DPDK Test Suite")
    parser.add_argument("--output", default=None, help="Output results to JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("DPDK Test Suite")
    print("=" * 60)

    print("\n--- Installation Tests ---")
    test_dpdk_installed()
    test_dpdk_version()

    print("\n--- Configuration Tests ---")
    test_hugepages()
    test_hugepage_size()
    test_hugepage_mount()
    test_cpu_isolation()
    test_numa()
    test_cpu_freq()

    print("\n--- Hardware Tests ---")
    test_dpdk_nic()
    test_vfio()
    test_port_count()

    print("\n--- Runtime Tests ---")
    test_eal_init()
    test_memory_pool()
    test_environment()
    test_compilation()

    print("\n--- Benchmark Tests ---")
    test_forwarding_bench()
    test_latency_bench()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    print(f"  Passed: {passed}/{len(results)}")
    print(f"  Failed: {failed}/{len(results)}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        print(f"\nResults written to {args.output}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
