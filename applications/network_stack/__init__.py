"""
ULL Network Stack — Ultra-Low-Latency Network Stack
====================================================

Kernel-bypass, zero-copy, lock-free network stack for HFT and
real-time systems.

Components:
    - NetBufPool: Zero-copy packet buffer pool (hugepage-backed)
    - NetRing: SPSC lock-free ring buffer (no CAS on fast path)
    - NetCQ: Lock-free completion queue
    - NetQP: RDMA-style Queue Pair
    - NetPort: NIC port abstraction
    - NetStack: Top-level network stack

Build:
    clang -O3 -march=native -shared -fPIC -o libnetstack.so net_stack.c

Usage:
    from applications.network_stack import NetStack, NetPort, NetQP, NetRing
"""

from .net_stack_py import (
    NetBufPool,
    NetRing,
    NetCQ,
    NetQP,
    NetPort,
    NetStack,
    now_ns,
)

__all__ = [
    "NetBufPool",
    "NetRing",
    "NetCQ",
    "NetQP",
    "NetPort",
    "NetStack",
    "now_ns",
]

__version__ = "1.0.0"
