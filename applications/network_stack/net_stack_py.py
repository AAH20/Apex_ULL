"""
ULL Network Stack — Python Interface
====================================

ctypes bindings to the C network stack library plus benchmarking infrastructure.

Usage:
    from applications.network_stack.net_stack_py import (
        NetBufPool, NetRing, NetCQ, NetQP, NetPort, NetStack, now_ns
    )
"""

import ctypes
import os
import subprocess
import sys
import time
import statistics
import threading
import platform
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# Build the C library on first import
_LIB_DIR = Path(__file__).parent
_LIB_PATH = _LIB_DIR / "libnetstack.so"


def _build_lib() -> None:
    """Compile the C network stack library if not already built."""
    if _LIB_PATH.exists():
        return
    src = _LIB_DIR / "net_stack.c"
    hdr = _LIB_DIR / "net_stack.h"
    if not src.exists() or not hdr.exists():
        raise RuntimeError(f"net_stack.c or net_stack.h not found in {_LIB_DIR}")

    cmd = [
        "clang", "-O3", "-march=native", "-shared", "-fPIC",
        "-o", str(_LIB_PATH), str(src),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build libnetstack.so:\n{result.stderr}")


_build_lib()

_lib = ctypes.CDLL(str(_LIB_PATH))

# ================================================================== #
# ctypes type signatures                                              #
# ================================================================== #

# Buffer pool
_lib.net_buf_pool_init.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
_lib.net_buf_pool_init.restype = ctypes.c_int
_lib.net_buf_pool_destroy.argtypes = [ctypes.c_void_p]
_lib.net_buf_alloc.argtypes = [ctypes.c_void_p]
_lib.net_buf_alloc.restype = ctypes.c_void_p
_lib.net_buf_free.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.net_buf_pool_free_count.argtypes = [ctypes.c_void_p]
_lib.net_buf_pool_free_count.restype = ctypes.c_uint32

# Ring
_lib.net_ring_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.net_ring_init.restype = ctypes.c_int
_lib.net_ring_destroy.argtypes = [ctypes.c_void_p]
_lib.net_ring_push.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.net_ring_push.restype = ctypes.c_bool
_lib.net_ring_pop.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.net_ring_pop.restype = ctypes.c_bool
_lib.net_ring_is_empty.argtypes = [ctypes.c_void_p]
_lib.net_ring_is_empty.restype = ctypes.c_bool
_lib.net_ring_is_full.argtypes = [ctypes.c_void_p]
_lib.net_ring_is_full.restype = ctypes.c_bool
_lib.net_ring_size.argtypes = [ctypes.c_void_p]
_lib.net_ring_size.restype = ctypes.c_uint64
_lib.net_ring_push_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint64]
_lib.net_ring_push_batch.restype = ctypes.c_uint64
_lib.net_ring_pop_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint64]
_lib.net_ring_pop_batch.restype = ctypes.c_uint64

# Completion queue
_lib.net_cq_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.net_cq_init.restype = ctypes.c_int
_lib.net_cq_destroy.argtypes = [ctypes.c_void_p]
_lib.net_cq_push.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.net_cq_push.restype = ctypes.c_bool
_lib.net_cq_pop.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.net_cq_pop.restype = ctypes.c_bool

# Queue pair
_lib.net_qp_init.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint64]
_lib.net_qp_init.restype = ctypes.c_int
_lib.net_qp_destroy.argtypes = [ctypes.c_void_p]
_lib.net_qp_send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.net_qp_send.restype = ctypes.c_bool
_lib.net_qp_recv.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.net_qp_recv.restype = ctypes.c_bool
_lib.net_qp_poll_tx.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.net_qp_poll_tx.restype = ctypes.c_bool
_lib.net_qp_poll_rx.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.net_qp_poll_rx.restype = ctypes.c_bool
_lib.net_qp_loopback.argtypes = [ctypes.c_void_p]
_lib.net_qp_loopback.restype = ctypes.c_uint64

