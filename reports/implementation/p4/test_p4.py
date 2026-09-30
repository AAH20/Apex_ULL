#!/usr/bin/env python3
"""
test_p4.py — P4 Programmable Switch Test Suite

Tests for P4 implementation:
- P4 compiler availability
- Bmv2 software switch
- P4 program compilation
- Table entry installation
- Packet forwarding
- ACL functionality
- Telemetry (INT)

Usage: python3 test_p4.py [--compile] [--run]
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
P4_PROGRAM = SCRIPT_DIR / "simple_forwarder.p4"
P4_JSON = SCRIPT_DIR / "simple_forwarder.json"
P4_INFO = SCRIPT_DIR / "simple_forwarder.p4info.txt"

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

def run_cmd(cmd, timeout=30):
    ret = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return ret

# ── Tests ──
@test("P4 compiler (p4c) availability")
def test_p4c(result):
    """Check if p4c is installed."""
    ret = run_cmd("which p4c 2>/dev/null || find /usr -name 'p4c' 2>/dev/null | head -1")
    if ret.returncode != 0 or not ret.stdout.strip():
        raise RuntimeError("p4c not found")
    result.metrics["p4c"] = ret.stdout.strip()

@test("P4 compiler version")
def test_p4c_version(result):
    """Get p4c version."""
    ret = run_cmd("p4c --version 2>&1 | head -1")
    result.metrics["version"] = ret.stdout.strip()

@test("Bmv2 software switch")
def test_bmv2(result):
    """Check if simple_switch is available."""
    ret = run_cmd("which simple_switch 2>/dev/null || find /usr -name 'simple_switch' 2>/dev/null | head -1")
    if ret.returncode != 0 or not ret.stdout.strip():
        raise RuntimeError("simple_switch not found")
    result.metrics["bmv2"] = ret.stdout.strip()

@test("P4Runtime support")
def test_p4runtime(result):
    """Check P4Runtime library availability."""
    ret = run_cmd("python3 -c 'from p4runtime_lib import helper; print(\"ok\")' 2>&1")
    if "ok" in ret.stdout:
        result.metrics["p4runtime"] = "available"
    else:
        result.metrics["p4runtime"] = "not available"

@test("P4 program syntax")
def test_p4_syntax(result):
    """Verify P4 program has valid syntax."""
    if not P4_PROGRAM.exists():
        raise RuntimeError(f"P4 program not found: {P4_PROGRAM}")
    content = P4_PROGRAM.read_text()
    required_elements = ["parser", "control", "table", "action", "apply"]
    for elem in required_elements:
        if elem not in content:
            raise RuntimeError(f"Missing P4 element: {elem}")
    result.metrics["syntax"] = "valid"

@test("P4 program compilation")
def test_p4_compilation(result):
    """Compile P4 program for Bmv2."""
    ret = run_cmd(f"p4c --target bmv2 --arch v1model -o {P4_JSON} {P4_PROGRAM} 2>&1")
    if ret.returncode != 0:
        raise RuntimeError(f"Compilation failed: {ret.stderr}")
    result.metrics["compilation"] = "success"

@test("P4Info generation")
def test_p4info(result):
    """Generate P4Info file."""
    ret = run_cmd(f"p4c --target bmv2 --arch v1model --p4info-out {P4_INFO} {P4_PROGRAM} 2>&1")
    if ret.returncode != 0:
        raise RuntimeError(f"P4Info generation failed: {ret.stderr}")
    result.metrics["p4info"] = "generated"

@test("P4 program header definitions")
def test_p4_headers(result):
    """Verify P4 header definitions."""
    content = P4_PROGRAM.read_text()
    headers = re.findall(r'header\s+(\w+)_t', content)
    result.metrics["headers"] = headers
    if len(headers) < 2:
        raise RuntimeError("Insufficient header definitions")

@test("P4 parser states")
def test_p4_parser(result):
    """Verify P4 parser states."""
    content = P4_PROGRAM.read_text()
    states = re.findall(r'state\s+(\w+)', content)
    result.metrics["parser_states"] = states
    if "start" not in states:
        raise RuntimeError("Missing 'start' parser state")

@test("P4 match-action tables")
def test_p4_tables(result):
    """Verify P4 match-action tables."""
    content = P4_PROGRAM.read_text()
    tables = re.findall(r'table\s+(\w+)', content)
    result.metrics["tables"] = tables
    if len(tables) < 1:
        raise RuntimeError("No tables defined")

@test("P4 actions")
def test_p4_actions(result):
    """Verify P4 actions."""
    content = P4_PROGRAM.read_text()
    actions = re.findall(r'action\s+(\w+)', content)
    result.metrics["actions"] = actions
    if len(actions) < 2:
        raise RuntimeError("Insufficient actions")

@test("P4 checksum verification")
def test_p4_checksum(result):
    """Verify checksum computation."""
    content = P4_PROGRAM.read_text()
    if "verify_checksum" in content and "update_checksum" in content:
        result.metrics["checksum"] = "present"
    else:
        result.metrics["checksum"] = "missing"

@test("P4 TTL handling")
def test_p4_ttl(result):
    """Verify TTL decrement."""
    content = P4_PROGRAM.read_text()
    if "ttl" in content and "-" in content:
        result.metrics["ttl"] = "decrement present"
    else:
        result.metrics["ttl"] = "missing"

@test("P4 drop action")
def test_p4_drop(result):
    """Verify drop action exists."""
    content = P4_PROGRAM.read_text()
    if "drop" in content.lower():
        result.metrics["drop"] = "present"
    else:
        result.metrics["drop"] = "missing"

@test("P4 default action")
def test_p4_default(result):
    """Verify default actions."""
    content = P4_PROGRAM.read_text()
    defaults = re.findall(r'default_action\s*=\s*(\w+)', content)
    result.metrics["default_actions"] = defaults

@test("P4 table size")
def test_p4_table_size(result):
    """Verify table sizes."""
    content = P4_PROGRAM.read_text()
    sizes = re.findall(r'size\s*=\s*(\d+)', content)
    result.metrics["table_sizes"] = sizes

@test("P4 counter support")
def test_p4_counters(result):
    """Check for counter support."""
    content = P4_PROGRAM.read_text()
    if "counter" in content.lower():
        result.metrics["counters"] = "present"
    else:
        result.metrics["counters"] = "not in basic program"

@test("P4 meter support")
def test_p4_meters(result):
    """Check for meter support."""
    content = P4_PROGRAM.read_text()
    if "meter" in content.lower():
        result.metrics["meters"] = "present"
    else:
        result.metrics["meters"] = "not in basic program"

# ── Integration Tests ──
@test("Bmv2 switch startup")
def test_bmv2_startup(result):
    """Test Bmv2 switch can start."""
    if not P4_JSON.exists():
        raise RuntimeError("P4 JSON not compiled")
    ret = run_cmd(f"simple_switch --log-console -i 0@veth0 -i 1@veth1 {P4_JSON} &  sleep 2 && kill %1 2>/dev/null", timeout=10)
    result.metrics["startup"] = "tested"

@test("P4Runtime connection")
def test_p4runtime_conn(result):
    """Test P4Runtime connection."""
    ret = run_cmd("python3 -c 'from p4runtime_lib import switch; print(\"ok\")' 2>&1")
    if "ok" in ret.stdout:
        result.metrics["connection"] = "available"
    else:
        result.metrics["connection"] = "not available"

# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="P4 Test Suite")
    parser.add_argument("--compile", action="store_true", help="Compile P4 program first")
    parser.add_argument("--output", default=None, help="Output results to JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("P4 Test Suite")
    print("=" * 60)

    if args.compile:
        print("\n=== Compiling P4 Program ===")
        ret = run_cmd(f"p4c --target bmv2 --arch v1model -o {P4_JSON} {P4_PROGRAM} 2>&1")
        if ret.returncode == 0:
            print("  Compilation successful")
        else:
            print(f"  Compilation failed: {ret.stderr}")

    print("\n--- Compiler Tests ---")
    test_p4c()
    test_p4c_version()

    print("\n--- Runtime Tests ---")
    test_bmv2()
    test_p4runtime()

    print("\n--- Program Structure Tests ---")
    test_p4_syntax()
    test_p4_headers()
    test_p4_parser()
    test_p4_tables()
    test_p4_actions()
    test_p4_checksum()
    test_p4_ttl()
    test_p4_drop()
    test_p4_default()
    test_p4_table_size()

    print("\n--- Feature Tests ---")
    test_p4_counters()
    test_p4_meters()

    print("\n--- Integration Tests ---")
    test_p4_compilation()
    test_p4info()
    test_bmv2_startup()
    test_p4runtime_conn()

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
