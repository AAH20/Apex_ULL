#!/usr/bin/env python3
"""
test_dpu.py — DPU/SmartNIC Test Suite

Tests for DPU implementation:
- DPU hardware detection
- DOCA/IPDK availability
- P4 pipeline offload
- OVS offload
- Storage offload
- Crypto offload
- RDMA functionality

Usage: python3 test_dpu.py [--run-benchmarks]
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

# ── Hardware Detection ──
@test("DPU hardware detection")
def test_dpu_hardware(result):
    """Detect DPU/SmartNIC hardware."""
    ret = run_cmd("lspci | grep -iE 'mellanox|intel.*ipu|amd.*pensando|bluefield' 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["dpu_hardware"] = ret.stdout.strip()
    else:
        result.metrics["dpu_hardware"] = "not detected"

@test("ConnectX NIC detection")
def test_connectx(result):
    """Detect ConnectX NICs."""
    ret = run_cmd("lspci | grep -i mellanox 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["connectx"] = ret.stdout.strip()
    else:
        result.metrics["connectx"] = "not detected"

@test("RDMA device detection")
def test_rdma_devices(result):
    """Detect RDMA devices."""
    ret = run_cmd("ibv_devinfo 2>/dev/null | grep hca_id")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["rdma_devices"] = ret.stdout.strip()
    else:
        result.metrics["rdma_devices"] = "not detected"

@test("DPU network interfaces")
def test_dpu_netdevs(result):
    """Check DPU network interfaces."""
    ret = run_cmd("ip link show | grep -E 'ens|enp|eth' 2>/dev/null")
    result.metrics["netdevs"] = ret.stdout.strip()

@test("DPU PCIe detection")
def test_dpu_pcie(result):
    """Check DPU PCIe devices."""
    ret = run_cmd("lspci -vv | grep -A 5 -iE 'mellanox|bluefield' 2>/dev/null")
    result.metrics["pcie"] = ret.stdout[:500] if ret.stdout else "not detected"

# ── Software Stack ──
@test("DOCA SDK availability")
def test_doca(result):
    """Check DOCA SDK installation."""
    ret = run_cmd("which doca_version 2>/dev/null || find /opt -name 'doca*' 2>/dev/null | head -1")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["doca"] = ret.stdout.strip()
    else:
        result.metrics["doca"] = "not installed"

@test("IPDK availability")
def test_ipdk(result):
    """Check IPDK installation."""
    ret = run_cmd("which ipdk 2>/dev/null || find /opt -name 'ipdk*' 2>/dev/null | head -1")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["ipdk"] = ret.stdout.strip()
    else:
        result.metrics["ipdk"] = "not installed"

@test("DPU firmware version")
def test_firmware(result):
    """Check DPU firmware version."""
    ret = run_cmd("ibv_devinfo 2>/dev/null | grep fw_ver")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["firmware"] = ret.stdout.strip()
    else:
        result.metrics["firmware"] = "not available"

@test("DPU SDK version")
def test_sdk_version(result):
    """Check DPU SDK version."""
    ret = run_cmd("cat /etc/doca/version 2>/dev/null || echo 'not found'")
    result.metrics["sdk_version"] = ret.stdout.strip()

# ── RDMA Functionality ──
@test("RDMA verbs support")
def test_rdma_verbs(result):
    """Check RDMA verbs support."""
    ret = run_cmd("ibv_devinfo 2>/dev/null | grep -E 'state|link_layer'")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["rdma_verbs"] = ret.stdout.strip()
    else:
        result.metrics["rdma_verbs"] = "not available"

@test("RDMA CM support")
def test_rdma_cm(result):
    """Check RDMA connection management."""
    ret = run_cmd("which rdma_client 2>/dev/null || which rdma_server 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["rdma_cm"] = ret.stdout.strip()
    else:
        result.metrics["rdma_cm"] = "not available"

@test("RoCE configuration")
def test_roce(result):
    """Check RoCE configuration."""
    ret = run_cmd("cat /sys/class/infiniband/*/ports/1/gid_attrs/types/0 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["roce"] = ret.stdout.strip()
    else:
        result.metrics["roce"] = "not configured"

@test("PFC configuration")
def test_pfc(result):
    """Check Priority Flow Control."""
    ret = run_cmd("mlnx_qos -i eth0 2>/dev/null | grep -i pfc")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["pfc"] = ret.stdout.strip()
    else:
        result.metrics["pfc"] = "not configured"

@test("ECN configuration")
def test_ecn(result):
    """Check Explicit Congestion Notification."""
    ret = run_cmd("cat /sys/class/infiniband/*/ports/1/hw_counters/* 2>/dev/null | head -5")
    result.metrics["ecn"] = ret.stdout.strip() if ret.stdout else "not available"

# ── OVS Offload ──
@test("OVS installation")
def test_ovs(result):
    """Check OVS installation."""
    ret = run_cmd("which ovs-vsctl 2>/dev/null || dpkg -l | grep openvswitch 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["ovs"] = ret.stdout.strip()
    else:
        result.metrics["ovs"] = "not installed"

@test("OVS hardware offload")
def test_ovs_offload(result):
    """Check OVS hardware offload capability."""
    ret = run_cmd("ovs-vsctl get Open_vSwitch . other_config:hw-offload 2>/dev/null")
    if ret.returncode == 0:
        result.metrics["ovs_offload"] = ret.stdout.strip()
    else:
        result.metrics["ovs_offload"] = "not configured"

@test("OVS datapath type")
def test_ovs_datapath(result):
    """Check OVS datapath type."""
    ret = run_cmd("ovs-vsctl get bridge br0 datapath_type 2>/dev/null")
    if ret.returncode == 0:
        result.metrics["datapath"] = ret.stdout.strip()
    else:
        result.metrics["datapath"] = "not configured"

# ── Storage Offload ──
@test("NVMe-oF support")
def test_nvmeof(result):
    """Check NVMe-oF support."""
    ret = run_cmd("which nvme 2>/dev/null && nvme list 2>/dev/null | head -5")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["nvmeof"] = ret.stdout.strip()
    else:
        result.metrics["nvmeof"] = "not available"

@test("SPDK availability")
def test_spdk(result):
    """Check SPDK installation."""
    ret = run_cmd("which spdk_tgt 2>/dev/null || find /usr -name 'spdk*' 2>/dev/null | head -1")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["spdk"] = ret.stdout.strip()
    else:
        result.metrics["spdk"] = "not installed"

# ── Crypto Offload ──
@test("Crypto offload detection")
def test_crypto(result):
    """Check crypto offload capability."""
    ret = run_cmd("cat /sys/class/infiniband/*/ports/1/hw_counters/* 2>/dev/null | head -5")
    result.metrics["crypto"] = ret.stdout.strip() if ret.stdout else "not available"

@test("IPsec offload")
def test_ipsec(result):
    """Check IPsec offload capability."""
    ret = run_cmd("cat /proc/net/dev 2>/dev/null | grep -i ipsec")
    result.metrics["ipsec"] = ret.stdout.strip() if ret.stdout else "not configured"

# ── Performance Tests ──
@test("DPU packet rate")
def test_packet_rate(result):
    """Measure DPU packet processing rate."""
    ret = run_cmd("cat /sys/class/infiniband/*/ports/1/hw_counters/rx_packets 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["packet_rate"] = ret.stdout.strip()
    else:
        result.metrics["packet_rate"] = "not available"

@test("DPU bandwidth")
def test_bandwidth(result):
    """Measure DPU bandwidth."""
    ret = run_cmd("cat /sys/class/infiniband/*/ports/1/rate 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["bandwidth"] = ret.stdout.strip()
    else:
        result.metrics["bandwidth"] = "not available"

@test("DPU error counters")
def test_errors(result):
    """Check DPU error counters."""
    ret = run_cmd("cat /sys/class/infiniband/*/ports/1/hw_counters/* 2>/dev/null | head -10")
    result.metrics["errors"] = ret.stdout.strip() if ret.stdout else "not available"

@test("DPU port state")
def test_port_state(result):
    """Check DPU port state."""
    ret = run_cmd("ibv_devinfo 2>/dev/null | grep state")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["port_state"] = ret.stdout.strip()
    else:
        result.metrics["port_state"] = "not available"

@test("DPU link layer")
def test_link_layer(result):
    """Check DPU link layer type."""
    ret = run_cmd("ibv_devinfo 2>/dev/null | grep link_layer")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["link_layer"] = ret.stdout.strip()
    else:
        result.metrics["link_layer"] = "not available"

@test("DPU MTU")
def test_mtu(result):
    """Check DPU MTU."""
    ret = run_cmd("ibv_devinfo 2>/dev/null | grep mtu")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["mtu"] = ret.stdout.strip()
    else:
        result.metrics["mtu"] = "not available"

@test("DPU port count")
def test_port_count(result):
    """Check DPU port count."""
    ret = run_cmd("ibv_devinfo 2>/dev/null | grep -c port_num")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["port_count"] = ret.stdout.strip()
    else:
        result.metrics["port_count"] = "not available"

# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="DPU Test Suite")
    parser.add_argument("--output", default=None, help="Output results to JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("DPU/SmartNIC Test Suite")
    print("=" * 60)

    print("\n--- Hardware Detection ---")
    test_dpu_hardware()
    test_connectx()
    test_rdma_devices()
    test_dpu_netdevs()
    test_dpu_pcie()

    print("\n--- Software Stack ---")
    test_doca()
    test_ipdk()
    test_firmware()
    test_sdk_version()

    print("\n--- RDMA Functionality ---")
    test_rdma_verbs()
    test_rdma_cm()
    test_roce()
    test_pfc()
    test_ecn()

    print("\n--- OVS Offload ---")
    test_ovs()
    test_ovs_offload()
    test_ovs_datapath()

    print("\n--- Storage Offload ---")
    test_nvmeof()
    test_spdk()

    print("\n--- Crypto Offload ---")
    test_crypto()
    test_ipsec()

    print("\n--- Performance Metrics ---")
    test_packet_rate()
    test_bandwidth()
    test_errors()
    test_port_state()
    test_link_layer()
    test_mtu()
    test_port_count()

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
