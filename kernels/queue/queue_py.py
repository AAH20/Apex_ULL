"""
ULL Queue Optimization Kernel — Python Interface
================================================

ctypes bindings to the C queue library plus benchmarking infrastructure.
"""

import ctypes
import os
import subprocess
import sys
import time
import statistics
from pathlib import Path
from typing import List, Tuple, Optional

# Build the C library on first import
_LIB_DIR = Path(__file__).parent
_LIB_PATH = _LIB_DIR / "libqueue.so"


def _build_lib() -> None:
    """Compile the C queue library if not already built."""
    if _LIB_PATH.exists() and _LIB_PATH.stat().st_mtime >= max(
        (_LIB_DIR / "queue.c").stat().st_mtime, (_LIB_DIR / "queue.h").stat().st_mtime
    ):
        return
    src = _LIB_DIR / "queue.c"
    hdr = _LIB_DIR / "queue.h"
    if not src.exists() or not hdr.exists():
        raise RuntimeError(f"queue.c or queue.h not found in {_LIB_DIR}")

    cmd = [
        os.environ.get("CC", "clang"), "-std=c11", "-pthread", "-O3", "-march=native", "-shared", "-fPIC",
        "-o", str(_LIB_PATH), str(src),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build libqueue.so:\n{result.stderr}")


_build_lib()

_lib = ctypes.CDLL(str(_LIB_PATH))
_lib.queue_storage_size.argtypes = [ctypes.c_uint]
_lib.queue_storage_size.restype = ctypes.c_size_t


def _aligned_storage(size):
    backing = ctypes.create_string_buffer(size + 63)
    pointer = ctypes.c_void_p((ctypes.addressof(backing) + 63) & ~63)
    return backing, pointer


# ================================================================== #
# ctypes type signatures                                              #
# ================================================================== #

_lib.spsc_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.spsc_init.restype = ctypes.c_int
_lib.spsc_destroy.argtypes = [ctypes.c_void_p]
_lib.spsc_push.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.spsc_push.restype = ctypes.c_bool
_lib.spsc_pop.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.spsc_pop.restype = ctypes.c_bool
_lib.spsc_is_empty.argtypes = [ctypes.c_void_p]
_lib.spsc_is_empty.restype = ctypes.c_bool
_lib.spsc_is_full.argtypes = [ctypes.c_void_p]
_lib.spsc_is_full.restype = ctypes.c_bool
_lib.spsc_size.argtypes = [ctypes.c_void_p]
_lib.spsc_size.restype = ctypes.c_uint64
_lib.spsc_push_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint64]
_lib.spsc_push_batch.restype = ctypes.c_uint64
_lib.spsc_pop_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint64]
_lib.spsc_pop_batch.restype = ctypes.c_uint64

_lib.mpsc_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.mpsc_init.restype = ctypes.c_int
_lib.mpsc_destroy.argtypes = [ctypes.c_void_p]
_lib.mpsc_push.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.mpsc_push.restype = ctypes.c_bool
_lib.mpsc_pop.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.mpsc_pop.restype = ctypes.c_bool
_lib.mpsc_is_empty.argtypes = [ctypes.c_void_p]
_lib.mpsc_is_empty.restype = ctypes.c_bool
_lib.mpsc_size.argtypes = [ctypes.c_void_p]
_lib.mpsc_size.restype = ctypes.c_uint64

_lib.mpmc_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.mpmc_init.restype = ctypes.c_int
_lib.mpmc_destroy.argtypes = [ctypes.c_void_p]
_lib.mpmc_push.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.mpmc_push.restype = ctypes.c_bool
_lib.mpmc_pop.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.mpmc_pop.restype = ctypes.c_bool
_lib.mpmc_is_empty.argtypes = [ctypes.c_void_p]
_lib.mpmc_is_empty.restype = ctypes.c_bool
_lib.mpmc_size.argtypes = [ctypes.c_void_p]
_lib.mpmc_size.restype = ctypes.c_uint64

_lib.spmc_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.spmc_init.restype = ctypes.c_int
_lib.spmc_destroy.argtypes = [ctypes.c_void_p]
_lib.spmc_push.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.spmc_push.restype = ctypes.c_bool
_lib.spmc_pop.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.spmc_pop.restype = ctypes.c_bool
_lib.spmc_is_empty.argtypes = [ctypes.c_void_p]
_lib.spmc_is_empty.restype = ctypes.c_bool
_lib.spmc_size.argtypes = [ctypes.c_void_p]
_lib.spmc_size.restype = ctypes.c_uint64

_lib.disruptor_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.disruptor_init.restype = ctypes.c_int
_lib.disruptor_destroy.argtypes = [ctypes.c_void_p]
_lib.disruptor_publish.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.disruptor_publish.restype = ctypes.c_bool
_lib.disruptor_next_sequence.argtypes = [ctypes.c_void_p]
_lib.disruptor_next_sequence.restype = ctypes.c_uint64

_lib.ull_queue_init.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.ull_queue_init.restype = ctypes.c_int
_lib.ull_queue_destroy.argtypes = [ctypes.c_void_p]
_lib.ull_queue_push.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.ull_queue_push.restype = ctypes.c_bool
_lib.ull_queue_pop.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.ull_queue_pop.restype = ctypes.c_bool
_lib.ull_queue_set_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]

_lib.ull_now_ns_export.argtypes = []
_lib.ull_now_ns_export.restype = ctypes.c_uint64


# ================================================================== #
# Python queue wrappers                                               #
# ================================================================== #