# Port
_lib.net_port_init.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32]
_lib.net_port_init.restype = ctypes.c_int
_lib.net_port_destroy.argtypes = [ctypes.c_void_p]
_lib.net_port_create_qp.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint64]
_lib.net_port_create_qp.restype = ctypes.c_void_p
_lib.net_port_rx_burst.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint32]
_lib.net_port_rx_burst.restype = ctypes.c_bool
_lib.net_port_tx_burst.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint32]
_lib.net_port_tx_burst.restype = ctypes.c_bool

# Stack
_lib.net_stack_init.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
_lib.net_stack_init.restype = ctypes.c_int
_lib.net_stack_destroy.argtypes = [ctypes.c_void_p]
_lib.net_stack_get_port.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
_lib.net_stack_get_port.restype = ctypes.c_void_p

# Timer
_lib.net_now_ns_export.argtypes = []
_lib.net_now_ns_export.restype = ctypes.c_uint64


# ================================================================== #
# Python wrappers                                                     #
# ================================================================== #

class NetBufPool:
    """Zero-copy packet buffer pool backed by hugepage memory."""

    def __init__(self, capacity: int = 65536, buf_size: int = 9000):
        self._buf = ctypes.create_string_buffer(4096)
        self._pool = ctypes.cast(self._buf, ctypes.c_void_p)
        if _lib.net_buf_pool_init(self._pool, capacity, buf_size) != 0:
            raise MemoryError("net_buf_pool_init failed")

    def __del__(self):
        _lib.net_buf_pool_destroy(self._pool)

    def alloc(self) -> int:
        """Allocate a buffer, returns buffer index."""
        ptr = _lib.net_buf_alloc(self._pool)
        if not ptr:
            return -1
        return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32))[0]

    def free(self, buf_index: int) -> None:
        """Free a buffer by index."""
        pass

    @property
    def free_count(self) -> int:
        return _lib.net_buf_pool_free_count(self._pool)


class NetRing:
    """SPSC lock-free ring buffer for packet descriptors."""

    def __init__(self, capacity: int = 4096):
        self._buf = ctypes.create_string_buffer(512)
        self._ring = ctypes.cast(self._buf, ctypes.c_void_p)
        if _lib.net_ring_init(self._ring, capacity) != 0:
            raise MemoryError("net_ring_init failed")

    def __del__(self):
        _lib.net_ring_destroy(self._ring)

    def push(self, buf_ptr: int) -> bool:
        return _lib.net_ring_push(self._ring, ctypes.c_void_p(buf_ptr))

    def pop(self) -> Optional[int]:
        ptr = ctypes.c_void_p()
        if _lib.net_ring_pop(self._ring, ctypes.byref(ptr)):
            return ptr.value
        return None

    @property
    def size(self) -> int:
        return _lib.net_ring_size(self._ring)

    def is_empty(self) -> bool:
        return _lib.net_ring_is_empty(self._ring)

    def is_full(self) -> bool:
        return _lib.net_ring_is_full(self._ring)


class NetCQ:
    """Lock-free completion queue for TX/RX completions."""

    def __init__(self, capacity: int = 4096):
        self._buf = ctypes.create_string_buffer(1024)
        self._cq = ctypes.cast(self._buf, ctypes.c_void_p)
        if _lib.net_cq_init(self._cq, capacity) != 0:
            raise MemoryError("net_cq_init failed")

    def __del__(self):
        _lib.net_cq_destroy(self._cq)

    def push(self, buf_ptr: int, status: int, length: int, timestamp_ns: int) -> bool:
        cqe = ctypes.create_string_buffer(32)
        ctypes.cast(cqe, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(buf_ptr)
        ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[1] = status
        ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[2] = length
        ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint64))[1] = timestamp_ns
        return _lib.net_cq_push(self._cq, ctypes.cast(cqe, ctypes.c_void_p))

    def pop(self) -> Optional[Tuple]:
        cqe = ctypes.create_string_buffer(32)
        if _lib.net_cq_pop(self._cq, ctypes.cast(cqe, ctypes.c_void_p)):
            buf_ptr = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_void_p))[0]
            status = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[1]
            length = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[2]
            timestamp_ns = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint64))[1]
            return (buf_ptr, status, length, timestamp_ns)
        return None


