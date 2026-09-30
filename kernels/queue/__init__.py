"""
ULL Queue Optimization Kernel
==============================

Ultra-low-latency lock-free queue implementations for HFT and real-time systems.

Supported topologies:
- SPSC: Single Producer, Single Consumer (zero CAS on fast path)
- MPSC: Multi Producer, Single Consumer (CAS on enqueue only)
- MPMC: Multi Producer, Multi Consumer (CAS on both ends)
- SPMC: Single Producer, Multi Consumer (CAS on dequeue only)
- Disruptor: LMAX-style event processor with sequence barriers
- ULL Queue: Hybrid SPSC/MPMC with automatic fallback

All queues use cache-line alignment, power-of-2 ring sizes, and minimal
memory barriers for nanosecond-scale latency.
"""

from .queue_py import (
    SPSCQueue,
    MPSCQueue,
    MPMCQueue,
    SPMCQueue,
    ULLQueue,
    Disruptor,
    now_ns,
)

__all__ = [
    "SPSCQueue",
    "MPSCQueue",
    "MPMCQueue",
    "SPMCQueue",
    "ULLQueue",
    "Disruptor",
    "now_ns",
]