class SPSCQueue:
    """Single Producer Single Consumer bounded atomic ring buffer."""

    def __init__(self, capacity: int = 1024):
        self._buf, self._q = _aligned_storage(_lib.queue_storage_size(0))
        if _lib.spsc_init(self._q, capacity) != 0:
            raise MemoryError("spsc_init failed")

    def __del__(self):
        _lib.spsc_destroy(self._q)

    def push(self, item) -> bool:
        return _lib.spsc_push(self._q, ctypes.c_void_p(item))

    def pop(self) -> Optional[object]:
        ptr = ctypes.c_void_p()
        if _lib.spsc_pop(self._q, ctypes.byref(ptr)):
            return ptr.value
        return None

    @property
    def size(self) -> int:
        return _lib.spsc_size(self._q)

    def is_empty(self) -> bool:
        return _lib.spsc_is_empty(self._q)

    def is_full(self) -> bool:
        return _lib.spsc_is_full(self._q)


class MPSCQueue:
    """Multi Producer Single Consumer bounded atomic ring buffer."""

    def __init__(self, capacity: int = 1024):
        self._buf, self._q = _aligned_storage(_lib.queue_storage_size(1))
        if _lib.mpsc_init(self._q, capacity) != 0:
            raise MemoryError("mpsc_init failed")

    def __del__(self):
        _lib.mpsc_destroy(self._q)

    def push(self, item) -> bool:
        return _lib.mpsc_push(self._q, ctypes.c_void_p(item))

    def pop(self) -> Optional[object]:
        ptr = ctypes.c_void_p()
        if _lib.mpsc_pop(self._q, ctypes.byref(ptr)):
            return ptr.value
        return None

    @property
    def size(self) -> int:
        return _lib.mpsc_size(self._q)

    def is_empty(self) -> bool:
        return _lib.mpsc_is_empty(self._q)


class MPMCQueue:
    """Multi Producer Multi Consumer bounded atomic ring buffer."""

    def __init__(self, capacity: int = 1024):
        self._buf, self._q = _aligned_storage(_lib.queue_storage_size(2))
        if _lib.mpmc_init(self._q, capacity) != 0:
            raise MemoryError("mpmc_init failed")

    def __del__(self):
        _lib.mpmc_destroy(self._q)

    def push(self, item) -> bool:
        return _lib.mpmc_push(self._q, ctypes.c_void_p(item))

    def pop(self) -> Optional[object]:
        ptr = ctypes.c_void_p()
        if _lib.mpmc_pop(self._q, ctypes.byref(ptr)):
            return ptr.value
        return None

    @property
    def size(self) -> int:
        return _lib.mpmc_size(self._q)

    def is_empty(self) -> bool:
        return _lib.mpmc_is_empty(self._q)


class SPMCQueue:
    """Single Producer Multi Consumer bounded atomic ring buffer."""

    def __init__(self, capacity: int = 1024):
        self._buf, self._q = _aligned_storage(_lib.queue_storage_size(3))
        if _lib.spmc_init(self._q, capacity) != 0:
            raise MemoryError("spmc_init failed")

    def __del__(self):
        _lib.spmc_destroy(self._q)

    def push(self, item) -> bool:
        return _lib.spmc_push(self._q, ctypes.c_void_p(item))

    def pop(self) -> Optional[object]:
        ptr = ctypes.c_void_p()
        if _lib.spmc_pop(self._q, ctypes.byref(ptr)):
            return ptr.value
        return None

    @property
    def size(self) -> int:
        return _lib.spmc_size(self._q)

    def is_empty(self) -> bool:
        return _lib.spmc_is_empty(self._q)


class ULLQueue:
    """Bounded queue: MPMC by default; explicit SPSC only under single-owner contract."""

    def __init__(self, capacity: int = 1024):
        self._buf, self._q = _aligned_storage(_lib.queue_storage_size(4))
        if _lib.ull_queue_init(self._q, capacity) != 0:
            raise MemoryError("ull_queue_init failed")

    def __del__(self):
        _lib.ull_queue_destroy(self._q)

    def push(self, item) -> bool:
        return _lib.ull_queue_push(self._q, ctypes.c_void_p(item))

    def pop(self) -> Optional[object]:
        ptr = ctypes.c_void_p()
        if _lib.ull_queue_pop(self._q, ctypes.byref(ptr)):
            return ptr.value
        return None

    def set_mode(self, mode: int):
        """0=auto, 1=force SPSC, 2=force MPMC"""
        _lib.ull_queue_set_mode(self._q, mode)


class Disruptor:
    """Unavailable Disruptor placeholder; refuses initialization."""

    def __init__(self, capacity: int = 1024):
        self._buf, self._d = _aligned_storage(_lib.queue_storage_size(5))
        if _lib.disruptor_init(self._d, capacity) != 0:
            raise NotImplementedError("Disruptor sequence barrier is not implemented")

    def __del__(self):
        _lib.disruptor_destroy(self._d)

    def publish(self, event) -> bool:
        return _lib.disruptor_publish(self._d, ctypes.c_void_p(event))

    @property
    def next_sequence(self) -> int:
        return _lib.disruptor_next_sequence(self._d)


# ================================================================== #
# Utility functions                                                   #
# ================================================================== #

def now_ns() -> int:
    """High-resolution monotonic timer in nanoseconds."""
    return _lib.ull_now_ns_export()


__all__ = [
    "SPSCQueue", "MPSCQueue", "MPMCQueue", "SPMCQueue",
    "ULLQueue", "Disruptor", "now_ns",
]