class NetQP:
    """RDMA-style Queue Pair for connection management."""

    def __init__(self, qp_num: int, pool: NetBufPool, ring_size: int = 4096):
        self._buf = ctypes.create_string_buffer(2048)
        self._qp = ctypes.cast(self._buf, ctypes.c_void_p)
        if _lib.net_qp_init(self._qp, qp_num, pool._pool, ring_size) != 0:
            raise MemoryError("net_qp_init failed")

    def __del__(self):
        _lib.net_qp_destroy(self._qp)

    def send(self, buf_ptr: int) -> bool:
        return _lib.net_qp_send(self._qp, ctypes.c_void_p(buf_ptr))

    def recv(self) -> Optional[int]:
        ptr = ctypes.c_void_p()
        if _lib.net_qp_recv(self._qp, ctypes.byref(ptr)):
            return ptr.value
        return None

    def poll_tx(self) -> Optional[Tuple]:
        cqe = ctypes.create_string_buffer(32)
        if _lib.net_qp_poll_tx(self._qp, ctypes.cast(cqe, ctypes.c_void_p)):
            buf_ptr = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_void_p))[0]
            status = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[1]
            length = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[2]
            timestamp_ns = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint64))[1]
            return (buf_ptr, status, length, timestamp_ns)
        return None

    def poll_rx(self) -> Optional[Tuple]:
        cqe = ctypes.create_string_buffer(32)
        if _lib.net_qp_poll_rx(self._qp, ctypes.cast(cqe, ctypes.c_void_p)):
            buf_ptr = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_void_p))[0]
            status = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[1]
            length = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint32))[2]
            timestamp_ns = ctypes.cast(cqe, ctypes.POINTER(ctypes.c_uint64))[1]
            return (buf_ptr, status, length, timestamp_ns)
        return None

    def loopback(self) -> int:
        """Move all buffers from TX ring to RX ring (for testing)."""
        return _lib.net_qp_loopback(self._qp)


class NetPort:
    """NIC port abstraction with buffer pool and queue pairs."""

    def __init__(self, port_id: int = 0, name: str = "eth0",
                 pool_capacity: int = 65536, buf_size: int = 9000):
        self._buf = ctypes.create_string_buffer(8192)
        self._port = ctypes.cast(self._buf, ctypes.c_void_p)
        if _lib.net_port_init(self._port, port_id, name.encode(),
                              pool_capacity, buf_size) != 0:
            raise MemoryError("net_port_init failed")

    def __del__(self):
        _lib.net_port_destroy(self._port)

    def create_qp(self, qp_num: int, ring_size: int = 4096) -> Optional[NetQP]:
        ptr = _lib.net_port_create_qp(self._port, qp_num, ring_size)
        if not ptr:
            return None
        qp = NetQP.__new__(NetQP)
        qp._buf = ctypes.create_string_buffer(2048)
        qp._qp = ctypes.cast(qp._buf, ctypes.c_void_p)
        ctypes.memmove(qp._qp, ptr, 2048)
        return qp


class NetStack:
    """Top-level network stack managing multiple ports."""

    def __init__(self, num_ports: int = 1):
        self._buf = ctypes.create_string_buffer(65536)
        self._stack = ctypes.cast(self._buf, ctypes.c_void_p)
        if _lib.net_stack_init(self._stack, num_ports) != 0:
            raise MemoryError("net_stack_init failed")

    def __del__(self):
        _lib.net_stack_destroy(self._stack)

    def get_port(self, port_id: int) -> Optional[int]:
        ptr = _lib.net_stack_get_port(self._stack, port_id)
        return ptr if ptr else None


def now_ns() -> int:
    """High-resolution monotonic timer in nanoseconds."""
    return _lib.net_now_ns_export()


__all__ = [
    "NetBufPool", "NetRing", "NetCQ", "NetQP", "NetPort", "NetStack", "now_ns",
]
