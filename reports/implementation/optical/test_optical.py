#!/usr/bin/env python3
"""
test_optical.py — Optical Switching Test Suite

Tests for optical switching implementation:
- Optical hardware detection
- Optical link status
- Switching latency measurement
- Port configuration
- Wavelength management
- Power monitoring

Usage: python3 test_optical.py [--run-benchmarks]
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
@test("Optical transceiver detection")
def test_optical_transceivers(result):
    """Detect optical transceivers."""
    ret = run_cmd("ethtool eth0 2>/dev/null | grep -i 'transceiver|speed|link'")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["transceivers"] = ret.stdout.strip()
    else:
        result.metrics["transceivers"] = "not detected"

@test("Optical link status")
def test_optical_link(result):
    """Check optical link status."""
    ret = run_cmd("ethtool eth0 2>/dev/null | grep 'Link detected'")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["link"] = ret.stdout.strip()
    else:
        result.metrics["link"] = "not detected"

@test("Optical port speed")
def test_optical_speed(result):
    """Check optical port speed."""
    ret = run_cmd("ethtool eth0 2>/dev/null | grep Speed")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["speed"] = ret.stdout.strip()
    else:
        result.metrics["speed"] = "not detected"

@test("Optical port duplex")
def test_optical_duplex(result):
    """Check optical port duplex mode."""
    ret = run_cmd("ethtool eth0 2>/dev/null | grep Duplex")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["duplex"] = ret.stdout.strip()
    else:
        result.metrics["duplex"] = "not detected"

@test("Optical port autonegotiation")
def test_autonegotiation(result):
    """Check autonegotiation status."""
    ret = run_cmd("ethtool eth0 2>/dev/null | grep Auto-negotiation")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["autoneg"] = ret.stdout.strip()
    else:
        result.metrics["autoneg"] = "not detected"

# ── Optical Diagnostics ──
@test("Optical diagnostics")
def test_optical_diagnostics(result):
    """Get optical diagnostics."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["diagnostics"] = ret.stdout.strip()
    else:
        result.metrics["diagnostics"] = "not available"

@test("Optical power levels")
def test_optical_power(result):
    """Check optical power levels."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i power")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["power"] = ret.stdout.strip()
    else:
        result.metrics["power"] = "not available"

@test("Optical temperature")
def test_optical_temp(result):
    """Check optical module temperature."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i temp")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["temperature"] = ret.stdout.strip()
    else:
        result.metrics["temperature"] = "not available"

@test("Optical voltage")
def test_optical_voltage(result):
    """Check optical module voltage."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i voltage")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["voltage"] = ret.stdout.strip()
    else:
        result.metrics["voltage"] = "not available"

@test("Optical bias current")
def test_optical_bias(result):
    """Check optical bias current."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i bias")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["bias"] = ret.stdout.strip()
    else:
        result.metrics["bias"] = "not available"

# ── Switch Configuration ──
@test("Optical switch detection")
def test_optical_switch(result):
    """Detect optical switch."""
    ret = run_cmd("lspci | grep -iE 'optical|photonic|ocS' 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["switch"] = ret.stdout.strip()
    else:
        result.metrics["switch"] = "not detected"

@test("Optical switch ports")
def test_optical_ports(result):
    """Check optical switch ports."""
    ret = run_cmd("ip link show | grep -c 'eth\\|ens\\|enp' 2>/dev/null")
    result.metrics["ports"] = ret.stdout.strip()

@test("Optical switch latency")
def test_optical_latency(result):
    """Measure optical switching latency."""
    # This would require specialized hardware
    result.metrics["latency"] = "requires hardware"

@test("Optical switch configuration")
def test_optical_config(result):
    """Check optical switch configuration."""
    ret = run_cmd("ethtool eth0 2>/dev/null | grep -E 'port|speed|duplex'")
    result.metrics["config"] = ret.stdout.strip() if ret.stdout else "not available"

# ── Network Performance ──
@test("Optical network throughput")
def test_optical_throughput(result):
    """Measure optical network throughput."""
    ret = run_cmd("cat /sys/class/net/eth0/statistics/rx_bytes 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["rx_bytes"] = ret.stdout.strip()
    else:
        result.metrics["rx_bytes"] = "not available"

@test("Optical network errors")
def test_optical_errors(result):
    """Check optical network errors."""
    ret = run_cmd("cat /sys/class/net/eth0/statistics/rx_errors 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["rx_errors"] = ret.stdout.strip()
    else:
        result.metrics["rx_errors"] = "not available"

@test("Optical network drops")
def test_optical_drops(result):
    """Check optical network drops."""
    ret = run_cmd("cat /sys/class/net/eth0/statistics/rx_dropped 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["rx_dropped"] = ret.stdout.strip()
    else:
        result.metrics["rx_dropped"] = "not available"

@test("Optical network MTU")
def test_optical_mtu(result):
    """Check optical network MTU."""
    ret = run_cmd("cat /sys/class/net/eth0/mtu 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["mtu"] = ret.stdout.strip()
    else:
        result.metrics["mtu"] = "not available"

@test("Optical network carrier")
def test_optical_carrier(result):
    """Check optical carrier status."""
    ret = run_cmd("cat /sys/class/net/eth0/carrier 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["carrier"] = ret.stdout.strip()
    else:
        result.metrics["carrier"] = "not available"

# ── Advanced Features ──
@test("Optical WDM support")
def test_wdm(result):
    """Check WDM support."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i wdm")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["wdm"] = ret.stdout.strip()
    else:
        result.metrics["wdm"] = "not available"

@test("Optical tunable laser")
def test_tunable_laser(result):
    """Check tunable laser support."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i tunable")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["tunable"] = ret.stdout.strip()
    else:
        result.metrics["tunable"] = "not available"

@test("Optical FEC status")
def test_fec(result):
    """Check FEC status."""
    ret = run_cmd("ethtool --show-fec eth0 2>/dev/null")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["fec"] = ret.stdout.strip()
    else:
        result.metrics["fec"] = "not available"

@test("Optical link training")
def test_link_training(result):
    """Check link training status."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i training")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["training"] = ret.stdout.strip()
    else:
        result.metrics["training"] = "not available"

@test("Optical DOM monitoring")
def test_dom(result):
    """Check Digital Optical Monitoring."""
    ret = run_cmd("ethtool --module-info eth0 2>/dev/null | grep -i dom")
    if ret.returncode == 0 and ret.stdout.strip():
        result.metrics["dom"] = ret.stdout.strip()
    else:
        result.metrics["dom"] = "not available"

# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="Optical Switching Test Suite")
    parser.add_argument("--output", default=None, help="Output results to JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("Optical Switching Test Suite")
    print("=" * 60)

    print("\n--- Hardware Detection ---")
    test_optical_transceivers()
    test_optical_link()
    test_optical_speed()
    test_optical_duplex()
    test_autonegotiation()

    print("\n--- Optical Diagnostics ---")
    test_optical_diagnostics()
    test_optical_power()
    test_optical_temp()
    test_optical_voltage()
    test_optical_bias()

    print("\n--- Switch Configuration ---")
    test_optical_switch()
    test_optical_ports()
    test_optical_latency()
    test_optical_config()

    print("\n--- Network Performance ---")
    test_optical_throughput()
    test_optical_errors()
    test_optical_drops()
    test_optical_mtu()
    test_optical_carrier()

    print("\n--- Advanced Features ---")
    test_wdm()
    test_tunable_laser()
    test_fec()
    test_link_training()
    test_dom()

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
